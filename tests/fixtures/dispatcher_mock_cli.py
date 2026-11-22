"""Deterministic CLI fixture. It has no provider client or shell tools."""

import json
import os
from pathlib import Path
import resource
import socket
import sys
import time


def verify_boundary():
    if (os.environ.get("GH_TOKEN") is not None or Path(os.environ["HOST_CANARY"]).exists()
            or any(Path(p).exists() for p in ("/home", "/mnt", "/init", "/usr/bin/bash"))
            or str(Path("/proc/self/ns/net").stat().st_ino) == os.environ["HOST_NETNS"]):
        raise RuntimeError("mock boundary failed")
    try:
        Path("write-probe").write_bytes(b"mock")
    except OSError:
        pass
    else:
        raise RuntimeError("workspace writable")
    try:
        with socket.create_connection(("203.0.113.1", 443), timeout=0.2):
            raise RuntimeError("unexpected external connectivity")
    except OSError:
        pass


def main(case):
    resource.setrlimit(resource.RLIMIT_FSIZE, (4097, 4097))
    verify_boundary()
    print("mock-boundary-ok", file=sys.stderr, flush=True)
    if case == "timeout":
        time.sleep(20)
    if case == "output-cap":
        os.write(sys.stdout.fileno(), b"x" * 8192)
        return 1
    if case == "nonzero":
        return 6
    records = json.loads(Path("records.json").read_text(encoding="ascii"))
    answer = {"catalog": records.count("catalog"), "handoff": records.count("handoff"), "total": len(records)}
    if case == "bad-oracle":
        answer["total"] = True
    print(json.dumps(answer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
