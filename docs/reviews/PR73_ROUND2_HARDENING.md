# PR #73 — Round 2 targeted security hardening (public-synthetic only)

Source branch `remediation/f3-f7-pr73` · Reviewed source SHA `329813e3db83265d4f6ed7862bcf9715ecb70ed5` · Audited baseline `0d884c9152d3812ad7f02b44f93f1375229c89ab` · Base `588b8fe1d3e54161fe194739d2c06552ca8c79f4` · Draft PR #73 (not merged, Owner Gate not approved).

Scope: only the offline public-synthetic qualification path. No Snapshot v2, no private data, no production access, no guard removed, no test weakened, no sealed evidence overwritten. Held-out corpus, models, six business E2Es, provider billing and the private retrieval metric remain `NOT_RUN`. This report does not self-certify; independent review remains `INDEPENDENT_REVIEW_BLOCKED`.

## 1. Round 1 review artifact availability

Round 1 findings were supplied in the mission text. No accessible Round 1 review artifact was found in this workspace: GitHub issue/PR comments, review threads, inline comments and commit comments were queried, and local evidence directories were searched. `docs/reviews/PR73_F3_F7_REMEDIATION.md` and `_audit72-logs/PR73_AUDIT_REPORT.md` are our own Round 1 remediation/audit records, not the external review. Reproduction below therefore reconstructs each NEW finding from the mission description, against the reviewed source SHA.

## 2. Phase A — red reproduction (before the fix)

Probe: `_pr73_work/probes/round2_repro.py` at `329813e` (public-synthetic fixtures, no repo assertion helpers). Raw log preserved locally at `_pr73_work/evidence/round2_red_probe.log`.

| Probe | Attack | Observed on `329813e` |
| --- | --- | --- |
| NEW-7a | Omit `journal_root`; checkpoint root = envelope genesis | `ACCEPT EXTERNAL_ANCHOR_UNVERIFIED` — the unsafe `journal_root=None → genesis` default |
| NEW-7b | Arbitrary caller-supplied `journal_root` | `ACCEPT EXTERNAL_ANCHOR_UNVERIFIED` — caller chose its own authority |
| NEW-7c | Prepared ledger root (valid baseline) | `ACCEPT EXTERNAL_ANCHOR_UNVERIFIED` |
| NEW-1 | Same validated receipt finalized twice, no store | accepted both times — no one-time consumption |
| NEW-2 | Same receipt finalized in two separate processes | accepted in both — replay state was an in-memory `set()` |
| NEW-3 | Reviewer timestamps reversed (first tick 2, second tick 1) | accepted — only list position was enforced |
| NEW-3 | Reviewer timestamps equal (2, 2) | accepted (also the fixture baseline) |

## 3. Phase B — remediation

| ID | Change | Failure codes added |
| --- | --- | --- |
| NEW-7 | Removed the `journal_root = genesis` fallback. `custody.ledger_root(genesis, custody_pin, acl_pin)` is the only derivation; `finalize` requires an explicit root equal to it. `qualification.prepare` uses the same function. | `journal-root` (omitted, arbitrary, stale), `checkpoint-binding` (checkpoint root ≠ ledger root) |
| NEW-1/2 | `offline_receipt72.verify` is pure/stateless. New `ReplayStore` (SQLite, `BEGIN IMMEDIATE`, `synchronous=FULL`, schema + `quick_check`) records one consumption per `(issuer, nonce)` via an atomic INSERT with primary-key uniqueness; same nonce with different bytes is a conflict. `finalize` requires the store when a receipt is present and returns `replay="MOCK_CONSUMED_ONCE"`; `trust` stays `EXTERNAL_ANCHOR_UNVERIFIED` / `MOCK_EXTERNAL_RECEIPT`. | `replay-store`, `replay-store-required`, `replay-shape`, `replay-schema`, `replay-storage`, `replay-create`, `receipt-replay`, `receipt-conflict` |
| NEW-3 | Explicit review ordering contract: `reviews` are listed in non-decreasing `tick` order. Equal ticks are allowed and follow list order; a later-tick review listed first is rejected. Role separation, distinct reference and duplicate-reviewer checks unchanged. | `custody-review-order` (existing `custody-review`, `custody-review-conflict` retained) |
| NEW-4 | No new mechanism. Existing revocation checks verified by tests: live revocation blocks (`custody-revoked`), unknown/duplicate target (`custody-revocation`), future revocation does not block. Caller-controlled pin limitation documented; no real revocation, identity or approval authority claimed. | none added |

