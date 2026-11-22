"""Synthetic HTTP client for the isolated Ollama fixture. Never invokes a real provider."""

import json
import os
from pathlib import Path
import socket
import sys
import urllib.error
import urllib.request


def main(case):
    config = json.loads(Path("/fixture/opencode.json").read_text())
    provider = config["provider"]["local-ollama"]
    base = provider["options"]["baseURL"]
    model = config["model"].split("/", 1)[1]
    task = json.loads(Path("/fixture/packet.json").read_text())
    expected = {"catalog": 2, "handoff": 1, "total": 3}
    if (base != "http://127.0.0.1:11435/v1" or Path("/mnt").exists() or Path("/dev/dxg").exists()
            or Path(os.environ["HOST_CANARY"]).exists()
            or str(Path("/proc/self/ns/net").stat().st_ino) != os.environ["FIXTURE_NETNS"]):
        raise RuntimeError("boundary mismatch")
    try:
        Path("/fixture/write-probe").write_text("unexpected writable input")
    except OSError:
        pass
    else:
        raise RuntimeError("fixture writable")
    try:
        with socket.create_connection(("203.0.113.1", 443), timeout=0.2):
            raise RuntimeError("unexpected external route")
    except OSError:
        pass

    def http(path, body=None):
        data = None if body is None else json.dumps(body).encode("ascii")
        request = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=0.25) as response:
                return response.status, json.loads(response.read(4097))
        except urllib.error.HTTPError as exc:
            return exc.code, None

    assert http("/models") == (200, {"data": [{"id": model}]})
    assert http("/api/generate", task)[0] == 404
    assert http("/chat/completions", task | {"model": "wrong"})[0] == 403
    assert http("/chat/completions", task | {"tools": []})[0] == 403
    try:
        status, reply = http("/chat/completions", task)
    except TimeoutError:
        assert case == "timeout"
        return {"outcome": "TIMED_OUT", "oracle": None}
    assert case != "timeout" and status == 200 and reply["model"] == model
    assert reply["choices"][0]["finish_reason"] == "stop"
    value = json.loads(reply["choices"][0]["message"]["content"])
    exact = value == expected and all(type(number) is int for number in value.values())
    assert http("/chat/completions", task)[0] == 409
    assert exact == (case == "ok")
    return {"outcome": "PASS" if exact else "INVALID_ORACLE", "oracle": expected if exact else None}


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
