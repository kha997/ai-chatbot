# Issue #36 — one storage-only export

**READY_FOR_STORAGE_OWNER_GATE at the synthetic review.** PR #35 merged at `b89497fed8fe070c200c52ff1ced8ffc68cf9a68` as historical evidence. Issue #34 is closed and its Ollama startup approval is consumed. The implementation was tested with synthetic files on D:. The Owner subsequently approved one storage-only attempt in Issue #36. The real copy was pending when this PR merged. [Owner approval](https://github.com/kha997/ai-chatbot/issues/36#issuecomment-7075133334) · [PR #35](https://github.com/kha997/ai-chatbot/pull/35).

| Item | Bound or evidence |
| --- | --- |
| Source | Current Windows profile's `%USERPROFILE%\.ollama\models`, opened read-only. One 859-byte manifest and five fixed blobs from the PR #33 allowlist, totaling **9,276,199,424 bytes** (8.64 GiB). The script verifies the allowlist's SHA-256 before using it. |
| Destination | Fresh `D:\ProjectData\AIChatBot\ollama-models`, also visible at `/mnt/d/ProjectData/AIChatBot/ollama-models`. The target was absent. D: was NTFS with 4,096-byte clusters and 68,429,983,744 bytes free at the offline snapshot. Recheck at execution and require at least 20 GiB free before writing. |
| Budget | **12,884,901,888 bytes** (12 GiB) total new storage. Projected allocation at the measured cluster size is **9,284,603,904 bytes**, including an 8 MiB allowance for directory and attempt-record overhead. The copy streams 1 MiB chunks and measures native file allocation during writes and on reopen. It also records D: free space before and after. Whole-volume free-space changes can include unrelated writes. |

After separate approval, run the following from a clean Windows checkout of the reviewed technical commit. Supply the numeric ID of the Owner's newly posted exact approval from Issue #36.

```powershell
pwsh -NoProfile -File scripts/Copy-OllamaStorage.ps1 -ApprovalCommentId <OWNER_COMMENT_ID>
```

1. The script checks the comment against the Issue #36 approval text and repository Owner identity. It checks the manifest digest, NTFS, the 20 GiB free-space floor and the fresh destination. The exclusive `.issue36-copy-attempt` record stays in the project parent across interruption or failure. Preserve it and reconcile any interrupted stage manually.
2. Hash all six read-only source handles before writing. Copy the blobs and then the manifest to one Owner/SYSTEM-only D: directory adjacent to the target. Each transfer and each reopened staging file must match SHA-256 and length. Reject link, unusual type, alternate stream, source mutation, identity or capacity failures. The I/O rate is capped at approximately 64 MiB/s including read and write work. True source integrity and current capacity will be checked only at the approved execution.
3. Publish by a single same-parent NTFS directory rename with no overwrite. Reopen the six final files and verify their full hashes again, then rehash the source handles and recheck source identity, size and last-write metadata. The receipt reports counts and byte totals without logging the Windows profile path to GitHub.
4. Before promotion, rollback checks the exact stage and recorded child identities and ACLs. It removes only those objects via validated NTFS handles, with no recursive delete or ignored entries. On an unknown entry, interruption, ambiguous ownership or post-promotion failure, preserve the remaining files and receipt for manual reconciliation. Normal reads may update filesystem access bookkeeping. The ACL isolates other Windows principals and has no separate security boundary against code already running as the same Windows account.

### Synthetic evidence

`pwsh -NoProfile -File tests/Test-OllamaStorageCopy.ps1` exercised six groups, including a six-file publish and full verification, allocation cap and existing destination rejection, late collision with the foreign sentinel preserved and stage removed, source timestamp change and attempt replay, junction rejection, and hardlink, alternate stream and same-length corruption rejection. Invoking the entry point without approval failed before opening any model files. Technical commit `9943b40143e0365a4eefd3cef2304adc0f138d3c`. [Windows handle sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) · [Handle-based deletion](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_disposition_info).

Independent Codex reviewer `storage36_review` reran those checks and verified the exact implementation, the pinned allowlist and the Issue #36 Owner text. NTFS requires releasing staging handles briefly for rename. Final identity and full hash checks detect observed changes across that window. The native allocation receipt counts file allocations separately from the metadata allowance.

This proposed approval covers one storage copy only. The shared Ollama listener and read-only watcher were left alone. Model startup, load, GPU use, inference, Agent Dispatcher, Gate 2 and production remain **NO-GO**.

### One-use attempt receipt

**BLOCKED_SOURCE_SPARSE_FILE / ONE_ATTEMPT_CONSUMED.** The Owner’s unedited approval matched the exact Issue #36 scope. PR #37 merged readiness evidence at `7374ec9b7a74417a0f42de4323f2a119efe2d15c`; the executable and pinned plan were unchanged from independently reviewed technical SHA `9943b40143e0365a4eefd3cef2304adc0f138d3c`. Six synthetic groups passed again before execution. [Owner approval](https://github.com/kha997/ai-chatbot/issues/36#issuecomment-7075133334) · [Merged PR #37](https://github.com/kha997/ai-chatbot/pull/37).

| Check | Observed |
| --- | --- |
| Start | 2026-11-22 06:09:16 UTC. D: was NTFS, 4,096-byte clusters, 68,427,800,576 bytes free. Project target, stage and one-use flag were initially absent. |
| Result | Exit 1 at the source file-attribute guard before opening the first blob for content or creating staging. Read-only follow-up inspected metadata for the exact six allowlisted paths. Canonical paths, single link counts and lengths matched. All five blobs were flagged `Archive, SparseFile`. The manifest was `Archive` only. |
| SHA-256 | Full source SHA-256 verification did not complete during this attempt. The previous Issue #32 digests remain historical evidence. There is no destination and no destination SHA-256 result. The execution performed no source writes. |
| Allocation and cleanup | Zero model bytes written, no stage created and no target created. Only the new project parent directories and one-use marker remain. Free space at the first post-failure snapshot was 68,427,771,904 bytes. This whole-volume reading includes unrelated activity. |
| Consumption | `.issue36-copy-attempt` is retained and explicitly marked `CONSUMED: BLOCKED_SOURCE_SPARSE_FILE`. Sanitized error category recorded here. SHA-256 of the unmodified private error log is `db3fcc696948e2bbbf519c96d528284189d1e7349a784e71779631d464a1a95e`. No retry. |

The synthetic files lacked the NTFS sparse attribute. A future candidate would need separate review of sparse files as read-only sources, bounded regular-file allocation on D: and a synthetic sparse-file regression. This attempt supplies no authorization to run that candidate. The Windows Ollama listener retained its PID and the watcher remained Ready. Ollama startup, GPU use, inference, Dispatcher, Gate 2 and production remain **NO-GO**.
