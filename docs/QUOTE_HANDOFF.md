# Synthetic draft quote handoff

[Issue #51](https://github.com/kha997/ai-chatbot/issues/51) exercises a local in-memory queue and tenant-scoped support inbox on top of the [accepted quote validator](QUOTE_ACCEPTANCE.md).

| Situation | Result |
| --- | --- |
| Quote answers or refuses | `not_offered`. No ticket, amount, source or foreign-tenant detail is returned by the handoff. |
| Quote needs clarification and consent is absent | `consent_required`. No queue entry. |
| Clarification with explicit consent | `queued` after enqueue succeeds. Only a synthetic ticket ID, tenant and static reason go to the mock inbox. |
| Queue cannot accept | `unavailable`, with no ticket or automatic retry. The caller may explicitly retry. |
| Matching support confirmation after delivery | `accepted`. Both delivery and confirmation require trusted support context for the ticket's tenant. Denied delivery leaves the queue unchanged. Invalid proof or another ticket is refused with no ticket details. |

The in-process adapter trusts the caller to supply independently authenticated tenant/session and support contexts. Session and message IDs are stable synthetic references supplied by that caller. The idempotency key scopes the minimal payload by tenant, session and message. Replays with the same reason return the existing ticket and never enqueue again. A changed reason is a conflict. Plain customer data, claimed prices, raw requests, sources and citations are excluded from the payload. The delivery proof stays on the support side and repeated valid confirmations are idempotent.

Run the quote-only suite used by existing CI.

```bash
python3 -B -m unittest discover -s tests -p 'test_quote*.py' -v
```

The state is process-local and discarded on restart. A future integration would need independent tenant/session and support authentication, a server-side tenant-to-inbox mapping, verifiable consent and revocation, and durable idempotency and authenticated event verification. The current adapter has no API listener, external delivery or provider integration. Live integration, Dispatcher, Gate 2 and production remain **NO-GO**.
