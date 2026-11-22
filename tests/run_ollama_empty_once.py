"""Issue #34 only: the exact sandbox preflight and optional single empty-store run."""

import errno
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time

SELF = Path(__file__).resolve()
BIN = Path("/usr/bin/ollama")
BIN_SHA = "cd0f8bac72d0441ae75bdb182f1f75a7b8dfa63f2e1d16bc31fa570523b1d7c9"
STORE = Path("/mnt/d/ProjectData/AIChatBot/ollama-empty-test")
GPU = ("/dev/dxg", "/dev/dri/card0", "/dev/dri/renderD128", "/dev/nvidia0",
       "/dev/nvidiactl", "/dev/nvidia-uvm", "/dev/kfd")
DEV = {"null": (1, 3), "zero": (1, 5), "full": (1, 7), "random": (1, 8),
       "urandom": (1, 9), "tty": (5, 0)}
LIB = Path("/usr/lib/x86_64-linux-gnu")
LOADER = (Path("/usr/lib64/ld-linux-x86-64.so.2"), LIB / "ld-linux-x86-64.so.2")
LIBS = tuple(LIB / x for x in ("libc.so.6", "libdl.so.2", "libpthread.so.0", "libm.so.6",
                             "libresolv.so.2", "libstdc++.so.6", "libgcc_s.so.1",
                             "libexpat.so.1", "libz.so.1"))
BUDGET = {"cpu.max": "100000 100000", "memory.max": "1073741824", "memory.swap.max": "0", "pids.max": "64"}


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def inode(path):
    info = Path(path).stat()
    return info.st_dev, info.st_ino


def audit(outer_net, private_net):
    proc = Path("/proc")
    require(inode(proc / "self/ns/net")[1] == private_net != outer_net, "wrong network namespace")
    interfaces = {row.split(":")[0].strip() for row in Path("/proc/net/dev").read_text().splitlines()[2:]}
    require(interfaces == {"lo"}, "unexpected interfaces")
    mounts = {row.split()[4]: row.split() for row in (proc / "self/mountinfo").read_text().splitlines()}
    expected = {"/", "/dev", "/dev/pts", "/proc", "/tmp", "/store", "/probe.py", str(BIN),
                "/usr/bin/python3", "/usr/lib/python3.12", *(f"/dev/{x}" for x in DEV),
                *(str(x) for x in (*LIBS, *LOADER))}
    require(set(mounts) == expected, f"unexpected mount inventory: {sorted(mounts)}")
    for path, row in mounts.items():
        fs = row[row.index("-") + 1]
        if path == "/store":
            require(fs == "9p" and row[3].endswith("/ProjectData/AIChatBot/ollama-empty-test")
                    and "rw" in row[5].split(","), "wrong D: store mount")
        elif path not in ("/proc", "/dev", "/dev/pts", "/tmp", *(f"/dev/{x}" for x in DEV)):
            require("ro" in row[5].split(","), f"writable mount: {path}")
    require(mounts["/dev"][mounts["/dev"].index("-") + 1] == "tmpfs", "not a private /dev")
    for path in ("/init", "/mnt", "/sys", "/run", "/var/run", "/home", "/usr/lib/wsl", "/usr/lib/ollama"):
        require(not os.path.lexists(path), f"host path present: {path}")
    require("WSL_INTEROP" not in os.environ, "interop environment exposed")
    for path in GPU:
        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC)
        except OSError as error:
            require(error.errno in (errno.ENOENT, errno.EACCES, errno.EPERM, errno.ENODEV), str(error))
        else:
            os.close(fd)
            raise RuntimeError("GPU open succeeded")
    allowed_devices = set()
    for name, entry in DEV.items():
        info = (Path("/dev") / name).stat()
        require(stat.S_ISCHR(info.st_mode) and (os.major(info.st_rdev), os.minor(info.st_rdev)) == entry,
                "unexpected /dev identity")
        allowed_devices.add(info.st_rdev)
    for task in proc.iterdir():
        if not task.name.isdecimal():
            continue
        try:
            for name in ("mnt", "user", "pid", "net"):
                require(inode(task / "ns" / name) == inode(proc / "self/ns" / name), "foreign process namespace")
            require(inode(task / "root") == inode("/"), "foreign process root")
            status = dict(line.split(":", 1) for line in (task / "status").read_text().splitlines())
            require(int(status["CapEff"], 16) == int(status["CapBnd"], 16) == 0 and
                    int(status["NoNewPrivs"]) == 1, "unexpected process capability")
            for fd in (task / "fd").iterdir():
                try:
                    desc = fd.stat()
                except FileNotFoundError:
                    continue
                require(not stat.S_ISBLK(desc.st_mode) and
                        (not stat.S_ISCHR(desc.st_mode) or desc.st_rdev in allowed_devices), "unexpected device FD")
        except FileNotFoundError:
            require(not task.exists(), "process audit incomplete")


