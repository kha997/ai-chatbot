import http.client
import re
import threading
import unittest
from urllib.parse import urlencode

from scripts.quote_preview import make_server


class QuotePreviewHttpTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(0)
        self.worker = threading.Thread(target=self.server.serve_forever)
        self.worker.start()
        self.addCleanup(self.close_server)
        self.host, self.port = self.server.server_address
        self.origin = f"http://{self.host}:{self.port}"
        status, _, page = self.http("GET", "/")
        self.assertEqual(status, 200)
        self.token = re.search(r'name="token" value="([0-9a-f]+)"', page).group(1)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(2)
        self.assertFalse(self.worker.is_alive())

    def http(self, method, path, body=None, **headers):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode("utf-8")
        finally:
            conn.close()

    def post(self, action, tenant="NHD", fields=None, origin=None):
        body = urlencode(fields if fields is not None else {"action": action, "tenant": tenant, "token": self.token})
        return self.http("POST", "/", body, Origin=origin or self.origin,
                         **{"Content-Type": "application/x-www-form-urlencoded"})

    def page(self, action, tenant="NHD", **fields):
        form = {"action": action, "tenant": tenant, "token": self.token, **fields}
        status, _, body = self.post(action, fields=form)
        self.assertEqual(status, 200)
        return body

    def test_loopback_and_local_assets_only(self):
        self.assertEqual(self.host, "127.0.0.1")
        _, headers, body = self.http("GET", "/")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn('href="/style.css"', body)
        self.assertNotIn("https://", body)
        self.assertEqual(self.http("GET", "/style.css")[0], 200)
        self.assertEqual(self.http("GET", "/eval/quote_acceptance.json")[0], 404)
        self.assertEqual(self.http("GET", "/", Host="example.invalid")[0], 400)

    def test_all_three_authorized_quotes_use_the_real_oracle(self):
        cases = {"NHD": ("600.000", "Phí giao hàng"), "HANU": ("50.000", "Chứng thực"),
                 "ZENA": ("600.000", "Giấy phép xây dựng")}
        for tenant, (amount, exclusion) in cases.items():
            with self.subTest(tenant=tenant):
                page = self.page("quote", tenant)
                self.assertIn("SYNTHETIC TEST DATA", page)
                self.assertIn("NONBINDING DRAFT", page)
                self.assertIn("NO LIVE DELIVERY / NO AI MODEL", page)
                self.assertIn(f"{amount} VND", page)
                self.assertIn(f"{tenant}-pricing-v1#p1", page)
                self.assertIn(exclusion, page)

    def test_clarification_and_consent_required_for_each_tenant(self):
        for tenant in ("NHD", "HANU", "ZENA"):
            with self.subTest(tenant=tenant):
                preview = self.page("clarify", tenant)
                self.assertIn("Cần làm rõ", preview)
                self.assertIn("Bổ sung số lượng", preview)
                self.assertNotIn('data-testid="ticket-id"', preview)
                without_consent = self.page("consent", tenant)
                self.assertNotIn('data-testid="ticket-id"', without_consent)
                self.assertIn('type="checkbox"', without_consent)
                delivered = self.page("consent", tenant, consent="yes")
                self.assertIn('data-testid="ticket-id"', delivered)
                self.assertIn("Chờ tiếp nhận", delivered)
                self.assertIn(f"Hộp thư {tenant}", delivered)

    def test_duplicate_and_wrong_staff_preserve_one_ticket_then_accept(self):
        self.page("clarify")
        delivered = self.page("consent", consent="yes")
        ticket = re.search(r'data-testid="ticket-id">([0-9a-f]+)', delivered).group(1)
        duplicate = self.page("consent", consent="yes")
        self.assertIn(ticket, duplicate)
        self.assertEqual(duplicate.count('data-testid="ticket-id"'), 1)
        self.assertNotIn("confirmation", delivered)
        for action in ("wrong-tenant", "wrong-role"):
            denied = self.page(action, ticket=ticket)
            self.assertIn("Từ chối xác nhận", denied)
            self.assertIn("Chờ tiếp nhận", denied)
            self.assertIn(ticket, denied)
        confirmed = self.page("confirm", ticket=ticket)
        self.assertIn("Đã tiếp nhận giả lập", confirmed)
        self.assertIn(ticket, confirmed)
        self.assertNotIn(ticket, self.page("select", "HANU"))
        self.assertNotIn(ticket, self.page("reset"))

    def test_stale_inbox_form_cannot_confirm_a_replacement_ticket(self):
        self.page("clarify")
        first = self.page("consent", consent="yes")
        old_ticket = re.search(r'data-testid="ticket-id">([0-9a-f]+)', first).group(1)
        self.page("reset")
        self.page("clarify")
        second = self.page("consent", consent="yes")
        new_ticket = re.search(r'data-testid="ticket-id">([0-9a-f]+)', second).group(1)
        self.assertNotEqual(old_ticket, new_ticket)
        response = self.page("confirm", ticket=old_ticket)
        self.assertIn("Phiếu đã thay đổi", response)
        self.assertIn("Chờ tiếp nhận", response)
        self.assertNotIn(old_ticket, response)
        self.assertIn("Đã tiếp nhận giả lập", self.page("confirm", ticket=new_ticket))

    def test_refusal_hides_any_price_citation_and_previous_ticket(self):
        self.page("clarify")
        self.page("consent", consent="yes")
        for tenant in ("NHD", "HANU", "ZENA"):
            with self.subTest(tenant=tenant):
                page = self.page("refuse", tenant)
                self.assertIn("Yêu cầu bị từ chối", page)
                self.assertNotRegex(page, r"(?:pricing-v1#p1|(?:600\.000|50\.000) VND)")
                self.assertNotIn('data-testid="ticket-id"', page)
                self.assertNotIn('value="consent"', page)
                self.assertNotIn('value="confirm"', page)

    def test_cross_origin_and_untrusted_inputs_are_rejected(self):
        self.assertEqual(self.post("quote", origin="https://example.invalid")[0], 403)
        fields = {"action": "quote", "tenant": "NHD", "token": self.token}
        for mutation in ({"role": "support"}, {"source_id": "arbitrary"}, {"tenant": "<script>"},
                         {"action": "execute"}, {"token": "invalid"}):
            with self.subTest(mutation=mutation):
                status, _, body = self.post("quote", fields=fields | mutation)
                self.assertIn(status, (400, 403))
                self.assertNotIn("<script>", body)
        duplicate = urlencode(fields) + "&tenant=HANU"
        oversized = "x" * 2048
        for body in (duplicate, oversized):
            status, _, _ = self.http("POST", "/", body, Origin=self.origin,
                                     **{"Content-Type": "application/x-www-form-urlencoded"})
            self.assertIn(status, (400, 413))
