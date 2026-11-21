import ctypes
import json
import os
from pathlib import Path
import signal
import socket
import tempfile
from threading import Timer
import time
import unittest

from kilo_tls_fixture import EXPECTED, certificates, peer
from scripts.kilo_activate import fixed_body
from scripts.kilo_gate15 import MODEL, json_reply, send_relay_reply
from scripts.kilo_tls_offline import TLS_SECONDS, HardJob, LocalTLSExchange, require_loopback


def require_test_namespace():
    try:
        require_loopback()
    except (OSError, ValueError):
        raise unittest.SkipTest("requires isolated WSL loopback namespace")


def catalogue():
    return {"data": [{"id": MODEL, "pricing": {"prompt": 0, "completion": 0}}]}


def live_tcp():
    return sum(1 for table in ("tcp", "tcp6")
               for line in Path(f"/proc/net/{table}").read_text().splitlines()[1:]
               if line.split()[3] in ("01", "0A"))


def socket_counts():
    return (len(os.listdir("/proc/self/fd")), live_tcp(),
            len(Path("/proc/net/unix").read_text().splitlines()) - 1)


class HardCancellationTests(unittest.TestCase):
    def setUp(self):
        require_test_namespace()

    def test_blocking_unix_read_is_killed_and_reaped(self):
        require_loopback()
        left, right = socket.socketpair(socket.AF_UNIX)
        with left, right, HardJob(lambda: left.recv(1)) as worker:
            receipt = worker.run(0.20)
            self.assertEqual(receipt["outcome"], "hard_timeout")
            self.assertEqual(receipt["signal"], 9)
            self.assertGreaterEqual(receipt["elapsed_ms"], 170)
            self.assertLess(receipt["elapsed_ms"], 1200)
            with self.assertRaises(ChildProcessError):
                os.waitpid(worker.pid, os.WNOHANG)
            with self.assertRaises(ValueError):
                worker.run(0.20)

    def test_full_unix_bridge_write_and_peer_exit(self):
        before = len(os.listdir("/proc/self/fd"))
        for abort_peer in (False, True):
            with self.subTest(abort_peer=abort_peer):
                left, right = socket.socketpair(socket.AF_UNIX)
                with left, right:
                    left.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                    left.setblocking(False)
                    with self.assertRaises(BlockingIOError):
                        for _ in range(128):
                            left.send(b"x" * 1024)
                    left.setblocking(True)

                    def write():
                        try:
                            send_relay_reply(left, json_reply(502))
                            return "unexpected_delivery"
                        except BrokenPipeError:
                            return "peer_closed"

                    with HardJob(write) as worker:
                        if abort_peer:
                            timer = Timer(0.08, right.shutdown, args=(socket.SHUT_RDWR,))
                            timer.start()
                            try:
                                receipt = worker.run(0.26)
                            finally:
                                timer.join()
                            self.assertEqual(receipt["result"], "peer_closed")
                        else:
                            receipt = worker.run(0.26)
                            self.assertEqual((receipt["outcome"], receipt["signal"]), ("hard_timeout", 9))
                        self.assertTrue(receipt["reaped"])
                        self.assertLess(receipt["elapsed_ms"], 1200)
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_process_group_kills_blocked_parent_and_grandchild(self):
        # Keep proof of the orphan's exit in this test process rather than delegating it to PID 1.
        libc = ctypes.CDLL(None)
        self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
        try:
            for early_exit in (True, False):
                with self.subTest(early_exit=early_exit), tempfile.TemporaryFile() as record:
                    def group():
                        pid = os.fork()
                        if pid == 0:
                            signal.signal(signal.SIGTERM, signal.SIG_IGN)
                            while True:
                                signal.pause()
                        os.write(record.fileno(), str(pid).encode("ascii"))
                        if early_exit:
                            os._exit(7)
                        os.waitpid(pid, 0)

                    with HardJob(group) as worker:
                        receipt = worker.run(0.30)
                        descendant = int(os.pread(record.fileno(), 32, 0))
                        self.assertEqual(receipt["outcome"], "worker_failed" if early_exit else "hard_timeout")
                        deadline = time.monotonic() + 1
                        while time.monotonic() < deadline:
                            pid, status = os.waitpid(descendant, os.WNOHANG)
                            if pid:
                                self.assertEqual(os.waitstatus_to_exitcode(status), -9)
                                break
                            time.sleep(0.01)
                        else:
                            os.kill(descendant, signal.SIGKILL)
                            os.waitpid(descendant, 0)
                            self.fail("process group left a descendant alive")
        finally:
            libc.prctl(36, 0, 0, 0, 0)


