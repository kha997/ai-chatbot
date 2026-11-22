# Issue #34 — OpenCode SDK loopback qualification

**SDK_MOCK_PASS / EMPTY_DAEMON_OWNER_APPROVAL_PENDING.** The installed OpenCode 1.18.30 Linux ELF selected the bundled AI SDK for `local-ollama/qwen3:14b`. Technical commit `ac9287fd9ae81d4ecee92ae8893c47a14c1b4036`; ELF SHA-256 `87bd160e053af86b5b409daabf71f8dc05bbc3a2a3a5f563f36011cdf706a999`. [Issue #34](https://github.com/kha997/ai-chatbot/issues/34) · [Bundled SDK source](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/packages/opencode/src/provider/provider.ts).

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

Proposed approval wording. “I approve one supervised startup of the installed Ollama Linux 0.31.1 in the Issue #34 empty-store scope below, for read-only version and model-list checks.”

- Use a new private NTFS folder at `D:\ProjectData\AIChatBot\ollama-empty-test`, mapped from `/mnt/d/ProjectData/AIChatBot/ollama-empty-test` and exposed as the only host write mount at `/store` with `OLLAMA_MODELS=/store`. Preflight the fresh path, ownership, absence of reparse points and contents, and owner/SYSTEM ACL. Set `OLLAMA_NO_CLOUD=1` and `OLLAMA_NOPRUNE=1`. Leave the shared Windows and WSL services outside the namespace. [Ollama 0.31.1 environment configuration](https://raw.githubusercontent.com/ollama/ollama/v0.31.1/envconfig/config.go).
- Preflight available host RAM and enforce CPU quota of one logical CPU, 1 GiB memory, zero swap and a 64-task limit before startup. Require a private no-egress namespace, synthetic home, no host sockets or GPU device mounts, and a bounded way to trace device-open attempts by the daemon and its children. Start once on `127.0.0.1:11436` inside that namespace. Allow one `GET /api/version` and one `GET /api/tags`. Verify version, empty tags and any store directories actually created on D. The probe has a 30 s total hard watchdog. GPU device-open attempts, missing isolation or tracing, budget or path failures, and unexpected activity end the probe as **BLOCKED**.
- Terminate the private process group, verify listener and children are gone, and remove only that run's verified scratch and D: test folder. This approval scope covers zero POSTs, pulls, copied model bytes, model loads and GPU work. Model copy and inference remain blocked. Agent Dispatcher, Gate 2 and production remain **NO-GO**.
