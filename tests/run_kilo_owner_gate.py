"""Exercise the frozen one-POST contract against local fixtures and pinned Bubblewrap."""

from contextlib import redirect_stdout
from functools import partial
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_gate15 import MAX_BYTES, MODEL, run
from scripts.kilo_owner_gate import FixtureReply, OfflineExchange, stage_sandbox
from test_kilo_sse import FIXTURES, SSE, VALID


def main(archive, sandbox, name):
    stage = partial(stage_sandbox, sandbox)
    if name == "timeout":
        return run(archive, "timeout", sandbox_stage=stage)
    if name == "response_cap":
        media, raw, expected = SSE, b":" * (MAX_BYTES + 1), 502
    elif name == "encoding":
        media, raw, expected = SSE, VALID, 502
    else:
        media, raw, expected = FIXTURES[name]
    fixture = FixtureReply(200, media, raw, "gzip" if name == "encoding" else None)
    exchange = OfflineExchange({"data": [{"id": MODEL, "pricing": {
        "prompt": "0", "completion": "0",
    }}]}, fixture)
    output = io.StringIO()
    with redirect_stdout(output):
        code = run(archive, "mock", sandbox_stage=stage, exchange=exchange)
    result = json.loads(output.getvalue())
    result.update(fixture=name, fixture_sha256=hashlib.sha256(raw).hexdigest(),
                  simulated_posts=exchange.attempts, wrapper_exit=code)
    print(json.dumps(result))
    safe = (result.get("boundary_check") and result.get("streams_closed")
            and not result.get("timeout") and not result.get("output_cap")
            and result["simulated_posts"] == 1 and result.get("forwarded") == 0
            and result.get("admitted") == 1 and result.get("denied", 0) >= 2
            and result.get("auxiliary_denied") and result.get("duplicate_denied")
            and result.get("relay_status") == expected)
    if expected == 200:
        return 0 if safe and code == result["exit"] == 0 and result["result"] else 1
    return 0 if safe and code == result["exit"] == 1 and result["cli"]["error"] >= 1 and not result["result"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in (*FIXTURES, "timeout", "response_cap", "encoding"):
        raise SystemExit("usage: run_kilo_owner_gate.py ARCHIVE REVIEWED_BWRAP FIXTURE")
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
