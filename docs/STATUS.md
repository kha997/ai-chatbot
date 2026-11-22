# AI ChatBot — remote status

## Gate 1.5 OpenCode SDK mock — Issue #34

- **STATE:** **SDK_MOCK_PASS.** The installed OpenCode 1.18.30 CLI sent one POST and zero auxiliary requests to the private HTTP mock, returned the exact synthetic JSON and exited 0.
- **EMPTY DAEMON:** **PASS — one-use approval consumed.** Ollama Linux 0.31.1 returned its version and an empty model list through two isolated GETs. It created only empty D: model directories. Cleanup took 2.5496532 s including setup. Model copy, inference, Agent Dispatcher, Gate 2 and production remain **NO-GO**. [Final receipt and Owner scope](OPENCODE_SDK_MOCK_34.md#final-one-use-empty-store-receipt).

## Gate 1.5 Ollama storage preflight — Issue #32

- **STATE:** **BLOCKED** for the storage copy. D: DrvFS and protected read-only bind passed a tiny fixture; the original manifest and all five source hashes match. Subsequent Issue #34 verified SDK-to-mock and empty-store daemon access.
- **SCOPE:** Proposed private D: store, 12 GiB maximum, after explicit approval and preflight. No model copied or loaded, no Ollama startup, no GPU workload and no prompt. Dispatcher, Gate 2 and production remain **NO-GO**. [Evidence and rollback](OLLAMA_STORAGE_PREFLIGHT_32.md).

## Gate 1.5 isolated local model feasibility — Issue #30

- **STATE:** **BLOCKED** for a real OpenCode/Ollama prompt. Local-only OpenCode configuration and isolated mock loopback passed. The actual inference adapter, project-owned model storage and resource reservation are pending.
- **EVIDENCE:** PR #29 merged as mock evidence. Existing Ollama services were left alone. No model was copied, loaded or called. Dispatcher, Gate 2 and production remain **NO-GO**. [Resource and isolation findings](OLLAMA_LOCAL_FEASIBILITY_30.md).

## Gate 1.5 agent pivot — Issue #28

- **STATE:** **BLOCKED for a real qualification.** Kilo live trials are retired. PR #27 was merged as historical NO-GO. Qoder Pro has included credits, with `BLOCKED_COST` and `BLOCKED_ISOLATION` for the native CLI.
- **NEXT CANDIDATE:** A separately isolated OpenCode/Ollama instance. The current Ollama listener is shared host infrastructure and a project-owned model and resource reservation are unverified.
- **EVIDENCE:** No prompts or purchases. Dispatcher subprocess validation ran only a fixed mock, with no production adapter. Dispatcher, Gate 2 and production remain **NO-GO**. [Comparison, verification and future Owner conditions](AGENT_PIVOT_28.md).

## Gate 1.5 exact Kilo activation — Issue #26

- **STATE:** **NO-GO.** Issue #26 consumed its Owner approval with one live POST and no retry. HTTP 200 SSE reached `unfinished_task` after 128 events, with 50,758 bytes read and zero task bytes delivered. Kilo exit 1, oracle and usage unverified, and no leftover processes. Further live runs are stopped pending the Owner's decision. Issue #20 remains spent. Dispatcher, Gate 2 and production remain **NO-GO**.
- **ARTIFACT:** `5f9a05f65701f60c832732550aca9eafd6cb4d80` with the 256 KiB bounded TLS/SSE adapter, 24 s hard HTTPS deadline and 55 s pipeline watchdog. [PR #27](https://github.com/kha997/ai-chatbot/pull/27) · [Exact manifest, evidence and Owner decision](KILO_OWNER_GATE_26.md).

## Gate 1.5 local TLS and hard cancellation — Issue #24

- **STATE:** Offline loopback TLS candidate. No provider inference or use of Issue #20 authorization. Dispatcher, Gate 2 and production remain **NO-GO**.
- **RESULT:** Bounded SSE parser exercised over TLS and through the pinned Kilo Linux sandbox. Hard deadlines cover blocked reads and deliberate Unix write stalls. [Socket matrix, cleanup and Owner Gate conditions](KILO_LOCAL_TLS.md).
- **RECOMMENDATION:** Conditional GO to request a new Owner Gate after a separately reviewed activation and fresh zero-price verification. No new live request is authorized by this PR.
- **SHA/BRANCH/PR:** `48fd2b72e489a84567dea81720d5f5dc038ea166`, `evidence/kilo-local-tls`, [PR #25](https://github.com/kha997/ai-chatbot/pull/25).

## Gate 1.5 bounded Kilo SSE — Issue #22

- **STATE:** Offline fix validated for synthetic SSE over 32 KiB. Live qualification and Dispatcher remain **NO-GO**. The Issue #20 authorization remains consumed.
- **CAUSE:** The exact Issue #20 HTTPS capture/relay body cap rejected byte 32,769 before parsing any SSE event. The historic full body and usable completion are unknown.
- **EVIDENCE:** The offline candidate validates bounded HTTP/SSE input incrementally, and forwards a compact result after terminal checks. [Measurements, synthetic ELF cases and future gate conditions](KILO_BOUNDED_SSE.md).
- **SHA/BRANCH/PR:** `57e455c59b69f43220ca4d6fea191af8c9c0390d`, `evidence/kilo-bounded-sse`, [PR #23](https://github.com/kha997/ai-chatbot/pull/23).

## Gate 1.5 one-use Kilo activation — Issue #20

- **STATE:** **NO-GO.** PR #19 is merged as offline evidence. Issue #20 consumed its separate Owner approval with exactly one live POST and no retry. Dispatcher remains **NO-GO**.
- **RESULT:** Anonymous Free route passed the zero-price preflight. HTTP 200 SSE exceeded the 32 KiB response cap, so the relay rejected it and Kilo exited 1. No valid oracle, usage receipt or leftover qualification process was observed. Keep the spent markers.
- **SHA/BRANCH/PR:** `ace3a4ef35c75e4899f52b5bf1a92b64dcbd0064`, `evidence/kilo-final-activation`, [PR #21](https://github.com/kha997/ai-chatbot/pull/21). [Review evidence, Owner decision and invocation](KILO_FINAL_ACTIVATION.md).

## Gate 1.5 Owner Gate readiness — Issue #18

- **STATE:** `READY_FOR_OWNER_GATE` for the offline candidate; `NO_LIVE_AUTHORIZATION`. PR #17 merged as offline evidence at `0190319c757e800507d61896a34b318cbf38dfbf`. **Dispatcher NO-GO.**
- **VALIDATION:** 21 unit tests and 22 Kilo ELF offline cases passed, with zero real inference requests. Exact Bubblewrap 0.13.1 staged from independently verified upstream source. Independent reviewer rechecked serial cases and documented fail-closed behavior under overlap.
- **OWNER GATE:** One future Kilo-only POST to the reviewed anonymous free model at 0 VND, conditional on exact separately reviewed activation SHA, durable one-use authorization, current price and runtime controls. No live transport or token is present in this candidate.
- **HEAD/BRANCH/PR:** technical `f480575fcad5d32dde5846ae9a740e76af21a989`, `evidence/kilo-owner-gate`, [PR #19](https://github.com/kha997/ai-chatbot/pull/19). [Approval packet, risks, results and rollback](KILO_LIVE_OWNER_GATE.md).

## Gate 1.5 offline SSE diagnosis — Issue #16

- **STATE:** Reproduced Kilo exit 1 offline when the original relay labelled an HTTP 200 JSON error as SSE. Fixed response validation, multi-line parsing, bounded wire framing and sanitized CLI diagnostics. Historical live root cause remains **UNKNOWN**.
- **DECISION:** **NO-GO** for Dispatcher. PR #15 merged as a factual failure record only. This work used zero provider/model requests. Kilo and OpenCode remain at 1/1, and Qoder remains blocked.
- **HEAD/BRANCH/PR:** Reviewed technical commit `1a077759c8d2d80cd4c6704a1745a4b8c607b4e2` on `evidence/kilo-offline-sse`, [PR #17](https://github.com/kha997/ai-chatbot/pull/17). [Evidence hierarchy, validation and future approval conditions](GATE_1_5_KILO_OFFLINE_SSE.md).

## Gate 1.5 follow-up — Issue #14

- **STATE:** Kilo offline isolation/oracle passed. One anonymous zero-priced Kilo POST returned HTTP 200, but CLI exit 1 and no valid result or usage receipt. One extra local request was blocked. Kilo and OpenCode allowances are now spent. Qoder sent zero prompts and remains blocked on selected-model credits and isolation.
- **DECISION:** NO-GO for an autonomous dispatcher. Diagnose Kilo stream handling offline before requesting any further live attempt. OpenCode's 429 is unexplained and upstream v1/free relay compatibility warnings are documented.
- **HEAD/BRANCH/PR:** Reviewed runner commit `60d670dda3b871f79f574ba7b0e6b4f763179c7b` on `evidence/gate-15-kilo-isolation`, tracked in [PR #15](https://github.com/kha997/ai-chatbot/pull/15). [Evidence and reviewer provenance](GATE_1_5_KILO_ISOLATION.md).

## Historical qualification — existing agent accounts (PR #13, 2026-11-21)

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
