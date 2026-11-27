"""Acceptance tests for the public-synthetic qualification path."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import multiprocessing
import os
from pathlib import Path
import socket
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import patch

from scripts import offline_corpus63 as corpus
from scripts import offline_heldout67 as h
from scripts import offline_source72 as source
from scripts import offline_qualification72 as q
from offline_fixture72 import CLAIMS, checkpoint, fixture, prove, trace


def commit_then_exit(path, materials, raw, root):
    runner = q.Runner.open(path, root, **materials)
    runner.submit(0, raw, 6, root)
    os._exit(17)


class QualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.run_spec = q.prepare(**cls.inputs)
        cls.root = checkpoint(cls.run_spec)

    def runner(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "test.db"
        return path, q.Runner.create(path, **self.inputs)

    def altered(self, index=0, **changes):
        raw = h.parse(trace(self.run_spec, index))
        raw["observation"].update(changes)
        return h.canonical(raw)

    def parity(self, index, raw, expected):
        preview = q.evaluate(index, raw, **self.inputs)
        self.assertEqual((preview.outcome, preview.code), expected)
        _, runner = self.runner()
        tip = self.root
        for before in range(index):
            candidate = runner.submit(before, None, 6, tip)
            tip = checkpoint(self.run_spec, before+1, candidate.anchor)
        candidate = runner.submit(index, raw, 6, tip)
        self.assertIs(type(candidate), q.PendingAnchor)
        accepted = runner.confirm(index, checkpoint(self.run_spec, index+1, candidate.anchor))
        self.assertEqual((accepted.outcome, accepted.code, accepted.hits, accepted.gold),
                         (preview.outcome, preview.code, preview.hits, preview.gold))

    def test_authorized_60_by_2_uses_each_official_position(self):
        _, runner = self.runner()
        tip = self.root
        counts = {1: 0, 2: 0}
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            for index in range(120):
                candidate = runner.submit(index, trace(self.run_spec, index), 6, tip)
                tip = checkpoint(self.run_spec, index+1, candidate.anchor)
                receipt = runner.confirm(index, tip)
                self.assertEqual((receipt.index, receipt.outcome, receipt.code),
                                 (index, "PASS", "matched"))
                counts[receipt.repetition] += 1
        self.assertEqual(counts, {1: 60, 2: 60})
        self.assertEqual(runner.confirm(119, tip).chain_length, 120)
        self.assertEqual(set(CLAIMS), {key for case in self.run_spec.cases for key in case.forbidden}
                         | {key for case in self.run_spec.cases for key, _, _ in case.allowed})

    def test_twelve_distinct_mock_journeys(self):
        journeys = (
            (0, "answer", "text", 5), (6, "answer", "text", 5),
            (12, "answer", "decimal", 5), (18, "answer", "decimal", 5),
            (24, "answer", "integer", 5), (30, "answer", "text", 5),
            (36, "abstain", None, 0), (42, "clarify", None, 0),
            (48, "answer", "text", 5), (53, "abstain", None, 0),
            (54, "refuse", None, 0), (119, "refuse", None, 0),
        )
        _, runner = self.runner()
        tip = self.root
        for index in range(120):
            sample = trace(self.run_spec, index)
            candidate = runner.submit(index, sample, 6, tip)
            tip = checkpoint(self.run_spec, index+1, candidate.anchor)
        for index, behavior, kind, gold in journeys:
            with self.subTest(index=index):
                trace_row = h.parse(trace(self.run_spec, index))["observation"]
                self.assertEqual(trace_row["behavior"], behavior)
                self.assertEqual([x["kind"] for x in trace_row["facts"]], [kind] if kind else [])
                self.assertEqual(runner.confirm(index, tip).gold, gold)
                self.assertEqual(bool(trace_row["denied_deliveries"]), index == 53)

    def test_pass_inconclusive_not_run_and_quality_fail_have_parity(self):
        for raw, result in (
            (trace(self.run_spec, 0), ("PASS", "matched")),
            (self.altered(status="incomplete", facts=[], links=[], reads=[]),
             ("INCONCLUSIVE", "incomplete-trace")),
            (None, ("NOT_RUN", "no-observation")),
            (self.altered(behavior="clarify"), ("FAIL", "oracle-mismatch")),
        ):
            with self.subTest(result=result):
                self.parity(0, raw, result)

    def test_required_complete_read_is_a_hard_gate_even_without_output(self):
        self.parity(0, self.altered(facts=[], links=[], reads=[]),
                    ("STOP", "missing-required-read"))

    def test_forbidden_identifier_cannot_be_rendered_in_any_typed_form(self):
        forbidden = min(self.run_spec.cases[0].forbidden)
        for kind, value, unit in (
            ("text", "fictional", None), ("integer", 3, "count"),
            ("decimal", "3.00", "VND"), ("boolean", True, None),
        ):
            for status in ("complete", "incomplete"):
                with self.subTest(kind=kind, status=status):
                    self.parity(0, self.altered(status=status, links=[],
                                facts=[dict(id=forbidden, kind=kind, value=value, unit=unit)]),
                                ("STOP", "forbidden-typed-fact"))

    def test_unsupported_and_malformed_traces_stop_in_all_paths(self):
        valid = trace(self.run_spec, 0)
        for raw, code in (
            (self.altered(links=[]), "unsupported-output"),
            (valid + b"\n", "noncanonical"),
            (b"{", "encoding"),
            (b'{"observation":null,"observation":null,"ranked":[]}\n', "duplicate-key"),
            (self.altered(writes=["mock-ticket"]), "unauthorized-effect"),
            (self.altered(repetition=2), "observation-binding"),
        ):
            with self.subTest(code=code):
                self.parity(0, raw, ("STOP", code))

    def test_revoked_delivery_blocks_output_and_records_denial(self):
        index = 53
        self.parity(index, trace(self.run_spec, index), ("PASS", "matched"))
        self.parity(index, self.altered(index, denied_deliveries=[]),
                    ("STOP", "missing-delivery-denial"))
        output = dict(id="invented", kind="boolean", value=True, unit=None)
        self.parity(index, self.altered(index, facts=[output]), ("STOP", "revoked-output"))
        ref = list(next(iter(self.run_spec.cases[index].must_read)))
        self.parity(index, self.altered(index, reads=[dict(ref=ref, tick=3, epoch=1)]),
                    ("STOP", "unauthorized-read"))

    def test_claim_recall_dedupes_before_top_five_in_stable_order(self):
        raw = h.parse(trace(self.run_spec, 0))
        full = q.evaluate(0, h.canonical(raw), **self.inputs)
        self.assertEqual((full.hits, full.gold), (5, 5))
        by_id = {key: list(ref) for key, ref, _ in self.run_spec.cases[0].allowed}
        irrelevant = sorted(set(by_id) - self.run_spec.cases[0].gold)
        first, second, third, fourth, fifth = raw["ranked"]
        raw["ranked"] = [first, first, *[dict(id=key, ref=by_id[key], tick=2)
                        for key in irrelevant[:2]], second, third, fourth, fifth]
        partial = q.evaluate(0, h.canonical(raw), **self.inputs)
        self.assertEqual((partial.hits, partial.gold), (3, 5))
        self.assertEqual((partial.outcome, partial.code), ("PASS", "matched"))
        raw["ranked"] = []
        empty = q.evaluate(0, h.canonical(raw), **self.inputs)
        self.assertEqual((empty.hits, empty.gold), (0, 5))
        self.assertEqual(q.evaluate(36, trace(self.run_spec, 36), **self.inputs).gold, 0)
        self.assertIsNone(q.evaluate(0, None, **self.inputs).gold)

    def test_unauthorized_ranked_tail_never_silently_lowers_recall(self):
        raw = h.parse(trace(self.run_spec, 0))
        last = raw["ranked"][-1]
        retired = [dict(id=key, ref=[claim["tenant"], *corpus.reference(claim)], tick=4)
                   for key, claim in CLAIMS.items() if claim["status"] != "active"]
        for attack in (*retired,
                       {**last, "ref": ["HANU", *last["ref"][1:]]},
                       {**last, "ref": [*last["ref"][:2], 999, last["ref"][3]]},
                       {**last, "tick": 1}):
            with self.subTest(attack=attack):
                forged = h.canonical(raw | {"ranked": [*raw["ranked"], attack]})
                self.parity(0, forged, ("STOP", "unauthorized-retrieval"))
        raw = h.parse(trace(self.run_spec, 53))
        (key, ref, _), = [(key, ref, end) for key, ref, end in self.run_spec.cases[53].allowed
                         if ref in self.run_spec.cases[53].must_read]
        raw["ranked"] = [dict(id=key, ref=list(ref), tick=3)]
        self.parity(53, h.canonical(raw), ("STOP", "unauthorized-retrieval"))

    def test_no_receipt_before_commit_or_without_latest_external_checkpoint(self):
        path, runner = self.runner()
        with self.assertRaisesRegex(h.Invalid, "uncommitted-receipt"):
            runner.confirm(0, self.root)
        candidate = runner.submit(0, trace(self.run_spec, 0), 6, self.root)
        with self.assertRaisesRegex(h.Invalid, "externally-pinned-anchor"):
            runner.confirm(0, candidate.anchor)
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            runner.confirm(0, self.root)
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            q.Runner.open(path, self.root, **self.inputs)
        external = checkpoint(self.run_spec, 1, candidate.anchor)
        with self.assertRaisesRegex(h.Invalid, "artifact-pin"):
            runner.confirm(0, (external[0], self.root[1]))
        self.assertEqual(q.Runner.open(path, external, **self.inputs).confirm(0, external).outcome,
                         "PASS")

    def test_replay_order_stop_latch_and_expired_or_rewound_clock(self):
        path, runner = self.runner()
        raw = trace(self.run_spec, 0)
        for index, tick, code in ((1, 6, "ledger-order"), (-1, 6, "journal-position"),
                                  (0, 4, "rewound-clock")):
            with self.subTest(code=code), self.assertRaisesRegex(h.Invalid, code):
                runner.submit(index, raw, tick, self.root)
        first = runner.submit(0, raw, 6, self.root)
        tip = checkpoint(self.run_spec, 1, first.anchor)
        self.assertEqual(runner.submit(0, raw, 6, tip), first)
        for replay, tick in ((raw+b"\n", 6), (raw, 7), (None, 6)):
            with self.subTest(tick=tick, replay=replay), self.assertRaisesRegex(h.Invalid, "changed-replay"):
                runner.submit(0, replay, tick, tip)
        with self.assertRaisesRegex(h.Invalid, "rewound-clock"):
            runner.submit(1, None, 5, tip)
        expired = runner.submit(1, None, 30, tip)
        final = checkpoint(self.run_spec, 2, expired.anchor)
        reopened = q.Runner.open(path, final, **self.inputs)
        self.assertEqual(reopened.confirm(1, final).code, "expired-mock-custody")
        with self.assertRaisesRegex(h.Invalid, "ledger-stopped"):
            reopened.submit(2, None, 31, final)

    def test_committed_stop_blocks_even_when_subsequent_trace_is_valid(self):
        _, runner = self.runner()
        candidate = runner.submit(0, self.altered(facts=[], links=[], reads=[]), 6, self.root)
        tip = checkpoint(self.run_spec, 1, candidate.anchor)
        with self.assertRaisesRegex(h.Invalid, "ledger-stopped"):
            runner.submit(1, trace(self.run_spec, 1), 6, tip)

    def test_competing_writers_cannot_both_append_with_same_checkpoint(self):
        _, runner = self.runner()
        gate = Barrier(2)
        raw = trace(self.run_spec, 0)

        def submit():
            gate.wait(timeout=10)
            try:
                return runner.submit(0, raw, 6, self.root)
            except h.Invalid as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            one, two = tuple(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sum(isinstance(value, q.PendingAnchor) for value in (one, two)), 1)
        self.assertIn("anchor-mismatch", (one, two))

    def test_process_crash_after_commit_requires_independent_recovery(self):
        path, _ = self.runner()
        raw = trace(self.run_spec, 0)
        ctx = multiprocessing.get_context("spawn")
        process = ctx.Process(target=commit_then_exit, args=(path, self.inputs, raw, self.root))
        process.start()
        try:
            process.join(15)
            self.assertEqual(process.exitcode, 17)
        finally:
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            q.Runner.open(path, self.root, **self.inputs)
        with self.assertRaisesRegex(h.Invalid, "recovery-evidence"):
            q.Runner.recover(path, 0, None, 6, self.root, **self.inputs)
        pending = q.Runner.recover(path, 0, raw, 6, self.root, **self.inputs)
        self.assertIs(type(pending), q.PendingAnchor)
        tip = checkpoint(self.run_spec, 1, pending.anchor)
        self.assertEqual(q.Runner.open(path, tip, **self.inputs).confirm(0, tip).outcome, "PASS")

    def test_transaction_commit_error_rolls_back_append(self):
        _, runner = self.runner()
        connect = sqlite3.connect

        class FailsCommit(sqlite3.Connection):
            def commit(self):
                raise sqlite3.OperationalError("invented disk fault")

        with patch.object(sqlite3, "connect",
                          side_effect=lambda *a, **k: connect(*a, **k, factory=FailsCommit)):
            with self.assertRaisesRegex(h.Invalid, "journal-storage"):
                runner.submit(0, None, 6, self.root)
        with self.assertRaisesRegex(h.Invalid, "uncommitted-receipt"):
            runner.confirm(0, self.root)

    def test_rehash_rollback_and_genesis_substitution_detected(self):
        path, runner = self.runner()
        pending = runner.submit(0, None, 6, self.root)
        tip = checkpoint(self.run_spec, 1, pending.anchor)
        with closing(sqlite3.connect(path)) as db, db:
            trigger, = db.execute("SELECT sql FROM sqlite_master WHERE name='receipt_no_update'").fetchone()
            payload, = db.execute("SELECT payload FROM receipt").fetchone()
            rehashed = h.canonical(h.parse(payload) | {"outcome": "PASS"})
            db.execute("DROP TRIGGER receipt_no_update")
            db.execute("UPDATE receipt SET payload=?,anchor=?", (rehashed, h.digest(rehashed)))
            db.execute(trigger)
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            q.Runner.open(path, tip, **self.inputs)
        with closing(sqlite3.connect(path)) as db, db:
            trigger, = db.execute("SELECT sql FROM sqlite_master WHERE name='receipt_no_delete'").fetchone()
            db.execute("DROP TRIGGER receipt_no_delete")
            db.execute("DELETE FROM receipt")
            db.execute(trigger)
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            q.Runner.open(path, tip, **self.inputs)
        alternate = reseal(self.inputs, field="run_id", value="mock-alternate")
        replacement = q.prepare(**alternate)
        with self.assertRaisesRegex(h.Invalid, "journal-context"):
            q.Runner.open(path, checkpoint(replacement), **alternate)
        with self.assertRaisesRegex(h.Invalid, "checkpoint-binding"):
            q.Runner.open(path, checkpoint(replacement), **self.inputs)


def reseal(materials, field, value):
    result = materials.copy()
    raw = h.canonical(h.parse(result["envelope_raw"]) | {field: value})
    result.update(envelope_raw=raw, envelope_pin=h.digest(raw))
    prove(result)
    return result


class CustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()

    def test_source_pin_count_and_revision(self):
        raw = self.inputs["source_raw"]
        sources = corpus.parse(raw)
        shortened = corpus.canonical(sources | {"claims": sources["claims"][:-1]})
        with self.assertRaisesRegex(h.Invalid, "source-inventory"):
            source.corpus(shortened, h.digest(shortened))
        changed = corpus.canonical(sources | {"claims": [
            sources["claims"][0] | {"version": 5}, *sources["claims"][1:]]})
        with self.assertRaisesRegex(h.Invalid, "source-profile"):
            source.corpus(changed, h.digest(changed))
        with self.assertRaisesRegex(h.Invalid, "artifact-pin"):
            source.corpus(changed, self.inputs["source_pin"])

    def test_custody_adapter_rejects_excerpt_foreign_tenant_swap_and_orphans(self):
        example = h.parse(self.inputs["cases_raw"][0])
        claim = example["required_claims"][0]
        with self.assertRaisesRegex(h.Invalid, "claim-value"):
            source.adapt(h.canonical(example | {"required_claims": [
                claim | {"expected_typed_value": "changed"}]}), CLAIMS)
        for edits, code in (
            ({"tenant": "HANU"}, "case-scope"),
            ({"as_of": 31_536_000}, "source-authority"),
            ({"case": "ga61-qa-offering-01"}, "case-id"),
            ({"scope": "PRIVATE"}, "private-not-authorized"),
            ({"allowed_writes": []}, "unsupported-case-fields"),
            ({"writes": ["mock-ticket"]}, "unsupported-effect-policy"),
            ({"allowed_claims": example["allowed_claims"] + example["allowed_claims"]},
             "claim-order"),
            ({"required_claims": [claim, claim]}, "claim-order"),
            ({"required_claims": [claim | {"id": example["forbidden_claims"][0]}]}, "claim-binding"),
            ({"required_claims": [claim | {"citation": claim["citation"] |
              {"source_sha256": "1"*64}}]}, "source-citation"),
            ({"required_claims": [claim | {"citation": claim["citation"] |
              {"version": 170}}]}, "source-citation"),
            ({"required_claims": [claim | {"statement": "invented excerpt"}]}, "claim-binding"),
            ({"retrieval_relevance": list(reversed(example["retrieval_relevance"]))}, "claim-order"),
        ):
            with self.subTest(edits=edits), self.assertRaisesRegex(h.Invalid, code):
                source.adapt(h.canonical(example | edits), CLAIMS)
        quote = h.parse(self.inputs["cases_raw"][18])
        with self.assertRaisesRegex(h.Invalid, "orphan-total"):
            source.adapt(h.canonical(quote | {"required_claims": []}), CLAIMS)

    def test_manifest_cannot_drop_reorder_rebind_or_replace_records(self):
        envelope = h.parse(self.inputs["envelope_raw"])
        entries = envelope["cases"]
        for field, value, code in (
            ("scope", "PRIVATE", "private-not-authorized"),
            ("cases", entries[:-1], "case-inventory"),
            ("cases", list(reversed(entries)), "case-pin"),
            ("manifest", "1"*64, "manifest-pin"),
            ("repetitions", [True, 2], "envelope-policy"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(h.Invalid, code):
                q.prepare(**reseal(self.inputs, field, value))
        changed = list(self.inputs["cases_raw"])
        changed[0] += b"\n"
        with self.assertRaisesRegex(h.Invalid, "case-pin"):
            q.prepare(**(self.inputs | {"cases_raw": changed}))
        with self.assertRaisesRegex(h.Invalid, "public-development-revision"):
            q.prepare(**(self.inputs | {"development_raw": b"{}\n"}))

    def test_custody_mismatch_role_collision_stale_acl_and_missing_retention(self):
        proof = h.parse(self.inputs["custody_raw"])
        cases = (
            (proof | {"genesis": "1"*64}, "custody-binding"),
            (proof | {"roles": proof["roles"] | {"semantic_two": "mock-Semantic_one"}},
             "role-collision"),
            (proof | {"roles": proof["roles"] | {"developer": "mock-custodian"}}, "role-collision"),
            (proof | {"approval": proof["approval"] | {"by": "mock-developer"}}, "custody-approval"),
            (proof | {"approval": {"status": "MOCK_ONLY", "by": "mock-owner",
                                    "reference": "mock-ok"}}, "schema"),
            (proof | {"approval": {}}, "schema"),
            (proof | {"retention": {}}, "schema"),
            (proof | {"retention": proof["retention"] | {"deletion_receipt": ""}},
             "custody-retention"),
            (proof | {"real_evidence": "VERIFIED"}, "custody-isolation"),
        )
        for changed, code in cases:
            packed = h.canonical(changed)
            with self.subTest(code=code):
                with self.assertRaisesRegex(h.Invalid, "artifact-pin"):
                    q.prepare(**(self.inputs | {"custody_raw": packed}))
                with self.assertRaisesRegex(h.Invalid, code):
                    q.prepare(**(self.inputs | {"custody_raw": packed,
                                                "custody_pin": h.digest(packed)}))
        acl = h.canonical(h.parse(self.inputs["acl_raw"]) | {"revision": 2})
        with self.assertRaisesRegex(h.Invalid, "acl-drift"):
            q.prepare(**(self.inputs | {"acl_raw": acl, "acl_pin": h.digest(acl)}))
        with self.assertRaisesRegex(h.Invalid, "custody-acl"):
            q.prepare(**(self.inputs | {"tick": 25}))
        with self.assertRaisesRegex(h.Invalid, "custody-window"):
            q.prepare(**(self.inputs | {"tick": 0}))


    def test_external_receipts_and_acl_log_must_bind_to_proof_and_roles(self):
        receipts = h.parse(self.inputs["receipts_raw"])
        for field, value, code in (
            ("architecture", receipts["architecture"] | {"reference": "mock-forged"},
             "custody-approval"),
            ("retention", receipts["retention"] | {"state": "DELETED"}, "custody-retention"),
            ("isolation", receipts["isolation"] | {"ipv4_routes": ["invented-route"]},
             "custody-isolation"),
            ("access_log", receipts["access_log"] | {"entries": []}, "custody-access-log"),
            ("access_log", receipts["access_log"] | {"entries": [
                dict(principal="mock-developer", action="MOCK_READ", tick=1)]}, "custody-access-log"),
        ):
            with self.subTest(field=field, value=value):
                pack = h.canonical(receipts | {field: value})
                pins = self.inputs | {"receipts_raw": pack, "receipts_pin": h.digest(pack)}
                with self.assertRaisesRegex(h.Invalid, "custody-receipt-pin"):
                    q.prepare(**pins)
                acl = h.parse(pins["acl_raw"])
                if field == "access_log":
                    acl["access_log"] = h.digest(h.canonical(value))
                acl_raw = h.canonical(acl)
                proof = h.parse(pins["custody_raw"])
                proof.update(receipts=pins["receipts_pin"], acl=h.digest(acl_raw))
                proof_raw = h.canonical(proof)
                with self.assertRaisesRegex(h.Invalid, code):
                    q.prepare(**(pins | {"custody_raw": proof_raw, "custody_pin": h.digest(proof_raw),
                                         "acl_raw": acl_raw, "acl_pin": h.digest(acl_raw)}))


if __name__ == "__main__":
    unittest.main()
