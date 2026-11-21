"""Pinned ELF replays and memory comparison. The outer network namespace is mandatory."""

import contextlib
import io
import json
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kilo_gate15 import MODEL, run
from scripts.kilo_sse_stream import StreamingOfflineExchange, inspect_response, require_offline_network
from test_kilo_sse import DELTAS, VALID, stream
from test_kilo_sse_stream import http_wire, large_sse


def fixtures(name):
    if name in ("32769", "65536", "131072", "262144"):
        return http_wire(large_sse(int(name)), chunk_size=997), "complete"
    if name == "large-trailing":
        return http_wire(large_sse(65536) + stream(DELTAS[0])), "data_after_done"
    if name == "large-truncated":
        return http_wire(large_sse(131072), chunk_size=277)[:-1], "invalid_http_framing"
    if name == "large-event":
        return http_wire(b"data: " + b"m" * 8192 + b"\n\n" + large_sse(65536)), "frame_cap"
    if name == "small":
        return http_wire(VALID), "complete"
    raise ValueError("unknown fixture")


def replay(archive, sandbox, name):
    wire, expected = fixtures(name)
    catalog = {"data": [{"id": MODEL, "pricing": {"prompt": 0, "completion": 0}}]}
    exchange = StreamingOfflineExchange(catalog, wire)
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        harness_exit = run(archive, "stream-mock", sandbox=sandbox, exchange=exchange)
    result = json.loads(log.getvalue())
    result.update(fixture=name, simulated_posts=exchange.attempts, real_posts=result["forwarded"],
                  harness_exit=harness_exit)
    print(json.dumps(result))
    success = expected == "complete"
    safe = (result["boundary_check"] and result["streams_closed"] and result["auxiliary_denied"]
            and result["duplicate_denied"] and result["simulated_posts"] == 1 and result["real_posts"] == 0
            and not result.get("output_cap") and not result.get("timeout"))
    outcome = (result["protocol"]["classification"] == expected and bool(result["result"]) == success
               and result["exit"] == int(not success) and harness_exit == int(not success))
    if success:
        outcome = outcome and result["cli"]["step_finish"] == 1
    else:
        outcome = outcome and result["cli"]["error"] >= 1 and result["protocol"]["relay_bytes"] == 0
    return int(not (safe and outcome))


def benchmark():
    # Both routes use the same validator. Fixture generation and import costs are outside the measurement.
    for size in (32768, 65536, 131072, 262144):
        wire = http_wire(large_sse(size), chunk_size=997)
        for whole in (False, True):
            elapsed, peaks = [], []
            for _ in range(7):
                source = io.BytesIO(wire)
                tracemalloc.start()
                start = time.perf_counter()
                if whole:
                    source = io.BytesIO(b"".join(iter(lambda: source.read(4096), b"")))
                result = inspect_response(source)
                elapsed.append((time.perf_counter() - start) * 1000)
                peaks.append(tracemalloc.get_traced_memory()[1])
                tracemalloc.stop()
                if result["status"] != 200:
                    raise ValueError("benchmark fixture was rejected")
            print(json.dumps({"body_bytes": size, "method": "whole-body" if whole else "pull",
                              "median_ms": round(statistics.median(elapsed), 2), "max_peak_bytes": max(peaks),
                              "relay_bytes": result["protocol"]["relay_bytes"]}))
    return 0


if __name__ == "__main__":
    require_offline_network()
    if sys.argv[1:] == ["--benchmark"]:
        raise SystemExit(benchmark())
    if len(sys.argv) == 4:
        raise SystemExit(replay(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
    raise SystemExit("usage: run_kilo_sse_stream.py ARCHIVE BWRAP FIXTURE or --benchmark")
