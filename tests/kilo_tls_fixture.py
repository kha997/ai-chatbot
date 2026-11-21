"""Private CA and one-accept loopback TLS peer for Issue #24 tests."""

from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_activate import fixed_body
from scripts.kilo_owner_gate import prepare_request
from scripts.kilo_tls_offline import require_loopback
from test_kilo_sse import DELTAS, JSON_ERROR, VALID, SSE, event, stream
from test_kilo_sse_stream import http_wire, large_sse

FAULT_SECONDS = 7
EXPECTED = {
    "large": ("complete", 1), "drip": ("complete", 1), "hold-open": ("complete", 1),
    "oversize": ("response_cap", 1), "oversized-frame": ("frame_cap", 1),
    "oversize-chunked": ("response_cap", 1),
    "wrong-media": ("unexpected_media", 1), "gzip": ("unsupported_encoding", 1),
    "embedded-error": ("embedded_error", 1), "wrong-model": ("model_mismatch", 1),
    "truncated-done": ("truncated_event", 1), "closed-mid-http": ("invalid_http_framing", 1),
    "stall-handshake": ("hard_timeout", 0), "stall-before-headers": ("hard_timeout", 1),
    "slow-headers": ("hard_timeout", 1), "stall-between-chunks": ("hard_timeout", 1),
    "stall-after-stop": ("hard_timeout", 1), "wrong-hostname": ("tls_certificate", 0),
    "untrusted": ("tls_certificate", 0), "invalid-tls": ("tls_protocol", 0),
}


def openssl(*args, cwd):
    subprocess.run(["/usr/bin/openssl", *args], cwd=cwd, check=True, timeout=15, env={},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@contextmanager
def certificates():
    require_loopback()
    with tempfile.TemporaryDirectory(prefix="issue24-ca-", dir="/tmp") as scratch:
        root = Path(scratch)
        openssl("req", "-new", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                "-subj", "/CN=Issue 24 ephemeral test root", "-keyout", "ca.key", "-out", "ca.pem",
                "-addext", "basicConstraints=critical,CA:TRUE", cwd=root)
        for name, serial in (("localhost", "2"), ("wrong.invalid", "3")):
            openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", f"/CN={name}",
                    "-keyout", name + ".key", "-out", name + ".csr", cwd=root)
            ext = root / (name + ".ext")
            ext.write_text(f"subjectAltName=DNS:{name}\nextendedKeyUsage=serverAuth\n")
            openssl("x509", "-req", "-in", name + ".csr", "-CA", "ca.pem", "-CAkey", "ca.key",
                    "-set_serial", serial, "-days", "1", "-extfile", ext.name, "-out", name + ".pem", cwd=root)
        yield root


@contextmanager
def peer(root, case):
    require_loopback()
    with tempfile.TemporaryDirectory(prefix="issue24-peer-", dir="/tmp") as base:
        log = Path(base) / "hits"
        with socket.socket(socket.AF_INET) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve", str(listener.fileno()),
                 str(root), str(log), case, str(os.getpid())],
                pass_fds=(listener.fileno(),), start_new_session=True, env={},
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            yield port, log, process
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)


def verify_post(conn):
    request = prepare_request(fixed_body())
    with conn.makefile("rb") as wire:
        if wire.readline(1024) != b"POST /api/v1/chat/completions HTTP/1.1\r\n":
            raise ValueError("unexpected local request")
        received = {}
        for _ in range(12):
            line = wire.readline(1024)
            if line == b"\r\n":
                break
            key, value = line.decode("ascii").removesuffix("\r\n").split(": ", 1)
            if key in received:
                raise ValueError("duplicate header")
            received[key] = value
        else:
            raise ValueError("undelimited headers")
        expected = {"Host": "localhost", "Content-Length": str(len(request.body)),
                    "Connection": "close"} | dict(request.headers)
        if received != expected or wire.read(len(request.body)) != request.body:
            raise ValueError("unexpected synthetic request envelope")


def response_for(case):
    if case in ("large", "hold-open"):
        return http_wire(large_sse(262144), chunk_size=997)
    if case == "drip":
        return http_wire(large_sse(32769), chunk_size=137)
    if case == "oversize":
        return http_wire(large_sse(262145))
    if case == "oversize-chunked":
        return http_wire(large_sse(262145), chunk_size=997)
    if case == "oversized-frame":
        return http_wire(stream(event("x" * 8192)) + large_sse(65536))
    if case == "wrong-media":
        return http_wire(VALID, "text/plain")
    if case == "gzip":
        return http_wire(VALID, extra=b"Content-Encoding: gzip\r\n")
    if case == "embedded-error":
        return http_wire(JSON_ERROR, "application/json")
    if case == "wrong-model":
        return http_wire(VALID.replace(b"recursive/flint-v1.0:free", b"other/model:free"))
    if case == "truncated-done":
        return http_wire(VALID[:-3])
    if case == "closed-mid-http":
        return http_wire(large_sse(65536), chunk_size=997)[:-300]
    raise ValueError("unknown response fixture")


def send_response(conn, case):
    if case == "stall-before-headers":
        time.sleep(FAULT_SECONDS)
    elif case == "slow-headers":
        for byte in b"HTTP/1.1 200 Fixture\r\nContent-Type: ":
            conn.sendall(bytes([byte]))
            time.sleep(0.15)
    elif case in ("stall-between-chunks", "stall-after-stop"):
        part = stream(*DELTAS) if case == "stall-after-stop" else stream(DELTAS[0])
        wire = http_wire(part, chunk_size=len(part))
        conn.sendall(wire[:-5])  # withhold HTTP terminal chunk and remaining SSE
        time.sleep(FAULT_SECONDS)
    else:
        wire = response_for(case)
        if case == "drip":
            for offset in range(0, len(wire), 1500):
                conn.sendall(wire[offset:offset + 1500])
                time.sleep(0.009)
        else:
            conn.sendall(wire)
        if case == "hold-open":
            time.sleep(FAULT_SECONDS)


def serve(fd, root, log, case, parent):
    require_loopback()
    if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid() != parent:
        return 2
    with socket.socket(fileno=fd) as listener:
        raw, _ = listener.accept()
    log.write_text("accepted\n")
    with raw:
        if case == "stall-handshake":
            time.sleep(FAULT_SECONDS)
            return 0
        if case == "invalid-tls":
            raw.sendall(b"HTTP/1.0 400 Not TLS\r\n\r\n")
            return 0
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        name = "wrong.invalid" if case == "wrong-hostname" else "localhost"
        context.load_cert_chain(root / (name + ".pem"), root / (name + ".key"))
        try:
            with context.wrap_socket(raw, server_side=True) as conn:
                verify_post(conn)
                with log.open("a") as file:
                    file.write("post\n")
                send_response(conn, case)
        except (ssl.SSLError, BrokenPipeError, ConnectionResetError):
            pass
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 7 and sys.argv[1] == "--serve":
        raise SystemExit(serve(int(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]),
                               sys.argv[5], int(sys.argv[6])))
    raise SystemExit("fixture server is launched only by the offline harness")
