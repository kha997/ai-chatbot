"""Opt-in SQLite backend for the offline synthetic quote session adapter."""

import hashlib
import hmac
import json
import re
import sqlite3
from contextlib import closing, contextmanager
from functools import wraps
from pathlib import Path
from secrets import token_bytes, token_hex
from time import time

from scripts.quote_sessions import REFERENCE, TICKET, SessionQuotes, _denied, _matches, _protected
from scripts.quote_validator import validate_quote


SCHEMA_VERSION = 1
APPLICATION_ID = 0x53594846
TTL_SECONDS = 86400
MAX_TICKETS_PER_TENANT = 1000
PROOF = re.compile(r"[0-9a-f]{64}")
SCHEMA = (
    """CREATE TABLE consents (
        tenant TEXT NOT NULL CHECK (tenant IN ('NHD', 'HANU', 'ZENA')),
        ticket_id TEXT NOT NULL PRIMARY KEY CHECK (length(ticket_id) = 32),
        scope TEXT NOT NULL CHECK (scope = 'synthetic-quote-support'),
        version INTEGER NOT NULL CHECK (version = 1),
        granted_at INTEGER NOT NULL CHECK (granted_at >= 0),
        expires_at INTEGER NOT NULL CHECK (expires_at = granted_at + 86400),
        withdrawn_at INTEGER CHECK (withdrawn_at >= granted_at),
        UNIQUE (tenant, ticket_id)
    )""",
    """CREATE TABLE tickets (
        tenant TEXT NOT NULL,
        ticket_id TEXT NOT NULL PRIMARY KEY,
        owner_scope TEXT NOT NULL CHECK (length(owner_scope) = 32),
        message_digest TEXT NOT NULL CHECK (length(message_digest) = 64),
        fingerprint TEXT NOT NULL CHECK (length(fingerprint) = 64),
        reason TEXT NOT NULL CHECK (reason IN ('invalid_quantity', 'unit_mismatch', 'currency_mismatch')),
        status TEXT NOT NULL CHECK (status IN ('queued', 'delivered', 'accepted', 'cancelled')),
        UNIQUE (tenant, owner_scope, message_digest),
        FOREIGN KEY (tenant, ticket_id) REFERENCES consents (tenant, ticket_id)
    )""",
    "CREATE INDEX tenant_queue ON tickets (tenant, status)",
)
JOINED = """SELECT t.*, c.granted_at, c.expires_at, c.withdrawn_at
            FROM tickets AS t JOIN consents AS c
            ON c.tenant = t.tenant AND c.ticket_id = t.ticket_id"""
ACTIVE = "c.withdrawn_at IS NULL AND c.granted_at <= ? AND ? < c.expires_at"


class _ExpiredSession(Exception):
    pass


