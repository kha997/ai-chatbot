# Issue #59 — validation and independent architecture review

Date: 2026-11-23. Author: Codex lead. Baseline `6243aa7806b9209e3df810fbe34f1dab7bc51a40`; [PR #60](https://github.com/kha997/ai-chatbot/pull/60), branch `docs/issue59-nhd-mvp-architecture`.

## Validation scope

Review plan: [bounded deliverables](../NHD_MVP_REVIEW_PLAN_59.md). Only Markdown documentation may change. No scripts/tests/eval/workflows/config/dependency edits, installation, model inference, runtime/service startup, private data or deployment.

Runtime suite NOT_RUN in this docs-only review. The accepted 73/73 at PR #58 is historical evidence, not a fresh test or AI benchmark. Existing hosted quote CI may run automatically on the PR; any result is recorded separately from architecture evidence.

The lead used inline Python standard-library checks for eight Markdown paths, 90 relative links including local Markdown heading anchors, 37 consecutive RTM IDs with 11 columns and NOT_RUN results, six numbered E2Es, 73 historical quote test methods by AST, and the three monthly cost rows. The 600-request allocation and regional token subtotal were recomputed with Decimal. `git diff --check origin/main HEAD` passed for the committed technical diff. Key model, data, hosting, database and license citations were sampled against official sources. The worktree at the original checkout retained its prior commit and clean status. Local runtime, model, E2E and deployment validation are NOT_RUN.

## Independent verdict

**NHD_MVP_ARCHITECTURE_REVIEW_READY_FOR_OWNER** for the documents. Fresh-context, read-only Codex session `/root/nhd_contract_reviewer` approved exact technical commit [98a90a1676c44480e83a2a78054b5fca292f3081](https://github.com/kha997/ai-chatbot/commit/98a90a1676c44480e83a2a78054b5fca292f3081). It verified the remote HEAD and baseline with `git ls-remote origin refs/heads/main refs/pull/60/head`, checked the exact range with `git diff --check`, verified the docs-only scope, and independently checked local link targets, costs, historical merge receipts and selected primary citations. Review was separate from authorship. This receipt does not represent a formal GitHub review approval.

| Finding | Final resolution |
| --- | --- |
| High: a valid citation could accompany an invented price or policy | Approved typed data and claim IDs drive a deterministic renderer. Negative acceptance tests cover valid-citation/false-claim responses. |
| High: excluding personal data lacked an enforceable provider boundary | A separate schema-checked egress policy limits real-data requests to approved fields, denies ambiguous inputs before dispatch, and defines the limits of withdrawal after sending. |
| High: critical suite and E2E tests were implicit release conditions | Gate B and C name the prerequisite 200-case suite and applicable E2Es. The final revision requires controlled staging, zero unresolved Critical/High findings and the rehearsed kill switch before any public canary. The independent reviewer confirmed the fix. |

The RTM reflects the authorized public Issue #59 and Owner QA briefs. The private v1.0 document was not accessed. The Owner compares the RTM with the original privately before Architecture Acceptance. The pending decision covers this dossier only. All six full business E2Es, paid inference, Gate 2 and live deployment remain outside the current approval.
