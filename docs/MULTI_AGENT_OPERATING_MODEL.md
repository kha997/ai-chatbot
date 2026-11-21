# Multi-Agent Operating Model — AI ChatBot

**Status:** ACCEPTED via [PR #2](https://github.com/kha997/ai-chatbot/pull/2), merged as `919b018045abd88e45a3ca7716643a48d25a5ce8` on 2026-11-21. Effective for Gate 0–1 only.
**Architecture owner:** ChatGPT (technical recommendation and later remote evidence review); **engineering lead:** Codex; **business owner:** non-technical Owner.
**Applicable Gate:** Gate 0–1 only. No authority to start executable Gate 2, spend money, connect live data, change other projects or deploy.

## 1. The outcome, not the roster, controls delegation

The objective is the strongest safe, evidenced Gate 0–1 result—not maximizing the number of agents. Codex leads the workstream, makes ordinary technical decisions, assigns bounded parallel work when beneficial and integrates the result. It must be capable of progressing even when Qoder, OpenCode or Kilo are unavailable.

Do not assume that any agent is installed, authenticated, cost-free or has permission to read or write project files. Verify actual availability, version, supported invocation method, access boundaries and billing **without installing or subscribing to anything** as part of the initial survey. Report `AVAILABLE`, `UNAVAILABLE` or `UNVERIFIED`. If unavailable, Codex or another approved agent does the task; no blocker to Gate 0–1 unless a mandatory independent review truly cannot be performed.

**Naming:** "Qcoder" in the current Owner conversation is interpreted as **Qoder**, the previously used coding assistant (not the separate QCoder-branded product). Correct this mapping only if the Owner later explicitly specifies otherwise.

## 2. Role ownership (a RACI-style boundary)

| Role | Primary accountability | Representative work | Not allowed |
| --- | --- | --- | --- |
| **Codex — Lead Engineering Agent** | System-level outcomes, complex architecture, critical coding, integration, defects, test gate and recommendation | architecture A/B; cross-cutting security model; integration contracts; final owner brief; technical tradeoffs and PR integration | Delegate away final accountability; approve its own work as independent reviewer; start Gate 2 |
| **Qoder — Research & Design Specialist** | Evidence-backed technology investigation and specifications | upstream versions/releases/licenses; vendor comparisons; interface/UX specs; architectural alternatives and citations | Independently change shared core or assert unverified claims |
| **OpenCode — Test & Reproducibility Specialist** | Golden fixtures, test oracle, evaluation methodology, reproducibility | synthetic NHD/HANU/ZENA datasets, rubric, negative tests, repeatable measurement plan and smoke validations | Expose real data or certify production security |
| **Kilo — Adversarial Reviewer** | Cross-check assumptions, security, permissions and license constraints from a fresh context | tenant-boundary threat model review, prompt-injection adversarial scenarios, architecture challenge, review of PR evidence | Approve own implementation; mutate implementation branch under review |
| **ChatGPT — Architecture Advisor** | Review remote evidence and recommend technical decisions to Owner when consulted | decide between alternatives, explain business impact, challenge conclusions | Pretend to monitor GitHub continuously or silently launch local coding agents |
| **Owner — Business authority** | Reserved matters only | budget, paid access, real data, contractual/legal choices, production go-live | Expected to choose frameworks, configs, test commands or debug procedures |

**Review independence:** Merely using a different brand of coding tool does not establish independent review if it consumes the same unchallenged conclusions, same authoring context, or self-authored test oracle. Reviewers need a separate session, a defined adversarial remit, source evidence and an immutable commit/diff. OpenCode and Kilo may share underlying agent components; therefore verify tool/model/runtime separation and note when independence is limited.

## 3. Dispatch policy

Codex decides how to staff each bounded task:

- **Critical/complex:** Codex leads; Qoder performs research if needed; OpenCode devises negative and regression tests; Kilo or another truly distinct fresh reviewer challenges the result. Security/tenant isolation/knowledge-promotion conclusions require independent scrutiny.
- **Medium complexity:** Codex implements or delegates a well-defined unit; OpenCode tests; reviewer assigned by risk.
- **Routine research/documentation:** Use Qoder/OpenCode if available; Codex reviews sources, integrates and signs off within scope.
- **No value in parallelization:** Use Codex alone. Do not make four calls just to satisfy a tool quota.

Initial Gate 0–1 suggested lanes (agent may refine from evidence):
1. Codex: architecture decisions, risk register, synthesis, Owner brief.
2. Qoder: official OSS/license/maintenance reconnaissance with dated citations.
3. OpenCode: golden dataset schema, synthetic fixtures, evaluation and metrics plan.
4. Kilo: independent adversarial review of tenant isolation, license interpretation and learning-promotion safety.

**Costs:** prefer existing authorized sessions/providers and smaller models for low-risk tasks; reserve high-capability Codex/model capacity for complex and critical work. Log model/provider, tool usage and cost **if available**; never invent totals. Do not activate paid APIs or subscriptions without explicit approval.

## 4. Safe parallel Git workflow

- **GitHub = system of record.** All meaningful work, evidence and reports must be pushed to `kha997/ai-chatbot`.
- Codex creates a parent GitHub issue and delegates scoped work into sub-issues (or clearly labeled work packets) with expected output, acceptance tests, owner and due gate.
- **One writer per issue and branch.** Do not allow multiple agents to edit the same Git working tree concurrently. Prefer separate Git worktrees/clones, or serialized work if worktrees are unavailable; first inspect uncommitted changes and avoid destructive operations.
- Delegate research using read-only scopes where possible. Use independent feature branches/PRs for contributions; Codex integrates after verified checks.
- Cross-check the intended baseline and exact commit SHA. Never push directly to `main` after bootstrap, force push, rebase others' active branches, or overwrite uncommitted local work.
- Before merging: relevant checks pass; review is recorded with source/diff and reviewer identity; no new unresolved Critical/High risk; branch stays in authorized Gate.
- Escalate conflicts to Codex for technical resolution, not to the non-technical Owner. If agent capabilities are missing, document a fallback and keep progressing.
- At meaningful milestones, push `docs/STATUS.md`, decision records and evidence. The final Owner report links to relevant issues, PRs and exact HEADs.

## 5. Work packet template

```md
OUTCOME: tangible artifact + how it reduces project risk
BOUNDARY: files or research scope; no other changes
INPUTS: authoritative sources, repo commit, synthetic fixtures
ACCEPTANCE: verifiable tests, citations, limitations
AUTHORITY: local reversible technical choices delegated
PROHIBITED: live data, paid calls, other-project writes, production
REVIEW: independent or self-audit with honest designation
DELIVERABLE: GitHub branch/PR + concise owner-facing result
```

Avoid handholding via command-by-command directions. Delegate a complete meaningful result with acceptance criteria. The assignee is free to choose methods within the boundary.

## 6. Mandatory decision and reporting protocol

Codex's status must report:
- What commercial/technical outcome was achieved; what was **actually tested** vs planned.
- Which agent authored what, branch, PR and SHA, and which agent reviewed independently.
- Evidence hyperlinks, review findings, corrections, unresolved risks and any cost.
- One recommended architecture/next action, not multiple technical choices for the Owner.
- `OWNER DECISION: NONE` unless a reserved matter blocks safe continuation.

A Gate 0–1 desktop research completion is **not** permission to start runtime experiments. All governance and production boundaries in `AGENTS.md` remain in force.

## 7. First actions after merge

1. Codex reads the accepted multi-agent operating model, inspects local `D:\Projects\AI ChatBot` safely, and checks availability of Qoder, OpenCode, Kilo (read-only checks; no installation/credential setup).
2. Codex delegates appropriate Gate 0–1 packets only to tools that are actually ready. If not available, continue with built-in capabilities and explicitly log the limitation.
3. Codex updates Issue #1, opens workstream PRs, publishes evidence and a single technically recommended next decision for remote review.
