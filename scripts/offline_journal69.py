"""Local SQLite journal for public dummy evaluation.

The latest known-good anchor is a mandatory input from a separate trust
boundary. Never adopt a tip returned by a suspect/reopened database.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from scripts import offline_heldout67 as h
from scripts.offline_evidence69 import ApprovedRun

SCHEMA = (
    "CREATE TABLE journal_context (id INTEGER PRIMARY KEY CHECK(id=1), genesis TEXT NOT NULL)",
    "CREATE TABLE receipt (seq INTEGER PRIMARY KEY, payload BLOB NOT NULL, anchor TEXT NOT NULL)",
    "CREATE TRIGGER receipt_no_update BEFORE UPDATE ON receipt "
    "BEGIN SELECT RAISE(ABORT,'append only'); END",
    "CREATE TRIGGER receipt_no_delete BEFORE DELETE ON receipt "
    "BEGIN SELECT RAISE(ABORT,'append only'); END",
    "CREATE TRIGGER context_no_update BEFORE UPDATE ON journal_context "
    "BEGIN SELECT RAISE(ABORT,'fixed journal context'); END",
    "CREATE TRIGGER context_no_delete BEFORE DELETE ON journal_context "
    "BEGIN SELECT RAISE(ABORT,'fixed journal context'); END",
)
OUTCOMES = ("NOT_RUN", "PASS", "FAIL", "INCONCLUSIVE", "STOP")


@dataclass(frozen=True)
class Receipt:
    run_id: str
    envelope: str
    manifest: str
    case: str
    category: str
    index: int
    repetition: int
    sequence: int
    tick: int
    bundle: str
    observation: str
    outcome: str
    code: str
    previous: str
    anchor: str


class Journal:
    def __init__(self, path, approval):
        h.require(type(approval) is ApprovedRun, "approved-mock-envelope")
        self._path = Path(path).resolve()
        self._uri = self._path.as_uri() + "?mode=rw"
        self._approved = approval

    @classmethod
    def create(cls, path, approval):
        self = cls(path, approval)
        try:
            with self._path.open("xb"):
                pass
            with self._transaction(check=False) as db:
                for statement in SCHEMA:
                    db.execute(statement)
                db.execute("INSERT INTO journal_context VALUES (1,?)", (approval.genesis,))
        except OSError:
            raise h.Invalid("journal-create") from None
        return self

    @classmethod
    def open(cls, path, approval, latest_anchor):
        self = cls(path, approval)
        with self._transaction() as db:
            self._history(db, latest_anchor)
        return self

    @contextmanager
    def _transaction(self, *, check=True):
        db = None
        try:
            db = sqlite3.connect(self._uri, uri=True, isolation_level=None, timeout=5)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if check:
                sql = {row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")}
                h.require(sql == set(SCHEMA) and db.execute("PRAGMA quick_check").fetchone() == ("ok",),
                          "journal-schema")
            yield db
            db.commit()
        except sqlite3.Error:
            raise h.Invalid("journal-storage") from None
        finally:
            if db is not None:
                db.close()

    def _position(self, index):
        size = len(self._approved.cases)
        h.require(h.integer(index, 0, 2*size-1), "journal-position")
        repetition, offset = divmod(index, size)
        return repetition+1, self._approved.cases[offset]

    def _history(self, db, latest_anchor):
        h.require(h.is_hash(latest_anchor), "externally-pinned-anchor")
        accepted = self._approved
        tip = accepted.genesis
        h.require(db.execute("SELECT id,genesis FROM journal_context").fetchall() == [(1, tip)],
                  "journal-context")
        records = []
        last_tick = accepted.from_tick
        for seq, raw, anchor in db.execute("SELECT seq,payload,anchor FROM receipt ORDER BY seq"):
            h.require(seq == len(records)+1 and (not records or records[-1].outcome != "STOP"),
                      "journal-chain")
            repetition, (case, category, _, _, _) = self._position(seq-1)
            row = h.parse(raw)
            h.shape(row, "run_id envelope manifest case category index repetition sequence tick bundle "
                    "observation outcome code previous")
            h.require(row["previous"] == tip and h.is_hash(anchor) and h.digest(raw) == anchor
                      and row["run_id"] == accepted.run_id and row["envelope"] == accepted.envelope_sha
                      and row["manifest"] == accepted.manifest_sha and row["case"] == case
                      and row["category"] == category and h.integer(row["index"], seq-1, seq-1)
                      and h.integer(row["sequence"], seq, seq)
                      and h.integer(row["repetition"], repetition, repetition)
                      and h.integer(row["tick"], last_tick)
                      and h.is_hash(row["bundle"])
                      and (row["observation"] == "ABSENT" or h.is_hash(row["observation"]))
                      and row["outcome"] in OUTCOMES and h.token(row["code"]), "journal-receipt")
            records.append(Receipt(**row, anchor=anchor))
            tip, last_tick = anchor, row["tick"]
        h.require(tip == latest_anchor, "anchor-mismatch")
        return records

    def submit(self, index, bundle_raw, observation_raw, tick, latest_anchor):
        """Generate an official mock receipt in the transaction that appends it."""
        repetition, (case, category, frozen_bundle, required_reads, forbidden_ids) = self._position(index)
        h.require(type(bundle_raw) is bytes
                  and (observation_raw is None or type(observation_raw) is bytes)
                  and h.integer(tick), "submission")
        # Bind even malformed byte submissions without retaining plaintext.
        bundle = h.digest(bundle_raw)
        observation = "ABSENT" if observation_raw is None else h.digest(observation_raw)
        agreed = self._approved
        with self._transaction() as db:
            history = self._history(db, latest_anchor)
            if index < len(history):
                old = history[index]
                h.require((bundle, observation, tick) == (old.bundle, old.observation, old.tick),
                          "changed-replay")
                return old
            h.require(index == len(history), "ledger-order")
            h.require(not history or history[-1].outcome != "STOP", "ledger-stopped")
            h.require(not history or tick >= history[-1].tick, "rewound-clock")
            if not agreed.from_tick <= tick < agreed.until_tick:
                # A past clock cannot be appended to a monotonic chain.
                h.require(tick >= agreed.from_tick, "rewound-clock")
                outcome, code = "STOP", "expired-mock-approval"
            elif frozen_bundle != bundle:
                outcome, code = "STOP", "frozen-record"
            else:
                diagnostic = h.evaluate(agreed.manifest_raw, agreed.manifest_sha,
                                        index, bundle_raw, observation_raw,
                                        forbidden_fact_ids=forbidden_ids)
                outcome, code = diagnostic.outcome, diagnostic.code
                if observation_raw is not None and outcome != "STOP":
                    observed = h.parse(observation_raw)
                    reads = {h.reference(read["ref"]) for read in observed["reads"]}
                    if observed["status"] == "complete" and not required_reads <= reads:
                        outcome, code = "STOP", "missing-required-read"
            row = dict(run_id=agreed.run_id, envelope=agreed.envelope_sha, manifest=agreed.manifest_sha,
                       case=case, category=category, index=index, repetition=repetition,
                       sequence=index+1, tick=tick, bundle=bundle, observation=observation,
                       outcome=outcome, code=code, previous=latest_anchor)
            raw = h.canonical(row)
            receipt = Receipt(**row, anchor=h.digest(raw))
            db.execute("INSERT INTO receipt VALUES (?,?,?)",
                       (receipt.sequence, raw, receipt.anchor))
            return receipt
