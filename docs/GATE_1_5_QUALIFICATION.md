# Gate 1.5 CLI qualification

**Dispatcher decision: NO-GO.** Checked 2026-11-21, Asia/Saigon, under [Owner Issue #8](https://github.com/kha997/ai-chatbot/issues/8). Zero of three permitted AI prompts were sent. No model call, charge, output artifact or usage measurement exists for this qualification. The authorized CLI diagnostics and Watcher update are complete. Issue #8 remains open for the account and quota dependency.

## Preflight by CLI

| CLI | Nonprompt diagnostics and observations | Existing authorized provider, quota and cost boundary | AI task |
| --- | --- | --- | --- |
| Qoder 1.1.94, Windows | `--version` and `status --help` responded. `status --output json` exited 0 in a temporary workspace. Parsed diagnostic indicators did not establish a valid signed-in account or included quota. Qoder config directory present and PAT environment variable absent. | Existing headless authentication and exact model unverified. No authoritative allowance or enforcement against add-on/overage established. | **BLOCKED_COST_OR_AUTH**, 0 attempts |
| OpenCode 1.18.30, Ubuntu-24.04 WSL | `--version` responded. `auth list --pure` exited 0 and reported no saved credentials in the tested CLI context. Default auth file and sampled provider environment variables absent. | No authenticated approved provider/model tuple verified. Vendor documentation describes Extra Usage that can debit a Console balance. Current account settings and remaining allowance unavailable. | **BLOCKED_COST_OR_AUTH**, 0 attempts |
| Kilo 7.8.32, Windows | `--version` responded. `auth list --pure` exited 0 and reported no saved credentials in the tested CLI context. Kilo API key environment variable and checked default auth file absent. | No authenticated approved provider/model tuple verified. Personal and organization auto top-up are possible. Documented anonymous free access does not establish access under an existing authorized account. | **BLOCKED_COST_OR_AUTH**, 0 attempts |

Absence checks are scoped to the tested CLI context and do not prove that no GUI, cloud or other account exists. Diagnostic subprocesses were time bounded. Only status categories were retained. No raw output, account identifiers, credential file contents or secret values were written to this repository. A zero diagnostic exit establishes command reachability only.

Official documentation consulted 2026-11-21: [Qoder authentication](https://docs.qoder.com/cli/authentication) and [credit usage](https://docs.qoder.com/cli/usage), [OpenCode CLI accounts](https://opencode.ai/docs/cli/providers/) and [Go extra usage](https://opencode.ai/docs/console/go/), [Kilo authentication](https://kilo.ai/docs/gateway/authentication) and [billing](https://kilo.ai/docs/gateway/usage-and-billing). Service features and prices do not establish the settings of a specific account.

## Isolation evidence

In WSL, `bwrap` launched `/usr/bin/true` in a new namespace with an explicit read-only runtime mount and shared-library links. The initial attempt omitted the shared-library mapping and failed before executing the binary. The corrected no-network probe exited 0. This establishes namespace launch capability for a local dummy process. Provider-only egress, a full isolated CLI workload, limits and model-process cleanup are unverified. For native Windows, the checked Windows Sandbox executable was absent and no other enforced read-only, credential-separated Windows lane was qualified.

## Watcher update and live verification

The separate Codex reviewer `gate15_review` checked [PR #9](https://github.com/kha997/ai-chatbot/pull/9) at `3361dc72bbf0a2450677450b0881e8acfd7d7d53`. The runtime change is a static Issue #8 entry for Codex. GitHub OWNER authorship remains mandatory, and queue classification adds no execution path. Six tests passed, including the non-Owner negative case. Python compilation and Git whitespace checks passed. The PR merged at `c5c24a481d857571609a8bded9c0677b4808d889`.

Lead Codex used the existing management script to disable and unregister the one task, archived the prior private snapshot as `github_watcher.pre-gate15-339e017.py`, installed the reviewed source, checked that pre-poll queue state was unchanged, and re-enabled the schedule. No running snapshot was replaced. The new installed snapshot SHA-256 is `1f538f381e4a981b7068c06417956a7a405670657df0a6c3f6f9b0af48f41b2e`.

At **12:51:56**, a manually triggered run through Task Scheduler returned **0**. Queue last success advanced from `1795239187` to `1795240316` with zero failures. Exactly one Issue #8 / Codex / `approved` entry was present, and closed Issue #5 was absent both before and after the update. The task returned to `Ready` and retained `PT30M` repetition. See the [Watcher runbook](GITHUB_WATCHER_DESIGN.md) for controls. Rollback uses the previous commit's management script and snapshot through the same disable/uninstall/install/enable sequence.

The scheduler fired automatically at **12:53:55**, returned **0** and advanced last success to `1795240435` with zero failures. The sole queue entry and prior last-change timestamp stayed unchanged. Task Scheduler showed the next run at **13:23:55**.

## One proposed next authorization

Recommend qualifying **OpenCode first**, using its existing WSL runtime and the proven namespace launcher. The Owner gate is account access only: authorize access to one specific existing provider account with confirmed included allowance, or explicitly approve one named public zero-price route if an existing account cannot be verified. Recommended purchase ceiling is **0 VND**. If an existing account needs connection, request approval for that connection and use the official channel without exposing credentials in GitHub or chat. No request is made to purchase credits or raise quota.

Before the one test, record exact provider and model, sufficient included allowance, provider-side refusal above the approved limit, and no overage, automatic top-up or paid fallback. Complete OS isolation and provider-only egress with no host credentials, private mounts or tool actions. Use one synthetic packet asking for JSON with an exact count and category from three invented records. Compare structured output to a fixed oracle, enforce the deadline and output cap, confirm cleanup and verify usage from the provider when available. An unknown charge or inconclusive account policy blocks launch. Qualify Qoder and Kilo individually when their own prerequisites pass. Keep scheduling and dispatch approvals separate.
