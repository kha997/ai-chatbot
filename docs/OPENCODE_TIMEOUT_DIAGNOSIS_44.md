# Issue #44 — OpenCode mock timeout diagnosis

**BLOCKED_ADAPTER_UNRESOLVED / BLOCKED_RESOURCES.** Two instrumented runs passed. Neither reproduced a timeout, so the historical failure mechanism remains unknown. PR #43 merged as factual blocked evidence at `d5304c3acaf7b1251587802819a492e5a56edee0`. Issue #42 remains open as the resource and inference record. [Issue #44](https://github.com/kha997/ai-chatbot/issues/44) · [PR #43](https://github.com/kha997/ai-chatbot/pull/43).

## Existing failure evidence

| Receipt | Observed boundary | Limit of the evidence |
| --- | --- | --- |
| Issue #34 PASS at `ac9287f` | One mock POST, HTTP 200 SSE, expected JSON, exit 0. | Demonstrates one successful offline SDK exchange. |
| PR #35 final replay at `99ee3ea` | SDK selected and one POST audited. Mock returned from writing 615 SSE bytes, but stdout had zero events and the CLI timed out with exit -9. | No client receipt marker, SSE parse marker or pre-kill leader status. The boundary is after the server write and before any exported text or step result. |
| Issue #42 run 1 | Zero audited HTTP requests, no observed SDK-selection marker, zero stdout, 2,635 stderr bytes, exit -9 at timeout. | The old audit begins after request parsing. TCP accept, incomplete HTTP and the final startup stage were unobserved. |
| Issue #42 run 2 | One mock POST and 615 SSE bytes, exact JSON, exit 0. | Different outcome under the same checked-in invocation and configuration. |

The Issue #42 mock, worker and sandbox launcher were byte-identical to the PR #35 final replay. Compared with the qualified Issue #34 commit, the later mock only tightened the verdict for auxiliary calls and kept the same invocation, config and SSE fixture. The retained earlier debug receipt contains a separate HTTP 403 for a quoted prompt, with SDK selection, a stream error and disposal logged. It represents a different request and does not explain either timeout. [Issue #34 report](OPENCODE_SDK_MOCK_34.md) · [PR #35](https://github.com/kha997/ai-chatbot/pull/35) · [Issue #42 receipt](https://github.com/kha997/ai-chatbot/issues/42#issuecomment-7076156999).

All compared final profiles use the pinned OpenCode 1.18.30 ELF, fresh private HOME/XDG, the bundled OpenAI-compatible SDK, one explicit provider and disabled external/project discovery paths. The worker pins two logical CPUs, an 8/10 s soft/hard CPU limit, 128 tasks, 96 descriptors and 64 MiB scratch. The same Bubblewrap/seccomp profile and loopback-only namespace apply throughout. The current parent cgroup had no CPU quota, zero `avg10` CPU pressure at the preflight sample and a task limit of 14,999. Historical timeout CPU pressure, Bun worker state and counters were not recorded. Static configuration does not establish a runtime cause. [Bundled provider](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/packages/opencode/src/provider/provider.ts) · [CLI event emission](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/packages/opencode/src/cli/cmd/run.ts).

## Reviewed hypothesis and two observations

The worker drains both pipes before waiting for the leader. One testable hypothesis was that the leader had already exited while a descendant retained a pipe. At the watchdog, a live leader would exclude this explanation for the observed run. An exited leader and selector-registered pipe would require more evidence because unread EOF or buffered bytes can also keep a pipe registered.

The diagnostic-only change at `4452c1efe52719edae1a30f3843b57b25cd243d7` records a bounded set of monotonic phase observations and the leader/pipe state before any watchdog kill. It logs no raw CLI stderr, request contents or arbitrary process information. The TCP marker means server-side accept. The SSE marker means a completed fixture-side write and cannot establish client receipt. CLI markers timestamp observation of allowed log tokens. Independent reviewer `sdk44_review` approved this exact patch and hypothesis before the two invocations. Two gate contracts and a no-network synthetic probe passed. The probe distinguished an exited leader with a still-open inherited pipe from a live sleeping leader and validated that split markers are captured once.

| Observation | Run 1 | Run 2 |
| --- | ---: | ---: |
| Spawn to observed SDK selection | 5,112.917 ms | 4,409.778 ms |
| Observed SDK selection to mock TCP accept | 18.672 ms | 22.445 ms |
| End of mock SSE write to observed CLI text | 93.583 ms | 80.321 ms |
| Observed CLI text to observed exit | 87.819 ms | 93.292 ms |
| Reaped child CPU time | 7.293 s | 6.365 s |
| Launcher wall time | 7.075 s | 6.360 s |

Both runs made one POST with the pinned model and 128-token maximum, zero tools, zero auxiliary HTTP requests, and zero real model POSTs. Each received HTTP 200, emitted exactly `{"catalog":2,"handoff":1,"total":3}`, produced one finish event, closed both pipes and exited 0. Fixture process, socket and scratch cleanup passed. Neither watchdog fired, so neither observed the failing state. The successful CPU totals do not explain the historic timeouts. The two sanitized receipt digests are `58a49a301ce8032ad188c3d7a51fff72225932d29a8290604c7993f94dee015b` and `c0c46dfee507d736b1d4bdac33170ddb68671464e2944e03ead52b6df6aa1f1a`.

Stop at these two runs. There is no supported fix to the SDK or need to raise the time/resource limits. If a later Owner-approved model gate becomes feasible, one direct local Ollama HTTP smoke test could isolate the backend without the OpenCode adapter. It still requires a separately reviewed GPU-visible boundary, Windows RAM/headroom and an exclusive GPU window. No such approval is requested here. No Ollama start, model access or copy, GPU work, real prompt, package install, or shared-service change occurred. Agent Dispatcher, Gate 2 and production remain **NO-GO**.
