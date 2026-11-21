"""Manually qualify one Kilo Free task from a verified Linux release archive."""

import errno
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import signal
import socket
import socketserver
import subprocess
import sys
import tarfile
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "recursive/flint-v1.0:free"
PROMPT = "Classify the synthetic records catalog, handoff, catalog. Return only JSON with integer fields catalog, handoff, total."
EXPECTED = {"catalog": 2, "handoff": 1, "total": 3}
RELEASE_SHA = "ab7a008a2c0ca6e035b96cd1dc5712a8466a14a45992291a8f0b4b549b94136e"
HOST = "ai-gateway.kilo.ai"
ENDPOINT = "/api/v1/chat/completions"
MAX_BYTES = 32768


class Permit:
    def __init__(self):
        self.used = False
        self.lock = threading.Lock()

    def take(self):
        with self.lock:
            if self.used:
                return False
            self.used = True
            return True


def approved_payload(body, authorization, system):
    messages = body.get("messages", [])
    users = [m.get("content") for m in messages if m.get("role") == "user"]
    if len(users) == 1 and isinstance(users[0], list):
        parts = users[0]
        if not parts or any(p.get("type") != "text" for p in parts):
            return None
        if any(not str(p.get("text", "")).lstrip().startswith("<environment_details>")
               for p in parts[1:]):
            return None
        users = [parts[0].get("text")]
    if (authorization not in (None, "Bearer anonymous") or body.get("model") != MODEL
            or body.get("stream") is not True or body.get("tools")
            or users not in ([PROMPT], [json.dumps(PROMPT)])
            or any(m.get("role") not in ("system", "user") for m in messages)
            or not system.lower().startswith(("you are kilo", "kilo"))):
        return None
    return {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "stream": True, "max_tokens": 128, "stream_options": {"include_usage": True}}


def json_reply(status, payload=None):
    return {"status": status, "content_type": "text/event-stream" if status == 200 else "application/json",
            "payload": payload if payload is not None else '{"error":{"message":"one-shot gate closed"}}'}


def relay_response(status, content_type, raw):
    # Legacy HTTP-200 path extracted unchanged so the offline replay can exercise it.
    if status == 200 and len(raw) <= MAX_BYTES:
        return json_reply(200, raw.decode())
    return json_reply(502)


