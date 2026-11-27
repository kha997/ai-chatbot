"""Mock external-receipt validation and one-time consumption for synthetic custody.

THIS IS NOT A SIGNATURE SYSTEM. The bundled key is public, so any caller can
produce a valid MAC. It exists only to exercise issuer, freshness, binding and
replay logic against public fixtures. A real deployment needs a private key and
issuer identity held outside this repository; until then treat real custody as
NOT_VERIFIED.

Validation (``verify``) is pure and stateless. One-time use is a separate,
explicit step through ``ReplayStore.consume``; a consumed nonce is mock replay
state and must never be read as proof of issuer identity or external trust.
"""
import hmac
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from scripts import offline_heldout67 as h
from scripts.offline_source72 import checked

SCHEMA = "offline72-external-receipt-v1"
FIELDS = "schema issuer key_id sequence issued expires envelope root checkpoint tip nonce attestation mac"
MAX_AGE = 3600
# MOCK ONLY. Public by construction; possession proves nothing.
MOCK_ISSUER = "mock-external-issuer"
MOCK_KEY_ID = "mock-public-key-1"
MOCK_KEY = b"offline72-public-test-key-not-a-secret"

STORE_SCHEMA = (
    "CREATE TABLE consumed (issuer TEXT NOT NULL, nonce TEXT NOT NULL, "
    "receipt TEXT NOT NULL, sequence INTEGER NOT NULL, consumed_at INTEGER NOT NULL, "
    "PRIMARY KEY (issuer, nonce)) WITHOUT ROWID",
)


@dataclass(frozen=True)
class Receipt:
    issuer: str
    sequence: int
    envelope: str
    checkpoint: str
    tip: str
    attestation: str
    nonce: str
    digest: str


def mac(body, key):
    return hmac.new(key, h.canonical(body), "sha256").hexdigest()


def verify(raw, pin, *, trusted, now, envelope=None, checkpoint_pin=None,
           root=None, sequence=None, tip=None):
    """Validate one receipt without consuming it. Pure and stateless."""
    proof = checked(raw, pin)
    h.shape(proof, FIELDS)
    h.require(proof["schema"] == SCHEMA and proof["attestation"] == "MOCK_ONLY",
              "receipt-version")
    trusted = trusted or {}
    h.require(proof["issuer"] in trusted
              and proof["key_id"] == trusted[proof["issuer"]][0], "receipt-issuer")
    h.require(h.integer(proof["sequence"], 0, 120)
              and h.is_hash(proof["envelope"]) and h.is_hash(proof["root"])
              and h.is_hash(proof["checkpoint"]) and h.is_hash(proof["tip"])
              and h.is_hash(proof["mac"]) and h.token(proof["nonce"]), "receipt-shape")
    h.require(h.integer(proof["issued"]) and h.integer(proof["expires"], proof["issued"]+1)
              and proof["issued"] <= now < proof["expires"]
              and now - proof["issued"] <= MAX_AGE, "receipt-freshness")
    if envelope is not None:
        h.require(proof["envelope"] == envelope, "receipt-binding")
    if checkpoint_pin is not None:
        h.require(proof["checkpoint"] == checkpoint_pin, "receipt-binding")
    if root is not None:
        h.require(proof["root"] == root, "receipt-binding")
    if sequence is not None:
        h.require(proof["sequence"] == sequence, "receipt-binding")
    if tip is not None:
        h.require(proof["tip"] == tip, "receipt-binding")
    body = {key: value for key, value in proof.items() if key != "mac"}
    h.require(hmac.compare_digest(proof["mac"], mac(body, trusted[proof["issuer"]][1])),
              "receipt-mac")
    return Receipt(proof["issuer"], proof["sequence"], proof["envelope"],
                   proof["checkpoint"], proof["tip"], proof["attestation"],
                   proof["nonce"], pin)


class ReplayStore:
    """Persistent mock replay state with atomic check-and-insert.

    This store records one consumption per (issuer, nonce). It is mock state
    only: it cannot prove who issued a receipt or that custody exists.
    """

    def __init__(self, path):
        self._path = Path(path).resolve()
        self._uri = self._path.as_uri() + "?mode=rw"

    @classmethod
    def create(cls, path):
        store = cls(path)
        try:
            with store._path.open("xb"):
                pass
            with store._transaction(check=False) as db:
                for statement in STORE_SCHEMA:
                    db.execute(statement)
        except OSError:
            raise h.Invalid("replay-create") from None
        return store

    @contextmanager
    def _transaction(self, *, check=True):
        db = None
        try:
            db = sqlite3.connect(self._uri, uri=True, isolation_level=None, timeout=10)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if check:
                sql = {row[0] for row in
                       db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")}
                h.require(sql == set(STORE_SCHEMA)
                          and db.execute("PRAGMA quick_check").fetchone() == ("ok",),
                          "replay-schema")
            yield db
            db.commit()
        except sqlite3.Error:
            raise h.Invalid("replay-storage") from None
        finally:
            if db is not None:
                db.close()


def consume(store, verified, now):
    """Consume one validated receipt exactly once; atomic across processes."""
    h.require(isinstance(store, ReplayStore), "replay-store")
    h.require(type(now) is int and 0 <= now and h.token(verified.issuer)
              and h.token(verified.nonce) and h.is_hash(verified.digest), "replay-shape")
    with store._transaction() as db:
        try:
            db.execute("INSERT INTO consumed VALUES (?,?,?,?,?)",
                       (verified.issuer, verified.nonce, verified.digest,
                        verified.sequence, now))
        except sqlite3.IntegrityError:
            row = db.execute("SELECT receipt FROM consumed WHERE issuer=? AND nonce=?",
                             (verified.issuer, verified.nonce)).fetchone()
            if row is None:
                raise h.Invalid("replay-storage") from None
            if row[0] == verified.digest:
                raise h.Invalid("receipt-replay") from None
            raise h.Invalid("receipt-conflict") from None
    return "MOCK_CONSUMED_ONCE"
