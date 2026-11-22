# Gate 1.5 agent pivot — Issue #28

**BLOCKED for a real qualification.** Retire Kilo Free live trials. The existing Qoder Pro account has included credits, but its request and native isolation boundaries are unverified. A separate local OpenCode/Ollama route is the preferred next qualification candidate once its own resources and containment are proven. The Windows watcher stays read-only. Dispatcher, Gate 2 and production remain **NO-GO**.

## Baseline and comparison

PR #27 was independently reviewed at `da50041e75429477a186547e13e40aec69444de0`. Runtime and tests match the activated SHA `5f9a05f65701f60c832732550aca9eafd6cb4d80`. The reviewer reran 46 no-egress tests. The PR merged as historical NO-GO evidence at `200ca19991c7737d0d2058cbe3dcd648b0c299a2`. The third live Kilo trial used one POST and recorded `unfinished_task`. The exact finish reason, terminal `[DONE]`, token count and full body remain unknown. The consumed Issue #20 and #26 state was preserved. [PR #27](https://github.com/kha997/ai-chatbot/pull/27) · [Issue #26 receipt](https://github.com/kha997/ai-chatbot/issues/26#issuecomment-7071017373).

| Route | Model, entitlement and spend control | Isolation and resources | Expected latency and value | Decision |
| --- | --- | --- | --- | --- |
| Qoder Pro, native Windows CLI 1.1.94 | Existing login and Pro plan confirmed. Usage snapshot showed positive remaining included credits and no remaining add-on credits. `DeepSeek-V4-Pro` was listed as a directly selectable candidate. The status command did not report an effective session model. No model was selected or changed for this work. Vendor docs describe metered credits and prepaid one-time packs. An account-bound cost stop and exact physical model-request count were not verified. | CLI exposes tool selection, output-token and retry controls. No verified Windows OS isolation and provider-only network boundary. | Cloud latency unmeasured. Potentially useful for independent code review with read-only tools after qualification. | **BLOCKED_COST / BLOCKED_ISOLATION** |
| OpenCode Free, WSL CLI 1.18.30 | Historical Beam Free attempt received HTTP 429 and consumed its approval. Current model, quota and provider cost boundary were not polled. | WSL mock containment is available. A current cloud adapter, auth and egress constraint have not been qualified. | Availability and remote latency unverified. Useful coding CLI if separately qualified. | **NO-GO for a cloud retry** |
| OpenCode plus a separate local Ollama instance | Stock `qwen3:14b` was present in Windows Ollama metadata, approximately 9.28 GB on disk. A dedicated offline route could avoid cloud billing. No project-private model store or local adapter was proven. | Windows loopback listener is shared host infrastructure and is reachable from WSL. Both binaries exist in Ubuntu. The stock model manifest was unavailable in the checked WSL stores. At capture the GPU had about 13.3 GiB VRAM free and the host about 4.8 GiB RAM free. Ownership and headroom are not reserved. | Cold load plus model evaluation, unmeasured. Good candidate for the fixed synthetic classification before testing coding quality. | **Preferred next candidate, currently BLOCKED** |

