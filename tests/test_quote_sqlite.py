import sqlite3
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from scripts.quote_sessions import SessionAuthority
from scripts.quote_sqlite import SQLiteSessionQuotes


REQUEST = {"sku": "SYN-TILE-A", "unit": "box", "currency": "VND"}
DENIED = {"status": "denied"}
EMPTY = {"status": "empty"}


class SQLiteHandoffTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "handoff.sqlite"
        self.utc = 1800000000
        self.tick = 100
        self.authority = SessionAuthority(clock=lambda: self.tick)
        self.customer = self.issue()
        self.staff = self.issue(role="support")
        self.app = self.open()

    def issue(self, tenant="NHD", role="customer"):
        return self.authority.issue(tenant=tenant, role=role, actor_id="synthetic-actor", lifetime=60)

    def open(self):
        return SQLiteSessionQuotes(self.authority, self.path, clock=lambda: self.utc)

    def enqueue(self, *, message="request-1", consent=True, request=None, handle=None):
        return self.app.handoff(handle or self.customer, "NHD", REQUEST if request is None else request,
                                message_id=message, consent=consent)

    def counts(self):
        with closing(sqlite3.connect(self.path)) as db:
            return tuple(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                         for table in ("consents", "tickets"))

    def restart(self):
        self.authority = SessionAuthority(clock=lambda: self.tick)
        self.app = self.open()

    def test_restart_support_can_finish_ticket_but_old_handles_and_same_actor_fail(self):
        ticket = self.enqueue()["ticket_id"]
        delivered = self.app.deliver_next(self.staff, "NHD")
        self.restart()
        new_staff, new_customer = self.issue(role="support"), self.issue()
        self.assertEqual(self.app.inbox(self.staff, "NHD"), DENIED)
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", ticket), DENIED)
        self.assertEqual(self.app.ticket_status(new_customer, "NHD", ticket), DENIED)
        self.assertEqual(self.app.withdraw(new_customer, "NHD", ticket), DENIED)
        self.assertEqual(self.app.confirm(new_staff, "NHD", ticket, delivered["proof"]), DENIED)
        renewed = self.app.inbox(new_staff, "NHD")["tickets"][0]
        self.assertEqual(renewed["ticket_id"], ticket)
        self.assertEqual(self.app.confirm(new_staff, "NHD", ticket, renewed["proof"])["status"], "accepted")
        self.restart()
        self.assertEqual(self.app.inbox(self.issue(role="support"), "NHD")["tickets"][0]["status"], "accepted")
        self.assertEqual(self.counts(), (1, 1))

    def test_same_key_reopens_idempotently_and_changed_payload_denies(self):
        first = self.enqueue()
        self.app = self.open()
        self.assertEqual(self.enqueue(), first)
        self.assertEqual(self.enqueue(request=REQUEST | {"quantity": "0"}), DENIED)
        self.assertEqual(self.counts(), (1, 1))

    def test_withdrawal_after_reopen_cancels_queued_and_delivered(self):
        delivered_id = self.enqueue()["ticket_id"]
        delivery = self.app.deliver_next(self.staff, "NHD")
        queued_id = self.enqueue(message="request-2")["ticket_id"]
        self.app = self.open()
        for ticket in (queued_id, delivered_id):
            result = {"status": "cancelled", "ticket_id": ticket}
            self.assertEqual(self.app.withdraw(self.customer, "NHD", ticket), result)
            self.assertEqual(self.app.withdraw(self.customer, "NHD", ticket), result)
        self.assertEqual(self.enqueue(), DENIED)
        self.assertEqual(self.enqueue(message="request-3", consent=False), {"status": "consent_required"})
        self.restart()
        staff = self.issue(role="support")
        self.assertEqual(self.app.deliver_next(staff, "NHD"), EMPTY)
        self.assertEqual(self.app.inbox(staff, "NHD"), {"status": "ok", "tickets": []})
        self.assertEqual(self.app.confirm(staff, "NHD", delivered_id, delivery["proof"]), DENIED)
        self.assertEqual(self.counts(), (2, 2))
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT withdrawn_at FROM consents").fetchall(), [(self.utc,)] * 2)
        self.customer = self.issue()
        self.assertEqual(self.enqueue(message="request-3")["status"], "queued")

    def test_accepted_withdrawal_preserves_history_but_hides_it_from_staff(self):
        ticket = self.enqueue()["ticket_id"]
        delivery = self.app.deliver_next(self.staff, "NHD")
        accepted = {"status": "accepted", "ticket_id": ticket}
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, delivery["proof"]), accepted)
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, delivery["proof"]), accepted)
        self.assertEqual(self.app.withdraw(self.customer, "NHD", ticket),
                         accepted | {"consent": "withdrawn"})
        self.app = self.open()
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", ticket),
                         accepted | {"consent": "withdrawn"})
        self.assertEqual(self.app.inbox(self.staff, "NHD")["tickets"], [])
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, delivery["proof"]), DENIED)

    def test_expiry_and_ordered_transitions(self):
        ticket = self.enqueue()["ticket_id"]
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, "0" * 64), DENIED)
        delivery = self.app.deliver_next(self.staff, "NHD")
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, "0" * 64), DENIED)
        self.assertEqual(self.app.confirm(self.issue(role="support"), "NHD", ticket, delivery["proof"]), DENIED)
        self.enqueue(message="queued-to-expire")
        self.utc += 86400
        self.app = self.open()
        self.assertEqual(self.app.deliver_next(self.staff, "NHD"), EMPTY)
        self.assertEqual(self.app.inbox(self.staff, "NHD")["tickets"], [])
        self.assertEqual(self.app.confirm(self.staff, "NHD", ticket, delivery["proof"]), DENIED)
        self.assertEqual(self.enqueue(), DENIED)
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", ticket)["consent"], "expired")

    def test_wrong_tenant_customer_role_and_malformed_fields_are_denied(self):
        ticket = self.enqueue()["ticket_id"]
        other = self.issue()
        foreign = self.issue(tenant="HANU", role="support")
        self.assertEqual(self.app.ticket_status(other, "NHD", ticket), DENIED)
        self.assertEqual(self.app.withdraw(other, "NHD", ticket), DENIED)
        self.assertEqual(self.app.withdraw(self.staff, "NHD", ticket), DENIED)
        self.assertEqual(self.app.deliver_next(foreign, "NHD"), DENIED)
        self.assertEqual(self.app.deliver_next(foreign, "HANU"), EMPTY)
        self.assertEqual(self.app.inbox(self.customer, "NHD"), DENIED)
        self.assertEqual(self.app.confirm(foreign, "HANU", ticket, "0" * 64), DENIED)
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", "' OR 1=1 --"), DENIED)
        self.assertEqual(self.app.withdraw({"tenant": "NHD"}, "NHD", ticket), DENIED)
        self.assertEqual(self.enqueue(request=REQUEST | {"actor_id": "synthetic-actor"}), DENIED)
        self.assertEqual(self.app.deliver_next(self.staff, "NHD")["ticket_id"], ticket)

    def test_no_write_for_no_consent_bare_assertion_refusal_or_expired_session(self):
        self.assertEqual(self.enqueue(consent=1), {"status": "consent_required"})
        self.assertEqual(self.enqueue(request=REQUEST | {"quantity": "3"}), {"status": "not_offered"})
        self.assertEqual(self.enqueue(request=REQUEST | {"tenant": "HANU"}), DENIED)
        self.assertEqual(self.enqueue(handle={"tenant": "NHD", "role": "customer"}), DENIED)
        self.authority.revoke(self.customer)
        self.assertEqual(self.enqueue(), DENIED)
        self.tick += 60
        self.assertEqual(self.app.deliver_next(self.staff, "NHD"), DENIED)
        self.assertEqual(self.counts(), (0, 0))

    def test_sqlite_failure_rolls_back_consent_and_ticket_and_allows_retry(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_ticket BEFORE INSERT ON tickets "
                       "BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.enqueue(), {"status": "unavailable"})
        self.assertEqual(self.counts(), (0, 0))
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DROP TRIGGER fail_ticket")
        self.app = self.open()
        self.assertEqual(self.enqueue()["status"], "queued")
        self.assertEqual(self.counts(), (1, 1))

    def test_ticket_id_collision_cannot_replace_existing_consent_or_ticket(self):
        with patch("scripts.quote_sqlite.token_hex", return_value="1" * 32):
            first = self.enqueue()
            self.assertEqual(self.enqueue(message="different"), {"status": "unavailable"})
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.enqueue(), first)

    def test_concurrent_connections_insert_one_record_for_same_trusted_scope(self):
        peer = self.open()
        session = self.authority._resolve(self.customer, "NHD", "customer")
        barrier = Barrier(2)

        def submit(app):
            barrier.wait(timeout=5)
            # This internal seam receives a server-resolved session. Bypassing
            # the authority lock here exercises real SQLite writer contention.
            return app._enqueue(session, "same-message", REQUEST, "invalid_quantity")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.submit(submit, self.app), pool.submit(submit, peer)
            self.assertEqual(first.result(timeout=10), second.result(timeout=10))
        self.assertEqual(self.counts(), (1, 1))

    def test_invalid_schema_is_rejected_without_overwrite(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA user_version = 99")
        with self.assertRaises(ValueError):
            self.open()
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone(), (99,))

    def test_new_python_process_reads_pending_and_revoked_records(self):
        queued = self.enqueue()["ticket_id"]
        cancelled = self.enqueue(message="withdraw-me")["ticket_id"]
        self.app.withdraw(self.customer, "NHD", cancelled)
        child = """
import sys
from scripts.quote_sessions import SessionAuthority
from scripts.quote_sqlite import SQLiteSessionQuotes

auth = SessionAuthority(clock=lambda: 100)
app = SQLiteSessionQuotes(auth, sys.argv[1], clock=lambda: 1800000000)
staff = auth.issue(tenant="NHD", role="support", actor_id="synthetic-agent")
assert app.deliver_next(staff, "NHD")["ticket_id"] == sys.argv[2]
assert app.deliver_next(staff, "NHD") == {"status": "empty"}
"""
        result = subprocess.run([sys.executable, "-B", "-c", child, str(self.path), queued],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", cancelled),
                         {"status": "cancelled", "ticket_id": cancelled, "consent": "withdrawn"})

    def test_withdrawal_rolls_back_if_cancellation_write_fails(self):
        ticket = self.enqueue()["ticket_id"]
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_cancel BEFORE UPDATE OF status ON tickets "
                       "WHEN NEW.status='cancelled' BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assertEqual(self.app.withdraw(self.customer, "NHD", ticket), {"status": "unavailable"})
        self.app = self.open()
        self.assertEqual(self.app.ticket_status(self.customer, "NHD", ticket),
                         {"status": "queued", "ticket_id": ticket, "consent": "granted"})
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DROP TRIGGER fail_cancel")
        self.assertEqual(self.app.withdraw(self.customer, "NHD", ticket)["status"], "cancelled")

    def test_local_store_requires_ignored_filename(self):
        with self.assertRaises(ValueError):
            SQLiteSessionQuotes(self.authority, self.path.with_suffix(".txt"))
        self.assertFalse(self.path.with_suffix(".txt").exists())
