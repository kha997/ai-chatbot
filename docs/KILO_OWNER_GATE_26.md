# Kilo Free — Issue #26 Owner decision packet

**NO-GO after the approved live run.** The offline candidate reached `READY_FOR_OWNER_GATE`. The Owner authorized one manual run, which consumed the Issue #26 slot without a qualifying result. Further live Kilo runs are stopped pending the Owner's decision. Issue #20's approval and both spent markers remain consumed. Dispatcher, Gate 2 and production remain **NO-GO**. PR #25 was independently reviewed on exact evidence head `b4819d0b1475852aa3e132bc5f8a5e326ac47e85`, verified with 44 tests and merged as offline evidence at `f61d96f3360aeebd8f1547607dbe2c1fdd171dfd`. [PR #25](https://github.com/kha997/ai-chatbot/pull/25) · [Issue #20 historical receipt](https://github.com/kha997/ai-chatbot/issues/20#issuecomment-7061006163).

## Approved live result — 2026-11-22 (Vietnam time)

The unedited Owner comment matched the exact activation SHA, manifest, runner and expiry. The pin checks validated the source, Kilo archive and Bubblewrap, and a fresh Kilo sandbox fixture passed offline with the exact oracle. The real slot started unspent. The public preflight at 06:36:10 confirmed one exact model row with both prices zero. The exact launcher reserved the slot at 06:37:27 and created the separate POST claim at 06:37:46. [Owner approval](https://github.com/kha997/ai-chatbot/issues/26#issuecomment-7070955543).

| Signal | Observed result |
| --- | --- |
| Request | **One real anonymous HTTPS POST** to the approved model. No retry, redirect, model change or purchase. Both Issue #26 spent markers remain. |
| HTTP and SSE | HTTP 200, identity-encoded SSE. At rejection the body reader had observed 50,758 transfer-decoded bytes and the parser had processed 128 frames/events. Zero task-text bytes and zero bytes of SSE relayed to Kilo. Classification `unfinished_task`. Neither the required stop nor terminal `[DONE]` was validated. The full response size is unknown. |
| Task outcome | Launcher and Kilo exit **1**, one CLI error event, no finish step, and no validated JSON oracle. The relay returned 502 after rejecting the SSE. |
| Model, usage and cost | Model metadata appeared. The receipt marked model identity `REJECTED` because the stream did not qualify and did not classify a model mismatch. Token usage and per-attempt billing receipt are `UNKNOWN`. The route passed zero-price preflight and no purchase or billing setup was performed. |
| Time and containment | HTTPS worker exited and was reaped in 2,198 ms. Pipeline exited and was reaped in 25,136 ms. Boundary check passed, three auxiliary/duplicate requests were denied and output streams closed. The final WSL sweep found no runner, worker, Bubblewrap, Kilo or probe process and no staged Unix socket paths. |

The reviewed parser emits `unfinished_task` when it encounters a non-null `finish_reason` other than `stop`. The sanitized receipt does not preserve that value. The exact upstream reason, any later frames and whether a larger token allowance would change the outcome remain unknown. Both Issue #20 markers retained their original timestamps. Preserve both approval records and their consumed state.

## Exact request and identities

| Input | Identity |
| --- | --- |
| Activation commit | `5f9a05f65701f60c832732550aca9eafd6cb4d80` |
| Manifest SHA-256 | `25fa10942ca1d3f5dc1bf3f97377e63b5a4ab0c84aea92e415d7048a957aab18` |
| Issue #26 WSL runner binding | `f6ba9bcacd248f9eee11c04b17ce6d11b857faa4170f5668dc4a85333856313e` |
| Launcher SHA-256 | `cc05f16bb09b9ad1fa6cb094501f8eec753ed8cb4956c628de1d956ea2ebbe9d` |
| Kilo v7.8.32 archive | `ab7a008a2c0ca6e035b96cd1dc5712a8466a14a45992291a8f0b4b549b94136e` |
| Kilo Linux x64 ELF | `474675d07e520067440df780a239f05bded6da2ae9b78bb2b5d2c2291ab03046` |
| Private verified Bubblewrap 0.13.1 | `3acde20bf6dadc53dfa708e8c5bfb81e9564ab831b2b28216c3c976808b50520` |
| Canonical 269-byte synthetic task | `619f9c39002b302768504f283803000ddd2ee112b09f2ee3e6d98ceb846000cd` |

The manifest binds all six runtime Git blobs, archive, ELF, Bubblewrap, request digest and Issue #26 scope. The bootstrap checks launcher SHA-256 before starting isolated Python. The launcher stages the full dependency set only after verifying exact Git contents, and checks the archive and Bubblewrap before it reads any proof. The sandbox independently checks the extracted ELF before running it.

The future request is exactly one `POST https://ai-gateway.kilo.ai:443/api/v1/chat/completions` with `recursive/flint-v1.0:free`, the fixed synthetic task, streaming and `max_tokens=128`. Real TLS uses the fixed vendor hostname, installed system trust and certificate verification, TLS 1.2 or 1.3. The client makes one direct HTTP request on the verified connection with no authorization, keys, credential loading, configurable host, redirect, retry, account fallback or proxy.

## Free route and time limits

A public HTTPS GET to the Kilo model catalog at **15:17:11 UTC on 2026-11-21** returned one exact model row with prompt and completion prices both `"0"`. Kilo documents anonymous use for free models and zero billing for `:free` models. The activation performs a fresh, exact zero-price catalog GET after reservation. Missing, ambiguous or nonzero prices stop the attempt before a POST. Current quota and availability are unknown. Offline preparation sent no inference requests. [Authentication](https://kilo.ai/docs/gateway/authentication) · [Usage and billing](https://kilo.ai/docs/gateway/usage-and-billing).

| Boundary | Budget and rationale |
| --- | --- |
| Owner proof and catalog | Two separate 12 s hard workers for public GETs, up to 8 s per blocking metadata socket operation. |
| HTTPS inference worker | **24 s absolute** across resolution, connect, TLS, request write and bounded read. Verified with blocking sockets; the 1.5 s PR #25 stress budget would reject the valid fixture delayed by 4 seconds. |
| SSE reader | **23 s cooperative** after starting response reads. The 24 s process deadline interrupts blocked I/O even if the parser cannot check its clock. |
| CLI and complete pipeline | Existing 28 s Unix bridge wait, 40 s Kilo and 45 s sandbox process bounds. **55 s** absolute pipeline watchdog includes artifact extraction, process startup, TLS and relay cleanup. The metadata checks and git staging occur before this pipeline. |

The selected 24 s leaves four seconds before the existing 28 s bridge wait and favors one bounded manual attempt over waiting indefinitely for an anonymous model. Header/body/frame/event/chunk/text/payload limits remain 16 KiB, 256 KiB transfer-decoded, 8 KiB normalized, 2,048 frames, 4,096 HTTP chunks, 4 KiB text and 32 KiB compact Unix relay. The worker publishes a bounded result after it exits, with no partial task delivery. On a legitimate stream larger than 256 KiB, classify `response_cap`, preserve the spent state and evaluate a new design offline. There is no automatic increase or retry.

## Offline evidence and remaining uncertainty

- A separate Codex review session (`issue26_review`) challenged exact **5f9a05f** after verifying the byte-identical executable and 46 passing no-egress unit tests at its parent. This is independent technical review. The staged integration then used the exact named commit.
- The source-to-runtime bootstrap was executed under outer WSL network isolation. Changed source, archive and Bubblewrap were refused before reservation. A real `--describe` request produced the identities above and created only the Issue #26 runner nonce. Missing authorization returned `NO_LIVE_AUTHORIZATION`.
- The staged launcher itself verified a synthetic Owner record and catalog over mock HTTPS, then drove pinned Kilo Linux with the same vendor Host/SNI and certificate verification. A fixture-only seam below the real HTTP client directed sockets to numeric loopback and used a temporary private CA. The tested script had no such switch, the outer network namespace had only loopback, and each fixture used a separate temporary home. No genuine approval comment was generated or posted by Codex.
- The fixture suite covers the previous issue scope, changed price, 256 KiB delayed success, certificate mismatch, HTTP 429/302, blocking header/body I/O, and a full Unix send buffer. It checks physical local POST counts, durable replay refusal, FD and TCP/Unix socket counts and removal of staging paths. The underlying prior suite covers malformed SSE, interrupted HTTP, invalid TLS, frame/response bounds and early worker exit/descendant cleanup.
- It is confirmed that the prior live Issue #20 response crossed the old 32 KiB cap. The historical full stream, future live SSE size, completion, usage and billing receipt are unverified. The 256 KiB and timing choices are fixture-supported bounds.

| Exact staged case | Synthetic HTTPS POSTs | Observed result |
| --- | ---: | --- |
| Issue #20 proof presented to the new scope | 0 | Rejected. No reservation or catalog lookup. |
| Price changed after valid scoped proof | 0 | Rejected. Reservation remained consumed and replay was refused. |
| SSE with 4 s before its first byte, 256 KiB complete | 1 | 4,068 ms HTTPS worker, 24,427 ms pipeline, exit 0. 262 frames, 260 data events, 661 bytes relayed and exact oracle. |
| Wrong TLS hostname | 0 | Certificate rejection, zero task bytes and exit 1. |
| HTTP 429 and 302 | 1 each | Both stopped at the first response, with zero task bytes and exit 1. |
| Header trickle and stall after SSE stop | 1 each | HTTPS worker killed and reaped with signal 9 at 24,006 ms in both cases. Zero task bytes and exit 1. |
| Full Unix send buffer during the sandbox run | 1 | Pipeline watchdog killed and reaped the driver with signal 9 at 55,047 ms against 55,000 ms. No task result or surviving child. |

All nine exact staged cases achieved their expected outcomes and sent zero external POSTs. The terminal inventory found no test PIDs or temporary paths. The real Issue #26 slot has no reservation or POST claim. Both Issue #20 historical markers retain their original modification times.

## Historical Owner action

The consumed Owner record used this format, with expiry set to 11:00 on 2026-11-22 in Vietnam. It authorized one manual Kilo Free POST at **0 VND** incremental spend, without retry. The slot is spent and the template is retained for audit. [Issue #26](https://github.com/kha997/ai-chatbot/issues/26).

```text
APPROVE ONE KILO FREE POST | issue=26 | commit=5f9a05f65701f60c832732550aca9eafd6cb4d80 | manifest=25fa10942ca1d3f5dc1bf3f97377e63b5a4ab0c84aea92e415d7048a957aab18 | runner=f6ba9bcacd248f9eee11c04b17ce6d11b857faa4170f5668dc4a85333856313e | model=recursive/flint-v1.0:free | max_posts=1 | incremental_vnd=0 | expires=<UTC expiry>
```

Run manually only from the reviewed ordinary WSL user and ext4 home. Start a clean shell using `/usr/bin/env -i HOME=/home/zen PATH=/usr/bin:/bin /usr/bin/bash --noprofile --norc`. The numeric argument must come from the Owner's actual Issue #26 comment link.

```bash
set -eu
umask 077
source_repo='/mnt/d/Projects/AI ChatBot'
commit=5f9a05f65701f60c832732550aca9eafd6cb4d80
launcher_sha=cc05f16bb09b9ad1fa6cb094501f8eec753ed8cb4956c628de1d956ea2ebbe9d
archive="$source_repo/sandbox-output/kilo-linux-x64-baseline-v7.8.32.tar.gz"
sandbox="$HOME/.aichatbot-issue18/bwrap"
stage=$(/usr/bin/mktemp -d /tmp/issue26-bootstrap.XXXXXXXX)
trap '/usr/bin/rm -r -- "$stage"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
/usr/bin/git clone --quiet --local --no-hardlinks --template= --no-checkout -- "$source_repo" "$stage/verified-repo"
/usr/bin/git --no-replace-objects -C "$stage/verified-repo" -c core.autocrlf=false checkout --quiet --detach "$commit"
/usr/bin/git --no-replace-objects -C "$stage/verified-repo" show "$commit:scripts/kilo_activate26.py" > "$stage/kilo_activate26.py"
printf '%s  %s\n' "$launcher_sha" "$stage/kilo_activate26.py" | /usr/bin/sha256sum --check --status

/usr/bin/env -i /usr/bin/python3 -IS "$stage/kilo_activate26.py" \
  --repo "$stage/verified-repo" --commit "$commit" --archive "$archive" --sandbox "$sandbox" \
  --approval "${OWNER_COMMENT_ID:?required}"
```

Success requires one recorded request, HTTP 200 SSE with complete HTTP framing, `finish_reason=stop` and terminal `[DONE]`, exact model if supplied, Kilo exit 0 and one finish step, exact integer oracle `{"catalog":2,"handoff":1,"total":3}`, duplicate/auxiliary denial and process cleanup. Missing model metadata, token usage or per-attempt receipt are `UNKNOWN`. A timeout may leave wire delivery unknown.

If anything fails, preserve the two Issue #26 markers once present. The first durable reservation consumes the authorization even on changed price, interruption, 429, or failure before POST. A separate atomic claim precedes the network write. No replay, state reset, clone or snapshot restoration. The guarantee assumes a trusted local WSL UID, OS, trust store and operator. Withdrawal must occur before the launcher verifies the GitHub comment. Stopping after reservation cannot revoke a request already in flight. The temporary bootstrap is removed separately from the durable state. Rollback is to revert the candidate, leaving both Issue #20 and any Issue #26 historical markers intact. No scheduling or deployment is part of the procedure.
