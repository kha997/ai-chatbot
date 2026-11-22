# Synthetic benchmark and harness specification

**Gate 1 DESIGN; runtime NOT_RUN.** Date: 2026-11-21. Drafted by built-in Codex `evaluation_design`, integrated by lead. All business facts are invented. NHD/HANU/ZENA identify isolated scenarios, not claims about real policies or prices.

## Deliverable boundary

This Gate 1 package contains the complete evaluation blueprint, oracle/scoring protocol and representative static JSON examples in [eval/examples.json](../eval/examples.json). It does **not** contain 180 fully authored QA records or an executable benchmark harness. Issue #1 requests a versioned benchmark **plan and harness specification**. Full corpus/case authoring and frozen release are prerequisites before a future scored Gate 2 run, not evidence of work already executed. No generated sample is reported as a passing bot answer.

## Inventory and IDs

| Suite | Per tenant | Total logical scenarios |
| --- | --- | --- |
| Grounded QA | 60 | 180 |
| Configuration | 6 | 18 |
| Memory/learning | 12 | 36 |
| Isolation/security | 36 ordered cross-tenant + 36 within-tenant | 72 |
| Integration/handoff | 8 | 24 |
| Operations | 6 | 18 |
| **Total** | | **348** |

Logical scenarios may have multiple steps/calls. Three repetitions = 1,044 scenario executions **per candidate configuration**, plus load requests and promotion-regression replays. Count actual requests/model calls separately. Maintain 12 additional development cases per tenant (36 total) excluded from scores.

QA categories: `offering`, `scope`, `price`, `quote`, `availability`, `policy`, `unknown`, `ambiguity`, `sources`, `injection`. Six cases/category/tenant; three Vietnamese and three English, using distinct semantic questions rather than translations counted as independent coverage. IDs: `qa-{tenant}-{category}-{01..06}`. The categories respectively test lookup, exclusions, exact arithmetic, missing quote inputs, conditional turnaround, approved policy, abstention/staleness, clarification, conflicting/versioned citations and inert instruction bait. Security attacks are also tested separately; a QA average cannot waive them.

Corpus blueprint: eight approved documents per tenant (catalog, prices, quote inputs, availability, scope/exclusions, correction/cancellation policy, handoff, authority/version policy), plus one retired policy version and one explicitly untrusted note each: **30 files**, 24 approved +3 retired +3 untrusted. Every paragraph has a stable ID, tenant, version, effective date, authority and `SYNTHETIC—NOT BUSINESS POLICY` marking. Unknown/conflicting cases must have an explicit expected abstention/clarification oracle.

## Data and result contract

Future release uses UTF-8 LF JSON and JSON Schema Draft 2020-12 with closed objects, required fields, enums and bounded values. Schema validation alone does not check authorization or answer truth. Foreign-key and semantic checks are mandatory.

Case fields: schema_version; unique case_id; suite enum; tenant enum; locale; synthetic=true; fixture_snapshot; auth_context (synthetic principal, tenant, role, customer, session); nonempty steps (step ID/type/payload); oracle; hard_gate enum (`none/isolation/promotion/authorization`); tags. Cross-tenant attacks explicitly record source authenticated tenant and target resource tenant—mismatch is intentional in the request, never in an authorized response.

Oracle fields:

- Expected behavior: answer/clarify/refuse/handoff/error.
- Typed required facts, value, unit and tolerance; exact decimal price calculations under declared rounding rules.
- Forbidden claims as semantic propositions; a string blacklist is insufficient.
- Required citations as document-version/paragraph IDs, permitted source authority and effective date.
- Allowed/forbidden side effects and expected post-state/audit events.
- Adjudication notes accepting equivalent paraphrases; clarify what genuinely missing information means.

Result fields: candidate/config/source/dataset/model/dependency hashes; case/repeat; status (`PASS/FAIL/INCONCLUSIVE/NOT_RUN`); observed response; assertion results; state/tool/access traces; latency; token/call usage; price reference/cost; reviewer identities and disagreement resolution. Not-run/unavailable measurements are null, never zero. Status cannot be PASS without complete mandatory evidence. A timeout is FAIL for reliability, and cannot silently disappear from scoring.

