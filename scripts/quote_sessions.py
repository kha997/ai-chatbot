"""Offline synthetic bearer sessions; trusted Python setup is NOT real login.

Only SessionQuotes is the request boundary. SessionAuthority.issue/revoke are
trusted fixture/admin capabilities and must never be exposed as request routes.
"""

from copy import deepcopy
from dataclasses import dataclass, replace
from functools import wraps
import json
import math
from pathlib import Path
import re
import secrets
from threading import RLock
from time import monotonic

from scripts.quote_handoff import MockHandoffQueue, MockQuoteHandoff
from scripts.quote_validator import validate_quote


TENANTS = frozenset(("NHD", "HANU", "ZENA"))
ROLES = frozenset(("customer", "support"))
REFERENCE = re.compile(r"[A-Za-z0-9_-]{1,128}")
HANDLE = re.compile(r"[A-Za-z0-9_-]{43}")
TICKET = re.compile(r"[0-9a-f]{32}")


def _matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def _denied():
    # No reason, price, currency, citation or ticket existence oracle.
    return {"status": "denied"}


@dataclass(frozen=True)
class _Session:
    tenant: str
    role: str
    actor_id: str
    session_id: str
    issued: float
    expires: float
    revoked: bool = False


class SessionAuthority:
    """Ephemeral local authority, owned exclusively by trusted setup code."""

    def __init__(self, *, clock=monotonic):
        self._clock = clock
        self._records = {}
        self._lock = RLock()

    def _now(self):
        now = self._clock()
        return now if type(now) in (int, float) and math.isfinite(now) else None

    def issue(self, *, tenant, role, actor_id, lifetime=3600):
        """Trusted fixture/admin call only. Roles are fixed for this handle."""
        if (type(tenant) is not str or tenant not in TENANTS
                or type(role) is not str or role not in ROLES
                or not _matches(REFERENCE, actor_id)
                or type(lifetime) is not int or not 0 < lifetime <= 86400):
            raise ValueError("Invalid synthetic session setup")
        with self._lock:
            now = self._now()
            if now is None:
                raise ValueError("Invalid synthetic clock")
            handle = secrets.token_urlsafe(32)
            while handle in self._records:
                handle = secrets.token_urlsafe(32)
            self._records[handle] = _Session(tenant, role, actor_id, secrets.token_hex(16), now, now + lifetime)
            return handle

    def revoke(self, handle):
        """Trusted admin call; unknown handles have no effect."""
        with self._lock:
            if _matches(HANDLE, handle) and handle in self._records:
                self._records[handle] = replace(self._records[handle], revoked=True)

    def _resolve(self, handle, tenant, role):
        # Called with the authority lock held for the entire protected operation,
        # so revoke cannot race between authorization and the side effect.
        if not _matches(HANDLE, handle) or type(tenant) is not str or tenant not in TENANTS:
            return None
        record = self._records.get(handle)
        now = self._now()
        if (record is None or now is None or record.revoked
                or record.tenant != tenant or record.role != role
                or not record.issued <= now < record.expires):
            return None
        return record


def _protected(role):
    def decorate(method):
        @wraps(method)
        def call(self, handle, tenant, *args, **kwargs):
            with self._authority._lock:
                session = self._authority._resolve(handle, tenant, role)
                if session is None:
                    return _denied()
                return method(self, session, *args, **kwargs)
        return call
    return decorate


