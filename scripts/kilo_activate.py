"""Manually activate a single Kilo Free qualification after a verified Owner record."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import ssl
import stat
import subprocess
import sys
import tempfile

ISSUE_URL = "https://api.github.com/repos/kha997/ai-chatbot/issues/20"
OWNER_ID = 207400889
MODEL = "recursive/flint-v1.0:free"
KILO_HOST = "ai-gateway.kilo.ai"
SOURCE_FILES = ("scripts/kilo_activate.py", "scripts/kilo_gate15.py", "scripts/kilo_owner_gate.py")
LINUX_LOCKS = sys.platform == "linux"
CA_FILE = "/etc/ssl/certs/ca-certificates.crt"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def match_digest(raw, expected):
    return isinstance(expected, str) and sha(raw) == expected


def compact(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("ascii")


def approval_line(commit, manifest, runner, expires):
    return (f"APPROVE ONE KILO FREE POST | issue=20 | commit={commit} | manifest={manifest} | runner={runner}"
            f" | model={MODEL} | max_posts=1 | incremental_vnd=0 | expires={expires}")


def parse_utc(stamp):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
        raise ValueError("invalid UTC timestamp")
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def verify_approval(record, comment_id, commit, manifest, runner, now):
    try:
        if (not re.fullmatch(r"[a-f0-9]{40}", commit) or not re.fullmatch(r"[a-f0-9]{64}", manifest)
                or not re.fullmatch(r"[a-f0-9]{64}", runner)
                or type(comment_id) is not int or comment_id < 1
                or record["id"] != comment_id or record["issue_url"] != ISSUE_URL
                or record["author_association"] != "OWNER"
                or record["user"]["id"] != OWNER_ID or record["user"]["login"] != "kha997"
                or record["updated_at"] != record["created_at"]):
            return False
        created = parse_utc(record["created_at"])
        expiry_text = record["body"].rsplit(" | expires=", 1)[1]
        expiry = parse_utc(expiry_text)
        return (record["body"] == approval_line(commit, manifest, runner, expiry_text)
                and created <= now < expiry <= created + timedelta(hours=24))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return False


def ensure_regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("untrusted state file")


class Lease:
    def __init__(self, directory):
        self.directory = directory
        self.active = True
        self.reserved = False


@contextmanager
def lease(path):
    import fcntl

    if not LINUX_LOCKS:
        raise ValueError("Linux locks required")
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(parent)
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError("untrusted state parent")
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        directory = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            os.fsync(parent)
        except OSError:
            os.close(directory)
            raise
    finally:
        os.close(parent)
    lock = None
    grant = Lease(directory)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("untrusted state directory")
        lock = os.open("exclusive.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                       0o600, dir_fd=directory)
        ensure_regular(lock)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another qualification owns the lock") from exc
        try:
            os.stat("issue20.spent", dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            yield grant
        else:
            raise ValueError("Issue #20 already spent")
    finally:
        grant.active = False
        if lock is not None:
            os.close(lock)
        os.close(directory)


def reserve(grant, commit, manifest, comment_id):
    if type(grant) is not Lease or not grant.active or grant.reserved:
        raise ValueError("reservation unavailable")
    try:
        fd = os.open("issue20.spent", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=grant.directory)
    except FileExistsError as exc:
        raise ValueError("Issue #20 already spent") from exc
    with os.fdopen(fd, "wb") as file:
        file.write(compact({"commit": commit, "manifest": manifest, "approval_comment": comment_id}))
        file.flush()
        os.fsync(file.fileno())
    os.fsync(grant.directory)
    grant.reserved = True


def runner_binding(grant, *, create=False):
    if type(grant) is not Lease or not grant.active:
        raise ValueError("runner binding unavailable")
    name = "runner-identity"
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(name, flags, dir_fd=grant.directory)
    except FileNotFoundError:
        if not create:
            raise
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=grant.directory)
        with os.fdopen(fd, "wb") as file:
            file.write(os.urandom(32))
            file.flush()
            os.fsync(file.fileno())
        os.fsync(grant.directory)
        fd = os.open(name, flags, dir_fd=grant.directory)
    with os.fdopen(fd, "rb") as file:
        ensure_regular(file.fileno())
        nonce = file.read(33)
    machine = Path("/etc/machine-id").read_bytes().strip()
    if len(nonce) != 32 or not re.fullmatch(rb"[a-f0-9]{32}", machine):
        raise ValueError("untrusted runner identity")
    return sha(b"AIChatBot Issue 20\0" + machine + nonce)


def tls_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=CA_FILE)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def require_tls(sock, host):
    if (not isinstance(sock, ssl.SSLSocket) or sock.server_hostname != host
            or sock.context.verify_mode != ssl.CERT_REQUIRED or not sock.context.check_hostname
            or sock.version() not in ("TLSv1.2", "TLSv1.3") or not sock.getpeercert()):
        raise ValueError("unverified TLS peer")


def fixed_body():
    from scripts.kilo_gate15 import PROMPT

    return {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "stream": True, "max_tokens": 128, "stream_options": {"include_usage": True}}


def network(kind, comment_id=None, proof=None):
    """Exactly one HTTP request, with no reconnect, redirect, retry or proxy path."""
    from scripts.kilo_owner_gate import prepare_request, read_http_response

    if kind == "owner" and type(comment_id) is int and 0 < comment_id < 10**19:
        host, path = "api.github.com", f"/repos/kha997/ai-chatbot/issues/comments/{comment_id}"
        method, body, limit = "GET", None, 128 * 1024
        headers = {"User-Agent": "AIChatBot-Issue20", "Accept": "application/vnd.github+json"}
    elif kind == "catalog":
        host, path = KILO_HOST, "/api/v1/models"
        method, body, limit = "GET", None, 2 * 1024 * 1024
        headers = {"Accept": "application/json"}
    elif kind == "post":
        if type(proof) is not PostProof or not proof.claim():
            raise ValueError("missing verified POST proof")
        request = prepare_request(fixed_body())
        host, path, method, body = request.host, request.path, request.method, request.body
        limit, headers = 32768, dict(request.headers)
    else:
        raise ValueError("unexpected network operation")

    headers = headers | {"Accept-Encoding": "identity", "Connection": "close"}
    posts = 0
    connection = None
    try:
        connection = http.client.HTTPSConnection(host, 443, context=tls_context(), timeout=8)
        connection.connect()
        require_tls(connection.sock, host)
        connection.auto_open = 0
        if kind == "post" and not proof.valid():
            raise ValueError("approval expired before POST")
        posts = int(kind == "post")  # Count at the request boundary, even for write failure.
        connection.request(method, path, body=body, headers=headers)
        with connection.getresponse() as response:
            reply = read_http_response(response, limit, require_framed=(kind == "post"))
        return posts, reply
    except (OSError, ValueError, http.client.HTTPException):
        return posts, (502, None, b"", None)
    finally:
        if connection:
            connection.close()


class PostProof:
    def __init__(self, grant, record, comment_id, commit, manifest, runner):
        self.grant, self.record = grant, record
        self.comment_id, self.commit, self.manifest = comment_id, commit, manifest
        self.runner = runner

    def valid(self):
        try:
            return (type(self.grant) is Lease and self.grant.active and self.grant.reserved
                    and runner_binding(self.grant) == self.runner
                    and verify_approval(self.record, self.comment_id, self.commit, self.manifest,
                                        self.runner, datetime.now(timezone.utc)))
        except (ValueError, OSError):
            return False

    def claim(self):
        if not self.valid():
            return False
        try:
            fd = os.open("issue20.post", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self.grant.directory)
        except FileExistsError:
            return False
        with os.fdopen(fd, "wb") as file:
            file.write(b"one request boundary claimed\n")
            file.flush()
            os.fsync(file.fileno())
        os.fsync(self.grant.directory)
        return True


def worker_child(pipe, kind, comment_id, proof, parent):
    import ctypes

    try:
        if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
            return
        os.environ.clear()
        if pipe.poll(50) and pipe.recv() == "go":
            pipe.send(network(kind, comment_id, proof))
    except (EOFError, OSError, ValueError):
        pass
    finally:
        pipe.close()


class Worker:
    """One operation in a disposable process. Start before the relay creates threads."""

    def __init__(self, kind, comment_id=None, *, proof=None):
        import multiprocessing

        if kind == "post" and (type(proof) is not PostProof or not proof.valid()):
            raise ValueError("missing verified POST proof")
        ctx = multiprocessing.get_context("fork")
        self.pipe, child = ctx.Pipe()
        self.kind = kind
        self.issued = False
        self.process = ctx.Process(target=worker_child, args=(child, kind, comment_id, proof, os.getpid()),
                                   daemon=True)
        try:
            self.process.start()
        finally:
            child.close()

    def call(self, timeout):
        if self.issued:
            raise ValueError("worker already used")
        self.issued = True
        try:
            self.pipe.send("go")
            if self.pipe.poll(timeout):
                return self.pipe.recv()
        except (EOFError, OSError):
            pass
        self.close()
        return None, (504, None, b"", None)  # A timed-out POST has uncertain wire delivery.

    def close(self):
        self.pipe.close()
        self.process.join(0.2)
        if self.process.is_alive():
            self.process.kill()
            self.process.join(2)
        if self.process.is_alive():
            raise ValueError("network worker did not exit")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AuthorizedExchange:
    def __init__(self, grant, worker, expires):
        if type(grant) is not Lease or not grant.active or not grant.reserved or (
            type(worker) is not Worker or worker.kind != "post"
        ):
            raise ValueError("no verified reservation")
        self._grant, self._worker, self._expires = grant, worker, expires
        self.post_count = 0

    @property
    def armed(self):
        return self._grant.active and self._grant.reserved

    def __call__(self, body):
        from scripts.kilo_owner_gate import prepare_request

        prepare_request(body)
        if not self.armed or datetime.now(timezone.utc) >= self._expires:
            return 403, None, b"", None
        self.post_count, response = self._worker.call(22)
        return response


def read_json_operation(kind, comment_id=None):
    with Worker(kind, comment_id) as worker:
        _, (status, media, raw, encoding) = worker.call(12)
    if (status != 200 or len(raw) > (128 * 1024 if kind == "owner" else 2 * 1024 * 1024)
            or (media or "").split(";", 1)[0].lower() not in ("application/json", "application/vnd.github+json")
            or encoding not in (None, "", "identity")):
        raise ValueError("metadata request rejected")
    return strict_json(raw)


def strict_json(raw):
    from decimal import Decimal

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        return json.loads(raw, parse_float=Decimal, object_pairs_hook=unique)
    except RecursionError as exc:
        raise ValueError("invalid metadata nesting") from exc


def git_bytes(root, *args):
    return subprocess.check_output(["/usr/bin/git", "--no-replace-objects", "-C", str(root), *args],
                                   stderr=subprocess.DEVNULL, timeout=5,
                                   env={"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})


def pin_source(root, commit, stage):
    if git_bytes(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("checkout SHA mismatch")
    sources = {}
    for item in SOURCE_FILES:
        approved = git_bytes(root, "show", f"{commit}:{item}")
        if (root / item).read_bytes() != approved:
            raise ValueError("source digest mismatch")
        target = stage / item
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(approved)
        sources[item] = sha(approved)
    return sources


def pin_artifact(source, target, expected, limit):
    with source.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit or not match_digest(data, expected):
        raise ValueError("artifact digest mismatch")
    target.write_bytes(data)


def verify_local_wsl(home):
    release = Path("/proc/sys/kernel/osrelease").read_text().lower()
    fs = subprocess.check_output(["/usr/bin/findmnt", "-T", str(home), "-n", "-o", "FSTYPE"],
                                 stderr=subprocess.DEVNULL, timeout=5, env={}).decode().strip()
    if "microsoft" not in release or fs != "ext4":
        raise ValueError("requires the reviewed WSL local ext4 state boundary")


def local_home():
    import pwd

    if not LINUX_LOCKS or os.geteuid() == 0 or not sys.flags.isolated or not sys.flags.no_site:
        raise ValueError("use Python -IS as an ordinary WSL user")
    home = Path(pwd.getpwuid(os.geteuid()).pw_dir)
    if home.is_symlink() or home.stat().st_uid != os.geteuid() or home.stat().st_mode & 0o022:
        raise ValueError("untrusted home")
    verify_local_wsl(home)
    return home


def activate(args):
    home = local_home()
    root = Path(args.repo).resolve()
    launcher = Path(__file__).resolve()
    if (launcher == root / SOURCE_FILES[0] or launcher.parent.stat().st_uid != os.geteuid()
            or stat.S_IMODE(launcher.parent.stat().st_mode) != 0o700):
        raise ValueError("launcher must be externally verified in a private staging directory")
    with tempfile.TemporaryDirectory(prefix="issue20-kilo-", dir="/tmp") as temp:
        stage = Path(temp)
        sources = pin_source(root, args.commit, stage)
        if not match_digest(launcher.read_bytes(), sources[SOURCE_FILES[0]]):
            raise ValueError("staged launcher digest mismatch")
        # Only the verified Git blobs can supply these modules.
        if any(name == "scripts" or name.startswith("scripts.") for name in sys.modules):
            raise ValueError("unexpected preloaded application modules")
        (stage / "scripts" / "__init__.py").write_bytes(b"")
        sys.path.insert(0, temp)
        if __name__ == "__main__":
            sys.modules["scripts.kilo_activate"] = sys.modules[__name__]
        from scripts.kilo_gate15 import KILO_ELF_SHA, RELEASE_SHA, run
        from scripts.kilo_owner_gate import SANDBOX_SHA256, approved_catalog, prepare_request

        archive, sandbox = stage / "archive.tar.gz", stage / "bwrap"
        pin_artifact(Path(args.archive), archive, RELEASE_SHA, 128 * 1024 * 1024)
        pin_artifact(Path(args.sandbox), sandbox, SANDBOX_SHA256, 2 * 1024 * 1024)
        manifest = sha(compact({"sources": sources, "archive": RELEASE_SHA, "kilo": KILO_ELF_SHA,
                                "bwrap": SANDBOX_SHA256, "body": sha(prepare_request(fixed_body()).body)}))
        with lease(home / ".aichatbot-issue20") as grant:
            runner = runner_binding(grant)
            owner = read_json_operation("owner", args.approval)
            if not verify_approval(owner, args.approval, args.commit, manifest, runner, datetime.now(timezone.utc)):
                raise ValueError("missing exact Owner authorization")
            expires = parse_utc(owner["body"].rsplit(" | expires=", 1)[1])
            reserve(grant, args.commit, manifest, args.approval)
            if not approved_catalog(read_json_operation("catalog")):
                raise ValueError("exact model unavailable or price not zero")
            proof = PostProof(grant, owner, args.approval, args.commit, manifest, runner)
            from contextlib import redirect_stdout
            import io

            evidence = io.StringIO()
            with Worker("post", proof=proof) as worker:
                exchange = AuthorizedExchange(grant, worker, expires)
                with redirect_stdout(evidence):
                    result = run(archive, "authorized", sandbox=sandbox, exchange=exchange)
            receipt = json.loads(evidence.getvalue())
            usage = receipt.get("protocol", {}).get("usage") or "UNKNOWN"
            print(json.dumps(receipt | {"network_worker_closed": True, "qualification_passed": result == 0,
                                        "provider_usage": usage}))
            return result


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--local-runner-id", action="store_true")
    for name in ("repo", "commit", "approval", "archive", "sandbox"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if args.local_runner_id and not any(getattr(args, name) for name in ("repo", "commit", "approval", "archive", "sandbox")):
        try:
            with lease(local_home() / ".aichatbot-issue20") as grant:
                print(runner_binding(grant, create=True))
            return 0
        except (OSError, ValueError, subprocess.SubprocessError):
            print("Runner identity unavailable")
            return 1
    if (args.local_runner_id or not all(getattr(args, name) for name in ("repo", "commit", "approval", "archive", "sandbox"))
            or not re.fullmatch(r"[a-f0-9]{40}", args.commit)
            or not re.fullmatch(r"[1-9][0-9]{0,18}", args.approval)):
        print("NO_LIVE_AUTHORIZATION")
        return 1
    args.approval = int(args.approval)
    try:
        return activate(args)
    except (OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt):
        print("Activation closed; if reserved, the attempt remains spent.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
