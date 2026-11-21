"""Bounded HTTP/SSE validation for synthetic offline Kilo qualification."""

import io
import json
import re
from http.client import HTTPException, HTTPResponse
from pathlib import Path
from time import monotonic

from scripts.kilo_gate15 import MAX_BYTES, MODEL, Permit, json_reply, unique_json_keys

BODY_LIMIT = 256 * 1024
FRAME_LIMIT = 8 * 1024
TEXT_LIMIT = 4 * 1024
HEADER_LIMIT = 16 * 1024
FRAME_COUNT_LIMIT = 2048
CHUNK_COUNT_LIMIT = 4096
READ_SIZE = 4096
BODY_SECONDS = 8
HEADER_FIELD = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+:[\t\x20-\x7e\x80-\xff]*\r\n")


class Rejected(ValueError):
    """A fixed, public classification."""


class HeaderBudget:
    def __init__(self, stream, deadline):
        self.stream = stream
        self.deadline = deadline
        self.remaining = HEADER_LIMIT
        self.status_line = True

    def readline(self, limit):
        if monotonic() >= self.deadline:
            raise Rejected("body_deadline")
        line = self.stream.readline(min(limit, self.remaining + 1))
        if monotonic() >= self.deadline:
            raise Rejected("body_deadline")
        self.remaining -= len(line)
        if self.remaining < 0:
            raise Rejected("header_cap")
        if self.status_line:
            if not re.fullmatch(rb"HTTP/1\.[01] [2-5][0-9]{2}(?: [\x20-\x7e]*)?\r\n", line):
                raise Rejected("invalid_http_framing")
            self.status_line = False
        elif line != b"\r\n" and not HEADER_FIELD.fullmatch(line):
            raise Rejected("invalid_http_framing")
        return line

    def close(self):
        pass

    def flush(self):
        pass


def body_parts(response, info, deadline):
    headers = response.headers
    for name in ("Content-Type", "Content-Encoding", "Transfer-Encoding", "Content-Length"):
        if len(headers.get_all(name, [])) > 1:
            raise Rejected("invalid_http_framing")
    transfer = headers.get("Transfer-Encoding")
    length = headers.get("Content-Length")
    if transfer is not None and (transfer.lower() != "chunked" or length is not None):
        raise Rejected("invalid_http_framing")
    if transfer is None and (length is None or not re.fullmatch(r"[0-9]{1,12}", length)):
        raise Rejected("invalid_http_framing")
    info["declared_bytes"] = None if length is None else int(length)
    stream = response.fp.stream

    def read(fn, size):
        if monotonic() >= deadline:
            raise Rejected("body_deadline")
        data = fn(size)
        if monotonic() >= deadline:
            raise Rejected("body_deadline")
        return data

    def blocks(size):
        if info["bytes"] + size > BODY_LIMIT:
            raise Rejected("response_cap")
        while size:
            data = read(stream.read, min(READ_SIZE, size))
            info["bytes"] += len(data)
            if not data:
                raise Rejected("invalid_http_framing")
            size -= len(data)
            yield data

    if length is not None:
        yield from blocks(int(length))
        return
    for _ in range(CHUNK_COUNT_LIMIT):
        line = read(stream.readline, 11)
        if not re.fullmatch(rb"[0-9A-Fa-f]{1,8}\r\n", line):
            raise Rejected("invalid_http_framing")
        size = int(line[:-2], 16)
        yield from blocks(size)
        if read(stream.read, 2) != b"\r\n":
            raise Rejected("invalid_http_framing")
        if not size:
            return
    raise Rejected("chunk_cap")


LINE_BREAK = re.compile(rb"[\r\n]")


