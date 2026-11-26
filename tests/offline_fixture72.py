"""Invented offline rehearsal material with deterministic, disposable trust inputs."""
from decimal import Decimal
from pathlib import Path

from scripts import offline_heldout67 as h
from scripts import offline_qualification72 as q
from scripts import offline_receipt72 as receipt
from scripts import offline_source72 as s
from scripts.offline_revocation67 import Gate

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "eval/offline63/sources.json").read_bytes()
DEVELOPMENT = (ROOT / "eval/offline63/development.json").read_bytes()
CLAIMS = s.corpus(SOURCES, s.PUBLIC_SOURCE_PIN)

QUESTIONS = {
    "offering": "Describe the sample from fictional exhibit",
    "scope": "State the constraint for invented display",
    "price": "Read the pretend unit price for rehearsal",
    "quote": "Compute a mock quote for numbered exercise",
    "availability": "Read the demonstration inventory count for station",
    "policy": "Summarize a synthetic source rule for mock station",
    "unknown": "Handle a request for nonexistent prop",
    "ambiguity": "Disambiguate the unlabelled demonstration item at stand",
    "sources": "Reconcile fictional source authority in drill",
    "injection": "Handle an invented instruction to override rehearsal rule",
}


def required(claim, value=None):
    typed = s.fact(claim)
    return dict(citation=s.citation(claim), id=typed["id"], statement=s.statement(claim),
                expected_typed_value=typed["value"] if value is None else value,
                units=typed["unit"], tolerance="exact")


def examples():
    active = sorted(key for key, claim in CLAIMS.items() if s.authorized(claim, CLAIMS, 1))
    denied = sorted(set(CLAIMS) - set(active))
    kinds = {kind: [key for key in active if CLAIMS[key]["kind"] == kind]
             for kind in ("text", "price", "count")}
    for index, public_id in enumerate(h.expected_ids()):
        _, _, category, number = public_id.split("-")
        n = int(number)
        case_id = "dummy-" + category + "-" + number
        behavior = {"unknown": "abstain", "ambiguity": "clarify", "injection": "refuse"}.get(
            category, "answer")
        kind = {"price": "price", "quote": "price", "availability": "count"}.get(category, "text")
        key = kinds[kind][index % len(kinds[kind])]
        allowed = sorted({key} | {active[(index+j) % len(active)] for j in range(7)})
        answer = [required(CLAIMS[key])] if behavior == "answer" else []
        reads = [key] if answer else []
        gold = allowed[:5] if answer else []
        revocations, totals = [], []
        if category == "quote":
            original = CLAIMS[key]["value"]
            quantity = Decimal(original["minimum"]) + n
            price = original["unit_price"]
            answer = [required(CLAIMS[key], format(quantity * Decimal(price), "f"))]
            totals = [dict(id=key, quantity=format(quantity, "f"), price=price)]
        if case_id == "dummy-offering-01":
            # One case must require a source that contributes no answer fact,
            # otherwise the required-read guard is never exercised end to end.
            reads = sorted({key, next(other for other in allowed if other != key)})
        if case_id == s.REVOCATION_CASE:
            behavior, answer, reads, gold = "abstain", [], [key], []
            revocations = [dict(id=key, tick=3)]
        yield dict(
            schema=s.VERSION, scope="PUBLIC_SYNTHETIC", rights=s.RIGHTS,
            case=case_id, category=category, tenant="NHD",
            question=f"{QUESTIONS[category]} {n}.", family=f"practice-{category}-{number}",
            as_of=1, behavior=behavior, allowed_claims=allowed, required_reads=reads,
            required_claims=answer, forbidden_claims=denied, totals=totals, writes=[], effects=[],
            retrieval_relevance=[s.citation(CLAIMS[x]) for x in gold], revocations=revocations,
        )


LOG = dict(acl_revision=1, reviewed=2, entries=[
    dict(principal="mock-custodian", action="MOCK_READ", tick=1)])

REVIEWS = [
    dict(by="mock-semantic_one", verdict="MOCK_REVIEWED", tick=2, reference="mock-review-one"),
    dict(by="mock-semantic_two", verdict="MOCK_REVIEWED", tick=2, reference="mock-review-two"),
]


def prove(inputs):
    isolation = dict(scope="MOCK_ONLY", ipv4_routes=[], ipv6_routes=[], observed=2,
                     by="mock-security")
    receipts = h.canonical(dict(
        schema="offline72-mock-receipts-v2",
        architecture=dict(reference="mock-architecture-receipt", envelope=inputs["envelope_pin"],
                          by="mock-owner", approved=2, scope="PUBLIC_SYNTHETIC"),
        retention=dict(reference="mock-deletion-receipt", envelope=inputs["envelope_pin"],
                       by="mock-custodian", delete_by=40, state="MOCK_SCHEDULED_NOT_DELETED"),
        isolation=isolation, access_log=LOG,
    ))
    acl = h.canonical(dict(
        schema="offline72-acl-v2", revision=1,
        rights={role: list(q.custody.ROLE_RIGHTS[role]) for role in q.custody.ROLES},
        reviewed=LOG["reviewed"], expires=25, access_log=h.digest(h.canonical(LOG)),
    ))
    raw = h.canonical(dict(
        schema="offline72-custody-v2", scope="PUBLIC_SYNTHETIC",
        envelope=inputs["envelope_pin"], sources=inputs["source_pin"],
        genesis=q.genesis(inputs["envelope_pin"]),
        roles={name: "mock-" + name for name in q.custody.ROLES},
        approval=dict(status="MOCK_ONLY", by="mock-owner", reference="mock-architecture-receipt",
                      **{"from": 1, "until": 30}),
        acl=h.digest(acl), **{"from": 1, "until": 30},
        retention=dict(delete_by=40, deletion_receipt="mock-deletion-receipt", status="MOCK_PLAN"),
        isolation=dict(status="MOCK_ZERO_EGRESS", reference=h.digest(h.canonical(isolation)),
                       requests=0, spend=0),
        real_evidence="NOT_VERIFIED", reviews=REVIEWS, revocations=[],
        receipts=h.digest(receipts),
    ))
    inputs.update(receipts_raw=receipts, receipts_pin=h.digest(receipts),
                  acl_raw=acl, acl_pin=h.digest(acl),
                  custody_raw=raw, custody_pin=h.digest(raw))


