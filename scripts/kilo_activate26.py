"""Default-inert manual Kilo Free gate for the new Issue #26 authorization scope."""

import argparse
from contextlib import closing, redirect_stdout
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import ssl
import stat
import subprocess
import sys
import tempfile

SCOPE = 26
ISSUE_URL = "https://api.github.com/repos/kha997/ai-chatbot/issues/26"
STATE_DIR = ".aichatbot-issue26"
LAUNCHER = "scripts/kilo_activate26.py"
SOURCES = (LAUNCHER, "scripts/kilo_activate.py", "scripts/kilo_gate15.py", "scripts/kilo_owner_gate.py",
           "scripts/kilo_sse_stream.py", "scripts/kilo_hard_job.py")
METADATA_SECONDS = 12
POST_SECONDS = 24
SSE_SECONDS = 23
PIPELINE_SECONDS = 55


def verify_owner(record, comment_id, commit, manifest, runner, now):
    from scripts.kilo_activate import verify_approval

    return verify_approval(record, comment_id, commit, manifest, runner, now, scope=SCOPE)


def closed(reason, status=None):
    from scripts.kilo_gate15 import json_reply

    return json_reply(502) | {"protocol": {"classification": reason, "http_status": status, "relay_bytes": 0}}


def post_once(proof):
    from scripts.kilo_activate import KILO_HOST, PostProof, fixed_body, require_tls, tls_context
    from scripts.kilo_owner_gate import prepare_request
    from scripts.kilo_sse_stream import inspect_response

    if type(proof) is not PostProof or proof.grant.scope != SCOPE or not proof.claim():
        raise ValueError("missing distinct, verified Issue #26 POST claim")
    request = prepare_request(fixed_body())
    headers = dict(request.headers) | {"Connection": "close"}
    count = 0
    try:
        with closing(http.client.HTTPSConnection(KILO_HOST, 443, context=tls_context(), timeout=None)) as connection:
            connection.connect()
            require_tls(connection.sock, KILO_HOST)
            connection.auto_open = 0
            if not proof.valid():
                return count, closed("approval_expired_before_post")
            count = 1  # One physical request boundary; delivery may be unknown after a failed write.
            connection.request(request.method, request.path, body=request.body, headers=headers)
            with connection.sock.makefile("rb") as wire:
                return count, inspect_response(wire, seconds=SSE_SECONDS)
    except ssl.SSLCertVerificationError:
        return count, closed("tls_certificate")
    except ssl.SSLError:
        return count, closed("tls_protocol")
    except (OSError, ValueError, http.client.HTTPException):
        return count, closed("transport_failure")


def metadata(kind, comment_id=None):
    from scripts.kilo_activate import network, strict_json
    from scripts.kilo_hard_job import HardJob
    from scripts.kilo_owner_gate import approved_catalog

    if kind not in ("owner", "catalog"):
        raise ValueError("unsupported read-only operation")

    def read():
        _, (status, media, raw, encoding) = network(kind, comment_id)
        if (status != 200 or len(raw) > (128 * 1024 if kind == "owner" else 2 * 1024 * 1024)
                or (media or "").split(";", 1)[0].lower() not in ("application/json", "application/vnd.github+json")
                or encoding not in (None, "", "identity")):
            return None
        value = strict_json(raw)
        if kind == "catalog":
            return approved_catalog(value)
        user = value["user"]
        record = {key: value[key] for key in ("id", "issue_url", "author_association", "created_at", "updated_at", "body")}
        record["user"] = {key: user[key] for key in ("id", "login")}
        return record

    with HardJob(read) as job:
        outcome = job.run(METADATA_SECONDS)
    if outcome["outcome"] != "complete" or outcome.get("result") is None:
        raise ValueError("metadata request rejected")
    return outcome["result"]


class AuthorizedExchange:
    """Typed one-shot adapter constructed only after durable reservation and zero-price check."""

    def __init__(self, proof, scratch):
        from scripts.kilo_activate import PostProof
        from scripts.kilo_hard_job import HardJob

        if type(proof) is not PostProof or proof.grant.scope != SCOPE or not proof.valid():
            raise ValueError("missing Issue #26 authorization")
        self.proof = proof
        self.scratch = scratch
        self.post_count = 0
        self.worker = HardJob(lambda: post_once(proof))

    @property
    def armed(self):
        return self.proof.valid()

    def __call__(self, body):
        from scripts.kilo_owner_gate import prepare_request

        prepare_request(body)
        if not self.armed:
            return closed("approval_expired_before_post")
        outcome = self.worker.run(POST_SECONDS)
        result = outcome.pop("result", None)
        if result is None:
            self.post_count = None
            answer = closed(outcome["outcome"])
        else:
            self.post_count, answer = result
        return answer | {"worker": outcome}


