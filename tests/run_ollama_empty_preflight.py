"""Exercise the Issue #34 boundary using Python children only."""

import errno
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid

SELF = Path(__file__).resolve()
PYTHON = "/usr/bin/python3"
BUDGET = {"cpu.max": "100000 100000", "memory.max": "1073741824",
          "memory.swap.max": "0", "pids.max": "64"}
GPU_PATHS = ("/dev/dxg", "/dev/dri/card0", "/dev/dri/renderD128", "/dev/nvidia0",
             "/dev/nvidiactl", "/dev/nvidia-uvm", "/dev/kfd")
CASE_NAMES = ("quick", "blocked_io", "busy_children")


def check(condition, error):
    if not condition:
        raise RuntimeError(error)


def namespace(name):
    return Path(f"/proc/self/ns/{name}").stat().st_ino


def child(mode, outer, private_net):
    namespaces = {name: namespace(name) for name in ("mnt", "pid", "net")}
    check(all(namespaces[name] != outer[name] for name in namespaces), "namespace was inherited")
    check(namespaces["net"] == private_net, "unexpected private network")
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    check(int(status["CapEff"], 16) == int(status["CapBnd"], 16) == 0
          and int(status["NoNewPrivs"]) == 1, "unexpected privileges")
    mounts = {line.split()[4]: line.split(" - ")[1].split()[0]
              for line in Path("/proc/self/mountinfo").read_text().splitlines()}
    check(mounts["/dev"] == "tmpfs" and mounts["/proc"] == "proc"
          and not any(path.startswith(("/dev/dxg", "/dev/nvidia", "/dev/dri", "/dev/kfd"))
                      for path in mounts), "unexpected GPU or host-device mount")
    check(not any(Path(path).exists() for path in ("/mnt", "/home", "/run", "/var/run", "/usr/lib/wsl")),
          "host paths visible")
    fds = {}
    for fd in Path("/proc/self/fd").iterdir():
        try:
            fds[int(fd.name)] = os.readlink(fd)
        except FileNotFoundError:
            continue  # The directory enumeration FD closes before inspection.
    check(set(fds) == {0, 1, 2} and fds[0] == "/dev/null"
          and all(fds[fd].startswith("pipe:[") for fd in (1, 2)), "unexpected inherited FD")
    denials = {}
    for path in GPU_PATHS:
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError as error:
            check(error.errno in (errno.ENOENT, errno.EACCES, errno.EPERM, errno.ENODEV),
                  f"unexpected open error for {path}")
            denials[path] = errno.errorcode[error.errno]
        else:
            os.close(fd)
            raise RuntimeError(f"GPU path was accessible: {path}")
    with socket.socket() as sock:
        sock.settimeout(1)
        check(sock.connect_ex(("127.0.0.1", 11434)) == errno.ECONNREFUSED, "unexpected Ollama route")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 11436))
        listener.listen()
        print("PROBE " + json.dumps({"gpu_open_denied": denials, "fds": sorted(fds),
                                    "mountpoints": sorted(mounts), "private_dev": mounts["/dev"],
                                    "namespace": namespaces,
                                    "host_11434": "ECONNREFUSED", "socket_bound": True}), flush=True)
        if mode == "quick":
            return
        if mode == "blocked_io":
            listener.accept()
        os.fork()
        print("CHILD", flush=True)
        while True:
            pass


def sandbox(mode, bwrap, outer):
    from run_ollama_local_mock import require_loopback
    from scripts.kilo_gate15 import emit_filter

    require_loopback()
    group = Path("/proc/self/cgroup").read_text().strip().removeprefix("0::/")
    limits = {key: (Path("/sys/fs/cgroup") / group / key).read_text().strip() for key in BUDGET}
    check(limits == BUDGET, "effective cgroup limits differ")
    print("CGROUP " + json.dumps({"path": group, "limits": limits}), flush=True)
    with tempfile.TemporaryFile(dir="/tmp") as seccomp:
        emit_filter(seccomp)
        cmd = [bwrap, "--unshare-all", "--unshare-user", "--share-net", "--disable-userns",
               "--new-session", "--die-with-parent", "--clearenv", "--cap-drop", "ALL",
               "--seccomp", str(seccomp.fileno()), "--ro-bind", PYTHON, PYTHON,
               "--ro-bind", "/usr/lib/python3.12", "/usr/lib/python3.12",
               "--ro-bind", "/usr/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu",
               "--ro-bind", "/usr/lib64", "/usr/lib64", "--symlink", "usr/lib", "/lib",
               "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev",
               "--size", "67108864", "--tmpfs", "/tmp", "--setenv", "HOME", "/tmp",
               "--ro-bind", str(SELF), "/probe.py", PYTHON, "-IS", "/probe.py",
               "child", mode, outer, str(namespace("net"))]
        subprocess.run(cmd, env={}, stdin=subprocess.DEVNULL, pass_fds=(seccomp.fileno(),), check=True)


