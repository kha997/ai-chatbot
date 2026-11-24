"""Mock-only Gate A byte bridge and approval validation. No file or network I/O."""
from dataclasses import dataclass
import json
from unicodedata import normalize

from scripts import offline_corpus63 as corpus
from scripts import offline_heldout67 as h

BRIDGE = "offline69-synthetic-bridge-v1"
ENVELOPE = "offline69-mock-gate-a-v2"
DESIGNATION = "SYNTHETIC—NOT BUSINESS POLICY"
INDENTED = "utf8-lf-sorted-keys-2spaces-v1"
COMPACT = "utf8-lf-sorted-keys-compact-v1"
BASELINE = "7e2a775acfd542d5d4db0ac4c5b061e2214e37ae"
DEV_SHA = "0b50d2ab2d0510dd75e65b5e8b47ade3abf6337f6a098f551670017e3171d53a"
SCHEMA_SHA = "043a1292b3aa6cb59c19553a8d9a0c25ad48cc549f3804ddfcd1e963b70df627"
RIGHTS = "invented-no-third-party-text"
EXTERNAL = (
    "owner_signature", "architecture_acceptance", "private_archive", "private_semantic_review",
    "private_role_identity", "acl", "retention", "access_log", "candidate_build",
    "prompt", "runtime_config", "state_provenance", "provider_account", "provider_terms",
    "region", "credential_custody", "provider_enforcement", "wire_framing", "pricing",
    "tax_fees", "isolation", "source_clock", "stop_controls", "rollback", "threat_coverage",
)
NOT_RUN = ("model", "six_business_e2es", "performance", "billing", "private_audit")
SOURCE_STATES = ("active", "retired", "revoked", "untrusted")


def pin(raw):
    h.require(type(raw) is bytes and 0 < len(raw) <= h.MAX_BYTES, "artifact-size")
    return {"sha256": h.digest(raw), "bytes": len(raw)}


def validate_pin(expected):
    h.shape(expected, "sha256 bytes")
    h.require(h.is_hash(expected["sha256"]) and h.integer(expected["bytes"], 1, h.MAX_BYTES),
              "artifact-pin")


def check_pin(raw, expected):
    validate_pin(expected)
    h.require(pin(raw) == expected, "artifact-pin")


def _parse_indented(raw):
    # Parse the 2-space format only after checking external pins. Reuse the
    # compact encoder's strict native-type/depth checks before interpreting data.
    def unique(pairs):
        data = dict(pairs)
        h.require(len(data) == len(pairs), "duplicate-key")
        return data

    def deny(_):
        raise h.Invalid("number")

    def number(value):
        h.require(len(value) <= 17, "number")
        return int(value)

    def unicode_check(value):
        if type(value) is str:
            h.require(normalize("NFC", value) == value, "non-nfc")
        elif type(value) is dict:
            for key, item in value.items():
                unicode_check(key)
                unicode_check(item)
        elif type(value) is list:
            for item in value:
                unicode_check(item)

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=deny,
                          parse_constant=deny, parse_int=number)
        h.canonical(data)
        unicode_check(data)
        h.require(corpus.canonical(data) == raw, "indented-format")
        return data
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise h.Invalid("format") from None


def normalized(value):
    h.require(h.text(value), "text")
    return h.normalize_overlap(value)


@dataclass(frozen=True)
class Development:
    families: frozenset
    question_hashes: frozenset

    def assert_distinct(self, case):
        family = normalized(case["family"])
        question = normalized(case["question"])
        h.require(bool(question) and family not in self.families
                  and h.digest(question.encode()) not in self.question_hashes, "development-overlap")


def development(raw, approved_pin):
    check_pin(raw, approved_pin)
    h.require(approved_pin["sha256"] == DEV_SHA, "public-development-revision")
    data = _parse_indented(raw)
    # The pinned bytes are the published canonical development artifact.
    corpus.public_header(data, "split scoring tenant cases")
    h.require(data["split"] == "public-development" and data["scoring"] is False
              and data["tenant"] == "NHD" and len(data["cases"]) == 12, "development")
    return Development(
        frozenset(normalized(row["family"]) for row in data["cases"]),
        frozenset(h.digest(normalized(row["question"]).encode()) for row in data["cases"]),
    )


def freeze_screened(mode, bundles, dev_raw, dev_pin):
    """Mechanical screening only. The caller supplies records already in memory."""
    dev = development(dev_raw, dev_pin)
    for bundle in h.array(bundles, 60):
        h.canonical(bundle)
        case = h.validate_bundle(bundle, mode)[0]
        dev.assert_distinct(case)
    return h.freeze(mode, bundles, development_families=tuple(sorted(dev.families)))


