"""SQLite qualification simulator. The transport is inert; amounts are micro-USD."""
import hashlib
import json
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

MODEL = "gpt-5.4-mini-2026-03-17"
SUITES = {"qa": 120, "dev": 12, "adversarial": 24, "journeys": 12, "performance": 100}
MAX_ATTEMPTS, CONTINGENCY, CEILING, PROTECTED = 600, 64, 8_000_000, 2_000_000
TEXT = "SYNTHETIC GATEWAY REFERENCE"
TRANSIENT = {"429-rate", "500", "503"}
HARD = {"400", "401", "403", "429-cap"}
SCHEMA = (
    """CREATE TABLE run (id INTEGER PRIMARY KEY CHECK(id=1), manifest TEXT NOT NULL,
    serial TEXT NOT NULL, expiry INTEGER NOT NULL, worker TEXT NOT NULL, session TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE','STOPPED')), reason TEXT NOT NULL)""",
    "CREATE TABLE approval (serial TEXT PRIMARY KEY)",
    """CREATE TABLE attempt (id INTEGER PRIMARY KEY, suite TEXT NOT NULL, execution INTEGER NOT NULL,
    stage INTEGER NOT NULL, kind TEXT NOT NULL, parent INTEGER REFERENCES attempt(id),
    digest TEXT NOT NULL, nonce TEXT NOT NULL UNIQUE, worst INTEGER NOT NULL,
    deadline INTEGER NOT NULL,
    UNIQUE(suite,execution,stage,kind))""",
    "CREATE TABLE intent (id INTEGER PRIMARY KEY REFERENCES attempt(id))",
    "CREATE UNIQUE INDEX diagnostic_slot ON attempt(execution) WHERE kind='diagnostic'",
    """CREATE TABLE observation (id INTEGER PRIMARY KEY REFERENCES intent(id), receipt TEXT NOT NULL)""",
    """CREATE TABLE settlement (id INTEGER PRIMARY KEY REFERENCES observation(id),
    charge INTEGER NOT NULL CHECK(charge>=0), result TEXT NOT NULL)""",
) + tuple(
    f"CREATE TRIGGER immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} "
    "BEGIN SELECT RAISE(ABORT,'immutable ledger'); END"
    for table in ("approval", "attempt", "intent", "observation", "settlement")
    for operation in ("UPDATE", "DELETE")
)
EXPECTED_SCHEMA = frozenset(SCHEMA)


