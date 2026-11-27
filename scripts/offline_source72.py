"""Closed public-synthetic custody adapter and claim-level retrieval scoring."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Context, localcontext

from scripts import offline_corpus63 as c
from scripts import offline_evidence69 as e
from scripts import offline_heldout67 as h

VERSION = "offline72-case-v1"
RIGHTS = "invented-no-third-party-text"
PUBLIC_SOURCE_PIN = "8a4a86a8c613ba3030d142db7f0f409bbbc9f80fcd962ae7099b090998c5bffb"
PUBLIC_SOURCE_COUNT = 37
START = datetime(2030, 1, 1, tzinfo=timezone.utc)
# The slot used for the public revocation simulation, with an invented payload.
REVOCATION_CASE = "dummy-sources-06"


def checked(raw, pin, parser=h.parse):
    h.require(type(raw) is bytes and 0 < len(raw) <= h.MAX_BYTES
              and h.is_hash(pin) and h.digest(raw) == pin, "artifact-pin")
    return parser(raw)


def corpus(raw, pin):
    # This version supports exactly the audited Issue 63 source corpus. A new
    # corpus needs its own inventory profile and independent pin.
    records = checked(raw, pin, e._parse_indented)
    h.require(type(records) is dict and type(records.get("claims")) is list
              and len(records["claims"]) == PUBLIC_SOURCE_COUNT, "source-inventory")
    h.require(pin == PUBLIC_SOURCE_PIN, "source-profile")
    c.validate_sources(records)
    return {claim_id(claim): claim for claim in records["claims"]}


def claim_id(claim):
    return "claim-" + h.digest(h.canonical([claim["tenant"], *c.reference(claim)]))


def citation(claim):
    return dict(document=claim["document"], version=claim["version"],
                paragraph=claim["paragraph"], source_sha256=h.digest(c.canonical(claim)))


def statement(claim):
    return claim["subject"] + "/" + claim["predicate"]


def tick_of(value):
    return (c.timestamp(value) - START) // timedelta(seconds=1)


def authorized(claim, all_claims, tick):
    now = START + timedelta(seconds=tick)
    if not c.eligible(claim, now):
        return False
    return sum(other["subject"] == claim["subject"] and
               other["predicate"] == claim["predicate"] and c.eligible(other, now)
               for other in all_claims.values()) == 1


def fact(claim):
    value = claim["value"]
    kind = claim["kind"]
    key = claim_id(claim)
    if kind == "text":
        return dict(id=key, kind="text", unit=None, value=value)
    if kind == "count":
        # Bind the count to its original claim. Its unit is a count, not a SKU unit.
        return dict(id=key, kind="integer", unit="count", value=value)
    if kind == "price":
        return dict(id=key, kind="decimal", unit=value["currency"], value=value["unit_price"])
    raise h.Invalid("unsupported-source-value")


def ordered_ids(values):
    h.require(type(values) is list and all(h.token(key) for key in values)
              and values == sorted(set(values)), "claim-order")
    return frozenset(values)


def guards_digest(must_read, forbidden):
    """Bind the exact safeguard set so a receipt names the guards that applied."""
    return h.digest(h.canonical({"required": sorted([list(ref) for ref in must_read]),
                                 "forbidden": sorted(forbidden)}))


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    bundle: bytes
    allowed: tuple
    must_read: frozenset
    forbidden: frozenset
    gold: frozenset
    start: int
    revocations: tuple
    guards: str


def adapt(raw, claims):
    item = h.parse(raw)
    h.require(type(item) is dict and item.get("schema") == VERSION
              and item.get("scope") == "PUBLIC_SYNTHETIC", "private-not-authorized")
    required = ("schema scope rights case category tenant question family as_of behavior "
                "allowed_claims required_reads required_claims forbidden_claims totals "
                "writes effects retrieval_relevance revocations")
    h.require(item.keys() == set(required.split()), "unsupported-case-fields")
    h.require(item["rights"] == RIGHTS and item["tenant"] == "NHD", "case-scope")
    h.validate_case_id(item["case"], item["category"], "dummy")
    start = item["as_of"]
    h.require(h.integer(start, 0, 31_536_000), "source-clock")
    h.require(c.safe_text(item["question"]) and h.token(item["family"]), "synthetic-case")

    allowed = ordered_ids(item["allowed_claims"])
    forbidden = ordered_ids(item["forbidden_claims"])
    must_read = ordered_ids(item["required_reads"])
    h.require(allowed <= claims.keys() and forbidden <= claims.keys()
              and allowed.isdisjoint(forbidden) and must_read <= allowed, "claim-policy")
    for key in allowed:
        h.require(authorized(claims[key], claims, start), "source-authority")

    # Only the public audit corpus is supported. One corpus record has one
    # citation and one claim ID. Every mapping binds the original excerpt bytes.
    by_ref = {c.reference(claim): key for key, claim in claims.items()}

    def resolve(cite):
        h.shape(cite, "document paragraph source_sha256 version")
        _, doc, version, paragraph = h.reference(
            ["NHD", cite["document"], cite["version"], cite["paragraph"]])
        key = by_ref.get((doc, version, paragraph))
        h.require(key in allowed and cite == citation(claims[key]), "source-citation")
        return key

    gold_order = [resolve(cite) for cite in h.array(item["retrieval_relevance"], 37)]
    gold = ordered_ids(gold_order)
    expected, required_ids = [], []
    totals = {}
    for total in h.array(item["totals"], 37):
        h.shape(total, "id quantity price")
        key = total["id"]
        h.require(h.token(key) and key in must_read and key not in totals
                  and claims[key]["kind"] == "price", "total-source")
        original = claims[key]["value"]
        quantity = h.decimal(total["quantity"])
        h.require(total["price"] == original["unit_price"]
                  and quantity >= h.decimal(original["minimum"]), "total-source")
        totals[key] = total
    ordered_ids(list(totals))

    for entry in h.array(item["required_claims"], 37):
        h.shape(entry, "citation id statement expected_typed_value tolerance units")
        key = resolve(entry["citation"])
        claim = claims[key]
        h.require(key in must_read and entry["id"] == key and entry["tolerance"] == "exact"
                  and entry["statement"] == statement(claim), "claim-binding")
        value = fact(claim)
        if key in totals:
            total = totals[key]
            with localcontext(Context(prec=64)):
                value["value"] = format(h.decimal(total["quantity"]) * h.decimal(total["price"]), "f")
        h.require(type(entry["expected_typed_value"]) is type(value["value"])
                  and entry["expected_typed_value"] == value["value"]
                  and entry["units"] == value["unit"], "claim-value")
        expected.append(value)
        required_ids.append(key)
    h.require(totals.keys() <= ordered_ids(required_ids), "orphan-total")

    refs = {key: [claims[key]["tenant"], *c.reference(claims[key])] for key in allowed}
    revocations = {}
    for event in h.array(item["revocations"], 1):
        h.shape(event, "id tick")
        key = event["id"]
        h.require(h.token(key) and key in must_read and key not in revocations
                  and h.integer(event["tick"], start+1, tick_of(claims[key]["expires_at"])-1),
                  "revocation-source")
        revocations[key] = event["tick"]
    h.require(bool(revocations) == (item["case"] == REVOCATION_CASE), "revocation-schedule")

    # Custody v1 denies writes and effects. This adapter has no broader scope.
    h.require(item["writes"] == [] and item["effects"] == [], "unsupported-effect-policy")
    bundle = {
        "case": {"id": item["case"], "category": item["category"], "tenant": item["tenant"],
                 "question": item["question"], "family": item["family"]},
        "oracle": {
            "approved": True, "behavior": item["behavior"], "facts": expected,
            "required": [[key, refs[key]] for key in required_ids],
            "forbidden": [], "reads": [refs[key] for key in sorted(allowed)],
            "writes": item["writes"], "effects": item["effects"], "totals": list(totals.values()),
            "revocations": [{"ref": refs[key], "tick": tick} for key, tick in revocations.items()],
        },
        "sources": [
            {"ref": refs[key], "from": tick_of(claims[key]["effective_from"]),
             "until": tick_of(claims[key]["expires_at"]), "approved": True, "epoch": 1,
             "facts": [fact(claims[key])] if key in required_ids else []}
            for key in sorted(allowed)
        ],
    }
    h.validate_bundle(bundle, "dummy")
    must_read_refs = frozenset(tuple(refs[key]) for key in must_read)
    return Case(item["case"], item["category"], h.canonical(bundle),
                tuple((key, tuple(refs[key]), tick_of(claims[key]["expires_at"]))
                      for key in sorted(allowed)),
                must_read_refs, forbidden, gold, start,
                tuple(revocations.items()), guards_digest(must_read_refs, forbidden))


def recall(case, ranked, end):
    """Validate every exposure before stable deduplication and top-five truncation."""
    allowed = {key: (ref, until) for key, ref, until in case.allowed}
    revoked = dict(case.revocations)
    unique_rank = {}
    last_tick = case.start
    for row in h.array(ranked):
        h.shape(row, "id ref tick")
        key, ref, tick = row["id"], h.reference(row["ref"]), row["tick"]
        h.require(h.token(key) and key in allowed and ref == allowed[key][0]
                  and h.integer(tick, last_tick, min(end, allowed[key][1]-1))
                  and (key not in revoked or tick < revoked[key]), "unauthorized-retrieval")
        unique_rank.setdefault(key, None)
        last_tick = tick
    if not case.gold:
        return None, 0
    return len(case.gold.intersection(list(unique_rank)[:5])), len(case.gold)