def child(mode, outer_net, private_net, started):
    audit(outer_net, private_net)
    require(os.readlink("/proc/self/fd/0") == "/dev/null" and
            all(os.readlink(f"/proc/self/fd/{fd}").startswith("pipe:[") for fd in (1, 2)),
            "unexpected supervisor standard FD")
    with socket.socket() as s:
        s.settimeout(1)
        require(s.connect_ex(("127.0.0.1", 11434)) == errno.ECONNREFUSED, "shared endpoint exposed")
    require(not list(Path("/store").iterdir()), "nonempty model store")
    probe = Path("/store/.issue34-dry-probe")
    with probe.open("xb") as file:
        file.write(b"dry-probe")
    probe.unlink()
    with BIN.open("rb") as file:
        require(hashlib.file_digest(file, "sha256").hexdigest() == BIN_SHA, "wrong Ollama ELF")
    print('PREFLIGHT exact boundary passed', flush=True)
    if mode == "preflight":
        return
    # Leave room for the independent 25 s unit timer and final cleanup.
    require(time.monotonic() - started < 2.5, "insufficient supervisor time before Ollama startup")
    with subprocess.Popen([str(BIN), "serve"], stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True) as daemon:
        print("STARTED 1", flush=True)
        try:
            for _ in range(100):
                require(daemon.poll() is None, "daemon exited during startup")
                listening = [row.split()[1] for table in ("tcp", "tcp6")
                             for row in Path("/proc/net", table).read_text().splitlines()[1:]
                             if row.split()[3] == "0A"]
                if listening:
                    require(listening == ["0100007F:2CAC"], f"unexpected listening sockets: {listening}")
                    break
                time.sleep(0.15)
            else:
                raise RuntimeError("private listener did not become ready")
            audit(outer_net, private_net)
            require(inode(f"/proc/{daemon.pid}/exe") == inode(BIN), "daemon ELF identity changed")
            print("AUDIT exact daemon boundary passed", flush=True)
            for path, expected in (("/api/version", {"version": "0.31.1"}), ("/api/tags", {"models": []})):
                print(f"GET {path}", flush=True)
                conn = http.client.HTTPConnection("127.0.0.1", 11436, timeout=2)
                try:
                    conn.request("GET", path, headers={"Connection": "close"})
                    response = conn.getresponse()
                    require(response.status == 200 and json.loads(response.read(8192)) == expected,
                            f"unexpected response: {path}")
                finally:
                    conn.close()
                print(f"HTTP 200 {path}", flush=True)
            audit(outer_net, private_net)
            contents = sorted(path.name for path in Path("/store").iterdir())
            require(all(name in ("blobs", "manifests") for name in contents), "unexpected store contents")
            print("STORE " + json.dumps(contents), flush=True)
        finally:
            if daemon.poll() is None:
                daemon.kill()
            daemon.wait(timeout=2)


def enter(mode, bwrap, outer_net, started):
    from run_ollama_local_mock import require_loopback
    from scripts.kilo_gate15 import emit_filter

    require_loopback()
    group = Path("/proc/self/cgroup").read_text().strip().removeprefix("0::/")
    limits = {name: (Path("/sys/fs/cgroup") / group / name).read_text().strip() for name in BUDGET}
    require(limits == BUDGET, "effective cgroup mismatch")
    print("CGROUP " + group, flush=True)
    with tempfile.TemporaryFile(dir="/tmp") as seccomp:
        emit_filter(seccomp)
        readonly = (BIN, Path("/usr/bin/python3"), Path("/usr/lib/python3.12"), *LIBS, *LOADER)
        mounts = [item for path in readonly for item in ("--ro-bind", str(path.resolve()), str(path))]
        variables = {"HOME": "/tmp", "PATH": "/usr/bin", "OLLAMA_MODELS": "/store",
                     "OLLAMA_HOST": "127.0.0.1:11436", "OLLAMA_NO_CLOUD": "1", "OLLAMA_NOPRUNE": "1",
                     "CUDA_VISIBLE_DEVICES": "-1", "ROCR_VISIBLE_DEVICES": "-1"}
        exports = [item for key, value in variables.items() for item in ("--setenv", key, value)]
        command = [bwrap, "--unshare-all", "--unshare-user", "--share-net", "--disable-userns",
                   "--new-session", "--as-pid-1",
                   "--die-with-parent", "--clearenv", "--cap-drop", "ALL", "--seccomp", str(seccomp.fileno()),
                   *mounts, "--ro-bind", str(SELF), "/probe.py", "--symlink", "usr/lib", "/lib",
                   "--symlink", "usr/lib64", "/lib64", "--size", "67108864", "--tmpfs", "/tmp",
                   "--proc", "/proc", "--dev", "/dev", "--bind", str(STORE), "/store", "--remount-ro", "/",
                   *exports, "/usr/bin/python3", "-IS", "/probe.py", "child", mode,
                   outer_net, str(inode("/proc/self/ns/net")[1]), started]
        subprocess.run(command, env={}, pass_fds=(seccomp.fileno(),), stdin=subprocess.DEVNULL, check=True)


