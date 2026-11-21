from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from scripts.kilo_gate15 import MAX_BYTES, MAX_RELAY_FRAME, MODEL, PROMPT, decode_reply_frame, relay_response, run
from scripts.kilo_owner_gate import (
    FixtureReply, OfflineExchange, approved_catalog, prepare_request, stage_sandbox,
)
from test_kilo_sse import SSE, VALID


def catalog(price="0", model=MODEL):
    return {"data": [{"id": model, "pricing": {"prompt": price, "completion": "0"}}]}


def approved_body():
    return {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "stream": True, "max_tokens": 128, "stream_options": {"include_usage": True}}


class OwnerGateTests(unittest.TestCase):
    def test_fixed_anonymous_post_contract(self):
        request = prepare_request(approved_body())
        self.assertEqual((request.method, request.host, request.path), (
            "POST", "ai-gateway.kilo.ai", "/api/v1/chat/completions"))
        self.assertTrue(request.verify_tls)
        self.assertFalse(request.follow_redirects)
        self.assertEqual(request.retries, 0)
        self.assertEqual(dict(request.headers), {
            "Content-Type": "application/json", "Accept": "text/event-stream", "Accept-Encoding": "identity",
        })
        self.assertEqual(json.loads(request.body), approved_body())
        with self.assertRaises(FrozenInstanceError):
            request.host = "example.invalid"
        with self.assertRaises(ValueError):
            prepare_request(approved_body() | {"model": "other:free"})
        with self.assertRaises(ValueError):
            prepare_request(approved_body() | {"tools": []})
        with self.assertRaises(ValueError):
            prepare_request(approved_body() | {"max_tokens": True})

    def test_catalog_fails_closed(self):
        self.assertTrue(approved_catalog(catalog()))
        for value in (catalog("0.01"), catalog("NaN"), catalog(model="other:free"),
                      {"data": catalog()["data"] * 2}, {"data": [None]},
                      {"data": [{"id": MODEL, "pricing": {"prompt": "0"}}]}):
            self.assertFalse(approved_catalog(value))

    def test_offline_exchange_rejects_real_mode_and_duplicate(self):
        exchange = OfflineExchange(catalog(), FixtureReply(200, SSE, VALID))
        reply = exchange(approved_body())
        self.assertEqual(reply[:3], (200, SSE, VALID))
        with self.assertRaises(ValueError):
            exchange(approved_body())
        self.assertEqual(exchange.attempts, 1)
        with self.assertRaises(ValueError):
            OfflineExchange(catalog("0.01"), FixtureReply(200, SSE, VALID))
        overlong = OfflineExchange(catalog(), FixtureReply(200, SSE, b"a" * (MAX_BYTES + 100)))
        self.assertEqual(len(overlong(approved_body())[2]), MAX_BYTES + 1)

    def test_response_metrics_usage_and_terminal(self):
        protocol = relay_response(200, SSE, VALID)["protocol"]
        self.assertEqual(protocol["usage"], {"prompt_tokens": 9, "completion_tokens": 8, "total_tokens": 17})
        self.assertTrue(protocol["done"])
        self.assertEqual(protocol["finish"], "stop")

    def test_http_boundary_reassembles_chunks_and_refuses_clipping(self):
        from scripts.kilo_owner_gate import inspect_http_fixture

        body = b""
        pieces = [VALID[:9], VALID[9:55], VALID[55:]]
        for piece in pieces:
            body += f"{len(piece):x}\r\n".encode() + piece + b"\r\n"
        headers = b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nTransfer-Encoding: chunked\r\n\r\n"
        self.assertEqual(inspect_http_fixture(headers + body + b"0\r\n\r\n"),
                         (200, "text/event-stream", VALID, None))
        with self.assertRaises(ValueError):
            inspect_http_fixture(headers + body)
        with self.assertRaises(ValueError):
            inspect_http_fixture(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nx")
        with self.assertRaises(ValueError):
            inspect_http_fixture(headers.replace(b"\r\n\r\n", b"\r\nContent-Length: 1\r\n\r\n") + body)

    def test_bwrap_mismatch_cannot_launch(self):
        with tempfile.TemporaryDirectory() as root:
            source, target = Path(root) / "fake", Path(root) / "staged"
            source.write_bytes(b"pretend ELF")
            with self.assertRaisesRegex(ValueError, "sandbox digest"):
                stage_sandbox(source, target)
            self.assertFalse(target.exists())

    def test_launcher_refuses_arbitrary_host_hooks_before_using_archive(self):
        def unexpected(*args):
            self.fail("executed untrusted hook")

        with self.assertRaisesRegex(ValueError, "inert fixture"):
            run(None, "mock", sandbox=Path("unused"), exchange=unexpected)
        with self.assertRaisesRegex(ValueError, "inert fixture"):
            run(None, "timeout", sandbox=unexpected)
        with self.assertRaisesRegex(ValueError, "inert fixture"):
            run(None, "mock", exchange=OfflineExchange(catalog(), FixtureReply(200, SSE, VALID)))

    def test_relay_rejects_frame_overflow(self):
        with self.assertRaisesRegex(ValueError, "incomplete relay frame"):
            decode_reply_frame(b" " * MAX_RELAY_FRAME + b"\n")
