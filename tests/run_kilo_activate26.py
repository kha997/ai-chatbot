"""Exact staged launcher tests. Only this test process can redirect a fixture socket."""

import sys


def bootstrap_fixture():
    import http.client
    from pathlib import Path
    import pwd
    import runpy
    import socket
    import ssl
    from types import SimpleNamespace
    from unittest.mock import patch

    launcher, repo, commit, archive, sandbox, home, trust, owner, catalog, post, fault = sys.argv[2:13]
    devices = Path("/proc/net/dev").read_text().splitlines()[2:]
    routes4 = Path("/proc/net/route").read_text().splitlines()[1:]
    active6 = [line.split() for line in Path("/proc/net/ipv6_route").read_text().splitlines()
               if int(line.split()[-2], 16) & 1]
    capabilities = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if ({line.split(":")[0].strip() for line in devices} != {"lo"} or routes4
            or any(row[-1] != "lo" or int(row[1], 16) != 128 or int(row[0], 16) != 1 for row in active6)
            or int(capabilities["CapEff"], 16) or int(capabilities["CapBnd"], 16)
            or int(capabilities["NoNewPrivs"]) != 1):
        raise SystemExit("test fixture requires no-egress namespace")
    account = SimpleNamespace(pw_dir=home)
    https = http.client.HTTPSConnection
    sendall = socket.socket.sendall

    class FixtureHTTPS(https):
        def __init__(self, host, port, *, context, timeout):
            if port != 443 or host not in ("ai-gateway.kilo.ai", "api.github.com"):
                raise AssertionError("unpinned hostname or port")
            if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
                raise AssertionError("TLS verification disabled")
            context.load_verify_locations(cafile=trust)
            super().__init__(host, port, context=context, timeout=timeout)
            target = int(owner if host == "api.github.com" else post if timeout is None else catalog)

            def local(address, seconds, source):
                if address != (host, 443) or source is not None or not target:
                    raise AssertionError("unexpected fixture connection")
                return socket.create_connection(("127.0.0.1", target), seconds)
            self._create_connection = local

    def fault_write(conn, data, flags=0):
        if conn.family != socket.AF_UNIX or not data.startswith(b'{"status": 200, "body":'):
            return sendall(conn, data, flags)
        left, right = socket.socketpair(socket.AF_UNIX)
        with left, right:
            left.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
            left.setblocking(False)
            try:
                for _ in range(128):
                    left.send(b"x" * 1024)
            except BlockingIOError:
                left.setblocking(True)
                (Path(home) / "unix-stalled").touch()
                return sendall(left, data, flags)
        raise AssertionError("Unix send buffer did not saturate")

    sys.argv = [launcher, "--repo", repo, "--commit", commit, "--archive", archive, "--sandbox", sandbox]
    sys.argv.extend(["--describe"] if fault == "describe" else ["--approval", "2600001"])
    with patch.object(pwd, "getpwuid", return_value=account), patch.object(http.client, "HTTPSConnection", FixtureHTTPS):
        if fault == "pipeline-unix-stall":
            with patch.object(socket.socket, "sendall", fault_write):
                runpy.run_path(launcher, run_name="__main__")
        else:
            runpy.run_path(launcher, run_name="__main__")


if __name__ == "__main__" and sys.argv[1:2] == ["--bootstrap-fixture"]:
    bootstrap_fixture()
    raise SystemExit("fixture launcher returned unexpectedly")


from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import subprocess
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kilo_tls_fixture import certificates, peer
from scripts.kilo_activate import ISSUE_URL, OWNER_ID, approval_line
from scripts.kilo_activate26 import ISSUE_URL as NEW_ISSUE
from scripts.kilo_gate15 import MODEL
from scripts.kilo_tls_offline import require_loopback
from test_kilo_tls_offline import socket_counts