def run_case(mode, bwrap):
    from run_ollama_local_mock import stage_sandbox

    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="issue34-preflight-", dir="/tmp") as scratch:
        pinned = stage_sandbox(bwrap, Path(scratch) / "bwrap")
        receipt = run_service(mode, pinned)
    check(not Path(scratch).exists(), "fixture scratch remains")
    elapsed = time.monotonic() - start
    check(elapsed < 30, "whole-service budget exceeded")
    check(receipt["systemd_seconds"] < elapsed, "service runtime exceeds measured fixture time")
    print(json.dumps(receipt | {"elapsed_seconds": round(elapsed, 4), "scratch_removed": True}),
          flush=True)


def run_service(mode, bwrap):
    unit = f"ai-chatbot-34-{uuid.uuid4().hex}.service"
    outer = json.dumps({name: namespace(name) for name in ("mnt", "pid", "net")})
    env = os.environ | {"LC_ALL": "C"}
    command = ["/usr/bin/systemd-run", "--user", f"--unit={unit}", "--collect", "--wait", "--pipe",
               "-p", "CPUQuota=100%", "-p", "MemoryMax=1073741824", "-p", "MemorySwapMax=0",
               "-p", "TasksMax=64", "-p", "RuntimeMaxSec=25s", "-p", "KillMode=control-group",
               "-p", "KillSignal=SIGKILL", "/usr/bin/unshare", "--user", "--map-current-user",
               "--net", "--keep-caps", "/usr/bin/bash", "-c",
               '/usr/sbin/ip link set lo up && exec /usr/bin/setpriv --bounding-set=-all '
               '--inh-caps=-all --ambient-caps=-all --no-new-privs "$@"', "bash", PYTHON,
               "-Bu", str(SELF), "sandbox", mode, str(bwrap), outer]
    try:
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=28)
    except subprocess.TimeoutExpired:
        # The in-unit 25 s SIGKILL timer is independent of the systemd-run client.
        # Also request an immediate stop if the client fails to report completion.
        subprocess.run(["/usr/bin/systemctl", "--user", "--no-block", "stop", unit],
                       capture_output=True, env=env, timeout=1)
        raise
    finally:
        state = subprocess.run(["/usr/bin/systemctl", "--user", "show", "-p", "LoadState", "-p",
                                "ActiveState", unit], capture_output=True, text=True, env=env, timeout=1)
    lines = result.stdout.splitlines()
    check("LoadState=not-found" in state.stdout and "ActiveState=inactive" in state.stdout,
          "fixture unit remains")
    group = json.loads(next(line.removeprefix("CGROUP ") for line in lines if line.startswith("CGROUP ")))
    receipt = json.loads(next(line.removeprefix("PROBE ") for line in lines if line.startswith("PROBE ")))
    check(not (Path("/sys/fs/cgroup") / group["path"]).exists(), "fixture cgroup remains")
    timed_out = mode != "quick"
    check((result.returncode != 0 and "result: timeout" in result.stderr and "status=KILL" in result.stderr)
          if timed_out else (result.returncode == 0), f"unexpected service outcome: {result.stderr}")
    check(lines.count("CHILD") == (2 if mode == "busy_children" else 0), "child test did not start")
    runtime = re.search(r"^Service runtime: (\d+(?:\.\d+)?)(us|ms|s)$", result.stderr, re.MULTILINE)
    check(runtime is not None, "unexpected systemd runtime format")
    seconds = float(runtime[1]) * {"us": 0.000001, "ms": 0.001, "s": 1}[runtime[2]]
    return receipt | {"case": mode, "systemd_seconds": seconds, "limits": group["limits"],
                      "killed": timed_out, "unit_and_cgroup_gone": True}


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2], json.loads(sys.argv[3]), int(sys.argv[4]))
    elif sys.argv[1] == "sandbox":
        sandbox(*sys.argv[2:])
    else:
        for case in CASE_NAMES:
            run_case(case, Path(sys.argv[1]))