def supervised(mode, staged, started):
    import uuid
    unit = "ai-chatbot-34-empty-" + uuid.uuid4().hex + ".service"
    argv = ["/usr/bin/systemd-run", "--user", f"--unit={unit}", "--wait", "--pipe", "--collect",
            "-p", "CPUQuota=100%", "-p", "MemoryMax=1073741824", "-p", "MemorySwapMax=0",
            "-p", "TasksMax=64", "-p", "RuntimeMaxSec=25s", "-p", "KillMode=control-group",
            "-p", "KillSignal=SIGKILL", "/usr/bin/unshare", "--user", "--map-current-user",
            "--net", "--keep-caps", "/usr/bin/bash", "-c",
            '/usr/sbin/ip link set lo up && exec /usr/bin/setpriv --bounding-set=-all '
            '--inh-caps=-all --ambient-caps=-all --no-new-privs "$@"', "bash", "/usr/bin/python3", "-Bu",
            str(SELF), "enter", mode, str(staged), str(inode("/proc/self/ns/net")[1]), str(started)]
    systemctl = ["/usr/bin/systemctl", "--user"]
    try:
        run = subprocess.run(argv, capture_output=True, text=True, timeout=26)
    finally:
        state = subprocess.run(systemctl + ["show", "-p", "LoadState", unit], capture_output=True, text=True, timeout=1)
        if "LoadState=not-found" not in state.stdout:
            subprocess.run(systemctl + ["stop", unit], capture_output=True, timeout=1)
            state = subprocess.run(systemctl + ["show", "-p", "LoadState", unit],
                                   capture_output=True, text=True, timeout=1)
        require("LoadState=not-found" in state.stdout, "unit still present")
    print(run.stdout, end="", flush=True)
    print(run.stderr, end="", file=sys.stderr, flush=True)
    for line in run.stdout.splitlines():
        if line.startswith("CGROUP "):
            require(not (Path("/sys/fs/cgroup") / line.split()[1]).exists(), "cgroup still present")
    require(run.returncode == 0 and "PREFLIGHT exact boundary passed" in run.stdout, "supervised run failed")
    if mode != "preflight":
        require(run.stdout.count("STARTED 1") == 1 and
                all(run.stdout.count(f"HTTP 200 /api/{path}") == 1 for path in ("version", "tags")),
                "execution receipt incomplete")


def main(mode, pinned):
    from run_ollama_local_mock import stage_sandbox

    marker = SELF.parents[2] / "issue34-start-7072288797.reservation"
    require(mode in ("preflight", "execute-7072288797"), "invalid mode")
    require(not marker.exists(), "one-use reservation already exists")
    require(STORE.resolve(strict=True) == STORE and not list(STORE.iterdir()), "invalid store")
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="issue34-empty-", dir="/tmp") as temp:
        staged = stage_sandbox(Path(pinned), Path(temp) / "bwrap")
        if mode == "execute-7072288797":
            with marker.open("x") as record:
                record.write("One attempt armed under Issue #34 / 7072288797. Do not retry.\n")
                record.flush()
                os.fsync(record.fileno())
        supervised(mode, staged, start)
    require(not Path(temp).exists(), "sandbox scratch remains")
    print(f"supervised_seconds={time.monotonic()-start:.6f}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "child":
        child(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
    elif sys.argv[1] == "enter":
        enter(*sys.argv[2:])
    else:
        main(*sys.argv[1:])
