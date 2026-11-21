"""Run the TLS candidate and pinned Kilo ELF within the isolated loopback profile."""

from pathlib import Path
import json
import os
import socket
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kilo_tls_fixture import EXPECTED, certificates, peer
from scripts import kilo_gate15
from scripts.kilo_activate import fixed_body
from scripts.kilo_tls_offline import require_loopback, run_local_candidate
from test_kilo_tls_offline import catalogue, live_tcp


def run_case(archive, sandbox, name, cert):
    unix_stall = name == "pipeline-unix-stall"
    expected, posts = EXPECTED["large" if unix_stall else name]
    send = kilo_gate15.send_relay_reply
    before = (len(os.listdir("/proc/self/fd")), live_tcp())
    with peer(cert, "large" if unix_stall else name) as (port, log, server):
        began = log.with_name("unix-blocked")

        def stall(connection, answer):
            if answer["status"] != 200:
                return send(connection, answer)
            # Exercise the normal reply function from the active relay handler on a kernel-full stream.
            left, right = socket.socketpair(socket.AF_UNIX)
            with left, right:
                left.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                left.setblocking(False)
                try:
                    for _ in range(128):
                        left.send(b"x" * 1024)
                except BlockingIOError:
                    left.setblocking(True)
                    began.write_text("send queue full\n")
                    return send(left, answer)
                raise RuntimeError("fixture failed to fill Unix send queue")

        trust = None if name == "untrusted" else cert / "ca.pem"
        if unix_stall:
            with patch.object(kilo_gate15, "send_relay_reply", stall):
                result = run_local_candidate(archive, sandbox, catalogue(), fixed_body(), port, trust)
        else:
            result = run_local_candidate(archive, sandbox, catalogue(), fixed_body(), port, trust)
        hits = log.read_text().splitlines() if log.exists() else []
        blocked = began.exists()

    common = (hits == ["accepted"] + ["post"] * posts and server.poll() is not None and
              (len(os.listdir("/proc/self/fd")), live_tcp()) == before)
    if unix_stall:
        print(json.dumps({"fixture": name, "synthetic_posts": posts, "real_posts": 0,
                          "unix_send_queue_full": blocked, "supervisor": result, "socket_cleanup": common}))
        return 0 if (common and blocked and result["outcome"] == "hard_timeout" and result["signal"] == 9
                     and result["reaped"] and result["elapsed_ms"] <= result["limit_ms"] + 1000) else 1

    detail = result.pop("result", None)
    if detail is None:
        print(json.dumps({"fixture": name, "supervisor": result, "socket_cleanup": common}))
        return 1
    evidence = detail["evidence"]
    print(json.dumps({"fixture": name, "synthetic_posts": hits.count("post"), "real_posts": 0,
                      "supervisor": result, "socket_cleanup": common, **evidence}))
    expected_ok = expected == "complete"
    good = (common and result["outcome"] == "complete" and result["reaped"] and detail["attempts"] == 1
            and evidence["protocol"]["classification"] == expected and evidence["forwarded"] == 0
            and evidence["streams_closed"] and evidence["boundary_check"] and evidence["auxiliary_denied"]
            and evidence["duplicate_denied"] and evidence["tls_worker"]["reaped"]
            and evidence["exit"] == int(not expected_ok) and detail["code"] == int(not expected_ok))
    if expected_ok:
        good = good and evidence["result"] and evidence["cli"]["step_finish"] == 1
    else:
        good = good and not evidence["result"] and evidence["protocol"]["relay_bytes"] == 0
    return int(not good)


def main():
    require_loopback()
    if len(sys.argv) < 4:
        raise SystemExit("usage: run_kilo_tls_offline.py ARCHIVE BWRAP CASE [CASE ...]")
    archive, sandbox = map(Path, sys.argv[1:3])
    with certificates() as cert:
        for case in sys.argv[3:]:
            if run_case(archive, sandbox, case, cert):
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
