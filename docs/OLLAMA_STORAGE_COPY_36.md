# Issue #36 — one storage-only export

**READY_FOR_STORAGE_OWNER_GATE.** PR #35 merged at `b89497fed8fe070c200c52ff1ced8ffc68cf9a68` as historical evidence. Issue #34 is closed and its Ollama startup approval is consumed. Issue #36 has no copy approval. The implementation has been tested only with synthetic files on D:. [Issue #36](https://github.com/kha997/ai-chatbot/issues/36) · [PR #35](https://github.com/kha997/ai-chatbot/pull/35).

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
