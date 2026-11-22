import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from scripts.quote_handoff import MockHandoffQueue, MockQuoteHandoff
from test_quote_acceptance import read_json


class QuoteHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = read_json("quote_acceptance.json")

    def setUp(self):
        self.queue = MockHandoffQueue()
        self.handoff = MockQuoteHandoff(self.queue)

    def inputs(self, case_id="unknown-sku", **changes):
        case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
        inputs = deepcopy({name: case[name] for name in ("context", "request", "candidate")})
        inputs.update(
            sources=deepcopy(self.fixture["sources"]),
            as_of=self.fixture["as_of"],
            session_id="synthetic-customer",
            message_id="synthetic-message",
            consent=True,
        )
        inputs.update(changes)
        return inputs

    def staff(self, tenant="NHD", role="support"):
        return {"tenant": tenant, "role": role}

    def test_explicit_consent_then_mock_delivery_and_confirmation(self):
        result = self.handoff.request(**self.inputs())
        self.assertEqual(set(result), {"status", "ticket_id"})
        self.assertEqual(result["status"], "queued")
        delivery = self.handoff.deliver_next()
        self.assertEqual(set(delivery), {"tenant", "ticket_id", "reason", "confirmation"})
        self.assertEqual(delivery["tenant"], "NHD")
        self.assertEqual(delivery["reason"], "unknown_sku")
        self.assertEqual(delivery["ticket_id"], result["ticket_id"])
        self.assertEqual(
            self.handoff.confirm(staff=self.staff(), ticket_id=result["ticket_id"],
                                 confirmation=delivery["confirmation"]),
            {"status": "accepted", "ticket_id": result["ticket_id"]},
        )
        self.assertEqual(self.handoff.request(**self.inputs())["status"], "accepted")
        self.assertIsNone(self.handoff.deliver_next())

    def test_no_consent_never_enqueues(self):
        for consent in (False, None, 1, "true"):
            with self.subTest(consent=consent):
                self.assertEqual(self.handoff.request(**self.inputs(consent=consent)), {"status": "consent_required"})
        self.assertIsNone(self.handoff.deliver_next())

    def test_refusal_cannot_offer_handoff_or_expose_amount_or_source(self):
        cases = [case["id"] for case in self.fixture["cases"] if case["oracle"]["behavior"] == "refuse"]
        for case_id in cases:
            with self.subTest(case=case_id):
                self.assertEqual(self.handoff.request(**self.inputs(case_id)), {"status": "not_offered"})
        self.assertIsNone(self.handoff.deliver_next())

    def test_an_answer_does_not_start_a_handoff(self):
        self.assertEqual(
            self.handoff.request(**self.inputs("qa-HANU-price-01")), {"status": "not_offered"}
        )
        self.assertIsNone(self.handoff.deliver_next())

    def test_identical_replays_enqueue_only_once(self):
        inputs = self.inputs()
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.handoff.request(**inputs), range(8)))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(results[0]["status"], "queued")
        self.assertEqual(self.handoff.deliver_next()["ticket_id"], results[0]["ticket_id"])
        self.assertIsNone(self.handoff.deliver_next())

    def test_conflicting_replay_does_not_replace_pending_payload(self):
        initial = self.handoff.request(**self.inputs())
        self.assertEqual(
            self.handoff.request(**self.inputs("wrong-unit")),
            {"status": "conflict"},
        )
        delivery = self.handoff.deliver_next()
        self.assertEqual(delivery["reason"], "unknown_sku")
        self.assertEqual(delivery["ticket_id"], initial["ticket_id"])
        self.assertIsNone(self.handoff.deliver_next())

    def test_queue_failure_reports_no_ticket_and_can_be_retried_explicitly(self):
        self.queue.available = False
        self.assertEqual(self.handoff.request(**self.inputs()), {"status": "unavailable"})
        self.assertIsNone(self.handoff.deliver_next())
        self.queue.available = True
        self.assertEqual(self.handoff.request(**self.inputs())["status"], "queued")
        self.assertIsNotNone(self.handoff.deliver_next())
        self.assertIsNone(self.handoff.deliver_next())

    def test_forgery_cannot_confirm_before_delivery_or_with_wrong_proof(self):
        ticket = self.handoff.request(**self.inputs())["ticket_id"]
        self.assertEqual(self.handoff.confirm(staff=self.staff(), ticket_id=ticket, confirmation="forged"),
                         {"status": "refused"})
        delivery = self.handoff.deliver_next()
        for proof in ("forged", "x" * 100, "đ", None):
            with self.subTest(proof=proof):
                self.assertEqual(self.handoff.confirm(staff=self.staff(), ticket_id=ticket, confirmation=proof),
                                 {"status": "refused"})
        self.assertEqual(self.handoff.request(**self.inputs())["status"], "queued")
        for _ in range(2):
            self.assertEqual(self.handoff.confirm(staff=self.staff(), ticket_id=ticket,
                                                  confirmation=delivery["confirmation"])["status"], "accepted")

    def test_confirmation_for_a_different_ticket_cannot_be_reused(self):
        first = self.handoff.request(**self.inputs())
        second = self.handoff.request(**self.inputs(message_id="other-message"))
        first_delivery, second_delivery = self.handoff.deliver_next(), self.handoff.deliver_next()
        self.assertEqual(
            self.handoff.confirm(staff=self.staff(), ticket_id=first["ticket_id"],
                                 confirmation=second_delivery["confirmation"]),
            {"status": "refused"},
        )
        self.assertEqual(self.handoff.request(**self.inputs())["status"], "queued")
        self.assertEqual(
            self.handoff.confirm(staff=self.staff(), ticket_id=first["ticket_id"],
                                 confirmation=first_delivery["confirmation"])["status"], "accepted"
        )
        self.assertEqual(second_delivery["ticket_id"], second["ticket_id"])

    def test_tenant_and_support_role_are_checked_even_with_valid_proof(self):
        ticket = self.handoff.request(**self.inputs())["ticket_id"]
        delivery = self.handoff.deliver_next()
        for staff in (self.staff("HANU"), self.staff("ZENA"), self.staff(role="customer"), {}):
            with self.subTest(staff=staff):
                self.assertEqual(self.handoff.confirm(staff=staff, ticket_id=ticket,
                                                      confirmation=delivery["confirmation"]), {"status": "refused"})
        self.assertEqual(self.handoff.request(**self.inputs())["status"], "queued")

    def test_idempotency_is_scoped_to_tenant_and_session(self):
        first = self.handoff.request(**self.inputs())
        second = self.handoff.request(**self.inputs(session_id="other-synthetic-customer"))
        foreign = self.inputs("unknown-sku")
        foreign["context"]["tenant"] = "HANU"
        third = self.handoff.request(**foreign)
        self.assertEqual(len({result["ticket_id"] for result in (first, second, third)}), 3)
        self.assertEqual([self.handoff.deliver_next()["tenant"] for _ in range(3)], ["NHD", "NHD", "HANU"])
