"""Invented public fixtures. No private record is needed for any test."""
import builtins
import copy
from hashlib import sha256
import io
import socket
import unittest
from unittest.mock import patch

from scripts import offline_heldout67 as h
from scripts.offline_revocation67 import Gate, Stopped


def dummy():
    ref = ["NHD", "SYN-PRISM", 1, "p1"]
    fact = {"id": "total", "kind": "decimal", "unit": "VND", "value": "37.50"}
    return {
        "case": {"id": "dummy-price-01", "category": "price", "tenant": "NHD",
                 "question": "Three fictional prisms at twelve and a half units each.",
                 "family": "mock-prism-quote"},
        "oracle": {"approved": True, "behavior": "answer", "facts": [fact],
                   "required": [["total", ref]], "forbidden": [],
                   "reads": [ref], "writes": [], "effects": [], "revocations": [],
                   "totals": [{"id": "total", "quantity": "3", "price": "12.50"}]},
        "sources": [{"ref": ref, "from": 1, "until": 20, "approved": True, "epoch": 1,
                     "facts": [{**fact, "value": "12.50"}]}],
    }


def observed(bundle=None, **updates):
    b = bundle or dummy()
    return dict({"case": b["case"]["id"], "category": b["case"]["category"], "repetition": 1,
                 "status": "complete", "behavior": "answer", "tick": 4, "facts": b["oracle"]["facts"],
                 "links": b["oracle"]["required"],
                 "reads": [{"ref": b["sources"][0]["ref"], "tick": 2, "epoch": 1}],
                 "writes": [], "effects": [], "epoch": 1, "authority": "valid", "consent": False,
                 "revocations": [], "denied_deliveries": []}, **updates)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.b = dummy()
        self.m = h.freeze("dummy", [self.b])
        self.pin = sha256(self.m).hexdigest()

    def score(self, obs=None, bundle=None, manifest=None, pin=None, index=0):
        return h.evaluate(manifest if manifest is not None else self.m,
                          pin if pin is not None else self.pin, index,
                          h.canonical(self.b if bundle is None else bundle),
                          None if obs is None else h.canonical(obs))

    def test_canonical_refuses_duplicate_keys_noncanonical_and_floats(self):
        for raw in (b'{"a":1,"a":2}\n', b'{"a":1.2}\n', b'{"a":1}', b'{"a":NaN}\n'):
            with self.subTest(raw=raw), self.assertRaises(h.Invalid):
                h.parse(raw)
        self.assertEqual(h.canonical({"z": 3, "a": 1}), b'{"a":1,"z":3}\n')

    def test_exact_mock_decimal_and_link_pass_without_io(self):
        obs = h.canonical(observed())
        case = h.canonical(self.b)
        with patch.object(socket, "socket", side_effect=AssertionError), \
             patch.object(builtins, "open", side_effect=AssertionError), \
             patch.object(io, "open", side_effect=AssertionError):
            r = h.evaluate(self.m, self.pin, 0, case, obs)
        self.assertEqual(r.outcome, "PASS")
        self.assertNotIn("37.50", repr(r))
        self.assertNotIn("SYN-PRISM", repr(r))

    def test_missing_observation_and_incomplete_trace_are_distinct(self):
        self.assertEqual(self.score().outcome, "NOT_RUN")
        obs = observed(status="incomplete", behavior=None, facts=[], links=[], reads=[])
        self.assertEqual(self.score(obs).outcome, "INCONCLUSIVE")

    def test_quality_vs_stop_and_known_breach_in_partial_trace(self):
        self.assertEqual(self.score(observed(behavior="clarify", facts=[], links=[])).outcome, "FAIL")
        for obs in (
            observed(status="incomplete", writes=["order"]),
            observed(effects=["handoff"], consent=False),
            observed(reads=[{"ref": ["HANU", "SYN-PRISM", 1, "p1"], "tick": 2, "epoch": 1}]),
            observed(links=[["total", ["NHD", "SYN-PRISM", 2, "p1"]]]),
            observed(tick=20),
            observed(epoch=0),
            observed(facts=[{"id": "total", "kind": "decimal", "unit": "VND", "value": "37.51"}]),
        ):
            with self.subTest(obs=obs):
                self.assertEqual(self.score(obs).outcome, "STOP")

    def test_oracle_and_observation_schema_are_closed(self):
        for label in ("missing", "unapproved", "malformed", "extra", "invalid-total", "unsupported"):
            b = copy.deepcopy(self.b)
            if label == "missing":
                del b["oracle"]["facts"]
            elif label == "unapproved":
                b["oracle"]["approved"] = False
            elif label == "malformed":
                b["oracle"]["required"][0][1][2] = True
            elif label == "extra":
                b["oracle"]["tool"] = "do-stuff"
            elif label == "invalid-total":
                b["oracle"]["totals"][0]["quantity"] = "4"
            else:
                b["oracle"]["totals"] = []
            with self.subTest(label=label), self.assertRaises(h.Invalid):
                h.freeze("dummy", [b])
        self.assertEqual(self.score(observed(oracle=self.b["oracle"])).outcome, "STOP")

    def test_tamper_does_not_pass_with_recomputed_untrusted_manifest(self):
        b = copy.deepcopy(self.b)
        b["case"]["question"] += " Changed."
        self.assertEqual(self.score(observed(), bundle=b).outcome, "STOP")
        self.assertEqual(self.score(observed(), bundle=b, manifest=h.freeze("dummy", [b])).outcome, "STOP")
        for field, value in (("case", "dummy-price-02"), ("category", "scope"), ("repetition", 2)):
            self.assertEqual(self.score(observed(**{field: value})).outcome, "STOP")
        self.assertEqual(self.score(observed(repetition=2), index=1).outcome, "PASS")

    def test_conflicting_active_authorities_and_partial_missing_keys(self):
        b = copy.deepcopy(self.b)
        other = copy.deepcopy(b["sources"][0])
        other["ref"][2] = 2
        b["sources"].append(other)
        with self.assertRaises(h.Invalid):
            h.freeze("dummy", [b])

    def test_exact_ids_and_family_or_normalized_question_collisions(self):
        other = copy.deepcopy(self.b)
        other["case"]["id"] = "dummy-price-02"
        with self.assertRaises(h.Invalid):
            h.freeze("dummy", [self.b, other])
        other["case"]["family"] = "mock-prism-other"
        other["case"]["question"] = "THREE fictional prisms, at twelve and a half units each!"
        with self.assertRaises(h.Invalid):
            h.freeze("dummy", [self.b, other])
        other["case"]["question"] = "Different invented test input."
        with self.assertRaises(h.Invalid):
            h.freeze("dummy", [other, self.b])
        with self.assertRaises(h.Invalid):
            h.freeze("heldout", [self.b])

    def test_receipt_idempotence_no_best_of_and_stop_blocks_run(self):
        run = h.Run(self.m, self.pin)
        bundle = h.canonical(self.b)
        obs = h.canonical(observed())
        with self.assertRaises(h.Invalid):
            run.submit(1, bundle, obs)
        first = run.submit(0, bundle, obs)
        self.assertEqual(run.submit(0, bundle, obs), first)
        with self.assertRaises(h.Invalid):
            run.submit(0, bundle, h.canonical(observed(behavior="clarify", facts=[], links=[])))
        self.assertEqual(run.submit(1, bundle, h.canonical(observed(repetition=2))).outcome, "PASS")
        self.assertEqual(len(run.receipts), 2)
        with self.assertRaises(h.Invalid):
            run.submit(2, bundle, obs)
        stopped = h.Run(self.m, self.pin)
        self.assertEqual(stopped.submit(0, b"", obs).outcome, "STOP")
        self.assertEqual(len(stopped.receipts), 1)
        with self.assertRaises(h.Invalid):
            stopped.submit(1, bundle, h.canonical(observed(repetition=2)))


