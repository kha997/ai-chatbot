# Local synthetic session boundary — Issue #55

Authorization: [Issue #55](https://github.com/kha997/ai-chatbot/issues/55), read 2026-11-22 (Asia/Saigon). Baseline: `c009f0bb46a74217f45f04f95b05b0fe6a0dea32`, accepted PRs #50, #52 and #54. Baseline command `py -B -m unittest discover -s tests -p 'test_quote*.py' -v`: 43 passed.

## Design and execution plan

Lead decision: add `scripts/quote_sessions.py`, a standard-library ephemeral authority and narrow adapter. Keep quote math and the core handoff unchanged. Reject self-asserted contexts at the adapter. A real identity provider and durable session store are outside this authorization; modifying core contracts would unnecessarily disturb accepted behavior.

- [x] Write adversarial `tests/test_quote_sessions.py`; observe RED before implementation.
- [x] Implement opaque handles, fixed tenant/role/actor/session records, controlled expiry and revocation. Use only trusted Python setup for issuance, never HTTP input.
- [x] Pin the bundled positive fixture records inside the adapter. Resolve sessions before quote, consent, ticket status, queue delivery, inbox and confirmation. Bind customer ticket access and idempotency to the issuing session. Reject changed replays and all extra authority fields with a uniform denial.
- [x] Keep the accepted preview usable and label its scenario selector explicitly. No session issuance HTTP endpoint. Retain all 43 accepted tests.
- [ ] Run current quote CI suite without egress, record exact results, freeze technical SHA, obtain fresh-context independent Codex review, fix findings, publish one PR.

Review focus: malformed JSON-like inputs; tenant swaps including valid foreign handles; same-actor different-session replay; expired/revoked staff access after delivery; mutable response data or attempted canonical source replacement.

## Trust and limitations

The caller passes an opaque bearer handle and an expected tenant/resource scope. Tenant/role in a request never grants authority. Handles are generated with `secrets`; records and tickets are process-local. Trusted fixture/admin code can issue and revoke; that code and the Python process are inside the trust boundary. Local callers able to execute arbitrary Python can bypass it. Possession of a valid handle represents its synthetic principal, not proof of a real person's identity.

The existing preview is a curated developer test harness, not a customer or staff access channel. Its tenant and wrong-role controls select predefined synthetic scenarios; they do not authenticate anyone. The new boundary is exercised through its offline adapter API. No public login or session issuance route is added.

Tokens, sessions, consent, tickets and revocation **do not survive process restart**. No real authentication/authorization claim, persistent services, external identity provider, database, delivery, model calls, new dependencies or spending. Dispatcher, Gate 2 and production remain NO-GO. This local simulation grants no permission to interact with real users.

## API and authority ownership

Trusted setup creates `SessionAuthority(clock=...)`, calls `issue(tenant=..., role=..., actor_id=..., lifetime=...)`, and constructs `SessionQuotes(authority)`. Only allowlisted `customer`/`support` and NHD/HANU/ZENA can be issued. The default lifetime is one hour; trusted setup may choose 1–86400 seconds. `revoke(handle)` is a trusted admin operation. No user input feeds these calls through a route. Session IDs are independently generated even when the synthetic actor is the same.

All protected calls take `(handle, tenant, ...)`. `tenant` is the expected resource scope: it must match the record and cannot change the record. The authority lock covers resolution and the complete operation, including revocation ordering. Requests accept only string `sku`, `quantity`, `unit`, `currency` fields, capped at 128 characters. The SKU must match the resolved tenant's pinned baseline. The optional untrusted candidate must exactly match the canonical source/version/citation; it is never passed through as authority. Only the bundled positive case's tenant-filtered source is passed to the core. The fixed synthetic valuation date is `2030-01-15T00:00:00Z`; this is independent of the injectable monotonic session clock.

| Operation | Required role | Additional boundary |
| --- | --- | --- |
| `quote(handle, tenant, request, candidate=...)` | customer | Canonical catalog; no caller context or source list |
| `handoff(..., message_id=..., consent=...)` | customer | Explicit Boolean true; exact same-session replay only |
| `ticket_status(handle, tenant, ticket_id)` | customer | Ticket belongs to this exact session and tenant |
| `deliver_next(handle, tenant)` | support | Dequeues only the resolved tenant |
| `inbox(handle, tenant)` | support | Copies only this tenant's delivered ticket summaries |
| `confirm(handle, tenant, ticket_id)` | support | Delivered ticket belongs to this tenant; proof stays inside adapter |

Denied authorization/catalog/malformed requests return exactly `{"status": "denied"}`. Valid customers may receive clarification or consent-required outcomes, but these have no price/citation/ticket details. Approved same-tenant support sessions can confirm a ticket delivered by another same-tenant support session: support authority is tenant-scoped, not tied to one staff member. A new customer session cannot see an old session's ticket even for the same actor. A replay with no explicit consent never reuses prior consent; a changed request under the same message ID is denied.

## Threat and remaining risk register

| Threat or limitation | Result / owner / mitigation |
| --- | --- |
| Forged tenant, role, context, session ID or source | Denied before core invocation; lead-owned adapter tests |
| Stale, foreign or customer handle used for staff actions | Denied without queue consumption or ticket data |
| Foreign SKU/citation or same-tenant forged revision | Denied; no foreign catalog selected |
| Customer replay / another session with same actor | Ticket and idempotency scoped to generated session ID |
| HIGH if misused as real auth | No identity verification; bearer theft permits impersonation. Owner must approve a separate real-auth phase; no such deployment is allowed |
| MEDIUM outside bounded demo | In-memory records are not durable, garbage-collected by TTL or rate-limited; restart clears everything. Lead keeps this API offline and synthetic |
| Preview harness / direct core calls | Explicitly outside the new adapter's request boundary; controlled test code can construct trusted mappings. Never expose them as real customer endpoints |
| Arbitrary local Python execution / fixture edits | Trusted process and repo are not a sandbox against local code execution |

## Validation evidence

Technical candidate: [`6a679b0d8352884e8684bdc8179e8529661dd20b`](https://github.com/kha997/ai-chatbot/commit/6a679b0d8352884e8684bdc8179e8529661dd20b), [PR #56](https://github.com/kha997/ai-chatbot/pull/56). Single author: Codex lead. No third-party code/dependencies added; accepted core and fixture files are unchanged.

- RED: `py -B -m unittest discover -s tests -p test_quote_sessions.py` — 16 failures because the session boundary did not yet exist. The temporary availability assertion was removed after implementation.
- RED: preview suite after adding disclosure assertions — 1 failure / 7 tests; corrected by the narrow visible disclosure change.
- GREEN: `py -B -m unittest discover -s tests -p 'test_quote*.py'` — **59 passed** on Windows (43 accepted, 16 new).
- GREEN no-egress: `wsl --exec unshare --user --map-root-user --net sh -c 'ip link set lo up && cd "/mnt/c/Users/Admin/.codex/worktrees/issue55-session-boundary/AI ChatBot" && python3 -B -m unittest discover -s tests -p "test_quote*.py" -v'` — **59 passed**. Private network namespace, only loopback enabled; no external interface or default route. HTTP regressions create and close their temporary loopback listener.
- `py -B -m scripts.quote_preview --help` — PASS; the existing startup entry point remains available. The seven HTTP tests exercise the existing `make_server` and actual HTTP flows. No new manual browser acceptance is claimed.
- `git diff --check` — PASS. Comparison against baseline confirms no changes to `scripts/quote_validator.py`, `scripts/quote_handoff.py`, `eval/quote_acceptance.json` or `.github/workflows/quote-acceptance.yml`.
- Unrelated retired CLI/model/Dispatcher test paths were NOT_RUN under Issue #55's NO-GO scope. Current quote-acceptance CI is the applicable project suite.

Independent review and final CI evidence pending. Exit status not yet asserted.
