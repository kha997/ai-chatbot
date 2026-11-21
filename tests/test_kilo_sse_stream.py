"""Synthetic HTTP/SSE contracts for the offline-only streaming candidate."""

import json
import io
import tracemalloc
import unittest
from unittest.mock import patch

from scripts.kilo_gate15 import MODEL, relay_response
from test_kilo_sse import DELTAS, JSON_ERROR, SSE, USAGE, VALID, event, stream

ORACLE = '{"catalog":2,"handoff":1,"total":3}'


def large_sse(size):
    chunks = [b": m\xc3\xa3 keepalive\r\n\r\n"]
    for char in ORACLE:
        data = json.loads(event(char))
        data["synthetic_metadata"] = "m" * 512
        chunks.append(stream(json.dumps(data), sep="\r\n"))
    chunks.append(stream(DELTAS[-1], USAGE, "[DONE]", sep="\r\n"))
    remaining = size - sum(map(len, chunks))
    metadata = stream(event(choices=[]).replace('[]', '[], "synthetic_metadata":"' + "x" * 900 + '"', 1))
    while remaining >= len(metadata):
        chunks.insert(-1, metadata)
        remaining -= len(metadata)
    while remaining >= 12:
        pad = min(remaining, 1024)
        chunks.insert(-1, b": " + b"m" * (pad - 6) + b"\r\n\r\n")
        remaining -= pad
    chunks.insert(-1, b"\r\n" * (remaining // 2) + b"\n" * (remaining % 2))
    return b"".join(chunks)


def http_wire(body, media=SSE, *, chunk_size=None, extra=b""):
    headers = b"HTTP/1.1 200 Fixture\r\nContent-Type: " + media.encode() + b"\r\n"
    if chunk_size is None:
        return headers + f"Content-Length: {len(body)}\r\n".encode() + extra + b"\r\n" + body
    body = b"".join(f"{len(part):x}\r\n".encode() + part + b"\r\n"
                    for offset in range(0, len(body), chunk_size)
                    for part in (body[offset:offset + chunk_size],)) + b"0\r\n\r\n"
    return headers + b"Transfer-Encoding: chunked\r\n" + extra + b"\r\n" + body


class StreamQualificationTests(unittest.TestCase):
    def parse(self, wire):
        from scripts.kilo_sse_stream import inspect_fixture

        return inspect_fixture(wire)

    def test_exact_32k_boundary_and_larger_valid_fixture(self):
        for size in (32767, 32768, 32769, 65536, 131072, 262144):
            with self.subTest(size=size):
                body = large_sse(size)
                self.assertEqual(len(body), size)
                legacy = relay_response(200, SSE, body, expected_model=MODEL)
                self.assertEqual(legacy["status"], 200 if size <= 32768 else 502)
                result = self.parse(http_wire(body))
                self.assertEqual(result["status"], 200, result["protocol"])
                self.assertEqual(result["protocol"]["bytes"], size)
                self.assertEqual(result["protocol"]["text_bytes"], len(ORACLE))
                self.assertEqual(result["protocol"]["usage"]["total_tokens"], 17)
                self.assertLess(len(result["payload"].encode()), 2048)
                truncated = self.parse(http_wire(body[:-2]))
                self.assertEqual(truncated["protocol"]["classification"], "truncated_event")

    def test_http_and_sse_failures(self):
        for name, wire in (
            ("response_cap", http_wire(large_sse(262145))),
            ("frame_cap", http_wire(b": " + b"x" * 8192 + b"\n\n" + VALID)),
            ("frame_cap", http_wire(stream(event("x" * 8192)) + VALID)),
            ("event_cap", http_wire(b":\n\n" * 2100 + VALID)),
            ("output_cap", http_wire(stream(event("x" * 4200), DELTAS[-1], "[DONE]"))),
            ("missing_completion", http_wire(stream(*DELTAS))),
            ("data_after_done", http_wire(VALID + stream(DELTAS[0]))),
            ("truncated_event", http_wire(VALID[:-2])),
            ("invalid_utf8", http_wire(b": \xff\n\n" + VALID)),
            ("embedded_error", http_wire(JSON_ERROR, "application/json")),
            ("embedded_error", http_wire(stream(DELTAS[0], JSON_ERROR.decode(), "[DONE]"))),
            ("model_mismatch", http_wire(VALID.replace(MODEL.encode(), b"other/model:free"))),
            ("invalid_http_framing", http_wire(VALID, extra=b"Transfer-Encoding: chunked\r\n")),
            ("invalid_http_framing", http_wire(VALID, extra=b" X-Obsolete: value\r\n")),
            ("header_cap", http_wire(VALID, extra=b"X-Synthetic: " + b"x" * 16384 + b"\r\n")),
            ("invalid_http_framing", http_wire(VALID)[:-1]),
            ("invalid_http_framing", http_wire(VALID, chunk_size=32)[:-1]),
            ("chunk_cap", http_wire(large_sse(32769), chunk_size=1)),
            ("unsupported_encoding", http_wire(VALID, extra=b"Content-Encoding: gzip\r\n")),
        ):
            with self.subTest(name=name):
                result = self.parse(wire)
                self.assertEqual(result["status"], 502)
                self.assertEqual(result["protocol"]["classification"], name)
                self.assertNotIn("synthetic gateway failure", result["payload"])

    def test_one_byte_chunk_boundaries_preserve_crlf_utf8_and_multiline(self):
        from test_kilo_sse import MULTILINE

        body = b": caf\xc3\xa9\r\n\r\n" + MULTILINE
        result = self.parse(http_wire(body, chunk_size=1))
        self.assertEqual(result["status"], 200, result["protocol"])
        self.assertEqual(result["protocol"]["bytes"], len(body))
        self.assertEqual(result["protocol"]["text_bytes"], len(ORACLE))

    def test_bom_duplicate_event_and_non_json_numbers(self):
        bom = bytes.fromhex("efbbbf")
        ambiguous = b"event: error\nevent: message\n" + stream(DELTAS[0])
        for body, classification in (
            (bom + VALID, "complete"),
            (b"\n" + bom + ambiguous + VALID, "unframed_data"),
            (ambiguous + VALID, "duplicate_event_type"),
            (stream(DELTAS[0][:-1] + ', "metadata": NaN}', *DELTAS[1:], "[DONE]"), "malformed_event"),
        ):
            with self.subTest(classification=classification):
                result = self.parse(http_wire(body, chunk_size=1))
                self.assertEqual(result["protocol"]["classification"], classification)

    def test_slow_body_deadline_and_pull_read_bound(self):
        from scripts.kilo_sse_stream import BODY_SECONDS, READ_SIZE, inspect_response

        class Source(io.BytesIO):
            now = 0
            reads = 0

            def read(self, size):
                self.reads += 1
                self.now += BODY_SECONDS / 2
                if not 0 < size <= READ_SIZE:
                    raise AssertionError("unbounded body read")
                return super().read(size)

        slow = Source(http_wire(large_sse(131072)))
        with patch("scripts.kilo_sse_stream.monotonic", side_effect=lambda: slow.now):
            result = inspect_response(slow)
        self.assertEqual(result["protocol"]["classification"], "body_deadline")
        self.assertEqual(slow.reads, 2)
        self.assertEqual(result["protocol"]["relay_bytes"], 0)

    def test_large_input_does_not_allocate_a_whole_body_copy(self):
        from scripts.kilo_sse_stream import inspect_response

        source = io.BytesIO(http_wire(large_sse(262144), chunk_size=997))
        tracemalloc.start()
        try:
            result = inspect_response(source)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(result["status"], 200)
        self.assertLess(peak, 128 * 1024)
