# Local synthetic session boundary — Issue #55

Authorization: [Issue #55](https://github.com/kha997/ai-chatbot/issues/55), read 2026-11-22 (Asia/Saigon). Baseline: `c009f0bb46a74217f45f04f95b05b0fe6a0dea32`, accepted PRs #50, #52 and #54. Baseline command `py -B -m unittest discover -s tests -p 'test_quote*.py' -v`: 43 passed.

## Design and execution plan

Lead decision: add `scripts/quote_sessions.py`, a standard-library ephemeral authority and narrow adapter. Keep quote math and the core handoff unchanged. Reject self-asserted contexts at the adapter. A real identity provider and durable session store are outside this authorization; modifying core contracts would unnecessarily disturb accepted behavior.

- [ ] Write adversarial `tests/test_quote_sessions.py`; observe RED before implementation.
- [ ] Implement opaque handles, fixed tenant/role/actor/session records, controlled expiry and revocation. Use only trusted Python setup for issuance, never HTTP input.
- [ ] Pin the bundled positive fixture records inside the adapter. Resolve sessions before quote, consent, ticket status, queue delivery, inbox and confirmation. Bind customer ticket access and idempotency to the issuing session. Reject changed replays and all extra authority fields with a uniform denial.
- [ ] Keep the accepted preview usable and label its scenario selector explicitly. No session issuance HTTP endpoint. Retain all 43 accepted tests.
- [ ] Run current quote CI suite without egress, record exact results, freeze technical SHA, obtain fresh-context independent Codex review, fix findings, publish one PR.

Review focus: malformed JSON-like inputs; tenant swaps including valid foreign handles; same-actor different-session replay; expired/revoked staff access after delivery; mutable response data or attempted canonical source replacement.

## Trust and limitations

The caller passes an opaque bearer handle and an expected tenant/resource scope. Tenant/role in a request never grants authority. Handles are generated with `secrets`; records and tickets are process-local. Trusted fixture/admin code can issue and revoke; that code and the Python process are inside the trust boundary. Local callers able to execute arbitrary Python can bypass it. Possession of a valid handle represents its synthetic principal, not proof of a real person's identity.

The existing preview is a curated developer test harness, not a customer or staff access channel. Its tenant and wrong-role controls select predefined synthetic scenarios; they do not authenticate anyone. The new boundary is exercised through its offline adapter API. No public login or session issuance route is added.

Tokens, sessions, consent, tickets and revocation **do not survive process restart**. No real authentication/authorization claim, persistent services, external identity provider, database, delivery, model calls, new dependencies or spending. Dispatcher, Gate 2 and production remain NO-GO. This local simulation grants no permission to interact with real users.

## Evidence

Implementation, review and final CI: pending. Exit status not yet asserted.
