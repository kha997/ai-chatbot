# Independent review of the Issue #64 offline gateway

**OFFLINE_GATEWAY_QUALIFIED** at technical SHA [eaa5600d](https://github.com/kha997/ai-chatbot/commit/eaa5600dafaaa2e69924f6de3c78f782b2fdc8e4). Fresh-context Codex reviewer `/root/gateway64_review` examined the exact commit from a Git archive and made no implementation edits. Architecture Acceptance remains pending on [PR #66](https://github.com/kha997/ai-chatbot/pull/66). This is independent Codex review within the offline scope.

## Findings and disposition

At the initial technical SHA, the reviewer reproduced peer dispatch after an ambiguous crash, callable values inside the fake or permit, insufficient receipt and transaction binding, and test gaps at the durable request ceiling and during STOP. The lead added serialized unsettled intent handling, lease expiry and generation fencing, closed primitive inputs, manifest/nonce-bound receipts, a same-transaction savepoint rollback for injected write errors, SQLite integrity checks, and a distinction between observed sends and ambiguous intents. Tests now reach 600 durable attempts, reject an eligible 601st attempt, and race five reserved dispatches against STOP.

Rechecks reproduced two further paths, a caller-controlled fault selector and a second stage enabled for an explicitly denied case. Exact selector validation now precedes side effects. Denial now applies to every stage and retry in the case. Reviewer rechecked all changes at the final technical SHA and independently passed the bounded offline simulation. The first hosted workflow failed before tests because the checkout commit ID had a typo. The workflow now pins the same checkout revision as the existing quote workflow, and hosted checks passed.

## Validation

- `python -B -m unittest discover -s tests -p "test_offline_gateway.py"`: 26 PASS on Windows and Ubuntu-24.04 WSL, independently repeated at the exact SHA. The WSL network namespace contained only down loopback and had no IPv4 or IPv6 routes.
- `python -B -m unittest discover -s tests -p "test_quote*.py"`: 73 PASS on Windows, plus existing hosted regression PASS. `git diff --check` against baseline PASS.
- Hosted checks at the technical SHA: [isolated gateway](https://github.com/kha997/ai-chatbot/actions/runs/45214860405) and [quote regression](https://github.com/kha997/ai-chatbot/actions/runs/45214860433) PASS.
- AI, real billing control and six business E2Es remain NOT_RUN. No provider/account interaction, real data, external test egress or spend.

## Example mock receipts

Observed at technical SHA eaa5600d using the one approved synthetic payload from the test fixture and a fresh temporary SQLite file per run. Frozen simulated manifest SHA-256 `47a6943dcda251ea991672dbcf6ffaa7ffd3d929bbca6f9ea84d37daa8545fcc`. The fake captured exactly one local attempt ID 1 and payload SHA-256 `b8e26078334ff0d21d823f764d08b40873eed2b5742ecd29e09e1c921117d527` per row. Amounts are simulated micro-USD.

| Scenario | Reserved before fake call | Reconciled | Outstanding after | Protected | State |
| --- | ---: | ---: | ---: | ---: | --- |
| Complete simulated receipt | 10,500 | 300 | 0 | 2,000,000 | ACTIVE |
| Missing usage field | 10,500 | 0 | 10,500 | 2,000,000 | STOPPED |

The provider-level `BLOCKED_COST_CONTROL` remains. The simulation assumes trusted local supervisor, clock and storage. If SQLite is unavailable, a new durable STOP may be impossible to persist while writes fail. Dispatch requires a healthy writable ledger, and a suspected storage/run fault needs supervised shutdown and inspection. No external hard-cap claim follows. The final receipt commit changes documentation only.
