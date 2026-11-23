"""Validate the public Issue #63 corpus offline. No held-out reader exists."""

import argparse
from datetime import datetime
from decimal import Context, Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
import sys

from scripts.quote_validator import validate_quote


MARKER = "SYNTHETIC—NOT BUSINESS POLICY"
VERSION = "offline63-v1"
BASELINE = "b213fb560902083ebeb87f3fd3f3aff25c25894d"
CUSTODY = "BLOCKED_HELDOUT_CUSTODY"
CATEGORIES = (
    "offering", "scope", "price", "quote", "availability",
    "policy", "unknown", "ambiguity", "sources", "injection",
)
FAMILIES = {
    "catalog": {"material": "text", "environment": "text", "alias": "text", "variant": "text"},
    "prices": {"price-rule": "price"},
    "quote-inputs": {"required-slots": "slots"},
    "availability": {"available-count": "count", "stock-condition": "text"},
    "scope-exclusions": {"scope": "text", "excluded": "text"},
    "policy": {"draft-cancel": "text", "discount": "text"},
    "handoff": {"handoff-mode": "text", "receipt-rule": "text"},
    "authority": {"activation-rule": "text", "override": "text"},
}
DEV_SEEDS = (
    "qa-NHD-price-01", "unknown-sku", "zero-quantity", "fractional-quantity",
    "wrong-currency", "wrong-unit", "expired-source", "revoked-source",
    "unapproved-source", "old-version", "missing-unit-price", "forged-same-tenant-citation",
)
DEV_FAMILIES = (
    "historic-box-total", "unknown-sku", "zero-quantity", "fractional-quantity",
    "wrong-currency", "wrong-unit", "expired-source", "revoked-source",
    "unapproved-source", "old-version", "missing-unit-price", "forged-same-tenant-citation",
)
FROZEN_FILES = (
    "coverage.json", "custody.schema.json", "development.json", "public.schema.json", "sources.json",
)
SYNTHETIC_SKU = r"SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*"
DECIMAL = r"(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,4})?"
CLOCK = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
TOKEN = r"[a-z][a-z0-9-]{0,79}"


def require(condition, label):
    if not condition:
        raise ValueError(label)


def closed(value, fields, label):
    require(type(value) is dict and set(value) == set(fields.split()), f"{label}: keys")


