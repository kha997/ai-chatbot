# AI ChatBot — remote status

## Issue #72 — Public synthetic qualification

- STATE: READY_FOR_ARCHITECTURE_REVIEW after hosted checks; independent review remains `INDEPENDENT_REVIEW_BLOCKED`.
- GATE: 1, offline public remediation under [Issue #72](https://github.com/kha997/ai-chatbot/issues/72), baseline `588b8fe1d3e54161fe194739d2c06552ca8c79f4`.
- RECOMMENDATION: Review the public-synthetic F3–F7 package at the frozen technical SHA named on the Draft PR.
- COMPLETED: [F3–F7 matrix, trust boundary and OpenCode handoff](OFFLINE_QUALIFICATION_72.md).
- VALIDATION: See the Draft PR for the exact Windows, WSL, and hosted CI receipts. Actual private audit, provider/model and six E2Es NOT_RUN.
- OPEN RISKS: HIGH — `BLOCKED_PRIVATE_AUDIT`, `BLOCKED_HELDOUT_CUSTODY_WORKFLOW`, `BLOCKED_CORPUS_BREADTH`, `BLOCKED_COST_CONTROL`.
- NEXT: Verify an isolated, zero-egress audit environment for independent review. Issue #63 stays OPEN.
- OWNER DECISION: Architecture review of the public package after independent audit evidence.
- HEAD/BRANCH/PR: `codex/issue72-public-offline`. Exact SHA and PR are recorded as evidence on [Issue #72](https://github.com/kha997/ai-chatbot/issues/72).

## Issue #69 — Public harness remediation (2026-11-24)

- STATE: BLOCKED — PARTIAL_REMEDIATION / BLOCKED pending Qoder re-review.
- GATE: 1, public offline only under [Issue #69](https://github.com/kha997/ai-chatbot/issues/69). Baseline `7e2a775acfd542d5d4db0ac4c5b061e2214e37ae`.
- RECOMMENDATION: Review the bounded remediation using public dummy cases.
- COMPLETED: [H1–H6 closure matrix and Qoder handoff](OFFLINE_REMEDIATION_69.md).
- VALIDATION: 15 original remediation tests + 4 correction tests + 132 baseline regressions PASS on Windows and route-free WSL. Four hosted checks PASS at technical SHA. Qoder re-review pending; 30 outside-repo checks NOT_RUN. The previous main harness CI result was NOT_RUN — no trigger. AI and six E2Es NOT_RUN.
- OPEN RISKS: HIGH — BLOCKED_PRIVATE_AUDIT / BLOCKED_HELDOUT_CUSTODY_WORKFLOW, BLOCKED_CORPUS_BREADTH, BLOCKED_COST_CONTROL.
- NEXT: Await the exact-SHA public [Qoder re-review](https://github.com/kha997/ai-chatbot/pull/70#issuecomment-7121343608) before Architecture Acceptance.
- OWNER DECISION: NONE while public proof is pending. Issue #63 stays OPEN.
- HEAD/BRANCH/PR: `codex/issue69-harness-remediation`, [Draft PR #70](https://github.com/kha997/ai-chatbot/pull/70), frozen correction SHA `bd56785dadbf1ee7fb8343edfd89d9278862b12e`. Exact reporting HEAD appears on the PR.

## Issue #67 — Offline held-out harness (2026-11-24)

- STATE: GATE_1_COMPLETE — public harness merged at `7e2a775acfd542d5d4db0ac4c5b061e2214e37ae`.
- GATE: 1, offline only under [Issue #67](https://github.com/kha997/ai-chatbot/issues/67), baseline `d7ada367443051ebe45c7461c2c6330733cad6bd`.
- RECOMMENDATION: Verify the public harness and keep actual private evaluation with the authorized custodian.
- COMPLETED: [Vietnamese dossier, revocation and private procedure](OFFLINE_HELDOUT_67.md).
- VALIDATION: 18 dummy harness, 15 corpus, 26 gateway, 73 quote tests and hosted CI PASS. [Independent exact-SHA review](reviews/ISSUE_67_HELDOUT_REVIEW.md) PASS. Actual private audit, AI and six E2Es NOT_RUN.
- OPEN RISKS: HIGH — BLOCKED_PRIVATE_AUDIT / BLOCKED_HELDOUT_CUSTODY_WORKFLOW. BLOCKED_CORPUS_BREADTH and provider-level BLOCKED_COST_CONTROL remain.
- NEXT: Issue #67 is closed. Track public audit remediation in Issue #69 and private audit separately.
- OWNER DECISION: Architecture Acceptance of the public harness only. Issue #63 stays open.
- HEAD/BRANCH/PR: `codex/issue67-heldout-harness`, [PR #68](https://github.com/kha997/ai-chatbot/pull/68). Review SHA `0992c15f86db032cd706866a1f9880dd2017b7e7`. Exact reporting HEAD will be recorded on the PR.

## Issue #64 — Offline fake gateway (2026-11-23)

- STATE: GATE_1_COMPLETE — OFFLINE_GATEWAY_QUALIFIED; Architecture Acceptance is offline only.
- GATE: 1, offline simulation under [Issue #64](https://github.com/kha997/ai-chatbot/issues/64).
- RECOMMENDATION: Accept the local SQLite safety controls for offline qualification. Live execution remains NO-GO.
- COMPLETED: [design, trust boundary and tests](OFFLINE_GATEWAY_64.md).
- VALIDATION: 26 gateway tests on Windows and route-free WSL, 73 existing regressions, hosted checks and [independent exact-SHA review](reviews/ISSUE_64_GATEWAY_REVIEW.md) PASS. AI and six E2Es NOT_RUN.
- OPEN RISKS: HIGH — BLOCKED_COST_CONTROL, including provider/account/region/terms/rates/fees and real framing. Offline gateway proof cannot close these.
- NEXT: Keep provider qualification separate and subject to future authorization.
- OWNER DECISION: ACCEPT_FOR_MERGE (OFFLINE ONLY) at approved HEAD `efbdce51522d4bd59714c8daf527b49c9e50ef4d`. No Gate 2, integration, spend or deployment.
- HEAD/BRANCH/PR: Reviewed SHA eaa5600dafaaa2e69924f6de3c78f782b2fdc8e4, branch codex/issue64-offline-gateway, [PR #66](https://github.com/kha997/ai-chatbot/pull/66). PR records the reviewed, approved, synchronized and merged revisions.

## Issue #63 — Offline synthetic corpus (2026-11-23)

- STATE: BLOCKED — public preparation merged; Issue #63 stays OPEN. `PARTIAL_CORPUS_READY / BLOCKED_HELDOUT_CUSTODY`.
- GATE: 1 — Issue #63 offline evidence only. The accepted baseline is [b213fb56](https://github.com/kha997/ai-chatbot/commit/b213fb560902083ebeb87f3fd3f3aff25c25894d).
- RECOMMENDATION: Keep the 60 private cases pending an authorized custody location and access policy.
- COMPLETED: [Public sources and separate development evidence](OFFLINE_CORPUS_63.md), [frozen public manifest](../eval/offline63/manifest.json), 60 reserved public coverage IDs. As recorded in the sanitized Issue #63 receipt, Snapshot v2 has 60/60 Owner content approvals. Independent technical verification and approved private custody workflow remain pending. No questions, answer keys, private pins or storage locators are published here.
- VALIDATION: 15 corpus tests on Windows and isolated WSL, 73 quote regressions, both hosted checks and [independent exact-SHA review](reviews/ISSUE_63_CORPUS_REVIEW.md) PASS. AI and all six E2E scenarios are NOT_RUN.
- OPEN RISKS: HIGH — `BLOCKED_HELDOUT_CUSTODY` and umbrella `BLOCKED_CORPUS_BREADTH`. The authorized custodian and independent reviewer must verify the privately held Snapshot v2 and access/retention workflow. No spending or external system approval.
- NEXT: Full corpus work awaits the separate custody decision below.
- OWNER DECISION: Confirm authorized custody and an independent review procedure for Snapshot v2 before private audit. [Custody decision](OFFLINE_CORPUS_63.md#held-out-custody-decision)
- HEAD/BRANCH/PR: Reviewed SHA `d0f475f0ebcfa5d2cca6dc2437223bf6dbaa145d`, branch `codex/issue63-offline-corpus`, [PR #65](https://github.com/kha997/ai-chatbot/pull/65). Owner accepted public preparation at HEAD `33d24cd5efe2f55941cf698efb2785ececd9dd45` (ACCEPT_PARTIAL_FOR_MERGE). Verified merge `7aa7e77b1ad949a425ec2aa1a9265e10e7df0bb9`.

## Issue #61 — Gate A preparation (2026-11-23)

- STATE: READY_FOR_ARCHITECTURE_REVIEW — **GATE_A_PREPARATION_READY_FOR_OWNER**, documents only.
- GATE: 1 — Gate A preparation under [Issue #61](https://github.com/kha997/ai-chatbot/issues/61); execution NOT_AUTHORIZED / NOT_RUN.
- RECOMMENDATION: Architecture Acceptance for the independently reviewed preparation dossier; retain GPT-5.4 mini snapshot and deterministic authority; no activation of600 requests/US$10.
- COMPLETED: [Owner memo](GATE_A_OWNER_61.md), [case/oracle inventory](GATE_A_CORPUS_61.md), [privacy/safety](GATE_A_CONTROLS_61.md), [budget](GATE_A_BUDGET_61.md), [manifest/approval packet](GATE_A_MANIFEST_61.md), [dated sources](GATE_A_SOURCES_61.md). PR #60 is merged and Issue #59 closed; accepted architecture baseline is `24d8fb46f7726e42bcce4bb48904e6f8738250d7`.
- VALIDATION: `git diff --check 24d8fb46f7726e42bcce4bb48904e6f8738250d7 HEAD` and independent offline checks PASS:9 Markdown paths,83 relative links,60/12/24/12 unique IDs, T1–T13, fixture provenance/hashes and cost/retry arithmetic. Fresh-context Codex review PASS at exact technical SHA; [receipt](reviews/ISSUE_61_PREPARATION_REVIEW.md). [Existing quote CI](https://github.com/kha997/ai-chatbot/actions/runs/45168990208) success at reviewed SHA. No local runtime/model tests; six business E2Es NOT_RUN. Historical73/73 and hosted quote regression are not AI evidence.
- OPEN RISKS: HIGH — BLOCKED_CORPUS_BREADTH, BLOCKED_COST_CONTROL, provider/access/terms and runtime prerequisites; lead owns technical qualification, Owner reserved approvals remain separate. No real data used.
- NEXT: wait for Architecture Acceptance; retain the separate fixture/control and execution prerequisites; no automatic implementation or new issue.
- OWNER DECISION: Architecture Acceptance of PR #62 documents only. Later fixture/control work and exact execution permission remain separate; this acceptance never grants spend/data/API access.
- HEAD/BRANCH/PR: reviewed technical HEAD `99babe18fb1306f05d2f0ece1ed74ef0798eebcb`; baseline `24d8fb46f7726e42bcce4bb48904e6f8738250d7`; `codex/issue61-gate-a-preparation`; [PR #62](https://github.com/kha997/ai-chatbot/pull/62). Following commit updates reporting only; exact final HEAD is in PR/issue delivery receipt to avoid circular self-hashing. Original worktree remains unchanged.

## Issue #59 — NHD MVP architecture review (2026-11-23)

Historical pre-merge receipt below: **superseded status only** by accepted PR #60 merge `24d8fb46f7726e42bcce4bb48904e6f8738250d7` and closed Issue #59, confirmed in Issue #61. This does not waive the retained source/taxonomy or runtime prerequisites. Original validation and review receipt remain unchanged.

- STATE: READY_FOR_ARCHITECTURE_REVIEW
- GATE: 1 — research/docs only under Issue #59; no runtime expansion.
- RECOMMENDATION: NHD-first Python state machine, approved lexical retrieval and deterministic quote policy; bounded GPT-5.4 mini trial only after separate provider/budget authorization. Proposed ADR-002 awaits Architecture Acceptance.
- COMPLETED: [Owner memo](NHD_MVP_OWNER_59.md), [inventory, ADR and diagram](NHD_MVP_ARCHITECTURE_59.md), [platform contracts, RTM and six NOT_RUN E2Es](NHD_PLATFORM_CONTRACTS_59.md), [costs and gates](NHD_MVP_COST_ROADMAP_59.md), [dated sources](NHD_MVP_SOURCES_59.md). PRs #56 and #58 are recorded as merged. Historical receipts are intact.
- VALIDATION: eight Markdown paths, 90 local links, 37 RTM rows, six full E2E specifications and cost arithmetic checked. Independent Codex PASS on reviewed technical SHA. Runtime/model tests and the six full E2Es are NOT_RUN. Historical 73/73 covers the synthetic components.
- OPEN RISKS: HIGH — real identity/recovery, source approval, provider cost/data controls and production operations absent; lead owns technical prerequisites, Owner retains reserved approvals. See dossier risk register.
- NEXT: await private source comparison and Architecture Acceptance.
- OWNER DECISION: Architecture Acceptance for PR #60 after Owner-side comparison with v1.0. A later execution approval is separate.
- HEAD/BRANCH/PR: independent review of technical SHA `98a90a1676c44480e83a2a78054b5fca292f3081`; `docs/issue59-nhd-mvp-architecture`; [PR #60](https://github.com/kha997/ai-chatbot/pull/60). The subsequent commit records the [review receipt](reviews/ISSUE_59_ARCHITECTURE_REVIEW.md) and status only.

## Issue #57 — durable synthetic handoff and consent

- STATE: GATE_1_COMPLETE — Issue #57 accepted/closed, PR #58 merged (local synthetic scope only).
- GATE: 1 (Issue #57 local development exception)
- RECOMMENDATION: SYNTHETIC_SQLITE_HANDOFF_DURABILITY_PASS for local synthetic SQLite, with support-only continuity after full restart.
- COMPLETED: [schema, restart demonstration, review and limitations](SQLITE_HANDOFF_57.md).
- VALIDATION: `py -B -m unittest discover -s tests -p 'test_quote*.py'` passed 73/73. Also passed with only loopback in WSL. Independent Codex PASS at the technical SHA. [Hosted CI passed](https://github.com/kha997/ai-chatbot/actions/runs/45087489896).
- OPEN RISKS: HIGH if used for real identity or data. Customer ownership recovery needs a separately approved identity design. Lead limits this to local synthetic fixtures.
- NEXT: architecture review in Issue #59; no automatic runtime work.
- OWNER DECISION: NONE for the completed Issue #57 scope.
- HEAD/BRANCH/PR: merged as `6243aa7806b9209e3df810fbe34f1dab7bc51a40` on 2026-11-23; reviewed technical SHA `8678c4fb36c193775d4486d54acc00d7b60aa785`, receipt head `d6f4d25d53fcadab540cf5169a617b6241d3f369`, branch `codex/issue57-sqlite-handoff`. [PR #58](https://github.com/kha997/ai-chatbot/pull/58). Prior receipts remain historical.

## Issue #55 — local synthetic session boundary

STATE: GATE_1_COMPLETE — Issue #55 accepted/closed, PR #56 merged (local synthetic scope only).
GATE: 1 (narrow development exception: Issue #55)
RECOMMENDATION: LOCAL_SYNTHETIC_SESSION_BOUNDARY_PASS for the accepted offline adapter only.
COMPLETED: [implementation, threat boundaries and validation evidence](SESSION_BOUNDARY_55.md); [PR #56](https://github.com/kha997/ai-chatbot/pull/56); original checkout preserved.
VALIDATION: `py -B -m unittest discover -s tests -p 'test_quote*.py'` — PASS, 59 tests on Windows and in a private WSL network namespace; independent Codex reviewer reran 59/59 and confirmed both findings fixed; [CI SUCCESS](https://github.com/kha997/ai-chatbot/actions/runs/45085345535/job/137402571523); baseline-to-reviewed-head `git diff --check` PASS.
OPEN RISKS: HIGH if used as real auth — synthetic identities only; sessions/revocation are ephemeral, and the HTTP preview remains a curated harness outside this adapter. No unresolved independent security findings within Issue #55 scope. Gate 2 and production remain NO-GO.
NEXT: assess remaining real-identity gaps under Issue #59; no automatic runtime work.
OWNER DECISION: NONE
HEAD/BRANCH/PR: merged as `7da8524c5cb674197423a97684601cdafe4946c3` on 2026-11-23 Asia/Saigon; independently reviewed technical head `db3296fbe37515c76f6d24b1818da6b4dd9e740c`, receipt head `a40b03655c7d91af45c135d3f22d88a84f27c44c`; `codex/issue55-session-boundary`; [PR #56](https://github.com/kha997/ai-chatbot/pull/56). Prior receipts remain historical.

## Local quote developer preview — Issue #53

- **STATE:** The loopback browser demo reuses the existing synthetic quote and support-handoff contracts for NHD, HANU and ZENA.
- **SCOPE:** Curated scenarios and mock roles only. All preview state stays in memory, and the app serves only its bundled HTML and CSS. No external delivery, model invocation or deployment. Dispatcher, Gate 2 and production remain **NO-GO**. [Windows run command](../README.md#local-quote-preview).

## Synthetic support handoff for draft quotes — Issue #51

- **STATE:** Offline handoff checks validate explicit consent, tenant boundaries, duplicate prevention, queue failure and forged confirmation. A refusal produces no ticket, price or citation.
- **SCOPE:** In-memory queue and mock inbox only. External channels, model calls, deployments, Dispatcher, Gate 2 and production remain **NO-GO**. [Contract and test command](QUOTE_HANDOFF.md).

## Deterministic draft quote validator — PR #48 development decision

- **STATE:** The offline Python validator passes all **22 synthetic fixture cases**, including **19 refusal or clarification** cases. The three draft totals are NHD **600,000 VND**, HANU **50,000 VND** and ZENA **600,000 VND** with their approved fixture citations.
- **SCOPE:** Qoder was not invoked. A Codex fallback authored the independently reviewed fixtures in PR #49. The validator runs on synthetic inputs with caller-supplied trusted context and no external actions. Ollama, Agent Dispatcher, Gate 2 and production remain **NO-GO**. [Fixture contract, implementation and tests](QUOTE_ACCEPTANCE.md).

## Gate 1.5 direct Ollama readiness — Issue #46

- **STATE:** **WAITING_RESOURCE_WINDOW_AND_GPU_BOUNDARY.** Windows had 5.10 GiB physical RAM available versus the 14 GiB admission floor. The GPU had 13,772 MiB free but there is no exclusive window or verified GPU-visible sandbox.
- **SCOPE:** Planning and read-only evidence only. Issue #44 closed with unresolved OpenCode timeouts. No new Owner Gate requested. Ollama startup, inference, Dispatcher, Gate 2 and production remain **NO-GO**. [One-start/one-POST plan and stop conditions](DIRECT_OLLAMA_READINESS_46.md).

## Gate 1.5 OpenCode mock timeout diagnosis — Issue #44

- **STATE:** **BLOCKED_ADAPTER_UNRESOLVED / BLOCKED_RESOURCES.** Both bounded instrumented mock runs passed. Neither reproduced the earlier pre-HTTP or post-SSE timeout. The stop-loss is reached and the adapter has no proven fix.
- **SCOPE:** Offline evidence only. No model or startup authorization, no change to host admission floors. Ollama startup, inference, Dispatcher, Gate 2 and production remain **NO-GO**. [Prior failures, reviewed hypothesis and phase timings](OPENCODE_TIMEOUT_DIAGNOSIS_44.md).

## Gate 1.5 one local coding prompt — Issue #42

- **STATE:** **BLOCKED_ADAPTER / BLOCKED_RESOURCES.** The current SDK mock passed once and timed out once. Windows available RAM was below the proposed floor, and no exclusive GPU window was reserved.
- **SCOPE:** Offline mock and synthetic Python regression only. No Owner activation requested. Ollama startup, inference, Dispatcher, Gate 2 and production remain **NO-GO**. [Readiness evidence and proposed one-run limits](ONE_LOCAL_PROMPT_READINESS_42.md).

## Gate 1.5 NTFS sparse-source compatibility — Issue #39

- **STATE:** **STORAGE_COPY_PASS / ONE_ATTEMPT_CONSUMED.** The single approved run published 9,276,199,424 bytes to the private D: store. All six source and destination SHA-256 checks passed. The destination files are non-sparse and staging is absent.
- **SCOPE:** Issues #36 and #39 remain consumed. No repeat transfer was authorized. Ollama startup, inference, Agent Dispatcher, Gate 2 and production remain **NO-GO**. [Final receipt and six SHA-256 digests](https://github.com/kha997/ai-chatbot/issues/39#issuecomment-7075781476).

## Gate 1.5 storage-only export — Issue #36

- **STATE:** **BLOCKED_SOURCE_SPARSE_FILE / ONE_ATTEMPT_CONSUMED.** The one approved qwen3:14b transfer stopped at source metadata validation. NTFS reports all five source blobs as sparse files. No model bytes were written and there is no destination or stage.
- **SCOPE:** No retry. The attempt record and error receipt were preserved. Inference, Ollama startup, Agent Dispatcher, Gate 2 and production remain **NO-GO**. [Owner approval](https://github.com/kha997/ai-chatbot/issues/36#issuecomment-7075133334) · [Attempt receipt](OLLAMA_STORAGE_COPY_36.md#one-use-attempt-receipt).

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
