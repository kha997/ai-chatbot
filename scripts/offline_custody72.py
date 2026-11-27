"""Validate externally pinned mock custody evidence. Real custody is NOT_VERIFIED.

The module enforces role separation, least-privilege rights, two independent
reviews in explicit event order, revocation, retention relationships, a derived
(not caller-chosen) ledger root and final-checkpoint binding for synthetic data
only. A mock receipt is validated statelessly and then consumed once in a
persistent store. It cannot verify real identities, real signatures, system
ACLs, actual deletion or a trusted anchor.
"""
from dataclasses import dataclass

from scripts import offline_heldout67 as h
from scripts import offline_receipt72 as receipt
from scripts.offline_source72 import checked

ROLES = ("author", "custodian", "semantic_one", "semantic_two", "security", "developer", "owner")

# Least privilege for the sealed synthetic run. The runtime developer and the
# author have no qualification rights at all, so neither can read or review the
# oracle after sealing. Only the two semantic reviewers may review.
ROLE_RIGHTS = {
    "author": (),
    "custodian": ("custody", "read"),
    "semantic_one": ("read", "review"),
    "semantic_two": ("read", "review"),
    "security": ("read", "security"),
    "developer": (),
    "owner": ("approve", "read"),
}
ALLOWED_RIGHTS = ("approve", "custody", "read", "review", "security")


@dataclass(frozen=True)
class Verified:
    start: int
    until: int
    proof: dict
    acl: dict


@dataclass(frozen=True)
class Finalized:
    custody: Verified
    checkpoint: dict
    external: object
    trust: str
    replay: str = "NOT_APPLICABLE"


# Sentinel distinguishes "caller omitted the root" from an explicit value, so a
# missing root is rejected instead of silently falling back to the genesis.
_MISSING = object()


def ledger_root(genesis, custody_pin, acl_pin):
    """Derive the prepared ledger root from the authenticated custody pins.

    The journal root is not an independent authority: it is a function of the
    envelope genesis and the pinned custody and ACL documents. A caller cannot
    substitute an arbitrary root and have it accepted.
    """
    h.require(h.is_hash(genesis) and h.is_hash(custody_pin) and h.is_hash(acl_pin),
              "journal-root")
    return h.digest(h.canonical({"envelope_genesis": genesis, "custody": custody_pin,
                                 "acl": acl_pin}))