def frames(parts, info):
    """Retain one normalized frame even when a read splits CRLF or UTF-8."""
    frame = bytearray()
    line_size = 0
    skip_lf = False
    first = True
    for part in parts:
        cursor = 0
        for match in LINE_BREAK.finditer(part):
            end = match.start()
            if skip_lf and end == cursor and part[end] == 10:
                cursor = end + 1
                skip_lf = False
                continue
            frame.extend(part[cursor:end])
            line_size += end - cursor
            ended = not line_size
            cursor = end + 1
            skip_lf = part[end] == 13
            frame.append(10)
            if len(frame) > FRAME_LIMIT:
                raise Rejected("frame_cap")
            line_size = 0
            if ended and len(frame) > 1:
                info["frames"] += 1
                if info["frames"] > FRAME_COUNT_LIMIT:
                    raise Rejected("event_cap")
                text = frame.decode("utf-8")
                yield text.removeprefix("\ufeff") if first else text
            if ended:
                first = False
                frame.clear()
        if cursor < len(part):
            skip_lf = False
            frame.extend(part[cursor:])
            line_size += len(part) - cursor
            if len(frame) >= FRAME_LIMIT:
                raise Rejected("frame_cap")
    if frame:
        raise Rejected("truncated_event")


def frame_data(frame, done):
    data = []
    kind = None
    for line in frame.split("\n"):
        if not line or line.startswith(":"):
            continue
        if done:
            raise Rejected("data_after_done")
        name, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if name == "data":
            data.append(value)
        elif name == "event":
            if kind is not None:
                raise Rejected("duplicate_event_type")
            kind = value or "message"
        elif name not in ("id", "retry"):
            raise Rejected("unframed_data")
    if kind == "error":
        raise Rejected("embedded_error")
    if kind not in (None, "message"):
        raise Rejected("unexpected_event")
    return "\n".join(data) if data else None


def parse_event_json(data):
    def invalid_constant(_):
        raise Rejected("malformed_event")

    return json.loads(data, object_pairs_hook=unique_json_keys, parse_constant=invalid_constant)