def run_case(case, launcher, repo, commit, archive, sandbox, ca):
    before = socket_counts()
    scratch = set(Path("/tmp").glob("issue26-kilo-*"))
    with tempfile.TemporaryDirectory(prefix="fixture26-home-", dir="/tmp") as home:
        command = [sys.executable, "-IS", str(Path(__file__).resolve()), "--bootstrap-fixture",
                   launcher, repo, commit, archive, sandbox, home, str(ca / "ca.pem")]
        env = {"PATH": "/usr/bin:/bin"}

        def invoke(owner, catalog, post, fault):
            return subprocess.run(command + [str(port) for port in (owner, catalog, post)] + [fault],
                                  capture_output=True, text=True, timeout=85, env=env)

        describe = invoke(0, 0, 0, "describe")
        if describe.returncode or not describe.stdout.startswith("{"):
            raise RuntimeError("staged manifest failed", describe.stdout, describe.stderr)
        description = json.loads(describe.stdout)
        manifest, runner = description["manifest"], description["runner"]
        now = datetime.now(timezone.utc)
        created = (now - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        expiry = (now + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        is_old = case == "old-proof"
        owner = {"id": 2600001, "issue_url": ISSUE_URL if is_old else NEW_ISSUE, "author_association": "OWNER",
                 "user": {"id": OWNER_ID, "login": "kha997"}, "created_at": created, "updated_at": created,
                 "body": approval_line(commit, manifest, runner, expiry, scope=20 if is_old else 26)}
        price = 1 if case == "paid" else 0
        catalog = {"data": [{"id": MODEL, "pricing": {"prompt": price, "completion": 0}}]}
        payload = lambda data: json.dumps(data).encode("utf-8")
        reply_case = "large" if case in ("old-proof", "paid", "pipeline-unix-stall") else case
        with (peer(ca, "owner-meta", vendor=True, payload=payload(owner)) as owner_peer,
              peer(ca, "catalog-meta", vendor=True, payload=payload(catalog)) as catalog_peer,
              peer(ca, reply_case, vendor=True) as model_peer):
            peers = (owner_peer, catalog_peer, model_peer)
            result = invoke(*(p[0] for p in peers), case)
            if result.stderr or not result.stdout:
                raise RuntimeError("unexpected fixture stderr", result.stdout, result.stderr)
            state = Path(home) / ".aichatbot-issue26"
            spent = (state / "issue26.spent").is_file()
            claimed = (state / "issue26.post").is_file()
            post_hits = model_peer[1].read_text().splitlines() if model_peer[1].exists() else []
            meta_hits = [p[1].read_text().splitlines() if p[1].exists() else [] for p in peers[:2]]
            if spent:
                replay = invoke(*(p[0] for p in peers), case)
                assert replay.returncode == 1 and "stays spent" in replay.stdout
                assert (model_peer[1].read_text().splitlines() if model_peer[1].exists() else []) == post_hits
        assert socket_counts() == before and set(Path("/tmp").glob("issue26-kilo-*")) == scratch
        if case == "old-proof":
            assert result.returncode == 1 and not spent and not claimed and not post_hits
            assert meta_hits == [["accepted", "get"], []]
        elif case == "paid":
            assert result.returncode == 1 and spent and not claimed and not post_hits
            assert meta_hits == [["accepted", "get"], ["accepted", "get"]]
        else:
            assert spent and claimed and meta_hits == [["accepted", "get"], ["accepted", "get"]]
            posts = 0 if case == "wrong-hostname" else 1
            assert post_hits == ["accepted"] + ["post"] * posts
            receipt = json.loads(result.stdout)
            assert receipt["commit"] == commit and receipt["manifest"] == manifest
            if case == "pipeline-unix-stall":
                watchdog = receipt["pipeline_worker"]
                assert (Path(home) / "unix-stalled").exists() and watchdog["outcome"] == "hard_timeout"
                assert watchdog["signal"] == 9 and watchdog["elapsed_ms"] <= watchdog["limit_ms"] + 1000
                assert receipt["forwarded"] is None and not receipt["qualification_passed"]
            else:
                assert (receipt["boundary_check"] and receipt["streams_closed"] and receipt["duplicate_denied"]
                        and receipt["auxiliary_denied"] and receipt["pipeline_worker"]["reaped"])
                protocol = receipt["protocol"]
                expected = {"slow-valid": "complete", "stall-after-stop": "hard_timeout",
                            "slow-headers": "hard_timeout", "wrong-hostname": "tls_certificate",
                            "rate-limit": "http_status", "redirect": "http_status"}[case]
                assert protocol["classification"] == expected
                if expected == "complete":
                    assert result.returncode == 0 and receipt["qualification_passed"] and receipt["result"]
                    assert receipt["forwarded"] == 1 and protocol["bytes"] == 262144
                else:
                    assert result.returncode == 1 and not receipt["qualification_passed"] and protocol["relay_bytes"] == 0
                if expected == "hard_timeout":
                    worker = receipt["tls_worker"]
                    assert worker["signal"] == 9 and worker["reaped"] and receipt["forwarded"] is None
                    assert worker["limit_ms"] <= worker["elapsed_ms"] <= worker["limit_ms"] + 1000
                if case in ("rate-limit", "redirect"):
                    assert receipt["forwarded"] == 1 and protocol["http_status"] == (429 if case == "rate-limit" else 302)
            print(json.dumps({"case": case, "synthetic_posts": posts, "external_posts": 0, "cleanup": True,
                              "replay_denied": True, "receipt": receipt}))
            return
        print(json.dumps({"case": case, "synthetic_posts": 0, "external_posts": 0, "reserved": spent,
                          "post_claimed": claimed, "cleanup": True}))


if __name__ == "__main__":
    require_loopback()
    if not sys.flags.optimize and len(sys.argv) >= 7:
        with certificates(vendor=True) as cert:
            for name in sys.argv[6:]:
                run_case(name, *sys.argv[1:6], cert)
    else:
        raise SystemExit("usage: run_kilo_activate26.py LAUNCHER REPO SHA ARCHIVE BWRAP CASE [...]")