def match(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def safe_text(value):
    return (
        type(value) is str and 0 < len(value) <= 400 and value == value.strip()
        and value.isprintable()
        and re.search(r"(?:https?://|www\.|@|\b\d{7,}\b)", value, re.I) is None
    )


def timestamp(value):
    require(match(CLOCK, value), "UTC timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def canonical(value):
    """Canonical bytes: UTF-8, sorted object keys, 2 spaces, LF and final LF."""
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def parse(raw):
    def deny_constant(value):
        raise ValueError(f"non-JSON constant: {value}")
    return json.loads(
        raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=deny_constant
    )


def read_json(path):
    return parse(Path(path).read_bytes())


def public_header(data, fields):
    closed(data, f"schema_version synthetic designation {fields}", "public artifact")
    require(data["schema_version"] == VERSION and data["synthetic"] is True
            and data["designation"] == MARKER, "public marking/version")


def validate_sources(data):
    public_header(data, "tenant provenance products claims")
    require(data["tenant"] == "NHD", "corpus tenant")
    provenance = data["provenance"]
    closed(provenance, "author authored_on derivation rights", "source provenance")
    require(provenance == {
        "author": "issue63-codex-corpus-author", "authored_on": "2026-11-23",
        "derivation": "original-invented-fixtures", "rights": "no-third-party-text",
    }, "source provenance")
    require(type(data["products"]) is list and type(data["claims"]) is list, "source arrays")
    products = {}
    for product in data["products"]:
        closed(product, "sku category variant unit", "product")
        sku = product["sku"]
        require(match(SYNTHETIC_SKU, sku) and sku not in products, "product identifier")
        require(all(match(TOKEN, product[key]) for key in ("category", "variant", "unit")),
                "product category/variant/unit")
        products[sku] = product
    require(len(products) >= 6, "product breadth")
    require(len({x["category"] for x in products.values()}) >= 4, "category breadth")
    require(len({x["unit"] for x in products.values()}) >= 4, "unit breadth")

    seen = set()
    for claim in data["claims"]:
        closed(claim, "tenant document version paragraph family subject predicate kind value "
               "status effective_from expires_at permitted", "source claim")
        require(claim["tenant"] == "NHD" and match(r"NHD-[a-z0-9-]{1,75}", claim["document"]),
                "source scope")
        require(type(claim["version"]) is int and claim["version"] >= 1
                and match(r"p[1-9][0-9]*", claim["paragraph"]), "source version/paragraph")
        ref = reference(claim)
        require(ref not in seen, "duplicate source revision paragraph")
        seen.add(ref)
        family, predicate, subject = claim["family"], claim["predicate"], claim["subject"]
        require(match(TOKEN, family) and match(TOKEN, predicate) and family in FAMILIES
                and FAMILIES[family].get(predicate) == claim["kind"], "typed claim family/predicate")
        require(type(subject) is str and (subject in products or match(TOKEN, subject)), "source subject")
        require(claim["status"] in ("active", "retired", "untrusted", "revoked")
                and type(claim["permitted"]) is bool, "source status/authority")
        require(claim["status"] == "active" or claim["permitted"] is False, "inactive authority")
        require(timestamp(claim["effective_from"]) < timestamp(claim["expires_at"]), "source window")
        value, kind = claim["value"], claim["kind"]
        if kind == "text":
            require(safe_text(value), "source text")
        elif kind == "count":
            require(type(value) is int and 0 <= value <= 10000, "stock count")
        elif kind == "slots":
            require(type(value) is list and value and all(
                type(x) is str and x in ("sku", "variant", "unit", "quantity") for x in value
            ) and len(value) == len(set(value)), "quote slots")
        elif kind == "price":
            closed(value, "unit_price minimum unit currency", "price rule")
            require(match(DECIMAL, value["unit_price"]) and match(DECIMAL, value["minimum"])
                    and value["currency"] == "VND" and subject in products
                    and value["unit"] == products[subject]["unit"], "typed price rule")
    require({x["family"] for x in data["claims"]} == set(FAMILIES), "source family inventory")


def reference(claim):
    return claim["document"], claim["version"], claim["paragraph"]


def source_index(claims):
    return {reference(claim): claim for claim in claims}


def eligible(claim, now):
    return (claim["tenant"] == "NHD" and claim["status"] == "active"
            and claim["permitted"] is True
            and timestamp(claim["effective_from"]) <= now < timestamp(claim["expires_at"]))


def lookup(claims, subject, predicate, as_of):
    now = timestamp(as_of)
    matches = [x for x in claims if x["tenant"] == "NHD"
               and x["subject"] == subject and x["predicate"] == predicate
               and eligible(x, now)]
    return matches[0] if len(matches) == 1 else None


def alias_candidates(claims, alias, as_of):
    """Return all unambiguous, active alias records for clarification."""
    return tuple(sorted({
        claim["subject"] for claim in claims
        if claim["tenant"] == "NHD" and claim["predicate"] == "alias" and claim["value"] == alias
        and lookup(claims, claim["subject"], "alias", as_of) is claim
    }))


def read_source(index, trusted_tenant, ref, as_of):
    if trusted_tenant != "NHD" or type(ref) is not tuple or len(ref) != 3:
        return None
    document, version, paragraph = ref
    if (not match(r"NHD-[a-z0-9-]{1,75}", document) or type(version) is not int or version < 1
            or not match(r"p[1-9][0-9]*", paragraph)):
        return None
    claim = index.get(ref)
    if claim is None or not eligible(claim, timestamp(as_of)) or reference(claim) != ref:
        return None
    selected = lookup(index.values(), claim["subject"], claim["predicate"], as_of)
    return claim if selected is claim else None


def quote_draft(claims, sku, quantity, unit, as_of):
    """Amount-only oracle for prevalidated selections, without quote-slot resolution."""
    if not match(SYNTHETIC_SKU, sku) or not match(r"[1-9][0-9]{0,5}", quantity):
        return None
    claim = lookup(claims, sku, "price-rule", as_of)
    if claim is None or claim["value"]["unit"] != unit:
        return None
    price = claim["value"]
    with localcontext(Context(prec=32)):  # bounded fixture digits and independent context
        amount = max(Decimal(quantity) * Decimal(price["unit_price"]), Decimal(price["minimum"]))
    return {"amount": format(amount, "f"), "currency": "VND", "citation": reference(claim),
            "effects": []}


def validate_coverage(data):
    public_header(data, "state scoring_repetitions slots")
    require(data["state"] == CUSTODY and type(data["scoring_repetitions"]) is int
            and data["scoring_repetitions"] == 2, "coverage custody/repetitions")
    require(type(data["slots"]) is list, "coverage slots")
    actual = []
    families = set()
    normalized_focuses = set()
    for slot in data["slots"]:
        closed(slot, "id category family focus state", "coverage row")
        require(slot["state"] == "reserved" and match(TOKEN, slot["family"])
                and safe_text(slot["focus"]), "coverage metadata")
        require(slot["family"] not in families and slot["family"] not in DEV_FAMILIES,
                "reused public semantic-family identifier")
        normalized_focus = "".join(char for char in slot["focus"].casefold() if char.isalnum())
        require(normalized_focus and normalized_focus not in normalized_focuses,
                "reused public coverage focus")
        normalized_focuses.add(normalized_focus)
        families.add(slot["family"])
        actual.append((slot["category"], slot["id"]))
    expected = [
        (category, f"ga61-qa-{category}-{number:02}")
        for category in CATEGORIES for number in range(1, 7)
    ]
    require(actual == expected, "complete ordered 60-slot inventory")


def validate_development(data, historical):
    public_header(data, "split scoring tenant cases")
    require(data["split"] == "public-development" and data["scoring"] is False
            and data["tenant"] == "NHD", "development-only scope")
    require(type(data["cases"]) is list and len(data["cases"]) == 12, "12 development records")
    seeds = {seed["id"]: seed for seed in historical["cases"]}
    for i, case in enumerate(data["cases"]):
        closed(case, "id seed family question oracle effects", "development case")
        require(case["id"] == f"ga61-dev-{i+1:02}" and case["seed"] == DEV_SEEDS[i]
                and case["family"] == DEV_FAMILIES[i] and safe_text(case["question"])
                and case["effects"] == [], "development case identity/side effects")
        seed = seeds[case["seed"]]
        calculated = validate_quote(**{key: seed[key] for key in ("context", "request", "candidate")},
                                    sources=historical["sources"], as_of=historical["as_of"])
        require(calculated == case["oracle"] == seed["oracle"], "development answer-key mismatch")


def load_public(directory, historical_path):
    """Read fixed public names only. Refuse the directory before opening extra files."""
    root = Path(directory)
    expected_names = {*FROZEN_FILES, "manifest.json"}
    observed = {entry.name: entry for entry in root.iterdir()}
    require(set(observed) == expected_names and all(
        entry.is_file() and not entry.is_symlink() for entry in observed.values()
    ), "unexpected artifact or link in public corpus directory")
    file_bytes = {name: observed[name].read_bytes() for name in expected_names}
    files = {}
    for name, raw in file_bytes.items():
        value = parse(raw)
        require(raw == canonical(value), f"noncanonical bytes: {name}")
        files[name] = value

    manifest = files["manifest.json"]
    public_header(manifest, "baseline approval author source_approval custody egress artifacts")
    require(manifest["baseline"] == BASELINE and manifest["custody"] == CUSTODY
            and manifest["author"] == "issue63-codex-corpus-author"
            and manifest["approval"] == "unapproved-for-execution"
            and manifest["source_approval"] == "see-independent-review-receipt"
            and manifest["egress"] == "denied-by-default", "manifest authority")
    require(manifest["artifacts"] == {
        name: {"byte_length": len(file_bytes[name]),
               "sha256": hashlib.sha256(file_bytes[name]).hexdigest()} for name in FROZEN_FILES
    }, "manifest bytes/hashes")
    validate_sources(files["sources.json"])
    validate_coverage(files["coverage.json"])
    validate_development(files["development.json"], read_json(historical_path))
    return {"sources": files["sources.json"], "coverage": files["coverage.json"],
            "dev": files["development.json"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # no alternate path, upload, or private read options
    root = Path(__file__).resolve().parents[1] / "eval"
    try:
        package = load_public(root / "offline63", root / "quote_acceptance.json")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Public corpus rejected: {exc}", file=sys.stderr)
        return 1
    sources = package["sources"]
    print(f"Validated {len(sources['products'])} products, {len(sources['claims'])} source claims, "
          f"{len(package['dev']['cases'])} public development oracles and "
          f"{len(package['coverage']['slots'])} reserved slots. Held-out frozen: 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
