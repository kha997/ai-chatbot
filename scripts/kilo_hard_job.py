"""A bounded one-shot worker for cancellable Linux I/O."""

import ctypes
import json
import os
import signal
import tempfile
import time

RESULT_LIMIT = 64 * 1024
STOP_SECONDS = 1
MAX_SECONDS = 60


class HardJob:
    """Run one blocking operation in a killable process group, outside relay threads."""

    def __init__(self, operation):
        self.result = tempfile.TemporaryFile(dir="/tmp")
        waiter, trigger = os.pipe()
        self.trigger = trigger
        self.used = False
        self.status = None
        parent = os.getpid()
        try:
            self.pid = os.fork()
        except BaseException:
            os.close(waiter)
            os.close(trigger)
            self.result.close()
            raise
        if self.pid == 0:
            try:
                os.close(trigger)
                os.setsid()
                if ctypes.CDLL(None).prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent:
                    os._exit(2)
                if os.read(waiter, 1) != b"1":
                    os._exit(2)
                os.close(waiter)
                result = json.dumps(operation(), ensure_ascii=False).encode("utf-8")
                if len(result) > RESULT_LIMIT:
                    os._exit(3)
                self.result.write(result)
                self.result.flush()
                os._exit(0)
            except BaseException:
                os._exit(4)
        os.close(waiter)

    def poll_until(self, deadline):
        while self.status is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            finished = os.waitid(os.P_PID, self.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if finished is not None:
                # The unreaped leader still owns its PID. Kill remaining group members even
                # when the operation exited early, before the leader PID can be reused.
                self.kill_group()
                _, self.status = os.waitpid(self.pid, 0)
                break
            time.sleep(min(0.005, remaining))
        return True

    def kill_group(self):
        try:
            os.killpg(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def stop(self):
        if self.status is not None:
            return
        self.kill_group()
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if not self.poll_until(time.monotonic() + STOP_SECONDS):
            raise RuntimeError("timed-out process could not be reaped")

    def run(self, seconds):
        if not 0 < seconds <= MAX_SECONDS:
            raise ValueError("invalid worker deadline")
        if self.used or self.trigger is None:
            raise ValueError("job already used or closed")
        self.used = True
        start = time.monotonic()
        try:
            os.write(self.trigger, b"1")
        except BrokenPipeError:
            pass
        finally:
            os.close(self.trigger)
            self.trigger = None
        completed = self.poll_until(start + seconds)
        if not completed:
            self.stop()
        code = os.waitstatus_to_exitcode(self.status)
        receipt = {"outcome": "complete" if completed and code == 0 else (
            "worker_failed" if completed else "hard_timeout"), "limit_ms": round(seconds * 1000),
            "elapsed_ms": round((time.monotonic() - start) * 1000),
            "signal": -code if code < 0 else None, "reaped": True}
        if completed and code == 0:
            raw = os.pread(self.result.fileno(), RESULT_LIMIT + 1, 0)
            receipt["result"] = json.loads(raw)
        return receipt

    def close(self):
        try:
            self.stop()
        finally:
            if self.trigger is not None:
                os.close(self.trigger)
                self.trigger = None
            self.result.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
