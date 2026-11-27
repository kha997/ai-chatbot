"""Round 2 hardening regressions for PR #73.

The ledger root is derived from authenticated custody pins, a mock external
receipt is consumed exactly once in a persistent store, and reviewer events must
be listed in explicit chronological order. Everything here is public-synthetic:
the mock key is public, so replay state and the mock MAC are bookkeeping labels,
never proof of issuer identity, revocation authority or external custody.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import multiprocessing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest

from scripts import offline_custody72 as custody
from scripts import offline_heldout67 as h
from scripts import offline_qualification72 as q
from scripts import offline_receipt72 as receipt
from offline_fixture72 import checkpoint, fixture, sign_receipt, trusted


def pin_proof(inputs, proof):
    raw = h.canonical(proof)
    return dict(inputs, custody_raw=raw, custody_pin=h.digest(raw))


def with_acl(inputs, acl):
    acl_raw = h.canonical(acl)
    proof = h.parse(inputs["custody_raw"])
    proof["acl"] = h.digest(acl_raw)
    return pin_proof(dict(inputs, acl_raw=acl_raw, acl_pin=h.digest(acl_raw)), proof)


def finalize(inputs, pinned, *, journal_root, store=None, receipt_pair=None):
    return custody.finalize(
        inputs["custody_raw"], inputs["custody_pin"], inputs["acl_raw"], inputs["acl_pin"],
        inputs["receipts_raw"], inputs["receipts_pin"], pinned[0], pinned[1],
        envelope=inputs["envelope_pin"], sources=inputs["source_pin"],
        genesis=q.genesis(inputs["envelope_pin"]), tick=5, journal_root=journal_root,
        receipt_raw=None if receipt_pair is None else receipt_pair[0],
        receipt_pin=None if receipt_pair is None else receipt_pair[1],
        trusted=trusted(), store=store)


def consume_in_child(store_path, raw, pin, bindings, queue):
    """Verify and consume one mock receipt in a separate spawned process."""
    try:
        verified = receipt.verify(raw, pin, trusted=trusted(), now=bindings["now"],
                                  envelope=bindings["envelope"],
                                  checkpoint_pin=bindings["checkpoint"],
                                  root=bindings["root"], sequence=bindings["sequence"],
                                  tip=bindings["tip"])
        queue.put(("ACCEPT", receipt.consume(receipt.ReplayStore(store_path), verified,
                                             bindings["now"])))
    except h.Invalid as error:
        queue.put(("REJECT", str(error)))


class LedgerRootBindingTests(unittest.TestCase):
    """NEW-7: the journal root is derived, mandatory and never caller authority."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.run_spec = q.prepare(**cls.inputs)
        cls.pinned = checkpoint(cls.run_spec)

    def test_derived_ledger_root_is_the_only_accepted_root(self):
        self.assertEqual(
            custody.ledger_root(q.genesis(self.inputs["envelope_pin"]),
                                self.inputs["custody_pin"], self.inputs["acl_pin"]),
            self.run_spec.genesis)
        finalized = finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis)
        self.assertEqual(finalized.trust, "EXTERNAL_ANCHOR_UNVERIFIED")

    def test_omitted_journal_root_is_rejected(self):
        with self.assertRaisesRegex(h.Invalid, "journal-root"):
            custody.finalize(
                self.inputs["custody_raw"], self.inputs["custody_pin"],
                self.inputs["acl_raw"], self.inputs["acl_pin"],
                self.inputs["receipts_raw"], self.inputs["receipts_pin"],
                self.pinned[0], self.pinned[1], envelope=self.inputs["envelope_pin"],
                sources=self.inputs["source_pin"],
                genesis=q.genesis(self.inputs["envelope_pin"]), tick=5)

    def test_arbitrary_caller_root_is_rejected(self):
        for root in ("a"*64,
                     custody.ledger_root(q.genesis(self.inputs["envelope_pin"]),
                                         self.inputs["custody_pin"], "b"*64)):
            with self.subTest(root=root), self.assertRaisesRegex(h.Invalid, "journal-root"):
                finalize(self.inputs, self.pinned, journal_root=root)

    def test_stale_root_after_acl_change_is_rejected(self):
        acl = h.parse(self.inputs["acl_raw"]) | {"expires": 24}
        fresh = with_acl(self.inputs, acl)
        fresh_spec = q.prepare(**fresh)
        self.assertNotEqual(fresh_spec.genesis, self.run_spec.genesis)
        with self.assertRaisesRegex(h.Invalid, "journal-root"):
            finalize(fresh, checkpoint(fresh_spec), journal_root=self.run_spec.genesis)
        finalized = finalize(fresh, checkpoint(fresh_spec), journal_root=fresh_spec.genesis)
        self.assertEqual(finalized.trust, "EXTERNAL_ANCHOR_UNVERIFIED")

    def test_checkpoint_must_match_the_ledger_root(self):
        packet = h.parse(self.pinned[0]) | {"root": q.genesis(self.inputs["envelope_pin"])}
        forged = h.canonical(packet)
        with self.assertRaisesRegex(h.Invalid, "checkpoint-binding"):
            finalize(self.inputs, (forged, h.digest(forged)),
                     journal_root=self.run_spec.genesis)

    def test_official_path_derives_genesis_from_the_envelope(self):
        # finalize binds what the caller asserts; only prepare ties proof.genesis
        # back to the pinned envelope, so substitution must fail there.
        proof = h.parse(self.inputs["custody_raw"])
        proof["genesis"] = "c"*64
        packed = h.canonical(proof)
        with self.assertRaisesRegex(h.Invalid, "custody-binding"):
            q.prepare(**(self.inputs | {"custody_raw": packed,
                                        "custody_pin": h.digest(packed)}))


