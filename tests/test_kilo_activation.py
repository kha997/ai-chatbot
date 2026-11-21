"""Synthetic authorization and wire fixtures. No credentials or provider requests."""

from datetime import datetime, timedelta, timezone
from http.client import HTTPResponse
import io
import os
import ssl
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scripts import kilo_activate as live
from scripts.kilo_gate15 import MODEL, relay_response
from test_kilo_sse import SSE, VALID, JSON_ERROR

SHA = "1" * 40
DIGEST = "2" * 64
RUNNER = "4" * 64
NOW = datetime(2026, 11, 21, 7, 0, tzinfo=timezone.utc)


def comment():
    return {"id": 999, "issue_url": live.ISSUE_URL, "author_association": "OWNER",
            "user": {"id": live.OWNER_ID, "login": "kha997"},
            "created_at": "2026-11-21T06:55:00Z", "updated_at": "2026-11-21T06:55:00Z",
            "body": live.approval_line(SHA, DIGEST, RUNNER, "2026-11-21T08:00:00Z")}


class ActivationTests(unittest.TestCase):
    def test_explicit_exact_owner_approval_only(self):
        self.assertTrue(live.verify_approval(comment(), 999, SHA, DIGEST, RUNNER, NOW))
        for values in ({}, comment() | {"author_association": "MEMBER"},
                       comment() | {"user": {"id": 123, "login": "kha997"}},
                       comment() | {"issue_url": live.ISSUE_URL + "0"},
                       comment() | {"updated_at": "2026-11-21T06:56:00Z"},
                       comment() | {"body": "agent:codex approved"},
                       comment() | {"body": live.approval_line(SHA, DIGEST, RUNNER, "2026-11-21T06:56:00Z")}):
            self.assertFalse(live.verify_approval(values, 999, SHA, DIGEST, RUNNER, NOW))
        self.assertFalse(live.verify_approval(comment(), 1000, SHA, DIGEST, RUNNER, NOW))
        self.assertFalse(live.verify_approval(comment(), 999, "3"*40, DIGEST, RUNNER, NOW))
        self.assertFalse(live.verify_approval(comment(), 999, SHA, "3"*64, RUNNER, NOW))
        self.assertFalse(live.verify_approval(comment(), 999, SHA, DIGEST, "5"*64, NOW))
        self.assertFalse(live.verify_approval(comment(), 999, SHA, DIGEST, RUNNER,
                                             datetime(2026, 11, 21, 8, 0, tzinfo=timezone.utc)))

    def test_only_reviewed_file_bytes(self):
        self.assertTrue(live.match_digest(b"approved", live.sha(b"approved")))
        self.assertFalse(live.match_digest(b"changed executable", live.sha(b"approved")))
        with tempfile.TemporaryDirectory() as root:
            source, staged = Path(root) / "source", Path(root) / "staged"
            source.write_bytes(b"unapproved executable contents")
            with self.assertRaisesRegex(ValueError, "artifact digest"):
                live.pin_artifact(source, staged, live.sha(b"approved"), 1024)
            self.assertFalse(staged.exists())
            live.pin_artifact(source, staged, live.sha(source.read_bytes()), 1024)
            self.assertEqual(staged.read_bytes(), source.read_bytes())

    def test_reply_model_and_failure_are_checked(self):
        self.assertEqual(relay_response(200, SSE, VALID, expected_model=MODEL)["status"], 200)
        wrong = VALID.replace(MODEL.encode(), b"unapproved:free")
        self.assertEqual(relay_response(200, SSE, wrong, expected_model=MODEL)["protocol"]["classification"],
                         "model_mismatch")
        self.assertEqual(relay_response(429, "application/json", JSON_ERROR)["status"], 502)
        self.assertEqual(relay_response(200, "application/json", JSON_ERROR)["status"], 502)

    def test_default_never_reads_approval_or_opens_transport(self):
        with patch.object(live, "activate", side_effect=AssertionError("activation reached")):
            self.assertEqual(live.main([]), 1)

    def test_improper_tls_is_rejected(self):
        with self.assertRaises(ValueError):
            live.require_tls(object(), live.KILO_HOST)
        context = live.tls_context() if Path(live.CA_FILE).is_file() else ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        with patch.object(live.http.client, "HTTPSConnection", side_effect=AssertionError("transport reached")):
            with self.assertRaisesRegex(ValueError, "POST proof"):
                live.network("post")

    def test_nonzero_tiny_catalog_price_and_duplicate_keys_fail_closed(self):
        from scripts.kilo_owner_gate import approved_catalog

        raw = b'{"data":[{"id":"recursive/flint-v1.0:free","pricing":{"prompt":1e-999,"completion":0}}]}'
        self.assertFalse(approved_catalog(live.strict_json(raw)))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            live.strict_json(b'{"pricing":{"prompt":1,"prompt":0}}')

    def test_malformed_chunk_delimiters_and_terminal_blank_line(self):
        from scripts.kilo_owner_gate import inspect_http_fixture

        headers = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
        for body in (b"1\r\nxXX0\r\n\r\n", b"1\r\nx\r\n0\r\n"):
            with self.assertRaises(ValueError):
                inspect_http_fixture(headers + body)

    @unittest.skipUnless(live.LINUX_LOCKS, "Linux filesystem-lock test")
    def test_durable_reservation_and_single_active_runner(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root)
            path = parent / "gate"
            with live.lease(path) as first:
                with self.assertRaises(ValueError):
                    with live.lease(path):
                        self.fail("second process-equivalent lock acquired")
                pid = os.fork()
                if pid == 0:
                    try:
                        with live.lease(path):
                            os._exit(3)
                    except ValueError:
                        os._exit(0)
                    except BaseException:
                        os._exit(4)
                _, status = os.waitpid(pid, 0)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                live.reserve(first, SHA, DIGEST, 999)
                with self.assertRaises(ValueError):
                    live.reserve(first, SHA, DIGEST, 999)
            with self.assertRaises(ValueError):
                with live.lease(path):
                    self.fail("spent scope reopened")
            alias = parent / "alias"
            alias.symlink_to(path, target_is_directory=True)
            with self.assertRaises(OSError):
                with live.lease(alias):
                    self.fail("symlink state accepted")

    @unittest.skipUnless(live.LINUX_LOCKS, "Linux filesystem-lock test")
    def test_exact_wire_posts_and_429_302_are_terminal(self):
        for status in (429, 302):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as root:
                with live.lease(Path(root) / "gate") as grant:
                    runner = live.runner_binding(grant, create=True)
                    self.assertEqual(live.runner_binding(grant), runner)
                    live.reserve(grant, SHA, DIGEST, 999)
                    now = datetime.now(timezone.utc)
                    utc = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
                    stamp = utc(now - timedelta(seconds=2))
                    expires = utc(now + timedelta(minutes=1))
                    record = comment() | {"created_at": stamp, "updated_at": stamp,
                                          "body": live.approval_line(SHA, DIGEST, runner, expires)}
                    proof = live.PostProof(grant, record, 999, SHA, DIGEST, runner)

                    class Memory:
                        def makefile(self, mode):
                            return io.BytesIO(f"HTTP/1.1 {status} Fixture\r\nContent-Length: 0\r\n"
                                              "Location: https://example.invalid/\r\n\r\n".encode())

                    response = HTTPResponse(Memory())
                    response.begin()
                    connection = MagicMock()
                    connection.getresponse.return_value = response
                    socket = MagicMock(spec=ssl.SSLSocket)
                    socket.server_hostname, socket.context = live.KILO_HOST, live.tls_context()
                    socket.version.return_value = "TLSv1.3"
                    socket.getpeercert.return_value = {"synthetic": True}
                    connection.sock = socket
                    with patch.object(live.http.client, "HTTPSConnection", return_value=connection) as factory:
                        self.assertEqual(live.network("post", proof=proof)[:2], (1, (status, None, b"", None)))
                        with self.assertRaisesRegex(ValueError, "POST proof"):
                            live.network("post", proof=proof)
                        factory.assert_called_once()
                    connection.request.assert_called_once()
                    self.assertEqual(connection.request.call_args.args, ("POST", "/api/v1/chat/completions"))
                    self.assertNotIn("Authorization", connection.request.call_args.kwargs["headers"])
                    connection.close.assert_called_once()

    @unittest.skipUnless(live.LINUX_LOCKS, "Linux process worker test")
    def test_approval_expiring_during_tls_never_writes_post(self):
        with tempfile.TemporaryDirectory() as root, live.lease(Path(root) / "gate") as grant:
            runner = live.runner_binding(grant, create=True)
            live.reserve(grant, SHA, DIGEST, 999)
            proof = live.PostProof(grant, comment(), 999, SHA, DIGEST, runner)
            connection = MagicMock()
            with (patch.object(proof, "valid", side_effect=[True, False]),
                  patch.object(live.http.client, "HTTPSConnection", return_value=connection),
                  patch.object(live, "require_tls")):
                self.assertEqual(live.network("post", proof=proof), (0, (502, None, b"", None)))
            connection.connect.assert_called_once()
            connection.request.assert_not_called()
            connection.close.assert_called_once()
            self.assertTrue((Path(root) / "gate" / "issue20.post").is_file())

    @unittest.skipUnless(live.LINUX_LOCKS, "Linux process worker test")
    def test_worker_deadline_reaps_process_and_refuses_reuse(self):
        with patch.object(live, "network", side_effect=lambda *args: time.sleep(20)):
            with live.Worker("catalog") as worker:
                count, reply = worker.call(0.15)
                self.assertIsNone(count)
                self.assertEqual(reply[0], 504)
                self.assertFalse(worker.process.is_alive())
                with self.assertRaisesRegex(ValueError, "already used"):
                    worker.call(0.15)
