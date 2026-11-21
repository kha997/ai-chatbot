# Kilo SSE over 32 KiB — Issue #22

**Offline qualification only.** Kilo live qualification, Dispatcher, Gate 2 and production remain **NO-GO**. PR #21 was independently reviewed and merged as the Issue #20 failure record at `d4c105797c3ee5b1e014d12ad6125cc49e0e2239`. Its live attempt remains consumed. [PR #21](https://github.com/kha997/ai-chatbot/pull/21) · [Issue #20 run receipt](https://github.com/kha997/ai-chatbot/issues/20#issuecomment-7061006163).

## Root-cause confidence

| Confidence | Finding |
| --- | --- |
| CONFIRMED_LIVE | At `ace3a4ef35c75e4899f52b5bf1a92b64dcbd0064`, the single approved request returned HTTP 200, SSE, identity encoding. The HTTPS reader reached byte 32,769. The relay rejected the capped body before parsing any event, classified `response_cap` and returned 502 to Kilo. Kilo exited 1 without a validated oracle. |
| CONFIRMED_OFFLINE | Legacy code accepted valid 32,767- and 32,768-byte fixtures and rejected the valid 32,769-byte fixture at the body cap. The candidate accepted complete synthetic SSE at those sizes and at 64, 128 and 256 KiB. The pinned Linux Kilo release handled the candidate's compact response and returned the exact oracle. |
| CONFIRMED_OFFLINE | Oversized frames, excessive events or HTTP chunks, missing/truncated terminal data, trailing events, wrong model, embedded errors, invalid encoding, ambiguous/truncated HTTP framing and an exhausted read deadline reach a closed error path. A larger input alone cannot relax any independent limit. |
| UNKNOWN | Full historic stream size and contents, whether the historic stream ever finished, upstream model identity and usage, and whether its task result would have been usable. Fixture usage is synthetic. The observed prefix cannot answer these questions. |

## Activated ceiling map

| Layer | Issue #20 behavior |
| --- | --- |
| HTTPS capture | `kilo_activate.py` POST limit 32,768 body bytes after HTTP transfer decoding. Reader retains at most cap + 1 as overflow evidence. Requires exact Content-Length or strict chunked framing. HTTPS socket idle timeout 8 s, POST worker deadline 22 s. |
| SSE | `relay_response` checks body length before whole-body UTF-8 decoding and SSE parsing. No independent frame limit. The upstream size rejection occurred before the Unix relay or CLI output caps. |
| Unix relay/bridge | One newline-framed Base64 JSON response, maximum read 43,820 bytes, decoded payload maximum 32,768. Host request readline limit 131,072, sandbox request body limit 32,768. Unix socket timeout 28 s. |
| Kilo | Fixed outbound `max_tokens=128`, 131,072 bytes each for process stdout/stderr, inner CLI deadline 40 s, outer sandbox deadline 45 s with kill and cleanup. The token cap cannot bound metadata bytes or HTTP/SSE overhead. |

## Candidate decision

Pull HTTP body blocks of at most **4 KiB** and validate one SSE frame at a time. Publish the compact text/stop/usage representation only after full HTTP framing and both `finish_reason=stop` and terminal `[DONE]` validate. The relay can withhold content until the complete decision, including late upstream errors or truncation. Arbitrary provider metadata and keepalives do not enter the sandbox payload. The case with 256 KiB input contained 260 data events, 35 task-text bytes and a 661-byte normalized relay payload. Its 17 total tokens are explicitly fixture data.

The independent candidate limits are **16 KiB HTTP headers**, **256 KiB transfer-decoded body**, **8 KiB per newline-normalized frame** (including its delimiters), **2,048 nonempty frames**, a **4,096-entry HTTP chunk budget including the terminator**, **4 KiB generated UTF-8 text**, and the existing **32 KiB** Unix-relay payload. Chunk framing is separately bounded by the chunk budget and bounded line syntax. An **8 s** cooperative deadline covers HTTP fixture reads and validation. It is checked on both sides of reads. A future socket adapter must also interrupt blocked I/O with a hard worker deadline, and prove this on stalled headers, chunks and downstream writes. The fixture runner retains the existing sandbox and client deadlines.

The fixture bytes are finite and in memory by design. The parser pulls synchronously and validates between reads, so it does not add a whole-body copy or producer queue. The Unix relay is unchanged. The alternative to merely increasing the old cap would still forward an expanded body through that envelope and delay validation until the entire body is buffered. Direct incremental delivery to Kilo would expose partial content before a late rejection. This candidate instead accepts the measured memory/copy tradeoff of a bounded normalized result and delays first delivery until validation is complete.

### Offline memory and time

Seven Python runs per size/method in Ubuntu 24.04 WSL, reporting median elapsed time and maximum `tracemalloc` peak. Both methods use the same validator. The comparator copies the entire fixture before validating. Figures exclude preallocated fixture bytes, ELF runtime, TLS, OS buffers and GitHub operations. They are a parser microbenchmark.

