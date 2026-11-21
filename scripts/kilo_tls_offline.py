"""Issue #24 loopback-only TLS candidate. The Issue #20 live launcher does not import it."""

from contextlib import redirect_stdout
import io
import json
import os
import socket
import ssl
import tempfile
import tracemalloc
from pathlib import Path

from scripts.kilo_gate15 import Permit, json_reply
from scripts.kilo_hard_job import HardJob
from scripts.kilo_owner_gate import approved_catalog, prepare_request
from scripts.kilo_sse_stream import inspect_response, require_offline_network

TLS_SECONDS = 1.5
PIPELINE_SECONDS = 52


def require_loopback():
    require_offline_network()
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    if int(status["CapEff"], 16) or int(status["CapBnd"], 16) or int(status["NoNewPrivs"]) != 1:
        raise ValueError("drop outer namespace capabilities before running the fixture")
    ipv6 = Path("/proc/net/ipv6_route").read_text().splitlines()
    for line in ipv6:
        dest, prefix, _, _, _, _, _, _, flags, interface = line.split()
        if int(flags, 16) & 1 and (interface != "lo" or (int(prefix, 16), int(dest, 16)) != (128, 1)):
            raise ValueError("unexpected IPv6 route in offline namespace")


def rejected(classification):
    return json_reply(502) | {"protocol": {"classification": classification, "relay_bytes": 0}}


def tls_reply(port, trust, request):
    require_loopback()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if trust is not None:
        context.load_verify_locations(cafile=trust)
    try:
        # A numeric IPv4 address avoids DNS and any host override. Verify the fixed test identity.
        with socket.socket(socket.AF_INET) as raw:
            raw.connect(("127.0.0.1", port))
            with context.wrap_socket(raw, server_hostname="localhost") as tls:
                headers = {"Host": "localhost", "Content-Length": str(len(request.body)),
                           "Connection": "close"} | dict(request.headers)
                lines = [f"{request.method} {request.path} HTTP/1.1"]
                lines.extend(f"{key}: {value}" for key, value in headers.items())
                tls.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + request.body)
                with tls.makefile("rb") as reply:
                    tracemalloc.start()
                    try:
                        answer = inspect_response(reply)
                        answer["parser_peak_bytes"] = tracemalloc.get_traced_memory()[1]
                        return answer
                    finally:
                        tracemalloc.stop()
    except ssl.SSLCertVerificationError:
        return rejected("tls_certificate")
    except ssl.SSLError:
        return rejected("tls_protocol")
    except OSError:
        return rejected("tls_io")


class LocalTLSExchange:
    """One synthetic POST to a private loopback peer. No live endpoint or credentials."""

    def __init__(self, catalog, body, port, trust, *, scratch=None):
        require_loopback()
        if not approved_catalog(catalog) or type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("local TLS fixture and free catalog required")
        self.request = prepare_request(body)
        self.permit = Permit()
        self.attempts = 0
        self.receipt = None
        self.scratch = scratch
        self.worker = HardJob(lambda: tls_reply(port, trust, self.request))

    def __call__(self, body):
        if prepare_request(body) != self.request or not self.permit.take():
            raise ValueError("local TLS exchange already consumed")
        self.attempts += 1
        receipt = self.worker.run(TLS_SECONDS)
        answer = receipt.pop("result", None)
        self.receipt = receipt
        return (answer or rejected(receipt["outcome"])) | {"worker": receipt}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.worker.close()


def run_local_candidate(archive, sandbox, catalog, request_body, port, trust):
    """Bound the entire offline pipeline, including Kilo and the Unix bridge."""
    from scripts.kilo_gate15 import run

    require_loopback()
    with tempfile.TemporaryDirectory(prefix="issue24-candidate-", dir="/tmp") as scratch:
        def pipeline():
            log = io.StringIO()
            with LocalTLSExchange(catalog, request_body, port, trust, scratch=scratch) as exchange:
                with redirect_stdout(log):
                    code = run(archive, "tls-mock", sandbox=sandbox, exchange=exchange)
                return {"code": code, "evidence": json.loads(log.getvalue()), "attempts": exchange.attempts}

        with HardJob(pipeline) as supervisor:
            return supervisor.run(PIPELINE_SECONDS)


if __name__ == "__main__":
    raise SystemExit("OFFLINE_FIXTURE_ONLY")