def _storage_result(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except _ExpiredSession:
            return _denied()
        except sqlite3.Error:
            return {"status": "unavailable"}
    return call


def _digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _active(row, now):
    return row["withdrawn_at"] is None and row["granted_at"] <= now < row["expires_at"]


def _status(row):
    return {"status": row["status"], "ticket_id": row["ticket_id"]}


class SQLiteSessionQuotes(SessionQuotes):
    """Trusted setup constructs one adapter per app. Request calls need a live handle."""

    def __init__(self, authority, path, *, clock=time):
        super().__init__(authority)
        path = Path(path).resolve()
        if path.suffix not in {".sqlite", ".sqlite3", ".db"}:
            raise ValueError("Use a local synthetic database with an ignored SQLite extension")
        self._uri = path.as_uri()
        self._clock = clock
        self._proof_key = token_bytes(32)
        # DDL is atomic too. An unrelated or unknown DB is never migrated or overwritten.
        with self._transaction(write=True, initialize=True) as db:
            signature = tuple(db.execute(f"PRAGMA {key}").fetchone()[0]
                              for key in ("application_id", "user_version"))
            if signature == (0, 0) and db.execute("SELECT 1 FROM sqlite_schema LIMIT 1").fetchone() is None:
                for statement in SCHEMA:
                    db.execute(statement)
                db.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            elif signature != (APPLICATION_ID, SCHEMA_VERSION):
                raise ValueError("Unsupported synthetic handoff database")

    @contextmanager
    def _transaction(self, session=None, *, write=False, initialize=False):
        mode = "rwc" if initialize else "rw"
        with closing(sqlite3.connect(f"{self._uri}?mode={mode}", uri=True, timeout=2,
                                     isolation_level=None)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            with db:
                if session is not None:
                    tick = self._authority._now()
                    if tick is None or not session.issued <= tick < session.expires:
                        raise _ExpiredSession()
                yield db

    def _now(self):
        # UTC epoch seconds, separate from the monotonic authority clock.
        try:
            now = int(self._clock())
        except (TypeError, ValueError, OverflowError):
            raise _ExpiredSession() from None
        if not 0 <= now <= 253402214399:
            raise _ExpiredSession()
        return now

    @_protected("customer")
    @_storage_result
    def handoff(self, session, request, *, message_id, consent, candidate=None):
        terms = self._terms(session, request, candidate)
        if terms is None or not _matches(REFERENCE, message_id):
            return _denied()
        if consent is not True:
            return {"status": "consent_required"}
        quote = validate_quote(**terms)
        if quote["behavior"] == "refuse":
            return _denied()
        return self._enqueue(session, message_id, terms["request"],
                             quote["reason"] if quote["behavior"] == "clarify" else None)

    def _enqueue(self, session, message_id, request, reason):
        message = _digest(message_id)
        fingerprint = _digest(request)
        with self._transaction(session, write=True) as db:
            now = self._now()
            row = db.execute(JOINED + " WHERE t.tenant=? AND t.owner_scope=? AND t.message_digest=?",
                             (session.tenant, session.session_id, message)).fetchone()
            if row is not None:
                return _status(row) if row["fingerprint"] == fingerprint and _active(row, now) else _denied()
            if reason is None:
                return {"status": "not_offered"}
            count = db.execute("SELECT count(*) FROM tickets WHERE tenant=?", (session.tenant,)).fetchone()[0]
            if count >= MAX_TICKETS_PER_TENANT:
                return {"status": "unavailable"}
            ticket = token_hex(16)
            db.execute("""INSERT INTO consents (tenant, ticket_id, scope, version, granted_at, expires_at)
                          VALUES (?, ?, 'synthetic-quote-support', 1, ?, ?)""",
                       (session.tenant, ticket, now, now + TTL_SECONDS))
            db.execute("""INSERT INTO tickets (tenant, ticket_id, owner_scope, message_digest, fingerprint, reason, status)
                          VALUES (?, ?, ?, ?, ?, ?, 'queued')""",
                       (session.tenant, ticket, session.session_id, message, fingerprint, reason))
            return {"status": "queued", "ticket_id": ticket}

    @staticmethod
    def _owned(db, session, ticket_id):
        return db.execute(JOINED + " WHERE t.tenant=? AND t.owner_scope=? AND t.ticket_id=?",
                          (session.tenant, session.session_id, ticket_id)).fetchone()

    @_protected("customer")
    @_storage_result
    def ticket_status(self, session, ticket_id):
        if not _matches(TICKET, ticket_id):
            return _denied()
        with self._transaction(session) as db:
            row = self._owned(db, session, ticket_id)
            if row is None:
                return _denied()
            if row["withdrawn_at"] is not None:
                return _status(row) | {"consent": "withdrawn"}
            now = self._now()
            if now < row["granted_at"]:
                return _denied()
            return _status(row) | {"consent": "granted" if _active(row, now) else "expired"}

    @_protected("customer")
    @_storage_result
    def withdraw(self, session, ticket_id):
        if not _matches(TICKET, ticket_id):
            return _denied()
        with self._transaction(session, write=True) as db:
            row = self._owned(db, session, ticket_id)
            if row is None:
                return _denied()
            status = row["status"]
            if row["withdrawn_at"] is None:
                db.execute("""UPDATE consents SET withdrawn_at=? WHERE tenant=? AND ticket_id=?
                              AND EXISTS (SELECT 1 FROM tickets WHERE tickets.tenant=consents.tenant
                              AND tickets.ticket_id=consents.ticket_id AND owner_scope=?)""",
                           (max(self._now(), row["granted_at"]), session.tenant, ticket_id, session.session_id))
                if status in ("queued", "delivered"):
                    db.execute("""UPDATE tickets SET status='cancelled'
                                  WHERE tenant=? AND ticket_id=? AND owner_scope=? AND status=?""",
                               (session.tenant, ticket_id, session.session_id, status))
                    status = "cancelled"
            result = {"status": status, "ticket_id": ticket_id}
            return result | {"consent": "withdrawn"} if status == "accepted" else result

    def _proof(self, session, ticket_id):
        scope = f"{session.tenant}:{session.session_id}:{ticket_id}".encode("ascii")
        return hmac.digest(self._proof_key, scope, "sha256").hex()

    def _summary(self, row, session, status):
        summary = {key: row[key] for key in ("tenant", "ticket_id", "reason")}
        summary["status"] = status
        if status == "delivered":
            summary["proof"] = self._proof(session, row["ticket_id"])
        return summary

    @_protected("support")
    @_storage_result
    def deliver_next(self, session):
        with self._transaction(session, write=True) as db:
            now = self._now()
            row = db.execute(JOINED + f""" WHERE t.tenant=? AND t.status='queued' AND {ACTIVE}
                                         ORDER BY t.rowid LIMIT 1""", (session.tenant, now, now)).fetchone()
            if row is None:
                return {"status": "empty"}
            db.execute("UPDATE tickets SET status='delivered' WHERE tenant=? AND ticket_id=? AND status='queued'",
                       (session.tenant, row["ticket_id"]))
            return self._summary(row, session, "delivered")

    @_protected("support")
    @_storage_result
    def inbox(self, session):
        with self._transaction(session) as db:
            now = self._now()
            rows = db.execute(JOINED + f""" WHERE t.tenant=? AND t.status IN ('delivered', 'accepted')
                                          AND {ACTIVE} ORDER BY t.rowid""", (session.tenant, now, now))
            return {"status": "ok", "tickets": [self._summary(row, session, row["status"]) for row in rows]}

    @_protected("support")
    @_storage_result
    def confirm(self, session, ticket_id, proof=None):
        if (not _matches(TICKET, ticket_id) or not _matches(PROOF, proof)
                or not hmac.compare_digest(self._proof(session, ticket_id), proof)):
            return _denied()
        with self._transaction(session, write=True) as db:
            now = self._now()
            row = db.execute(JOINED + f""" WHERE t.tenant=? AND t.ticket_id=? AND {ACTIVE}
                                         AND t.status IN ('delivered', 'accepted')""",
                             (session.tenant, ticket_id, now, now)).fetchone()
            if row is None:
                return _denied()
            if row["status"] == "delivered":
                db.execute("UPDATE tickets SET status='accepted' WHERE tenant=? AND ticket_id=? AND status='delivered'",
                           (session.tenant, ticket_id))
            return {"status": "accepted", "ticket_id": ticket_id}
