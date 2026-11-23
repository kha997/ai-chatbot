import copy
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest

from scripts import offline_corpus63 as c
from scripts import offline_heldout67 as h
from scripts import offline_evidence69 as e
from scripts.offline_journal69 import Journal
from test_offline_heldout67 import dummy, observed

ROOT = Path(__file__).resolve().parents[1]
DEV = (ROOT / "eval/offline63/development.json").read_bytes()
CUSTODY_SCHEMA = (ROOT / "eval/offline63/custody.schema.json").read_bytes()


def fixture(bundle=None):
    bundle = dummy() if bundle is None else bundle
    source = {"schema": e.BRIDGE, "synthetic": True, "scope": "PUBLIC_DUMMY",
              "provenance": {"author": "mock-author", "reviewer": "mock-reviewer",
                             "rights": "invented-no-third-party-text",
                             "revision": 1, "from": 1, "until": 20},
              "sources": [{"ref": src["ref"], "state": "active",
                           "authority": "approved"} for src in bundle["sources"]],
              "safeguards": {"required_reads": [], "forbidden_fact_ids": []},
              "bundle": bundle}
    raw = c.canonical(source)
    out = h.canonical(bundle)
    bridge = {"input": e.pin(raw), "output": e.pin(out), "source_revision": 1}
    return source, raw, out, bridge


def package(bundle=None, required_reads=()):
    src, _, out, _ = fixture(bundle)
    src["safeguards"]["required_reads"] = list(required_reads)
    raw = c.canonical(src)
    descriptor = {"input": e.pin(raw), "output": e.pin(out), "source_revision": 1}
    manifest = h.freeze("dummy", [src["bundle"]])
    setup = h.canonical({"schema": "offline69-settings-v1", "candidate": "dummy-renderer",
                         "config": {"transport": "NONE", "model": "NOT_RUN", "max_calls": 0},
                         "prompt": None, "initial_state": {"epoch": 1, "tenant": "NHD"}})
    case = src["bundle"]["case"]
    packet = {"schema": e.ENVELOPE, "scope": "PUBLIC_DUMMY", "run_id": "SYN-69-A",
              "baseline": e.BASELINE, "tenant": "NHD", "clock": 2,
              "roles": {"author": "mock-author", "reviewer": "mock-reviewer",
                        "custodian": "mock-custodian", "implementer": "mock-engineer"},
              "approval": {"state": "MOCK_ONLY", "from": 1, "until": 20,
                           "receipt": "NOT_VERIFIED"},
              "pins": {"manifest": e.pin(manifest), "development": e.pin(DEV),
                       "custody_schema": e.pin(CUSTODY_SCHEMA), "settings": e.pin(setup),
                       "candidate_fixture": e.pin(h.canonical("dummy-renderer")),
                       "config_fixture": e.pin(h.canonical(h.parse(setup)["config"]))},
              "source_policy": {"rights": "invented-no-third-party-text",
                                "egress": "DENIED", "requests": 0, "spend": 0},
              "attestations": dict.fromkeys(e.EXTERNAL, "NOT_VERIFIED"),
              "outcomes": dict.fromkeys(e.NOT_RUN, "NOT_RUN"),
              "retention": {"acl": "NOT_VERIFIED", "days": None, "access_log": "NOT_VERIFIED"},
              "repetition_seeds": [123, 456],
              "cases": [{"id": case["id"], "category": case["category"], "bridge": descriptor,
                         "seeds": [123,456], "pre_state": e.pin(h.canonical({"epoch":1,"tenant":"NHD"})),
                         "post_state": e.pin(h.canonical({"epoch":1,"tenant":"NHD"}))}]}
    return packet, manifest, setup, raw, out


def approval(pkg):
    packet, manifest, setup, raw, _ = pkg
    sealed = h.canonical(packet)
    return e.verify(sealed, e.pin(sealed), manifest, DEV, CUSTODY_SCHEMA, setup, [raw])


