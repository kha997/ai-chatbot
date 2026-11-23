# NHD MVP — cost model, roadmap and acceptance gates

Date: 2026-11-23. [Architecture](NHD_MVP_ARCHITECTURE_59.md) · [Sources](NHD_MVP_SOURCES_59.md) · [Owner memo](NHD_MVP_OWNER_59.md). All volumes, effort, staffing, exchange rate and sizing below are **planning assumptions, not NHD measurements or supplier quotations**. Published unit prices are separately cited. No spending, model request, installation or deployment is authorized by this document.

## 1. Transparent recurring cost scenarios

Default model: `gpt-5.4-mini-2026-03-17`, standard uncached input $0.75/M tokens and output $4.50/M tokens, [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini.md), checked 2026-11-23. No cache, batch, promotional or subscription credit assumed. Tokens include all requests for slot extraction and answer generation, history, instructions and evidence; output includes any billed reasoning tokens, not just visible text. Proposed reasoning `none`; verify exact usage semantics at the future test.

`C_AI = N * turns * (input_tokens_per_turn * P_in + output_tokens_per_turn * P_out) / 1,000,000 * (1 + retry_fraction)`

`C_month = C_AI + embeddings + rerank + hosting + backup + storage/egress/monitoring + software fees + ops_hours*ops_rate + handoffs*minutes_per_handoff/60*staff_rate`

`C_per_conversation = C_month / N`; `C_per_success = C_month / successful_conversations` (UNKNOWN until measured). Failed requests remain in costs and reliability denominators. The 10% allowance below is a sensitivity input, not permission to retry indefinitely. Inference spending must be reserved before a retry.

| Assumption | Low | Base | High |
| --- | ---: | ---: | ---: |
| Conversations/month N | 1,000 | 10,000 | 100,000 |
| User turns/conversation | 4 | 6 | 8 |
| Combined input/output tokens per turn | 2,000 / 300 | 3,000 / 400 | 5,000 / 600 |
| Calls per turn | <=2 | <=2 | <=2 |
| Retry/failure token overhead | 10% | 10% | 10% |
| Monthly input/output before overhead | 8M / 1.2M | 180M / 24M | 4,000M / 480M |
| Peak simultaneous turns, to test | 1 | 5 | 20 |
| Approved passages / raw corpus budget | 500 / 5 MB | 5,000 / 50 MB | 50,000 / 500 MB |
| Lexical index disk allowance (unmeasured) | 50 MB | 500 MB | 5 GB |
| Handoff share / staff minutes each | 15% / 6 | 20% / 6 | 25% / 6 |
| Ops/maintenance hours per month | 8 | 16 | 40 |

Concurrency is not inferred from monthly volume. Larger bursts, lengthy histories, uploads and complex parsing are outside these envelopes and require new measurement. Index allowances include headroom, not a measured multiplier. Default lexical retrieval adds no embedding API fee; database/search CPU is included in hosting. No paid reranker or hosted file-search tool is included.

| Monthly USD estimate | Low | Base | High |
| --- | ---: | ---: | ---: |
| Model, including 10% overhead | 12.54 | 267.30 | 5,676.00 |
| App/DB compute allowance | 24.00 | 48.00 | 246.00 |
| Backup allowance | 7.20 | 14.40 | 28.80 |
| Additional storage/egress/monitoring allowance | 10.00 | 30.00 | 100.00 |
| **Technical cash subtotal** | **53.74** | **359.70** | **6,050.80** |
| Ops labor at assumed $15/hour | 120.00 | 240.00 | 600.00 |
| Human support at assumed $5/hour | 75.00 | 1,000.00 | 12,500.00 |
| **Economic total, including labor** | **248.74** | **1,599.70** | **19,150.80** |
| Technical cash / conversation | 0.05374 | 0.03597 | 0.060508 |
| Economic total / conversation | 0.24874 | 0.15997 | 0.191508 |
| Technical cash, million VND at assumed 26,000/USD | 1.40 | 9.35 | 157.32 |
| Economic total, million VND at same planning rate | 6.47 | 41.59 | 497.92 |

