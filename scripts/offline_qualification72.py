"""Official qualification for the public-synthetic v72 rehearsal only."""
from dataclasses import dataclass

from scripts import offline_custody72 as custody
from scripts import offline_evidence69 as evidence
from scripts import offline_heldout67 as h
from scripts import offline_source72 as source
from scripts.offline_journal69 import OUTCOMES, SQLiteChain

SCHEMA = "offline72-envelope-v1"
SIZE = 60
# Digest over the 60 ordered raw case SHA-256 values of the reviewed public
# profile. A new corpus is a new profile version, not a resealed envelope.
PUBLIC_CASESET_PIN = "ded0730ddbfdf98340f604b68a1301fa3253af8add609e987111f9cd26ef7970"
FIELDS = ("envelope index tick case repetition bundle guards observation outcome code "
          "hits gold previous")


@dataclass(frozen=True)
class _Run:
    envelope: str
    manifest: bytes
    manifest_pin: str
    genesis: str
    start: int
    until: int
    verified_at: int
    cases: tuple

    def position(self, index):
        h.require(h.integer(index, 0, 2*SIZE-1), "journal-position")
        repetition, offset = divmod(index, SIZE)
        return repetition+1, self.cases[offset]


def genesis(envelope_pin):
    return h.digest(h.canonical({"schema": "offline72-genesis-v1", "envelope": envelope_pin}))


def caseset(cases_raw):
    """Ordered digest of the exact raw case bytes; guards live in these bytes."""
    h.require(type(cases_raw) in (tuple, list), "case-inventory")
    return h.digest(h.canonical([h.digest(raw) for raw in cases_raw]))


def prepare(*, envelope_raw, envelope_pin, source_raw, source_pin, development_raw, cases_raw,
            custody_raw, custody_pin, acl_raw, acl_pin, receipts_raw, receipts_pin, tick):
    envelope = source.checked(envelope_raw, envelope_pin)
    h.require(type(envelope) is dict and envelope.get("schema") == SCHEMA
              and envelope.get("scope") == "PUBLIC_SYNTHETIC", "private-not-authorized")
    h.shape(envelope, "schema scope designation run_id canonicalization source development manifest cases repetitions")
    h.require(envelope["designation"] == "SYNTHETIC_ONLY" and h.token(envelope["run_id"])
              and envelope["run_id"].startswith("mock-")
              and envelope["canonicalization"] == "compact-v67-and-indented-v63"
              and type(envelope["repetitions"]) is list and len(envelope["repetitions"]) == 2
              and all(h.integer(n, i, i) for i, n in enumerate(envelope["repetitions"], 1))
              and envelope["source"] == source_pin
              and envelope["development"] == evidence.DEV_SHA, "envelope-policy")
    root = genesis(envelope_pin)
    custody_run = custody.verify(custody_raw, custody_pin, acl_raw, acl_pin, receipts_raw,
                                 receipts_pin, envelope=envelope_pin,
                                 sources=source_pin, genesis=root, tick=tick)
    start, until = custody_run.start, custody_run.until
    claims = source.corpus(source_raw, source_pin)
    entries = h.array(envelope["cases"], SIZE)
    h.require(type(cases_raw) in (tuple, list) and len(entries) == len(cases_raw) == SIZE,
              "case-inventory")
    cases = []
    for expected, entry, raw in zip(h.expected_ids(), entries, cases_raw, strict=True):
        case_id = expected.replace("ga61-qa-", "dummy-", 1)
        h.shape(entry, "id sha256 bytes")
        h.require(entry["id"] == case_id and type(raw) is bytes
                  and h.integer(entry["bytes"], 1, h.MAX_BYTES) and entry["bytes"] == len(raw)
                  and h.digest(raw) == entry["sha256"], "case-pin")
        case = source.adapt(raw, claims)
        h.require(case.id == case_id, "case-binding")
        cases.append(case)
    manifest = evidence.freeze_screened("dummy", [h.parse(case.bundle) for case in cases],
                                       development_raw, evidence.pin(development_raw))
    manifest_pin = h.digest(manifest)
    h.require(envelope["manifest"] == manifest_pin, "manifest-pin")
    # The manifest covers compiled bundles only. required_reads and
    # forbidden_claims are not bundle fields, so the raw case profile must be
    # pinned independently or a caller could strip a safeguard and still match.
    h.require(caseset(cases_raw) == PUBLIC_CASESET_PIN, "case-profile")
    ledger_root = custody.ledger_root(root, custody_pin, acl_pin)
    return _Run(envelope_pin, manifest, manifest_pin, ledger_root, start, until, tick, tuple(cases))


