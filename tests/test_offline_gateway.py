"""Adversarial tests for the Issue #64 local fake gateway."""
import hashlib
import json
import multiprocessing
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from scripts.offline_gateway import Approval, FakeTransport, Gateway, Permit, Rejected, SimulatedCrash


SNAPSHOT = "gpt-5.4-mini-2026-03-17"
BUCKETS = {"qa": 120, "dev": 12, "adversarial": 24, "journeys": 12, "performance": 100}
PAYLOAD = b'{"source":{"id":"SYN-GW-NHD-01","version":1},"text":"SYNTHETIC GATEWAY REFERENCE"}'
HASH = hashlib.sha256(PAYLOAD).hexdigest()


def manifest(**changes):
    record = {
        "schema": 1, "run": "SYN-GW-RUN-01", "synthetic": True, "tenant": "NHD",
        "source": {"id": "SYN-GW-NHD-01", "version": 1, "approved": True,
                   "reviewed": True, "synthetic": True, "active_from": 1, "active_until": 2000},
        "oracle_reviewed": True, "prompt": "a" * 64, "config": "b" * 64,
        "permits": [{"suite": suite, "execution": index, "stage": stage,
                     "fields": ["source", "text"], "digest": HASH, "allow_send": True}
                    for suite, count in BUCKETS.items() for index in range(1, count + 1)
                    for stage in (1, 2)],
        "diagnostics": list(range(1, 65)),
        "rate": {"date": "2026-11-23", "model": SNAPSHOT, "tier": "standard",
                 "input_micro_per_m": 750000, "output_micro_per_m": 4500000,
                 "regional_bps": 0, "tax_bps": 0, "per_attempt_micro": 0,
                 "fixed_micro": 0, "rounding_micro": 1},
    }
    record.update(changes)
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


def approval(raw, *, serial="approval-1", expiry=1000):
    return Approval(hashlib.sha256(raw).hexdigest(), serial, expiry)


def restart_worker(path, raw, approved, worker_token, session, destination):
    gateway = Gateway.join(path, raw, approved, worker_token, FakeTransport(), clock=lambda: 10)
    try:
        permit = gateway.reserve(session, "performance", 1, 1, PAYLOAD)
    except Rejected as error:
        destination.put(error.code)
    else:
        destination.put(permit.attempt)


def crash_worker(path, raw, approved, worker_token, session, phase):
    import os
    gateway = Gateway.join(path, raw, approved, worker_token, FakeTransport(), clock=lambda: 10)
    try:
        if phase == "before-reserve":
            gateway.reserve(session, "qa", 1, 1, PAYLOAD, fault=phase)
        if phase == "after-reserve":
            gateway.reserve(session, "qa", 1, 1, PAYLOAD, fault=phase)
        permit = gateway.reserve(session, "qa", 1, 1, PAYLOAD)
        gateway.dispatch(permit, PAYLOAD, fault=phase)
    except SimulatedCrash:
        os._exit(17)
    os._exit(18)


