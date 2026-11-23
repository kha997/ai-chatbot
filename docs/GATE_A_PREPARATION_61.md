# Gate A preparation — Issue #61

Date: 2026-11-23 (Asia/Saigon). Authority: [Issue #61](https://github.com/kha997/ai-chatbot/issues/61), documents only. Accepted architecture: [PR #60](https://github.com/kha997/ai-chatbot/pull/60), merge [24d8fb46f7726e42bcce4bb48904e6f8738250d7](https://github.com/kha997/ai-chatbot/commit/24d8fb46f7726e42bcce4bb48904e6f8738250d7). Historical documents retain their pre-merge receipts; this dossier records the current baseline.

## Authorization and preparation plan

One branch `codex/issue61-gate-a-preparation`, one dedicated worktree, one PR. Only Markdown under `docs/` changes. No implementation, fixtures, installation, model/API execution, embeddings, account connection, paid service, business data, integration or deployment. The explicitly requested fresh-context Codex document review is a review subtask in this session environment, not a provider experiment or CLI model invocation.

1. Inspect accepted architecture, fixture contracts and public official model documentation; freeze evidence and distinguish facts from assumptions.
2. Draft complete case inventory/oracle plan, privacy boundaries, request allocation, cost controls, proposed manifest and future approval packet. Keep absent corpus and runtime controls visibly blocked.
3. Run offline document/scope/link/count/arithmetic checks, freeze a technical commit and obtain independent fresh-context Codex review. Resolve findings on this same branch; publish review and status. Wait for Architecture Acceptance; do not merge.

Design choice: retain ADR-002's Python state machine, tenant-scoped lexical retrieval and deterministic authority. A larger framework comparison or a reduced suite pretending to satisfy 60 independent questions would not answer this issue. New source material and executable controls require a later separately authorized step.

## Evidence boundary

The accepted 73/73 component tests and preview 5/5 are historical synthetic evidence, not rerun here. The six business E2Es, all inference, latency, usage and budget-enforcement experiments are **NOT_RUN**. The existing NHD quote corpus has one SKU; repeated versions and paraphrases do not create domain breadth. Core invariant remains **1 Core – N Tenant – N Channel – N Products/Services**; NHD first, HANU/ZENA denial canaries only.

Preparation status: **IN_PROGRESS**. Independent review and the final document checks are pending. Execution status: **NOT_RUN / NOT_AUTHORIZED**. Current approved experiment requests: **0**; approved experiment spending: **0**. The proposed 600 / US$10 envelope is inactive.

## Dossier index and acceptance map

| Issue #61 deliverable | Reviewable document |
| --- | --- |
| Vietnamese decision memo | [Owner memo](GATE_A_OWNER_61.md) |
| Complete case IDs, existing evidence versus missing corpus, oracle/scoring plan | [Corpus and evaluation](GATE_A_CORPUS_61.md) |
| Input/output allowlist, trust boundaries, T1–T13 and rollback | [Controls](GATE_A_CONTROLS_61.md) and corpus adversarial table |
| Model, 600-request allocation, all-in arithmetic, hard-stop/retry/concurrency design | [Budget](GATE_A_BUDGET_61.md) |
| Immutable future manifest, unresolved prerequisites and separate approval template | [Manifest](GATE_A_MANIFEST_61.md) |
| Public provider facts, versions/access dates versus assumptions | [Source ledger](GATE_A_SOURCES_61.md) |
| Offline validation and independent reviewer findings/rechecks | [Review receipt](reviews/ISSUE_61_PREPARATION_REVIEW.md) |
| Milestone state / exact branch and PR | [Status](STATUS.md), [PR #62](https://github.com/kha997/ai-chatbot/pull/62) |

Ready means the documents are consistent and independently reviewed with execution blockers visible; it never means the synthetic corpus or runtime controls already exist. The known remaining work is a separate authorization decision, not scope silently added to this PR.
