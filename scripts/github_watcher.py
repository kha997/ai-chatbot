"""Read public AI ChatBot work metadata and maintain a local queue."""

import hashlib
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

API = "https://api.github.com/repos/kha997/ai-chatbot"
AGENTS = {"codex", "qoder", "opencode", "kilo"}
# Mapping applies only to verified GitHub identities. Add others through review.
USERS = {"kha997": "codex"}
TEAMS = {}
LIMIT = 8 * 1024 * 1024
PAGES = 5
PAGE_SIZE = 50


class PollError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_for(resource, index):
    if resource not in {"issues", "pulls"} or not 1 <= index <= PAGES:
        raise ValueError("route")
    return Request(
        f"{API}/{resource}?state=open&per_page={PAGE_SIZE}&page={index}",
        headers={"User-Agent": "AIChatBot-local-watcher/1",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="GET",
    )


def get_page(resource, index):
    request = request_for(resource, index)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=5) as response:
        payload = response.read(LIMIT + 1)
    if len(payload) > LIMIT:
        raise PollError("size")
    return payload


def page(resource, index, sleep=time.sleep):
    for attempt in range(2):
        try:
            data = json.loads(get_page(resource, index))
            if not isinstance(data, list) or len(data) > PAGE_SIZE:
                raise PollError("parse")
            return data
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if code in {403, 429}:
                raise PollError("rate-or-access") from None
            if attempt or code not in {500, 502, 503, 504}:
                raise PollError("http") from None
        except (TimeoutError, URLError, ConnectionError):
            if attempt:
                raise PollError("network") from None
        except (ValueError, UnicodeError):
            raise PollError("parse") from None
        sleep(1)
    raise AssertionError("unreachable")


def collect(resource):
    records = []
    for index in range(1, PAGES + 1):
        batch = page(resource, index)
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            return records
    raise PollError("page-limit")


def mapped(identities, key, mapping):
    return {mapping[item[key].lower()] for item in identities
            if item[key].lower() in mapping}


def classify(issues, pulls):
    jobs = set()
    pull_metadata = {}
    try:
        for item in issues:
            number = item["number"]
            if type(number) is not int or number < 1:
                raise ValueError("number")
            labels = {label["name"].lower() for label in item["labels"]}
            explicit = {agent for agent in AGENTS if f"agent:{agent}" in labels}
            routes = explicit or mapped(item["assignees"], "login", USERS)
            if item.get("pull_request") is not None:
                pull_metadata[number] = routes
                continue
            approved = (item["author_association"] == "OWNER"
                        and "work:approved" in labels)
            for agent in routes:
                jobs.add(("issue", number, agent, "approved" if approved else "triage", ""))
        for item in pulls:
            number = item["number"]
            sha = item["head"]["sha"]
            if type(number) is not int or number < 1 or not re.fullmatch("[0-9a-f]{40}", sha):
                raise ValueError("PR identity")
            requested = mapped(item["requested_reviewers"], "login", USERS)
            requested |= mapped(item["requested_teams"], "slug", TEAMS)
            if not item["draft"]:
                for agent in requested:
                    jobs.add(("review", number, agent, "review-requested", sha))
            for agent in pull_metadata.get(number, set()) - (requested if not item["draft"] else set()):
                jobs.add(("pr", number, agent, "triage", sha))
    except (KeyError, AttributeError, TypeError, ValueError):
        raise PollError("parse") from None
    return [list(job) for job in sorted(jobs)]


@contextmanager
def exclusive(directory):
    with (directory / "poll.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                yield False
                return
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
        yield True


def poll(directory, discover, now):
    target = directory / "state.json"
    try:
        state = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
        if not isinstance(state, dict) or state.get("schema", 1) != 1:
            raise ValueError("state schema")
        if now < int(state.get("retry_after", 0)):
            print("backoff")
            return 0
        failures = int(state.get("failures", 0))
    except (ValueError, TypeError, OSError):
        print("invalid state; see recovery runbook", file=sys.stderr)
        return 1
    state.update(schema=1, last_poll=now)
    result = 0
    try:
        jobs = discover()
    except PollError as exc:
        failures += 1
        delay = 3600 if str(exc) == "rate-or-access" else 1800
        state.update(failures=failures, retry_after=now + min(14400, delay * 2 ** min(failures - 1, 3)),
                     error=str(exc))
        result = 1
        print(f"poll failed: {exc}", file=sys.stderr)
    else:
        digest = hashlib.sha256(json.dumps(jobs, separators=(",", ":")).encode()).hexdigest()
        changed = digest != state.get("queue_hash")
        state.update(jobs=jobs, queue_hash=digest, last_success=now,
                     failures=0, retry_after=0, error=None)
        if changed:
            state["last_change"] = now
        print(f"{'changed' if changed else 'unchanged'}: {len(jobs)} queue entries")
    temp = directory / "state.tmp"
    temp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temp.replace(target)
    return result


def run(directory, discover=None):
    directory.mkdir(parents=True, exist_ok=True)
    with exclusive(directory) as acquired:
        if not acquired or (directory / "paused").exists():
            print("overlap or paused")
            return 0
        if discover is None:
            discover = lambda: classify(collect("issues"), collect("pulls"))
        return poll(directory, discover, int(time.time()))


if __name__ == "__main__":
    if len(sys.argv) != 1 or not os.environ.get("LOCALAPPDATA"):
        raise SystemExit("Run without arguments under the registered Windows user.")
    raise SystemExit(run(Path(os.environ["LOCALAPPDATA"]) / "AIChatBotWatcher"))