@dataclass(frozen=True)
class Grade:
    """Preview from the same scoring function used by the coordinator."""
    outcome: str
    code: str
    hits: int | None = None
    gold: int | None = None


def _score(run, index, raw):
    _, case = run.position(index)
    try:
        if raw is None:
            return Grade("NOT_RUN", "no-observation")
        trace = h.parse(raw)
        h.shape(trace, "observation ranked")
        obs = trace["observation"]
        diagnostic = h.evaluate(run.manifest, run.manifest_pin, index, case.bundle,
                                h.canonical(obs), required_reads=case.must_read,
                                forbidden_fact_ids=case.forbidden)
        if diagnostic.outcome == "STOP":
            return Grade(diagnostic.outcome, diagnostic.code)
        h.require(h.integer(obs["tick"], case.start)
                  and all(read["tick"] >= case.start for read in obs["reads"]), "case-clock")
        hits, gold = source.recall(case, trace["ranked"], obs["tick"])
        if diagnostic.outcome == "INCONCLUSIVE":
            return Grade(diagnostic.outcome, diagnostic.code)
        return Grade(diagnostic.outcome, diagnostic.code, hits, gold)
    except h.Invalid as error:
        return Grade("STOP", str(error))


def evaluate(index, raw, **materials):
    """Return authoritative-policy preview, without ledger or receipt authority."""
    return _score(prepare(**materials), index, raw)


@dataclass(frozen=True)
class PendingAnchor:
    index: int
    anchor: str


@dataclass(frozen=True)
class Receipt:
    index: int
    case: str
    repetition: int
    outcome: str
    code: str
    hits: int | None
    gold: int | None
    row_anchor: str
    verified_tip: str
    chain_length: int
    guards: str
    # The external checkpoint is caller-supplied. This value records that the
    # chain is internally consistent, not that a custodian/WORM store issued it.
    trust: str = "EXTERNAL_ANCHOR_UNVERIFIED"


