"""One-shot mock dispatcher audit in the existing Bubblewrap qualification profile."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_gate15 import Permit, emit_filter, unique_json_keys
from scripts.kilo_owner_gate import stage_sandbox
from scripts.kilo_sse_stream import require_offline_network

POLICY = {"adapter": "mock", "scope": "issue28", "incremental_vnd": 0, "model_requests": 0}
ORACLE = {"catalog": 2, "handoff": 1, "total": 3}
RECORDS = b'["catalog","handoff","catalog"]'
CASES = {"ok": "PASS", "bad-oracle": "INVALID_ORACLE", "nonzero": "CLI_ERROR",
         "timeout": "TIMED_OUT", "output-cap": "OUTPUT_CAP"}
OUTPUT_LIMIT = 4096
DEADLINE = 2
FIXTURE = Path(__file__).with_name("fixtures") / "dispatcher_mock_cli.py"


def verify_result(raw):
    value = json.loads(raw, object_pairs_hook=unique_json_keys)
    if value != ORACLE or not all(type(n) is int for n in value.values()):
        raise ValueError("oracle mismatch")
    return value


class MockDispatch:
    def __init__(self, policy):
        if policy != POLICY or any(type(policy[k]) is not int for k in ("incremental_vnd", "model_requests")):
            raise ValueError("mock policy mismatch")
        self.permit = Permit()

    def run(self, case, sandbox):
        require_offline_network()
        if case not in CASES or not self.permit.take():
            raise ValueError("invalid case or duplicate mock invocation")
        started = time.monotonic()
        with (tempfile.TemporaryDirectory(prefix="issue28-mock-", dir="/tmp") as scratch,
              tempfile.TemporaryFile(dir="/tmp") as seccomp,
              tempfile.TemporaryFile(dir="/tmp") as output, tempfile.TemporaryFile(dir="/tmp") as errors):
            root = Path(scratch)
            bwrap = stage_sandbox(sandbox, root / "bwrap")
            fixture, canary = root / "fixture.py", root / "host-only"
            fixture.write_bytes(FIXTURE.read_bytes())
            canary.write_text("synthetic outside workspace", encoding="ascii")
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "records.json").write_bytes(RECORDS)
            emit_filter(seccomp)
            argv = [str(bwrap), "--unshare-all", "--unshare-user", "--disable-userns",
                    "--die-with-parent", "--new-session", "--clearenv", "--cap-drop", "ALL",
                    "--seccomp", str(seccomp.fileno()),
                    "--ro-bind", "/usr/bin/python3", "/usr/bin/python3",
                    "--ro-bind", "/usr/lib/python3.12", "/usr/lib/python3.12",
                    "--ro-bind", "/usr/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu",
                    "--ro-bind", "/usr/lib64", "/usr/lib64",
                    "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
                    "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "--ro-bind", str(workspace), "/work", "--ro-bind", str(fixture), "/fixture.py",
                    "--chdir", "/work", "--setenv", "HOST_CANARY", str(canary),
                    "--setenv", "HOST_NETNS", str(Path("/proc/self/ns/net").stat().st_ino),
                    "--setenv", "HOME", "/tmp", "/usr/bin/python3", "-IS", "/fixture.py", case]
            timed_out = False
            with subprocess.Popen(argv, env={"GH_TOKEN": "synthetic-not-a-credential"},
                                  stdin=subprocess.DEVNULL, stdout=output, stderr=errors,
                                  start_new_session=True, pass_fds=(seccomp.fileno(),)) as child:
                try:
                    child.wait(timeout=DEADLINE)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=2)
            raw, err = (os.pread(pipe.fileno(), OUTPUT_LIMIT + 1, 0) for pipe in (output, errors))
            boundary = b"mock-boundary-ok\n" in err
            answer = None
            if not boundary:
                outcome = "BOUNDARY_FAILED"
            elif timed_out:
                outcome = "TIMED_OUT"
            elif max(len(raw), len(err)) > OUTPUT_LIMIT:
                outcome = "OUTPUT_CAP"
            elif child.returncode:
                outcome = "CLI_ERROR"
            else:
                try:
                    answer = verify_result(raw)
                    outcome = "PASS"
                except (ValueError, RecursionError):
                    outcome = "INVALID_ORACLE"
            receipt = {"case": case, "outcome": outcome, "oracle": answer, "boundary": boundary,
                       "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                       "input_sha256": hashlib.sha256(RECORDS).hexdigest(),
                       "elapsed_ms": round((time.monotonic() - started) * 1000), "exit": child.returncode,
                       "captured_bytes": len(raw) + len(err), "model_requests": 0, "incremental_vnd": 0,
                       "child_reaped": not Path(f"/proc/{child.pid}").exists()}
        return receipt | {"scratch_removed": not root.exists()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sandbox", type=Path)
    args = parser.parse_args()
    for case, expected in CASES.items():
        dispatch = MockDispatch(POLICY)
        receipt = dispatch.run(case, args.sandbox)
        try:
            dispatch.run(case, args.sandbox)
        except ValueError:
            replay_denied = True
        else:
            replay_denied = False
        receipt["replay_denied"] = replay_denied
        print(json.dumps(receipt))
        if (receipt["outcome"] != expected or not replay_denied or not receipt["child_reaped"]
                or not receipt["scratch_removed"]):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
