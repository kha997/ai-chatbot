# Issue #42 — one local coding prompt readiness

**BLOCKED_ADAPTER / BLOCKED_RESOURCES.** The same OpenCode SDK profile passed once and timed out once in this investigation. Windows RAM is below the proposed floor and no exclusive GPU window is reserved. The separate GPU-visible sandbox remains a design, so there is no exact launch for Owner approval yet. PR #41 merged at `14bc1546b97489befe8b2771ed97c9f5b57e114a`, and Issue #39 closed as storage completed and spent. [Issue #42](https://github.com/kha997/ai-chatbot/issues/42) · [PR #41](https://github.com/kha997/ai-chatbot/pull/41).

## Read-only snapshot and budget

| Resource | Observed on 2026-11-22 | Proposed admission floor or cap |
| --- | --- | --- |
| Windows physical RAM | 31.92 GiB visible. Free snapshots 5.83 GiB and 5.75 GiB. Memory compression, WSL and multiple browser processes held working sets. | At least **14 GiB available** at admission. Combined local trial cgroup maximum **12 GiB RAM**, allowing 2 GiB host margin against that cap. Halt on a host pressure event or cgroup OOM. |
| WSL | Ubuntu 24.04 on WSL2, kernel `6.6.87.2-microsoft-standard-WSL2`, 56 logical CPUs, configured 24 GB memory and 8 GB swap. Effective 23.46 GiB total, about 18.41 GiB available and 6.74 GiB swap free. CPU, memory and PID controllers are present. | At least **14 GiB WSL available**. Cgroup limits of **4 logical CPUs**, **zero swap** and **128 tasks**. No changes to shared WSL limits. |
| GPU | RTX 5060 Ti, Windows driver 610.88, 16,311 MiB total, 13,838–13,924 MiB free, 1–2% utilization. WDDM listed desktop/browser workloads and entries without process memory attribution. WSL exposes `/dev/dxg` and `libcuda.so.1`. | Owner-coordinated exclusive compute window with at least **13 GiB free VRAM**. Abort for unaccounted compute contention or less than 1 GiB device headroom while active. Free VRAM is an observation and per-cgroup VRAM enforcement is unverified. |
| Model store | NTFS on D:, 59,100,545,024 free bytes, exposed via WSL 9p/DrvFS. Six files totaling 9,276,199,424 bytes in the private store. Both copy markers consumed. Shared Windows Ollama listener retained its PID. | Read-only D: mount of the existing six-file store and bounded disposable runtime scratch. No additional transfer. |

