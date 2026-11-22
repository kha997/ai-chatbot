# Issue #34 — OpenCode SDK loopback qualification

**SDK_MOCK_PASS.** The installed OpenCode 1.18.30 Linux ELF selected the bundled AI SDK for `local-ollama/qwen3:14b`. Technical commit `ac9287fd9ae81d4ecee92ae8893c47a14c1b4036`; ELF SHA-256 `87bd160e053af86b5b409daabf71f8dc05bbc3a2a3a5f563f36011cdf706a999`. [Issue #34](https://github.com/kha997/ai-chatbot/issues/34) · [Bundled SDK source](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/packages/opencode/src/provider/provider.ts).

| Check | Observed |
| --- | --- |
| HTTP | One `POST /v1/chat/completions` to `127.0.0.1:11435`, 651 request bytes under a 16 KiB body limit, expected model, streaming, output cap 128 tokens, two messages and zero advertised tools. Zero catalog requests, retries or other requests reached the mock. |
| Response and CLI | HTTP 200, 615 bytes of mock SSE including the terminal event, one text event, one step finish, zero error and tool events. Exact parsed JSON `{"catalog":2,"handoff":1,"total":3}`. OpenCode exited 0. |
| Isolation and cleanup | WSL private user and network namespaces with loopback only, no external route and no capabilities. Pinned Bubblewrap with private PID/mount namespaces, synthetic read-only fixture, cleared environment, disposable 64 MiB scratch, and no host drives, home, Windows interop or GPU nodes. The CLI PID was reaped, the sandbox exited, the mock socket closed and fixture scratch was removed. Zero real AI requests or dependency downloads. |
| Limits and regression | 24 s CLI watchdog, 29 s outer sandbox deadline, up to two logical CPUs, 8/10 s soft/hard CPU time, 96 FDs, 128 tasks and 32 KiB per captured stream. Two gate contracts and the earlier three transport-fixture cases passed. |

Independent Codex reviewer `sdk34_review` replayed technical commit `ac9287fd9ae81d4ecee92ae8893c47a14c1b4036` in a fresh namespace. The reviewer confirmed all result counts, exact oracle, exit 0, fixture-owned cleanup and both focused gate contracts. A pre-existing listener on port 11435 in the main WSL network namespace was outside the fixture and left alone. PR #33 was merged as offline evidence at `6fb993dede67d1c3fa7914f20c541f02ae7adc1d`. [PR #33](https://github.com/kha997/ai-chatbot/pull/33).

During setup, the mock rejected the extra literal quotes that 1.18.30 adds around a positional argument containing spaces. Passing individual tokens preserves the exact fixed synthetic message. One unqualified run received HTTP 200 and timed out without CLI output. The qualified profile caps CPU affinity and uses explicit HTTP/1.1 close framing. The cause of the earlier timeout was not isolated. The HTTP counts cover requests that reached the fake server. The namespace blocks external destinations independently of those counts. [CLI positional argument handling](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/packages/opencode/src/cli/cmd/run.ts).

For a local replay, supply a reviewed pinned Bubblewrap artifact to the mock runner. This example runs from the repository root in Ubuntu WSL and sets up a new network namespace for the entire test.

```bash
py=/usr/bin/python3
bwrap="$HOME/.aichatbot-issue18/bwrap"
unshare --user --map-current-user --net --keep-caps bash -c '
  /usr/sbin/ip link set lo up &&
  exec /usr/bin/setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"
' bash "$py" -Bu tests/run_opencode_sdk_mock.py "$bwrap"
```

## Separate Owner decision — one empty Linux Ollama startup

The Owner approved one supervised startup of the installed Ollama Linux 0.31.1 for read-only version and model-list checks, conditional on successful preflight. [Owner approval](https://github.com/kha997/ai-chatbot/issues/34#issuecomment-7072288797).

- Use a new private NTFS folder at `D:\ProjectData\AIChatBot\ollama-empty-test`, mapped from `/mnt/d/ProjectData/AIChatBot/ollama-empty-test` and exposed as the only host write mount at `/store` with `OLLAMA_MODELS=/store`. Preflight the fresh path, ownership, absence of reparse points and contents, and owner/SYSTEM ACL. Set `OLLAMA_NO_CLOUD=1` and `OLLAMA_NOPRUNE=1`. Leave the shared Windows and WSL services outside the namespace. [Ollama 0.31.1 environment configuration](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/envconfig/config.go).
- Preflight available host RAM and enforce CPU quota of one logical CPU, 1 GiB memory, zero swap and a 64-task limit before startup. Require a private no-egress namespace, synthetic home, no host sockets or GPU device mounts, and a bounded way to trace device-open attempts by the daemon and its children. Start once on `127.0.0.1:11436` inside that namespace. Allow one `GET /api/version` and one `GET /api/tags`. Verify version, empty tags and any store directories actually created on D. The probe has a 30 s total hard watchdog. GPU device-open attempts, missing isolation or tracing, budget or path failures, and unexpected activity end the probe as **BLOCKED**.
- Terminate the private process group, verify listener and children are gone, and remove only that run's verified scratch and D: test folder. This approval scope covers zero POSTs, pulls, copied model bytes, model loads and GPU work. Model copy and inference remain blocked. Agent Dispatcher, Gate 2 and production remain **NO-GO**.

## Historical follow-up offline preflight

**BLOCKED_GPU_OBSERVABILITY.** The one startup slot remains unused. The GPU denial and 30 s cleanup margin were exercised using inert Python processes. The approved gate still requires a bounded way to observe device-open attempts by Ollama and its children. The available WSL environment has neither a verified syscall tracer nor readable tracefs event lists. [Owner approval](https://github.com/kha997/ai-chatbot/issues/34#issuecomment-7072288797) · [Follow-up directive](https://github.com/kha997/ai-chatbot/issues/34#issuecomment-7072350835).

From the PR worktree in Ubuntu WSL, replay only the Python probes with `/usr/bin/python3 -Bu tests/run_ollama_empty_preflight.py "$HOME/.aichatbot-issue18/bwrap"`. Exact fixture commit `f5ec7eaead715d17047101532e7e0566a7b434d6`. The runner accepts no daemon command. It verifies the pinned Bubblewrap digest and reads the effective cgroup values `cpu.max=100000 100000`, `memory.max=1073741824`, `memory.swap.max=0`, and `pids.max=64`.

The post-exec child verified distinct PID/mount/network namespaces, private tmpfs at `/dev`, no GPU device mounts, no host home/drives, no WSL GPU library path and only stdin/stdout/stderr FDs. The mount inventory showed standard pseudo-devices, the synthetic script, the Python runtime and its read-only library trees. All seven direct open attempts returned `ENOENT` for `/dev/dxg`, both tested DRI nodes, three NVIDIA nodes and `/dev/kfd`. WSL exposed `/dev/dxg` outside the test. Private loopback refused TCP port 11434. The prospective daemon binary, D: store mount and syscall behavior remain to be verified before startup.

| Synthetic case | systemd unit seconds | Monotonic seconds through cleanup |
| --- | ---: | ---: |
| Normal exit | 0.637 | 0.7539 |
| Blocked socket accept | 25.155 | 25.2993 |
| Busy parent and child holding a listener | 25.109 | 25.2291 |

systemd applies `SIGKILL` to the whole cgroup after 25 seconds. Both stuck cases reported a timeout and SIGKILL. The child TCP socket was confined to an unpinned namespace. The units, cgroups and Linux scratch directories were gone after the run, and port 11436 had no host-side listener. Independent Codex reviewer `empty_preflight_review` reviewed the exact fixture and passed it for synthetic evidence. The `systemd-run` client-timeout exception requests a stop and exits without asserting cleanup. The timings cover the three measured cases. The fixture is solely for offline qualification.

A disposable NTFS directory on D: had only explicit Owner and SYSTEM access and passed a WSL-to-Windows marker write/read. The fixture was removed and the approved store path is still absent. The read-only watcher remained Ready, the Windows Ollama listener kept the same PID and the existing WSL Ollama process was left alone.

Zero Ollama startups, API GET/POST, GPUs accessed, model loads or model copies. Keep the existing one-use approval unconsumed. If device-open tracing remains unavailable, any change to the observation criterion requires a clarification on Issue #34. A later manual instruction is required for execution.

## Final one-use empty-store receipt

**PASS — authorization consumed.** The Owner accepted enforced GPU denial in the exact Ollama sandbox in place of per-open tracing. The original one-start limit and two GETs remained in force. Launcher SHA `050638d2710b6d6b7ceced2b95f87ddf4169fc42`. Ollama Linux ELF SHA-256 `cd0f8bac72d0441ae75bdb182f1f75a7b8dfa63f2e1d16bc31fa570523b1d7c9`. [One-start approval](https://github.com/kha997/ai-chatbot/issues/34#issuecomment-7072288797) · [Owner clarification](https://github.com/kha997/ai-chatbot/issues/34#issuecomment-7072525079).

- Final dry preflight passed with the actual binary and Owner/SYSTEM-only empty D: store bound at `/store`. The audited mount allowlist, private `/dev` and PID-local `/proc` prevented host device, FD and Windows interop access. GPU opens were denied. After startup, the runtime process and accessible descendants passed namespace, mount, process-root, capability and device-FD inspection. The only listener in that namespace was `127.0.0.1:11436` and the private network had no egress.
- Exactly one `ollama serve` process was started. One `GET /api/version` returned HTTP 200 and `{"version":"0.31.1"}`. One `GET /api/tags` returned HTTP 200 and `{"models":[]}`. Windows confirmed that Ollama created empty `blobs` and `manifests` directories in the approved D: store. Zero POSTs, model copies or loads, inference or GPU workloads.
- The exact cgroup read back CPU quota 100%, memory 1 GiB, swap 0 and tasks 64. The 25 s external systemd cgroup SIGKILL fallback remained armed and did not fire. The supervisor ended the daemon after the two GETs. systemd reported 1.262 s. The launcher including Linux scratch cleanup took 1.380924 s. The Windows stopwatch measured **2.5496532 s** from before store setup to completion of store cleanup. The controller then verified no fixture unit, cgroup, process, socket or scratch remained. The pre-existing WSL and Windows Ollama PIDs and the read-only watcher were left alone.
- Independent Codex reviewer `review_empty_once` reviewed the exact launcher and confirmed bounded use, conditional on the separate full host timing and cleanup checks. The live run was performed once by the lead. The local one-use record was marked consumed. Agent Dispatcher, Gate 2, production, model storage copy and inference remain **NO-GO**.
