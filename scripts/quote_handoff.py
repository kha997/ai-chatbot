"""In-memory synthetic support handoff for the draft quote contract."""

import re
from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from secrets import compare_digest, token_hex
from threading import Lock

from scripts.quote_validator import TENANTS, validate_quote


REFERENCE = re.compile(r"[A-Za-z0-9_-]{1,128}")


def _support_tenant(staff):
    if isinstance(staff, Mapping) and staff.get("role") == "support":
        tenant = staff.get("tenant")
        if isinstance(tenant, str) and tenant in TENANTS:
            return tenant
    return None


@dataclass
class _Ticket:
    tenant: str
    reason: str
    ticket_id: str = field(default_factory=lambda: token_hex(16))
    confirmation: str = ""
    accepted: bool = False


class MockHandoffQueue:
    """Local queue with an injectable unavailable state."""

    def __init__(self):
        self.available = True
        self._pending = defaultdict(deque)

    def enqueue(self, ticket):
        if not self.available:
            return False
        self._pending[ticket.tenant].append(ticket)
        return True

    def take(self, tenant):
        pending = self._pending.get(tenant)
        return pending.popleft() if pending else None


class MockQuoteHandoff:
    """Use trusted tenant/session and staff contexts supplied by the caller."""

    def __init__(self, queue):
        self._queue = queue
        self._requests = {}
        self._inboxes = {tenant: {} for tenant in TENANTS}
        self._lock = Lock()

    def request(self, *, context, request, candidate, sources, as_of, session_id, message_id, consent):
        """Offer support after clarification and enqueue only with consent."""
        quote = validate_quote(
            context=context, request=request, candidate=candidate, sources=sources, as_of=as_of,
        )
        if quote["behavior"] != "clarify":
            return {"status": "not_offered"}
        if consent is not True:
            return {"status": "consent_required"}
        if not all(isinstance(ref, str) and REFERENCE.fullmatch(ref) for ref in (session_id, message_id)):
            return {"status": "refused"}

        tenant, reason = context["tenant"], quote["reason"]
        key = (tenant, session_id, message_id)
        with self._lock:
            ticket = self._requests.get(key)
            if ticket is None:
                ticket = _Ticket(tenant, reason)
                if not self._queue.enqueue(ticket):
                    return {"status": "unavailable"}
                self._requests[key] = ticket
            elif ticket.reason != reason:
                return {"status": "conflict"}
            return {"status": "accepted" if ticket.accepted else "queued", "ticket_id": ticket.ticket_id}

    def deliver_next(self, *, staff):
        """Move the next ticket for the authenticated support tenant to its inbox."""
        tenant = _support_tenant(staff)
        if tenant is None:
            return None
        with self._lock:
            ticket = self._queue.take(tenant)
            if ticket is None:
                return None
            ticket.confirmation = token_hex(16)
            self._inboxes[tenant][ticket.ticket_id] = ticket
            return {
                "tenant": ticket.tenant, "ticket_id": ticket.ticket_id,
                "reason": ticket.reason, "confirmation": ticket.confirmation,
            }

    def confirm(self, *, staff, ticket_id, confirmation):
        """Accept only a delivered ticket with a valid tenant-scoped receipt."""
        tenant = _support_tenant(staff)
        if tenant is None:
            return {"status": "refused"}
        if (not isinstance(ticket_id, str) or not isinstance(confirmation, str)
                or len(confirmation) != 32 or not confirmation.isascii()):
            return {"status": "refused"}

        with self._lock:
            ticket = self._inboxes[tenant].get(ticket_id)
            if ticket is None or not compare_digest(ticket.confirmation, confirmation):
                return {"status": "refused"}
            ticket.accepted = True
            return {"status": "accepted", "ticket_id": ticket.ticket_id}