For a single 2,048-token sequence, the upstream Qwen3-14B dimensions give an estimated **320 MiB** f16 KV cache (40 layers × 8 KV heads × 128 elements × 2 K/V × 2 bytes × 2,048 tokens). The 8.64 GiB store size is a planning proxy for weights. Allow about 2 GiB for device runtime/workspace and about 2 GiB for headroom, yielding the 13 GiB admission floor. This estimate has no measured load peak. Today’s VRAM snapshot clears the numeric floor, but the RAM and exclusivity conditions fail. No CPU-only fallback is proposed. [Qwen3-14B configuration](https://huggingface.co/Qwen/Qwen3-14B/raw/main/config.json) · [NVIDIA WSL driver and tooling limits](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

## SDK mock evidence

The installed OpenCode 1.18.30 ELF (`87bd160e053af86b5b409daabf71f8dc05bbc3a2a3a5f563f36011cdf706a999`) ran the existing `tests/run_opencode_sdk_mock.py` from `14bc1546b97489befe8b2771ed97c9f5b57e114a` (script Git blob `d0532693dd1f307362f2279220b0ee47d61e9e7a`). Each invocation used fresh WSL loopback and the pinned Bubblewrap profile from Issue #34. The only provider endpoint was `127.0.0.1:11435` in that network namespace. Outside routes, credentials and host mounts were unavailable. [Existing launcher and repro command](OPENCODE_SDK_MOCK_34.md#issue-34--opencode-sdk-loopback-qualification).

| Run | Mock requests and response | CLI result |
| --- | --- | --- |
| Historical Issue #34 PASS | 1 POST, no auxiliary request, HTTP 200 SSE | Exit 0, exact synthetic JSON. |
| Historical PR #35 merge replay | 1 POST, HTTP 200 SSE written | Timeout, exit -9, no JSON. |
| Issue #42 run 1 | 0 requests reached the mock | Timeout, exit -9, no JSON; 29.216 s wall time including launcher. |
| Issue #42 run 2 | 1 POST, no auxiliary request, HTTP 200 with 615 SSE bytes written | Exit 0, one text/finish sequence, exact synthetic JSON; 7.016 s wall time. |

Both fresh runs reported clean reaping, socket closure and scratch removal, zero tool events and zero real model POSTs. The first run had no SDK runtime selection marker. The current timeout is reproducible as an intermittent outcome. Its cause is unknown, and it differs from the earlier replay that reached HTTP 200. The mock audit records traffic arriving at the fixture. The no-egress boundary separately prevents cloud traffic.

## Proposed task and one-run limits

Ask for a small bug fix in the supplied synthetic Python function `combine_windows` in `tests/fixtures/local_prompt_42/availability.py`. Given sorted or unsorted half-open intervals `[start, end)`, merge overlaps and preserve intervals whose boundaries merely touch. Ask for a single JSON object with `old` and `new` line strings, no tool calls or file writes, and include only the fixture source, rule and example in the task input. The fixed expectation is:

```json
{"old":"if start <= merged[-1][1]:","new":"if start < merged[-1][1]:"}
```

Parse the result with duplicate-key and size checks and require that exact one-line edit. Trusted test code applies the allowlisted change to a scratch copy. The model output is never executed as Python. Run `python -B -m unittest discover -s tests/fixtures/local_prompt_42 -v`. In this investigation the baseline failed only the adjacent-interval test. A trusted one-line replacement in a disposable copy passed all **3** tests.

- A future run needs a separately reviewed, GPU-visible Ollama 0.31.1 sandbox. Give only Ollama and its runner access to the verified WSL `/dev/dxg` node and pinned read-only CUDA/WSL driver libraries. Keep OpenCode GPU-blind in a separate PID/mount sandbox with synthetic HOME/XDG and no host `/proc`, Windows interop, real repository, credentials, project config, plugins, MCP or tools. Use only private loopback with no egress, a separate Ollama port, and a one-request bridge so OpenCode cannot access shared Windows port 11434. The GPU device and library allowlist, inherited FD audit, and cleanup need their own verification before activation.
- Mount the six-file D: store read-only at `/store`, set `OLLAMA_MODELS=/store`, disable cloud and pruning, and use a private writable tmpfs of at most **256 MiB** for runtime scratch outside the model path. The Ollama source creates the already-present `manifests` and `blobs` directories as needed and normalizes legacy colon-prefixed names at startup. The copied file names already use `sha256-`. That layout is compatible in principle; actual read-only startup and 9.3 GB mmap/model loading remain unverified. Abort on a write requirement or path/kernel failure without widening the mount. [Manifest and blob paths](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/manifest/paths.go) · [Blob normalization](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/server/fixblobs.go).
- One scheduled model, one runner, one request and no queue/retry. Pin `qwen3:14b`, context **2,048**, output **128 tokens**, temperature **0** and no thinking. Require proof that the bridge passes `max_tokens=128` and `reasoning_effort=none` to the Ollama OpenAI-compatible endpoint before authorization. Permit exactly one `POST /v1/chat/completions` after validating the synthetic body, with a 16 KiB request and 256 KiB response ceiling. No auxiliary generation or tool calls. Cap setup plus response at **90 s**, kill the whole private cgroup by **105 s**, and require cleanup by **120 s**. Record timings, GPU/RAM peaks, physical request count, oracle/test results and cleanup. Do not generalize a single successful run to agent reliability. [Ollama runtime settings](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/envconfig/config.go) · [OpenAI-compatible option mapping](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/openai/openai.go).

The lowest-cost next step is to diagnose the SDK startup timeout using the existing offline profile, without touching the model or running more attempts under this issue. Only after stable mock results would a manually coordinated idle window on the same hardware be worth scheduling. No approval is requested now. No Ollama startups, model loads, GPU inference, AI prompts, new copies or shared-service changes occurred. Dispatcher, Gate 2 and production remain **NO-GO**.
