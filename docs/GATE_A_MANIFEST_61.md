# Gate A immutable manifest and future signoff packet

Date: 2026-11-23. **PROPOSAL ONLY — PENDING_OWNER_APPROVAL. No runnable configuration, credentials or execution permission.** [Owner memo](GATE_A_OWNER_61.md) · [Cases](GATE_A_CORPUS_61.md) · [Controls](GATE_A_CONTROLS_61.md) · [Budget](GATE_A_BUDGET_61.md).

## 1. Proposed manifest fields

Future manifest must be a versioned immutable record, signed off against its exact content SHA-256 and accepted Git commit. Serialize future records as canonical UTF-8 LF bytes; specify canonicalization version, algorithm and byte lengths. Hash exact Git blob bytes for existing source artifacts; use path+SHA+length, no platform checkout newline ambiguity. Signature/approval receipt is detached from the hashed payload to avoid circular self-hashing. Any source/model/prompt/oracle/fee/boundary change invalidates approval; no moving `main` pointer substitutes for a frozen SHA.

| Field | Proposed value / current state |
| --- | --- |
| manifest_schema / run_id | `gate-a-proposal-v1` / `GA61-SYNTHETIC-001-PROPOSED`; not an execution ID or reusable authorization |
| preparation baseline | `24d8fb46f7726e42bcce4bb48904e6f8738250d7`, PR #60 |
| future accepted main / candidate SHA | UNKNOWN; freeze exact reviewed implementation after separate authorization, not today's docs SHA |
| future manifest SHA / approval receipt | UNKNOWN / PENDING_OWNER_APPROVAL |
| fixture/oracle/schema/source inventory | Each: path, SHA-256, byte length, schema version, synthetic flag, author, independent reviewer, provenance/rights, tenant, active revision, effective time, allowed scope; expanded inventory UNKNOWN |
| prompt/config/dependency artifacts | Exact SHA-256, tokenizer/framing version, schema, adapter and renderer hashes, dependency/license/security lock; UNKNOWN, not installed |
| provider/model | Proposed OpenAI direct / `gpt-5.4-mini-2026-03-17`, no aliases/fallback; actual availability UNKNOWN |
| provider account/project / credentials | UNKNOWN / PENDING_OWNER_APPROVAL; future restricted reference only, no account ID/key in public manifest |
| API key custody / operator | UNKNOWN; proposed dedicated least-privilege key available only to approved budget gateway, revocation custodian named before activation |
| provider terms/data controls | UNKNOWN / PENDING_OWNER_APPROVAL; exact applicable terms/version, retention/opt-in and data handling evidence required |
| region/host | Proposed global processing, no specific-country residency assurance; `api.openai.com:443`, `/v1/responses` only; actual permitted region UNKNOWN / PENDING_OWNER_APPROVAL |
| isolation/network | Isolated local synthetic worker/store, no public listener or persistent service; gateway-only inference egress, no foreign tenant grants, no tools/telemetry exports; implementation UNKNOWN |
| permitted input/output | Exact allowlist/schema hashes from controls document; synthetic/public rights-approved text only; both call stages captured; full approved payload hashes UNKNOWN |
| time | Synthetic source clock `2030-01-15T00:00:00Z`; independent monotonic deadline clock; actual start/end UNKNOWN, <=2h approval window proposed |
| model config | Reasoning none; standard tier; store false; non-streaming foreground; tools absent; <=8000 billed input /1000 total billed output per attempt, <=2 logical stages/turn or entire journey, no hidden repairs |
| request allocations | QA240/dev24/adversarial48/journeys24/performance200/contingency64, total <=600, no automatic transfers; zero-egress paths zero calls |
| concurrency / retries | Default1; performance five turns, <=5 total in-flight requests including retries; no automatic retry, <=1 eligible retry per logical stage (<=4 physical attempts/execution), <=64 shared contingency. Retry debits contingency+global once, retains origin-suite metric tag, never replaces first scored result |
| monetary envelope | Proposed <=US$10 all cash/fees, $8 admission stop-loss +$2 unavailable contingency; inactive; verified per-call/fixed fees/rates/tax UNKNOWN |
| account protections | Hard account/project limit and no other spend routes/top-up/fallback to be verified; alert alone insufficient; protection proof UNKNOWN |
| price evidence validity | Rate source/access timestamp, applicable invoice rules, bounded run-window price guarantee or conservative enforceable maximum, all fee upper bounds; UNKNOWN |
| corpus order/split | Complete IDs from case ledger; two QA repetitions, frozen order/seeds/semantic families, disjoint dev set; exact ordered payload/oracle files UNKNOWN |
| performance | 100 turns, <=200 initial attempts plus eligible retries charged to shared64 contingency (<=264 performance-origin attempts, not extra quota); p95<=8s at five concurrent turns, <=1% failed physical attempts including retries; bounded descriptive sample, not production SLO proof |
| evaluator roles | Corpus author, implementer, two independent semantic evaluators, security reviewer, operator, Owner; named actual assignments UNKNOWN |
| stop controls | Atomic STOP flag, permit revocation, no replay after crash, five-flight reservation, key revocation and billing reconciliation; evidence NOT_RUN |
| retention/evidence | Proposed local synthetic content7d/audit30d; public only sanitized approved receipts; provider retention separate; exact approval UNKNOWN |
| rollback | No provider egress; restore deterministic mock with tombstones, preserve all failure and billing reservations; drill NOT_RUN |
| execution / usage / spending | NOT_RUN / UNKNOWN runtime usage / no experiment spend authorized or incurred by this preparation |