def sanitized_sse(parts, info):
    text = bytearray()
    for frame in frames(parts, info):
        data = frame_data(frame, info["done"])
        if data is not None:
            info["events"] += 1
            if data == "[DONE]":
                info["done"] = True
                continue
            event = parse_event_json(data)
            if not isinstance(event, dict):
                raise Rejected("invalid_event")
            if "error" in event:
                raise Rejected("embedded_error")
            if "model" in event:
                info["model_supplied"] = True
                if event["model"] != MODEL:
                    raise Rejected("model_mismatch")
            usage = event.get("usage")
            if isinstance(usage, dict):
                info["usage_present"] = True
                counts = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if type(usage.get(k)) is int and 0 <= usage[k] <= 2**31 - 1}
                if counts:
                    info["usage"] = counts
            choices = event.get("choices")
            if not isinstance(choices, list) or len(choices) > 1:
                raise Rejected("invalid_choices")
            if not choices:
                continue
            choice = choices[0]
            if (not isinstance(choice, dict) or type(choice.get("index")) is not int
                    or choice["index"] != 0 or info["finish"] != "absent"):
                raise Rejected("invalid_choices")
            delta = choice.get("delta", {})
            if not isinstance(delta, dict) or ("tool_calls" in delta or "function_call" in delta):
                raise Rejected("unexpected_delta")
            content = delta.get("content")
            if content is not None and not isinstance(content, str):
                raise Rejected("unexpected_delta")
            if content:
                encoded = content.encode("utf-8")
                info["text_bytes"] += len(encoded)
                if info["text_bytes"] > TEXT_LIMIT:
                    raise Rejected("output_cap")
                text.extend(encoded)
            finish = choice.get("finish_reason")
            if finish is not None:
                if finish != "stop":
                    raise Rejected("unfinished_task")
                info["finish"] = "stop"
    if not text or not info["done"] or info["finish"] != "stop":
        raise Rejected("missing_completion")

    # Deliver one canonical bounded stream after upstream framing AND terminal validation.
    # Only forward the validated task text and typed usage counters, never arbitrary metadata.
    prefix = {"id": "bounded-relay", "object": "chat.completion.chunk", "created": 1}
    if info["model_supplied"]:
        prefix["model"] = MODEL
    chunks = [
        prefix | {"choices": [{"index": 0, "delta": {"role": "assistant", "content": text.decode("utf-8")},
                               "finish_reason": None}]},
        prefix | {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
    ]
    if info["usage"] is not None:
        chunks.append(prefix | {"choices": [], "usage": info["usage"]})
    return "".join("data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"


def inspect_response(stream):
    """Read synchronous HTTP input incrementally. The caller owns hard I/O cancellation."""
    start = monotonic()
    deadline = start + BODY_SECONDS
    info = {"http_status": None, "media": "other", "encoding": "identity", "declared_bytes": None,
            "bytes": 0, "frames": 0, "events": 0, "text_bytes": 0, "done": False, "finish": "absent",
            "model_supplied": False, "usage_present": False, "usage": None, "relay_bytes": 0}

    class FixtureSocket:
        def makefile(self, mode):
            return HeaderBudget(stream, deadline)

    try:
        with HTTPResponse(FixtureSocket()) as response:
            response.begin()
            info["http_status"] = response.status
            if response.status != 200:
                raise Rejected("http_status")
            media = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if response.headers.get("Content-Encoding", "").lower() not in ("", "identity"):
                info["encoding"] = "unsupported"
                raise Rejected("unsupported_encoding")
            info["media"] = {"text/event-stream": "sse", "application/json": "json"}.get(media, "other")
            parts = body_parts(response, info, deadline)
            if media == "application/json":
                error_body = bytearray()
                for part in parts:
                    if len(error_body) + len(part) > READ_SIZE:
                        raise Rejected("unexpected_media")
                    error_body.extend(part)
                event = parse_event_json(error_body)
                if isinstance(event, dict) and "error" in event:
                    raise Rejected("embedded_error")
                raise Rejected("unexpected_media")
            if media != "text/event-stream":
                raise Rejected("unexpected_media")
            payload = sanitized_sse(parts, info)
            if monotonic() >= deadline:
                raise Rejected("body_deadline")
            size = len(payload.encode("utf-8"))
            if size > MAX_BYTES:
                raise Rejected("relay_cap")
            info["relay_bytes"] = size
        answer, reason = json_reply(200, payload), "complete"
    except Rejected as exc:
        answer, reason = json_reply(502), str(exc)
    except UnicodeError:
        answer, reason = json_reply(502), "invalid_utf8"
    except (ValueError, RecursionError):
        answer, reason = json_reply(502), "malformed_event"
    except (HTTPException, OSError):
        answer, reason = json_reply(502), "invalid_http_framing"
    return answer | {"protocol": info | {"classification": reason, "duration_ms": int((monotonic() - start) * 1000)}}


def inspect_fixture(wire):
    return inspect_response(io.BytesIO(wire))


def require_offline_network():
    device = Path("/proc/net/dev").read_text().splitlines()[2:]
    interfaces = {line.split(":", 1)[0].strip() for line in device if ":" in line}
    if interfaces != {"lo"} or Path("/proc/net/route").read_text().splitlines()[1:]:
        raise ValueError("outer no-egress network namespace required")


class StreamingOfflineExchange:
    """One fixed synthetic exchange. Accepts no provider, URL or transport callback."""

    def __init__(self, catalog, wire):
        from scripts.kilo_owner_gate import approved_catalog

        if not approved_catalog(catalog):
            raise ValueError("fixture requires exact free catalog")
        if type(wire) is not bytes or len(wire) > HEADER_LIMIT + BODY_LIMIT + 12 * CHUNK_COUNT_LIMIT:
            raise ValueError("fixture bounds exceeded")
        self._wire = wire
        self._permit = Permit()
        self.attempts = 0

    def __call__(self, body):
        from scripts.kilo_owner_gate import prepare_request

        prepare_request(body)
        if not self._permit.take():
            raise ValueError("offline exchange already attempted")
        self.attempts += 1
        return inspect_fixture(self._wire)