| Body | Incremental median | Incremental peak | Full-copy median | Full-copy peak |
| --- | ---: | ---: | ---: | ---: |
| 32 KiB | 6.98 ms | 38,918 B | 7.05 ms | 66,714 B |
| 64 KiB | 11.00 ms | 21,653 B | 11.07 ms | 134,400 B |
| 128 KiB | 16.21 ms | 20,448 B | 16.28 ms | 268,332 B |
| 256 KiB | 29.54 ms | 22,308 B | 31.75 ms | 536,214 B |

### Verification

- RED before implementation: boundary fixtures reproduced the old limit and the new acceptance/rejection contract failed with the candidate missing. GREEN: 38 unit tests in the outer unshared WSL network namespace. Tests cover exact body limits, split UTF-8/CRLF, multiline data, malformed/partial framing, over-limit text and frames, many small events, a simulated slow reader, and a peak-memory ceiling for the parser.
- Independent Codex review (`issue22_review`) found that an interior BOM could conceal an error event and that the JSON decoder accepted `NaN`. Both reproduced before the fix and now fail closed. The reviewer checked exact candidate SHA `57e455c59b69f43220ca4d6fea191af8c9c0390d`, reran 38 tests in no-egress WSL and found no remaining issue for the offline scope. No live transport or hard I/O cancellation was attested.
- Serial Kilo **v7.8.32 Linux ELF** cases use verified private Bubblewrap **v0.13.1**, with the existing nested network/filesystem boundaries, pinned artifacts, fixed synthetic request and model, one fixture permit, no credential forwarding, duplicate denial and an explicit cleanup check. Positive cases are the small control and 32,769 / 65,536 / 131,072 / 262,144 bytes. Negative cases are a large terminal suffix, a large truncated chunked body, and an oversized event. Each fixture uses only an outer isolated network namespace with loopback and no external route.
- A positive run requires Kilo exit 0, one terminal CLI step and the exact JSON `{"catalog":2,"handoff":1,"total":3}`. Every invalid run requires CLI exit 1, zero forwarded task bytes and the expected classification. Every fixture expects zero real POSTs.
- The inherited forced-timeout probe checks exit `-9`, zero forwards and closed output streams. The final WSL process scan checks for orphaned Kilo and sandbox probes.

| Kilo ELF fixture | Body declared / observed | Classification | Relay SSE bytes | CLI exit |
| --- | --- | --- | ---: | ---: |
| Small control | 876 / 876 B | complete | 661 | 0 |
| First byte beyond old cap | chunked / 32,769 B | complete | 661 | 0 |
| 64 KiB | chunked / 65,536 B | complete | 661 | 0 |
| 128 KiB | chunked / 131,072 B | complete | 661 | 0 |
| 256 KiB | chunked / 262,144 B | complete | 661 | 0 |
| Data after terminal marker | 65,749 / 65,749 B | data_after_done | 0 | 1 |
| Truncated terminal chunk | chunked / 131,072 B | invalid_http_framing | 0 | 1 |
| Oversized event | 73,736 / 8,192 B | frame_cap | 0 | 1 |

Reproducible commands from the worktree. `ARCHIVE` and `BWRAP` point to the local artifacts pinned in PR #21.

```bash
unshare --user --map-current-user --net python3 -m unittest discover -s tests -q
unshare --user --map-current-user --net python3 tests/run_kilo_sse_stream.py --benchmark
for fixture in small 32769 65536 131072 262144 large-trailing large-truncated large-event; do
  unshare --user --map-current-user --net python3 tests/run_kilo_sse_stream.py "$ARCHIVE" "$BWRAP" "$fixture" || exit
done
unshare --user --map-current-user --net python3 tests/run_kilo_owner_gate.py "$ARCHIVE" "$BWRAP" timeout
```

## Before considering a new Owner Gate

1. Establish the value of another live qualification and use a separately reviewed activation artifact with an exact SHA and manifest, including any new parser dependency. This PR contains an offline fixture path and does not wire it into the outbound worker.
2. Prove the full read/cancel/cleanup path through TLS against bounded local fixtures, including slowloris input and late errors. Recheck the proposed cap and compatibility with the currently supported upstream framing contract. Keep hard deadlines, the one-request envelope, exact model and token limit, hostname/certificate validation, isolation and duplicate denial.
3. Reconfirm current zero pricing and the anonymous account-free route with read-only evidence. A later authorization must use a new issue scope, machine-bound, expiring exact-SHA proof, and a new durable one-use reservation. Preserve both Issue #20 spent markers. No new authorization is requested by this report.
4. Roll back by reverting the offline candidate PR. The historical runner and its evidence remain independently pinned. No provider state, schedule, production component or external service was changed.
