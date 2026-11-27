"""Adversarial regression tests for the F3-F7 findings raised on PR #73.

Every value here is public-synthetic. The mock external receipt uses a bundled
public key and therefore proves no real identity, signature or custody.
"""
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from scripts import offline_corpus63 as corpus
from scripts import offline_custody72 as custody
from scripts import offline_heldout67 as h
from scripts import offline_qualification72 as q
from scripts import offline_receipt72 as receipt
from scripts import offline_source72 as source
from offline_fixture72 import CLAIMS, checkpoint, fixture, prove, sign_receipt, trace, trusted


def reseal_case(inputs, index, raw):
    """Re-pin one raw case in a fully resealed envelope and custody proof."""
    cases = list(inputs["cases_raw"])
    cases[index] = raw
    envelope = h.parse(inputs["envelope_raw"])
    entries = [dict(entry) for entry in envelope["cases"]]
    entries[index] = {"id": h.parse(raw)["case"], "sha256": h.digest(raw), "bytes": len(raw)}
    packed = h.canonical(envelope | {"cases": entries})
    fresh = dict(inputs, envelope_raw=packed, envelope_pin=h.digest(packed), cases_raw=cases)
    prove(fresh)
    return fresh


def pin_proof(inputs, proof):
    raw = h.canonical(proof)
    return dict(inputs, custody_raw=raw, custody_pin=h.digest(raw))


def with_acl(inputs, acl, proof=None):
    acl_raw = h.canonical(acl)
    proof = h.parse(inputs["custody_raw"]) if proof is None else proof
    proof["acl"] = h.digest(acl_raw)
    return pin_proof(dict(inputs, acl_raw=acl_raw, acl_pin=h.digest(acl_raw)), proof)


