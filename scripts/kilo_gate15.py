"""Replay synthetic Kilo HTTP responses offline in a verified Linux sandbox."""

import base64
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
MAX_BYTES = 32768
MAX_RELAY_FRAME = 4 * ((MAX_BYTES + 2) // 3) + 128


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


def reply_frame(answer):
    body = base64.b64encode(answer["payload"].encode("utf-8")).decode("ascii")
    return json.dumps({"status": answer["status"], "body": body}).encode("ascii") + b"\n"


def decode_reply_frame(frame):
    if len(frame) > MAX_RELAY_FRAME or not frame.endswith(b"\n"):
        raise ValueError("incomplete relay frame")
    reply = json.loads(frame)
    if not isinstance(reply, dict) or reply.get("status") not in (200, 403, 502):
        raise ValueError("unsupported relay status")
    encoded = reply.get("body")
    if not isinstance(encoded, str):
        raise ValueError("invalid relay body")
    payload = base64.b64decode(encoded, validate=True)
    if len(payload) > MAX_BYTES:
        raise ValueError("relay body exceeds cap")
    status = reply["status"]
    content_type = "text/event-stream" if status == 200 else "application/json"
    return status, content_type, payload


def sse_events(text):
    # Split only on SSE line endings. Unicode line separators are valid JSON text.
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    data, kind = [], "message"
    for line in lines:
        if not line:
            if data:
                yield kind, "\n".join(data)
            data, kind = [], "message"
        elif not line.startswith(":"):
            field, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if field == "data":
                data.append(value)
            elif field == "event":
                kind = value or "message"
            elif field not in ("id", "retry"):
                # Intentionally strict for this fixed OpenAI-compatible route.
                raise ValueError("unframed_data")
    if data:
        raise ValueError("truncated_event")


def relay_response(status, content_type, raw, content_encoding=None):
    media = (content_type or "").split(";", 1)[0].strip().lower()
    info = {"http_status": status, "media": (
        "sse" if media == "text/event-stream" else "json" if media == "application/json" else "other"
    ), "encoding": "identity" if content_encoding in (None, "", "identity") else "unsupported",
            "bytes": len(raw), "events": 0, "text_deltas": 0, "done": False,
            "finish": "absent", "usage_present": False}

    def reject(reason):
        return json_reply(502) | {"protocol": info | {"classification": reason}}

    if status != 200:
        return reject("http_status")
    if len(raw) > MAX_BYTES:
        return reject("response_cap")
    if info["encoding"] != "identity":
        return reject("unsupported_encoding")
    if info["media"] == "json":
        try:
            body = json.loads(raw)
            if isinstance(body, dict) and body.get("error") is not None:
                return reject("embedded_error")
        except (ValueError, UnicodeError):
            return reject("malformed_json")
    if info["media"] != "sse":
        return reject("unexpected_media")
    try:
        text = raw.decode("utf-8")
        for kind, data in sse_events(text):
            info["events"] += 1
            if info["done"]:
                return reject("data_after_done")
            if kind == "error":
                return reject("embedded_error")
            if data == "[DONE]":
                info["done"] = True
                continue
            event = json.loads(data)
            if not isinstance(event, dict):
                return reject("invalid_event")
            if event.get("error") is not None:
                return reject("embedded_error")
            info["usage_present"] |= isinstance(event.get("usage"), dict)
            choices = event.get("choices")
            if not isinstance(choices, list) or len(choices) > 1:
                return reject("invalid_choices")
            for choice in choices:
                if not isinstance(choice, dict) or choice.get("index", 0) != 0 or info["finish"] != "absent":
                    return reject("invalid_choices")
                delta = choice.get("delta") or {}
                if not isinstance(delta, dict) or delta.get("tool_calls") or delta.get("function_call"):
                    return reject("unexpected_delta")
                content = delta.get("content")
                if content is not None and not isinstance(content, str):
                    return reject("unexpected_delta")
                info["text_deltas"] += bool(content)
                finish = choice.get("finish_reason")
                if finish is not None:
                    info["finish"] = finish if finish in ("stop", "length", "content_filter", "tool_calls") else "other"
                    if finish != "stop":
                        return reject("unfinished_task")
    except UnicodeDecodeError:
        return reject("invalid_utf8")
    except json.JSONDecodeError:
        return reject("malformed_json")
    except ValueError as exc:
        return reject(str(exc))
    if not info["text_deltas"] or info["finish"] != "stop":
        return reject("missing_completion")
    # Buffering and size caps are intentional. Preserve native SSE bytes and delimiters.
    return json_reply(200, text) | {"protocol": info | {"classification": "complete"}}


def cli_evidence(stdout):
    info = {"events": 0, "text": 0, "step_finish": 0, "error": 0, "invalid_text": 0}
    parts = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, UnicodeError):
            continue
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            continue
        info["events"] += 1
        kind = event["type"]
        if kind in ("text", "step_finish", "error"):
            info[kind] += 1
        if kind == "text":
            part = event.get("part")
            text = part.get("text") if isinstance(part, dict) else None
            if isinstance(text, str):
                parts.append(text)
            else:
                info["invalid_text"] += 1
    try:
        result = json.loads("".join(parts))
        match = isinstance(result, dict) and result == EXPECTED and all(type(v) is int for v in result.values())
    except ValueError:
        match = False
    return info, bool(match and not info["error"] and not info["invalid_text"])


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
                with conn.makefile("rb") as wire:
                    status, media, payload = decode_reply_frame(wire.readline(MAX_RELAY_FRAME + 1))
            self.send_response(status)
            self.send_header("Content-Type", media)
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


