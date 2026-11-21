# Website, mock tools, handoff and operating-cost protocol

Gate 1 specification only, 2026-11-21. Author: lead Codex, incorporating Codex evaluation-design input. No website, inbox, API service, provider or shared infrastructure was contacted or modified for integration tests.

## Widget and API contract

Use a framework-neutral embeddable widget with a server-owned tenant configuration and a narrow API. Initial examples use only synthetic/local origins; no NHD/HANU/ZENA repository changes. Suggested endpoints are design contracts, not deployed routes:

| Endpoint | Input | Required behavior |
| --- | --- | --- |
| `POST /v1/sessions` | public site ID, locale, explicit memory consent | Resolve allowed tenant; issue short-lived opaque session; no private account access from public site ID |
| `POST /v1/messages` | session token, client message ID, text <=8 KiB | Reauthorize tenant/session; max 20 KiB structured response; idempotent message handling |
| `GET /v1/messages/{id}/events` | scoped authenticated resume cursor | Stream authorized message only; revalidate expired/revoked sessions; no other tenant events |
| `POST /v1/handoffs` | message/session reference, consent, idempotency key | Server-side inbox mapping; minimal authorized transcript; no real delivery in synthetic tests |
| `DELETE /v1/memory` | authenticated customer request + CSRF protection as applicable | Scoped tombstone/purge workflow; anonymous session cannot delete another customer |

Use TLS in future deployment, tight origin allowlists, HttpOnly/Secure/SameSite cookies where applicable, CSRF defense for cookie-authenticated writes, and explicit token TTL/revocation. No provider keys in widget code/localStorage. Render model output as untrusted text/sanitized Markdown; no arbitrary HTML/script. Block unsafe URL schemes and avoid automatically fetching model-generated URLs. CORS is not authorization; signed/session-bound server checks remain mandatory.

Response schema: request ID, safe status (`answer/clarify/refuse/handoff/error`), text, authorized citation objects (doc/version/paragraph), current corpus revision, optional structured quote draft, safe retry hint. Never reveal prompt secrets, framework tracebacks or raw database IDs. Proposed limits: 20 requests/minute per anonymous session and tenant-level shared quota configurable by lead; exact budget limits await approved envelope. Retry at most twice with bounded exponential backoff; never retry non-idempotent actions without idempotency key.

Widget states: closed → welcome/consent → typing → streaming → answer/clarification → handoff pending → human-owned/closed; offline/error supports retry without duplicate submission. On token expiry show session recovery; do not display another session's history from a global cache. On human takeover stop automated outbound replies, drain/ignore in-flight bot completions, and preserve ordering by server sequence.

Accessibility/mobile targets (proposed, NOT_TESTED): 320/375/768 CSS-pixel widths without horizontal scroll; 200% zoom; keyboard-only open/close/send/cancel; focus returns to launcher; labeled controls and visible focus; screen-reader announcement of final responses without streaming overload; reduced motion; touch targets >=44px; contrast >=4.5:1 for normal text; Vietnamese diacritics and English; visible errors and consent. Test screen reader and mobile virtual keyboard occlusion. These are acceptance targets, not certification of conformance.

## Synthetic tool contracts

`product_search`: typed query/category/limit<=10; backend selects NHD-only synthetic catalog; returns SKU/name/unit/price/currency/source revision. Reject tenant overrides, arbitrary URLs/filters and unknown IDs. `mock_quote`: SKU/service IDs, quantities, declared conditions and idempotency key; calculate decimal amounts from pinned fixture policy, return a **DRAFT, SYNTHETIC, NONBINDING** quote with expiration. No order creation, payment, email or external webhook. HANU fixture uses invented words/rate/minimum; ZENA fixture uses invented consultation package/revision limits. Never promise professional approval or legal translation validity from synthetic examples.

Tool output is validated and scoped before use. Missing/contradictory prices → clarify or staff review; do not let the LLM invent price arithmetic. Test negative/overflow quantities, stale catalog revision, wrong-tenant SKU, timeout, forged result and replayed idempotency key with changed payload.

## Handoff boundary

