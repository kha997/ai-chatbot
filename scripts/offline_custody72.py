"""Validate externally pinned synthetic custody evidence. Real custody is NOT_VERIFIED."""
from scripts import offline_heldout67 as h
from scripts.offline_source72 import checked

ROLES = ("author", "custodian", "semantic_one", "semantic_two", "security", "developer", "owner")


def verify(raw, pin, acl_raw, acl_pin, receipts_raw, receipts_pin, *,
           envelope, sources, genesis, tick):
    proof = checked(raw, pin)
    h.require(type(proof) is dict and proof.get("schema") == "offline72-custody-v1"
              and proof.get("scope") == "PUBLIC_SYNTHETIC", "private-not-authorized")
    h.shape(proof, "schema scope envelope sources genesis roles approval acl from until "
            "retention isolation receipts real_evidence")
    h.require(proof["envelope"] == envelope and proof["sources"] == sources
              and proof["genesis"] == genesis, "custody-binding")
    roles = proof["roles"]
    h.shape(roles, " ".join(ROLES))
    h.require(all(h.token(value) and value.startswith("mock-") for value in roles.values())
              and len({value.casefold() for value in roles.values()}) == len(ROLES), "role-collision")

    start, until = proof["from"], proof["until"]
    h.require(h.integer(start) and h.integer(until, start+1)
              and h.integer(tick, start, until-1), "custody-window")
    approval = proof["approval"]
    h.shape(approval, "status by reference")
    h.require(approval["status"] == "MOCK_ONLY" and approval["by"] == roles["owner"]
              and h.token(approval["reference"]) and approval["reference"].startswith("mock-"),
              "custody-approval")

    acl = checked(acl_raw, acl_pin)
    h.require(proof["acl"] == acl_pin, "acl-drift")
    h.shape(acl, "schema revision principals access_log reviewed expires")
    h.require(acl["schema"] == "offline72-acl-v1" and h.integer(acl["revision"], 1)
              and acl["principals"] == sorted([roles["custodian"], roles["security"], roles["owner"]])
              and h.is_hash(acl["access_log"]) and h.integer(acl["reviewed"], start, tick)
              and h.integer(acl["expires"], tick+1, until), "custody-acl")

    retention = proof["retention"]
    h.shape(retention, "delete_by deletion_receipt status")
    h.require(h.integer(retention["delete_by"], until)
              and retention["status"] == "MOCK_PLAN"
              and h.token(retention["deletion_receipt"])
              and retention["deletion_receipt"].startswith("mock-"), "custody-retention")
    isolation = proof["isolation"]
    h.shape(isolation, "status reference requests spend")
    h.require(isolation["status"] == "MOCK_ZERO_EGRESS" and h.is_hash(isolation["reference"])
              and h.integer(isolation["requests"], 0, 0) and h.integer(isolation["spend"], 0, 0)
              and proof["real_evidence"] == "NOT_VERIFIED", "custody-isolation")

    receipts = checked(receipts_raw, receipts_pin)
    h.require(proof["receipts"] == receipts_pin, "custody-receipt-pin")
    _check_receipts(receipts, proof, acl, tick)
    return start, acl["expires"]


def _check_receipts(receipts, proof, acl, tick):
    h.shape(receipts, "schema architecture retention isolation access_log")
    h.require(receipts["schema"] == "offline72-mock-receipts-v1", "custody-receipt-version")
    architecture = receipts["architecture"]
    h.shape(architecture, "reference envelope by approved scope")
    h.require(architecture["reference"] == proof["approval"]["reference"]
              and architecture["envelope"] == proof["envelope"]
              and architecture["by"] == proof["roles"]["owner"]
              and architecture["scope"] == "PUBLIC_SYNTHETIC"
              and h.integer(architecture["approved"], proof["from"], tick), "custody-approval")
    retention = receipts["retention"]
    h.shape(retention, "reference envelope by delete_by state")
    h.require(retention["reference"] == proof["retention"]["deletion_receipt"]
              and retention["envelope"] == proof["envelope"]
              and retention["by"] == proof["roles"]["custodian"]
              and retention["state"] == "MOCK_SCHEDULED_NOT_DELETED"
              and h.integer(retention["delete_by"], proof["retention"]["delete_by"],
                            proof["retention"]["delete_by"]), "custody-retention")
    isolation = receipts["isolation"]
    h.shape(isolation, "scope ipv4_routes ipv6_routes observed by")
    h.require(isolation["scope"] == "MOCK_ONLY" and isolation["ipv4_routes"] == []
              and isolation["ipv6_routes"] == [] and isolation["by"] == proof["roles"]["security"]
              and h.integer(isolation["observed"], proof["from"], tick)
              and h.digest(h.canonical(isolation)) == proof["isolation"]["reference"],
              "custody-isolation")
    log = receipts["access_log"]
    h.require(h.digest(h.canonical(log)) == acl["access_log"], "custody-access-log")
    h.shape(log, "acl_revision reviewed entries")
    h.require(h.integer(log["acl_revision"], acl["revision"], acl["revision"])
              and h.integer(log["reviewed"], acl["reviewed"], acl["reviewed"]), "custody-access-log")
    last = proof["from"]
    entries = h.array(log["entries"])
    h.require(entries, "custody-access-log")
    for entry in entries:
        h.shape(entry, "principal action tick")
        h.require(entry["principal"] in acl["principals"] and entry["action"] == "MOCK_READ"
                  and h.integer(entry["tick"], last, log["reviewed"]), "custody-access-log")
        last = entry["tick"]
