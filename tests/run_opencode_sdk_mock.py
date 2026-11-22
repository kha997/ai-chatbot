"""Exercise the installed OpenCode 1.18.30 SDK against a no-egress local fake."""

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import tempfile
import threading

from run_ollama_local_mock import (BASE, CONFIG, MODEL, MODEL_REF, ORACLE, require_loopback,
                                  sandbox_run, stage_sandbox, unique_json_keys)
from scripts.kilo_gate15 import cli_evidence

ELF_SHA = "87bd160e053af86b5b409daabf71f8dc05bbc3a2a3a5f563f36011cdf706a999"
PROMPT = "Classify the synthetic records catalog, handoff, catalog. Return only the three-count JSON."
SYSTEM = "This is a synthetic offline fixture. Reply with one JSON object. No tools."
LIMIT = 16384
FIXTURE = Path(__file__).with_name("fixtures") / "opencode_sdk_worker.py"


class RequestAudit:
    def __init__(self):
        self.rows = []
        self.generation = 0
        self.metadata = 0

    def has_exact_exchange(self):
        return self.generation == 1 and len(self.rows) == 1 and self.rows[0]["status"] == 200

    def admit(self, method, path, body, length):
        row = {"method": method if method in ("GET", "POST") else "other",
               "path": path if path in ("/v1/models", "/v1/chat/completions") else "<unexpected>",
               "bytes": length}
        status = 404
        if method == "GET" and path == "/v1/models":
            self.metadata += 1
            status = 200 if self.metadata == 1 and body is None and length == 0 else 409
        elif method == "POST" and path == "/v1/chat/completions":
            self.generation += 1
            status = 409 if self.generation > 1 else 403
            if isinstance(body, dict):
                budget = body.get("max_tokens", body.get("max_completion_tokens"))
                messages = body.get("messages")
                tools = body.get("tools", [])
                row.update(model_match=body.get("model") == MODEL, stream=body.get("stream") is True,
                           max_output=budget if type(budget) is int else None,
                           messages=len(messages) if isinstance(messages, list) else None,
                           tool_count=len(tools) if isinstance(tools, list) else None)
                if status != 409 and 0 < length <= LIMIT and valid_packet(body):
                    status = 200
        self.rows.append(row | {"status": status})
        return status


def valid_packet(body):
    if not body.keys() <= {"model", "stream", "stream_options", "messages", "max_tokens", "max_completion_tokens",
                           "temperature", "top_p", "top_k", "seed", "frequency_penalty", "presence_penalty",
                           "tools", "tool_choice", "parallel_tool_calls"}:
        return False
    limits = [body[key] for key in ("max_tokens", "max_completion_tokens") if key in body]
    if (body.get("model") != MODEL or body.get("stream") is not True or body.get("tools", []) != []
            or body.get("tool_choice") not in (None, "none") or not limits
            or any(type(n) is not int or not 1 <= n <= 128 for n in limits)):
        return False
    messages = body.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 8:
        return False
    users = []
    for item in messages:
        if not isinstance(item, dict) or set(item) != {"role", "content"} or item["role"] not in ("system", "user"):
            return False
        if item["role"] != "user":
            continue
        content = item["content"]
        if isinstance(content, list) and len(content) == 1 and isinstance(content[0], dict):
            part = content[0]
            if part.get("type") == "text" and set(part) == {"type", "text"}:
                content = part["text"]
        users.append(content)
    return users == [PROMPT]


