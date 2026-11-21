# Kilo Free activation decision — Issue #20

**READY_FOR_OWNER_GATE** for one manual Kilo Free qualification. Live approval is pending. Dispatcher **NO-GO**. PR #19 was independently reviewed at `0bd680da0f1680286e8ec88a14bcd67164f42e75` and merged as offline evidence at `307bd2123633c981dc1515bbed4448dbfdab44eb`. Issue #20 preparation sent zero inference requests. The previous Kilo and OpenCode allowances remain exhausted.

## Exact reviewed inputs

| Input | Approved identity |
| --- | --- |
| Activation commit | `ace3a4ef35c75e4899f52b5bf1a92b64dcbd0064` |
| Manifest SHA-256 | `2073e85f27ed03a4bc2b34eca06744d6eda7a6cee412b825025afea845ec45fd` |
| WSL runner binding | `df5fedd3db3791fa0cc7be3c1babc10c70d4f5e6caebb318c30ba2bff9099ee6` |
| `scripts/kilo_activate.py` | `6ed14680edf24db67afe6f88c5181e3ad0e44dfb2b3239962a956e028b807072` |
| `scripts/kilo_gate15.py` | `342428f7e17ce7ec9ae5531b09cc4f1e73a775c5b3a05a4c54443d08e99fb3d1` |
| `scripts/kilo_owner_gate.py` | `c1fdcf5ca60bc72bf7e0d0da755af3db31b35240aa04e005a15dfc6e792cfc4d` |
| Kilo v7.8.32 release archive | `ab7a008a2c0ca6e035b96cd1dc5712a8466a14a45992291a8f0b4b549b94136e` |
| Kilo Linux x64 ELF | `474675d07e520067440df780a239f05bded6da2ae9b78bb2b5d2c2291ab03046` |
| Private Bubblewrap v0.13.1 executable | `3acde20bf6dadc53dfa708e8c5bfb81e9564ab831b2b28216c3c976808b50520` |
| Fixed synthetic body, 269 bytes | `619f9c39002b302768504f283803000ddd2ee112b09f2ee3e6d98ceb846000cd` |

