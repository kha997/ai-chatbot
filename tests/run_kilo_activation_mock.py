"""Exercise the authorized orchestration with a synthetic worker in a no-network namespace."""

from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import kilo_activate as gate
from scripts.kilo_gate15 import run
from test_kilo_sse import SSE, VALID, JSON_ERROR


def main(archive, sandbox, case):
    # The outer namespace is required even though the transport is replaced with a fixture.
    device = Path("/proc/net/dev").read_text().splitlines()[2:]
    interfaces = {line.split(":")[0].strip() for line in device if ":" in line}
    if interfaces != {"lo"} or Path("/proc/net/route").read_text().splitlines()[1:]:
        raise SystemExit("outer offline network namespace required")
    expected = case == "valid"
    responses = {
        "valid": (200, SSE, VALID, None),
        "429": (429, "application/json", b"{}", None),
        "json_error": (200, "application/json", JSON_ERROR, None),
        "wrong_model": (200, SSE, VALID.replace(gate.MODEL.encode(), b"different/model:free"), None),
    }

    def fake_network(kind, comment_id, proof):
        if kind != "post" or not proof.claim():
            raise AssertionError("synthetic POST proof missing or reused")
        return 1, responses[case]

    def utc(value):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    with tempfile.TemporaryDirectory(prefix="issue20-mock-", dir="/tmp") as temp:
        state = Path(temp) / "isolated-synthetic-state"
        commit, manifest, comment_id = "1" * 40, "2" * 64, 999
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=2)
        created = utc(now - timedelta(seconds=2))
        record = {"id": comment_id, "issue_url": gate.ISSUE_URL, "author_association": "OWNER",
                  "user": {"id": gate.OWNER_ID, "login": "kha997"},
                  "created_at": created, "updated_at": created,
                  }
        with gate.lease(state) as grant:
            runner = gate.runner_binding(grant, create=True)
            record["body"] = gate.approval_line(commit, manifest, runner, utc(expires))
            gate.reserve(grant, commit, manifest, comment_id)
            proof = gate.PostProof(grant, record, comment_id, commit, manifest, runner)
            captured = io.StringIO()
            with patch.object(gate, "network", side_effect=fake_network):
                with gate.Worker("post", proof=proof) as worker:
                    exchange = gate.AuthorizedExchange(grant, worker, expires)
                    with redirect_stdout(captured):
                        code = run(archive, "authorized", sandbox=sandbox, exchange=exchange)
            evidence = json.loads(captured.getvalue())
            evidence["worker_closed"] = not worker.process.is_alive()
            evidence["case"] = case
            evidence["simulated_posts"] = evidence.pop("forwarded")
            evidence["real_posts"] = 0
        try:
            with gate.lease(state):
                raise AssertionError("replay accepted after worker exit")
        except ValueError:
            evidence["durable_replay_denied"] = True
        print(json.dumps(evidence))
    safe = (evidence["boundary_check"] and evidence["streams_closed"] and evidence["worker_closed"]
            and evidence["simulated_posts"] == 1 and evidence["admitted"] == 1
            and evidence["auxiliary_denied"] and evidence["duplicate_denied"]
            and evidence["durable_replay_denied"] and not evidence.get("output_cap"))
    if expected:
        return 0 if safe and code == 0 and evidence["result"] and evidence["exit"] == 0 else 1
    return 0 if safe and code == 1 and not evidence["result"] and evidence["exit"] == 1 and evidence["cli"]["error"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[3] not in ("valid", "429", "json_error", "wrong_model"):
        raise SystemExit("usage: run_kilo_activation_mock.py ARCHIVE BWRAP FIXTURE")
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
