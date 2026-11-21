"""Offline contract for a future Owner-authorized Kilo request. No network transport."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
from http.client import HTTPException, HTTPResponse
import io
import json

from scripts.kilo_gate15 import MAX_BYTES, MODEL, PROMPT, Permit

SANDBOX_SHA256 = "3acde20bf6dadc53dfa708e8c5bfb81e9564ab831b2b28216c3c976808b50520"
SANDBOX_VERSION = "0.13.1"
ARCHIVE_LIMIT = 2 * 1024 * 1024


@dataclass(frozen=True)
class Request:
    method: str
    host: str
    path: str
    headers: tuple
    body: bytes
    verify_tls: bool = True
    follow_redirects: bool = False
    retries: int = 0
    timeout_seconds: int = 20


@dataclass(frozen=True)
class FixtureReply:
    status: int
    content_type: str
    body: bytes
    content_encoding: str | None = None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def prepare_request(body):
    expected = canonical({
        "model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
        "stream": True, "max_tokens": 128, "stream_options": {"include_usage": True},
    })
    if canonical(body) != expected:
        raise ValueError("unexpected request shape")
    return Request("POST", "ai-gateway.kilo.ai", "/api/v1/chat/completions", (
        ("Content-Type", "application/json"), ("Accept", "text/event-stream"),
        ("Accept-Encoding", "identity"),
    ), expected)


def approved_catalog(catalog):
    try:
        rows = catalog["data"]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            return False
        matches = [row for row in rows if row.get("id") == MODEL]
        if len(matches) != 1 or not MODEL.endswith(":free"):
            return False
        prices = matches[0]["pricing"]
        if not isinstance(prices, dict) or not {"prompt", "completion"} <= prices.keys():
            return False
        return all(Decimal(str(value)).is_zero() for key, value in prices.items() if key != "discount")
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False


def inspect_http_fixture(wire):
    """Exercise the standard HTTP response reader without a socket or HTTP client."""
    class MemoryInput:
        def makefile(self, mode):
            return io.BytesIO(wire)

    try:
        with HTTPResponse(MemoryInput()) as response:
            response.begin()
            headers = response.headers
            metadata = {name: headers.get_all(name, []) for name in (
                "Content-Type", "Content-Encoding", "Transfer-Encoding", "Content-Length",
            )}
            if any(len(values) > 1 for values in metadata.values()):
                raise ValueError("ambiguous HTTP headers")
            transfer = headers.get("Transfer-Encoding")
            length = headers.get("Content-Length")
            if transfer and (transfer.lower() != "chunked" or length is not None):
                raise ValueError("ambiguous HTTP framing")
            if length is not None and (not length.isascii() or not length.isdecimal() or len(length) > 12):
                raise ValueError("invalid HTTP length")
            raw = response.read(MAX_BYTES + 1)
            if length is not None and len(raw) != min(int(length), MAX_BYTES + 1):
                raise ValueError("truncated HTTP body")
            return response.status, headers.get("Content-Type"), raw, headers.get("Content-Encoding")
    except HTTPException as exc:
        raise ValueError("invalid HTTP framing") from exc


def fixture_wire(fixture):
    fields = (("Content-Type", fixture.content_type), ("Content-Encoding", fixture.content_encoding))
    metadata = [f"HTTP/1.1 {fixture.status} Fixture", f"Content-Length: {len(fixture.body)}"]
    for name, value in fields:
        if value is not None:
            if "\r" in value or "\n" in value:
                raise ValueError("invalid fixture header")
            metadata.append(f"{name}: {value}")
    return ("\r\n".join(metadata) + "\r\n\r\n").encode("ascii") + fixture.body


class OfflineExchange:
    """Records one would-be POST against local response data. No connector is accepted."""

    def __init__(self, catalog, fixture):
        if not approved_catalog(catalog) or type(fixture) is not FixtureReply:
            raise ValueError("invalid free catalog or fixture")
        self.fixture = fixture
        self.permit = Permit()
        self.attempts = 0

    def __call__(self, body):
        prepare_request(body)
        if not self.permit.take():
            raise ValueError("offline exchange already attempted")
        self.attempts += 1
        return inspect_http_fixture(fixture_wire(self.fixture))


def stage_sandbox(source, target):
    """Copy and execute only the exact reviewed, non-setuid artifact in a private tempdir."""
    with source.open("rb") as file:
        image = file.read(ARCHIVE_LIMIT + 1)
    if len(image) > ARCHIVE_LIMIT or hashlib.sha256(image).hexdigest() != SANDBOX_SHA256:
        raise ValueError("sandbox digest mismatch")
    with target.open("xb") as file:
        file.write(image)
    target.chmod(0o500)
    return target


if __name__ == "__main__":
    raise SystemExit("NO_LIVE_AUTHORIZATION: this contract has no executable transport")
