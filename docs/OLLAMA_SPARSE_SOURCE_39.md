# Issue #39 — NTFS sparse source compatibility

**STORAGE_COPY_PASS / ONE_ATTEMPT_CONSUMED / INFERENCE_NO_GO.** See the final receipt below. Before this operation, Issue #36 closed as not completed after PR #38 merged at `3a59dd97bfb4396696511ac1ceede8b21d509d40`. The Issue #36 error log and spent marker were preserved. [Issue #39](https://github.com/kha997/ai-chatbot/issues/39) · [PR #38](https://github.com/kha997/ai-chatbot/pull/38).

## Read-only source receipt

All six full SHA-256 digests and logical lengths matched the pinned allowlist. A single 1 MiB buffer and a 64 MiB/s read limit bounded memory and I/O. Canonical path, file ID, single-link count, last-write time, attributes and default-stream-only checks held across the read. Only the five blobs carry the sparse flag. Allocation below is reported by NTFS for each open handle. No source attributes or contents were changed. [Pinned manifest and full digests](OLLAMA_QWEN3_14B_STORAGE_MANIFEST.json).

| File | Logical bytes | Allocated bytes | Sparse flag |
| --- | ---: | ---: | --- |
| Config blob | 488 | 65,536 | Yes |
| Model blob | 9,276,184,896 | 9,276,227,584 | Yes |
| Template blob | 1,723 | 65,536 | Yes |
| License blob | 11,338 | 65,536 | Yes |
| Params blob | 120 | 120 | Yes |
| Manifest | 859 | 4,096 | No |

The sanitized six-file local verification receipt SHA-256 is `0b8ac3edf99228def74ca8f7cb7e5e8eca8dacf39a4fe3a85909686d70a9a1b3`.

## Synthetic evidence and gate

Technical SHA `dd642df26b9dabca35d8cb5bb07306d1f3a4c089`. The sole metadata exception is for pinned source blobs opened read-only. The exact SHA-256 and length checks remain before and during copying and on reopened outputs. The source manifest, stage and destination continue to reject sparse files. The existing alternate-stream, hardlink, junction, no-overwrite, one-stage and 12 GiB guards remain.

`pwsh -NoProfile -File tests/Test-OllamaStorageCopy.ps1` used a genuine 1 MiB NTFS sparse file on D:, with written endpoints and less than half its logical length allocated. The pre-fix code rejected the source. The patch preserved the zero-filled logical content and source flag, and produced an ordinary destination with the same full digest. Nine check groups passed, including sparse output and manifest rejection, wrong hash and same-bytes wrong identity, alternate streams, hardlink, junction, cap, no overwrite, rollback and replay. A CLI invocation without approval was refused before any model path was opened.

Independent Codex reviewer `sparse39_review` verified the exact technical SHA and reran all nine groups. The source replacement test held the other checked metadata and full digest equal and changed only the NTFS file ID. The original NTFS rename window remains covered by final identity and full-hash checks. The Owner/SYSTEM ACL does not isolate concurrent code running as the same Windows principal.

The entry point verifies the new Issue #39 comment, immutable Git script blob, exact reviewed commit and pinned allowlist digest. The planned Issue #39 attempt uses a new exclusive `.issue39-copy-attempt` record. The Issue #36 record remains spent. At the end of the synthetic review, no full-size transfer or service startup had occurred.

### Historical Owner approval wording

```text
TÔI PHÊ DUYỆT đúng một lượt sao chép lưu trữ theo Issue #39, commit dd642df26b9dabca35d8cb5bb07306d1f3a4c089, allowlist SHA-256 52debe5e5fa772cc86df634751c505b1b73547cd5fb31e946469cceff442be38. Cho phép đọc logic blob nguồn NTFS sparse của qwen3:14b mà không sửa nguồn. Chỉ sao chép 1 manifest và 5 blob sang D:\ProjectData\AIChatBot\ollama-models, tối đa 12 GiB dữ liệu mới trên D: gồm staging. Không ghi đè, không thử lại, không khởi động Ollama, không nạp model, không dùng GPU và không gửi prompt hoặc POST AI. Agent Dispatcher, Gate 2 và production tiếp tục NO-GO.
```

### Final one-use copy receipt

The Owner posted the exact storage-only approval and PR #40 merged at `f95d2b331c501de45c48b864b2e349ccd48f4ea1`. The only live invocation ran from a detached checkout at technical SHA `dd642df26b9dabca35d8cb5bb07306d1f3a4c089`, from 06:57:59 to 07:11:56 UTC. [Owner approval](https://github.com/kha997/ai-chatbot/issues/39#issuecomment-7075616402) · [PR #40](https://github.com/kha997/ai-chatbot/pull/40).

The six non-sparse files totaled **9,276,199,424 logical bytes** and **9,276,207,712 bytes of measured file allocation**. The before/after D: free-space difference was 9,318,588,416 bytes, including possible unrelated disk activity. Both remained below 12 GiB. All six final SHA-256 values matched, and the read-only post-copy source rehash and metadata checks passed. The protected D: destination remains in place and staging was removed by the same-volume publish. The Issue #39 marker is consumed and the Issue #36 marker is unchanged. Zero Ollama startups, model loads, GPU work or AI POSTs. The shared service PID and read-only watcher state were unchanged. [Immutable Issue receipt with all six final digests](https://github.com/kha997/ai-chatbot/issues/39#issuecomment-7075781476).