@dataclass(frozen=True)
class Bridge:
    compact: bytes
    required_reads: frozenset
    forbidden_fact_ids: frozenset
    author: str
    reviewer: str
    until_tick: int


def bridge(raw, descriptor, tick):
    """Map only the new, explicitly dummy bridge wrapper to an offline67 bundle.

    Source authority lives in the wrapper; the narrower scorer consumes the
    explicitly typed bundle. The envelope pins both, so no authority metadata
    is implicitly transformed into a scorer approval.
    """
    h.shape(descriptor, "input output source_revision")
    check_pin(raw, descriptor["input"])
    source = _parse_indented(raw)
    h.shape(source, "schema synthetic scope provenance sources safeguards bundle")
    h.require(source["schema"] == BRIDGE and source["synthetic"] is True
              and source["scope"] == "PUBLIC_DUMMY", "bridge-scope")
    p = source["provenance"]
    h.shape(p, "author reviewer rights revision from until")
    h.require(h.token(p["author"]) and h.token(p["reviewer"]) and p["author"] != p["reviewer"]
              and p["rights"] == RIGHTS and h.integer(p["revision"], 1)
              and h.integer(descriptor["source_revision"], p["revision"], p["revision"])
              and h.integer(p["from"]) and h.integer(p["until"], p["from"]+1)
              and h.integer(tick, p["from"], p["until"]-1), "bridge-provenance")
    bundle = source["bundle"]
    case, _, records, readable, _, _, expected, _, _, _ = h.validate_bundle(bundle, "dummy")
    h.require(case["tenant"] == "NHD", "bridge-tenant")
    states = h.array(source["sources"], 48)
    h.require(len(states) == len(records), "source-inventory")
    for stamped, (ref, record) in zip(states, records.items()):
        h.shape(stamped, "ref state authority")
        state = stamped["state"]
        h.require(h.reference(stamped["ref"]) == ref and state in SOURCE_STATES, "source-order-state")
        h.require(stamped["authority"] == ("approved" if record["approved"] else "denied")
                  and (state == "active" or not record["approved"]), "source-authority")
    s = source["safeguards"]
    h.shape(s, "required_reads forbidden_fact_ids")
    required = frozenset(h.unique([h.reference(ref) for ref in h.array(s["required_reads"])]))
    forbidden = frozenset(h.ids(s["forbidden_fact_ids"]))
    h.require(required <= readable and forbidden.isdisjoint(expected), "mock-safeguards")
    compact = h.canonical(bundle)
    check_pin(compact, descriptor["output"])
    return Bridge(compact, required, forbidden, p["author"], p["reviewer"], p["until"])


@dataclass(frozen=True)
class ApprovedRun:
    """Result of mock verification. The Python caller and imported code are trusted."""
    run_id: str
    envelope_sha: str
    manifest_raw: bytes
    manifest_sha: str
    from_tick: int
    until_tick: int
    cases: tuple

    @property
    def genesis(self):
        return h.digest(h.canonical(["offline69-genesis-v1", self.run_id, self.envelope_sha]))


