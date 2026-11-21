# Kilo HTTP 200 failure investigation

Date: 2026-11-21, Asia/Saigon. [Issue #16](https://github.com/kha997/ai-chatbot/issues/16). **Dispatcher remains NO-GO.** PR #15 merged as the original failure record at `ffb5f3bdded555b08d3e08b9a299698807f0172a`. The separately reviewed offline repair is in [PR #17](https://github.com/kha997/ai-chatbot/pull/17). New model requests: **0 for Kilo, 0 for OpenCode, 0 for Qoder**. Previous allowances remain Kilo 1/1, OpenCode 1/1, Qoder 0/1 and blocked.

| Evidence level | Finding |
| --- | --- |
| **CONFIRMED_OFFLINE** | The old relay ignored the HTTP media type and promoted every bounded UTF-8 HTTP 200 body to a local SSE 200. Feeding it a synthetic JSON error reproduced Kilo v7.8.32 exit 1 with no oracle result. The repaired relay reports `embedded_error` and returns a generic local 502. |
| **CONFIRMED_OFFLINE** | The historical per-line usage scan can raise a JSON decode error on a valid JSON event split across several `data:` lines. The repaired relay validates complete event frames and forwards accepted bytes unchanged. |
| **CONFIRMED_OFFLINE** | An in-cap, 32,768-byte SSE body could overflow the old Unix JSON envelope limit after escape expansion. Review reproduced this and the bounded Base64 frame now fits the full response cap. The 32 KiB model response cap itself is unchanged. |
| **CONFIRMED_OFFLINE** | A synthetic title-style request refused before Kilo starts leaves the permit available for the primary. The real CLI then completed valid fixtures with the expected JSON, and a deliberate duplicate was refused. This test does not exercise a title request emitted by Kilo itself. |
| **CONSISTENT_WITH_LIVE** | An error-shaped body, invalid MIME/encoding, incomplete or malformed SSE, empty answer, or a forwarding problem could yield an upstream HTTP 200 and a failing local task. The observed historical handler-exit flag does not certify protocol completion. |
| **UNKNOWN** | The original response body, headers other than recorded status, CLI output and nature of its second local request were not retained. None of the offline failures can be identified as that run's root cause. A native auxiliary failure, missing terminal event, output cap, provider response shape, or a CLI-output failure remains possible. |

## Frame and output semantics

The isolated bridge sends the canonical `text/event-stream` media type only after validation. It verifies a complete bounded Unix envelope, decodes the exact UTF-8 bytes, and sets Content-Length from the resulting bytes. It forwards accepted SSE data verbatim, including CRLF, keep-alives and multi-line `data:` framing. Inspection does not rewrite assistant deltas. For the fixed single-answer task, acceptance requires a text delta and choice zero with `finish_reason=stop`; `[DONE]` and usage are recorded independently and may be absent. This is a narrow qualification policy, not a general-purpose SSE gateway.

Kilo v7.8.32 emits completed parts as JSON-lines `type=text` and `type=step_finish`, and errors as `type=error`. The tagged run command can set exit 1 for either an error or a run ending without assistant output. A valid transport or HTTP status alone does not verify the JSON task oracle. The harness reports only status/media categories, counts, done/finish/usage flags, CLI exit class, oracle boolean and process/stream closure. It stores no raw CLI output, session IDs, prompts from logs, provider text or generated content. Sources accessed 2026-11-21. [Tagged Kilo run source](https://github.com/Kilo-Org/kilocode/blob/v7.8.32/packages/opencode/src/cli/cmd/run.ts) · [SSE framing specification](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream).

The runner in this branch has only mock and timeout modes. Provider hostname, HTTPS POST and live entry point were removed from it. The fixed task/model admission rules, tool prohibition, atomic permit, verified Linux ELF, read-only mounts, clean env, distinct loopback-only network namespace, seccomp, per-stream caps and process-group cleanup remain in place. The historical attempt marker was left intact. The Watcher, other projects and production were not changed.

## Reproducible evidence

- **RED** `dab0c9721724e849329a70930ff7f42bde80a9d2`. `python -m unittest discover -s tests -p test_kilo_sse.py -v` returned 12 failed subtest assertions and one UTF-8 decode error. The real pinned Linux CLI was separately run on the old relay with `json_error` and returned exit 1, oracle false, zero forwarded requests. The archived scan was separately exercised on the multi-line frame and raised `JSONDecodeError`.
- **GREEN** code `1a077759c8d2d80cd4c6704a1745a4b8c607b4e2`. `python -m unittest discover -s tests -v` passed **13 tests**: two existing Kilo guards, six watcher tests and five protocol/diagnostic tests, including 19 generated SSE/JSON fixtures. Fixture manifest SHA-256 `ec9d9365dca3c32935562f1ae276465d949e7eb08ac00ac5d496847ec13a03d2`, calculated over compact, sorted JSON mapping each name to media, byte SHA-256 and expected relay status. See [fixture definitions](../tests/test_kilo_sse.py).
- The separate fresh Codex session `offline_sse_review` independently reran RED and GREEN checks and found two issues. The lead addressed the relay envelope and negative-test false pass on timeout/output-cap failure. The reviewer rechecked the exact GREEN commit and the 32,768-byte wire round-trip. They made no live calls. PR #15's evidence-only review was by the separate `pr15_evidence_review` session.

From the WSL checkout, run `python3 tests/run_kilo_offline.py <verified-archive> <fixture-name>`. The existing pinned Kilo archive hash remains recorded in [Issue #14 evidence](GATE_1_5_KILO_ISOLATION.md). The runner fails if the offline fixture unexpectedly forwards a request, times out, exceeds output cap, misses boundary/cleanup checks, admits more than one request, or produces a mismatched result. Use `python3 scripts/kilo_gate15.py timeout <verified-archive>` for the expected SIGKILL cleanup case. The timeout case is separate from expected malformed responses.

**Real CLI integration:** 11 named fixtures passed their assertions on the exact GREEN code. The five valid cases (`crlf_usage`, `finish_only`, `no_usage`, `multiline_utf8`, `full_size`) yielded relay 200, child exit 0 and the exact oracle. In all five, the two injected auxiliary/duplicate requests were denied. The six rejection cases (`json_error`, `embedded_error`, `truncated`, `wrong_type`, `malformed`, `empty_choices`) yielded relay 502, child exit 1, an error event, no text result and closed streams. Each admitted one request, denied three local requests and forwarded zero externally. The positive default mock also passed. The separate timeout mode returned the expected child `-9`, closed both streams, forwarded zero requests, and a post-suite process check found zero remaining probe or Kilo children.

| Representative fixture | Body SHA-256 | Observed local status / CLI task result |
| --- | --- | --- |
| `crlf_usage` | `7c5168ef6b5f9649bff22bf232e799d5854a5693241e57c9a3f0f7e9feb27b98` | 200, correct JSON |
| `finish_only` | `2685de61f50ff02f766d23eb8e87ff42e9157fc7cdc43d2e16f079afc840616a` | 200, correct JSON, no DONE or usage |
| `multiline_utf8` | `a2afe29871c601a330896cc62264fa4170581b63dc1e54e3dec1f82b8ba1be20` | 200, correct JSON |
| `full_size` | `03d47657d44cd2b0d9499a4d625aa8f071e72a16444a9f6601a8d3db34b1086b` | 200, correct JSON across the bridge at 32 KiB |
| `json_error` | `28523ed7e560a71bd3e80f01e88d6b42429b3b9d68aac48d6b28ff3749488d82` | 502, error event, exit 1 and no task result |
| `embedded_error` | `1d03b8428759bfa82f6832ec15bbeddcdb80b20e3e31f9bd4743ccf4d631dc34` | 502, error event, exit 1 and no task result |
| `truncated` | `ff37b140c39c68dc72a420a4a398803b2a1f2b99ae623f8d6b2787ca5f671373` | 502, error event, exit 1 and no task result |

## Decision before a new live attempt

First qualify an independently reviewed one-attempt runner and supported, patched sandbox with the same exact model, pinned protocol, free-only/zero-incremental-price checks, one POST and redacted classifications. Separate explicit Owner approval is required because the Kilo allowance has already been used. A future measured hypothesis is that a provider response with accepted SSE framing and a stop finish yields Kilo exit 0 and the exact synthetic JSON. Success requires those observations together. Otherwise retain only the allowlisted status, classification, event counts, CLI error/exit category and cleanup evidence and stop without retries. No automated dispatch or product Gate 2 authorization follows from the offline repair.