Replay state is explicitly mock bookkeeping: it cannot prove issuer identity, real signature, real custody or authorization. The public MAC key means any caller can mint a receipt; the store only prevents the same nonce being used twice inside the tested harness.

## 4. Phase C — green evidence

Green probe: `_pr73_work/probes/round2_verify.py`, same attacks, independent expected-value checks. Log: `_pr73_work/evidence/round2_green_probe.log`.

| Probe | Observed after fix |
| --- | --- |
| NEW-7a omitted root | `REJECT journal-root` |
| NEW-7b arbitrary root | `REJECT journal-root` |
| NEW-7c checkpoint not bound to derived root | `REJECT checkpoint-binding` |
| NEW-7d valid derived root | `ACCEPT EXTERNAL_ANCHOR_UNVERIFIED` |
| NEW-1 first / second consumption | `MOCK_CONSUMED_ONCE` / `REJECT receipt-replay` |
| NEW-2 child process / parent after child | `ACCEPT MOCK_CONSUMED_ONCE` / `REJECT receipt-replay` |
| NEW-3 reversed / equal review ticks | `REJECT custody-review-order` / `ACCEPT prepared` |

`probes_failed=0` on Windows and in a route-free WSL network namespace (`unshare --net`, empty IPv4/IPv6 routes; loopback enabled only for the quote suite). Log: `_pr73_work/evidence/round2_routefree_wsl.log`.

Permanent regressions: `tests/test_offline_hardening73.py` (25 tests) plus the updated `tests/test_offline_remediation73.py` (21 tests).

| Command (worktree `D:\Projects\_pr73_work\repo`) | Result |
| --- | --- |
| `py -B -m unittest discover -s tests -p "test_offline*.py"` | **Ran 145 tests — OK**, exit 0 |
| `py -B -m unittest discover -s tests -p "test_quote*.py"` | **Ran 73 tests — OK**, exit 0 |
| `py -B -m scripts.offline_corpus63` | `Validated 9 products, 37 source claims, 12 public development oracles and 60 reserved slots. Held-out frozen: 0.` exit 0 |
| `git diff --check` | exit 0 |
| WSL Ubuntu 24.04, route-free netns: offline + quote + corpus | **145 OK + 73 OK**, routes empty before/after loopback up |
| Hosted CI at the final exact SHA | `NOT_RUN` in this session — requires the branch push; the previous SHA's checks are historical only |

## 5. Finding-to-test traceability

| ID | Regression tests |
| --- | --- |
| NEW-7 | `test_derived_ledger_root_is_the_only_accepted_root`, `test_omitted_journal_root_is_rejected`, `test_arbitrary_caller_root_is_rejected`, `test_stale_root_after_acl_change_is_rejected`, `test_checkpoint_must_match_the_ledger_root`, `test_official_path_derives_genesis_from_the_envelope` |
| NEW-1/NEW-2 | `test_validation_is_pure_and_repeatable`, `test_same_process_double_consumption_is_rejected`, `test_cross_process_consumption_persists`, `test_concurrent_consumption_admits_exactly_one`, `test_invalid_receipt_never_consumes`, `test_distinct_valid_nonces_are_independent`, `test_same_nonce_with_different_bytes_conflicts`, `test_receipt_requires_a_persistent_store`, `test_store_schema_tamper_is_rejected`, `test_consumption_is_labelled_mock_not_external_trust`; existing `test_mock_external_receipt_is_labelled_and_replay_protected`, `test_receipt_requires_a_persistent_replay_store`, `test_receipt_rejects_tamper_stale_issuer_and_binding` |
| NEW-3 | `test_reversed_review_ticks_are_rejected`, `test_equal_ticks_follow_explicit_list_order`, `test_chronological_ticks_are_accepted`, `test_duplicate_reviewer_and_reference_are_rejected`, `test_reviewer_role_separation_survives_ordering`; existing `test_two_ordered_independent_reviews_are_required` |
| NEW-4 | `test_live_revocation_blocks_use_and_future_revocation_does_not`, `test_unknown_and_duplicate_revocation_targets_are_rejected`, `test_real_evidence_cannot_be_claimed`, `test_pinned_role_names_are_caller_labels_not_identities` |

