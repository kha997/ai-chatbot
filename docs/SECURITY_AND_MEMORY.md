# Tenant threat model and controlled learning

Gate 1 design, 2026-11-21. Author: Codex lead. All controls below are requirements, **not implemented/tested security claims**. Evidence motivating controls: [official advisory dossier](OSS_DUE_DILIGENCE.md). Scope covers API, tools, stores, sessions, queues, handoff, telemetry and restoration.

## Assets, adversaries and trust assumptions

Protect tenant knowledge, customer preferences, conversations/checkpoints, staff review permissions, tool credentials, inbox routing, exports and audit integrity. Adversaries include anonymous visitors, authenticated customers, malicious tenant staff, poisoned retrieved documents, forged tool output and compromised dependencies. A tenant administrator is not a platform administrator. Host/platform administrator compromise is outside the isolation guarantee; it remains a residual high-impact operational risk.

Identity comes from a trusted authentication service; tenant membership and role come from server-side records. Anonymous users receive a tenant-bound opaque session with no private customer-memory access. Site Origin/CORS checks reduce browser abuse but are not authentication. Public site IDs never grant customer or staff permissions. No model output can modify this trust context.

## Threat/control/test traceability

The [evaluation spec](EVALUATION_SPEC.md) defines cross-pair security IDs `sec-{source}-{target}-{surface}` and within-tenant IDs `sec-{tenant}-local-{01..12}`.

| Risk | Severity if realized | Required preventive/control evidence | Test mapping / owner |
| --- | --- | --- | --- |
| Tenant ID substitution / IDOR | Critical | Bind tenant at gateway; reauthorize every read/write/action; default-deny; opaque IDs only supplemental | config-03; cross pairs all; local-02/03/05; lead |
| Session/checkpoint collision or resume theft | Critical | Server-generated canonical IDs; tenant/customer ACL before load; separate store grants; reauth on replay | cross-session; local-01/04/12; security reviewer |
| Retrieval/vector metadata bypass | Critical | Tenant-scoped credentials/index; validate source ownership before retrieval and before citation; no global fallback | cross-retrieval; QA source/injection; lead |
| Memory delimiter collision / wrong customer | Critical | Typed scope, restricted canonical IDs, independent storage boundary; never concatenate raw user input into keys | cross-memory; memory-04; adversarial separators/Unicode; lead |
| Prompt injection / tool overreach | High | Retrieved text and tool output are untrusted; schema/action checks outside LLM; fixed allowlist and egress; no shell/SQL/URL supplied by model | local-08/09/10/11; QA injection; lead |
| Unauthorized knowledge promotion | Critical | Separate reviewer identity/role; proposal hash + expected revision; no chatbot write credential; immutable audit | memory-07..12; local-06/07; knowledge owner |
| Cross-tenant cache/queue/retry | Critical | Server-generated scoped routing; signed job context; reject mismatched tenant/revision on consumption; TTL/epoch invalidation | cross-async; config-06; lead |
| Handoff account reassignment | Critical | Server-fixed tenant→account/inbox; consent, staff ACL and idempotency; no client account_id assignment | cross-handoff; integration-04..08; lead |
| Attachment/export/log disclosure | High | No arbitrary fetch/path; scoped signed URLs; bounded parser sandbox; output encoding; minimal private logs | cross-export; local-11; integration checks; lead |
| Resource exhaustion / surprise spend | High | Per-tenant quotas, byte/token/call/time limits; bounded retries; explicit budget enforcement and graceful refusal | ops-02/03; operations owner |
| Dependency/serialization exploit | High | Locked artifacts, advisory/license review, safe serialization; never trust imported checkpoints/code components | advisory regression cases; ops-05; security reviewer |
| Backup resurrects revoked data | High | Tenant-bound restore, deletion tombstones outside restored snapshot, revoke before serving, audit restore | memory-06/12; ops-04; operations owner |

A forbidden read/tool invocation fails a hard gate even if the final response hides it. Canary absence alone cannot prove access isolation. Inspect authorization events, store access and side effects. Cross-tenant writes, wrong-tenant notification, stale approval acceptance and unauthorized knowledge mutation each block release independently of answer quality.

## Memory layers and retention proposal

