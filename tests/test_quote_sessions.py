"""Adversarial tests for the synthetic adapter, not caller-asserted contexts."""

import json
from pathlib import Path
import unittest

from scripts.quote_sessions import SessionAuthority, SessionQuotes


DENIED = {"status": "denied"}
TENANTS = ("NHD", "HANU", "ZENA")


class QuoteSessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.authority = SessionAuthority(clock=lambda: self.now)
        self.app = SessionQuotes(self.authority)
        self.customer = {t: self.issue(t, "customer") for t in TENANTS}
        self.support = {t: self.issue(t, "support") for t in TENANTS}
        fixture = json.loads((Path(__file__).resolve().parents[1] / "eval/quote_acceptance.json").read_text())
        self.cases = {c["context"]["tenant"]: c for c in fixture["cases"] if "baseline_case_id" in c}

    def issue(self, tenant="NHD", role="customer", actor="synthetic-actor"):
        return self.authority.issue(tenant=tenant, role=role, actor_id=actor, lifetime=60)

    def request(self, tenant="NHD", clarify=False):
        request = dict(self.cases[tenant]["request"])
        if clarify:
            request.pop("quantity")
        return request

    def queue(self, tenant="NHD", handle=None, message="message-1"):
        return self.app.handoff(handle or self.customer[tenant], tenant, self.request(tenant, True),
                                message_id=message, consent=True)

    def test_three_positive_prices_and_citations(self):
        for tenant, total in (("NHD", "600000"), ("HANU", "50000"), ("ZENA", "600000")):
            self.assertEqual(self.app.quote(self.customer[tenant], tenant, self.request(tenant)),
                             {"behavior": "answer", "reason": "quoted", "total": total,
                              "currency": "VND", "citation": tenant + "-pricing-v1#p1"})

    def test_handles_are_opaque_unique_and_restart_invalidates(self):
        handles = {self.issue() for _ in range(100)}
        self.assertEqual(len(handles), 100)
        for handle in handles:
            self.assertGreaterEqual(len(handle), 40)
            self.assertNotIn("synthetic-actor", handle)
            self.assertNotIn("NHD", handle)
        restarted = SessionQuotes(SessionAuthority(clock=lambda: self.now))
        self.assertEqual(restarted.quote(self.customer["NHD"], "NHD", self.request()), DENIED)

    def test_invalid_missing_tampered_self_asserted_handles_deny_all_operations(self):
        valid = self.customer["NHD"]
        for handle in (None, "", "random", valid[:-1], valid + "x", [], {}, 1, True,
                       {"tenant": "NHD", "role": "support"}):
            with self.subTest(handle=handle):
                self.assertEqual(self.app.quote(handle, "NHD", self.request()), DENIED)
                self.assertEqual(self.app.handoff(handle, "NHD", self.request(clarify=True),
                                                 message_id="m", consent=True), DENIED)
                self.assertEqual(self.app.deliver_next(handle, "NHD"), DENIED)
                self.assertEqual(self.app.inbox(handle, "NHD"), DENIED)
                self.assertEqual(self.app.confirm(handle, "NHD", "ticket"), DENIED)
                self.assertEqual(self.app.ticket_status(handle, "NHD", "ticket"), DENIED)

    def test_expiry_is_half_open_and_revocation_is_immediate(self):
        customer, staff = self.customer["NHD"], self.support["NHD"]
        ticket = self.queue()["ticket_id"]
        self.app.deliver_next(staff, "NHD")
        self.now = 1059
        self.assertEqual(self.app.quote(customer, "NHD", self.request())["behavior"], "answer")
        self.now = 1060
        self.assertEqual(self.app.quote(customer, "NHD", self.request()), DENIED)
        self.assertEqual(self.app.handoff(customer, "NHD", self.request(clarify=True),
                                         message_id="m", consent=True), DENIED)
        self.assertEqual(self.app.ticket_status(customer, "NHD", ticket), DENIED)
        self.assertEqual(self.app.deliver_next(staff, "NHD"), DENIED)
        self.assertEqual(self.app.inbox(staff, "NHD"), DENIED)
        self.assertEqual(self.app.confirm(staff, "NHD", ticket), DENIED)
        self.now = 999
        self.assertEqual(self.app.quote(customer, "NHD", self.request()), DENIED)

    def test_revoked_customer_and_staff_cannot_reuse_delivered_ticket(self):
        ticket = self.queue()["ticket_id"]
        self.app.deliver_next(self.support["NHD"], "NHD")
        for handle in (self.customer["NHD"], self.support["NHD"]):
            self.authority.revoke(handle)
            self.assertEqual(self.app.quote(handle, "NHD", self.request()), DENIED)
            self.assertEqual(self.app.handoff(handle, "NHD", self.request(clarify=True),
                                             message_id="m", consent=True), DENIED)
            self.assertEqual(self.app.deliver_next(handle, "NHD"), DENIED)
            self.assertEqual(self.app.inbox(handle, "NHD"), DENIED)
            self.assertEqual(self.app.confirm(handle, "NHD", ticket), DENIED)
            self.assertEqual(self.app.ticket_status(handle, "NHD", ticket), DENIED)

    def test_every_tenant_swap_denies_without_consuming_queue(self):
        for tenant in TENANTS:
            ticket = self.queue(tenant)["ticket_id"]
            for foreign in set(TENANTS) - {tenant}:
                self.assertEqual(self.app.quote(self.customer[foreign], tenant, self.request(tenant)), DENIED)
                self.assertEqual(self.app.handoff(self.customer[foreign], tenant, self.request(tenant, True),
                                                 message_id="m", consent=True), DENIED)
                self.assertEqual(self.app.deliver_next(self.support[foreign], tenant), DENIED)
                self.assertEqual(self.app.inbox(self.support[foreign], tenant), DENIED)
                self.assertEqual(self.app.confirm(self.support[foreign], tenant, ticket), DENIED)
                self.assertEqual(self.app.confirm(self.support[foreign], foreign, ticket), DENIED)
                self.assertEqual(self.app.ticket_status(self.customer[foreign], foreign, ticket), DENIED)
            delivered = self.app.deliver_next(self.support[tenant], tenant)
            self.assertEqual(delivered["ticket_id"], ticket)
            self.assertNotIn("confirmation", delivered)

    def test_customer_and_support_roles_are_not_interchangeable(self):
        ticket = self.queue()["ticket_id"]
        customer, staff = self.customer["NHD"], self.support["NHD"]
        self.assertEqual(self.app.deliver_next(customer, "NHD"), DENIED)
        self.assertEqual(self.app.inbox(customer, "NHD"), DENIED)
        self.app.deliver_next(staff, "NHD")
        self.assertEqual(self.app.confirm(customer, "NHD", ticket), DENIED)
        self.assertEqual(self.app.quote(staff, "NHD", self.request()), DENIED)
        self.assertEqual(self.app.handoff(staff, "NHD", self.request(clarify=True),
                                         message_id="m", consent=True), DENIED)
        self.assertEqual(self.app.ticket_status(staff, "NHD", ticket), DENIED)

    def test_forged_authority_and_catalog_fields_deny_before_clarification(self):
        for key, value in (("tenant", "HANU"), ("requested_tenant", "HANU"), ("role", "support"),
                           ("context", {"tenant": "NHD"}), ("session_id", "other"),
                           ("source_id", "HANU-pricing-v1"), ("citation", "HANU-pricing-v1#p1"),
                           ("sources", []), ("candidate", {}), ("active_sources", [])):
            request = self.request(clarify=True) | {key: value}
            self.assertEqual(self.app.quote(self.customer["NHD"], "NHD", request), DENIED)
            self.assertEqual(self.app.handoff(self.customer["NHD"], "NHD", request,
                                             message_id="m", consent=True), DENIED)
        self.assertEqual(self.app.deliver_next(self.support["NHD"], "NHD"), {"status": "empty"})

    def test_foreign_skus_and_citations_never_select_foreign_catalog(self):
        for tenant in TENANTS:
            for foreign in set(TENANTS) - {tenant}:
                request = self.request(tenant) | {"sku": self.request(foreign)["sku"]}
                self.assertEqual(self.app.quote(self.customer[tenant], tenant, request), DENIED)
                candidate = self.cases[foreign]["candidate"]
                self.assertEqual(self.app.quote(self.customer[tenant], tenant, self.request(tenant),
                                               candidate=candidate), DENIED)
                self.assertEqual(self.app.handoff(self.customer[tenant], tenant, self.request(tenant, True),
                                                 message_id="m", consent=True, candidate=candidate), DENIED)

    def test_same_tenant_forged_citation_version_or_amount_is_denied(self):
        canonical = self.cases["NHD"]["candidate"]
        for mutation in ({"citation": "NHD-pricing-v1#p99"}, {"version": True},
                         {"version": 2}, {"total": "1"}):
            self.assertEqual(self.app.quote(self.customer["NHD"], "NHD", self.request(),
                                           candidate=canonical | mutation), DENIED)

    def test_explicit_consent_only_then_support_confirmation(self):
        customer, staff = self.customer["NHD"], self.support["NHD"]
        for consent in (False, None, "true", 1, {}, []):
            self.assertEqual(self.app.handoff(customer, "NHD", self.request(clarify=True),
                                             message_id="m", consent=consent), {"status": "consent_required"})
        self.assertEqual(self.app.deliver_next(staff, "NHD"), {"status": "empty"})
        queued = self.queue()
        self.assertEqual(queued["status"], "queued")
        ticket = queued["ticket_id"]
        self.assertEqual(self.app.confirm(staff, "NHD", ticket), DENIED)
        delivered = self.app.deliver_next(staff, "NHD")
        self.assertEqual(self.app.inbox(staff, "NHD"), {"status": "ok", "tickets": [delivered]})
        self.assertEqual(self.app.confirm(staff, "NHD", ticket), {"status": "accepted", "ticket_id": ticket})
        self.assertEqual(self.app.ticket_status(customer, "NHD", ticket),
                         {"status": "accepted", "ticket_id": ticket})

    def test_same_actor_new_session_has_no_ticket_access_or_replay_authority(self):
        first = self.queue()
        other = self.issue()
        self.assertEqual(self.app.ticket_status(other, "NHD", first["ticket_id"]), DENIED)
        second = self.queue(handle=other)
        self.assertNotEqual(first["ticket_id"], second["ticket_id"])
        self.assertEqual(self.app.ticket_status(self.customer["NHD"], "NHD", second["ticket_id"]), DENIED)
        self.assertEqual(self.queue(), first)
        self.assertEqual(self.app.deliver_next(self.support["NHD"], "NHD")["ticket_id"], first["ticket_id"])
        self.assertEqual(self.app.deliver_next(self.support["NHD"], "NHD")["ticket_id"], second["ticket_id"])
        self.assertEqual(self.app.deliver_next(self.support["NHD"], "NHD"), {"status": "empty"})

    def test_changed_replay_cannot_reuse_prior_consent(self):
        self.queue()
        request = self.request(clarify=True) | {"quantity": "0"}
        self.assertEqual(self.app.handoff(self.customer["NHD"], "NHD", request,
                                         message_id="message-1", consent=True), DENIED)
        self.assertEqual(self.app.handoff(self.customer["NHD"], "NHD", self.request(clarify=True),
                                         message_id="message-1", consent=False), {"status": "consent_required"})

    def test_mutating_outputs_or_requests_does_not_change_server_state(self):
        request = self.request(clarify=True)
        ticket = self.app.handoff(self.customer["NHD"], "NHD", request, message_id="m", consent=True)["ticket_id"]
        request["role"] = "support"
        delivery = self.app.deliver_next(self.support["NHD"], "NHD")
        delivery["tenant"] = "HANU"
        delivery["ticket_id"] = "forged"
        inbox = self.app.inbox(self.support["NHD"], "NHD")
        inbox["tickets"].clear()
        self.assertEqual(self.app.confirm(self.support["NHD"], "NHD", ticket)["status"], "accepted")
        self.assertEqual(len(self.app.inbox(self.support["NHD"], "NHD")["tickets"]), 1)

    def test_malformed_inputs_are_uniformly_denied(self):
        for value in (None, [], {}, True, 123, "", "x" * 5000):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(self.app.quote(self.customer["NHD"], value, self.request()), DENIED)
                self.assertEqual(self.app.quote(self.customer["NHD"], "NHD", value), DENIED)
                self.assertEqual(self.app.confirm(self.support["NHD"], "NHD", value), DENIED)
                self.assertEqual(self.app.ticket_status(self.customer["NHD"], "NHD", value), DENIED)
                self.assertEqual(self.app.handoff(self.customer["NHD"], "NHD", self.request(clarify=True),
                                                 message_id=value, consent=True), DENIED)
        for key in ("sku", "quantity", "unit", "currency"):
            for value in (None, [], {}, True, 1, "x" * 5000):
                self.assertEqual(self.app.quote(self.customer["NHD"], "NHD", self.request() | {key: value}), DENIED)

    def test_unknown_roles_tenants_and_invalid_lifetimes_never_issue(self):
        for tenant, role, actor, lifetime in (("OTHER", "customer", "synthetic-a", 60),
                                             ("NHD", "admin", "synthetic-a", 60),
                                             ([], "support", "synthetic-a", 60),
                                             ("NHD", [], "synthetic-a", 60),
                                             ("NHD", "customer", "", 60),
                                             ("NHD", "customer", "synthetic-a", 0),
                                             ("NHD", "customer", "synthetic-a", True)):
            with self.assertRaises(ValueError):
                self.authority.issue(tenant=tenant, role=role, actor_id=actor, lifetime=lifetime)


if __name__ == "__main__":
    unittest.main()