A public HTTPS `GET /api/v1/models` at 09:01:56 UTC on 2026-11-21 returned one exact `recursive/flint-v1.0:free` row with prompt and completion pricing both `"0"`. The launcher repeats that check after verifying Owner approval. The POST uses the anonymous Kilo gateway route, with no API key, account, organization, BYOK credentials or fallback model. Kilo documents anonymous access for free models and zero billing for `:free` requests. Catalog visibility does not verify available capacity or successful inference. [Kilo authentication](https://kilo.ai/docs/gateway/authentication) · [Kilo usage and billing](https://kilo.ai/docs/gateway/usage-and-billing).

## Offline evidence

- Lead Codex and a separate Codex reviewer (`activation_security`) each verified 32 tests in network-isolated Ubuntu 24.04 WSL. The reviewer checked the exact activation commit, resolved findings from the initial review, and gave conditional GO to request approval after the bootstrap and serial tests. No vendor or GitHub proof requests were issued by the reviewer.
- The tested launcher was extracted from the approved Git commit to a private directory and ran only after external SHA-256 verification. Direct execution with no flags returned `NO_LIVE_AUTHORIZATION`. An unreachable synthetic comment ID in the no-egress profile failed closed before `issue20.spent` or `issue20.post` appeared. The official runner binding was generated locally without authorizing inference.
- The automated controls cover owner/issue/digest/runner/expiry mismatch, edited or missing records, cross-process overlap, durable replay denial, altered files, exact-price parsing, TLS identity, expiry during TLS, fixed request shape, redirects, malformed HTTP chunking, SSE and JSON ambiguity, worker timeout and cleanup. Exact model ID is checked whenever the SSE supplies it.
- The pinned Kilo ELF was exercised serially in an outer network namespace with only loopback and no routes, using synthetic responses. The inner Bubblewrap namespace, filesystem canary, denied auxiliary/duplicate requests and process cleanup checks remained active. The prior overlapping negatives in PR #19 remain evidence of fail-closed outcomes with an unknown contention cause. Keep the qualification serial.

| Offline ELF scenario | Observed outcome |
| --- | --- |
| Valid activation fixture | One simulated POST, complete SSE, CLI exit 0, exact oracle, duplicate/auxiliary denied and replay refused |
| 429 | One simulated POST, relay rejected, CLI exit 1 and state remained spent |
| HTTP 200 JSON error | One simulated POST, relay refused to label JSON as SSE, CLI exit 1 |
| Wrong returned model | One simulated POST, `model_mismatch`, CLI exit 1 |
| Prior relay regressions | Exact size cap and UTF-8 multiline streams accepted. Truncated SSE and unexpected encoding rejected. Timeout killed the child group with exit -9 and zero forwards. |

The serial suite found no remaining Kilo or sandbox probe process. Every fixture recorded zero real POSTs. Fixture token counts are synthetic. The only Kilo network access in the preparation was the public catalog GET.

## Owner action and supported invocation

Authorize **one manual Kilo Free POST**, that exact commit, manifest and runner, this fixed packet and **0 VND incremental spend**. The Owner must personally post an unedited single-line comment on [Issue #20](https://github.com/kha997/ai-chatbot/issues/20) using the following format. Replace the expiry placeholder with a UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` format. It must expire within 24 hours of publication.

```text
APPROVE ONE KILO FREE POST | issue=20 | commit=ace3a4ef35c75e4899f52b5bf1a92b64dcbd0064 | manifest=2073e85f27ed03a4bc2b34eca06744d6eda7a6cee412b825025afea845ec45fd | runner=df5fedd3db3791fa0cc7be3c1babc10c70d4f5e6caebb318c30ba2bff9099ee6 | model=recursive/flint-v1.0:free | max_posts=1 | incremental_vnd=0 | expires=<UTC expiry>
```

Use the reviewed ordinary WSL user with the project archive and private Bubblewrap path from PR #19. Open a clean shell with `/usr/bin/env -i HOME=/home/zen PATH=/usr/bin:/bin /usr/bin/bash --noprofile --norc`. Agent or scheduled workflows never invoke this runner. Execute these bootstrap steps in a shell or file you control. The SHA-256 check runs before any Python from the checkout.

```bash
set -eu
umask 077
source_repo='/mnt/d/Projects/AI ChatBot'
commit=ace3a4ef35c75e4899f52b5bf1a92b64dcbd0064
launcher_sha=6ed14680edf24db67afe6f88c5181e3ad0e44dfb2b3239962a956e028b807072
archive="$source_repo/sandbox-output/kilo-linux-x64-baseline-v7.8.32.tar.gz"
sandbox="$HOME/.aichatbot-issue18/bwrap"
stage=$(/usr/bin/mktemp -d /tmp/issue20-bootstrap.XXXXXXXX)
trap '/usr/bin/rm -r -- "$stage"' EXIT
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
/usr/bin/git clone --quiet --local --no-hardlinks --template= --no-checkout -- "$source_repo" "$stage/verified-repo"
/usr/bin/git --no-replace-objects -C "$stage/verified-repo" -c core.autocrlf=false checkout --quiet --detach "$commit"
/usr/bin/git --no-replace-objects -C "$stage/verified-repo" show "$commit:scripts/kilo_activate.py" > "$stage/kilo_activate.py"
printf '%s  %s\n' "$launcher_sha" "$stage/kilo_activate.py" | /usr/bin/sha256sum --check --status
```

From that same shell, the active invocation takes the numeric comment ID directly from the Owner's GitHub comment link. The tested offline preflight instead runs `--local-runner-id` and the no-argument command inside an outer network namespace. Keep the shell and stage open through the one approved invocation.

```bash
/usr/bin/env -i /usr/bin/python3 -IS "$stage/kilo_activate.py" \
  --repo "$stage/verified-repo" --commit "$commit" \
  --approval "${OWNER_COMMENT_ID:?required}" --archive "$archive" --sandbox "$sandbox"
```

## Abort, outcome and cleanup

- Expect a sanitized JSON receipt and exit code 0. Success requires verified TLS, one recorded POST to the fixed endpoint, explicit HTTP body framing, complete SSE with `finish_reason=stop`, Kilo exit 0 and a single terminal CLI step, the exact integer oracle `{"catalog":2,"handoff":1,"total":3}`, denied duplicate/auxiliary requests, passing sandbox probes and closed workers and output streams. HTTP 200 by itself leaves the gate unpassed. If the provider omits its model ID or usage, record that field as `UNKNOWN`. A supplied model must match exactly. Live token counts and billing receipts are unmeasured.
- Missing, replayed or expired proof, wrong digest, TLS/encoding/framing mismatch, changed price or catalog, 429, timeout, nonzero CLI exit, model mismatch, invalid oracle or incomplete cleanup stops the attempt. Once reserved, a failed preflight, timeout, interrupt, write failure, or uncertain upstream delivery consumes the slot. Preserve the one-use records. Do not retry, switch models or start a second runner.
- WSL owns the lock and durable state in `~/.aichatbot-issue20` on local ext4. Both the issue reservation and the POST claim are atomically created and synced before their protected work. The guarantee assumes the ordinary WSL operator, UID, OS, system TLS trust and local state are trusted. It does not cover intentional same-UID code execution, state tampering, home/VM cloning, or snapshot rollback. Do not copy or restore the runner identity or remove the state. Stage and process cleanup are independent of the durable state.
- Before reservation the Owner can withdraw the decision by deleting the comment. After reservation stop the process and check that no Kilo/bridge children remain. Do not assume that stopping the runner cancels a POST already in flight. Keep sanitized evidence and the state for audit. There is no deployment and no scheduled qualification to roll back.
