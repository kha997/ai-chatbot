"""Mock external-receipt validation for synthetic custody evidence.

THIS IS NOT A SIGNATURE SYSTEM. The bundled key is public, so any caller can
produce a valid MAC. It exists only to exercise issuer, freshness, binding and
replay logic against public fixtures. A real deployment needs a private key and
issuer identity held outside this repository; until then treat real custody as
NOT_VERIFIED.
"""
import hmac
from dataclasses import dataclass

from scripts import offline_heldout67 as h
from scripts.offline_source72 import checked

SCHEMA = "offline72-external-receipt-v1"
FIELDS = "schema issuer key_id sequence issued expires envelope root checkpoint tip nonce attestation mac"
MAX_AGE = 3600
# MOCK ONLY. Public by construction; possession proves nothing.
MOCK_ISSUER = "mock-external-issuer"
MOCK_KEY_ID = "mock-public-key-1"
MOCK_KEY = b"offline72-public-test-key-not-a-secret"


@dataclass(frozen=True)
class Receipt:
    issuer: str
    sequence: int
    envelope: str
    checkpoint: str
    tip: str
    attestation: str


def mac(body, key):
    return hmac.new(key, h.canonical(body), "sha256").hexdigest()


def verify(raw, pin, *, trusted, now, seen=None, envelope=None, checkpoint_pin=None,
           root=None, sequence=None, tip=None):
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
    if seen is not None:
        identity = (proof["issuer"], proof["nonce"])
        h.require(identity not in seen, "receipt-replay")
        seen.add(identity)
    return Receipt(proof["issuer"], proof["sequence"], proof["envelope"],
                   proof["checkpoint"], proof["tip"], proof["attestation"])