def verify(raw, approved_pin, manifest_raw, dev_raw, custody_schema_raw, settings_raw, bridges):
    """Validate an independently pinned public-dummy envelope and exact input bytes."""
    check_pin(raw, approved_pin)
    packet = h.parse(raw)
    h.shape(packet, "schema scope designation canonicalization schedule run_id baseline tenant clock "
            "roles approval pins source_policy attestations outcomes retention repetition_seeds cases")
    h.require(packet["schema"] == ENVELOPE and packet["scope"] == "PUBLIC_DUMMY"
              and packet["designation"] == DESIGNATION
              and h.token(packet["run_id"]) and packet["run_id"].startswith("SYN-")
              and packet["baseline"] == BASELINE and packet["tenant"] == "NHD", "envelope-scope")
    h.require(packet["canonicalization"] == {"envelope": COMPACT, "bridge_input": INDENTED,
                                             "scorer": COMPACT}, "canonicalization")
    schedule = packet["schedule"]
    h.shape(schedule, "mode expected_cases")
    expected_count = schedule["expected_cases"]
    h.require((schedule["mode"] == "small-dummy" and h.integer(expected_count, 1, 59))
              or (schedule["mode"] == "full-dummy" and h.integer(expected_count, 60, 60)),
              "schedule")
    roles = packet["roles"]
    h.shape(roles, "author reviewer custodian implementer")
    h.require(all(h.token(x) and x.startswith("mock-") for x in roles.values())
              and len(set(roles.values())) == len(roles), "independent-mock-roles")
    approval = packet["approval"]
    h.shape(approval, "state from until receipt")
    h.require(approval["state"] == "MOCK_ONLY" and approval["receipt"] == "NOT_VERIFIED"
              and h.integer(approval["from"]) and h.integer(approval["until"], approval["from"]+1)
              and h.integer(packet["clock"], approval["from"], approval["until"]-1), "mock-approval")
    policy = packet["source_policy"]
    h.shape(policy, "rights egress requests spend")
    h.require(policy["rights"] == RIGHTS and policy["egress"] == "DENIED"
              and h.integer(policy["requests"], 0, 0) and h.integer(policy["spend"], 0, 0),
              "zero-egress")
    h.require(packet["attestations"] == dict.fromkeys(EXTERNAL, "NOT_VERIFIED")
              and packet["outcomes"] == dict.fromkeys(NOT_RUN, "NOT_RUN")
              and packet["retention"] == {"acl": "NOT_VERIFIED", "days": None,
                                          "access_log": "NOT_VERIFIED"}, "mock-only-evidence")
    pins = packet["pins"]
    h.shape(pins, "manifest development custody_schema settings candidate_fixture config_fixture")
    dev = development(dev_raw, pins["development"])
    check_pin(custody_schema_raw, pins["custody_schema"])
    h.require(pins["custody_schema"]["sha256"] == SCHEMA_SHA, "public-schema-revision")
    check_pin(manifest_raw, pins["manifest"])
    manifest = h.parse(manifest_raw)
    h.validate_manifest(manifest)
    h.require(manifest["mode"] == "dummy", "mock-manifest")
    check_pin(settings_raw, pins["settings"])
    settings = h.parse(settings_raw)
    h.shape(settings, "schema candidate config prompt initial_state")
    h.shape(settings["config"], "transport model max_calls")
    config = settings["config"]
    state = settings["initial_state"]
    h.shape(state, "epoch tenant")
    h.require(settings["schema"] == "offline69-settings-v1" and h.token(settings["candidate"])
              and settings["candidate"].startswith("dummy-") and settings["prompt"] is None
              and config["transport"] == "NONE" and config["model"] == "NOT_RUN"
              and h.integer(config["max_calls"], 0, 0)
              and state["tenant"] == "NHD" and h.integer(state["epoch"], 1), "dummy-settings")
    check_pin(h.canonical(settings["candidate"]), pins["candidate_fixture"])
    check_pin(h.canonical(config), pins["config_fixture"])
    seeds = h.array(packet["repetition_seeds"], 2)
    h.require(len(seeds) == 2 and all(h.integer(seed) for seed in seeds) and seeds[0] != seeds[1],
              "repetition-seeds")
    cases = h.array(packet["cases"], 60)
    bridge_bytes = h.array(bridges, 60)
    h.require(len(cases) == len(bridge_bytes) == len(manifest["entries"]) == expected_count,
              "case-inventory")
    if schedule["mode"] == "full-dummy":
        full_ids = [case_id.replace("ga61-qa-", "dummy-", 1) for case_id in h.expected_ids()]
        h.require([entry["case"] for entry in manifest["entries"]] == full_ids,
                  "full-dummy-inventory")
    state_raw = h.canonical(state)
    verified = []
    records = []
    authorized_until = approval["until"]
    for row, bridge_raw, entry in zip(cases, bridge_bytes, manifest["entries"]):
        h.shape(row, "id category bridge seeds pre_state post_state")
        h.require(row["id"] == entry["case"] and row["category"] == entry["category"]
                  and type(row["seeds"]) is list and len(row["seeds"]) == 2
                  and all(h.integer(value, expected, expected) for value, expected
                          in zip(row["seeds"], seeds)), "case-schedule")
        check_pin(state_raw, row["pre_state"])
        check_pin(state_raw, row["post_state"])
        mapped = bridge(bridge_raw, row["bridge"], packet["clock"])
        authorized_until = min(authorized_until, mapped.until_tick)
        check_pin(mapped.compact, {"sha256": entry["sha256"], "bytes": entry["bytes"]})
        case_bundle = h.parse(mapped.compact)
        dev.assert_distinct(case_bundle["case"])
        h.require(mapped.author == roles["author"] and mapped.reviewer == roles["reviewer"]
                  and not case_bundle["oracle"]["writes"] and not case_bundle["oracle"]["effects"],
                  "bridge-roles-state")
        records.append(case_bundle)
        verified.append((entry["case"], entry["category"], entry["sha256"],
                         mapped.required_reads, mapped.forbidden_fact_ids))
    h.require(freeze_screened("dummy", records, dev_raw, pins["development"]) == manifest_raw,
              "manifest-rebuild")
    return ApprovedRun(packet["run_id"], approved_pin["sha256"], manifest_raw,
                       pins["manifest"]["sha256"], packet["clock"], authorized_until, tuple(verified))
