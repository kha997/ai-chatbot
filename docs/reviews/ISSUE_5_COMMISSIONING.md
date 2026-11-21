# Issue #5 commissioning evidence

Date 2026-11-21, Asia/Saigon. Author and runtime verifier: lead Codex. Independent read-only reviews: separate built-in Codex session `issue5_review`, with shared vendor/model family. The reviewer did not install or operate the watcher.

| Evidence | Result |
| --- | --- |
| Governance PR #6 | Reviewer approved exact head `3b90f70c33735787f7e67aa2a8a7c73102a4a36a`. Merged `8d7949470cf3df4b1f77165f779b80f208085afd`. |
| CLI version and no-prompt help | Qoder 1.1.94, OpenCode 1.18.30, Kilo 7.8.32 exit 0. Qoder npm fallback had a libuv error and was removed. [Paths and publisher verification](../AGENT_CLI_READINESS.md). |
| Static checks | `python -m unittest discover -s tests -v` passed 5 tests. PowerShell parse and `git diff --check` passed. Coverage includes owner approval, routing, timeout retry, malformed response, lock, pause and restart/duplicate suppression. |
| Independent review | Initial findings on task identity validation, ambiguous Python path and mutable labels as approval resolved. Reviewer also caught unsupported scheduler settings and broad write grants on the checkout. Final GO at `385079f850a9306b5d5353639b1774c6c25e88c6`. Installed Python script matched Git blob `e493a8199197e562a3e1bcd484bba325ed337dd1`. |
| Host compatibility | AppData action failed first with `0x8007010B`, then Python exit 2. Temporary read-only diagnostic on the scoped task showed the script missing in its AppData view and profile directory visible. Shared checkout was rejected due to broad ACLs. Final private profile directory/snapshot grants only the current user, SYSTEM and Administrators write access. No ACL or scheduler logging policy changed. |
| Real scheduler action | Manually started through Task Scheduler at 10:00:51. Task result 0. Public GitHub discovery found one approved entry for Issue #5 / Codex. Second scheduler run advanced last success and retained the same queue hash and last-change time. |
| Pause and recovery | Disabled task and pause marker confirmed. Enable restored Ready and cleared marker. Uninstall removed the single task and preserved exact queue bytes. Reinstall and enable restored the task with those same queue bytes. |
| Automatic trigger after restore | Task Scheduler fired without a manual start at 10:03:05. LastTaskResult 0, last_success advanced to 1795230186, zero failures, same 1-entry queue hash. Scheduler readback showed next run at 10:33:05 and PT30M repetition. |

Watch task settings: 30 minute interval, limited interactive principal, two minute hard limit and IgnoreNew. Check runtime evidence via scheduler last result and queue last success together. The scheduler Operational channel was disabled on this host. Last-run fields and local state were verified without changing that system policy. The watchers' CLI access and queue tests involve no AI prompt calls. This implementation preserves the earlier Gate 2 scope.
