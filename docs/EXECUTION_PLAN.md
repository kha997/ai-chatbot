# Gate 0–1 delivery plan

Date: 2026-11-21 (Asia/Saigon). Baseline: `237984c966c6fd5070b04e2166494a873f882920`.
Authority: Issues [1](https://github.com/kha997/ai-chatbot/issues/1), [3](https://github.com/kha997/ai-chatbot/issues/3), current Owner directive and AGENTS.md.

This plan concerns research documents and static evaluation assets, not implementation of a bot or dispatcher. Technical choices are delegated to Codex; no additional technical-choice approval is needed.

| Work packet | Author | Deliverable | Acceptance |
| --- | --- | --- | --- |
| GOV | Codex lead + separate governance_review session | Review/correct/merge PR #2 | Immutable review evidence; scope unchanged |
| OSS | Codex oss_research session, lead integrates | `OSS_DUE_DILIGENCE.md` | Five primary-source dossiers; versions/licenses/security caveats |
| EVAL | Codex evaluation_design session, lead integrates | `EVALUATION_SPEC.md`, synthetic examples | 180-QA blueprint, oracles, hard gates, fair A/B, static validation |
| ARCH | Codex lead | `ARCHITECTURE.md`, `SECURITY_AND_MEMORY.md`, `INTEGRATION_AND_OPERATIONS.md` | Single recommendation, tenant boundaries, rollback, cost protocol |
| CLI | Codex lead | `AGENT_DISPATCHER_DESIGN.md` | Dated Windows/WSL observations, no AI prompt calls, safe future protocol |
| REVIEW | Separate Codex reviewer session | `reviews/GATE_1_REVIEW.md` | Adversarial license/security/architecture review of immutable commit; fixes rechecked |
| CLOSE | Codex lead | `OWNER_BRIEF.md`, `STATUS.md`, PR and issue reports | Evidence remotely readable; precise tested/not-run distinction |

Sequence: baseline and governance → publish discovery milestone → synthesize designs and static assets → commit/push → independent review → corrections/validation → reviewed research merge → report conditional Gate 2 decision.

Validation: `git diff --check`; local Markdown target checks; JSON parse and synthetic fixture oracle checks; matrix count arithmetic; manual scope/secret scan; independent adversarial review. No dependency installation, runtime PoC, model benchmarks or dispatcher execution.

Reviewer independence is context separation within Codex, not vendor/model diversity. Qoder/OpenCode/Kilo will not receive prompts under this authorization. Full benchmark materialization and runtime harness implementation are future Gate 2 work; Gate 1 delivers their precise design and representative static contract examples.