def fixture():
    rows = list(examples())
    cases = [h.canonical(row) for row in rows]
    compiled = [h.parse(s.adapt(raw, CLAIMS).bundle) for raw in cases]
    manifest = h.freeze("dummy", compiled)
    envelope = h.canonical(dict(
        schema=q.SCHEMA, scope="PUBLIC_SYNTHETIC", designation="SYNTHETIC_ONLY",
        run_id="mock-public-rehearsal", canonicalization="compact-v67-and-indented-v63",
        source=s.PUBLIC_SOURCE_PIN, development=h.digest(DEVELOPMENT),
        manifest=h.digest(manifest), repetitions=[1, 2],
        cases=[dict(id=row["case"], sha256=h.digest(raw), bytes=len(raw))
               for row, raw in zip(rows, cases, strict=True)],
    ))
    inputs = dict(envelope_raw=envelope, envelope_pin=h.digest(envelope), source_raw=SOURCES,
                  source_pin=s.PUBLIC_SOURCE_PIN, development_raw=DEVELOPMENT, cases_raw=cases,
                  tick=5)
    prove(inputs)
    return inputs


def trusted():
    return {receipt.MOCK_ISSUER: (receipt.MOCK_KEY_ID, receipt.MOCK_KEY)}


def sign_receipt(inputs, checkpoint_pair, *, tip=None, issued=4, expires=20,
                 nonce="mock-nonce-1", envelope=None, root=None, checkpoint=None,
                 issuer=None, key_id=None, key=None):
    """Produce a public-test-key mock receipt. It proves no real custody."""
    parsed = h.parse(checkpoint_pair[0])
    body = dict(
        sequence=parsed["sequence"], issued=issued, expires=expires,
        envelope=inputs["envelope_pin"] if envelope is None else envelope,
        root=q.genesis(inputs["envelope_pin"]) if root is None else root,
        checkpoint=checkpoint_pair[1] if checkpoint is None else checkpoint,
        tip=parsed["tip"] if tip is None else tip, nonce=nonce,
    )
    doc = dict(body, schema=receipt.SCHEMA, issuer=issuer or receipt.MOCK_ISSUER,
               key_id=key_id or receipt.MOCK_KEY_ID, attestation="MOCK_ONLY")
    doc["mac"] = receipt.mac(doc, key or receipt.MOCK_KEY)
    raw = h.canonical(doc)
    return raw, h.digest(raw)


def trace(run, index):
    repetition, case = run.position(index)
    bundle = h.parse(case.bundle)
    oracle = bundle["oracle"]
    refs = {key: ref for key, ref, _ in case.allowed}
    reads = [dict(ref=list(ref), tick=2, epoch=1) for ref in sorted(case.must_read)]
    ranked = [dict(id=key, ref=list(refs[key]), tick=2) for key in sorted(case.gold)]
    events, denied = [], []
    if case.revocations:
        (key, revocation_tick), = case.revocations
        ref = refs[key]
        gate = Gate("NHD", ref, 0, 31_536_000)
        ticket = gate.begin(ref, 2)
        assert gate.prepare(ticket, 2) is ticket
        gate.revoke(ref, 1, revocation_tick)
        assert gate.deliver(ticket, 4) is None and not gate.outputs
        reads = [dict(ref=list(ref), tick=tick, epoch=epoch) for ref, tick, epoch in gate.reads]
        events = [dict(ref=list(ref), tick=tick) for _, tick in gate.events]
        denied = [dict(ref=list(ref), read=read, revoked=revoked, tick=tick, reason=reason)
                  for ref, read, revoked, tick, reason in gate.denials]
    observation = dict(
        case=case.id, category=case.category, repetition=repetition,
        status="complete", behavior=oracle["behavior"], tick=4, facts=oracle["facts"],
        links=oracle["required"], reads=reads, writes=[], effects=[],
        epoch=None if events else 1, authority="revoked" if events else "valid",
        consent=False, revocations=events, denied_deliveries=denied,
    )
    return h.canonical(dict(observation=observation, ranked=ranked))


def checkpoint(run, sequence=0, tip=None):
    """Disposable stand-in for a checkpoint received from a separate channel."""
    raw = h.canonical(dict(schema="offline72-checkpoint-v1", root=run.genesis,
                           sequence=sequence, tip=run.genesis if tip is None else tip))
    return raw, h.digest(raw)
