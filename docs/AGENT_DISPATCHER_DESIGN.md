# Agent CLI readiness and future dispatcher design

**Date:** 2026-11-21, Asia/Saigon. **Scope:** Issue #3, discovery and specification only.
**Recommendation:** explicit subprocess adapters under Codex supervision, with an enforceable OS isolation boundary. No dispatcher has been implemented or run.

## Observed capability matrix

| Environment/tool | Discovery | Version/help | Authentication / billing | Actual delegation |
| --- | --- | --- | --- | --- |
| Windows PowerShell Qoder (`qoder`, `qodercli`) | UNAVAILABLE on current PATH | NOT_RUN: binary absent | UNVERIFIED | NOT_RUN |
| Windows PowerShell OpenCode | UNAVAILABLE on current PATH | NOT_RUN | UNVERIFIED | NOT_RUN |
| Windows PowerShell Kilo | UNAVAILABLE on current PATH | NOT_RUN | UNVERIFIED | NOT_RUN |
| Existing running WSL Ubuntu-24.04 Qoder | UNAVAILABLE on login-shell PATH | NOT_RUN | UNVERIFIED | NOT_RUN |
| Existing running WSL Ubuntu-24.04 OpenCode | AVAILABLE `/usr/bin/opencode` | `1.18.30`; version, top-level help, run help, auth help exit 0 | UNVERIFIED; credential values and auth list deliberately not read | NOT_RUN |
| Existing running WSL Ubuntu-24.04 Kilo | UNAVAILABLE on login-shell PATH | NOT_RUN | UNVERIFIED | NOT_RUN |

Absence on these PATHs does not prove the application is absent everywhere on disk. No whole-disk/private-project search was performed. WSL and Windows are distinct execution environments. `wsl --list --quiet` and `wsl --list --running --quiet` identified Ubuntu-24.04 and docker-desktop as already running; only Ubuntu received read-only commands. Docker lifecycle/configuration was untouched.

OpenCode resolves to `/usr/lib/node_modules/opencode-ai/bin/opencode.exe`; despite suffix, `file` identified an ELF x86-64 Linux binary. Installed package metadata and executable both report 1.18.30. No package was installed or updated. Codex successfully spawned WSL and the binary for help/version using existing terminal access. This proves subprocess reachability, **not** authorized model usage, provider connectivity, permission enforcement or safe agent execution.

Readiness commands actually executed (each OpenCode command bounded by `timeout 15s`):

```text
Get-Command qoder,qodercli,opencode,kilo -ErrorAction SilentlyContinue
wsl --list --quiet
wsl --list --running --quiet
wsl -d Ubuntu-24.04 --exec sh -lc 'command -v ...'
readlink -f /usr/bin/opencode
file /usr/lib/node_modules/opencode-ai/bin/opencode.exe
cat /usr/lib/node_modules/opencode-ai/package.json
opencode --version
opencode --help
opencode run --help
opencode auth --help
```

The `command -v ...` line abbreviates the four-name loop, not a literal reproducible command; use `for c in qoder qodercli opencode kilo; do command -v "$c"; done` in the selected Ubuntu shell. Only nonsecret package metadata was read. No credential/configuration dumps, auth login, model list, provider probe, session export or prompt invocation occurred. Host terminal is allowed to spawn processes; it is not an agent sandbox and must not be presented as one.

## Upstream documentation, accessed 2026-11-21

