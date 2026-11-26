# PR #73 — F3–F7 remediation report (public-synthetic only)

Baseline audited: `0d884c9152d3812ad7f02b44f93f1375229c89ab` · Base: `588b8fe1d3e54161fe194739d2c06552ca8c79f4` · Branch: `remediation/f3-f7-pr73` · Draft PR: #73 (not merged, Owner Gate not approved).

Scope: only the offline public-synthetic qualification path. No private data, no Snapshot v2, no sealed evidence modified, no guard removed. Held-out corpus, models, six business E2Es, provider billing and the private retrieval metric remain `NOT_RUN`. Independent third-party review remains `INDEPENDENT_REVIEW_BLOCKED`.

## 1. Finding traceability

| ID | Finding (as reported/verified) | Classification | Evidence |
| --- | --- | --- | --- |
| F4-1 | `required_reads`/`forbidden_claims` are not authenticated: the pinned manifest only covers compiled bundles, so a resealed envelope with a stripped safeguard still verifies. | **CONFIRMED — HIGH** | `test_stripped_required_read_is_rejected_at_case_profile`, `test_stripped_forbidden_claim_is_rejected_at_case_profile`; before the fix, `prepare` accepted the resealed envelope and both preview and ledger returned `PASS / matched 5/5` while the guarded trace `STOP`s. |
| F4-2 | Legacy `h.Run`/v67 evaluation can return `PASS` where the official v72 path `STOP`s, and its result type is indistinguishable from an official receipt. | **CONFIRMED — LOW (diagnostic)** | `test_legacy_diagnostic_helper_cannot_authorize_the_guarded_case`: legacy returns `("PASS", "DIAGNOSTIC")`, guarded evaluation returns `STOP / missing-required-read`. |
| F3-1 | A forged or stale external checkpoint is rejected if the honest pin is used. | **FALSE POSITIVE** | `test_no_receipt_before_commit_or_without_latest_external_checkpoint`: forged tip, stale sequence and mismatched root raise `anchor-mismatch` / `checkpoint-binding`. |
| F3-2 | If an attacker controls both SQLite and the checkpoint channel, the hash chain cannot prove WORM/anti-rollback. | **CONFIRMED — structural boundary, not code-fixable** | Journal rewrite + rehash with a matching forged checkpoint is accepted by design. Mitigated by explicit `trust=EXTERNAL_ANCHOR_UNVERIFIED` and the optional external-receipt channel; real WORM still requires a store outside this repo. |
| F5-1 | Recall@5 can be inflated by duplicate ranks, unauthorized tail rows or revoked sources. | **FALSE POSITIVE** | `test_claim_recall_dedupes_before_top_five_in_stable_order`, `test_unauthorized_ranked_tail_never_silently_lowers_recall`: stable dedupe before top-5; any revoked/expired/foreign tail row raises `STOP / unauthorized-retrieval`. |
| F6-1 | Custody v1 had no explicit approval window, no least-privilege rights map, no two independent semantic reviews and no final-checkpoint binding. | **CONFIRMED — HIGH (model)** | Rewritten as `offline72-custody-v2`; covered by `test_approval_window_is_explicit_and_exclusive`, `test_rights_must_equal_least_privilege_exactly`, `test_two_ordered_independent_reviews_are_required`, `test_checkpoint_must_bind_genesis`. |
| F6-2 | No external receipt/trusted-channel design; mock receipts could be mistaken for signatures. | **CONFIRMED — PARTIAL** | `offline_receipt72.py` validates issuer allowlist, freshness, bindings and replay nonce via HMAC-SHA256 with a **public test key**. Results are labelled `MOCK_EXTERNAL_RECEIPT`; real identity/custody stays `NOT_VERIFIED`. |
| F7-1 | Source corpus validation (count, revision, canonical bytes, citation, typed values) is weak. | **FALSE POSITIVE** | `test_source_pin_count_and_revision`, `test_custody_adapter_rejects_excerpt_foreign_tenant_swap_and_orphans`, `test_abnormal_bytes_fail_closed`. |
| F7-2 | The 60-case profile itself was not authenticated (same root cause as F4-1). | **CONFIRMED — HIGH** | `PUBLIC_CASESET_PIN` and per-row `guards` digest; see F4-1 evidence. |

## 2. Source changes