| Layer | Permitted content and owner | Scope | Proposed synthetic retention |
| --- | --- | --- | --- |
| Session context | Current conversation, user requests | tenant + session; authenticated customer link only if verified | 24h idle TTL, hard 7-day maximum |
| Customer memory | Explicitly consented typed preferences; correction/deletion supported | tenant + customer; no cross-tenant profile merge | 30 days unless renewed; delete on request |
| Organization knowledge | Reviewed synthetic policies/catalog facts with evidence | tenant + approved corpus revision | Versioned; retention chosen before real-data phase |
| Learning proposal | Redacted suggested correction with source and rationale | tenant + restricted reviewer queue | 30 days pending; reject/expire without promotion |

These TTLs are engineering defaults for a synthetic experiment, not legal retention policy for real customers. No identity matching, sensitive inference or shared global memory. A low-confidence preference stays session-only. All summaries/embeddings inherit the underlying scope/TTL and deletion obligations; deleting the visible record alone is insufficient.

## Promotion workflow

1. Conversation or staff input may create a **proposal**, never approved knowledge. Record tenant, author type, public/synthetic source reference, proposed diff, current corpus revision and content hash. Conversation frequency/ratings do not increase authority.
2. Validate schema, source authority, contradictions, synthetic-only status and tenant. Quarantine untrusted attachments/instructions. Reject unsupported business promises.
3. A separate authorized synthetic staff reviewer reviews evidence and exact diff. Require reviewer != proposal author, tenant membership, fresh authentication and a single-use approval bound to hash and expected current revision. An LLM judgment cannot grant this permission.
4. Build candidate corpus/index revision in quarantine. Replay affected cases plus full frozen 180-QA regression; verify all isolation/promotion hard gates. This future pipeline may not run during current scope.
5. Compare-and-swap active revision only after successful review/evaluation. If revision changed meanwhile, reject stale approval and request a new review; never silently rebase the approved payload.
6. Invalidate cache by tenant+revision epoch. Drain or reject in-flight jobs with old authority; sessions may preserve conversational text but must retrieve current approved knowledge. Record who approved what and when with before/after hashes.
7. Rollback points to prior approved revision, invalidates cache and repeats regression. Preserve incident/audit record. A revoked/deleted item remains tombstoned across rollback/backup restore and cannot reappear because an old index exists.

Delete flow: authorize scope → tombstone immediately → deny serving → purge preference, derived summaries, vectors and cache → cancel affected jobs → record purge completion; backup retention may defer physical deletion but restored copies must apply tombstones before service. Check deletion/revocation tombstones **before context assembly, checkpoint replay and preference extraction**, not only before store reads. Redact/exclude affected retained conversation/checkpoint source text; if reliable selective removal cannot be established, invalidate that session/checkpoint. A deleted preference cannot be recreated from retained text or replay; require renewed explicit consent and new authorized input. Mandatory sequence: remember → checkpoint → delete → resume/re-extract → neither recall nor recreation, including concurrent/in-flight work. Concurrent requests are tested against this sequence. No promise of instantaneous physical deletion from every backup.

## Risk register at Gate 1

| ID | Residual state | Owner | Resolution / exit condition |
| --- | --- | --- | --- |
| R1 | High: runtime isolation untested | Lead + separate reviewer | Execute all 72 security cases and relevant config/memory/handoff assertions after Gate 2 authorization; zero breaches |
| R2 | High: RAGFlow advisory applicability unresolved | Lead research | Map vulnerable code/fix to chosen artifact and review; keep RAGFlow excluded meanwhile |
| R3 | High: final transitive licenses/SBOM unreviewed | Lead | Lock artifact inventory; resolve prohibited/unknown terms before use; Owner only for contractual decisions |
| R4 | Medium: model cost/capacity unknown | Lead; Owner approves budget | Approved price/usage envelope and measured paired workload; no financial assumption now |
| R5 | Medium: external CLI auth/permission behavior unknown | Lead | Separate dispatcher approval + isolated qualification; no external prompt calls now |
| R6 | Medium: correlated Codex review blind spots | Lead | Fresh-context adversarial review now; diversify reviewer/vendor later if authorized and valuable; never label current review Kilo |
| R7 | High-impact trusted-host compromise remains | Operations/security owner | Least privilege, host hardening and backup controls before any deployment; no production claim |

Research-document merge does not waive these future execution prerequisites. No new unresolved design defect of Critical/High severity may be merged as a completed design; unmeasured runtime risk is explicitly retained, not marked passed.