def fixture_server(audit):
    chunk = {"id": "issue34-fake", "object": "chat.completion.chunk", "created": 1, "model": MODEL}
    events = [chunk | {"choices": [{"index": 0, "delta": {"role": "assistant", "content": json.dumps(ORACLE)},
                                   "finish_reason": None}]},
              chunk | {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
              chunk | {"choices": [], "usage": {"prompt_tokens": 6, "completion_tokens": 8, "total_tokens": 14}}]
    sse = "".join("data: " + json.dumps(event) + "\n\n" for event in events) + "data: [DONE]\n\n"

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            self.request.settimeout(1)
            super().setup()

        def log_message(self, *args):
            pass

        def __getattr__(self, name):
            if name.startswith("do_"):
                return self.handle_fixture
            raise AttributeError(name)

        def handle_fixture(self):
            length, body = 0, None
            if self.command == "POST":
                try:
                    values = self.headers.get_all("Content-Length", [])
                    if len(values) == 1 and values[0].isdigit() and len(values[0]) < 10:
                        length = int(values[0])
                    if 0 < length <= LIMIT and self.headers.get("Transfer-Encoding") is None:
                        body = json.loads(self.rfile.read(length), object_pairs_hook=unique_json_keys)
                except (ValueError, OSError, RecursionError):
                    pass
            status = audit.admit(self.command, self.path, body, length)
            is_sse = status == 200 and self.command == "POST"
            if is_sse:
                response = sse.encode("ascii")
            elif status == 200:
                response = json.dumps({"data": [{"id": MODEL}]}).encode("ascii")
            else:
                response = b'{"error":{"message":"offline fixture refused the request"}}'
            self.send_response(status)
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Content-Type", "text/event-stream" if is_sse else "application/json")
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            try:
                self.wfile.write(response)
                audit.rows[-1]["response_bytes_written"] = len(response)
            except OSError:
                pass

    return HTTPServer(("127.0.0.1", 11435), Handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sandbox", type=Path)
    args = parser.parse_args()
    require_loopback()
    opencode = Path("/usr/bin/opencode").resolve(strict=True)
    with opencode.open("rb") as binary:
        if binary.read(4) != b"\x7fELF":
            raise ValueError("expected Linux ELF")
        binary.seek(0)
        if hashlib.file_digest(binary, "sha256").hexdigest() != ELF_SHA:
            raise ValueError("unexpected OpenCode ELF hash")

    config = CONFIG | {"agent": {"fixture": {"mode": "primary", "prompt": SYSTEM, "permission": {"*": "deny"}}},
                       "compaction": {"auto": False}}
    audit = RequestAudit()
    with tempfile.TemporaryDirectory(prefix="issue34-sdk-", dir="/tmp") as temp:
        scratch = Path(temp)
        bwrap = stage_sandbox(args.sandbox, scratch / "bwrap")
        (scratch / "host-canary").touch()
        inputs = scratch / "inputs"
        inputs.mkdir()
        (inputs / "opencode.json").write_text(json.dumps(config))
        (inputs / "run.json").write_text(json.dumps({"model": MODEL_REF, "prompt": PROMPT}))
        (inputs / "worker.py").write_bytes(FIXTURE.read_bytes())
        with fixture_server(audit) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                receipt = sandbox_run(["/usr/bin/python3", "-IS", "/fixture/worker.py"], bwrap, scratch, opencode,
                                      timeout=29, scratch_limit=64 * 1024 * 1024)
            finally:
                server.shutdown()
                thread.join(2)
        closed = server.fileno() == -1 and not thread.is_alive()
    stats, exact = cli_evidence(receipt.pop("fixture_stdout").encode("utf-8"))
    passed = (audit.has_exact_exchange()
              and all(row.get("response_bytes_written", 0) > 0 for row in audit.rows)
              and receipt["exit"] == 0 and not receipt["timeout"] and not receipt["output_cap"] and receipt["boundary"]
              and receipt["sdk_runtime"] and receipt["tool_events"] == 0 and receipt["reaped"] and closed
              and not scratch.exists() and exact and stats["step_finish"] == 1)
    print(json.dumps({"qualification": "SDK_MOCK_PASS" if passed else "BLOCKED_ADAPTER",
                      "requests": audit.rows, "cli": stats, "oracle": ORACLE if exact else None, "worker": receipt,
                      "endpoint": BASE, "real_model_posts": 0, "socket_closed": closed,
                      "scratch_removed": not scratch.exists(), "elf_sha256": ELF_SHA}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