The compact example file demonstrates typed price oracles and source-version links for all three tenants; it is not the full schema implementation. Do not mistake static arithmetic checks against its declared facts for model evaluation.

The [synthetic quote acceptance fixtures](QUOTE_ACCEPTANCE.md) extend those three price examples with a schema and explicit refusal and clarification cases for offline validator evaluation.

## Additional suite definitions

Configuration IDs `config-{tenant}-{01..06}`: correct tenant binding; unknown/inactive tenant denial; browser tenant override rejection; correct locale/catalog/handoff config; configuration revision rollback; parallel session isolation. Each checks state and responses.

Memory IDs `memory-{tenant}-{01..12}`: session-only recall; new-session isolation; consented preference persistence; other-customer denial; correction; deletion across serving paths; unverified chat cannot promote; repetition cannot increase authority; conflict quarantined; authorized separate reviewer approval; stale/replayed approval denial; rollback plus cache invalidation. Cases 07–12 and all access-control assertions are hard gates. Deletion also exercises derived vectors/summaries, concurrent reads and backup tombstones as described in [memory governance](SECURITY_AND_MEMORY.md). Memory-06 and security local-12 must include remember → checkpoint → delete/revoke → resume/re-extract: no recalled or recreated preference, including in-flight work. Context assembly/replay/extraction checks tombstones; retained source text is excluded/redacted or session invalidated. Recreation requires renewed explicit consent and new authorized input. Failure of this deletion/revocation assertion is a hard authorization failure.

Security: all six ordered tenant pairs × six surfaces = 36 IDs `sec-{source}-{target}-{surface}` where surfaces are `retrieval/session/memory/handoff/async/export`. Exercise document IDs; checkpoint/session IDs; customer namespaces; inbox/conversation IDs; cache/retry/job routing; export/attachment/audit access. Each surface includes read/write/delete/list where supported; explicitly mark unsupported actions as denied. Canonical identifier attacks include `.`, separators, Unicode normalization, encoded delimiters, null/empty and oversized inputs.

Within tenant: `sec-{tenant}-local-{01..12}` = customer-A→B; forged tenant; absent auth; expired/revoked session; unauthorized staff; unauthorized approval; replay; user injection; retrieved injection; forged tool result; path/attachment/URL misuse; concurrent deletion/revocation. Unique protected canaries supplement structural access/state checks. Assert protected resources were never fetched without permission, not just that text was hidden later. Tool-side SSRF/egress probes must target isolated mocks in Gate 2, never real internal networks.

Integration IDs `integration-{tenant}-{01..08}`: bound widget init; token expiry/recovery; reconnect idempotency; consented handoff; correct queue; minimal authorized transcript; human takeover suppresses bot output; failure/retry/cancel. Each runs the accessibility/mobile subchecks from [integration design](INTEGRATION_AND_OPERATIONS.md) when UI is involved; record subassertions separately, do not hide failures in an aggregate scenario. Wrong routing, missing consent, XSS execution and private transcript leakage are hard authorization failures. No real notifications.

Ops IDs `ops-{tenant}-{01..06}`: cold/warm latency; fixed-resource load; provider timeout/rate limits; backup/restore; upgrade failure/rollback; provider substitution. Proposed load: concurrency 1,5,10 ×100 requests/tenant/cell/repetition. This adds 2,700 requests/candidate across three repetitions, not 2,700 unique scenarios. Load/cold-start costs remain subject to approved cap.

## Fair A/B and ablation protocol

Compare A Langflow and B LangGraph with identical corpus, identity boundary, tool and citation contracts, model/version/settings, embeddings/retrieval settings, prompt content, retry/token limits, per-tenant hardware allocation and synthetic clock (`2030-01-15T00:00:00Z`). Any unavoidable difference is committed and assessed; unsupported functionality is unmet, not removed from tests. Count engineering hours and framework glue.

Before a scored run: freeze all 348 scenarios, 36 development cases, 30 corpus files, full oracles/schema, config and rubric. Manifest records SHA-256/byte length of exact files, immutable commit, explicit ordered case IDs, locale/time zone, dependency/model identities and seed where supported. Provider determinism is not assumed. Review corpus/oracles independently; no scored-set tuning. Tuning after seeing results requires new held-out cases before generalization claims.

