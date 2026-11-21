"""Run one named fixture against the real Kilo ELF in the offline sandbox."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_gate15 import run
from test_kilo_sse import FIXTURES


def main(archive, name):
    media, raw, expected = FIXTURES[name]
    output = io.StringIO()
    with redirect_stdout(output):
        code = run(archive, "mock", (200, media, raw))
    evidence = json.loads(output.getvalue())
    evidence.update(fixture=name, fixture_sha256=hashlib.sha256(raw).hexdigest(), wrapper_exit=code)
    print(json.dumps(evidence))
    safe = (evidence.get("boundary_check") and evidence.get("streams_closed") and
            not evidence.get("timeout") and not evidence.get("output_cap") and
            evidence.get("forwarded") == 0 and evidence.get("admitted") == 1 and
            evidence.get("denied", 0) >= 2 and evidence.get("auxiliary_denied") and
            evidence.get("duplicate_denied") and evidence.get("relay_status") == expected)
    if expected == 200:
        return 0 if safe and code == 0 and evidence["exit"] == 0 and evidence["result"] else 1
    return 0 if safe and code == 1 and evidence["exit"] == 1 and not evidence["result"] else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), sys.argv[2]))