Hosting reference: [DigitalOcean Basic regular](https://www.digitalocean.com/pricing/droplets), checked 2026-11-23: 2-vCPU/4-GiB $24/month; 4-vCPU/8-GiB $48/month; daily percentage backup 30%. Low/base assume one VM with local DB and explicitly accepted pilot outage risk; high assumes two $48 app VMs plus **$150 managed-DB allowance (not a verified quote)**. High backup line covers app VM snapshots; managed DB backup/PITR pricing is UNKNOWN and must fit or increase the $150 allowance after procurement. Extra storage, monitoring and egress are allowances, not guaranteed vendor packages. Compute sizing does not imply proven capacity or regional availability. Production managed DB/redundancy may be needed even at low traffic if continuity requirements demand it.

Tax, FX spread, domain, contracted SLA/security/legal assessment, third-party inbox seats, long-term media storage and any existing staff opportunity cost beyond the stated hours are excluded. Support hours total 15/200/2,500 monthly: high traffic is a staffing challenge, not only an AI token bill. Existing salaries may reduce incremental cash, but not effort. Use a 20% planning contingency on technical cash: approximately $65/$432/$7,261; these are **not approved budgets**. At a verified NHD volume, lead recalculates before recommending an actual cap.

## 2. Sensitivity and alternatives

| Change holding workload constant | Effect |
| --- | --- |
| Double average context | Input cost doubles: base model cost rises from $267.30 to $415.80 including overhead |
| Double output | Base model cost rises to $386.10 |
| 0% rather than 10% overhead | Base model cost $243.00; 30% overhead gives $315.90 |
| Handoff share +10 percentage points | +$50/$500/$5,000 staff cost at stated volume and minutes/rate |
| GPT-6.1 Terra at $1/M input, $5/M output | Same-token estimate $15.40/$330.00/$7,040.00; quality/actual tokens UNKNOWN |
| Gemini 3.5 Flash-Lite at $0.30/M input, $2.50/M output | Same-token estimate $5.94/$125.40/$2,640.00; tokenizer/quality differ, so this is not measured savings |
| Optional embeddings at $0.02/M input tokens | Example 2M-token initial corpus $0.04; 60,000 queries x100 tokens = $0.12/month; reindex/retries/storage extra |

Model/embedding sources: [GPT-6.1 Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra.md), [Gemini pricing](https://aistudio.google.com/docs/pricing), [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small.md), checked 2026-11-23. No provider signup or quota verification occurred. Lower list price alone is insufficient to replace the default; compare the same held-out Vietnamese cases and hard gates. Default model wins provisionally on bounded scope, dated snapshot and documented structured-output interface, not on demonstrated superiority over Gemini.

Cheapest safe non-AI option: approved searchable FAQ plus deterministic inquiry/quote form, zero model tokens, human completion. It does not meet the natural-language MVP promise but is the outage/budget fallback. Hosted default removes GPU management and keeps local footprint small; it introduces provider availability, data-processing and spending dependencies.

Local alternative: existing Ollama 0.31.1/Qwen3:14B artifacts do not prove usable capacity. Historical admission is blocked; no service is accessed here. Illustrative power only: 0.15–0.35 kW incremental draw x240 hours x3,000 VND/kWh = 108,000–252,000 VND/month; at 720 hours = 324,000–756,000 VND/month. These watts/tariff/hours are assumptions, not measured draw or a current electricity quote. Add hardware depreciation, cooling, backup, connectivity and 8–20 extra ops hours/month ($120–300 at the assumed rate). Existing hardware is a sunk purchase, not free throughput or production availability. Hardware procurement cost, tokens/sec, concurrency and cost per successful answer remain UNKNOWN; no local-vs-hosted break-even claim is justified.

## 3. Investment and sequence

Effort estimates are lead judgment for one engineer with part-time QA/security review and responsive NHD approver. One person-day =8h. Technical estimates include independent review/rework; customer-domain preparation is separate. No developer subscription is treated as free/unlimited labor or API credit. Ranges are not commitments, bids or a delivery date.

| Phase after acceptance | Deliverables / dependencies | Technical effort | Exit / rollback |
| --- | --- | ---: | --- |
| A — future bounded synthetic AI slice | Freeze NHD synthetic corpus/oracles, provider adapter and explicit state machine, lexical retrieval, reuse quote invariants, mock handoff, spend/usage controls; approved provider/test budget required | 5–8 days | A gates below. Stop requests, revoke test key, retain sanitized receipt, return to deterministic mock; no infrastructure or business data |
| B — internal NHD MVP/pilot | Approved small corpus; dedicated DB/session/recovery, staff MFA/inbox, consent/deletion, operator ownership, backup/restore, limited authenticated UI; separately authorized data/hosting scope | 15–25 additional days | B gates below; disable AI, retain authorized operator inquiry workflow; rollback app/corpus with tombstones |
| C — controlled real website rollout / production readiness | Secure widget integration, production identity/abuse controls, incident runbook, monitored canary, managed storage/recovery, independent security review; website/data/channel access separately authorized | 15–30 additional days | C gates below; disable widget/AI feature flag, restore tested version, retain audit and process pending consented tickets |

MVP through B: **20–33 technical days**, $2,400–3,960 at assumed $15/hour; with 25% engineering contingency **$3,000–4,950 (78–128.7 million VND)**. Production path through C: cumulative **35–63 days**, with 25% contingency **$5,250–9,450 (136.5–245.7 million VND)**. NHD corpus/policy approval adds approximately 3–5 business person-days at an assumed $10/hour = $240–400, excluded from technical investment. Any external security/legal contract is unquoted and excluded. Hosting/model operations are separate recurring lines. Calendar estimate: 1–2 weeks A, another 3–5 weeks B, another 3–6 weeks C, conditional on approvals and input availability; blocked time is not engineering effort. Do not start later phases automatically.

## 4. Future Gate A proposal — synthetic AI vertical slice

**Not authorized.** After Architecture Acceptance, recommend one bounded synthetic experiment, not the full three-tenant benchmark. Proposed permission envelope: isolated local application (no public listener or new persistent service), outbound only to the selected official provider; model `gpt-5.4-mini-2026-03-17`; public/synthetic text only; no real customer records, tools, notifications or embeddings; maximum **600 model requests**, at most **8,000 input and 1,000 total billed output tokens per request**, and **US$10 maximum total including fees** (illustrative 260,000 VND at the planning FX). Budget safety reserves $0.0105/request at the observed rates: 600 calls <=$6.30 model list cost, leaving margin. Stop at whichever limit arrives first; no retry outside the envelope or paid fallback. Actual billing protection and current prices must be verified before approval can be activated. If enforceable cost protection cannot be demonstrated, BLOCKED_COST, not “best effort”.

Prepare separately reviewed immutable execution/fixture manifest before requesting that precise approval. Provider project/account, secret handling, terms and test dates must be identified then; absent now. Application budget ledger must durably reserve worst-case cost, account for parallel in-flight calls, disable auto-top-up where supported, reconcile provider usage and stop on missing usage or unknown model identity. A dashboard alert is not a hard cap. Owner approval of this architecture PR does not grant this spending/access permission.

Reserve `(input_cap * input_rate + billed_output_cap * output_rate) / 1M × applicable regional multiplier + worst-case per-request fees` before each request and also reserve fixed charges against the total. At the dated rates, $0.0105 is the standard per-call token charge and $0.01155 with the documented 10% regional uplift ($6.93 for 600). If fees, billed-token bounds or the all-in cap cannot be established, stop before test activation.

Proposed narrow suite: **60 held-out NHD semantic QA cases** (10 categories x6 from the existing evaluation taxonomy; Vietnamese accents/unaccented/paraphrases), plus 12 unscored development cases; 24 adversarial scenarios spanning T1–T13, with all applicable subassertions mandatory; 12 customer/handoff/recovery scenarios. Frozen synthetic HANU/ZENA canaries test forbidden retrieval/routing; those tenants provide no live features. Two QA repetitions =120 case executions; <=2 requests per execution =240 calls. Adversarial and journey model calls, if any, count toward 600; bounded performance sample fits remaining capacity. If incomplete within cap, report INCONCLUSIVE and stop; do not remove cases to claim PASS. No model judge required; two separate reviewers grade evidence, resolve disagreements or mark INCONCLUSIVE.

Proposed allocation to freeze before approval: 240 requests QA, 24 development, 48 adversarial, 24 journeys, 200 for 100 performance turns, and up to 64 for bounded retries or mandatory diagnostic repetitions. A path that should deny before egress must use zero of its allowance. Any increased sample size or retry still fits the same 600-request and US$10 caps or yields INCONCLUSIVE.

Pass all safety subassertions and 73 existing offline regressions; QA >=54/60 **in each repetition**, >=5/6 each category; semantic citation support >=95% of required claim-source links; zero invented/unauthorized citations and zero wrong price/approval/isolation/consent side effects. Retrieval recall@5 >=95% of answerable cases with a source oracle; report ambiguity cases separately. Latency pilot target p95 <=8s at concurrency 5, <=1% failures in a declared sample of at least100 turns; 30s deadline, timeouts counted as failures. At this tiny sample, confidence is limited; report sample size/distribution, not a production SLO. Success requires complete usage/latency/corpus/model/request evidence within cap and independent review. All thresholds are proposed, all actual AI metrics NOT_RUN.

This A scope deliberately does not claim the original 348-scenario multi-tenant benchmark or all production T1–T13 implementations passed. Features absent from A (real identity, external delivery, real data, production restore) must be explicitly denied/mocked and remain blockers for B/C. A pass means the narrow experiment worked, not that absent controls are waived.

## 5. Pilot and production acceptance

**Gate B, separately approved internal pilot:** proposed maximum 20 named internal testers, 200 conversations over two weeks, a small approved NHD corpus, no public website or real customer notifications. Default external provider use excludes customer PII until a business/privacy approval explicitly permits exact fields/region/retention. Engineer creates a private data destination; public repo remains code/synthetic evidence only. Business approver signs source/version/exclusion manifest; staff coverage and correction process are assigned. Every applicable T1–T13 control must pass including real auth, restart ownership/withdrawal, purge and restore. Mandatory restore drill RPO <=24h/RTO <=60min; no unresolved Critical/High security finding. QA/retrieval thresholds from A on fresh approved-domain held-out cases must hold; zero incorrect price promises. Operator reviews every pilot answer; >=90% domain correctness and >=80% of 200 journeys reach a correct answer, useful clarification or consented handoff, independently adjudicated. Report denominators/abandonment separately. These are proposed business targets to validate, not ROI promises.

Proposed pilot technical allowance: **$150 total for two weeks**, including model/hosting/backup and contingency, excluding separately approved labor; subset invoice assumptions must be frozen before activation. No automatic recurring renewal. Staff/data legal terms and regional processing are unresolved Owner matters. Any leakage, unapproved policy promotion, consent violation, false order claim, unknown spend or absent coverage stops AI use; lead disables feature and independent reviewer investigates. Insufficient sample/evidence means INCONCLUSIVE, not pass.

Before inviting pilot participants, freeze and pass the **200-case critical price, stock and policy suite** with zero fabricated or unauthorized claims. Also pass full pilot-scope E2E 2–4 with approved corpus and identity. Exercise E2E 1 with a second isolated synthetic canary and retain the full multi-tenant E2E as NOT_RUN until the complete configured path exists. E2E 6 must pass with authentic staff and the separately authorized inbox before enabling live human control. E2E 5 remains NOT_RUN in a pilot without an authorized real channel adapter.

**Gate C, separately approved real rollout:** Owner approves exact NHD site/channel, allowed customer fields/legal basis, provider region/terms, spending ceiling, staffing, incident contacts and rollback authority. Start proposed canary at <=5% eligible traffic for seven days, then staged increase only after engineering/security acceptance and the approved cap; never infer traffic volume from this document. Before canary: widget mobile/keyboard/screen-reader checks; XSS/CSRF and API authorization; load test at measured peak x2 without budget violations; independent security review; deletion/recovery drill; production backup/PITR target RPO <=1h/RTO <=4h. The latter trades a longer restoration window for much less data loss than pilot and requires explicit business acceptance. Availability target 99.5% monthly (about3.6h/30days downtime) and p95 <=8s are proposed SLOs, not SLAs. Validate monitoring and the error-budget policy before exposure. Same-host pilot architecture alone cannot substantiate these goals.

In controlled, separately authorized staging on the exact proposed rollout configuration, pass the 200-case critical suite and E2E 2–4, pass the isolation canaries from E2E 1, and pass E2E 5 and 6 on the exact delivery adapter and authenticated staff/inbox path. **Before any public canary exposure**, require zero unresolved Critical/High findings, zero safety breaches, staffed handoff, source-update ownership and a rehearsed kill switch. Failure or NOT_RUN on a required test blocks exposure. Maintain every entry condition for expansion and additionally meet held-out domain thresholds and seven days of monitored canary evidence. Any hard breach stops immediately. Later HANU/ZENA onboarding requires full E2E 1 and complete per-tenant gates before activation.

## 6. Risk register and decision ownership

| Risk | Severity / state | Owner and exit condition |
| --- | --- | --- |
| Architecture not accepted; no Gate 2 execution/budget/provider authority | BLOCKER to runtime | Owner: accept architecture separately from bounded Gate A permission |
| NHD source rights, price rules, traffic, staffing and success economics unknown | BLOCKER to real-data pilot | NHD business approver: approved small source sample and operating rules at B; lead handles technical mapping |
| Real identity/recovery/consent lifecycle absent | HIGH, blocks B/C | Lead + independent security reviewer: T2/T3/T7/T12 evidence |
| Injection, false support/citations, unapproved learning | HIGH, blocks AI release if failed | Lead: T4–T6/T13; independent semantic/security tests, abstain on uncertainty |
| SQLite/local predicates mistaken for production isolation | HIGH, blocks B/C | Lead: dedicated tenant DB/roles, scoped queries, migration and restore proof |
| Spend surprise or undocumented provider retention/terms | HIGH, blocks provider activation/real data | Lead verifies controls; Owner approves finite cost and permitted data processing |
| Local GPU contention/RAM/confinement | BLOCKER to Ollama route | Lead retains Issue #46 NO-GO; no need to resolve for hosted research |
| Missing whole-stack lock/SBOM, upstream advisories, edition terms | HIGH before installation/reuse | Lead pin artifacts and resolve license/advisory applicability; contractual exceptions only Owner |
| Quality, tokenization, latency/capacity unmeasured | MEDIUM now; blocks release evidence | Lead measures frozen workload after A; no public readiness claim |
| Handoff workload/after-hours ownership underestimated | HIGH commercial risk | Business operator accepts coverage; absent coverage → no response-time promise and no production launch |
| Same-family Codex independent review has correlated blind spots | MEDIUM | Fresh context/no authorship, source and arithmetic challenge; external review before higher-risk production if warranted |

Current verdict: **GO for planning; CONDITIONAL GO for requesting the bounded future synthetic experiment after prerequisites; NO-GO for current live deployment.** The next immediate Owner decision is Architecture Acceptance of PR #60, not model/library selection. No follow-up implementation PR, purchase or data request is automatically created.