def probe_refusal(system):
    conn = http.client.HTTPConnection("127.0.0.1", 18746, timeout=5)
    try:
        conn.request("POST", "/chat/completions", json.dumps({
            "model": MODEL, "stream": True, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": PROMPT},
            ]}), {"Content-Type": "application/json"})
        response = conn.getresponse()
        response.read(MAX_BYTES)
        if response.status != 403:
            raise RuntimeError("expected local request refusal")
    finally:
        conn.close()


def inner(hang):
    check_boundary()
    print('{"boundary_check":true}', flush=True)
    if hang:
        threading.Event().wait()
        return
    with ThreadingHTTPServer(("127.0.0.1", 18746), Bridge) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            probe_refusal("You are a title generator.")
            print('{"auxiliary_denied":true}', flush=True)
            code = subprocess.run(
                ["/gate/kilo", "run", "--pure", "--format", "json", "--model", "kilo/" + MODEL, PROMPT],
                timeout=40).returncode
            probe_refusal("You are Kilo, a CLI coding assistant.")
            print('{"duplicate_denied":true}', flush=True)
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


def run(archive, mode, fixture=None):
    if mode not in ("mock", "timeout"):
        raise SystemExit("Only offline mock and timeout modes are enabled")
    if os.uname().machine != "x86_64":
        raise SystemExit("Requires x86-64 Linux")
    with archive.open("rb") as file:
        archive_bytes = file.read(128 * 1024 * 1024 + 1)
    if len(archive_bytes) > 128 * 1024 * 1024 or hashlib.sha256(archive_bytes).hexdigest() != RELEASE_SHA:
        raise SystemExit("Release archive hash mismatch")
    stats = dict(forwarded=0, denied=0, admitted=0, result=None)
    permit = Permit()
    counters = threading.Lock()

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
                    with counters:
                        stats["denied"] += 1
                else:
                    stats["admitted"] += 1
                    if fixture is not None:
                        answer = relay_response(*fixture)
                    else:
                        event = {"id":"mock","object":"chat.completion.chunk","created":1,"model":MODEL,
                                 "choices":[{"index":0,"delta":{"content":json.dumps(EXPECTED)},"finish_reason":"stop"}]}
                        raw = ("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode()
                        answer = relay_response(200, "text/event-stream", raw)
                    stats["protocol"] = answer["protocol"]
                    stats["relay_status"] = answer["status"]
            except (AttributeError, ValueError, OSError, KeyError, http.client.HTTPException):
                answer = json_reply(502)
            self.wfile.write(reply_frame(answer))

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
                    {"timeout":"--hang", "mock":"--mock-inner"}[mode]]
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
        out, err = buffers
        stats["boundary_check"] = b'{"boundary_check":true}' in out
        if mode == "mock":
            stats["duplicate_denied"] = b'{"duplicate_denied":true}' in out
            stats["auxiliary_denied"] = b'{"auxiliary_denied":true}' in out
        stats["cli"], stats["result"] = cli_evidence(out)
        stats["exit_class"] = "timeout" if stats.get("timeout") else (
            "ok" if stats["exit"] == 0 else "cli_nonzero" if stats["exit"] > 0 else "signal")
        stats["stderr_present"] = bool(err)
    print(json.dumps(stats))
    safe = stats.get("boundary_check") and stats.get("streams_closed") and not stats.get("output_cap")
    if mode == "timeout":
        return 0 if safe and stats.get("timeout") and stats["forwarded"] == 0 and stats["exit"] == -9 else 1
    expected = (stats["forwarded"] == 0 and stats["relay_status"] == 200
                and stats["duplicate_denied"] and stats["auxiliary_denied"]) if "relay_status" in stats else False
    return 0 if safe and expected and stats["admitted"] == 1 and stats["exit"] == 0 and stats["result"] else 1


if __name__ == "__main__":
    if sys.argv[1:] in (["--mock-inner"], ["--hang"]):
        inner(sys.argv[1] == "--hang")
    elif len(sys.argv) == 3 and sys.argv[1] in ("mock", "timeout"):
        raise SystemExit(run(Path(sys.argv[2]), sys.argv[1]))
    else:
        raise SystemExit("usage: kilo_gate15.py mock|timeout VERIFIED_RELEASE_ARCHIVE")
