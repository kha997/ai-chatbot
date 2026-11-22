"""Bound the installed OpenCode process inside the Issue #34 sandbox."""

import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

CAP = 32768
TIMEOUT = 24


def is_tool_event(line):
    try:
        event = json.loads(line)
    except ValueError:
        return False
    return isinstance(event, dict) and event.get("type") == "tool_use"


def main():
    if (Path("/mnt").exists() or Path("/home").exists() or Path("/dev/dxg").exists()
            or any(Path("/dev").glob("nvidia*")) or Path(os.environ["HOST_CANARY"]).exists()
            or {"GH_TOKEN", "OPENAI_API_KEY", "WSL_INTEROP", "HTTPS_PROXY"} & os.environ.keys()
            or str(Path("/proc/self/ns/net").stat().st_ino) != os.environ["FIXTURE_NETNS"]):
        raise RuntimeError("Issue #34 sandbox boundary failed")
    resource.setrlimit(resource.RLIMIT_NOFILE, (96, 96))
    resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))
    resource.setrlimit(resource.RLIMIT_CPU, (8, 10))
    # Bound Bun startup parallelism on large WSL hosts within the fixed task budget.
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    spec = json.loads(Path("/fixture/run.json").read_text())
    # OpenCode adds literal quotes around any positional argument containing spaces.
    argv = ["/usr/bin/opencode", "run", "--pure", "--print-logs", "--log-level", "DEBUG", "--format", "json",
            "--title", "Issue #34 synthetic mock", "--model", spec["model"], "--agent", "fixture",
            "--", *spec["prompt"].split(" ")]
    deadline = time.monotonic() + TIMEOUT
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as process, selectors.DefaultSelector() as reader:
        output = {pipe: bytearray() for pipe in (process.stdout, process.stderr)}
        for pipe in output:
            reader.register(pipe, selectors.EVENT_READ)
        timed_out, over_limit = False, False

        def kill():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:
            while reader.get_map() and not over_limit:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv[0], TIMEOUT)
                for key, _ in reader.select(remaining):
                    buffer = output[key.fileobj]
                    data = os.read(key.fd, min(4096, CAP + 1 - len(buffer)))
                    if not data:
                        reader.unregister(key.fileobj)
                    buffer.extend(data)
                    if len(buffer) > CAP:
                        over_limit = True
                        break
            if over_limit:
                kill()
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            kill()
            process.wait(timeout=1)
        except BaseException:
            kill()
            raise
        raw, stderr = output[process.stdout], output[process.stderr]
    print(json.dumps({"exit": process.returncode, "timeout": timed_out, "boundary": True,
                      "output_cap": over_limit, "stdout_bytes": len(raw),
                      "stderr_bytes": len(stderr), "reaped": not Path(f"/proc/{process.pid}").exists(),
                      "sdk_runtime": b'llm.runtime=ai-sdk llm.provider=local-ollama' in stderr,
                      "tool_events": sum(is_tool_event(line) for line in raw.splitlines()),
                      "fixture_stdout": raw.decode("utf-8", errors="replace")}))


if __name__ == "__main__":
    main()