The Qoder checks used `status --output json` with allowlisted fields, `--list-models` with public model names only, and the existing desktop Profile/Usage views. The public record omits account identifiers, exact personal usage amounts and screenshots. Direct selection and a credit multiplier establish availability and pricing semantics. They do not establish a per-task credit ceiling, timeout-safe one-request enforcement, or account-specific protection against charges. Existing subscription renewal and a purchase triggered by a run are separate. No settings, payment methods, model defaults or subscriptions changed. [Qoder CLI usage](https://docs.qoder.com/cli/usage) · [Model selection](https://docs.qoder.com/cli/model) · [Credits](https://docs.qoder.com/Credits) · [Billing](https://docs.qoder.com/account/Billing).

## Windows and local isolation findings

The read-only Windows CIM query returned `Containers-DisposableClientVM` with `InstallState=2` (disabled), and the Windows Sandbox launch executables were absent from the checked System32 paths. No OS feature was enabled. Qoder's documented CLI permissions limit exposed tools and provide approval controls. Qoder's documented Windows terminal sandbox is an IDE feature. We did not establish that the installed native CLI runs in that sandbox. A temporary Windows working directory, Qoder plan mode, or launching a Windows executable from WSL supplies no independent host/filesystem boundary for that executable. No code was run to probe unrelated repositories or credentials. [Windows feature states](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-optionalfeature) · [Windows Sandbox network and mapped folders](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file) · [Qoder CLI permissions](https://docs.qoder.com/cli/permissions) · [Qoder IDE terminal sandbox](https://docs.qoder.com/user-guide/quest/terminal-and-sandbox).

Ollama inventory used local `GET /api/tags`, `GET /api/ps`, `GET /api/version` and the read-only `ollama show qwen3:14b` metadata command. The local tag digest was `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`, with Q4_K_M quantization and completion capability. Windows owned the listener on `127.0.0.1:11434`. WSL could reach it while no Ubuntu listener was observed on that port. No model was loaded at the snapshot. Neither endpoint ownership nor idle utilization establishes permission to reserve the host model or GPU. No service was started, stopped or reconfigured, and no model was pulled, copied or loaded. [OpenCode provider configuration](https://opencode.ai/docs/providers) · [Ollama local mode and model storage](https://docs.ollama.com/faq).

## Dispatcher mock evidence

A fixture-only runner enters the existing hash-verified Bubblewrap 0.13.1 profile from WSL with no external route. It mounts a single read-only synthetic record set, checks a distinct network namespace, canary invisibility, blocked workspace write, absent shell and stripped synthetic credential, then returns a single deterministic JSON result. The task packet is fixed to `mock`, zero model requests and zero incremental VND. There is one in-memory permit per fixture case. Success requires both exit 0 and the exact integer oracle. Raw error/output bytes are not in the audit receipt. The test harness exposes only the reviewed sandbox path and has no provider adapter or queue.

| Scenario | Recorded outcome |
| --- | --- |
| Success | One JSON result `{"catalog":2,"handoff":1,"total":3}`, exit 0, receipt emitted |
| Wrong oracle with exit 0 | `INVALID_ORACLE` |
| Nonzero exit | `CLI_ERROR`, exit 6 |
| Hung process | `TIMED_OUT`, exit -9 at about two seconds |
| Oversized output | `OUTPUT_CAP`; files bounded independently |
| Reuse of any fixture permit | Denied before subprocess creation |

All five subprocess cases passed the boundary checks, replay denial, child reaping and scratch cleanup. The unit suite passed **48 tests** in no-egress WSL. The scope/oracle regressions rejected real adapter selection, non-integer caps, duplicate JSON keys, boolean fields and multiple JSON results. Independent Codex reviewer `pivot_review` evaluated exact technical SHA `15e8289b00193ce0f49a4e32f788ce0bc3e7a610` and reran the two contract tests and all five mock subprocess cases. The output limit comes from the deterministic fixture's file-size limit and the permit is per mock instance. This intentionally tests dispatcher bookkeeping and the Linux mock boundary. It does not exercise a real provider adapter, durable release authorization or a Windows isolation boundary.

```bash
unshare --user --map-current-user --net python3 tests/run_dispatcher_mock.py /home/zen/.aichatbot-issue18/bwrap
```

## Owner decision

Do not request a real prompt on the current evidence. Prefer the isolated local route to prepare next, using only a project-owned copy of a pinned stock model, a disposable WSL profile with no external route, a dedicated loopback endpoint, fresh CLI state and a preflight resource reservation that leaves shared projects unaffected. Confirm no cloud/plugin fallback, one model request, time and output limits, and complete cleanup using metadata and mock traffic first. Only after those checks can the Owner decide on one exact-SHA synthetic prompt with no retry and 0 VND cloud spend. Keep the shared Windows service and other projects outside the qualification. Qoder can be reconsidered once its native isolation, exact request count and account spend stop can be demonstrated.

No prompts were sent to Qoder, OpenCode, Kilo or local Ollama. No credit was purchased and no schedule or deployment was changed.