## 2. Blocker and prerequisite register

| ID / severity | Present condition | Required closure and owner |
| --- | --- | --- |
| BLOCKED_CORPUS_BREADTH — HIGH | Single NHD SKU, no frozen 60 independent QA/oracles | Later authorized independent synthetic corpus authoring, provenance/diversity review; lead + corpus reviewer |
| BLOCKED_COST_CONTROL — HIGH | Gateway, all-in fees, input framing bound, exclusive account and bounded rates unproved | Later authorized implementation, offline race/crash/bypass evidence, account-side protections and independent security review; lead |
| BLOCKED_PROVIDER_TERMS — HIGH | Account access, key custody, region, entitlement and applicable terms unknown | Owner-approved account/data/legal route; technical evidence prepared by lead, no secrets in public |
| BLOCKED_RUNTIME — HIGH | No integrated model adapter/renderer/state harness or full control proof | Separate implementation scope, artifact/license checks and 73 regression plus hard-gate qualification; lead |
| BLOCKED_TAXONOMY — MEDIUM | Exact v1.0 intent/stage/playbook/status reconciliation incomplete | Sanitized authorized identifiers and source-owner comparison; do not claim full taxonomy acceptance |
| BLOCKED_MEASUREMENT — MEDIUM | All AI quality, latency, inference usage and six business E2Es NOT_RUN | Future approved bounded run and independent adjudication; no production extrapolation |

These are **execution prerequisites**, not hidden work to perform under #61. Preparation can be ready with them explicitly unresolved. A missing/contradictory preparation document or unresolved High design-review finding instead requires `BLOCKED_PREPARATION_EVIDENCE`. No automatic new issue or implementation follows this PR.

## 3. Separation of approval stages

1. **This PR:** Architecture Acceptance of the documents after independent review; no execution or budget. No self-merge before this acceptance.
2. **Recommended next work, only if separately requested:** authorize synthetic fixture authoring and offline control implementation/qualification, with no model calls, account connection or spend. This cannot run automatically on accepting #61.
3. **Future execution request:** only after prerequisites close, present a fully populated immutable packet; unresolved fields mean do not ask for broad/blanket execution permission. Owner approves reserved data/access/legal/cost scope; lead chooses the technical model/implementation and reviewer challenges it.

## 4. Future Owner execution decision template — NOT SIGNED

Use only after all prerequisite evidence exists. An affirmative response to this preparation PR does not complete this template.

| Exact approval item | Value to fill before decision |
| --- | --- |
| Single-run purpose and benefit | Measure narrow synthetic Vietnamese grounded inquiry/quote/handoff behavior; no live customers or product launch |
| Accepted implementation and manifest | Exact accepted main SHA, candidate SHA, manifest SHA-256, corpus/oracle/prompt/config hashes and independent review receipts: UNKNOWN |
| Provider/model/account/region | OpenAI / `gpt-5.4-mini-2026-03-17` recommended; restricted project/key-custody reference and actual region/terms: UNKNOWN |
| Data permission | Exact hashed field allowlist and approved synthetic/public provenance; no real/private data; retention and processing terms approved explicitly |
| Network/host permission | Exact isolated host and gateway-only destination/method/path; no public endpoint, tools, embeddings, external integration or other repository/service |
| Maximum money/requests/window | At most 600 sent/reserved attempts and US$10 **all-in cash including fees**; $8 admission/$2 contingency, no renewal/top-up/fallback; exact verified fees/rates and <=2h start/end: UNKNOWN |
| Safety/stop authority | Any reviewer/operator can stop; named lead contains and reconciles; no retry on unknown usage; exact offline proof and key revocation custodian: UNKNOWN |
| Residual risk/impact | Provider retention and small-sample uncertainty, possible incomplete result within cap, irretrievable bytes already sent; no production assurance |
| Rollback | Disable admission/egress, revoke only future dedicated test credential, retain liabilities/receipts, deterministic mock; no production effect |
| Decision | APPROVE EXACT SINGLE RUN / DECLINE / REQUEST REVISION; Owner identity/date/expiry and immutable receipt: PENDING_OWNER_APPROVAL |

Independent security reviewer clearance, semantic evaluator assignments and all-in financial/account evidence must accompany the future decision. Approval can be revoked before dispatch; revocation stops remaining calls. New manifest, expired window, changed provider/terms/price or safety incident requires new review/authorization. A previous failed run's unused money/request allowance is not a new permit.