class Runner:
    """Append to SQLite, then confirm separately using the custodian's latest tip.

    The adapter never publishes or retrieves an anchor. Callers must obtain it
    from a separate trusted channel. Candidate anchors are not official receipts.
    """
    def __init__(self, store):
        self._store = store
        self._run = store._approved

    @classmethod
    def create(cls, path, **materials):
        return cls(SQLiteChain.create(path, prepare(**materials)))

    @classmethod
    def open(cls, path, latest_anchor, **materials):
        runner = cls(SQLiteChain(path, prepare(**materials)))
        with runner._store._transaction() as db:
            runner._history(db, latest_anchor)
        return runner

    def _history(self, db, external, *, recovering=False):
        h.require(type(external) is tuple and len(external) == 2, "externally-pinned-anchor")
        checkpoint = source.checked(*external)
        h.shape(checkpoint, "schema root sequence tip")
        h.require(checkpoint["schema"] == "offline72-checkpoint-v1"
                  and checkpoint["root"] == self._run.genesis
                  and h.integer(checkpoint["sequence"], 0, 2*SIZE)
                  and h.is_hash(checkpoint["tip"]), "checkpoint-binding")
        anchor = checkpoint["tip"]
        tip = self._run.genesis
        h.require(db.execute("SELECT id,genesis FROM journal_context").fetchall() == [(1, tip)],
                  "journal-context")
        rows = []
        last_tick = self._run.start
        for seq, raw, next_tip in db.execute("SELECT seq,payload,anchor FROM receipt ORDER BY seq"):
            repetition, case = self._run.position(len(rows))
            h.require(seq == len(rows)+1 and (not rows or rows[-1][0]["outcome"] != "STOP"),
                      "journal-chain")
            row = h.parse(raw)
            h.shape(row, FIELDS)
            h.require(row["previous"] == tip and h.digest(raw) == next_tip
                      and row["envelope"] == self._run.envelope and row["case"] == case.id
                      and row["bundle"] == h.digest(case.bundle)
                      and row["guards"] == case.guards and h.is_hash(row["guards"])
                      and h.integer(row["index"], seq-1, seq-1)
                      and h.integer(row["repetition"], repetition, repetition)
                      and h.integer(row["tick"], last_tick) and row["outcome"] in OUTCOMES
                      and h.token(row["code"])
                      and (row["observation"] == "ABSENT" or h.is_hash(row["observation"]))
                      and (row["hits"] is None or h.integer(row["hits"], 0, 5))
                      and (row["gold"] is None or h.integer(row["gold"], 0, source.PUBLIC_SOURCE_COUNT)),
                      "journal-receipt")
            rows.append((row, next_tip))
            tip, last_tick = next_tip, row["tick"]
        if recovering:
            h.require(len(rows) == checkpoint["sequence"]+1
                      and rows[-1][0]["previous"] == anchor, "recovery-anchor")
        else:
            h.require(len(rows) == checkpoint["sequence"] and tip == anchor, "anchor-mismatch")
        return rows

    def _candidate(self, index, raw, tick, previous):
        repetition, case = self._run.position(index)
        h.require((raw is None or type(raw) is bytes) and h.integer(tick, self._run.start),
                  "submission")
        grade = (_score(self._run, index, raw) if tick < self._run.until
                 else Grade("STOP", "expired-mock-custody"))
        return dict(envelope=self._run.envelope, index=index, tick=tick, case=case.id,
                    repetition=repetition, bundle=h.digest(case.bundle), guards=case.guards,
                    observation="ABSENT" if raw is None else h.digest(raw),
                    outcome=grade.outcome, code=grade.code, hits=grade.hits, gold=grade.gold,
                    previous=previous)

    def submit(self, index, raw, tick, latest_anchor):
        """Commit exactly one position and return a proposal for external pinning."""
        self._run.position(index)
        with self._store._transaction() as db:
            rows = self._history(db, latest_anchor)
            if index < len(rows):
                old, anchor = rows[index]
                proposed = self._candidate(index, raw, tick, old["previous"])
                h.require(proposed == old, "changed-replay")
                return PendingAnchor(index, anchor)
            h.require(index == len(rows), "ledger-order")
            h.require(not rows or rows[-1][0]["outcome"] != "STOP", "ledger-stopped")
            h.require(not rows or h.integer(tick, rows[-1][0]["tick"]), "rewound-clock")
            h.require(h.integer(tick, self._run.verified_at), "rewound-clock")
            tip = rows[-1][1] if rows else self._run.genesis
            row = self._candidate(index, raw, tick, tip)
            payload = h.canonical(row)
            anchor = h.digest(payload)
            db.execute("INSERT INTO receipt VALUES (?,?,?)", (index+1, payload, anchor))
            return PendingAnchor(index, anchor)

    @classmethod
    def recover(cls, path, index, raw, submission_tick, latest_anchor, **materials):
        """Recompute one unpinned tail from caller-supplied evidence, without promoting it."""
        runner = cls(SQLiteChain(path, prepare(**materials)))
        with runner._store._transaction() as db:
            rows = runner._history(db, latest_anchor, recovering=True)
            old, anchor = rows[-1]
            h.require(runner._candidate(index, raw, submission_tick, old["previous"]) == old, "recovery-evidence")
            return PendingAnchor(index, anchor)

    def confirm(self, index, latest_anchor):
        self._run.position(index)
        with self._store._transaction() as db:
            rows = self._history(db, latest_anchor)
            h.require(index < len(rows), "uncommitted-receipt")
            row, anchor = rows[index]
            return Receipt(index, row["case"], row["repetition"], row["outcome"], row["code"],
                           row["hits"], row["gold"], anchor, rows[-1][1], len(rows), row["guards"])
