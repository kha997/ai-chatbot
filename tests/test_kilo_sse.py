import hashlib
import json
import unittest

from scripts.kilo_gate15 import MAX_BYTES, MODEL, cli_evidence, relay_response, run

SSE = "text/event-stream; charset=utf-8"


def event(content=None, finish=None, usage=None, choices=None):
    delta = {"content": content} if content is not None else {}
    value = {"id": "synthetic-fixture", "object": "chat.completion.chunk",
             "created": 1, "model": MODEL, "choices": choices if choices is not None else
             [{"index": 0, "delta": delta, "finish_reason": finish}]}
    if usage is not None:
        value["usage"] = usage
    return json.dumps(value, ensure_ascii=False)


def stream(*values, sep="\n"):
    return "".join("data: " + value + sep * 2 for value in values).encode()


DELTAS = (event('{"catalog":2,'), event('"handoff":1,"total":3}'), event(finish="stop"))
USAGE = event(choices=[], usage={"prompt_tokens": 9, "completion_tokens": 8, "total_tokens": 17})
VALID = b": keep-alive\r\n\r\n" + stream(*DELTAS, USAGE, "[DONE]", sep="\r\n")
JSON_ERROR = b'{"error":{"message":"synthetic gateway failure","type":"server_error"}}'
MULTILINE = (": Tiếng Việt\n\ndata: " + DELTAS[0].replace(",", ",\ndata: ", 1)
             + "\n\n").encode() + stream(*DELTAS[1:], "[DONE]")
FULL_SIZE = b":" + (b"\0" * (MAX_BYTES - len(VALID) - 3)) + b"\n\n" + VALID
FIXTURES = {
    "crlf_usage": (SSE, VALID, 200),
    "no_usage": (SSE, stream(*DELTAS, "[DONE]"), 200),
    "finish_only": (SSE, stream(*DELTAS), 200),
    "multiline_utf8": (SSE, MULTILINE, 200),
    "full_size": (SSE, FULL_SIZE, 200),
    "json_error": ("application/json", JSON_ERROR, 502),
    "normal_json": ("application/json", b'{"choices":[{"message":{"content":"synthetic"}}]}', 502),
    "wrong_type": ("text/plain", VALID, 502),
    "false_sse": (SSE, JSON_ERROR, 502),
    "embedded_error": (SSE, stream(DELTAS[0], JSON_ERROR.decode(), "[DONE]"), 502),
    "sse_error_event": (SSE, b"event: error\ndata: provider error fixture\n\n", 502),
    "malformed": (SSE, stream(DELTAS[0], '{"choices":', "[DONE]"), 502),
    "truncated": (SSE, stream(DELTAS[0]) + b'data: {"choices":', 502),
    "empty_choices": (SSE, stream(USAGE, "[DONE]"), 502),
    "length_limit": (SSE, stream(DELTAS[0], event(finish="length"), "[DONE]"), 502),
    "no_finish": (SSE, stream(*DELTAS[:2], "[DONE]"), 502),
    "invalid_utf8": (SSE, b"data: \xff\n\n", 502),
    "data_after_done": (SSE, stream(*DELTAS, "[DONE]", DELTAS[0]), 502),
    "unframed_suffix": (SSE, stream(*DELTAS, "[DONE]") + b"extra garbage\n", 502),
}


class KiloSSERelayTests(unittest.TestCase):
    def test_response_status_and_byte_fidelity(self):
        for name, (media, raw, expected) in FIXTURES.items():
            with self.subTest(fixture=name, sha256=hashlib.sha256(raw).hexdigest()):
                response = relay_response(200, media, raw)
                self.assertEqual(response["status"], expected)
                if expected == 200:
                    self.assertEqual(response["payload"].encode(), raw)
                else:
                    self.assertEqual(response["content_type"], "application/json")
                    self.assertNotIn("synthetic gateway failure", response["payload"])

    def test_safe_diagnostics_distinguish_metadata_and_failure(self):
        good = relay_response(200, SSE, VALID)["protocol"]
        self.assertEqual((good["classification"], good["events"], good["text_deltas"]),
                         ("complete", 5, 2))
        self.assertTrue(good["done"] and good["usage_present"])
        self.assertEqual(good["finish"], "stop")
        without_usage = relay_response(200, SSE, stream(*DELTAS))["protocol"]
        self.assertFalse(without_usage["usage_present"] or without_usage["done"])
        for status, media, raw, encoding, reason in (
            (200, "application/json", JSON_ERROR, None, "embedded_error"),
            (200, "text/plain", VALID, None, "unexpected_media"),
            (200, SSE, VALID, "gzip", "unsupported_encoding"),
            (200, SSE, b"0" * (MAX_BYTES + 1), None, "response_cap"),
            (429, "application/json", JSON_ERROR, None, "http_status"),
        ):
            with self.subTest(reason=reason):
                response = relay_response(status, media, raw, encoding)
                self.assertEqual(response["status"], 502)
                self.assertEqual(response["protocol"]["classification"], reason)
                self.assertNotIn("synthetic gateway failure", json.dumps(response))

    def test_kilo_json_lines_redact_errors_and_require_oracle(self):
        text_a = b'{"type":"text","part":{"text":"{\\"catalog\\":2,"}}\n'
        text_b = b'{"type":"text","part":{"text":"\\"handoff\\":1,\\"total\\":3}"}}\n'
        finished = b'{"type":"step_finish","part":{}}'
        events, result = cli_evidence(b'[]\n' + text_a + text_b + finished)
        self.assertTrue(result)
        self.assertEqual((events["text"], events["step_finish"]), (2, 1))
        rejected = b'{"type":"error","error":{"message":"synthetic redaction canary"}}'
        evidence, result = cli_evidence(text_a + text_b + rejected)
        self.assertFalse(result)
        self.assertEqual(evidence["error"], 1)
        self.assertNotIn("canary", json.dumps(evidence))
        self.assertFalse(cli_evidence(b'{"type":"text","part":[]}')[1])

    def test_live_mode_rejected_before_reading_an_archive(self):
        with self.assertRaisesRegex(SystemExit, "Only offline"):
            run(None, "live")

    def test_full_size_sse_survives_bounded_relay_frame(self):
        from scripts.kilo_gate15 import MAX_RELAY_FRAME, decode_reply_frame, reply_frame

        # Control bytes in a comment are ignored by SSE but expand under JSON escaping.
        raw = FULL_SIZE
        self.assertEqual(len(raw), MAX_BYTES)
        response = relay_response(200, SSE, raw)
        self.assertGreater(len(json.dumps(response).encode()), MAX_BYTES * 4)
        frame = reply_frame(response)
        self.assertLessEqual(len(frame), MAX_RELAY_FRAME)
        status, content_type, payload = decode_reply_frame(frame)
        self.assertEqual((status, content_type, payload), (200, "text/event-stream", raw))
        with self.assertRaises(ValueError):
            decode_reply_frame(frame[:-1])
