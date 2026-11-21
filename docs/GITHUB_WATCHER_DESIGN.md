# Local GitHub work watcher

Issue #5 runs one Windows Task Scheduler entry for `kha997/ai-chatbot` under the current signed-in user with limited privileges. The trigger repeats every 30 minutes while Windows and the interactive session are available. A first trigger two minutes after installation supports commissioning. The task can run after a missed start when available. It does not wake the PC. The action uses a copied Python snapshot in `%LOCALAPPDATA%\AIChatBotWatcher` and the existing Python executable with isolated mode enabled.

## What enters the queue

| Source | Route | Status |
| --- | --- | --- |
| Open issue or PR | Exact `agent:codex`, `agent:qoder`, `agent:opencode`, `agent:kilo` labels. With no label, use an explicitly mapped assignee. | Triage |
| Open issue | Reviewed approval table in code tied to Owner authorization and GitHub OWNER authorship. Initially Issue #5 for Codex. | Approved queue entry |
| Open non-draft PR | Explicit `review:<agent>` label or current GitHub review request to a mapped identity | Review requested |

The only verified login mapping is `kha997 → codex`. Other agents can be routed using labels. Unmapped staff/team names create no inferred assignment. Approval table updates require a linked Owner decision in a reviewed PR. A label, assignment, or review request is a discovery signal. The program has no execution or authorization path for any queue entry. Codex can read `state.json` via Status without asking the Owner to relay GitHub content.

## Boundaries and failure recovery

- Public anonymous HTTPS GET to the fixed repository Issues and Pulls endpoints. No token, proxy, redirect, subprocess, prompt, outbound notification or GitHub write path. Lead publishes evidence manually via PR.
- Up to five pages of 50 per endpoint and up to 8 MiB per page. If the cap is reached, fail visibly and preserve the prior queue. Five-second network timeout, one retry for transient network/5xx, and two-minute scheduler process cap. Rate/access denial waits at least an hour. Failures back off up to four hours.
- Scheduler ignores concurrent invocations. An OS-level file lock also prevents concurrent manual polls. State replacement is atomic under the lock. State contains type/number/agent/status/PR SHA, hash, timestamps, last success and sanitized status. Issue text and credentials are excluded. Canonical hash suppresses duplicate changes across restarts.
- Queue statuses are local discovery records. PR head changes and removed matching work update the hash. Network or parse failures preserve the previous successful queue and its timestamp.

## Runbook

Run from the reviewed checkout in PowerShell:

```powershell
& .\scripts\Manage-GitHubWatcher.ps1 -Action Status
& .\scripts\Manage-GitHubWatcher.ps1 -Action Install
& .\scripts\Manage-GitHubWatcher.ps1 -Action Enable
Start-ScheduledTask -TaskName 'AIChatBot-GitHubWatcher' -TaskPath '\'
& .\scripts\Manage-GitHubWatcher.ps1 -Action Status
& .\scripts\Manage-GitHubWatcher.ps1 -Action Disable
& .\scripts\Manage-GitHubWatcher.ps1 -Action Enable
& .\scripts\Manage-GitHubWatcher.ps1 -Action Uninstall
```

Install registers a disabled task and writes a pause marker. Enable compares the installed file with the reviewed source. Disable stops this task and retains state. Uninstall removes only this task and retains the paused snapshot and queue for restore. Reinstall then enable to restore. If a snapshot differs, disable/uninstall and archive the reviewed installation's `github_watcher.py` by literal path before installing the new snapshot. If state is corrupt, disable the task and archive only `state.json` before enabling. Fresh polling rebuilds the queue. An unexpected task configuration must be inspected before any action.

Health is reported through Task Scheduler last/next run and result plus local last-success time, hash and counters. A zero scheduler result may mean backoff or pause. Check that `last_success` advances on a real poll. The Windows scheduler history channel can be disabled independently of this task. The account and relevant event values should be redacted in published evidence.

If managed controls refuse an unexpected registration, create the empty `%LOCALAPPDATA%\AIChatBotWatcher\paused` marker to stop the installed Python snapshot from polling. Inspect the exact task's action in Task Scheduler before disabling a modified registration there.

Use `python -m unittest discover -s tests -v` for deterministic checks. See [remote status](STATUS.md) for the on-machine observations.
