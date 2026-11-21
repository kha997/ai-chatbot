import hashlib
import json
import unittest

from scripts.kilo_gate15 import MODEL, relay_response

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
FIXTURES = {
    "crlf_usage": (SSE, VALID, 200),
    "no_usage": (SSE, stream(*DELTAS, "[DONE]"), 200),
    "finish_only": (SSE, stream(*DELTAS), 200),
    "multiline_utf8": (SSE, b'data: {\ndata: "choices":[]}\n\n'
                      + stream(event("tổng"), event(finish="stop"), "[DONE]"), 200),
    "json_error": ("application/json", JSON_ERROR, 502),
    "normal_json": ("application/json", b'{"choices":[{"message":{"content":"synthetic"}}]}', 502),
    "wrong_type": ("text/plain", VALID, 502),
    "false_sse": (SSE, JSON_ERROR, 502),
    "embedded_error": (SSE, stream(DELTAS[0], JSON_ERROR.decode(), "[DONE]"), 502),
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