def verify(raw, pin, acl_raw, acl_pin, receipts_raw, receipts_pin, *,
           envelope, sources, genesis, tick):
    proof = checked(raw, pin)
    h.require(type(proof) is dict and proof.get("schema") == "offline72-custody-v2"
              and proof.get("scope") == "PUBLIC_SYNTHETIC", "private-not-authorized")
    h.shape(proof, "schema scope envelope sources genesis roles approval acl from until "
            "retention isolation receipts real_evidence reviews revocations")
    h.require(proof["envelope"] == envelope and proof["sources"] == sources
              and proof["genesis"] == genesis, "custody-binding")
    roles = proof["roles"]
    h.shape(roles, " ".join(ROLES))
    h.require(all(h.token(value) and value.startswith("mock-") for value in roles.values())
              and len({value.casefold() for value in roles.values()}) == len(ROLES), "role-collision")

    start, until = proof["from"], proof["until"]
    h.require(h.integer(start) and h.integer(until, start+1), "custody-window")

    retention = proof["retention"]
    h.shape(retention, "delete_by deletion_receipt status")
    h.require(h.integer(retention["delete_by"], until) and retention["status"] == "MOCK_PLAN"
              and h.token(retention["deletion_receipt"])
              and retention["deletion_receipt"].startswith("mock-"), "custody-retention")
    # Mock deletion is due at delete_by. No evidence may be used from then on.
    h.require(tick < retention["delete_by"], "custody-deleted")
    h.require(h.integer(tick, start, until-1), "custody-window")

    approval = proof["approval"]
    h.shape(approval, "status by reference from until")
    h.require(approval["status"] == "MOCK_ONLY" and approval["by"] == roles["owner"]
              and h.token(approval["reference"]) and approval["reference"].startswith("mock-")
              and h.integer(approval["from"], start)
              and h.integer(approval["until"], start+1, until)
              and approval["from"] < approval["until"]
              and h.integer(tick, approval["from"], approval["until"]-1), "custody-approval")

    acl = checked(acl_raw, acl_pin)
    h.require(proof["acl"] == acl_pin, "acl-drift")
    h.shape(acl, "schema revision rights access_log reviewed expires")
    h.require(acl["schema"] == "offline72-acl-v2" and h.integer(acl["revision"], 1)
              and h.is_hash(acl["access_log"])
              and h.integer(acl["reviewed"], approval["from"], tick)
              and h.integer(acl["expires"], approval["from"], approval["until"])
              and acl["expires"] > tick, "custody-acl")
    # Deletion may not precede the end of access, and access may not outlive approval.
    h.require(retention["delete_by"] >= acl["expires"], "custody-retention")

    rights = acl["rights"]
    h.require(type(rights) is dict and rights.keys() == set(ROLES), "custody-rights")
    for role in ROLES:
        values = rights[role]
        h.require(type(values) is list and values == sorted(set(values))
                  and all(value in ALLOWED_RIGHTS for value in values)
                  and tuple(values) == ROLE_RIGHTS[role], "custody-rights")

    reviews = h.array(proof["reviews"], 2)
    h.require(len(reviews) == 2, "custody-review")
    references = set()
    for review, reviewer in zip(reviews, (roles["semantic_one"], roles["semantic_two"])):
        h.shape(review, "by verdict tick reference")
        h.require(review["by"] == reviewer and review["verdict"] == "MOCK_REVIEWED"
                  and h.integer(review["tick"], approval["from"], min(tick, acl["reviewed"]))
                  and h.token(review["reference"]) and review["reference"].startswith("mock-")
                  and review["reference"] != approval["reference"]
                  and review["reference"] not in references, "custody-review")
        references.add(review["reference"])
    # Explicit event order. Two independent reviews may share one logical tick,
    # but the earlier review may not be listed after the later one.
    h.require(reviews[0]["tick"] <= reviews[1]["tick"], "custody-review-order")
    acting = {roles[name] for name in ("author", "custodian", "developer", "owner", "security")}
    h.require(all(review["by"] not in acting for review in reviews), "custody-review-conflict")

    revocations = h.array(proof["revocations"], 2)
    revoked = set()
    for event in revocations:
        h.shape(event, "target tick reference")
        target = event["target"]
        h.require(target in roles.values() and target not in revoked
                  and h.integer(event["tick"], start)
                  and h.token(event["reference"]) and event["reference"].startswith("mock-"),
                  "custody-revocation")
        revoked.add(target)
    h.require(not any(event["tick"] <= tick for event in revocations), "custody-revoked")

    isolation = proof["isolation"]
    h.shape(isolation, "status reference requests spend")
    h.require(isolation["status"] == "MOCK_ZERO_EGRESS" and h.is_hash(isolation["reference"])
              and h.integer(isolation["requests"], 0, 0) and h.integer(isolation["spend"], 0, 0)
              and proof["real_evidence"] == "NOT_VERIFIED", "custody-isolation")

    receipts = checked(receipts_raw, receipts_pin)
    h.require(proof["receipts"] == receipts_pin, "custody-receipt-pin")
    _check_receipts(receipts, proof, acl, roles, tick)
    return Verified(start, until, proof, acl)


