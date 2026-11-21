# Kilo loopback TLS and hard cancellation — Issue #24

**Offline candidate.** The approved Issue #20 attempt remains spent. No provider request was made by this work. Dispatcher, Gate 2 and production remain **NO-GO**. PR #23 was independently reviewed and merged as an offline improvement at `dd8e060ad452f54ddab6772b07746e2169c75795`. [PR #23](https://github.com/kha997/ai-chatbot/pull/23) · [Issue #20 receipt](https://github.com/kha997/ai-chatbot/issues/20#issuecomment-7061006163).

## Confidence and decision

| Confidence | Finding |
| --- | --- |
| CONFIRMED_LIVE | Issue #20 observed HTTP 200 SSE and rejected byte 32,769 at its 32 KiB body cap. No event was parsed and no valid task result was observed. |
| CONFIRMED_OFFLINE | A real loopback TLS connection delivered a finite 262,144-byte chunked stream. The bounded parser validated 262 frames and 260 data events, then forwarded 661 normalized SSE bytes. Pinned Kilo Linux v7.8.32 exited 0 and produced `{"catalog":2,"handoff":1,"total":3}`. The fixture's token count of 17 is synthetic. |
| CONFIRMED_OFFLINE | Limits outside the TLS worker interrupt blocked I/O, including waits that the parser's cooperative deadline cannot interrupt. No partial task text was returned on failed framing, certificate verification or timeout. |
| UNKNOWN | Full historic response size, completion, model identity and usage. The live gateway's future stream size, terminal behavior, available capacity and current zero-price terms were outside this assignment. |

**CONDITIONAL GO to prepare a separate Owner Gate request.** Before requesting approval, produce a default-inert activation artifact with a fresh exact commit and manifest and an independently reviewed source-to-runtime bootstrap. Confirm zero-price anonymous routing from current read-only evidence. Demonstrate that the future vendor-host-pinned transport retains these cancellation and cleanup properties, document why a new live attempt is necessary, and use one separate expiring approval, machine binding and durable one-use state. The current local candidate has no route to send that request.

## Design and limits

- The socket suite runs in an outer Linux user/network namespace with only loopback and no IPv4 route or reachable IPv6 route beyond loopback. The harness raises if these checks fail or effective/bounding capabilities are present. WSL's current UID is preserved. A temporary namespace capability raises loopback, then the harness drops all capabilities and sets `no_new_privs`. This avoids privileged Windows or WSL changes.
- HTTPS connects only to numeric `127.0.0.1` with TLS 1.2 or later and validates the fixed hostname `localhost` against a one-day ephemeral test CA. The certificate, keys, listener and work directories are private temporary artifacts. The fixture verifies the exact synthetic request and fixed free model, including the absence of authorization headers. The one-shot permit rejects duplicate use. The existing vendor activation and reviewed CA/hostname policy are unchanged.
- The PR #23 parser keeps its independent caps. These are 16 KiB header, 256 KiB decoded body, 8 KiB newline-normalized frame, 2,048 frames, 4,096 chunk entries and 4 KiB task text. Reads pull at most 4 KiB. The existing Unix response envelope and Kilo stdout/stderr bounds are retained. No task output is released before HTTP termination and complete, validated SSE.
- An isolated blocking HTTPS worker has a **1,500 ms** hard deadline. A supervisor measures wall clock, sends `SIGKILL` to the worker/process group and reaps it. On normal or early worker exit, the leader remains unreaped while any surviving group members are signalled. The supervisor only reads the bounded result file after process exit. This avoids a second blocking receive while collecting a partial IPC result. The child also binds its lifetime to its parent. No async queue accumulates partial frames.
- The offline pipeline wraps the existing Bubblewrap/Kilo run in a supervised **52 s** process boundary. Normal local Unix sends use the existing socket timeout and join their relay handlers. A test-only fault fills a real Unix stream send buffer in the active relay handler, then calls the same send function with no socket timeout. The full watchdog must kill the still-blocked driver. Bubblewrap retains its existing parent-death and namespace behavior. The supervisor owns the staging directory and removes it after hard cancellation.

## Socket matrix