class SafeguardAuthenticationTests(unittest.TestCase):
    """F4/F7: a pinned envelope must authenticate the safeguard set itself."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.run_spec = q.prepare(**cls.inputs)

    def test_stripped_required_read_is_rejected_at_case_profile(self):
        original = self.inputs["cases_raw"][0]
        row = h.parse(original)
        self.assertEqual(len(row["required_reads"]), 2)
        stripped = h.canonical(row | {"required_reads": [row["required_claims"][0]["id"]]})
        # The compiled bundle is unchanged, so the manifest pin alone cannot see it.
        self.assertEqual(source.adapt(stripped, CLAIMS).bundle,
                         source.adapt(original, CLAIMS).bundle)
        fresh = reseal_case(self.inputs, 0, stripped)
        with self.assertRaisesRegex(h.Invalid, "case-profile"):
            q.prepare(**fresh)

    def test_stripped_forbidden_claim_is_rejected_at_case_profile(self):
        original = self.inputs["cases_raw"][0]
        row = h.parse(original)
        stripped = h.canonical(row | {"forbidden_claims": row["forbidden_claims"][1:]})
        self.assertEqual(source.adapt(stripped, CLAIMS).bundle,
                         source.adapt(original, CLAIMS).bundle)
        with self.assertRaisesRegex(h.Invalid, "case-profile"):
            q.prepare(**reseal_case(self.inputs, 0, stripped))

    def test_case_bytes_still_must_match_the_envelope_entry(self):
        changed = list(self.inputs["cases_raw"])
        row = h.parse(changed[0])
        changed[0] = h.canonical(row | {"forbidden_claims": row["forbidden_claims"][1:]})
        with self.assertRaisesRegex(h.Invalid, "case-pin"):
            q.prepare(**(self.inputs | {"cases_raw": changed}))

    def test_guard_digest_names_the_safeguards_applied(self):
        row = h.parse(self.inputs["cases_raw"][0])
        stripped = h.canonical(row | {"required_reads": [row["required_claims"][0]["id"]]})
        self.assertNotEqual(source.adapt(stripped, CLAIMS).guards,
                            self.run_spec.cases[0].guards)
        runner = self.runner()
        candidate = runner.submit(0, trace(self.run_spec, 0), 6, checkpoint(self.run_spec))
        pinned = checkpoint(self.run_spec, 1, candidate.anchor)
        self.assertEqual(runner.confirm(0, pinned).guards, self.run_spec.cases[0].guards)

    def test_legacy_diagnostic_helper_cannot_authorize_the_guarded_case(self):
        raw = h.parse(trace(self.run_spec, 0))
        case = self.run_spec.cases[0]
        by_id = {key: tuple(ref) for key, ref, _ in case.allowed}
        answered = {entry["id"] for entry in h.parse(self.inputs["cases_raw"][0])["required_claims"]}
        extra = next(iter(case.must_read - {by_id[key] for key in answered}))
        reads = [read for read in raw["observation"]["reads"] if tuple(read["ref"]) != extra]
        forged = h.canonical(raw | {"observation": raw["observation"] | {"reads": reads}})
        observation = h.canonical(h.parse(forged)["observation"])
        legacy = h.evaluate(self.run_spec.manifest, self.run_spec.manifest_pin, 0,
                            case.bundle, observation)
        self.assertEqual((legacy.outcome, legacy.authority), ("PASS", "DIAGNOSTIC"))
        official = h.evaluate(self.run_spec.manifest, self.run_spec.manifest_pin, 0,
                              case.bundle, observation, required_reads=case.must_read,
                              forbidden_fact_ids=case.forbidden)
        self.assertEqual((official.outcome, official.code), ("STOP", "missing-required-read"))
        self.assertEqual(q.evaluate(0, forged, **self.inputs).outcome, "STOP")

    def runner(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return q.Runner.create(Path(tmp.name) / "test.db", **self.inputs)


class CheckpointTrustTests(unittest.TestCase):
    """F3: the journal proves internal consistency, never external custody."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.run_spec = q.prepare(**cls.inputs)

    def appended(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "test.db"
        runner = q.Runner.create(path, **self.inputs)
        candidate = runner.submit(0, trace(self.run_spec, 0), 6, checkpoint(self.run_spec))
        return path, runner, checkpoint(self.run_spec, 1, candidate.anchor)

    def test_receipt_records_unverified_external_anchor(self):
        path, runner, pinned = self.appended()
        self.assertEqual(runner.confirm(0, pinned).trust, "EXTERNAL_ANCHOR_UNVERIFIED")
        self.assertEqual(q.Runner.open(path, pinned, **self.inputs)
                         .confirm(0, pinned).trust, "EXTERNAL_ANCHOR_UNVERIFIED")

    def store(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return receipt.ReplayStore.create(Path(tmp.name) / "replay.db")

    def finalize(self, pinned, *, receipt_pair=None, store=None):
        material = self.inputs
        return custody.finalize(
            material["custody_raw"], material["custody_pin"],
            material["acl_raw"], material["acl_pin"],
            material["receipts_raw"], material["receipts_pin"],
            pinned[0], pinned[1], envelope=material["envelope_pin"],
            sources=material["source_pin"], genesis=q.genesis(material["envelope_pin"]),
            journal_root=self.run_spec.genesis, tick=5,
            receipt_raw=None if receipt_pair is None else receipt_pair[0],
            receipt_pin=None if receipt_pair is None else receipt_pair[1],
            trusted=trusted(), store=store)

    def test_checkpoint_only_finalization_is_unverified(self):
        _, _, pinned = self.appended()
        self.assertEqual(self.finalize(pinned).trust, "EXTERNAL_ANCHOR_UNVERIFIED")

    def test_checkpoint_must_bind_genesis(self):
        _, _, pinned = self.appended()
        packet = h.parse(pinned[0]) | {"root": "1"*64}
        forged = h.canonical(packet)
        with self.assertRaisesRegex(h.Invalid, "checkpoint-binding"):
            self.finalize((forged, h.digest(forged)))

    def test_mock_external_receipt_is_labelled_and_replay_protected(self):
        _, _, pinned = self.appended()
        signed = sign_receipt(self.inputs, pinned, root=self.run_spec.genesis)
        store = self.store()
        finalized = self.finalize(pinned, receipt_pair=signed, store=store)
        self.assertEqual(finalized.trust, "MOCK_EXTERNAL_RECEIPT")
        self.assertEqual(finalized.replay, "MOCK_CONSUMED_ONCE")
        with self.assertRaisesRegex(h.Invalid, "receipt-replay"):
            self.finalize(pinned, receipt_pair=signed, store=store)

    def test_receipt_requires_a_persistent_replay_store(self):
        _, _, pinned = self.appended()
        signed = sign_receipt(self.inputs, pinned, root=self.run_spec.genesis)
        with self.assertRaisesRegex(h.Invalid, "replay-store-required"):
            self.finalize(pinned, receipt_pair=signed)

    def test_receipt_rejects_tamper_stale_issuer_and_binding(self):
        _, _, pinned = self.appended()
        good = sign_receipt(self.inputs, pinned, root=self.run_spec.genesis)
        document = h.parse(good[0])
        tampered = h.canonical(document | {"mac": "0"*64})
        for pair, code in (
            ((tampered, h.digest(tampered)), "receipt-mac"),
            (sign_receipt(self.inputs, pinned, root=self.run_spec.genesis,
                          issued=0, expires=4), "receipt-freshness"),
            (sign_receipt(self.inputs, pinned, root=self.run_spec.genesis,
                          issuer="mock-outsider"), "receipt-issuer"),
            (sign_receipt(self.inputs, pinned, root=q.genesis(self.inputs["envelope_pin"])),
             "receipt-binding"),
            (sign_receipt(self.inputs, pinned, root=self.run_spec.genesis, tip="1"*64),
             "receipt-binding"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(h.Invalid, code):
                self.finalize(pinned, receipt_pair=pair, store=self.store())


class CustodyModelTests(unittest.TestCase):
    """F6: approval window, least privilege, two reviews, revocation, retention."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()

    def proof(self):
        return h.parse(self.inputs["custody_raw"])

    def acl(self):
        return h.parse(self.inputs["acl_raw"])

    def test_retention_relationship_and_deletion_clock(self):
        proof = self.proof()
        proof["retention"]["delete_by"] = 20  # earlier than acl.expires
        with self.assertRaisesRegex(h.Invalid, "custody-retention"):
            q.prepare(**pin_proof(self.inputs, proof))
        with self.assertRaisesRegex(h.Invalid, "custody-deleted"):
            q.prepare(**(self.inputs | {"tick": 40}))
        with self.assertRaisesRegex(h.Invalid, "custody-window"):
            q.prepare(**(self.inputs | {"tick": 30}))

    def test_approval_window_is_explicit_and_exclusive(self):
        proof = self.proof()
        proof["approval"]["until"] = 6
        with self.assertRaisesRegex(h.Invalid, "custody-approval"):
            q.prepare(**(pin_proof(self.inputs, proof) | {"tick": 6}))
        proof = self.proof()
        proof["approval"]["by"] = proof["roles"]["developer"]
        with self.assertRaisesRegex(h.Invalid, "custody-approval"):
            q.prepare(**pin_proof(self.inputs, proof))

    def test_rights_must_equal_least_privilege_exactly(self):
        for role, rights in (
            ("developer", ["read"]),
            ("author", ["review"]),
            ("semantic_one", ["read"]),
            ("owner", ["read"]),
        ):
            acl = self.acl()
            acl["rights"][role] = rights
            with self.subTest(role=role), self.assertRaisesRegex(h.Invalid, "custody-rights"):
                q.prepare(**with_acl(self.inputs, acl))

    def test_two_ordered_independent_reviews_are_required(self):
        proof = self.proof()
        swapped = list(reversed(proof["reviews"]))
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": swapped}))
        duplicated = [proof["reviews"][0], dict(proof["reviews"][1],
                                                reference=proof["reviews"][0]["reference"])]
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": duplicated}))
        same_reviewer = [proof["reviews"][0], dict(proof["reviews"][1],
                                                   by=proof["reviews"][0]["by"])]
        with self.assertRaisesRegex(h.Invalid, "custody-review"):
            q.prepare(**pin_proof(self.inputs, proof | {"reviews": same_reviewer}))

    def test_revocation_blocks_use_and_future_revocation_does_not(self):
        proof = self.proof()
        live = {"target": proof["roles"]["semantic_one"], "tick": 3, "reference": "mock-revoke"}
        with self.assertRaisesRegex(h.Invalid, "custody-revoked"):
            q.prepare(**pin_proof(self.inputs, proof | {"revocations": [live]}))
        future = dict(live, tick=6)
        self.assertIsNotNone(q.prepare(**pin_proof(self.inputs, proof | {"revocations": [future]})))

    def test_access_log_must_bind_acl_revision_and_reader_rights(self):
        for log in (
            dict(acl_revision=2, reviewed=2, entries=[
                dict(principal="mock-custodian", action="MOCK_READ", tick=1)]),
            dict(acl_revision=1, reviewed=2, entries=[
                dict(principal="mock-developer", action="MOCK_READ", tick=1)]),
        ):
            with self.subTest(log=log):
                receipts = h.parse(self.inputs["receipts_raw"])
                receipts["access_log"] = log
                acl_raw = h.canonical(self.acl() | {"access_log": h.digest(h.canonical(log))})
                proof = self.proof()
                proof["acl"] = h.digest(acl_raw)
                receipts_raw = h.canonical(receipts)
                proof["receipts"] = h.digest(receipts_raw)
                packed = h.canonical(proof)
                with self.assertRaisesRegex(h.Invalid, "custody-access-log"):
                    q.prepare(**(self.inputs | {
                        "acl_raw": acl_raw, "acl_pin": h.digest(acl_raw),
                        "receipts_raw": receipts_raw, "receipts_pin": h.digest(receipts_raw),
                        "custody_raw": packed, "custody_pin": h.digest(packed)}))

    def test_acl_expiry_must_stay_inside_approval_and_current_tick(self):
        acl = self.acl()
        acl["expires"] = 31
        with self.assertRaisesRegex(h.Invalid, "custody-acl"):
            q.prepare(**with_acl(self.inputs, acl))
        acl = self.acl()
        acl["expires"] = 5
        with self.assertRaisesRegex(h.Invalid, "custody-acl"):
            q.prepare(**with_acl(self.inputs, acl))
        acl = self.acl()
        acl["reviewed"] = 6
        with self.assertRaisesRegex(h.Invalid, "custody-acl"):
            q.prepare(**with_acl(self.inputs, acl))


class MalformedCaseTests(unittest.TestCase):
    """F7: the case adapter fails closed on abnormal public-synthetic inputs."""

    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.original = cls.inputs["cases_raw"][0]
        cls.row = h.parse(cls.original)

    def adapt(self, value):
        return source.adapt(h.canonical(value), CLAIMS)

    def test_non_integer_clocks_and_duplicate_safeguards(self):
        for edit, code in (
            ({"as_of": True}, "source-clock"),
            ({"required_reads": [self.row["required_reads"][0],
                                 self.row["required_reads"][0]]}, "claim-order"),
            ({"forbidden_claims": ["forged"]}, "claim-policy"),
            ({"allowed_claims": []}, "claim-policy"),
            ({"tenant": "ZENA"}, "case-scope"),
            ({"rights": "third-party"}, "case-scope"),
            ({"extra": 1}, "unsupported-case-fields"),
        ):
            with self.subTest(edit=edit), self.assertRaisesRegex(h.Invalid, code):
                self.adapt(self.row | edit)

    def test_abnormal_bytes_fail_closed(self):
        for raw, code in (
            (self.original + b" " * h.MAX_BYTES, "bytes"),
            (b'{"schema":"offline72-case-v1","schema":"x"}', "duplicate-key"),
            (b"", "bytes"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(h.Invalid, code):
                source.adapt(raw, CLAIMS)
        float_clock = self.original.replace(b'"as_of":1', b'"as_of":1.0')
        with self.assertRaisesRegex(h.Invalid, "number"):
            source.adapt(float_clock, CLAIMS)
        indented = corpus.canonical(self.row)
        with self.assertRaisesRegex(h.Invalid, "noncanonical"):
            source.adapt(indented, CLAIMS)

    def test_forged_allowed_claim_fails_source_authority(self):
        retired = min(key for key, claim in CLAIMS.items() if claim["status"] != "active")
        allowed = sorted(set(self.row["allowed_claims"]) | {retired})
        with self.assertRaisesRegex(h.Invalid, "source-authority"):
            self.adapt(self.row | {"allowed_claims": allowed,
                                   "forbidden_claims": sorted(
                                       set(self.row["forbidden_claims"]) - {retired})})


if __name__ == "__main__":
    unittest.main()
