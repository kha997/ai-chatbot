"""Offline OpenCode configuration and one-request localhost fixture check."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_gate15 import Permit, emit_filter, unique_json_keys
from scripts.kilo_owner_gate import stage_sandbox
from scripts.kilo_tls_offline import require_loopback

MODEL = "qwen3:14b"
PROVIDER = "local-ollama"
MODEL_REF = f"{PROVIDER}/{MODEL}"
BASE = "http://127.0.0.1:11435/v1"
ORACLE = {"catalog": 2, "handoff": 1, "total": 3}
CONFIG = {"enabled_providers": [PROVIDER], "model": MODEL_REF, "small_model": MODEL_REF,
          "autoupdate": False, "share": "disabled", "permission": {"*": "deny"}, "mcp": {}, "plugin": [],
          "provider": {PROVIDER: {"name": "Dedicated local fixture", "npm": "@ai-sdk/openai-compatible",
                                 "options": {"baseURL": BASE}, "models": {
                                     MODEL: {"name": "Qwen3 14B", "tool_call": False,
                                             "limit": {"context": 2048, "output": 128}}}}}}
PACKET = {"model": MODEL, "messages": [{"role": "user", "content":
            'Classify the synthetic records catalog, handoff, catalog. Return {"catalog":2,"handoff":1,"total":3}.'}],
          "max_tokens": 128, "stream": False}
FIXTURE = Path(__file__).with_name("fixtures") / "ollama_local_client.py"


def validate_config(config):
    if config.get("autoupdate") is not False or any(config.get(key) != value for key, value in CONFIG.items()):
        raise ValueError("resolved configuration differs from pinned local fixture")


class RequestGate:
    def __init__(self):
        self.permit = Permit()
        self.accepted = 0

    def admit(self, body):
        if body != PACKET or type(body["max_tokens"]) is not int or body["stream"] is not False:
            return 403
        if not self.permit.take():
            return 409
        self.accepted += 1
        return 200


def mock_server(gate, case):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            data = json.dumps(payload).encode("ascii")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if self.path != "/v1/models":
                return self.reply(404, {})
            return self.reply(200, {"data": [{"id": MODEL}]})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                return self.reply(404, {})
            try:
                self.connection.settimeout(1)
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    return self.reply(413, {})
                value = json.loads(self.rfile.read(size), object_pairs_hook=unique_json_keys)
            except (ValueError, OSError):
                return self.reply(400, {})
            status = gate.admit(value)
            if status != 200:
                return self.reply(status, {})
            if case == "timeout":
                time.sleep(0.5)
            oracle = ORACLE if case != "invalid" else ORACLE | {"total": True}
            self.reply(200, {"model": MODEL, "choices": [{
                "finish_reason": "stop", "message": {"content": json.dumps(oracle)}}]})

    return HTTPServer(("127.0.0.1", 11435), Handler)


def sandbox_run(argv, verify_bwrap, directory, opencode, *, timeout=10, scratch_limit=None):
    with tempfile.TemporaryFile(dir="/tmp") as seccomp:
        emit_filter(seccomp)
        options = {"PATH": "/usr/bin", "HOME": "/tmp/home", "XDG_CONFIG_HOME": "/tmp/config",
                   "XDG_DATA_HOME": "/tmp/data", "XDG_STATE_HOME": "/tmp/state", "XDG_CACHE_HOME": "/tmp/cache",
                   "OPENCODE_CONFIG": "/fixture/opencode.json",
                   "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_SHARE": "1",
                   "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
                   "OPENCODE_DISABLE_PROJECT_CONFIG": "1", "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
                   "HOST_CANARY": str(directory / "host-canary"),
                   "FIXTURE_NETNS": str(Path("/proc/self/ns/net").stat().st_ino)}
        flags = [word for key, val in options.items() for word in ("--setenv", key, val)]
        command = [str(verify_bwrap), "--unshare-all", "--unshare-user", "--share-net", "--disable-userns",
                   "--new-session", "--die-with-parent", "--clearenv", "--cap-drop", "ALL",
                   "--seccomp", str(seccomp.fileno()), "--ro-bind", "/usr/bin/python3", "/usr/bin/python3",
                   "--ro-bind", "/usr/lib/python3.12", "/usr/lib/python3.12",
                   "--ro-bind", "/usr/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu",
                   "--ro-bind", "/usr/lib64", "/usr/lib64", "--ro-bind", str(opencode), "/usr/bin/opencode",
                   "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
                   "--proc", "/proc", "--dev", "/dev",
                   *(("--size", str(scratch_limit)) if scratch_limit else ()),
                   "--tmpfs", "/tmp", "--dir", "/work",
                   "--ro-bind", str(directory / "inputs"), "/fixture", "--chdir", "/work",
                   *flags, *argv]
        result = subprocess.run(command, env={}, pass_fds=(seccomp.fileno(),),
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise ValueError(f"isolated fixture process exited {result.returncode}")
    return json.loads(result.stdout, object_pairs_hook=unique_json_keys)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sandbox", type=Path)
    args = parser.parse_args()
    require_loopback()
    opencode = Path("/usr/bin/opencode").resolve(strict=True)
    with opencode.open("rb") as binary:
        if binary.read(4) != b"\x7fELF":
            raise ValueError("expected WSL OpenCode ELF")
    with tempfile.TemporaryDirectory(prefix="issue30-fixture-", dir="/tmp") as temp:
        scratch = Path(temp)
        bwrap = stage_sandbox(args.sandbox, scratch / "bwrap")
        (scratch / "host-canary").touch()
        inputs = scratch / "inputs"
        inputs.mkdir()
        (inputs / "opencode.json").write_text(json.dumps(CONFIG), encoding="ascii")
        (inputs / "packet.json").write_text(json.dumps(PACKET), encoding="ascii")
        (inputs / "client.py").write_bytes(FIXTURE.read_bytes())
        resolved = sandbox_run(["/usr/bin/opencode", "debug", "config", "--pure"], bwrap, scratch, opencode)
        validate_config(resolved)
        print(json.dumps({"opencode_resolves_local_config": True, "model": resolved["model"],
                          "endpoint": BASE, "opencode_inference_commands": 0}))
        for case in ("ok", "invalid", "timeout"):
            gate = RequestGate()
            with mock_server(gate, case) as service:
                thread = threading.Thread(target=service.serve_forever)
                thread.start()
                try:
                    receipt = sandbox_run(["/usr/bin/python3", "-IS", "/fixture/client.py", case],
                                          bwrap, scratch, opencode)
                finally:
                    service.shutdown()
                    thread.join(2)
                if thread.is_alive() or gate.accepted != 1 or gate.admit(PACKET) != 409:
                    raise ValueError("mock gate or cleanup failed")
            print(json.dumps({"case": case, "mock_posts_admitted": gate.accepted, "real_posts": 0,
                              "socket_closed": service.fileno() == -1, "replay_denied": True, **receipt}))
    if scratch.exists():
        raise ValueError("temporary profile remained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