| Fixture | Observed |
| --- | --- |
| Valid 256 KiB, valid dripping 32,769 B, valid 256 KiB with TCP held open after explicit HTTP end | Complete. One local POST each. Delivery followed the HTTP chunk terminator and SSE stop/DONE, even when the peer kept its connection open. |
| Declared and chunked bodies of 262,145 B and oversized event | `response_cap` before reading the declared body or the first over-budget chunk, and `frame_cap` within the body. Zero task bytes forwarded. |
| Non-SSE media, gzip, HTTP 200 JSON error, wrong returned model | Classified respectively as `unexpected_media`, `unsupported_encoding`, `embedded_error` and `model_mismatch`. |
| Truncated SSE terminal and TCP cut mid-chunk | `truncated_event` and `invalid_http_framing`, respectively, with zero task bytes forwarded. |
| Stall before TLS handshake, stall after POST before headers, slow header trickle, stall between chunks, stall after stop before DONE | Hard timeout around 1,506 ms. `SIGKILL` and reaped. The handshake stall sent zero POSTs. The other four each sent one local POST. |
| Wrong hostname, untrusted signer, plaintext on TLS port | Certificate or protocol rejection with zero POSTs. |
| Full Unix send buffer and peer shutdown | The blocking sender was killed and reaped under a 260 ms cap. Closing the peer released the blocked sender with a closed-peer result. |
| Unresponsive process group and early leader exit | A blocking worker and a child that ignored `SIGTERM` were both killed and reaped. When the leader failed before its deadline, its remaining child was also killed and reaped. |

The 20 socket cases assert the local POST count from the fixture peer, no replay, worker exit, server reaping and identical parent descriptor, namespace Unix socket and listening/established TCP counts before and after each case. TCP TIME_WAIT records are kernel state and are excluded from the open-listener/connection count. Five consecutive 256 KiB parses peaked at roughly 22–25 KiB of Python parser allocations per worker, with stable descriptor and socket counts and no worker retained. Measurements exclude native OpenSSL, ELF and kernel buffers. This is bounded fixture evidence, with no claim about indefinite live operation.

## Verification and rollback

- RED: the socket cancellation contract failed before the supervisor existed. The initial sandbox run with outer namespace UID 0 failed at Bubblewrap's nested UID map. Keeping the ordinary WSL UID and dropping capabilities after configuring loopback passed without changing Bubblewrap or its security profile.
- Independent Codex reviewer `tls_review` reproduced a descendant surviving early leader exit. A regression test failed before the change. The updated supervisor terminates the group while its leader PID is still held, then reaps the leader. The regression proves both early-exit and deadline outcomes against real processes.
- The suite runs with the pinned `kilo` ELF from release v7.8.32 and the previously verified private Bubblewrap 0.13.1. During TLS cutoff the peer sees only the fixed synthetic POST (or zero with TLS rejection). Per-case observations include sanitized classification, bytes, frames, stop/DONE, worker elapsed time, exit class and cleanup. No provider content, raw secrets or TLS private keys are committed.
- Exact executable candidate SHA `48fd2b72e489a84567dea81720d5f5dc038ea166`. The real Kilo suite covers six serial cases, including the full Unix write-buffer fault. Every case checks return to the initial Unix socket, TCP and process FD counts and removal of the owned candidate directory.
- Existing live runner and Issue #20 authorization state are outside the candidate. The two spent markers remain at their historical timestamps. To roll back, revert this offline PR. No network route, credentials, schedule or production deployment need cleanup.

Reproduce from the project worktree in Ubuntu 24.04 WSL. Set `ARCHIVE` and `BWRAP` to the pinned local artifact paths from PR #23.

```bash
offline() {
  /usr/bin/unshare --user --map-current-user --net --keep-caps /usr/bin/bash -c '
    /usr/sbin/ip link set lo up &&
    exec /usr/bin/setpriv --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"
  ' bash "$@"
}
offline /usr/bin/python3 -m unittest discover -s tests -q
offline /usr/bin/python3 -u tests/run_kilo_tls_offline.py "$ARCHIVE" "$BWRAP" \
  large stall-between-chunks stall-after-stop closed-mid-http wrong-hostname pipeline-unix-stall
```