class LocalTLSTests(unittest.TestCase):
    def test_socket_matrix_one_post_and_cleanup(self):
        require_test_namespace()
        before = socket_counts()
        with certificates() as cert:
            for name, (classification, posts) in EXPECTED.items():
                with self.subTest(name=name), peer(cert, name) as (port, log, process):
                    trust = None if name == "untrusted" else cert / "ca.pem"
                    with LocalTLSExchange(catalogue(), fixed_body(), port, trust) as exchange:
                        answer = exchange(fixed_body())
                        self.assertEqual(answer["protocol"]["classification"], classification)
                        self.assertEqual(exchange.attempts, 1)
                        with self.assertRaises(ValueError):
                            exchange(fixed_body())
                        receipt = exchange.receipt
                        with self.assertRaises(ChildProcessError):
                            os.waitpid(exchange.worker.pid, os.WNOHANG)
                        if classification == "hard_timeout":
                            self.assertEqual(receipt["signal"], 9)
                            self.assertGreaterEqual(receipt["elapsed_ms"], TLS_SECONDS * 1000 - 40)
                            self.assertLess(receipt["elapsed_ms"], TLS_SECONDS * 1000 + 750)
                        elif classification == "complete":
                            self.assertLess(answer["parser_peak_bytes"], 256 * 1024)
                            self.assertEqual(answer["protocol"]["usage"]["total_tokens"], 17)
                        else:
                            self.assertEqual(answer["protocol"]["relay_bytes"], 0)
                    self.assertEqual(log.read_text().splitlines(), ["accepted"] + ["post"] * posts)
                self.assertIsNotNone(process.poll())
                self.assertEqual(socket_counts(), before)
                print(json.dumps({"fixture": name, "synthetic_posts": posts, "external_posts": 0,
                                  "protocol": answer["protocol"], "worker": receipt,
                                  "parser_peak_bytes": answer.get("parser_peak_bytes"), "cleanup": True}))

    def test_rejects_price_or_wrong_body_before_connecting(self):
        require_test_namespace()
        with self.assertRaisesRegex(ValueError, "free catalog"):
            LocalTLSExchange({"data": []}, fixed_body(), 9999, None)
        with self.assertRaisesRegex(ValueError, "request shape"):
            LocalTLSExchange(catalogue(), fixed_body() | {"model": "different"}, 9999, None)

    def test_repeated_large_tls_does_not_retain_workers_or_descriptors(self):
        require_test_namespace()
        before = socket_counts()
        peaks = []
        with certificates() as cert:
            for _ in range(5):
                with peer(cert, "large") as (port, log, process):
                    with LocalTLSExchange(catalogue(), fixed_body(), port, cert / "ca.pem") as exchange:
                        answer = exchange(fixed_body())
                        self.assertEqual(answer["protocol"]["bytes"], 262144)
                        self.assertTrue(exchange.receipt["reaped"])
                        peaks.append(answer["parser_peak_bytes"])
                    self.assertEqual(log.read_text().splitlines(), ["accepted", "post"])
                self.assertIsNotNone(process.poll())
                self.assertEqual(socket_counts(), before)
        self.assertLess(max(peaks), 128 * 1024)
        print(json.dumps({"fixture": "repeated-large", "runs": len(peaks), "parser_peak_min": min(peaks),
                          "parser_peak_max": max(peaks), "same_fd_and_socket_counts": True}))