class SessionQuotes:
    """Protected offline operations over pinned bundled synthetic fixtures.

    No caller-supplied context, staff, catalog, clock or session identifier.
    expected tenant is a resource scope, never an authority assignment.
    """

    def __init__(self, authority):
        self._authority = authority
        fixture = json.loads((Path(__file__).resolve().parents[1] / "eval/quote_acceptance.json").read_text(encoding="utf-8"))
        self._as_of = fixture["as_of"]  # Fixed quote valuation date, not session expiry time.
        self._catalog = {}
        for case in fixture["cases"]:
            if "baseline_case_id" not in case:
                continue
            tenant = case["context"]["tenant"]
            source = [s for s in fixture["sources"] if s["tenant"] == tenant
                      and s["source_id"] == case["candidate"]["source_id"]
                      and s["version"] == case["candidate"]["version"]]
            if len(source) != 1 or tenant in self._catalog:
                raise ValueError("Ambiguous bundled synthetic catalog")
            self._catalog[tenant] = deepcopy((case, source))
        if set(self._catalog) != TENANTS:
            raise ValueError("Incomplete bundled synthetic catalog")
        self._handoff = MockQuoteHandoff(MockHandoffQueue())
        self._requests = {}
        self._tickets = {}
        self._deliveries = {}

    def _terms(self, session, request, candidate):
        case, sources = self._catalog[session.tenant]
        if (type(request) is not dict or not request
                or not set(request) <= {"sku", "quantity", "unit", "currency"}
                or any(type(v) is not str or len(v) > 128 for v in request.values())
                or request.get("sku") != case["request"]["sku"]):
            return None
        canonical = case["candidate"]
        if candidate is not None:
            if (type(candidate) is not dict or set(candidate) != set(canonical)
                    or any(type(candidate[k]) is not type(v) or candidate[k] != v
                           for k, v in canonical.items())):
                return None
        return dict(context=deepcopy(case["context"]), request=dict(request),
                    candidate=deepcopy(canonical), sources=deepcopy(sources), as_of=self._as_of)

    @_protected("customer")
    def quote(self, session, request, *, candidate=None):
        terms = self._terms(session, request, candidate)
        if terms is None:
            return _denied()
        result = validate_quote(**terms)
        return _denied() if result["behavior"] == "refuse" else result

    @_protected("customer")
    def handoff(self, session, request, *, message_id, consent, candidate=None):
        terms = self._terms(session, request, candidate)
        if terms is None or not _matches(REFERENCE, message_id):
            return _denied()
        if consent is not True:
            return {"status": "consent_required"}
        key = (session.session_id, message_id)
        prior = self._requests.get(key)
        if prior is not None and prior != terms["request"]:
            return _denied()
        result = self._handoff.request(**terms, session_id=session.session_id,
                                       message_id=message_id, consent=True)
        if "ticket_id" in result:
            self._requests[key] = dict(terms["request"])
            self._tickets.setdefault(result["ticket_id"], {
                "tenant": session.tenant, "session_id": session.session_id, "status": "queued",
            })
        return result

    @_protected("customer")
    def ticket_status(self, session, ticket_id):
        if not _matches(TICKET, ticket_id):
            return _denied()
        ticket = self._tickets.get(ticket_id)
        if ticket is None or (ticket["tenant"], ticket["session_id"]) != (session.tenant, session.session_id):
            return _denied()
        return {"status": ticket["status"], "ticket_id": ticket_id}

    @_protected("support")
    def deliver_next(self, session):
        delivery = self._handoff.deliver_next(staff={"tenant": session.tenant, "role": "support"})
        if delivery is None:
            return {"status": "empty"}
        self._deliveries[delivery["ticket_id"]] = delivery
        return self._public_delivery(delivery)

    @staticmethod
    def _public_delivery(delivery):
        return {key: delivery[key] for key in ("tenant", "ticket_id", "reason")}

    @_protected("support")
    def inbox(self, session):
        return {"status": "ok", "tickets": [self._public_delivery(d) for d in self._deliveries.values()
                                            if d["tenant"] == session.tenant]}

    @_protected("support")
    def confirm(self, session, ticket_id):
        if not _matches(TICKET, ticket_id):
            return _denied()
        delivery = self._deliveries.get(ticket_id)
        if delivery is None or delivery["tenant"] != session.tenant:
            return _denied()
        result = self._handoff.confirm(staff={"tenant": session.tenant, "role": "support"},
                                       ticket_id=ticket_id, confirmation=delivery["confirmation"])
        if result["status"] != "accepted":
            return _denied()
        self._tickets[ticket_id]["status"] = "accepted"
        return result