class Bridge(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != "/chat/completions" or not 0 < length <= MAX_BYTES:
                self.send_error(403)
                return
            req = {"body": json.loads(self.rfile.read(length)), "auth": self.headers.get("Authorization")}
            with socket.socket(socket.AF_UNIX) as conn:
                conn.settimeout(28)
                conn.connect("/gate/relay.sock")
                conn.sendall(json.dumps(req).encode() + b"\n")
                answer = json.loads(conn.makefile("rb").readline(MAX_BYTES * 4))
            payload = answer["payload"].encode()
            self.send_response(answer["status"])
            self.send_header("Content-Type", answer["content_type"])
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (ValueError, OSError, KeyError):
            self.send_error(502)


def check_boundary():
    for path in ("/mnt", "/init", "/run/WSL", "/root/.gitconfig", "/home", "/usr/local", "/usr/lib/wsl"):
        if Path(path).exists():
            raise RuntimeError("unexpected host path")
    if any(key in os.environ for key in ("GH_TOKEN", "GITHUB_TOKEN", "KILO_API_KEY", "WSL_INTEROP")):
        raise RuntimeError("ambient credentials or WSL interop")
    interfaces = {line.split(":")[0].strip() for line in
                  Path("/proc/net/dev").read_text().splitlines()[2:] if ":" in line}
    if interfaces != {"lo"} or str(Path("/proc/self/ns/net").stat().st_ino) == os.environ["GATE_HOST_NETNS"]:
        raise RuntimeError("network namespace not isolated")
    try:
        Path("/gate/work/denied").touch()
    except OSError:
        pass
    else:
        raise RuntimeError("work directory is writable")
    for family, kind in ((socket.AF_VSOCK, socket.SOCK_STREAM), (socket.AF_PACKET, socket.SOCK_RAW)):
        try:
            with socket.socket(family, kind):
                raise RuntimeError("unapproved socket family")
        except OSError as exc:
            if exc.errno != errno.EPERM:
                raise
    try:
        with socket.create_connection(("203.0.113.1", 443), timeout=1):
            raise RuntimeError("sandbox has external egress")
    except OSError:
        pass


def inner(hang, mock):
    check_boundary()
    print('{"boundary_check":true}', flush=True)
    if hang:
        threading.Event().wait()
        return
    with ThreadingHTTPServer(("127.0.0.1", 18746), Bridge) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            code = subprocess.run(
                ["/gate/kilo", "run", "--pure", "--format", "json", "--model", "kilo/" + MODEL, PROMPT],
                timeout=40).returncode
            if mock and code == 0:
                dupe = http.client.HTTPConnection("127.0.0.1", 18746, timeout=5)
                try:
                    dupe.request("POST", "/chat/completions", json.dumps({
                        "model": MODEL, "stream": True, "messages": [
                            {"role":"system", "content":"You are Kilo, a CLI coding assistant."},
                            {"role":"user", "content":PROMPT},
                        ]}), {"Content-Type":"application/json"})
                    response = dupe.getresponse()
                    if response.status != 403:
                        raise RuntimeError("duplicate admitted")
                    print('{"duplicate_denied":true}', flush=True)
                finally:
                    dupe.close()
            raise SystemExit(code)
        finally:
            server.shutdown()


def emit_filter(file):
    # Linux x86-64 classic BPF. Deny non-loopback transport families at syscall entry.
    # AF_UNIX supplies the single private bridge socket; INET/INET6 stay in the private netns.
    import struct
    instructions = [
        (0x20, 0, 0, 4), (0x15, 1, 0, 0xC000003E), (0x06, 0, 0, 0x80000000),
        (0x20, 0, 0, 0), (0x45, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000),
        (0x15, 0, 1, 425), (0x06, 0, 0, 0x00050001),
        (0x15, 2, 0, 41), (0x15, 1, 0, 53), (0x06, 0, 0, 0x7FFF0000),
        (0x20, 0, 0, 16), (0x15, 3, 0, 1), (0x15, 2, 0, 2), (0x15, 1, 0, 10),
        (0x06, 0, 0, 0x00050001), (0x06, 0, 0, 0x7FFF0000),
    ]
    file.write(b"".join(struct.pack("HBBI", *item) for item in instructions))
    file.flush()
    file.seek(0)


def confirm_free_listing():
    from decimal import Decimal, InvalidOperation

    conn = http.client.HTTPSConnection(HOST, timeout=8)
    try:
        conn.request("GET", "/api/v1/models", headers={"Accept":"application/json"})
        response = conn.getresponse()
        limit = 2 * 1024 * 1024
        data = response.read(limit + 1)
        if response.status != 200 or len(data) > limit:
            return False
        matches = [m for m in json.loads(data)["data"] if m.get("id") == MODEL]
        if len(matches) != 1 or not MODEL.endswith(":free"):
            return False
        prices = matches[0]["pricing"]
        return all(key in prices for key in ("prompt", "completion")) and all(
            Decimal(str(value)) == 0 for key, value in prices.items() if key != "discount")
    except (KeyError, TypeError, ValueError, OSError, http.client.HTTPException, InvalidOperation):
        return False
    finally:
        conn.close()


def run(archive, mode, fixture=None):
    if os.uname().machine != "x86_64":
        raise SystemExit("Requires x86-64 Linux")
    with archive.open("rb") as file:
        archive_bytes = file.read(128 * 1024 * 1024 + 1)
    if len(archive_bytes) > 128 * 1024 * 1024 or hashlib.sha256(archive_bytes).hexdigest() != RELEASE_SHA:
        raise SystemExit("Release archive hash mismatch")
    if mode == "live":
        if not confirm_free_listing():
            raise SystemExit("Free catalog verification failed; no attempt reserved")
        import pwd
        marker = Path(pwd.getpwuid(os.geteuid()).pw_dir) / ".aichatbot-gate15-kilo-issue8-attempt"
        with marker.open("x", encoding="utf-8") as file:
            file.write("Issue #8 Kilo attempt reserved\n")
    stats = dict(forwarded=0, denied=0, admitted=0, result=None, http_status=None)
    permit = Permit()
    evidence = []
    upstream_done = threading.Event()

    class Relay(socketserver.StreamRequestHandler):
        def handle(self):
            answer = json_reply(403)
            try:
                self.request.settimeout(4)
                req = json.loads(self.rfile.readline(MAX_BYTES * 4))
                body = req["body"]
                system = next((m.get("content") or "" for m in body.get("messages", [])
                               if m.get("role") == "system"), "")
                payload = approved_payload(body, req.get("auth"), str(system))
                if payload is None or not permit.take():
                    stats["denied"] += 1
                    if mode == "mock":
                        evidence.append({"system_prefix": str(system)[:90], "model_matches":body.get("model") == MODEL,
                                         "tools_present":bool(body.get("tools")), "auth_present":req.get("auth") is not None,
                                         "auth_length":len(req.get("auth") or ""),
                                         "public_placeholder":req.get("auth") == "Bearer anonymous",
                                         "undefined_placeholder":req.get("auth") == "Bearer undefined",
                                         "stream":body.get("stream") is True})
                else:
                    stats["admitted"] += 1
                    if mode == "live":
                        conn = http.client.HTTPSConnection(HOST, timeout=20)
                        try:
                            stats["forwarded"] += 1
                            conn.request("POST", ENDPOINT, json.dumps(payload), {"Content-Type":"application/json"})
                            response = conn.getresponse()
                            stats["http_status"] = response.status
                            retry_after = response.getheader("Retry-After", "")
                            if retry_after.isascii() and retry_after.isdecimal() and len(retry_after) <= 8:
                                stats["retry_after_seconds"] = int(retry_after)
                            raw = response.read(MAX_BYTES + 1)
                            if response.status == 200 and len(raw) <= MAX_BYTES:
                                for line in raw.splitlines():
                                    if line.startswith(b"data: {"):
                                        event = json.loads(line[6:])
                                        usage = event.get("usage")
                                        if isinstance(usage, dict):
                                            stats["usage"] = {k:v for k,v in usage.items()
                                                if k in ("prompt_tokens","completion_tokens","total_tokens")
                                                and type(v) is int and v >= 0}
                                answer = relay_response(response.status, response.getheader("Content-Type"), raw)
                            else:
                                answer = json_reply(502)
                        finally:
                            conn.close()
                            upstream_done.set()
                    elif fixture is not None:
                        answer = relay_response(*fixture)
                    else:
                        event = {"id":"mock","object":"chat.completion.chunk","created":1,"model":MODEL,
                                 "choices":[{"index":0,"delta":{"content":json.dumps(EXPECTED)},"finish_reason":"stop"}]}
                        answer = json_reply(200, "data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n")
            except (AttributeError, ValueError, OSError, KeyError, http.client.HTTPException):
                answer = json_reply(502)
            self.wfile.write(json.dumps(answer).encode() + b"\n")

    with tempfile.TemporaryDirectory(prefix="gate15-kilo-", dir="/tmp") as tmp, tempfile.TemporaryFile(dir="/tmp") as bpf:
        folder = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
            member = tar.getmember("kilo")
            if not member.isfile() or not 0 < member.size <= 256 * 1024 * 1024:
                raise SystemExit("Unexpected release member")
            binary = tar.extractfile(member).read()
            if binary[:4] != b"\x7fELF":
                raise SystemExit("Release member is not ELF")
        (folder / "kilo").write_bytes(binary)
        (folder / "kilo").chmod(0o500)
        (folder / "probe.py").write_bytes(Path(__file__).read_bytes())
        config = {"enabled_providers":["kilo"], "model":"kilo/"+MODEL, "small_model":"kilo/"+MODEL,
                  "permission":"deny", "autoupdate":False, "mcp":{}, "plugin":[],
                  "provider":{"kilo":{"name":"Kilo","npm":"@ai-sdk/openai-compatible",
                    "options":{"baseURL":"http://127.0.0.1:18746"},
                    "models":{MODEL:{"name":"Flint Free","cost":{"input":0,"output":0},
                                     "limit":{"context":8192,"output":128}}}}}}
        (folder / "config.json").write_text(json.dumps(config))
        (folder / "work").mkdir()
        emit_filter(bpf)
        with socketserver.ThreadingUnixStreamServer(str(folder / "relay.sock"), Relay) as relay:
            relay.daemon_threads = True
            threading.Thread(target=relay.serve_forever, daemon=True).start()
            args = ["/usr/bin/bwrap","--unshare-all","--unshare-user","--disable-userns","--die-with-parent","--new-session","--clearenv",
                    "--cap-drop","ALL","--seccomp",str(bpf.fileno()),
                    "--ro-bind","/usr/bin/python3","/usr/bin/python3",
                    "--ro-bind","/usr/lib/python3.12","/usr/lib/python3.12",
                    "--ro-bind","/usr/lib/x86_64-linux-gnu","/usr/lib/x86_64-linux-gnu",
                    "--ro-bind","/usr/lib64","/usr/lib64","--symlink","usr/lib","/lib","--symlink","usr/lib64","/lib64",
                    "--proc","/proc","--dev","/dev","--tmpfs","/tmp",
                    "--ro-bind",tmp,"/gate","--chdir","/gate/work",
                    "--setenv","PATH","/usr/bin:/bin","--setenv","HOME","/tmp",
                    "--setenv","GATE_HOST_NETNS",str(Path("/proc/self/ns/net").stat().st_ino),
                    "--setenv","KILO_CONFIG","/gate/config.json",
                    "--setenv","OPENCODE_CONFIG","/gate/config.json",
                    "--setenv","OPENCODE_DISABLE_AUTOUPDATE","1",
                    "--setenv","OPENCODE_DISABLE_MODELS_FETCH","1",
                    "--setenv","OPENCODE_DISABLE_SHARE","1","/usr/bin/python3","/gate/probe.py",
                    {"timeout":"--hang", "mock":"--mock-inner", "live":"--inner"}[mode]]
            proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    pass_fds=(bpf.fileno(),), start_new_session=True)
            buffers = [bytearray(), bytearray()]

            def kill_group():
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            def drain(pipe, buffer):
                with pipe:
                    while block := pipe.read1(4096):
                        if len(buffer) + len(block) > 128 * 1024:
                            stats["output_cap"] = True
                            kill_group()
                            return
                        buffer.extend(block)

            readers = [threading.Thread(target=drain, args=(pipe, buffer), daemon=True)
                       for pipe, buffer in zip((proc.stdout, proc.stderr), buffers)]
            for reader in readers:
                reader.start()
            try:
                proc.wait(timeout=3 if mode == "timeout" else 45)
                stats["exit"] = proc.returncode
            except subprocess.TimeoutExpired:
                kill_group()
                proc.wait(timeout=5)
                stats["timeout"] = True
                stats["exit"] = proc.returncode
            finally:
                if proc.poll() is None:
                    kill_group()
                    proc.wait(timeout=5)
                for reader in readers:
                    reader.join(3)
                stats["streams_closed"] = not any(reader.is_alive() for reader in readers)
                relay.shutdown()
                if mode == "live":
                    stats["upstream_finished"] = bool(stats["admitted"] and upstream_done.wait(2))
        out, err = buffers
        stats["boundary_check"] = b'{"boundary_check":true}' in out
        if mode == "mock":
            stats["duplicate_denied"] = b'{"duplicate_denied":true}' in out
        answer = ""
        for line in out.splitlines():
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if data.get("type") == "text":
                answer += data.get("part", {}).get("text", "")
        try:
            value = json.loads(answer)
            stats["result"] = value == EXPECTED and all(type(v) is int for v in value.values())
        except (AttributeError, ValueError):
            stats["result"] = False
        if mode != "live":
            stats["mock_denials"] = evidence
            if not stats["boundary_check"]:
                stats["sandbox_start_error"] = bytes(err).decode(errors="replace").splitlines()[:2]
            stats["mock_errors"] = [x for x in ("Traceback","not found","Operation not permitted",
                "Permission denied","ECONNREFUSED","ProviderModelNotFound","unexpected host path",
                "ambient credentials","unapproved socket family","work directory is writable")
                if x.lower().encode() in (out + err).lower()]
    print(json.dumps(stats))
    safe = stats.get("boundary_check") and stats.get("streams_closed") and not stats.get("output_cap")
    if mode == "timeout":
        return 0 if safe and stats.get("timeout") and stats["forwarded"] == 0 and stats["exit"] == -9 else 1
    expected = (stats["forwarded"] == 0 and stats.get("duplicate_denied")) if mode == "mock" else (
        stats["forwarded"] == 1 and stats["http_status"] == 200 and stats.get("upstream_finished"))
    return 0 if safe and expected and stats["admitted"] == 1 and stats["exit"] == 0 and stats["result"] else 1


if __name__ == "__main__":
    if sys.argv[1:] in (["--inner"], ["--mock-inner"], ["--hang"]):
        inner(sys.argv[1] == "--hang", sys.argv[1] == "--mock-inner")
    elif len(sys.argv) == 3 and sys.argv[1] in ("mock", "timeout", "live"):
        raise SystemExit(run(Path(sys.argv[2]), sys.argv[1]))
    else:
        raise SystemExit("usage: kilo_gate15.py mock|timeout|live VERIFIED_RELEASE_ARCHIVE")
