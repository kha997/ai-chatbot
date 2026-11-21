"""Regression contracts specific to the new authorization scope."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scripts import kilo_activate as legacy, kilo_activate26 as gate


class NewScopeTests(unittest.TestCase):
    def test_new_owner_proof_and_old_spend_are_distinct(self):
        now = datetime.now(timezone.utc)
        utc = lambda stamp: stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        created = utc(now - timedelta(seconds=1))
        expiry = utc(now + timedelta(minutes=15))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with legacy.lease(root / "old") as old:
                legacy.reserve(old, "a" * 40, "b" * 64, 999)
            original = (root / "old" / "issue20.spent").read_bytes()
            with legacy.lease(root / "new", scope=26) as new:
                with self.assertRaisesRegex(ValueError, "owns the lock"):
                    with legacy.lease(root / "new", scope=26):
                        self.fail("concurrent lease accepted")
                runner = legacy.runner_binding(new, create=True)
                record = {"id": 999, "issue_url": legacy.ISSUE_URL, "author_association": "OWNER",
                          "user": {"id": legacy.OWNER_ID, "login": "kha997"},
                          "created_at": created, "updated_at": created,
                          "body": legacy.approval_line("a" * 40, "b" * 64, runner, expiry)}
                self.assertFalse(gate.verify_owner(record, 999, "a" * 40, "b" * 64, runner, now))
                record["issue_url"] = gate.ISSUE_URL
                record["body"] = legacy.approval_line("a" * 40, "b" * 64, runner, expiry, scope=26)
                self.assertTrue(gate.verify_owner(record, 999, "a" * 40, "b" * 64, runner, now))
                self.assertFalse(gate.verify_owner(record, 999, "c" * 40, "b" * 64, runner, now))
                self.assertFalse(gate.verify_owner(record, 999, "a" * 40, "d" * 64, runner, now))
                self.assertFalse(gate.verify_owner(record, 999, "a" * 40, "b" * 64, "f" * 64, now))
                self.assertFalse(gate.verify_owner(record, 999, "a" * 40, "b" * 64, runner,
                                                  now + timedelta(hours=2)))
                proof = legacy.PostProof(new, record, 999, "a" * 40, "b" * 64, runner)
                self.assertFalse(proof.valid())
                legacy.reserve(new, "a" * 40, "b" * 64, 999)
                self.assertTrue(proof.valid())
                self.assertTrue(proof.claim())
                self.assertFalse(proof.claim())
            self.assertTrue((root / "new" / "issue26.post").exists())
            self.assertEqual((root / "old" / "issue20.spent").read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "already spent"):
                with legacy.lease(root / "new", scope=26):
                    self.fail("durable replay accepted")

    def test_post_rechecks_expiry_after_tls_and_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp, legacy.lease(Path(tmp) / "state", scope=26) as grant:
            proof = legacy.PostProof(grant, {}, 999, "a" * 40, "b" * 64, "c" * 64)
            connection = MagicMock()
            connection.__enter__.return_value = connection
            with (patch.object(proof, "claim", return_value=True),
                  patch.object(proof, "valid", return_value=False),
                  patch.object(legacy, "require_tls") as verify,
                  patch.object(gate.http.client, "HTTPSConnection", return_value=connection)):
                posts, reply = gate.post_once(proof)
            self.assertEqual(posts, 0)
            self.assertEqual(reply["protocol"]["classification"], "approval_expired_before_post")
            verify.assert_called_once_with(connection.sock, legacy.KILO_HOST)
            connection.request.assert_not_called()