def run_pipeline(archive, sandbox, proof, scratch):
    from scripts.kilo_gate15 import run
    from scripts.kilo_hard_job import HardJob

    def pipeline():
        exchange = AuthorizedExchange(proof, scratch)
        log = io.StringIO()
        with exchange.worker, redirect_stdout(log):
            code = run(archive, "authorized26", sandbox=sandbox, exchange=exchange)
        return {"code": code, "evidence": json.loads(log.getvalue())}

    with HardJob(pipeline) as job:
        outcome = job.run(PIPELINE_SECONDS)
    result = outcome.pop("result", None)
    try:
        os.stat("issue26.post", dir_fd=proof.grant.directory, follow_symlinks=False)
        claim = True
    except FileNotFoundError:
        claim = False
    receipt = result["evidence"] if result is not None else {"forwarded": None if claim else 0}
    protocol = receipt.get("protocol", {})
    usage = protocol.get("usage") if protocol.get("classification") == "complete" else None
    model = ("MATCH" if protocol.get("classification") == "complete" else "REJECTED") \
        if protocol.get("model_supplied") else "UNKNOWN"
    passed = result is not None and result["code"] == 0
    return int(not passed), receipt | {"pipeline_worker": outcome, "post_claimed": claim,
                                        "qualification_passed": passed, "provider_usage": usage or "UNKNOWN",
                                        "provider_model_identity": model}


def manifest_for(sources):
    from scripts.kilo_activate import compact, fixed_body, sha
    from scripts.kilo_gate15 import KILO_ELF_SHA, RELEASE_SHA
    from scripts.kilo_owner_gate import SANDBOX_SHA256, prepare_request

    return sha(compact({"scope": SCOPE, "sources": sources, "archive": RELEASE_SHA, "kilo": KILO_ELF_SHA,
                        "bwrap": SANDBOX_SHA256, "body": sha(prepare_request(fixed_body()).body)}))


def activate(args):
    # Staging is always the entry point. The bootstrap externally verifies this file before Python starts.
    launcher = Path(__file__).resolve()
    root = Path(args.repo).resolve()
    if (launcher == root / LAUNCHER or launcher.parent.stat().st_uid != os.geteuid()
            or stat.S_IMODE(launcher.parent.stat().st_mode) != 0o700
            or any(name == "scripts" or name.startswith("scripts.") for name in sys.modules)):
        raise ValueError("use the externally verified private launcher stage")
    with tempfile.TemporaryDirectory(prefix="issue26-kilo-", dir="/tmp") as name:
        stage = Path(name)
        # Verify Git identities before importing any project code from the stage.
        git_env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}

        def git(*args):
            return subprocess.check_output(["/usr/bin/git", "--no-replace-objects", "-C", str(root), *args],
                                           env=git_env, timeout=5, stderr=subprocess.DEVNULL)
        if git("rev-parse", "HEAD").decode().strip() != args.commit:
            raise ValueError("checkout SHA mismatch")
        verified = {}
        for filename in SOURCES:
            blob = git("show", f"{args.commit}:{filename}")
            if len(blob) > 256 * 1024 or (root / filename).read_bytes() != blob:
                raise ValueError("Git source mismatch")
            target = stage / filename
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(blob)
            verified[filename] = hashlib.sha256(blob).hexdigest()
        if launcher.read_bytes() != (stage / LAUNCHER).read_bytes():
            raise ValueError("staged launcher mismatch")
        (stage / "scripts" / "__init__.py").write_bytes(b"")
        sys.path.insert(0, name)
        if __name__ == "__main__":
            sys.modules["scripts.kilo_activate26"] = sys.modules[__name__]

        from scripts.kilo_activate import PostProof, lease, local_home, pin_artifact, reserve, runner_binding
        from scripts.kilo_gate15 import RELEASE_SHA
        from scripts.kilo_owner_gate import SANDBOX_SHA256

        home = local_home()
        archive, sandbox = stage / "archive.tar.gz", stage / "bwrap"
        pin_artifact(Path(args.archive), archive, RELEASE_SHA, 128 * 1024 * 1024)
        pin_artifact(Path(args.sandbox), sandbox, SANDBOX_SHA256, 2 * 1024 * 1024)
        manifest = manifest_for(verified)
        with lease(home / STATE_DIR, scope=SCOPE) as grant:
            runner = runner_binding(grant, create=args.describe)
            if args.describe:
                print(json.dumps({"commit": args.commit, "manifest": manifest, "runner": runner, "sources": verified}))
                return 0
            owner = metadata("owner", args.approval)
            if not verify_owner(owner, args.approval, args.commit, manifest, runner, datetime.now(timezone.utc)):
                raise ValueError("missing exact Issue #26 Owner authorization")
            reserve(grant, args.commit, manifest, args.approval)
            if metadata("catalog") is not True:
                raise ValueError("exact model unavailable or nonzero price")
            proof = PostProof(grant, owner, args.approval, args.commit, manifest, runner)
            code, receipt = run_pipeline(archive, sandbox, proof, name)
            print(json.dumps(receipt | {"commit": args.commit, "manifest": manifest}))
            return code


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    for name in ("repo", "commit", "archive", "sandbox", "approval"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if (not all(getattr(args, key) for key in ("repo", "commit", "archive", "sandbox"))
            or not re.fullmatch(r"[a-f0-9]{40}", args.commit)
            or (args.describe and args.approval is not None)
            or (not args.describe and not re.fullmatch(r"[1-9][0-9]{0,18}", args.approval or ""))):
        print("NO_LIVE_AUTHORIZATION")
        return 1
    if args.approval is not None:
        args.approval = int(args.approval)
    try:
        return activate(args)
    except (OSError, ValueError, subprocess.SubprocessError, RuntimeError, KeyboardInterrupt):
        print("Issue #26 activation closed; any reserved attempt stays spent.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
