# AI ChatBot — remote status

## Gate 1.5 follow-up — Issue #14

- **STATE:** Kilo offline isolation/oracle passed. One anonymous zero-priced Kilo POST returned HTTP 200, but CLI exit 1 and no valid result or usage receipt. One extra local request was blocked. Kilo and OpenCode allowances are now spent. Qoder sent zero prompts and remains blocked on selected-model credits and isolation.
- **DECISION:** NO-GO for an autonomous dispatcher. Diagnose Kilo stream handling offline before requesting any further live attempt. OpenCode's 429 is unexplained and upstream v1/free relay compatibility warnings are documented.
- **HEAD/BRANCH/PR:** Reviewed runner commit `60d670dda3b871f79f574ba7b0e6b4f763179c7b` on `evidence/gate-15-kilo-isolation`, tracked in [PR #15](https://github.com/kha997/ai-chatbot/pull/15). [Evidence and reviewer provenance](GATE_1_5_KILO_ISOLATION.md).

## New Owner authorization — existing agent accounts (2026-11-21)

- **STATE:** Qoder sign-in verified. Qoder model test `BLOCKED_COST_OR_AUTH` and native isolation unqualified. Kilo free catalog verified, model test `BLOCKED_ISOLATION`. OpenCode Beam Free `FAIL_RATE_LIMIT`: one upstream prompt received HTTP 429 and no retry was sent.
- **OWNER-REPORTED ACCOUNTS:** Qoder Pro (paid existing subscription); OpenCode/Kilo free use (reported 200,000 tokens/day, **not provider verified**).
- **NEW SCOPE:** Codex may initiate official interactive login to existing CLI accounts; Owner must personally approve browser/device/MFA steps. No passwords/tokens in logs or GitHub. [Issue #8](https://github.com/kha997/ai-chatbot/issues/8).
- **SPEND/GATE:** 0 VND incremental purchase, at most one read-only synthetic model prompt per CLI only after individual allowance and enforceable billing controls have been verified. No scheduled model calls, dispatcher activation or Gate 2 product PoC.
- **DECISION:** NO-GO for an autonomous dispatcher. One free route reached the provider within the enforced budget and request envelope, but produced no task output. [Qualification evidence and next step](GATE_1_5_ACCOUNT_CONNECTION.md).
- **PR:** [Governance PR #12](https://github.com/kha997/ai-chatbot/pull/12) merged at `3a2b0687db88b79ef8be673df3b2dd3d468e3edc`. [Evidence PR #13](https://github.com/kha997/ai-chatbot/pull/13), branch `evidence/gate-15-existing-account-auth`. [Ollama fallback issue #11](https://github.com/kha997/ai-chatbot/issues/11) is closed.

Date: 2026-11-21 (Asia/Saigon).

## Previous Gate 1.5 preflight

- **STATE:** `BLOCKED_COST_OR_AUTH` for Qoder, OpenCode and Kilo model execution. Zero prompts of three attempted. No provider usage measured.
- **WATCHER:** updated from merged [PR #9](https://github.com/kha997/ai-chatbot/pull/9) at `c5c24a481d857571609a8bded9c0677b4808d889`. Actual scheduler poll found Issue #8 approved for Codex and confirmed Issue #5 absent. The 30-minute read-only task remains active.
- **RECOMMENDATION:** **NO-GO** for a dispatcher. Recommended first follow-up is one OpenCode qualification with verified existing access or a separately approved public zero-price route. Recommended new-purchase ceiling 0 VND, with provider-side enforcement and completed isolation required.
- **EVIDENCE:** [Gate 1.5 qualification and next authorization](GATE_1_5_QUALIFICATION.md). Separate Codex reviewer `gate15_review` reviewed PR #9. Lead Codex verified Windows scheduling and CLI diagnostics. Branch `evidence/gate-1-5`.

## Issue #5 local setup

- **CLI installed/reused:** Qoder native 1.1.94 and Kilo native 7.8.32 are installed in project-specific user-local directories. OpenCode 1.18.30 was reused in WSL. Codex informational subprocess probes passed. Authentication, quotas and prompts remain unverified. [CLI evidence and rollback](AGENT_CLI_READINESS.md).
- **Watcher active:** one limited interactive Windows task, `AIChatBot-GitHubWatcher`, public GET access to this repository, interval PT30M, hard limit PT2M, overlap ignored. Automatic trigger succeeded at 10:03:05 local after restoring the task. [Design and runbook](GITHUB_WATCHER_DESIGN.md).
- **Live validation:** see the [commissioning record](reviews/ISSUE_5_COMMISSIONING.md) for local task results, duplicate handling, pause, restore and uninstall. Five deterministic tests passed.
- **Review:** separate Codex `issue5_review` session approved PR #6 and the final watcher permission scope. Reviewed implementation `385079f850a9306b5d5353639b1774c6c25e88c6`, branch `ops/agent-readiness-watcher`, [PR #7](https://github.com/kha997/ai-chatbot/pull/7). Governance merge `8d7949470cf3df4b1f77165f779b80f208085afd`.
- **Execution authorization:** future real model qualification requires a separate provider/access and cost/quota decision. The Watcher depends on the PC and signed-in user session.

## Gate 0–1 research baseline

- **STATE:** GATE_1_COMPLETE (research and design documentation; no runtime acceptance)
- **GATE:** 1, research/design only. Runtime NOT_RUN.
- **RECOMMENDATION:** **CONDITIONAL GO** for separately approved synthetic Gate 2 using LangGraph OSS with application-owned authorization and per-tenant credentials/storage. Optional modules remain gated.
- **COMPLETED:** [Owner brief](OWNER_BRIEF.md), [OSS evidence](OSS_DUE_DILIGENCE.md), [architecture](ARCHITECTURE.md), [tenant/memory threat model](SECURITY_AND_MEMORY.md), [348-scenario evaluation blueprint](EVALUATION_SPEC.md), [integration/cost/ops](INTEGRATION_AND_OPERATIONS.md), [CLI/dispatcher discovery/design](AGENT_DISPATCHER_DESIGN.md). Full benchmark and executable harness are future pre-scoring work.
- **VALIDATION:** [Static evidence and reproducible checks](VALIDATION.md): local links, three synthetic source/oracle examples, decimal arithmetic, null NOT_RUN metrics, count/weight checks, git diff --check; five release tags/SHAs independently rechecked. WSL OpenCode 1.18.30 version/help succeeded. No external AI prompt, PoC, dispatcher, real integration or paid call executed.
- **REVIEW:** Separate built-in Codex governance_review inspected b29f3e8ac52d135ea3d2f469246d9f0dac8571b9, sampled primary license/security sources, and rechecked all corrections at **0148b55c07c52db03aeef641b0d837cfd5fce823**. Both Medium findings resolved; no Critical/High design defect or remaining blocker. Reviewer independently reran static validation: 43 local links, three examples, arithmetic and committed hash PASS. [Review record](reviews/GATE_1_REVIEW.md). Contributor checks are separately labeled; this is not vendor/model-diverse review.
- **OPEN RISKS:** High: runtime tenant isolation untested; final dependency/license/SBOM review required; RAGFlow advisory applicability unknown (module excluded). Cost/capacity and external agent auth/billing UNKNOWN. See [risk register](SECURITY_AND_MEMORY.md).
- **NEXT:** stop at Gate 1; retain runtime prerequisites for a separately authorized synthetic Gate 2. Recommended default is B; full dataset materialization and dependency qualification precede scoring. No Gate 2 or dispatcher execution.
- **OWNER DECISION:** NONE to complete research. Before future Gate 2: separately approve bounded synthetic execution and any spend/access; before dispatcher build/run: separate explicit approval. No production or real-data approval is implied.
- **HEAD/BRANCH/PR:** final technical review target **0148b55c07c52db03aeef641b0d837cfd5fce823**; initial research b29f3e8ac52d135ea3d2f469246d9f0dac8571b9; discovery 11ea02b76bdad92c1e3872db3ba4f166ee5ce6ed; branch `research/gate-0-1`; [PR #4](https://github.com/kha997/ai-chatbot/pull/4). This final status/review-record commit is reporting-only; its exact HEAD and merge SHA are recorded in the PR/issue closure evidence to avoid circular self-hashing. Inspect PR state for merge outcome.

Governance: [PR #2](https://github.com/kha997/ai-chatbot/pull/2) reviewed/corrected and merged at `919b018045abd88e45a3ca7716643a48d25a5ce8`.

Authorship: lead Codex; source research by oss_research; evaluation design by evaluation_design; independent context review by governance_review. Qoder/Kilo not invoked; OpenCode used only for help/version inspection. Review is a separate built-in Codex session and does not certify runtime safety.