Adapter maps tenant to account/inbox on server; user input cannot set account_id. Future Chatwoot evaluation uses CE-only capabilities verified at the selected release. Mock workflow: `requested → queued → accepted → human_owned → closed`, with failure/cancel states. Consent stores exact transcript scope and event ID; attachments/private memory excluded by default. Replayed events are idempotent; a conflicting payload is rejected. Staff identity, account and event signature must be checked before takeover; no raw Chatwoot admin credential in the widget.

If queue fails: acknowledge unavailability, keep only permitted pending state, allow bounded retry/cancel, do not claim a human has received it. Handoff must not silently send real notifications. In Gate 2 synthetic scope, adapter network delivery stays disabled unless separately approved.

## Cost and measurement protocol

No model, hosting price or dollar budget is assumed. All measured values currently `null/NOT_RUN`, never zero. At future execution freeze official price URLs/date/currency/unit and usage model. Track every call including failed attempts, retries, memory extraction, embeddings and reranking:

`C_model = sum((uncached_input * P_in + cached_input * P_cache + output * P_out) / 1e6) + C_embeddings + C_rerank + C_other`

`C_month = compute + storage + backup + egress + observability + licenses + model + ops_hours * hourly_rate`

`C_success = allocated recurring cost / successful conversations`; denominator zero is undefined. Count failed traffic in cost numerator. Report implementation/migration effort separately from recurring cost. Module increment = matched cost with module minus matched baseline; pair with quality/latency/resource changes.

Planning volumes: 1,000 / 10,000 / 100,000 conversations/month, explicitly hypothetical. For each, declare turns/conversation, input/output tokens, ingestion volume, cache-hit ratio, retention, peak concurrency and staffing. Provide low/base/high sensitivity cases rather than claiming framework choice alone fixes price. Owner approves a finite spending envelope before any paid calls; lead selects technical options inside it.

Future measurement rows: candidate/config/commit/dependency/model/corpus hashes; run/repeat/tenant/case; timestamps; latency to first token and completion; status/retries; tokens/call counts; price reference; CPU/RSS/disk/queue depth; rubric result; operator minutes; usage gaps. Unknown provider usage is `UNKNOWN`, not estimated as free.

Compare A/B at identical per-tenant resources and workload: concurrency 1/5/10, 100 requests per tenant per cell per repetition, 3 repetitions. Separate cold/warm runs and include parsing/indexing time. Record actual host/OS/runtime versions and background contention. Proposed target: warm p95 <=8s at concurrency 5; error <=1% in each tenant/load cell. Report distributions and minima, not just overall averages. No capacity or cost result exists yet.

Measure from client request dispatch to first visible token and to final completed response using monotonic clock; include gateway, queue and retries. Declare a 30-second request deadline for the synthetic load profile. Sort successful-request durations and use nearest-rank p95 at index ceil(0.95*N), one-based; if no successes, p95 is undefined. Report failures/timeouts separately with count, elapsed time and outcome, and an all-request completion distribution with timeouts censored at the deadline. Never drop failed/time-out requests from the reliability denominator or imply successful-only p95 proves overall latency acceptance. Both latency and <=1% failure targets must pass in each declared cell.

## Backup, rollback, portability and upgrades

Future synthetic targets: RPO <=24h; RTO <=60min. Backup covers tenant DB, object corpus, vector index rebuild inputs, configuration revisions and approval/audit records, with independently controlled credentials and encryption. Restore one tenant into isolated target; apply revocation/deletion tombstones before reads; verify source hashes, authorization and regression cases. A successful backup command is not restore proof.

Upgrade sequence: pin SBOM/license/advisories → snapshot → isolated migration rehearsal → full hard gates and QA regression → separately authorized activation → monitor → rollback app/config/corpus revision together. Backward-incompatible database migration requires a tested restore path; downgrading a package alone is not rollback. Never change live Docker/VPS under this task.

Export formats: versioned JSON for tenant config/preferences and document metadata; original synthetic source files; provider-neutral tool/citation API. Keep database-specific checkpoints behind an adapter; migration may require session restart and must be documented. Test provider substitution without relaxing the oracle. Proposed recovery from provider outage: bounded retries → safe refusal/handoff mock, not unapproved paid fallback.