class ReplayConsumptionTests(unittest.TestCase):
    """NEW-1/NEW-2: validation is pure, consumption is one-time and persistent."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.run_spec = q.prepare(**cls.inputs)
        cls.pinned = checkpoint(cls.run_spec)

    def signed(self, **changes):
        return sign_receipt(self.inputs, self.pinned, root=self.run_spec.genesis, **changes)

    def verified(self, pair):
        return receipt.verify(pair[0], pair[1], trusted=trusted(), now=5,
                              envelope=self.inputs["envelope_pin"],
                              checkpoint_pin=self.pinned[1], root=self.run_spec.genesis,
                              sequence=0, tip=self.run_spec.genesis)

    def bindings(self):
        return dict(now=5, envelope=self.inputs["envelope_pin"],
                    checkpoint=self.pinned[1], root=self.run_spec.genesis,
                    sequence=0, tip=self.run_spec.genesis)

    def store(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "replay.db"
        return path, receipt.ReplayStore.create(path)

    def test_validation_is_pure_and_repeatable(self):
        signed = self.signed()
        first, second = self.verified(signed), self.verified(signed)
        self.assertEqual(first, second)
        self.assertFalse(hasattr(first, "trust"))
        path, store = self.store()
        self.assertEqual(receipt.consume(store, first, 5), "MOCK_CONSUMED_ONCE")
        with self.assertRaisesRegex(h.Invalid, "receipt-replay"):
            receipt.consume(receipt.ReplayStore(path), second, 5)

    def test_same_process_double_consumption_is_rejected(self):
        signed = self.signed()
        _, store = self.store()
        receipt.consume(store, self.verified(signed), 5)
        with self.assertRaisesRegex(h.Invalid, "receipt-replay"):
            receipt.consume(store, self.verified(signed), 5)

    def test_cross_process_consumption_persists(self):
        signed = self.signed()
        path, _ = self.store()
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        process = ctx.Process(target=consume_in_child,
                              args=(str(path), signed[0], signed[1], self.bindings(), queue))
        process.start()
        try:
            process.join(30)
            self.assertEqual(process.exitcode, 0)
        finally:
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
        self.assertEqual(queue.get(timeout=5), ("ACCEPT", "MOCK_CONSUMED_ONCE"))
        with self.assertRaisesRegex(h.Invalid, "receipt-replay"):
            receipt.consume(receipt.ReplayStore(path), self.verified(signed), 5)

    def test_concurrent_consumption_admits_exactly_one(self):
        signed = self.signed()
        path, _ = self.store()
        verified = self.verified(signed)
        gate = Barrier(4)

        def consume():
            gate.wait(timeout=10)
            try:
                return receipt.consume(receipt.ReplayStore(path), verified, 5)
            except h.Invalid as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: consume(), range(4)))
        self.assertEqual(results.count("MOCK_CONSUMED_ONCE"), 1)
        self.assertEqual(results.count("receipt-replay"), 3)

    def test_invalid_receipt_never_consumes(self):
        signed = self.signed()
        _, store = self.store()
        document = h.parse(signed[0])
        tampered = h.canonical(document | {"mac": "0"*64})
        with self.assertRaisesRegex(h.Invalid, "receipt-mac"):
            finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis,
                     store=store, receipt_pair=(tampered, h.digest(tampered)))
        finalized = finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis,
                             store=store, receipt_pair=signed)
        self.assertEqual(finalized.replay, "MOCK_CONSUMED_ONCE")

    def test_distinct_valid_nonces_are_independent(self):
        _, store = self.store()
        for nonce in ("mock-nonce-one", "mock-nonce-two"):
            finalized = finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis,
                                 store=store, receipt_pair=self.signed(nonce=nonce))
            self.assertEqual(finalized.replay, "MOCK_CONSUMED_ONCE")

    def test_same_nonce_with_different_bytes_conflicts(self):
        path, store = self.store()
        first = self.signed(nonce="mock-nonce-fixed", issued=4)
        later = self.signed(nonce="mock-nonce-fixed", issued=3)
        self.assertNotEqual(first[1], later[1])
        receipt.consume(store, self.verified(first), 5)
        with self.assertRaisesRegex(h.Invalid, "receipt-conflict"):
            receipt.consume(receipt.ReplayStore(path), self.verified(later), 5)

    def test_receipt_requires_a_persistent_store(self):
        with self.assertRaisesRegex(h.Invalid, "replay-store-required"):
            finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis,
                     receipt_pair=self.signed())

    def test_store_schema_tamper_is_rejected(self):
        path, _ = self.store()
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE injected (x INTEGER)")
        with self.assertRaisesRegex(h.Invalid, "replay-schema"):
            receipt.consume(receipt.ReplayStore(path), self.verified(self.signed()), 5)

    def test_consumption_is_labelled_mock_not_external_trust(self):
        _, store = self.store()
        finalized = finalize(self.inputs, self.pinned, journal_root=self.run_spec.genesis,
                             store=store, receipt_pair=self.signed())
        self.assertEqual(finalized.trust, "MOCK_EXTERNAL_RECEIPT")
        self.assertEqual(finalized.replay, "MOCK_CONSUMED_ONCE")
        self.assertEqual(finalized.custody.proof["real_evidence"], "NOT_VERIFIED")


class ReviewerOrderTests(unittest.TestCase):
    """NEW-3: two independent reviews in explicit, non-decreasing event order."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()

    def proof(self):
        return h.parse(self.inputs["custody_raw"])

    def test_reversed_review_ticks_are_rejected(self):
        proof = self.proof()
        reversed_reviews = [dict(proof["reviews"][0], tick=2), dict(proof["reviews"][1], tick=1)]
        with self.assertRaisesRegex(h.Invalid, "custody-review-order"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": reversed_reviews}))

    def test_equal_ticks_follow_explicit_list_order(self):
        proof = self.proof()
        for tick in (1, 2):
            with self.subTest(tick=tick):
                reviews = [dict(proof["reviews"][0], tick=tick),
                           dict(proof["reviews"][1], tick=tick)]
                self.assertIsNotNone(
                    q.prepare(**pin_proof(self.inputs, proof | {"reviews": reviews})))

    def test_chronological_ticks_are_accepted(self):
        proof = self.proof()
        reviews = [dict(proof["reviews"][0], tick=1), dict(proof["reviews"][1], tick=2)]
        self.assertIsNotNone(q.prepare(**pin_proof(self.inputs, proof | {"reviews": reviews})))

    def test_duplicate_reviewer_and_reference_are_rejected(self):
        proof = self.proof()
        same_reviewer = [proof["reviews"][0], dict(proof["reviews"][1],
                                                   by=proof["reviews"][0]["by"])]
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": same_reviewer}))
        same_reference = [proof["reviews"][0], dict(proof["reviews"][1],
                                                    reference=proof["reviews"][0]["reference"])]
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": same_reference}))

    def test_reviewer_role_separation_survives_ordering(self):
        proof = self.proof()
        swapped = [dict(proof["reviews"][0], by=proof["roles"]["semantic_two"]),
                   dict(proof["reviews"][1], by=proof["roles"]["semantic_one"])]
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": swapped}))


class RevocationBoundaryTests(unittest.TestCase):
    """NEW-4: revocation checks are enforced, but mock pins carry no real authority."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()

    def proof(self):
        return h.parse(self.inputs["custody_raw"])

    def test_live_revocation_blocks_use_and_future_revocation_does_not(self):
        proof = self.proof()
        live = dict(target=proof["roles"]["semantic_one"], tick=3, reference="mock-revoke")
        with self.assertRaisesRegex(h.Invalid, "custody-revoked"):
            q.prepare(**pin_proof(self.inputs, proof | {"revocations": [live]}))
        future = dict(live, tick=6)
        self.assertIsNotNone(
            q.prepare(**pin_proof(self.inputs, proof | {"revocations": [future]})))

    def test_unknown_and_duplicate_revocation_targets_are_rejected(self):
        proof = self.proof()
        unknown = [dict(target="mock-outsider", tick=3, reference="mock-revoke")]
        with self.assertRaisesRegex(h.Invalid, "custody-revocation"):
            q.prepare(**pin_proof(self.inputs, proof | {"revocations": unknown}))
        duplicate = [dict(target=proof["roles"]["semantic_one"], tick=3,
                          reference="mock-revoke-one"),
                     dict(target=proof["roles"]["semantic_one"], tick=4,
                          reference="mock-revoke-two")]
        with self.assertRaisesRegex(h.Invalid, "custody-revocation"):
            q.prepare(**pin_proof(self.inputs, proof | {"revocations": duplicate}))

    def test_real_evidence_cannot_be_claimed(self):
        proof = self.proof()
        with self.assertRaisesRegex(h.Invalid, "custody-isolation"):
            q.prepare(**pin_proof(self.inputs, proof | {"real_evidence": "VERIFIED"}))

    def test_pinned_role_names_are_caller_labels_not_identities(self):
        # Boundary, documented rather than fixed: a caller who controls the pinned
        # bytes can rename a mock principal. Mock custody proves internal
        # consistency only; real identity, signatures and revocation authority
        # stay NOT_VERIFIED outside this repository.
        proof = self.proof()
        proof["roles"]["author"] = "mock-author-two"
        run_spec = q.prepare(**pin_proof(self.inputs, proof))
        self.assertEqual(run_spec.cases[0].guards, q.prepare(**self.inputs).cases[0].guards)


if __name__ == "__main__":
    unittest.main()