## 6. Residual risks

- **HIGH — trust boundary (unchanged):** a caller who controls SQLite, the checkpoint channel and the pinned documents can still present a consistent chain. The ledger root is now derived rather than caller-chosen, but derivation only binds authenticated pins; it does not create an external anchor. WORM/anti-rollback needs a store outside this repository.
- **HIGH — real custody:** the MAC key is public; identities, signatures, system ACLs, retention deletion and revocation authority are simulated. `real_evidence` stays `NOT_VERIFIED`.
- **MEDIUM — replay store is local mock state:** persistence is a local SQLite file. It proves one-time consumption inside this harness, not a distributed or authenticated replay service. Deleting **or copying/replacing** the file resets apparent consumption, and a caller that substitutes its own store class bypasses the check; store identity is not recorded in `Finalized`. `consume` also accepts a hand-built `Receipt` object, so validation and consumption must stay separate in any caller.
- **MEDIUM — review ordering is a mock contract:** non-decreasing ticks plus list position is explicit, but reviewer identity and real-world review independence are not verified. Role names are caller labels: relabelling `semantic_one`/`semantic_two` can place a later event first. The `custody-review-conflict` check is retained as defence-in-depth but is unreachable while `role-collision` enforces distinct roles.
- **MEDIUM — `finalize` vs `prepare`:** `finalize` binds the pins the caller presents; only `prepare` ties `proof.genesis` back to the pinned envelope (`custody-binding`). A caller using `finalize` directly must not treat its output as qualification.
- **HIGH — private audit:** held-out corpus, private metric, model and six E2Es remain `NOT_RUN`; handling rights `NOT_AUTHORIZED`.

## 7. Separate agent review (not third-party)

A separate read-only agent session (different context, same vendor — **not** a qualified third-party reviewer) independently reviewed commit `71003a7`, wrote its own probes outside the repository and reran the suites. Reported evidence: omitted/`None`/empty/uppercase/foreign-pin roots → `journal-root`; stale root after ACL change rejected; checkpoint mismatch → `checkpoint-binding`; fresh store object on a consumed file → `receipt-replay`; two-process sequence and four concurrent processes gave exactly one `MOCK_CONSUMED_ONCE`; same-nonce/different-bytes → `receipt-conflict`; invalid MAC left zero rows; missing store path → `replay-storage` with no file created; reversed ticks → `custody-review-order`; equal/ordered ticks accepted; duplicate reviewer/reference rejected. Suites it reran: hardening 25 OK, remediation 21 OK, offline 145 OK, quote 73 OK, corpus PASS, `git diff --check` exit 0. Verdict: NEW-7 and NEW-1/NEW-2 FIXED, NEW-3 FIXED as a list/role contract but only role-label chronology, NEW-4 correctly scoped with no real authority claimed. Its boundary findings are folded into §6, and one gap it named (envelope-to-genesis binding) is now covered at the official path by `test_official_path_derives_genesis_from_the_envelope`.

This does **not** satisfy the governance requirement for a qualified independent review. Third-party review remains `INDEPENDENT_REVIEW_BLOCKED`. A reviewer should, at the exact final SHA: (a) omit / substitute / stale the journal root and confirm `journal-root`; (b) consume one receipt twice in-process and across processes, and race four concurrent consumers; (c) confirm invalid receipts never consume and same-nonce conflicts are rejected; (d) reverse and equalize review ticks and confirm the ordering contract; (e) confirm revocation checks and that no real authority is claimed.

## 8. Recommendation

**CONDITIONAL — public synthetic only.** NEW-1, NEW-2, NEW-3 and NEW-7 are fixed and regression-tested on the public path; NEW-4 is verified with its trust boundary documented. Gate A (public-synthetic) recommends architecture review only after an independent reviewer reproduces the green probe. Gate B (real data / production) remains **NO-GO**: no real custody, identity, ACL, retention, provider cost or private-corpus evidence exists. PR #73 stays Draft; no merge and no Owner Gate approval is claimed here.
