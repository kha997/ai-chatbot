"""Loopback-only browser preview of the synthetic quote and handoff contracts."""

import argparse
import json
import re
from dataclasses import dataclass, field
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from secrets import compare_digest, token_hex
from socketserver import TCPServer
from string import Template
from urllib.parse import parse_qsl

from scripts.quote_handoff import MockHandoffQueue, MockQuoteHandoff
from scripts.quote_validator import validate_quote


ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).with_name("quote_preview_assets")
HOST = "127.0.0.1"
TENANTS = ("NHD", "HANU", "ZENA")
NEXT_TENANT = dict(zip(TENANTS, (*TENANTS[1:], TENANTS[0])))
TENANT_LABELS = {"NHD": "Sản phẩm", "HANU": "Dịch thuật", "ZENA": "Tư vấn"}
EXCLUSIONS = {
    "delivery_included": "Phí giao hàng",
    "certification_included": "Chứng thực",
    "permit_included": "Giấy phép xây dựng",
    "professional_signoff": "Xác nhận chuyên môn",
}
SCENARIOS = {
    "quote": ("Báo giá hợp lệ", "Xem giá và nguồn đã duyệt"),
    "clarify": ("Thiếu số lượng", "Xem cách đề nghị hỗ trợ"),
    "refuse": ("Nguồn khác tenant", "Kiểm tra từ chối an toàn"),
}
STAFF_ACTIONS = {"confirm", "wrong-tenant", "wrong-role"}
ACTIONS = {*SCENARIOS, *STAFF_ACTIONS, "select", "consent", "reset"}
MAX_FORM = 1024
CSP = "default-src 'none'; style-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"


@dataclass
class Journey:
    scenario: str = "quote"
    handoff: MockQuoteHandoff = field(default_factory=lambda: MockQuoteHandoff(MockHandoffQueue()))
    delivery: dict | None = None
    accepted: bool = False