class OfflineGatewayTests(unittest.TestCase):
    def build(self, raw=None, scenario="ok", *, approved=None):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.sqlite"
        self.raw = manifest() if raw is None else raw
        self.approved = approved or approval(self.raw)
        self.tick = 10
        self.transport = FakeTransport(scenario)
        self.gateway = Gateway.create(
            self.path, self.raw, self.approved, self.transport, clock=lambda: self.tick)
        self.session = self.gateway.session
        return self.gateway

    def denial(self, code, operation, *args, **kwargs):
        with self.assertRaises(Rejected) as problem:
            operation(*args, **kwargs)
        self.assertEqual(problem.exception.code, code)

    def push(self, suite="qa", execution=1, stage=1, **kwargs):
        permit = self.gateway.reserve(self.session, suite, execution, stage, PAYLOAD, **kwargs)
        result = self.gateway.dispatch(permit, PAYLOAD)
        return permit, result

    def test_exact_payload_and_single_use_permit(self):
        self.build()
        permit, result = self.push()
        self.assertEqual(result, "ok")
        self.assertEqual(self.transport.calls, ((permit.attempt, HASH),))
        self.denial("permit", self.gateway.dispatch, permit, PAYLOAD)
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.gateway.snapshot()["attempts"], 1)

    def test_payload_mutation_blocks_send_and_keeps_reservation(self):
        self.build()
        permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
        self.denial("payload", self.gateway.dispatch, permit, PAYLOAD + b" ")
        self.assertEqual(self.transport.calls, ())
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 10500)
        self.assertEqual(self.gateway.snapshot()["status"], "STOPPED")

    def test_closed_schema_denies_forbidden_shape_without_transport_or_new_slots(self):
        malformed = [
            PAYLOAD.replace(b'"version":1', b'"version":1,"tenant":"HANU"'),
            PAYLOAD.replace(b'SYN-GW-NHD-01', b'SYN-GW-HANU-01'),
            PAYLOAD.replace(b'SYN-GW-NHD-01', b'SYN-GW-ZENA-01'),
            PAYLOAD.replace(b'SYN-GW-NHD-01', b'SYN-GW-NHD-02'),
            PAYLOAD.replace(b'"version":1', b'"version":2'),
            PAYLOAD.replace(b'SYNTHETIC GATEWAY REFERENCE', b'demo@example.invalid'),
            PAYLOAD.replace(b'SYNTHETIC GATEWAY REFERENCE', b'https://invalid.example'),
            PAYLOAD[:-1] + b',"attachment":"dummy"}',
            PAYLOAD[:-1] + b',"role":"admin"}',
            PAYLOAD.replace(b'"version":1', b'"version":1,"version":1'),
            PAYLOAD.replace(b'"version":1', b'"version":true'),
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                self.build()
                self.denial("payload", self.gateway.reserve, self.session, "qa", 1, 1,
                            payload)
                self.assertEqual(self.gateway.snapshot()["attempts"], 0)
                self.assertEqual(self.transport.calls, ())

    def test_forged_session_worker_and_transport_are_rejected(self):
        self.build()
        self.denial("session", self.gateway.reserve, "forged", "qa", 1, 1, PAYLOAD)
        self.denial("worker", Gateway.join, self.path, self.raw, self.approved,
                    "forged", FakeTransport(), clock=lambda: 10)
        self.denial("transport", Gateway.join, self.path, self.raw, self.approved,
                    self.gateway.worker, object(), clock=lambda: 10)
        class FakeSubclass(FakeTransport):
            pass
        self.denial("transport", Gateway.join, self.path, self.raw, self.approved,
                    self.gateway.worker, FakeSubclass(), clock=lambda: 10)
        self.assertEqual(self.transport.calls, ())

    def test_explicit_zero_egress_case_never_reserves(self):
        record = json.loads(manifest())
        record["permits"][0]["allow_send"] = False
        self.build(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
        self.denial("zero-egress", self.gateway.reserve, self.session, "qa", 1, 1, PAYLOAD)
        self.assertEqual(self.gateway.snapshot()["attempts"], 0)
        self.assertEqual(self.transport.calls, ())

    def test_unapproved_hash_fees_snapshot_source_and_oracle_stop_before_fake(self):
        clean = json.loads(manifest())
        for scenario in ("hash", "fees", "model", "price", "source", "oracle", "foreign-source"):
            with self.subTest(scenario=scenario):
                record = json.loads(json.dumps(clean))
                if scenario == "fees":
                    del record["rate"]["tax_bps"]
                elif scenario == "model":
                    record["rate"]["model"] = "gpt-5.4-mini"
                elif scenario == "price":
                    record["rate"]["input_micro_per_m"] = None
                elif scenario == "source":
                    record["source"]["approved"] = False
                elif scenario == "oracle":
                    record["oracle_reviewed"] = False
                elif scenario == "foreign-source":
                    record["source"]["id"] = "SYN-GW-HANU-01"
                raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
                self.build(raw, approved=Approval("0" * 64, "approval-1", 1000)
                           if scenario == "hash" else approval(raw))
                self.assertEqual(self.gateway.snapshot()["status"], "STOPPED")
                self.denial("stopped", self.gateway.reserve, self.session, "qa", 1, 1, PAYLOAD)
                self.assertEqual(self.transport.calls, ())

    def test_exact_admission_ceiling_and_protected_reserve(self):
        rate = json.loads(manifest())["rate"]
        for fixed in (7989500, 7989501):
            with self.subTest(fixed=fixed):
                self.build(manifest(rate=rate | {"fixed_micro": fixed}))
                if fixed == 7989500:
                    self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
                    self.assertEqual(self.gateway.snapshot()["committed_micro"], 8000000)
                else:
                    self.denial("money", self.gateway.reserve, self.session, "qa", 1, 1, PAYLOAD)
                    self.assertEqual(self.gateway.snapshot()["attempts"], 0)
                self.assertEqual(self.gateway.snapshot()["protected_micro"], 2000000)

    def test_regional_tax_fee_and_rounding_bound(self):
        rate = json.loads(manifest())["rate"]
        self.build(manifest(rate=rate | {"regional_bps": 1000, "tax_bps": 999,
                                         "per_attempt_micro": 7, "fixed_micro": 99,
                                         "rounding_micro": 10}))
        self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
        # (11,550 + 7) * 1.0999 = 12,711.5443; round upward to multiples of 10.
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 12720)
        self.assertEqual(self.gateway.snapshot()["committed_micro"], 12819)

    def test_retries_charge_shared_contingency_and_keep_failed_origin(self):
        self.build(scenario="503")
        first, result = self.push("performance")
        self.assertEqual(result, "transient")
        permit = self.gateway.reserve(self.session, "performance", 1, 1, PAYLOAD,
                                      kind="retry", parent=first.attempt)
        self.assertEqual(self.gateway.dispatch(permit, PAYLOAD), "transient")
        self.denial("duplicate", self.gateway.reserve, self.session, "performance", 1, 1,
                    PAYLOAD, kind="retry", parent=first.attempt)
        result = self.gateway.snapshot()
        self.assertEqual(result["by_bucket"]["performance"], 1)
        self.assertEqual(result["by_bucket"]["contingency"], 1)
        self.assertEqual(result["by_origin"]["performance"], {"sent": 2, "failed": 2})
        self.assertEqual(result["attempts"], 2)

    def test_bucket_boundaries_and_no_transfer(self):
        self.build()
        for case in range(1, 13):
            for stage in (1, 2):
                self.push("dev", case, stage)
        self.denial("case", self.gateway.reserve, self.session, "dev", 13, 1, PAYLOAD)
        self.denial("case", self.gateway.reserve, self.session, "dev", 12, 3, PAYLOAD)
        self.assertEqual(self.gateway.snapshot()["by_bucket"]["dev"], 24)
        self.assertEqual(self.gateway.snapshot()["by_bucket"]["qa"], 0)

    def test_599_600_and_601_and_contingency_63_64_65(self):
        self.build(scenario="503")
        for suite, count in BUCKETS.items():
            for case in range(1, count + 1):
                for stage in (1, 2):
                    self.push(suite, case, stage)
        for diagnostic in range(1, 64):
            self.push("qa", diagnostic, 0, kind="diagnostic", parent=(diagnostic-1)*2+1)
        self.assertEqual(self.gateway.snapshot()["attempts"], 599)
        self.assertEqual(self.gateway.snapshot()["by_bucket"]["contingency"], 63)
        self.push("qa", 64, 0, kind="diagnostic", parent=127)
        self.assertEqual(self.gateway.snapshot()["attempts"], 600)
        self.assertEqual(self.gateway.snapshot()["by_bucket"]["contingency"], 64)
        self.denial("capacity", self.gateway.reserve, self.session, "qa", 65, 0, PAYLOAD,
                    kind="diagnostic", parent=129)
        # A valid, previously unspent retry must reach persisted quota enforcement.
        self.denial("capacity", self.gateway.reserve, self.session, "qa", 1, 1, PAYLOAD,
                    kind="retry", parent=1)
        self.assertEqual(self.gateway.snapshot()["reason"], "capacity")
        self.assertEqual(len(self.transport.calls), 600)

    def test_six_concurrent_workers_respect_five_in_flight_and_stop_all(self):
        self.build()
        barrier = threading.Barrier(6)
        def contender(n):
            worker = Gateway.join(self.path, self.raw, self.approved, self.gateway.worker,
                                  FakeTransport(), clock=lambda: 10)
            barrier.wait(timeout=5)
            try:
                return worker.reserve(self.session, "performance", n, 1, PAYLOAD)
            except Rejected as error:
                return error.code
        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(contender, range(1, 7)))
        permits = [x for x in outcomes if x != "in-flight"]
        self.assertEqual(len(permits), 5)
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 52500)
        self.gateway.stop()
        for permit in permits:
            self.denial("stopped", self.gateway.dispatch, permit, PAYLOAD)
        self.assertEqual(self.transport.calls, ())
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 52500)

    def test_final_cost_slot_shared_by_six_connections(self):
        rate = json.loads(manifest())["rate"]
        self.build(manifest(rate=rate | {"fixed_micro": 7989500}))
        barrier = threading.Barrier(6)
        def contender(n):
            barrier.wait(timeout=5)
            try:
                return self.gateway.reserve(self.session, "performance", n, 1, PAYLOAD)
            except Rejected as error:
                return error.code
        with ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(contender, range(1, 7)))
        self.assertEqual(sum(not isinstance(x, str) for x in outcomes), 1)
        self.assertIn("money", outcomes)
        self.assertEqual(self.gateway.snapshot()["attempts"], 1)
        self.assertEqual(self.gateway.snapshot()["committed_micro"], 8000000)

    def test_independent_processes_cannot_reserve_same_attempt(self):
        self.build()
        context = multiprocessing.get_context("spawn")
        answers = context.Queue()
        processes = [context.Process(target=restart_worker,
                    args=(self.path, self.raw, self.approved, self.gateway.worker, self.session,
                          answers)) for _ in range(2)]
        for p in processes:
            p.start()
        try:
            values = [answers.get(timeout=15) for _ in processes]
            self.assertCountEqual(values, [1, "duplicate"])
        finally:
            for p in processes:
                p.join(5)
                if p.is_alive():
                    p.terminate()
                    p.join(5)
            answers.close()
        self.assertEqual([p.exitcode for p in processes], [0, 0])
        self.assertEqual(self.gateway.snapshot()["attempts"], 1)

    def test_unknown_usage_and_invalid_output_causes_durable_stop(self):
        for scenario in ("missing", "forged", "out-of-order", "model", "tier", "rate",
                         "fixed", "over-token", "timeout", "partial", "ambiguous", "cancel",
                         "price-action", "tool", "foreign-output", "stale-output",
                         "typed-citation", "foreign-manifest", "nonce"):
            with self.subTest(scenario=scenario):
                self.build(scenario=scenario)
                permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
                self.denial("receipt", self.gateway.dispatch, permit, PAYLOAD)
                self.assertEqual(len(self.transport.calls), 1)
                self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 10500)
                self.denial("stopped", self.gateway.reserve, self.session, "qa", 2, 1, PAYLOAD)

    def test_hard_provider_like_errors_stop_transient_only_reconciled(self):
        for scenario in ("400", "401", "403", "429-cap", "429-rate", "500", "503"):
            with self.subTest(scenario=scenario):
                self.build(scenario=scenario)
                permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
                if scenario in {"429-rate", "500", "503"}:
                    self.assertEqual(self.gateway.dispatch(permit, PAYLOAD), "transient")
                    self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 0)
                else:
                    self.denial("hard-response", self.gateway.dispatch, permit, PAYLOAD)
                    self.denial("stopped", self.gateway.reserve, self.session, "qa", 2, 1,
                                PAYLOAD)
                self.assertEqual(len(self.transport.calls), 1)

    def test_restart_stops_then_requires_separate_clean_resume(self):
        self.build()
        self.push()
        old_worker = self.gateway.worker
        restarted = Gateway.restart(self.path, self.raw, self.approved, FakeTransport(),
                                    clock=lambda: 10)
        self.assertEqual(restarted.snapshot()["status"], "STOPPED")
        self.denial("stopped", self.gateway.reserve, self.session, "qa", 2, 1, PAYLOAD)
        self.denial("approval", restarted.resume, self.approved)
        restarted.resume(approval(self.raw, serial="approval-2"))
        self.denial("worker", Gateway.join, self.path, self.raw, self.approved, old_worker,
                    FakeTransport(), clock=lambda: 10)
        self.assertEqual(restarted.snapshot()["attempts"], 1)
        self.denial("duplicate", restarted.reserve, restarted.session, "qa", 1, 1, PAYLOAD)

    def test_expired_approval_stops_between_reserve_and_send(self):
        self.build()
        permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
        self.tick = 1000
        self.denial("expired", self.gateway.dispatch, permit, PAYLOAD)
        self.assertEqual(self.transport.calls, ())
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 10500)
        self.assertEqual(self.gateway.snapshot()["status"], "STOPPED")

    def test_expired_attempt_lease_blocks_other_workers(self):
        self.build()
        permit = self.gateway.reserve(self.session, "performance", 1, 1, PAYLOAD)
        self.tick += 30
        self.denial("stale", self.gateway.reserve, self.session, "performance", 2, 1, PAYLOAD)
        self.denial("stopped", self.gateway.dispatch, permit, PAYLOAD)
        self.assertEqual(self.transport.calls, ())
        self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 10500)

    def test_survivor_cannot_dispatch_past_abandoned_intent(self):
        for phase in ("after-intent", "after-send", "after-observation"):
            with self.subTest(phase=phase):
                self.build()
                other_fake = FakeTransport()
                worker = Gateway.join(self.path, self.raw, self.approved, self.gateway.worker,
                                      other_fake, clock=lambda: self.tick)
                first = self.gateway.reserve(self.session, "performance", 1, 1, PAYLOAD)
                second = worker.reserve(self.session, "performance", 2, 1, PAYLOAD)
                with self.assertRaises(SimulatedCrash):
                    self.gateway.dispatch(first, PAYLOAD, fault=phase)
                self.denial("dispatch-pending", worker.dispatch, second, PAYLOAD)
                self.denial("dispatch-pending", worker.reserve, self.session, "performance", 3, 1,
                            PAYLOAD)
                self.tick += 30
                self.denial("stale", worker.dispatch, second, PAYLOAD)
                self.assertEqual(self.gateway.snapshot()["outstanding_micro"], 21000)
                self.assertEqual(other_fake.calls, ())
                state = self.gateway.snapshot()
                known = int(phase == "after-observation")
                self.assertEqual(state["by_origin"]["performance"]["sent"], known)
                self.assertEqual(state["ambiguous_intents"], 1-known)

    def test_stop_races_with_five_already_reserved_dispatches(self):
        self.build()
        permits = [self.gateway.reserve(self.session, "performance", n, 1, PAYLOAD)
                   for n in range(1, 6)]
        barrier = threading.Barrier(6)
        def contender(permit):
            barrier.wait(timeout=10)
            try:
                return self.gateway.dispatch(permit, PAYLOAD)
            except Rejected as error:
                return error.code
        def stop():
            barrier.wait(timeout=10)
            self.gateway.stop()
            return self.transport.calls
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = [pool.submit(contender, permit) for permit in permits]
            stop_receipt = pool.submit(stop).result(timeout=15)
            for result in results:
                self.assertIn(result.result(timeout=15), {"ok", "stopped", "dispatch-pending"})
        self.assertEqual(self.transport.calls, stop_receipt)
        self.assertEqual(self.gateway.snapshot()["status"], "STOPPED")

    def test_fake_rejects_callback_values_and_state_replacement(self):
        self.build()
        class Callback:
            def __hash__(self):
                raise AssertionError("callback executed")
            def __eq__(self, other):
                raise AssertionError("callback executed")
        self.denial("transport", FakeTransport, Callback())
        self.denial("transport", FakeTransport, "unknown")
        fake = FakeTransport()
        with self.assertRaises(AttributeError):
            fake._calls = Callback()
        self.denial("session", self.gateway.reserve, Callback(), "qa", 1, 1, PAYLOAD)
        self.denial("fault", self.gateway.reserve, self.session, "qa", 1, 1, PAYLOAD,
                    fault=Callback())
        permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
        self.denial("permit", self.gateway.dispatch, Permit(permit.attempt, Callback()), PAYLOAD)
        self.denial("fault", self.gateway.dispatch, permit, PAYLOAD, fault=Callback())
        self.denial("fault", self.gateway.dispatch, permit, PAYLOAD, fault="unknown")
        self.assertEqual(self.transport.calls, ())

    def test_hard_stop_survives_restart_and_new_approval(self):
        self.build(scenario="401")
        permit = self.gateway.reserve(self.session, "qa", 1, 1, PAYLOAD)
        self.denial("hard-response", self.gateway.dispatch, permit, PAYLOAD)
        restarted = Gateway.restart(self.path, self.raw, self.approved, FakeTransport(),
                                    clock=lambda: 10)
        self.assertEqual(restarted.snapshot()["reason"], "hard-response")
        self.denial("approval", restarted.resume, approval(self.raw, serial="fresh"))

    def test_write_rollback_does_not_grant_permit(self):
        for fault in ("before-write", "after-write"):
            with self.subTest(fault=fault):
                self.build()
                self.denial("storage", self.gateway.reserve, self.session, "qa", 1, 1,
                            PAYLOAD, fault=fault)
                self.assertEqual(self.gateway.snapshot()["attempts"], 0)
                self.assertEqual(self.gateway.snapshot()["status"], "STOPPED")
                self.assertEqual(self.transport.calls, ())

    def test_crash_process_preserves_liability_at_all_boundaries(self):
        ctx = multiprocessing.get_context("spawn")
        for phase in ("before-reserve", "after-reserve", "after-intent",
                      "after-send", "after-observation"):
            with self.subTest(phase=phase):
                self.build()
                p = ctx.Process(target=crash_worker, args=(self.path, self.raw, self.approved,
                                self.gateway.worker, self.session, phase))
                p.start()
                p.join(15)
                if p.is_alive():
                    p.terminate()
                    p.join(5)
                self.assertEqual(p.exitcode, 17)
                restarted = Gateway.restart(self.path, self.raw, self.approved, FakeTransport(),
                                            clock=lambda: 10)
                before = phase == "before-reserve"
                self.assertEqual(restarted.snapshot()["attempts"], 0 if before else 1)
                self.assertEqual(restarted.snapshot()["outstanding_micro"], 0 if before else 10500)
                if not before:
                    self.denial("uncertain", restarted.resume, approval(self.raw, serial="fresh"))
                    self.denial("stopped", self.gateway.reserve, self.session, "qa", 2, 1, PAYLOAD)

    def test_append_only_and_corrupt_schema_fail_closed(self):
        self.build()
        permit, _ = self.push()
        with closing(sqlite3.connect(self.path)) as db, db:
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM attempt WHERE id=?", (permit.attempt,))
            db.execute("DROP TRIGGER immutable_attempt_delete")
        self.denial("storage", self.gateway.reserve, self.session, "qa", 2, 1, PAYLOAD)
        self.assertEqual(len(self.transport.calls), 1)


if __name__ == "__main__":
    unittest.main()