- [Qoder run in scripts](https://docs.qoder.com/cli/run-in-scripts): headless `-p`, JSON/stream output and permission controls are documented. Installed behavior remains unverified because no binary was discovered. Never choose yolo/bypass for this project.
- [OpenCode CLI](https://opencode.ai/docs/cli): documents noninteractive `run`, and warns through its architecture that clients may discover/start a shared background service. Live docs can differ from local 1.18.30 help: do not assume a documented `--standalone` flag is locally supported. Local `run --help` exposes JSON event format, explicit model/agent/directory, `--pure`, attach/share and auto options. Treat attach/share/auto as prohibited in the planned adapter.
- [Kilo CLI](https://kilo.ai/docs/code-with-ai/platforms/cli): docs apply to 1.0+, show `kilo run`, version/help and provider auth commands. No installed-version or permission verification exists here.

These are documented capabilities, not end-to-end integration evidence. CLI/model terms and costs remain UNKNOWN. No new financial commitment is inferred from an existing subscription or executable.

## Alternatives and decision

| Method | Benefit | Cost/risk | Decision |
| --- | --- | --- | --- |
| Direct subprocess with versioned adapter | Least new infrastructure; explicit process lifetime, exit and output capture | Platform/version quirks; child privileges and background processes need OS containment | Recommended first design |
| MCP/SDK or server protocol | Structured lifecycle and tool interaction | More packages/services, network endpoints and credential exposure; not itself isolation | Revisit only when CLI cannot provide required evidence/control |
| GitHub issue queue | Durable asynchronous ownership and reports | Requires an authorized worker; issue text can inject instructions; does not launch local tools itself | Durable queue/report fallback, not operational dispatcher |
| Built-in Codex sessions | Available now for research and distinct-context scrutiny | Same system/model family, correlated blind spots; no claim of vendor diversity | Current research fallback |

## End-to-end task protocol (DESIGN, NOT IMPLEMENTED)

Task packet fields: `schema_version`, random `task_id`, parent issue, immutable `base_sha`, input-file hashes, prompt hash, role, expected artifact paths/schema, allowed public sources, `execution_profile`, permitted binary hash/version, explicit provider/model, approval reference, absolute deadline, token/output/retry caps, cost ceiling and review rubric. Missing approval/provider/cost boundary fails closed; a missing price is not zero cost.

State machine: `CREATED → POLICY_CHECKED → ISOLATED → RUNNING → COLLECTED → VERIFIED → PUBLISHED`. Alternate terminal states: `DENIED`, `TIMED_OUT`, `FAILED`, `CANCELLED`, `REVIEW_REQUIRED`. Only lead verification permits publication; exit 0 alone cannot.

1. Validate approved task scope and dependency versions. Reject executable requests during current Gate 0–1. Treat issue bodies, retrieved files and agent output as untrusted data.
2. Create an immutable read-only export for reviewer; for authorized writers later, create a dedicated worktree/branch. A worktree shares Git administration and is **not** an access-control sandbox. Never supply GitHub write credentials or host home-directory access to a child.
3. Enforce OS-level file/network/process boundaries before first prompt. Reviewer gets only public snapshot and allowlisted public-source access. Linux mount namespace/container/VM or Windows sandbox choice needs separately approved setup; none exists or is provisioned here. If enforceable isolation is unavailable, refuse actual dispatch, keep manual built-in research fallback.
4. Build argument arrays with `shell=false`, never interpolate task text into a shell command. Resolve executable allowlist and hash. Remove inherited credentials, proxy secrets, plugin/MCP configs and external project hooks. Inject only separately approved provider credential via protected mechanism, never argv or public log.
5. Runtime proposal: 10-minute deadline, at most one correction retry, 5 MiB captured output per attempt. Cost/token ceilings come from approved envelope and provider enforcement; a timer alone does not prevent overspend. Refuse launch if required caps cannot be enforced. Cap applies across retries and child calls.
6. Collect bounded stdout/stderr, structured result, exit code, timestamps, tool version and provider/model identity where available. Kill entire process group/job tree on cancellation/timeout and verify cleanup. Any daemon/shared-server/attach mode is rejected; do not stop unrelated running services.
7. Validate schema, baseline invariance, path confinement, artifact hashes, test outputs and citations. Reject symlinks/path traversal, unknown files, secret-like content and oversized artifacts. Failed/partial execution remains failure even if useful prose exists.
8. Separate fresh reviewer checks critical outputs. Lead may request one scoped correction against the same baseline or a newly explicit baseline. Retain redacted finding lineage and all failed outcomes.
9. Only lead stages reviewed files, commits/pushes to task branch, creates PR and updates status. Persist public summary with hashes and provenance; raw logs stay private/local and are never automatically uploaded.

Planned result envelope: task/base/prompt/artifact hashes; observed tool/model; start/end/exit; `PASS/FAIL/INCONCLUSIVE`; validation findings; usage values or `null`; attempted prohibited actions; redaction audit; reviewer/session identity and limitations; published commit/PR. Never put credential identifiers or account details in public artifacts.

## Future qualification before any actual delegation

Separate Owner authorization is required to build/run the dispatcher and for any billable call or new access. Recommended first authorized exercise: one synthetic read-only summarization with no repository writes, a fixed approved provider/model, enforceable spend cap and isolated temporary workspace. Include attempts to escape directory, invoke shell/network, access credentials, exceed output/deadline and ignore cancellation. Require zero unauthorized access and full process cleanup. Then qualify correction flow and GitHub publication by lead. These tests are all NOT_RUN.

Current outcome: Issue #3 discovery/design can complete despite Qoder/Kilo absence. Automatic four-tool delegation is **not ready**. Owner needs no technical choice now; any later spend/access/dispatcher approval must be concrete and separately scoped.