class Preview:
    def __init__(self):
        fixture = json.loads((ROOT / "eval" / "quote_acceptance.json").read_text(encoding="utf-8"))
        original = json.loads((ROOT / "eval" / "examples.json").read_text(encoding="utf-8"))
        self.sources, self.as_of = fixture["sources"], fixture["as_of"]
        self.cases = {case["context"]["tenant"]: case for case in fixture["cases"] if "baseline_case_id" in case}
        self.original = {case["id"]: case for case in original["cases"]}
        self.template = Template((ASSETS / "index.html").read_text(encoding="utf-8"))
        self.styles = (ASSETS / "style.css").read_bytes()
        self.token = token_hex(24)
        self.journeys = {tenant: Journey() for tenant in TENANTS}

    def terms(self, tenant, scenario):
        case = self.cases[tenant]
        request = dict(case["request"])
        if scenario == "clarify":
            request.pop("quantity")
        candidate = self.cases[NEXT_TENANT[tenant]]["candidate"] if scenario == "refuse" else case["candidate"]
        return dict(context=case["context"], request=request, candidate=candidate,
                    sources=self.sources, as_of=self.as_of)

    def act(self, action, tenant, consent, ticket_id):
        journey = self.journeys[tenant]
        if action in SCENARIOS:
            journey.scenario = action
        elif action == "reset":
            self.journeys[tenant] = Journey()
            return "Đã đặt lại tình huống và hộp thư giả lập."
        elif action == "consent" and journey.scenario == "clarify":
            handoff = journey.handoff.request(
                **self.terms(tenant, "clarify"), consent=consent, session_id="preview", message_id="missing-quantity",
            )
            if handoff["status"] == "consent_required":
                return "Hãy đánh dấu đồng ý trước khi gửi hỗ trợ."
            if handoff["status"] == "queued" and journey.delivery is None:
                journey.delivery = journey.handoff.deliver_next(staff={"tenant": tenant, "role": "support"})
            if journey.delivery is None:
                return "Hộp thư giả lập chưa nhận được phiếu."
        elif action in STAFF_ACTIONS:
            if (journey.scenario == "refuse" or journey.delivery is None
                    or ticket_id != journey.delivery["ticket_id"]):
                return "Phiếu đã thay đổi. Hãy dùng phiếu đang hiển thị."
            staff = {"tenant": NEXT_TENANT[tenant] if action == "wrong-tenant" else tenant,
                     "role": "customer" if action == "wrong-role" else "support"}
            receipt = journey.handoff.confirm(
                staff=staff, ticket_id=journey.delivery["ticket_id"], confirmation=journey.delivery["confirmation"],
            )
            if receipt["status"] == "accepted":
                journey.accepted = True
            else:
                return "Từ chối xác nhận: sai tenant hoặc vai trò."
        return ""

    def hidden(self, tenant=None):
        fields = f'<input type="hidden" name="token" value="{self.token}">'
        if tenant is not None:
            fields += f'<input type="hidden" name="tenant" value="{escape(tenant)}">'
        return fields

    def quote_panel(self, tenant, quote, inputs):
        if quote["behavior"] == "refuse":
            return ('<div class="state danger">Từ chối</div><h2>Yêu cầu bị từ chối</h2>'
                    '<p>Nguồn yêu cầu không thuộc phạm vi được phép của tenant đã chọn.</p>')
        if quote["behavior"] == "clarify":
            return (
                '<div class="state warning">Cần làm rõ</div><h2>Bổ sung số lượng</h2>'
                '<p>Chưa đủ thông tin để tính báo giá.</p>'
                f'<form method="post" action="/" class="consent">{self.hidden(tenant)}'
                '<label><input type="checkbox" name="consent" value="yes"> Tôi đồng ý chuyển yêu cầu '
                'giả lập sang hộp thư hỗ trợ.</label>'
                '<button class="primary" name="action" value="consent">Gửi hỗ trợ giả lập</button></form>'
            )

        whole, dot, fraction = quote["total"].partition(".")
        amount = f"{int(whole):,}".replace(",", ".") + (f",{fraction}" if dot else "")
        source = self.original[self.cases[tenant]["baseline_case_id"]]
        exclusions = [EXCLUSIONS[claim] for claim in source["oracle"]["forbidden_claims"] if claim in EXCLUSIONS]
        request = inputs["request"]
        items = "".join(f"<li>{escape(item)}</li>" for item in exclusions)
        return (
            '<div class="state success">Hợp lệ</div><h2>Báo giá nháp</h2>'
            f'<p class="amount">{escape(amount)} {escape(quote["currency"])}</p>'
            f'<p>Mã <code>{escape(request["sku"])}</code> · Số lượng {escape(request["quantity"])}</p>'
            f'<dl class="source"><dt>Nguồn trích dẫn</dt><dd><code>{escape(quote["citation"])}</code></dd></dl>'
            f'<h3>Không bao gồm</h3><ul>{items}</ul>'
        )

    def inbox_panel(self, tenant, journey, behavior):
        if behavior == "refuse":
            return '<p>Không hiển thị phiếu hỗ trợ trong tình huống từ chối.</p>'
        if journey.delivery is None:
            return '<p>Chưa có phiếu. Thử tình huống thiếu số lượng và đồng ý chuyển hỗ trợ.</p>'
        state = "Đã tiếp nhận giả lập" if journey.accepted else "Chờ tiếp nhận"
        ticket_id = escape(journey.delivery["ticket_id"])
        return (
            f'<div class="ticket"><p class="state">{state}</p>'
            f'<p>Mã phiếu <code data-testid="ticket-id">{ticket_id}</code></p>'
            '<p>Cần bổ sung số lượng.</p></div>'
            f'<form method="post" action="/" class="staff-actions">{self.hidden(tenant)}'
            f'<input type="hidden" name="ticket" value="{ticket_id}">'
            '<button class="primary" name="action" value="confirm">Xác nhận đúng tenant</button>'
            '<button name="action" value="wrong-tenant">Thử sai tenant</button>'
            '<button name="action" value="wrong-role">Thử sai vai trò</button></form>'
        )

    def render(self, tenant, notice=""):
        journey = self.journeys[tenant]
        inputs = self.terms(tenant, journey.scenario)
        quote = validate_quote(**inputs)
        tenant_buttons = "".join(
            f'<button name="tenant" value="{name}" aria-pressed="{str(name == tenant).lower()}">'
            f'<strong>{name}</strong><span>{TENANT_LABELS[name]}</span></button>' for name in TENANTS
        )
        scenario_buttons = "".join(
            f'<button name="action" value="{action}" aria-pressed="{str(action == journey.scenario).lower()}">'
            f'<strong>{label}</strong><span>{detail}</span></button>' for action, (label, detail) in SCENARIOS.items()
        )
        return self.template.substitute(
            tenant=escape(tenant), tenant_label=escape(TENANT_LABELS[tenant]),
            tenant_fields=self.hidden(), fields=self.hidden(tenant),
            tenants=tenant_buttons, scenarios=scenario_buttons,
            quote=self.quote_panel(tenant, quote, inputs), inbox=self.inbox_panel(tenant, journey, quote["behavior"]),
            notice=f'<p class="notice" role="status">{escape(notice)}</p>' if notice else "",
        ).encode("utf-8")