class RevocationTests(unittest.TestCase):
    ref = ("NHD", "SYN-PRISM", 1, "p1")

    def gate(self):
        return Gate("NHD", self.ref, 1, 20)

    def test_sources_06_revoked_during_generation(self):
        g = self.gate()
        ticket = g.begin(self.ref, 2)
        g.revoke(self.ref, 1, 3)
        self.assertIsNone(g.deliver(ticket, 4))
        self.assertEqual(g.outputs, ())
        self.assertEqual(g.events, ((1, 3),))

    def test_dummy_revocation_is_required_evidence_for_a_pass(self):
        g = self.gate()
        b = dummy()
        b["case"].update(id="dummy-sources-01", category="sources",
                         question="Public dummy failed-authority drill.")
        b["oracle"].update(behavior="abstain", facts=[], required=[], totals=[],
                           revocations=[{"ref": list(self.ref), "tick": 3}])
        manifest = h.freeze("dummy", [b])
        first = g.begin(self.ref, 2)
        g.revoke(self.ref, 1, 3)
        self.assertIsNone(g.deliver(first, 4))
        obs = observed(b, behavior="abstain", authority="revoked", epoch=None,
                       reads=[{"ref": list(ref), "tick": tick, "epoch": epoch}
                              for ref, tick, epoch in g.reads],
                       revocations=[{"ref": list(self.ref), "tick": tick} for _, tick in g.events],
                       denied_deliveries=[{"ref": list(ref), "read": read, "revoked": revoked,
                                           "tick": tick, "reason": reason}
                                          for ref, read, revoked, tick, reason in g.denials])
        def score(evidence):
            return h.evaluate(manifest, sha256(manifest).hexdigest(), 0,
                              h.canonical(b), h.canonical(evidence)).outcome
        self.assertEqual(score(obs), "PASS")
        self.assertEqual(score(dict(obs, revocations=[])), "STOP")
        self.assertEqual(score(dict(obs, denied_deliveries=[])), "STOP")
        self.assertEqual(score(dict(obs, tick=3)), "STOP")
        self.assertEqual(score(dict(obs, reads=[{"ref": list(self.ref), "tick": 3, "epoch": 1}])), "STOP")
        self.assertEqual(score(dict(obs, reads=[{"ref": list(self.ref), "tick": 2, "epoch": 2}])), "STOP")

    def test_denial_before_retrieval_and_foreign_ref_has_no_read(self):
        g = self.gate()
        self.assertIsNone(g.begin(("ZENA",) + self.ref[1:], 2))
        g.revoke(self.ref, 1, 3)
        self.assertIsNone(g.begin(self.ref, 4))
        self.assertEqual(g.reads, ())

    def test_attempted_render_has_no_authority_until_delivery(self):
        g = self.gate()
        ticket = g.begin(self.ref, 2)
        candidate = g.prepare(ticket, 3)
        g.revoke(self.ref, 1, 4)
        self.assertIsNone(g.deliver(candidate, 5))
        self.assertEqual(g.outputs, ())

    def test_duplicate_and_out_of_order_events_are_fail_closed(self):
        g = self.gate()
        self.assertTrue(g.revoke(self.ref, 1, 4))
        self.assertFalse(g.revoke(self.ref, 1, 4))
        with self.assertRaises(Stopped):
            g.revoke(self.ref, 1, 5)
        self.assertIsNone(g.begin(self.ref, 5))

    def test_restart_replays_tombstone_and_detects_rollback(self):
        g = self.gate()
        ticket = g.begin(self.ref, 2)
        before, _ = g.checkpoint()
        g.revoke(self.ref, 1, 3)
        data, pin = g.checkpoint()
        new = Gate.restore(data, pin)
        self.assertIsNone(new.begin(self.ref, 4))
        self.assertIsNone(new.deliver(ticket, 4))
        with self.assertRaises(Stopped):
            Gate.restore(before, pin)

    def test_fresh_success_is_single_use_and_invalid_epoch_discards(self):
        g = self.gate()
        good = g.begin(self.ref, 2)
        self.assertEqual(g.deliver(good, 3), self.ref)
        self.assertIsNone(g.deliver(good, 4))
        cached = g.begin(self.ref, 5)
        g.invalidate()
        self.assertIsNone(g.deliver(cached, 6))
        self.assertEqual(g.outputs, (self.ref,))