def commit_then_exit(path, app, bundle, obs):
    journal = Journal.open(path, app, app.genesis)
    journal.submit(0, bundle, obs, 2, app.genesis)
    os._exit(17)  # The external anchor store has not been updated.


class EvidenceTests(unittest.TestCase):
    def test_bridge_requires_both_byte_pins_and_exact_representation(self):
        src, raw, out, pins = fixture()
        self.assertNotEqual(pins["input"], pins["output"])
        self.assertEqual(e.bridge(raw, pins, 2).compact, out)
        self.assertEqual(e.bridge(raw, pins, 2).compact, e.bridge(raw, pins, 2).compact)
        for invalid in (h.canonical(src), raw.replace(b"\n",b"\r\n"), raw+b"\n"):
            with self.subTest(invalid=invalid[:30]), self.assertRaises(h.Invalid):
                e.bridge(invalid, pins | {"input": e.pin(invalid)}, 2)
        with self.assertRaises(h.Invalid):
            e.bridge(raw, pins | {"output":pins["input"]}, 2)
        with self.assertRaises(h.Invalid):
            e.bridge(raw, pins, 20)
        duplicate = raw.replace(b'"synthetic": true', b'"synthetic": true, "synthetic": true')
        with self.assertRaises(h.Invalid):
            e.bridge(duplicate, pins | {"input": e.pin(duplicate)}, 2)
        unicode_bundle = dummy()
        unicode_bundle["case"]["question"] = "Mẫu giả để chấm riêng."
        _, raw, out, pins = fixture(unicode_bundle)
        self.assertEqual(e.bridge(raw, pins, 2).compact, out)

    def test_bridge_rejects_lossy_types_unicode_and_false_provenance(self):
        for variant in ("nfd", "float", "retired", "wrong-role", "unexpected", "reordered"):
            src, _, out, pins = fixture()
            if variant == "nfd":
                src["bundle"]["case"]["question"] = "e\u0301"
            elif variant == "float":
                src["bundle"]["sources"][0]["epoch"] = 1.0
            elif variant == "retired":
                src["sources"][0]["state"] = "retired"
            elif variant == "wrong-role":
                src["provenance"]["reviewer"] = src["provenance"]["author"]
            elif variant == "unexpected":
                src["bundle"]["source_note"] = "not mapped"
            else:
                src["sources"][0]["ref"] = ["NHD", "SYN-OTHER", 1, "p1"]
            raw = c.canonical(src)
            with self.subTest(variant=variant), self.assertRaises(h.Invalid):
                e.bridge(raw, pins | {"input": e.pin(raw)}, 2)

    def test_real_public_dev_bytes_overlap_and_mutation(self):
        item = c.parse(DEV)["cases"][0]
        corpus = e.development(DEV, e.pin(DEV))
        for key in ("family", "question"):
            b = dummy()
            b["case"][key] = item[key].upper() + "!" if key == "question" else item[key]
            with self.subTest(key=key), self.assertRaises(h.Invalid):
                corpus.assert_distinct(b["case"])
        altered = DEV.replace(b"historic-box-total", b"historic-box-fake!")
        with self.assertRaises(h.Invalid):
            e.development(altered, e.pin(altered))

    def test_complete_closed_envelope_and_external_pin(self):
        pkg = package()
        self.assertEqual(approval(pkg).run_id, "SYN-69-A")
        for field in pkg[0]:
            damaged = copy.deepcopy(pkg[0])
            del damaged[field]
            with self.subTest(field=field), self.assertRaises(h.Invalid):
                approval((damaged, *pkg[1:]))
        packet, manifest, setup, raw, _ = pkg
        with self.assertRaises(h.Invalid):
            e.verify(h.canonical(packet), e.pin(b"false"), manifest, DEV, CUSTODY_SCHEMA, setup, [raw])

    def test_envelope_refuses_changed_authority_archive_settings_and_attestations(self):
        for variant in ("roles", "source-pin", "authority", "settings", "candidate-pin", "attestation",
                        "outcome", "case-state", "seeds", "approval"):
            packet, manifest, setup, raw, out = package()
            if variant == "roles":
                packet["roles"]["reviewer"] = packet["roles"]["author"]
            elif variant == "source-pin":
                packet["cases"][0]["bridge"]["input"] = e.pin(b"other")
            elif variant == "authority":
                packet["source_policy"]["egress"] = "ALLOWED"
            elif variant == "settings":
                setup += b" "
            elif variant == "candidate-pin":
                packet["pins"]["candidate_fixture"] = e.pin(b"wrong-candidate")
            elif variant == "attestation":
                packet["attestations"]["provider_account"] = "VERIFIED"
            elif variant == "outcome":
                packet["outcomes"]["model"] = "PASS"
            elif variant == "case-state":
                packet["cases"][0]["pre_state"] = e.pin(b"wrong")
            elif variant == "seeds":
                packet["cases"][0]["seeds"][1] = 789
            else:
                packet["approval"]["state"] = "APPROVED-LIVE"
            with self.subTest(variant=variant), self.assertRaises(h.Invalid):
                approval((packet, manifest, setup, raw, out))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "local.sqlite"
        self.pkg = package()
        self.app = approval(self.pkg)
        self.journal = Journal.create(self.path, self.app)
        self.anchor = self.app.genesis

    def submit(self, obs, **changes):
        return self.journal.submit(changes.get("index",0), changes.get("bundle",self.pkg[-1]),
                                   None if obs is None else h.canonical(obs),
                                   changes.get("tick",2), changes.get("anchor",self.anchor))

    def test_reopen_and_replay_checks_both_inputs(self):
        first = self.submit(observed())
        self.assertEqual(first.outcome, "PASS")
        self.assertEqual(first.case, "dummy-price-01")
        self.assertEqual(first.repetition, 1)
        self.assertEqual(first.sequence, 1)
        self.journal = Journal.open(self.path, self.app, first.anchor)
        self.assertEqual(self.submit(observed(), anchor=first.anchor), first)
        for change in ({"bundle":b"invalid"}, {"tick":3}):
            with self.assertRaises(h.Invalid):
                self.submit(observed(), anchor=first.anchor, **change)

    def test_crash_after_commit_requires_current_separately_pinned_anchor(self):
        worker = multiprocessing.get_context("spawn").Process(
            target=commit_then_exit,
            args=(self.path, self.app, self.pkg[-1], h.canonical(observed())),
        )
        worker.start()
        worker.join(15)
        if worker.is_alive():
            worker.terminate()
            worker.join(5)
        self.assertEqual(worker.exitcode, 17)
        with self.assertRaises(h.Invalid):
            Journal.open(self.path, self.app, self.anchor)

    def test_empty_journal_is_bound_to_a_single_approved_run(self):
        pkg = package()
        pkg[0]["run_id"] = "SYN-69-B"
        other = approval(pkg)
        with self.assertRaises(h.Invalid):
            Journal.open(self.path, other, other.genesis)

    def test_competing_appends_need_a_fresh_external_anchor(self):
        barrier = Barrier(2)
        def contender():
            barrier.wait(timeout=5)
            try:
                return self.submit(observed()).outcome
            except h.Invalid as err:
                return str(err)
        with ThreadPoolExecutor(max_workers=2) as workers:
            got = list(workers.map(lambda _: contender(), range(2)))
        self.assertCountEqual(got, ["PASS", "anchor-mismatch"])

    def test_stop_latches_across_reopen(self):
        first = self.submit(observed(writes=["order"]))
        self.assertEqual(first.outcome, "STOP")
        self.journal = Journal.open(self.path, self.app, first.anchor)
        with self.assertRaises(h.Invalid):
            self.submit(observed(repetition=2), index=1, anchor=first.anchor)

    def test_five_outcomes_and_required_reads(self):
        for i, (obs, expected) in enumerate((
            (None, "NOT_RUN"),
            (observed(), "PASS"),
            (observed(behavior="clarify", facts=[], links=[]), "FAIL"),
            (observed(status="incomplete", behavior=None, facts=[], links=[]), "INCONCLUSIVE"),
            (observed(links=[], authority="unavailable"), "STOP"),
        )):
            j = Journal.create(Path(self.tmp.name)/f"other{i}.sqlite", self.app)
            receipt = j.submit(0, self.pkg[-1], None if obs is None else h.canonical(obs),
                               2, self.app.genesis)
            self.assertEqual(receipt.outcome, expected)
        pkg = package(required_reads=[dummy()["sources"][0]["ref"]])
        app = approval(pkg)
        j = Journal.create(Path(self.tmp.name)/"required.sqlite", app)
        obs = observed(behavior="clarify", facts=[], links=[], reads=[])
        self.assertEqual(j.submit(0, pkg[-1], h.canonical(obs), 2, app.genesis).outcome, "STOP")

    def test_untrusted_ledger_tamper_and_rollback(self):
        import sqlite3
        from contextlib import closing
        first = self.submit(observed())
        rewound = Path(self.tmp.name)/"rewound.sqlite"
        Journal.create(rewound, self.app)
        with self.assertRaises(h.Invalid):
            Journal.open(rewound, self.app, first.anchor)
        with closing(sqlite3.connect(self.path)) as db, db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE receipt SET payload=? WHERE seq=1",(b"fake",))
            db.execute("DROP TRIGGER receipt_no_update")
            db.execute("UPDATE receipt SET payload=? WHERE seq=1",(b"fake",))
        with self.assertRaises(h.Invalid):
            Journal.open(self.path, self.app, first.anchor)

    def test_locally_rehashed_receipt_cannot_replace_external_anchor(self):
        import sqlite3
        from contextlib import closing
        first = self.submit(observed())
        with closing(sqlite3.connect(self.path)) as db, db:
            original = db.execute("SELECT payload FROM receipt").fetchone()[0]
            altered = h.canonical(h.parse(original) | {"outcome": "FAIL"})
            sql = db.execute("SELECT sql FROM sqlite_master WHERE name='receipt_no_update'").fetchone()[0]
            db.execute("DROP TRIGGER receipt_no_update")
            db.execute("UPDATE receipt SET payload=?, anchor=?", (altered, h.digest(altered)))
            db.execute(sql)
        with self.assertRaisesRegex(h.Invalid, "anchor-mismatch"):
            Journal.open(self.path, self.app, first.anchor)

    def test_forbidden_typed_claim_and_ungraded_plain_text_cannot_enter_trace(self):
        source, _, out, _ = fixture()
        source["safeguards"]["forbidden_fact_ids"] = ["fake-stock"]
        packet, manifest, setup, _, _ = package()
        raw = c.canonical(source)
        packet["cases"][0]["bridge"]["input"] = e.pin(raw)
        app = approval((packet, manifest, setup, raw, out))
        invented = {"id": "fake-stock", "kind": "integer", "unit": "each", "value": 5}
        observations = [
            observed(facts=[invented], links=[]),
            observed(answer_text="Unverified free text is outside the closed trace."),
        ]
        for i, obs in enumerate(observations):
            j = Journal.create(Path(self.tmp.name)/f"forbidden{i}.sqlite", app)
            decision = j.submit(0, out, h.canonical(obs), 2, app.genesis)
            self.assertEqual(decision.outcome, "STOP")
            self.assertNotIn("fake-stock", repr(decision))

    def test_expired_mock_approval_stops_and_cannot_be_refreshed_by_open(self):
        first = self.submit(observed(), tick=self.app.until_tick)
        self.assertEqual((first.outcome, first.code), ("STOP", "expired-mock-approval"))
        self.journal = Journal.open(self.path, self.app, first.anchor)
        with self.assertRaises(h.Invalid):
            self.submit(None, index=1, anchor=first.anchor, tick=self.app.until_tick+1)


if __name__ == "__main__":
    unittest.main()