class PreviewServer(HTTPServer):
    def server_bind(self):
        # HTTPServer's default calls getfqdn(), which can do DNS lookups.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address

    def handle_error(self, request, client_address):
        print("Không thể xử lý yêu cầu preview cục bộ.")


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def log_message(self, format, *args):
        pass

    @property
    def authority(self):
        return f"{HOST}:{self.server.server_port}"

    def respond(self, status, body, content_type="text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def reject(self, status):
        self.respond(status, "Yêu cầu preview không hợp lệ.".encode("utf-8"))

    def do_GET(self):
        if self.headers.get_all("Host") != [self.authority]:
            return self.reject(400)
        if self.path == "/":
            return self.respond(200, self.server.preview.render(TENANTS[0]), "text/html")
        if self.path == "/style.css":
            return self.respond(200, self.server.preview.styles, "text/css")
        self.reject(404)

    def do_POST(self):
        if self.headers.get_all("Host") != [self.authority]:
            return self.reject(400)
        if self.path != "/":
            return self.reject(404)
        if self.headers.get_all("Origin") != [f"http://{self.authority}"]:
            return self.reject(403)
        if (self.headers.get_content_type() != "application/x-www-form-urlencoded"
                or self.headers.get("Transfer-Encoding") is not None):
            return self.reject(400)

        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit() or len(lengths[0]) > 9:
            return self.reject(400)
        length = int(lengths[0])
        if not 0 < length <= MAX_FORM:
            return self.reject(413)
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                return self.reject(400)
            pairs = parse_qsl(body.decode("ascii"), strict_parsing=True, keep_blank_values=True,
                              errors="strict", max_num_fields=4)
        except (UnicodeError, ValueError, TimeoutError):
            return self.reject(400)
        form = dict(pairs)
        action, tenant, token = (form.get(name, "") for name in ("action", "tenant", "token"))
        expected = {"action", "tenant", "token"}
        if action == "consent" and form.get("consent") == "yes":
            expected.add("consent")
        ticket = form.get("ticket", "")
        if action in STAFF_ACTIONS:
            if not re.fullmatch(r"[0-9a-f]{32}", ticket):
                return self.reject(400)
            expected.add("ticket")
        if set(form) != expected or len(form) != len(pairs) or tenant not in TENANTS or action not in ACTIONS:
            return self.reject(400)
        preview = self.server.preview
        if not token.isascii() or not compare_digest(token, preview.token):
            return self.reject(403)
        notice = preview.act(action, tenant, "consent" in form, ticket)
        self.respond(200, preview.render(tenant, notice), "text/html")


def make_server(port):
    preview = Preview()
    server = PreviewServer((HOST, port), Handler)
    server.preview = preview
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="loopback port; default is chosen by Windows or Linux")
    args = parser.parse_args()
    try:
        with make_server(args.port) as server:
            print(f"Quote preview: http://{HOST}:{server.server_port} — Ctrl+C để dừng.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng preview.")
    except (OSError, OverflowError):
        parser.exit(1, "Không thể mở cổng preview trên loopback. Hãy chọn cổng khác với --port.\n")


if __name__ == "__main__":
    main()
