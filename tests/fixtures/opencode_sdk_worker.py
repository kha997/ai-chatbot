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
LOG_MARKS = {
    "cli_instance": b"creating instance",
    "cli_config_loaded": b"loaded custom config",
    "cli_event_connected": b"event connected",
    "cli_shell_initialized": b"shell tool using shell",
    "cli_project_refreshed": b"project copy refresh done",
    "cli_provider_stream": b"message=stream providerID=local-ollama",
    "cli_sdk_selected": b"llm.runtime=ai-sdk llm.provider=local-ollama",
    "cli_stream_error": b"stream error",
    "cli_disposing": b"disposing instance",
}
EVENT_MARKS = {
    "cli_step_started": b'"type":"step_start"',
    "cli_text": b'"type":"text"',
    "cli_step_finished": b'"type":"step_finish"',
}


def record_marks(buffer, markers, phases):
    for name, token in markers.items():
        if name not in phases and token in buffer:
            phases[name] = time.monotonic_ns()


def deadline_state(process, open_pipes):
    status = process.poll()
    snapshot = {"exit_before_kill": status, "open_pipes": sorted(open_pipes)}
    if status is None:
        try:
            lines = Path(f"/proc/{process.pid}/status").read_text().splitlines()
            for key in ("State", "Threads"):
                value = next(line.split(":", 1)[1].split()[0] for line in lines if line.startswith(key + ":"))
                snapshot[key.lower()] = int(value) if key == "Threads" else value
        except (OSError, StopIteration, ValueError):
            pass
    return snapshot


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
    phases = {"cli_spawn_requested": time.monotonic_ns()}
    deadline = time.monotonic() + TIMEOUT
    at_deadline = None
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as process, selectors.DefaultSelector() as reader:
        phases["cli_spawned"] = time.monotonic_ns()
        output = {pipe: bytearray() for pipe in (process.stdout, process.stderr)}
        streams = {process.stdout: ("stdout", EVENT_MARKS), process.stderr: ("stderr", LOG_MARKS)}
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
                    name, markers = streams[key.fileobj]
                    buffer = output[key.fileobj]
                    data = os.read(key.fd, min(4096, CAP + 1 - len(buffer)))
                    if not data:
                        reader.unregister(key.fileobj)
                        phases[f"cli_{name}_eof"] = time.monotonic_ns()
                    buffer.extend(data)
                    record_marks(buffer, markers, phases)
                    if len(buffer) > CAP:
                        over_limit = True
                        break
            if over_limit:
                kill()
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            phases["cli_watchdog"] = time.monotonic_ns()
            at_deadline = deadline_state(process, (streams[key.fileobj][0] for key in reader.get_map().values()))
            kill()
            process.wait(timeout=1)
        except BaseException:
            kill()
            raise
        phases["cli_exit_observed"] = time.monotonic_ns()
        raw, stderr = output[process.stdout], output[process.stderr]
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(json.dumps({"exit": process.returncode, "timeout": timed_out, "boundary": True,
                      "output_cap": over_limit, "stdout_bytes": len(raw),
                      "stderr_bytes": len(stderr), "reaped": not Path(f"/proc/{process.pid}").exists(),
                      "sdk_runtime": b'llm.runtime=ai-sdk llm.provider=local-ollama' in stderr,
                      "phase_ns": phases, "at_deadline": at_deadline,
                      "child_cpu_seconds": round(usage.ru_utime + usage.ru_stime, 3),
                      "tool_events": sum(is_tool_event(line) for line in raw.splitlines()),
                      "fixture_stdout": raw.decode("utf-8", errors="replace")}))


if __name__ == "__main__":
    main()