def finalize(raw, pin, acl_raw, acl_pin, receipts_raw, receipts_pin,
             checkpoint_raw, checkpoint_pin, *, envelope, sources, genesis, tick,
             journal_root=_MISSING, receipt_raw=None, receipt_pin=None, trusted=None,
             store=None):
    """Bind the final journal checkpoint and optional external receipt to custody.

    `genesis` is the envelope genesis bound by the custody proof. `journal_root`
    is mandatory and must equal `ledger_root(genesis, pin, acl_pin)`; there is no
    fallback and no caller-supplied alternative. A receipt is validated purely by
    `receipt.verify`, then consumed exactly once in the persistent `store`; the
    resulting replay state is mock bookkeeping, never external trust.
    """
    verified = verify(raw, pin, acl_raw, acl_pin, receipts_raw, receipts_pin,
                      envelope=envelope, sources=sources, genesis=genesis, tick=tick)
    h.require(journal_root is not _MISSING and type(journal_root) is str
              and h.is_hash(journal_root)
              and journal_root == ledger_root(genesis, pin, acl_pin), "journal-root")
    checkpoint = checked(checkpoint_raw, checkpoint_pin)
    h.shape(checkpoint, "schema root sequence tip")
    h.require(checkpoint["schema"] == "offline72-checkpoint-v1"
              and checkpoint["root"] == journal_root
              and h.integer(checkpoint["sequence"], 0, 120) and h.is_hash(checkpoint["tip"]),
              "checkpoint-binding")
    if receipt_raw is None:
        # Pins and hashes alone are not a trusted channel.
        return Finalized(verified, checkpoint, None, "EXTERNAL_ANCHOR_UNVERIFIED")
    h.require(isinstance(store, receipt.ReplayStore), "replay-store-required")
    external = receipt.verify(receipt_raw, receipt_pin, trusted=trusted, now=tick,
                              envelope=verified.proof["envelope"],
                              checkpoint_pin=checkpoint_pin, root=checkpoint["root"],
                              sequence=checkpoint["sequence"], tip=checkpoint["tip"])
    consumed = receipt.consume(store, external, tick)
    # The receipt is a public test-key mock, never proof of real custody. The
    # replay label records mock bookkeeping only.
    return Finalized(verified, checkpoint, external, "MOCK_EXTERNAL_RECEIPT", consumed)


def _check_receipts(receipts, proof, acl, roles, tick):
    h.shape(receipts, "schema architecture retention isolation access_log")
    h.require(receipts["schema"] == "offline72-mock-receipts-v2", "custody-receipt-version")
    approval = proof["approval"]
    architecture = receipts["architecture"]
    h.shape(architecture, "reference envelope by approved scope")
    h.require(architecture["reference"] == approval["reference"]
              and architecture["envelope"] == proof["envelope"]
              and architecture["by"] == roles["owner"]
              and architecture["scope"] == "PUBLIC_SYNTHETIC"
              and h.integer(architecture["approved"], approval["from"], tick), "custody-approval")
    retention = receipts["retention"]
    h.shape(retention, "reference envelope by delete_by state")
    h.require(retention["reference"] == proof["retention"]["deletion_receipt"]
              and retention["envelope"] == proof["envelope"]
              and retention["by"] == roles["custodian"]
              and retention["state"] == "MOCK_SCHEDULED_NOT_DELETED"
              and h.integer(retention["delete_by"], proof["retention"]["delete_by"],
                            proof["retention"]["delete_by"]), "custody-retention")
    isolation = receipts["isolation"]
    h.shape(isolation, "scope ipv4_routes ipv6_routes observed by")
    h.require(isolation["scope"] == "MOCK_ONLY" and isolation["ipv4_routes"] == []
              and isolation["ipv6_routes"] == [] and isolation["by"] == roles["security"]
              and h.integer(isolation["observed"], approval["from"], tick)
              and h.digest(h.canonical(isolation)) == proof["isolation"]["reference"],
              "custody-isolation")
    log = receipts["access_log"]
    h.require(h.digest(h.canonical(log)) == acl["access_log"], "custody-access-log")
    h.shape(log, "acl_revision reviewed entries")
    h.require(h.integer(log["acl_revision"], acl["revision"], acl["revision"])
              and h.integer(log["reviewed"], acl["reviewed"], acl["reviewed"]), "custody-access-log")

    principal_roles = {principal: role for role, principal in roles.items()}
    revoked = {event["target"]: event["tick"] for event in proof["revocations"]}
    last = approval["from"]
    entries = h.array(log["entries"])
    h.require(entries, "custody-access-log")
    for entry in entries:
        h.shape(entry, "principal action tick")
        role = principal_roles.get(entry["principal"])
        h.require(role is not None and "read" in acl["rights"][role]
                  and entry["action"] == "MOCK_READ"
                  and h.integer(entry["tick"], last, log["reviewed"])
                  and (roles[role] not in revoked or entry["tick"] < revoked[roles[role]]),
                  "custody-access-log")
        last = entry["tick"]
