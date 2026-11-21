# Gate 1.5 existing-account connection

**Checkpoint: OWNER_CONSENT_PENDING.** Scope is the latest Owner authorization in [Issue #8](https://github.com/kha997/ai-chatbot/issues/8). The earlier [PR #10](https://github.com/kha997/ai-chatbot/pull/10) documents the previous preflight. This record tracks the newly authorized official sign-in attempt. Date: 2026-11-21, Asia/Saigon.

## Governance and connection

[PR #12](https://github.com/kha997/ai-chatbot/pull/12) was independently reviewed by the read-only Codex session `pr12_review` at `0c5fcc590642811bb66d4228aa6e5ea5fc64bfc0` and merged at `3a2b0687db88b79ef8be673df3b2dd3d468e3edc`. Exact diff whitespace check and all six existing watcher tests passed. The review confirmed a narrow existing-account sign-in exception, Owner-performed consent, 0 VND incremental spend and at most one isolated synthetic prompt per CLI once prerequisites pass. Approximately 200,000 tokens/day is an Owner-reported usage allowance requiring separate verification per account/model.

| CLI / declared entitlement | Verified installed command surface | Connection checkpoint | Verified account, model, quota and billing controls | Model attempts |
| --- | --- | --- | --- | --- |
| Qoder 1.1.94 / existing Pro | `qodercli login --help` | Dedicated visible console launched with `qodercli login`. Completion unverified. | Pending Owner confirmation and provider checks. | 0, NOT_RUN |
| OpenCode 1.18.30 / existing free | `opencode auth login --help` in Ubuntu-24.04 WSL | Dedicated console launched with `opencode auth login --pure`. The WSL child was observed. | Pending existing-account authentication and confirmation of a free-only route. | 0, NOT_RUN |
| Kilo 7.8.32 / existing free | `kilo auth login --help` | Dedicated console launched with `kilo auth login --pure`. The Kilo child was observed. | Pending existing-account authentication and confirmation of a free-only route. | 0, NOT_RUN |

The Owner was handed the exact local CLI steps for the browser, device-code or MFA prompt issued by the vendor. Gate 1.5 inputs were excluded from the sign-in commands. No login output, device code, URL, token, account identifier or cookie was captured. Success is not inferred from starting the console or from its exit. Official references accessed 2026-11-21 include [Qoder authentication](https://docs.qoder.com/cli/authentication), [OpenCode providers](https://opencode.ai/docs/cli/providers/), [OpenCode free models](https://opencode.ai/docs/models/), and [Kilo authentication](https://kilo.ai/docs/getting-started/setup-authentication).

## Qualification after consent

1. Verify that the intended existing account is reachable through that installed CLI with a read-only status check. Keep output limited to redacted status, account tier, provider and model. An installed CLI or a completed browser step alone does not verify inference access.
2. Verify exact model pricing, available included quota and a provider-side refusal when included access is exhausted. Confirm pay-as-you-go, overage, automatic recharge and paid fallback cannot apply. If the route cannot be bounded to 0 VND new spend, publish the specific remaining blocker and skip the model call.
3. Verify a disposable read-only workspace and bounded execution, with only approved provider egress, no GitHub credentials or private mounts, tools disabled, bounded output and process cleanup. Current WSL namespace proof is a dummy process only. Windows and provider-enabled isolation remain unqualified.
4. One candidate task per eligible CLI. Classify three invented records with categories `catalog`, `handoff`, `catalog`. Expected JSON is `{"catalog":2,"handoff":1,"total":3}` with integer values and exactly those keys. Report the observed model, evidence, pass/fail, usage or UNKNOWN, and actual incremental spend if available. No retry prompts. Preserve the current approval and all watch-only boundaries.

**Dispatcher:** decision still pending qualification under the new authorization. Scheduler operation is outside these account-linking steps.
