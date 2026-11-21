# Multi-Agent Orchestration — execution reality and bootstrap design

**Status:** DESIGN ONLY. No cross-agent execution or bridge has been installed or verified. This is a proposal inside the governance PR and cannot be described as an operational capability.

## 1. What actually dispatches the work?

The `AGENTS.md` and [operating model](MULTI_AGENT_OPERATING_MODEL.md) assign responsibilities, but a text policy **cannot launch another program**.

A local orchestrator (Codex with working terminal/process permissions, or a separately authorized small host runner) can invoke other agents' **noninteractive CLIs** as child processes and collect machine-readable outputs. The Windows Codex Desktop session may not have permission to run arbitrary external programs. Confirm that in the actual environment rather than presuming it.

**Official references to validate at execution date:**
- Qoder CLI: `qoder -p "<task>" --output-format json` (headless, tool/permission flags): https://docs.qoder.com/cli/run-in-scripts
- OpenCode CLI: `opencode run "<task>"` (automation command): https://opencode.ai/docs/cli
- Kilo CLI 1.0+: `kilo run "<task>"` (headless): https://kilo.ai/docs/code-with-ai/platforms/cli
- Kilo and OpenCode share lineage; difference in CLI brand is not itself proof of independent security review: https://kilo.ai/docs/contributing/architecture/cli-runtime

These are **usage illustrations, not commands already executed**. Exact CLI flags/version require on-machine verification.

## 2. Proposed minimum architecture

```text
Owner → Codex (lead / coordinator, approved scope)
            |
            v
      job planner (work packet)
            |
            v
      local dispatch runner (bounded commands, auth check, budgets)
        |             |            |
        v             v            v
     Qoder CLI    OpenCode CLI    Kilo CLI
        |             |            |
        +--- outputs / logs / verification ---+
                              |
                              v
                   Codex review / correction
                              |
                              v
                        Git branch / PR
                              |
                              v
                  GitHub remote evidence / status
```

This is an **orchestration hypothesis to implement/test only after permission and readiness**. No cross-agent API/MCP is needed initially if CLI invocation is reliable.

## 3. Safety-first readiness: inspection only

Codex should inspect, without installation/config/auth mutation:
1. Confirm execution context (Windows, WSL, Codex Desktop sandbox, shell permissions, git safe directory); detect `qoder`, `opencode`, `kilo` binaries and versions from PATH; if missing mark unavailable. Never assume existence from a desktop shortcut.
2. Read `--help`, available permissions, noninteractive modes, auth-status features. Do **not** output or log secrets, or issue prompt calls to paid providers to probe sign-in.
3. Record permitted provider/model and whether an already authorized credential/plan supports noninteractive usage. If uncertain, state `UNVERIFIED`.
4. Inspect repository/local Git state and branches; don't overwrite unknown changes; do not open external service ports.
5. Propose the smallest safe smoke test using a synthetic public text task, no code modification, no secrets, no paid call until independently authorized.

Initial report schema: `agent | binary present | version | headless mode | auth state (without token) | model/billing known? | subprocess allowed? | permission controls | status | evidence`.

## 4. Work packet and output contract

Each delegated work item has a scoped, versioned prompt; immutable base commit; task ID; expected artifact; permission profile (`read-only` for reviews); disallowed paths/actions; resource/time/token cap; and validation rubric. The host runner should:

- Execute each child in **its own worktree or sandbox**, never the active Codex Desktop working tree concurrently.
- Permitlist commands and paths; default read-only; block network/tool writing or escalation unless task requires and is approved.
- Capture exit code, machine-readable output, timestamps, tool version/model metadata if exposed, prompt hash, git diff and artifact hashes.
- Enforce bounded runtime and cap retries; redact log content before pushing; never collect tokens/passwords in stdout.
- Do not consider an exit code of 0 equivalent to passing factual/security tests.
- Codex performs integration review and corrections; a separate fresh reviewer performs required independent review. That reviewer receives independently scoped questions and source access, not merely the author's conclusions.
- **Publish the audited summary/evidence to GitHub** (work branch/PR), not raw secret-bearing logs.

An authorized child can perform **only** its assigned role. Git push/merge/release privileges are not inherited by default.

## 5. Proposed progression

- **P0 — Read-only discovery:** Check CLIs, versions, safe invocation/permission options, access limits; publish capability matrix on GitHub.
- **P1 — Nonmutating smoke test (separate authorization for any paid model usage):** One synthetic task each, verify outputs and logs, compare behavior and actual cost.
- **P2 — Delegation in Gate 0/1:** Split independent research, fixture/test design, adversarial review; Codex integrates and publishes PRs, reviews and limitations.
- **P3 — Code-writing delegated work (future separately scoped):** Extend the isolation and least-privilege controls required from the first execution to code-writing tasks, with branch gating and automated validation. This does not grant Gate 2 executable PoC permissions. Building or running the actual dispatcher also requires separate Owner approval.

At any stage, missing Qoder/Kilo/OpenCode is a **capability shortfall**, not a reason to block in-scope Codex research; it can use its own subprocesses/subagents for independent work while labeling review provenance honestly.

## 6. Historical baseline (2026-11-21, original PR head c429243)

- GitHub issue and agent roles exist.
- This file supplies a design to connect the tools.
- **No executable orchestrator was built.**
- **No verification of the user's Windows machine is available to the author of this file.**
- **No Qoder/OpenCode/Kilo CLI has been launched by the assistant.**
- The user does not need to copy messages between agents once and only once an actual, validated dispatcher is running.
