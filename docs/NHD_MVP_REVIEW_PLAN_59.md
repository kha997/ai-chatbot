# Issue #59 — architecture review plan

Date: 2026-11-23. Authority: [Issue #59](https://github.com/kha997/ai-chatbot/issues/59), research and documentation only.

Baseline: `6243aa7806b9209e3df810fbe34f1dab7bc51a40` (main, PR #58). One worktree, branch `docs/issue59-nhd-mvp-architecture`, one PR; await Architecture Acceptance before merge.

## Deliverables and checks

- [ ] Inventory accepted code, tests, fixtures, CI and historical research; distinguish implemented, tested, design-only and missing.
- [ ] Define the NHD customer journey, orchestration/model/RAG default and trust boundaries with dated official evidence.
- [ ] Calculate low/base/high costs and investment effort; specify future gates, acceptance, rollback and missing business inputs.
- [ ] Refresh current STATUS for merged PRs #56/#58 while preserving historical receipts.
- [ ] Validate document links, arithmetic and docs-only diff; freeze a commit and request independent fresh-context Codex architecture review.
- [ ] Resolve review findings, publish evidence and owner memo in the same PR, leave unmerged.

Planned files: `NHD_MVP_ARCHITECTURE_59.md` (inventory, requirements, ADR and trust), `NHD_MVP_COST_ROADMAP_59.md` (cost and gates), `NHD_MVP_SOURCES_59.md` (dated source ledger), `NHD_MVP_OWNER_59.md` (Vietnamese decision memo), `reviews/ISSUE_59_ARCHITECTURE_REVIEW.md` (validation and independent review), and `STATUS.md`. No runtime, test, fixture, configuration or dependency edits.

## Evidence rules

73/73 and the earlier preview 5/5 are historical synthetic acceptance, not measured AI quality. This review will not invoke a model, start a service, run a dispatcher, access private business data or authorize Gate 2. Local regression execution is optional; if omitted label NOT_RUN and cite the accepted receipt. Prices and proposed acceptance targets are assumptions until measured under a later approval. Review must challenge licensing, tenant isolation, cost, scope and gate boundaries at an immutable SHA.