class Rejected(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class SimulatedCrash(Exception):
    pass


@dataclass(frozen=True)
class Approval:
    """Explicit authorization supplied by the trusted local test supervisor."""
    manifest: str
    serial: str
    expiry: int


@dataclass(frozen=True)
class Permit:
    attempt: int
    nonce: str


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def unpack(raw):
    def unique(items):
        record = dict(items)
        if len(record) != len(items):
            raise ValueError("duplicate field")
        return record
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def closed(obj, keys):
    return type(obj) is dict and obj.keys() == set(keys.split())


def number(value, low, high):
    return type(value) is int and low <= value <= high


def hexhash(value):
    return type(value) is str and re.fullmatch("[a-f0-9]{64}", value) is not None


def ceiling(value, unit):
    return (value + unit - 1) // unit


def charge(rate, input_tokens, output_tokens):
    # Round each upper bound upward, including taxes on per-attempt fees.
    tokens = ceiling(input_tokens * rate["input_micro_per_m"] +
                     output_tokens * rate["output_micro_per_m"], 1_000_000)
    regional = ceiling(tokens * (10_000 + rate["regional_bps"]), 10_000)
    taxed = ceiling((regional + rate["per_attempt_micro"]) *
                    (10_000 + rate["tax_bps"]), 10_000)
    unit = rate["rounding_micro"]
    return ceiling(taxed, unit) * unit


def parse_manifest(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= 150_000:
        raise ValueError("manifest size")
    data = unpack(raw)
    if encode(data).encode() != raw or not closed(
        data, "schema run synthetic tenant source oracle_reviewed prompt config permits diagnostics rate"
    ):
        raise ValueError("closed manifest")
    if (data["schema"] != 1 or type(data["schema"]) is not int
            or data["run"] != "SYN-GW-RUN-01" or data["synthetic"] is not True
            or data["tenant"] != "NHD" or data["oracle_reviewed"] is not True
            or not all(hexhash(data[k]) for k in ("prompt", "config"))):
        raise ValueError("unapproved manifest")
    source = data["source"]
    if (not closed(source, "id version approved reviewed synthetic active_from active_until")
            or source["id"] != "SYN-GW-NHD-01" or not number(source["version"], 1, 999)
            or not all(source[k] is True for k in ("approved", "reviewed", "synthetic"))
            or not number(source["active_from"], 0, 2**53)
            or not number(source["active_until"], source["active_from"] + 1, 2**53)):
        raise ValueError("unapproved source")
    rate = data["rate"]
    if (not closed(rate, "date model tier input_micro_per_m output_micro_per_m regional_bps "
                   "tax_bps per_attempt_micro fixed_micro rounding_micro")
            or rate["date"] != "2026-11-23" or rate["model"] != MODEL or rate["tier"] != "standard"
            or not number(rate["input_micro_per_m"], 750000, 750000)
            or not number(rate["output_micro_per_m"], 4500000, 4500000)
            or not number(rate["regional_bps"], 0, 1000)
            or rate["regional_bps"] not in (0, 1000)
            or not number(rate["tax_bps"], 0, 10000)
            or not number(rate["per_attempt_micro"], 0, CEILING)
            or not number(rate["fixed_micro"], 0, CEILING)
            or not number(rate["rounding_micro"], 1, 100000)):
        raise ValueError("unknown rate/fee")
    payload = encode({"source": {"id": source["id"], "version": source["version"]},
                      "text": TEXT}).encode()
    permits = {}
    if type(data["permits"]) is not list or len(data["permits"]) > 536:
        raise ValueError("permit list")
    for row in data["permits"]:
        if (not closed(row, "suite execution stage fields digest allow_send")
                or type(row["suite"]) is not str or row["suite"] not in SUITES
                or not number(row["execution"], 1, SUITES[row["suite"]])
                or not number(row["stage"], 1, 2) or row["fields"] != ["source", "text"]
                or row["digest"] != digest(payload) or type(row["allow_send"]) is not bool):
            raise ValueError("invalid permit")
        key = row["suite"], row["execution"], row["stage"]
        if key in permits:
            raise ValueError("duplicate permit")
        permits[key] = row["allow_send"]
    diagnostics = data["diagnostics"]
    if (type(diagnostics) is not list or len(diagnostics) > CONTINGENCY
            or not all(number(x, 1, CONTINGENCY) for x in diagnostics)
            or len(set(diagnostics)) != len(diagnostics)):
        raise ValueError("diagnostics")
    return data, payload, permits, frozenset(diagnostics)


class FakeTransport:
    """Scripted observations and a local metadata trace. Accepts no callbacks."""
    __slots__ = ("_scenario", "_calls")

    def __init__(self, scenario="ok"):
        self._scenario = scenario
        self._calls = []

    @property
    def calls(self):
        return tuple(self._calls)

    def _observe(self, attempt, payload, model, tier, rate_hash, fixed, source):
        self._calls.append((attempt, digest(payload)))
        scenario = self._scenario
        receipt = {
            "attempt": attempt, "request": digest(payload), "model": model, "tier": tier,
            "rate": rate_hash, "fixed": fixed, "input": 100, "output": 50,
            "status": scenario if scenario in HARD | TRANSIENT else "ok",
            "output_data": {"citation": source, "disposition": "proposal-only"},
        }
        mutations = {
            "forged": ("request", "0" * 64), "out-of-order": ("attempt", attempt + 1),
            "model": ("model", "mutable"), "tier": ("tier", "unexpected"),
            "rate": ("rate", "0" * 64), "fixed": ("fixed", fixed + 1),
            "over-token": ("input", 8001),
        }
        if scenario in mutations:
            key, value = mutations[scenario]
            receipt[key] = value
        if scenario in {"missing", "timeout", "partial", "ambiguous", "cancel"}:
            del receipt["output"]
        if scenario == "price-action":
            receipt["output_data"]["amount"] = 1
        if scenario == "tool":
            receipt["output_data"]["tool_call"] = "fake"
        if scenario in {"foreign-output", "stale-output"}:
            receipt["output_data"]["citation"] = ["NHD", "SYN-GW-NHD-01", 0]
            if scenario == "foreign-output":
                receipt["output_data"]["citation"][0] = "HANU"
        return receipt


class Gateway:
    def __init__(self, path, raw, approval, fake, clock):
        if type(fake) is not FakeTransport:
            raise Rejected("transport")
        self._db_path = Path(path).resolve().as_uri() + "?mode=rw"
        self._fake = fake
        self._clock = clock
        self._invalid = False
        self._digest = digest(raw) if type(raw) is bytes else ""
        self._approval = approval
        self.worker = None
        self.session = None
        self._data = self._rate = None
        try:
            self._data, self._payload, self._permits, self._diagnostics = parse_manifest(raw)
            self._rate = self._data["rate"]
            self._rate_hash = digest(encode(self._rate).encode())
            self._source = self._data["source"]
            self._worst = charge(self._rate, 8000, 1000)
        except (ValueError, TypeError, OverflowError, RecursionError):
            pass

    @contextmanager
    def _transaction(self):
        if self._invalid:
            raise Rejected("storage")
        db = None
        try:
            db = sqlite3.connect(self._db_path, uri=True, timeout=12, isolation_level=None)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            actual = frozenset(row[0] for row in db.execute(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
            if actual != EXPECTED_SCHEMA:
                raise sqlite3.DatabaseError("unexpected ledger schema")
            yield db
            db.commit()
        except sqlite3.Error as exc:
            raise Rejected("storage") from exc
        finally:
            if db is not None:
                db.close()

    def _approved(self, approval):
        return (type(approval) is Approval and bool(self._data)
                and approval.manifest == self._digest
                and type(approval.serial) is str
                and re.fullmatch("[a-zA-Z0-9-]{1,80}", approval.serial) is not None
                and number(approval.expiry, self._clock() + 1, 2**53))

    def _source_active(self):
        return self._source["active_from"] <= self._clock() < self._source["active_until"]

    @classmethod
    def create(cls, path, raw, approval, fake, *, clock):
        self = cls(path, raw, approval, fake, clock)
        # Exclusive creation prevents accidental reset of any existing run file.
        with Path(path).open("xb"):
            pass
        db = sqlite3.connect(self._db_path, uri=True, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            for sql in SCHEMA:
                db.execute(sql)
            active = self._approved(approval) and self._source_active()
            serial = approval.serial if active else "invalid-approval"
            self.worker, self.session = secrets.token_hex(16), secrets.token_hex(16)
            db.execute("INSERT INTO run VALUES (1,?,?,?,?,?,?,?)",
                       (self._digest, serial, approval.expiry if active else 0,
                        self.worker, self.session, "ACTIVE" if active else "STOPPED",
                        "" if active else "invalid-manifest-approval"))
            db.execute("INSERT INTO approval VALUES (?)", (serial,))
            db.commit()
        finally:
            db.close()
        return self

    @staticmethod
    def _run(db):
        row = db.execute("SELECT * FROM run WHERE id=1").fetchone()
        if row is None:
            raise sqlite3.DatabaseError("missing run")
        return row

    @classmethod
    def join(cls, path, raw, approval, worker, fake, *, clock):
        self = cls(path, raw, approval, fake, clock)
        with self._transaction() as db:
            run = self._run(db)
            if type(worker) is not str or worker != run["worker"]:
                raise Rejected("worker")
            if (type(approval) is not Approval or approval.manifest != run["manifest"]
                    or self._digest != run["manifest"] or approval.serial != run["serial"]
                    or approval.expiry != run["expiry"]):
                raise Rejected("approval")
            self.worker = worker
            self.session = run["session"]
        return self

    @classmethod
    def restart(cls, path, raw, approval, fake, *, clock):
        self = cls(path, raw, approval, fake, clock)
        with self._transaction() as db:
            run = self._run(db)
            if self._digest != run["manifest"]:
                raise Rejected("approval")
            self.worker, self.session = secrets.token_hex(16), secrets.token_hex(16)
            db.execute("""UPDATE run SET worker=?,session=?,
                       reason=CASE WHEN status='ACTIVE' THEN 'restart' ELSE reason END,
                       status='STOPPED' WHERE id=1""", (self.worker, self.session))
        return self

    @staticmethod
    def _stop(db, code):
        db.execute("UPDATE run SET status='STOPPED',reason=? WHERE id=1 AND status='ACTIVE'",
                   (code,))

    def stop(self):
        with self._transaction() as db:
            run = self._run(db)
            if run["worker"] != self.worker:
                raise Rejected("worker")
            self._stop(db, "operator")

    def _denial(self, db):
        run = self._run(db)
        if run["status"] != "ACTIVE":
            return "stopped"
        if run["worker"] != self.worker:
            return "worker"
        if (not self._data or run["manifest"] != self._digest
                or type(self._approval) is not Approval
                or self._approval.serial != run["serial"]):
            self._stop(db, "approval")
            return "approval"
        if not self._approved(self._approval) or self._approval.expiry != run["expiry"]:
            self._stop(db, "expired")
            return "expired"
        if not self._source_active():
            self._stop(db, "source")
            return "source"
        if db.execute("""SELECT 1 FROM attempt a LEFT JOIN settlement s USING(id)
                      WHERE s.id IS NULL AND a.deadline<=?""", (self._clock(),)).fetchone():
            self._stop(db, "stale")
            return "stale"
        return None

    @staticmethod
    def _totals(db):
        return db.execute(
            """SELECT COUNT(*), COALESCE(SUM(CASE WHEN s.id IS NULL THEN a.worst ELSE 0 END),0),
               COALESCE(SUM(s.charge),0), COUNT(*)-COUNT(s.id)
               FROM attempt a LEFT JOIN settlement s USING(id)""").fetchone()

    def _validate_history(self, db):
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise Rejected("storage")
        if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise Rejected("storage")
        rows = db.execute("""SELECT a.*,o.receipt,s.charge,s.result FROM attempt a
            LEFT JOIN observation o USING(id) LEFT JOIN settlement s USING(id) ORDER BY a.id""")
        history = {}
        quota = dict.fromkeys((*SUITES, "contingency"), 0)
        for row in rows:
            identifier = row["id"]
            if identifier != len(history) + 1 or identifier > MAX_ATTEMPTS:
                raise Rejected("storage")
            code = self._case(row["suite"], row["execution"], row["stage"], row["kind"])
            if code or row["digest"] != digest(self._payload) or row["worst"] != self._worst:
                raise Rejected("storage")
            parent = history.get(row["parent"])
            if not self._parent_ok(parent, row["suite"], row["execution"], row["stage"], row["kind"]):
                raise Rejected("storage")
            bucket = row["suite"] if row["kind"] == "initial" else "contingency"
            quota[bucket] += 1
            cap = CONTINGENCY if bucket == "contingency" else SUITES[bucket] * 2
            if quota[bucket] > cap:
                raise Rejected("storage")
            if row["charge"] is None:
                raise Rejected("uncertain")
            try:
                result, amount = self._judge(row, json.loads(row["receipt"]))
            except (TypeError, ValueError) as exc:
                raise Rejected("storage") from exc
            if result != row["result"] or amount != row["charge"]:
                raise Rejected("storage")
            history[identifier] = row
        _, hold, actual, _ = self._totals(db)
        if self._rate["fixed_micro"] + hold + actual > CEILING:
            raise Rejected("storage")

    def resume(self, approval):
        with self._transaction() as db:
            run = self._run(db)
            if (run["worker"] != self.worker or run["status"] != "STOPPED"
                    or run["reason"] != "restart" or not self._approved(approval)
                    or not self._source_active()
                    or db.execute("SELECT 1 FROM approval WHERE serial=?",
                                  (approval.serial,)).fetchone()):
                raise Rejected("approval")
            self._validate_history(db)
            db.execute("INSERT INTO approval VALUES (?)", (approval.serial,))
            db.execute("UPDATE run SET status='ACTIVE',serial=?,expiry=?,reason='' WHERE id=1",
                       (approval.serial, approval.expiry))
        self._approval = approval

    def _case(self, suite, execution, stage, kind):
        if type(suite) is not str or suite not in SUITES or type(kind) is not str:
            return "case"
        if kind == "diagnostic":
            return (None if number(stage, 0, 0) and type(execution) is int
                    and execution in self._diagnostics else "capacity")
        if (kind not in {"initial", "retry"} or not number(execution, 1, SUITES[suite])
                or not number(stage, 1, 2)):
            return "case"
        permit = self._permits.get((suite, execution, stage))
        return "case" if permit is None else None if permit else "zero-egress"

    @staticmethod
    def _parent_ok(parent, suite, execution, stage, kind):
        if kind == "initial":
            return parent is None
        if parent is None or parent["kind"] != "initial" or parent["suite"] != suite:
            return False
        if kind == "diagnostic":
            return parent["result"] in ("ok", "transient")
        return (parent["execution"] == execution and parent["stage"] == stage
                and parent["result"] == "transient")

    def _admit(self, db, session, suite, execution, stage, payload, kind, parent, fault):
        code = self._denial(db)
        if code:
            return code
        if session != self.session or type(session) is not str:
            return "session"
        if type(payload) is not bytes or payload != self._payload:
            self._stop(db, "payload")
            return "payload"
        code = self._case(suite, execution, stage, kind)
        if code:
            return code
        if kind == "initial" and parent is not None or (
                kind != "initial" and not number(parent, 1, MAX_ATTEMPTS)):
            return "parent"
        parent_record = db.execute("""SELECT a.*,s.result FROM attempt a
            LEFT JOIN settlement s USING(id) WHERE a.id=?""", (parent,)).fetchone()
        if not self._parent_ok(parent_record, suite, execution, stage, kind):
            return "parent"
        if db.execute("SELECT 1 FROM attempt WHERE suite=? AND execution=? AND stage=? AND kind=?",
                      (suite, execution, stage, kind)).fetchone():
            return "duplicate"
        if kind == "diagnostic" and db.execute(
                "SELECT 1 FROM attempt WHERE kind='diagnostic' AND execution=?",
                (execution,)).fetchone():
            return "duplicate"
        attempts, hold, actual, inflight = self._totals(db)
        bucket_sql = ("kind='initial' AND suite=?" if kind == "initial" else "kind!='initial'")
        params = (suite,) if kind == "initial" else ()
        used = db.execute("SELECT COUNT(*) FROM attempt WHERE " + bucket_sql, params).fetchone()[0]
        cap = SUITES[suite]*2 if kind == "initial" else CONTINGENCY
        if attempts >= MAX_ATTEMPTS or used >= cap:
            self._stop(db, "capacity")
            return "capacity"
        # Only an all-performance batch can open the five-request window.
        if inflight and (suite != "performance" or kind == "diagnostic" or inflight >= 5
                         or db.execute("""SELECT 1 FROM attempt a LEFT JOIN settlement s USING(id)
                            WHERE s.id IS NULL AND (a.suite!='performance' OR a.kind='diagnostic')"""
                                       ).fetchone()):
            return "in-flight"
        if self._rate["fixed_micro"] + hold + actual + self._worst > CEILING:
            self._stop(db, "money")
            return "money"
        if fault == "before-write":
            raise sqlite3.OperationalError("injected write fault")
        nonce = secrets.token_hex(16)
        deadline = min(self._clock() + 30, self._approval.expiry)
        if kind != "diagnostic":
            first = db.execute("""SELECT MIN(deadline) FROM attempt
                               WHERE suite=? AND execution=? AND kind!='diagnostic'""",
                               (suite, execution)).fetchone()[0]
            if first is not None:
                deadline = min(deadline, first)
            if deadline <= self._clock():
                return "stage-deadline"
        row = db.execute("INSERT INTO attempt VALUES (NULL,?,?,?,?,?,?,?,?,?)",
                         (suite, execution, stage, kind, parent, digest(payload),
                          nonce, self._worst, deadline))
        if fault == "after-write":
            raise sqlite3.OperationalError("injected write fault")
        return Permit(row.lastrowid, nonce)

    def reserve(self, session, suite, execution, stage, payload, *,
                kind="initial", parent=None, fault=None):
        if fault == "before-reserve":
            raise SimulatedCrash()
        try:
            with self._transaction() as db:
                outcome = self._admit(db, session, suite, execution, stage, payload, kind, parent, fault)
        except Rejected as error:
            if error.code == "storage":
                self._storage_stop()
            raise
        if type(outcome) is not Permit:
            raise Rejected(outcome)
        if fault == "after-reserve":
            raise SimulatedCrash()
        return outcome

    def _storage_stop(self):
        try:
            self.stop()
        except Rejected:
            self._invalid = True

    def _consume(self, db, permit, payload):
        code = self._denial(db)
        if code:
            return code
        row = None
        if type(permit) is Permit and number(permit.attempt, 1, MAX_ATTEMPTS):
            row = db.execute("""SELECT a.*,i.id AS consumed FROM attempt a
                LEFT JOIN intent i USING(id) WHERE a.id=?""", (permit.attempt,)).fetchone()
        if row is None or row["nonce"] != permit.nonce or row["consumed"] is not None:
            return "permit"
        if type(payload) is not bytes or payload != self._payload or digest(payload) != row["digest"]:
            self._stop(db, "payload")
            return "payload"
        db.execute("INSERT INTO intent VALUES (?)", (row["id"],))
        return row

    def _judge(self, row, receipt):
        if (not closed(receipt, "attempt request model tier rate fixed input output status output_data")
                or not number(receipt["attempt"], row["id"], row["id"])
                or receipt["request"] != row["digest"] or receipt["model"] != MODEL
                or receipt["tier"] != "standard" or receipt["rate"] != self._rate_hash
                or not number(receipt["fixed"], self._rate["fixed_micro"], self._rate["fixed_micro"])
                or not number(receipt["input"], 0, 8000)
                or not number(receipt["output"], 0, 1000)
                or type(receipt["status"]) is not str
                or receipt["status"] not in HARD | TRANSIENT | {"ok"}
                or receipt["output_data"] != {"citation": ["NHD", self._source["id"],
                                                          self._source["version"]],
                                              "disposition": "proposal-only"}):
            return "receipt", 0
        result = ("hard-response" if receipt["status"] in HARD else
                  "transient" if receipt["status"] in TRANSIENT else "ok")
        amount = charge(self._rate, receipt["input"], receipt["output"])
        return (result, amount) if amount <= row["worst"] else ("receipt", 0)

    def dispatch(self, permit, payload, *, kind=None, parent=None, fault=None):
        # kind/parent are admitted solely from the stored permit, never from dispatch hints.
        try:
            with self._transaction() as db:
                row = self._consume(db, permit, payload)
            if type(row) is str:
                raise Rejected(row)
            if fault == "after-intent":
                raise SimulatedCrash()
            with self._transaction() as db:
                code = self._denial(db)
                if not code:
                    # Only the primitive fake observation runs under the STOP lock.
                    receipt = FakeTransport._observe(
                        self._fake, row["id"], payload, MODEL, "standard", self._rate_hash,
                        self._rate["fixed_micro"], ["NHD", self._source["id"], self._source["version"]])
                    if fault == "after-send":
                        raise SimulatedCrash()
                    db.execute("INSERT INTO observation VALUES (?,?)", (row["id"], encode(receipt)))
                    result, amount = self._judge(row, receipt)
                    if result in ("hard-response", "receipt"):
                        self._stop(db, result)
            if code:
                raise Rejected(code)
            if fault == "after-observation":
                raise SimulatedCrash()
            with self._transaction() as db:
                if result != "receipt":
                    db.execute("INSERT INTO settlement VALUES (?,?,?)", (row["id"], amount, result))
                if result in {"ok", "transient"} and self._denial(db):
                    result = "stopped"
            if result not in {"ok", "transient"}:
                raise Rejected(result)
            return result
        except Rejected as error:
            if error.code == "storage":
                self._storage_stop()
            raise

    def snapshot(self):
        with self._transaction() as db:
            attempts, hold, actual, inflight = self._totals(db)
            buckets = dict.fromkeys((*SUITES, "contingency"), 0)
            origins = {suite: {"sent": 0, "failed": 0} for suite in SUITES}
            for row in db.execute("""SELECT a.suite,a.kind,i.id AS intended,s.result FROM attempt a
                LEFT JOIN intent i USING(id) LEFT JOIN settlement s USING(id)"""):
                buckets[row["suite"] if row["kind"] == "initial" else "contingency"] += 1
                if row["intended"] is not None and row["kind"] != "diagnostic":
                    origin = origins[row["suite"]]
                    origin["sent"] += 1  # conservative: includes ambiguous intent
                    origin["failed"] += row["result"] != "ok"
            run = self._run(db)
            fixed = self._rate["fixed_micro"] if self._rate else None
            return {"status": run["status"], "reason": run["reason"], "attempts": attempts,
                    "outstanding_micro": hold, "actual_micro": actual, "fixed_micro": fixed,
                    "committed_micro": None if fixed is None else actual + hold + fixed,
                    "protected_micro": PROTECTED, "in_flight": inflight,
                    "by_bucket": buckets, "by_origin": origins}