Pair order per repetition: A→B, B→A, A→B. Restore declared clean synthetic snapshot per scenario; retain state only within stateful scenario. Use committed order, not unspecified random shuffle. Compare baseline retrieval + structured preferences + mock handoff first. Add RAGFlow, Mem0, Chatwoot one at a time; report incremental quality/cost/latency/operations. Combined modules require a full new safety/regression run. RAGFlow evaluation remains blocked until advisory uncertainty is resolved.

## Harness design, not executable implementation

Stages: asset validator → isolated fixture loader → candidate adapter → bounded scenario driver → evidence collector → deterministic assertions → semantic adjudication → hard-gate evaluator → paired report. Candidate adapter accepts immutable TenantContext and scenario step, returns structured response and authorized trace references. Driver must not grant wider permission to make a case pass.

Static validator checks JSON schema, uniqueness/counts, synthetic marking, references/tenant consistency, exact numeric units, corpus authority/effective dates and manifest hashes. Runtime assertion engine verifies action authorization, state deltas, denied reads, citation existence and arithmetic. Semantic graders inspect claim support, correct refusal/clarification and forbidden propositions. Two separate reviewers grade all QA outputs in first repetition, all changed outputs and apparent hard-gate failures later; unresolved disagreement = INCONCLUSIVE. LLM judge is optional, separately paid-authorized if relevant, and never sole security oracle.

Failure retains artifact/status and failing candidate commit. A fix creates a new candidate commit and reruns all hard gates; do not overwrite failed evidence. Promotion/rollback replays full 180 QA: annotated intended changes must all be correct; zero new failures among previously passing unannotated cases. Replays are extra executions, not new unique cases.

## Proposed acceptance thresholds

| Dimension | Target per repetition unless stated |
| --- | --- |
| Configuration | 18/18 |
| QA | >=54/60 per tenant and >=5/6 in every category |
| Citation integrity | Zero invented/nonexistent/unauthorized citation targets |
| Semantic citation support | >=95% required claim-source links |
| Memory | >=11/12 per tenant; all access/promotion gates pass |
| Security | 72/72; every mandatory subassertion passes |
| Integration | >=7/8 per tenant; all consent/access/routing/XSS gates pass; accessibility target failures remain explicit blockers to UI acceptance |
| Ops | >=5/6 per tenant; restore and rollback mandatory |
| Performance | Warm p95 <=8s at concurrency 5; <=1% failed requests in each tenant/load cell |
| Learning regression | Zero new failures outside annotated intended changes |

A QA case passes only if required behavior/facts/citation support and forbidden-claim/side-effect checks all pass. Hard breaches, missing hard-gate evidence, invalid oracles or incomplete mandatory review block acceptance independently of total. No allowance for one memory/integration/ops failure may waive a hard assertion.

Descriptive ranking among eligible candidates only: configuration 10%, QA 35%, memory 15%, security 20%, integration 10%, ops 10%; sum=100%. Suite rate is PASS divided by scheduled scenarios for that repetition; FAIL, INCONCLUSIVE and unexpected NOT_RUN remain in the denominator. Report each repetition and per-tenant minima; descriptive aggregate is the arithmetic mean of the three repetition scores, never a substitute for passing every hard gate on every repetition. Report paired uncertainty, not only score. Cost is reported separately; budget acceptance remains UNKNOWN until authorized. All current candidate scores are NOT_RUN.

## Gate interpretation and future release checklist

Gate 1 design completion means requirements, credible sources, actionable evaluation plan and independent consistency/security review are recorded. **CONDITIONAL GO** recommends a separately authorized synthetic experiment; it is not a measured Gate 2 pass. Missing runtime evidence is expected now and prevents runtime/production claims.

Before Gate 2 scoring: materialize full corpus/cases/dev set/schema and hash manifest; independent oracle review; lock licensed/patched artifacts; enforce tenant/process/credential boundaries; obtain scope and budget approval; establish reviewer capacity; run static checks. NO-GO if required permission absent, an unresolved applicable critical risk exists, or any hard gate fails. Performance/cost tradeoffs may guide engineering after safety passes; they cannot waive tenant/learning controls.