- `scripts/offline_source72.py`: `guards_digest()` binds the exact required-read and forbidden-claim set; `Case.guards` is carried into the ledger row.
- `scripts/offline_qualification72.py`: `caseset()` + `PUBLIC_CASESET_PIN = ded0730ddbfdf98340f604b68a1301fa3253af8add609e987111f9cd26ef7970` (ordered SHA-256 of the 60 raw case bytes); ledger rows record `guards`; `Receipt.trust = EXTERNAL_ANCHOR_UNVERIFIED`.
- `scripts/offline_custody72.py`: custody v2 — explicit approval window, exact least-privilege rights, two ordered independent reviews with distinct references, revocation, retention relationship `delete_by >= acl.expires`, deletion clock `tick < delete_by`, ACL binding `expires > tick`, access-log rights/revocation, `finalize()` binds the final checkpoint by ledger root (separate from envelope genesis) and optionally verifies an external receipt.
- `scripts/offline_receipt72.py` (new): mock-only external receipt validator. **Not a signature system**; the bundled key is public.
- `scripts/offline_heldout67.py`: `Receipt.authority = "DIAGNOSTIC"` so legacy results cannot be presented as qualification receipts.
- `tests/offline_fixture72.py`: one case now genuinely requires a read that contributes no answer fact; custody v2 fixture (roles, rights ACL, two reviews, approval window, retention, signed mock receipt helper).
- `tests/test_offline_qualification72.py`: updated to custody v2 (approval shape, expiry clock) without weakening any assertion.
- `tests/test_offline_remediation73.py` (new): 20 adversarial regressions mapping to the confirmed findings.

## 3. Test evidence

Run on Windows, Python 3.14.3, worktree `D:\Projects\_pr73_work\repo`.

| Command | Result |
| --- | --- |
| `python -B -m unittest discover -s tests -p "test_offline*.py"` | **Ran 119 tests — OK** |
| `python -B -m unittest discover -s tests -p "test_offline_remediation73.py"` | **Ran 20 tests — OK** |
| `python -B -m unittest discover -s tests -p "test_quote*.py"` | **Ran 73 tests — OK** |
| `python -B -m scripts.offline_corpus63` | `Validated 9 products, 37 source claims, 12 public development oracles and 60 reserved slots. Held-out frozen: 0.` |
| `git diff --check 588b8fe1d3e54161fe194739d2c06552ca8c79f4 HEAD` | exit 0 |

Hosted CI (route-free namespace) and WSL were not re-run in this session: `NOT_RUN`.

## 4. Residual risks and blockers

- **HIGH — trust boundary:** SQLite + checkpoint channel under one attacker still defeats anti-rollback. Only an external WORM/anchor store can close this; code now states the limitation instead of implying WORM.
- **HIGH — real custody:** ACL enforcement, reviewer identity, approval signatures and actual deletion are simulated. `real_evidence` stays `NOT_VERIFIED`; the external receipt uses a public test key.
- **HIGH — private audit:** held-out corpus, private metric, model and six E2Es remain `NOT_RUN`; handling rights `NOT_AUTHORIZED`.
- **MEDIUM — case profile pin maintenance:** changing any case byte requires a new reviewed `PUBLIC_CASESET_PIN`; this is intentional but must be part of any future corpus revision.
- **LOW — legacy diagnostic helpers** remain in the repo for compatibility; they are marked but still callable by a caller that ignores the marker.

## 5. Independent review

No qualified independent reviewer was available in this session. Per the governance contract, this report **does not self-certify**. Status: `INDEPENDENT_REVIEW_BLOCKED`. A reviewer should, at the new technical SHA: (a) strip a guard and reseal to confirm `case-profile`; (b) run a guarded trace through the legacy helper and confirm it cannot yield an official receipt; (c) exercise forged/stale/replayed external receipts; (d) exercise approval-window, rights, review-order, revocation, retention and ACL expiry variants; (e) confirm the journal+checkpoint compromise remains declared as an external-boundary limitation.

## 6. Recommendation

**CONDITIONAL — public synthetic only.** The confirmed code-level defects (F4-1, F7-2, F6-1) are fixed and regression-tested; F3/F6 external-custody claims remain `NOT_VERIFIED` and block any Owner Gate claim. PR #73 stays Draft and unmerged; Owner Architecture Gate is not approved by this work.
