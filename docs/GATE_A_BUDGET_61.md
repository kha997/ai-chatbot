# Gate A request, token and all-in budget proposal

Date: 2026-11-23. [Sources](GATE_A_SOURCES_61.md) · [Controls](GATE_A_CONTROLS_61.md) · [Manifest](GATE_A_MANIFEST_61.md). **Inactive proposal; no spend or inference authorized. `BLOCKED_COST_CONTROL` until independently qualified. All runtime results NOT_RUN.**

## 1. Model and arithmetic

Retain accepted ADR-002 recommendation `gpt-5.4-mini-2026-03-17` on OpenAI direct Responses, standard synchronous text, reasoning `none`. Official model page still lists this snapshot on the access date; account availability is UNKNOWN. No alias, model upgrade, automatic fallback, tools, embeddings, reranker, batch discount, cached-token discount, subscription entitlement or trial credit assumed. This is a bounded starting candidate, not measured best Vietnamese quality.

Published prices: $0.75 per **1,000,000 input tokens**, $4.50 per **1,000,000 output tokens**. Regional processing uplift 10%. Proposed per-call maxima include **all billed** input (8000) and output (1000, including reasoning). Exact wire token accounting remains a preflight blocker. [Official model](https://developers.openai.com/api/docs/models/gpt-5.4-mini) and [pricing](https://developers.openai.com/api/docs/pricing), accessed 2026-11-23.

| Computation | USD, before unverified taxes/other fees |
| --- | ---: |
| Input maximum: 8000 × 0.75 / 1000000 | 0.006000 |
| Output maximum: 1000 × 4.50 / 1000000 | 0.004500 |
| One standard request | 0.010500 |
| Five concurrent standard requests | 0.052500 |
| 600 requests =4.8M input +0.6M output | 6.300000 |
| One regional request ×1.10 | 0.011550 |
| Five concurrent regional requests | 0.057750 |
| 600 regional requests | 6.930000 |
| Remaining under $10: standard / regional | 3.70 / 3.07 |

The remaining amount is **not verified tax/fee coverage**. Global endpoint is proposed; country residency is not guaranteed. For a sensitivity illustration only, 10% tax on the regional subtotal gives $7.623 for 600, leaving $2.377; this is not an applicable tax determination. Actual tax, FX/payment fees, fixed fees, minimum funding/purchase charge, region, account plan, host/network cash costs and billing rounding are UNKNOWN. No claim that $10 is presently guaranteed. Any required top-up/purchase counts in the all-in cash envelope, not just consumed tokens; no funding action is allowed now. No new infrastructure is planned; existing resource cost assumptions must still be declared/approved, not silently excluded.

## 2. Allocation — requests are not turns or scenarios

| Bucket | Logical work | Maximum charged attempt slots | Standard worst-case USD |
| --- | --- | ---: | ---: |
| qa | 60 ×2 repetitions ×<=2 calls | 240 | 2.520 |
| dev | 12 ×<=2 calls | 24 | 0.252 |
| adversarial | 24 ×<=2 calls; pre-egress denials actually zero | 48 | 0.504 |
| journeys | 12 ×<=2 total calls per journey | 24 | 0.252 |
| performance | 100 turns ×<=2 calls | 200 | 2.100 |
| contingency | Explicit eligible retries/diagnostics only | 64 | 0.672 |
| **Total** | No hidden warmups, graders or repair calls | **600** | **6.300** |

All buckets are ceilings, not targets or transferred credit. Unused zero-egress allowances remain unused. **A logical stage, its initial attempt and its retry are different counters.** The first five buckets fund only first attempts for at most two logical model stages per case execution (or per entire journey). Each retry is a new physical attempt charged once to the **contingency bucket and global600**, not to the original quota bucket again; it retains an `origin_suite` and parent-attempt ID for metrics. At most one retry per stage means at most four physical attempts per execution, still within the shared64 contingency, budget and30s deadline. Performance therefore has <=200 initial attempts, and at most264 origin-tagged attempts if all64 contingency slots are spent there; this is not264 plus another64. A diagnostic attempt uses contingency and global600 once and cannot be mislabeled as a scored/performance success.

Physical attempts consume a slot even on 4xx/5xx/timeouts/unknown acceptance; a request reservation is consumed before send. All model warmup/diagnostic requests, if later approved, must have frozen case IDs and use contingency; no model judge. Diagnostic IDs reserved `ga61-diag-001`…`ga61-diag-064`, only a specifically approved subset may be used; retry IDs are parent attempt plus `retry-1`, both share the64-slot ceiling. No retry creates a new logical QA case or replaces its first result. Extra requests beyond allocation or any new model require a new authorization, never an automatic follow-up issue.

## 3. Proposed pre-call reservation algorithm (design, no implementation)

Use integer micro-USD with conservative upward rounding, durable append-only attempt ledger, one run-wide transaction/lock and at most five in-flight requests across **all** workers. Counters and spend cannot reset at restart/month boundary. Test has one exclusive account/project credential route with no unrelated traffic; billing controls are defense in depth, not a substitute for the local gate.

Define verified rates `Pin`, `Pout`; regional multiplier `m`; maximum effective tax/percentage fees `t`; maximum additional per-call fee `f`; known fixed cash obligations `F`. Compute `W = ceil_microUSD(((8000*Pin +1000*Pout)/1000000*m + f)*(1+t))`. If fee compounding differs, use the actual conservatively bounded invoice formula, not this simplification. Freeze a **$2 all-in contingency reserve H** and an **$8 admission stop-loss** inside the $10 cap. H is unavailable for inference; it protects reconciliation/rounding, not unidentified fees. Unknown values block activation; a convenient percentage is not evidence. Proposed nominal totals fit $8 only if verified all-in charges do.

1. Before any transport, require signed, unexpired Owner execution approval bound to immutable manifest/candidate SHA; PASS on offline control proofs; current approved pricing/terms/model/region; matching corpus/oracle/prompt hashes; no STOP flag or unresolved usage. Unknowns → STOP, no send.
2. Under the run-wide lock, validate payload and fixed host/path, bound tokens including framing, recheck tenant/source/consent/control epochs, and enforce per-case logical-stage, per-stage retry, charged-bucket and global physical-attempt counters. First attempt uses its suite bucket; retry uses contingency only, with immutable origin-suite tag. Default concurrency 1, only performance uses up to 5. Sixth in-flight request waits boundedly within its turn deadline or fails locally; never creates a reservation outside the limit.
3. Let `A` be reconciled all-in actual charges, `R` outstanding/ambiguous worst-case reservations and `F` outstanding fixed obligations, with no double counting. Require `N_reserved + 1 <=600`, bucket allowance, and **`A + R + F + W <=8.00`** (therefore `A+R+F+W+H <=10.00`). Any threshold denial stops further dispatch; if mandatory work remains, INCONCLUSIVE. Reserve the full W and consume the attempt/case/bucket slot **atomically and durably before sending**. No check-then-send race or floating-point rounding.
4. Gateway consumes a one-use dispatch permit tied to payload hash, request ID, deadline and credential scope. Commit dispatch intent before handing bytes to transport; no redirects, proxy retry, SDK retry, hedging or second caller using the credential. Crash between intent and send is conservatively ambiguous, never automatically resent. Do not recycle a slot because a sender believes bytes were not transmitted.
5. On complete response, verify exact model and service tier, status/schema and complete billed usage. Actual charge <=W under frozen fee rules; atomically replace reservation with actual charge. Original attempt count never decreases. Token/model/price mismatch or usage absent/late/contradictory → STOP and retain W; observed charge above W is a failed cost-control hard gate, preserve actual liability and immediately contain. Do not declare cap compliance from a missing bill.
6. Reconcile provider ledger/account evidence after each bounded batch and at finish; no next batch while usage unknown. Planned batch boundary is at most five completed attempts. Price validity must cover the approved run window or there must be a verified binding maximum. Public pricing could change: no architecture claim of guaranteed $10 without evidence of the maximum during that window. Any discovered price/terms change invalidates admission. Under an accepted bounded-rate contract, already-sent calls are covered by R; otherwise execution is blocked.

No refund/released reservation funds extra cases beyond 600 or bucket maxima. Receipt and run locks survive crash. Cancellation or client timeout cannot release W without authoritative billing reconciliation. All-in final accounting includes unsuccessful/ambiguous requests and fees; report UNKNOWN if incomplete, never zero. Review proves both inequalities against fake transport under race/crash scenarios before any future live approval. This design does not certify the present repo as having a budget gateway.

## 4. Retry, errors and time bounds

Proposed default **zero automatic retries** at every layer. At most one controlled retry per logical failed call, <=64 across the entire run, only where the frozen policy declares it eligible and independent evidence establishes usage/cost reconciliation and safe replay. Each retry reserves W and a new attempt slot before transport. No output repair, model substitution, parallel hedged requests or hidden extraction reattempt.

| Condition | Action |
| --- | --- |
| 400/401/403, invalid schema/model/field, spend-limit 429 | STOP; configuration/auth/budget defect, no retry |
| Rate-limit 429 or transient 5xx with definitive completed attempt and reconciled charge | Record failure; at most one eligible retry, only if ledger/approval still valid, no unknown usage; wait max(Retry-After, 2s) plus 0–1s jitter within original 30s turn deadline, otherwise no retry |
| Timeout, broken connection, partial/truncated response, crash or unknown provider acceptance | Retain full W; STOP all dispatch; reconcile, no automatic retry |
| Missing usage, unexpected model/tier, price/fee drift, ledger corruption/lock failure | STOP; no billing inference from HTTP success or token estimates |
| High-severity safety failure, source/hash mismatch, wrong egress | STOP and preserve evidence, no diagnostic model call |
| Input too large or unapproved before send | Zero provider requests; record local denial. Mandatory-case inability → STOP/INCONCLUSIVE rather than truncation |

The two logical stages and any permitted retry share one30s turn deadline including queues, backoff and rendering; proposed whole execution window <=2h, frozen start/end expiry, no scheduled resume. Expiry stops new dispatch and leaves admitted liabilities reserved. No “keep trying until it works”. A transient error lacking complete usage remains UNKNOWN regardless of apparent HTTP code and cannot take the retry branch. A retry later authorized after reconciliation still counts failed original attempt in reliability and preserves first-response QA result.

## 5. Account controls and qualification matrix

[Official spend-limit guidance](https://developers.openai.com/api/docs/guides/spend-limits), checked 2026-11-23, distinguishes alerts from enforced project/organization limits and warns enforcement is not instantaneous. Thus neither dashboard alert nor provider hard-limit setting alone guarantees this experiment's exact all-in cap. Account eligibility, enforceability and overshoot are UNKNOWN; no account inspected. Require dedicated approved project/credential, no other spend routes, no auto-top-up/chargeable fallback, least privilege and evidence of effective provider/account protections. Settings changes need separate approval. If applicable billing protection/rate maximum cannot be verified, retain **BLOCKED_COST_CONTROL**, even if arithmetic fits.

Future offline mandatory tests (all NOT_RUN): 599→600→601 attempts; five concurrent final-slot contenders; cost exactly at and one micro-USD over $8; per-bucket exhaustion; taxes/fixed charge consuming margin; Unicode/framing token-bound overflow; disabled SDK/proxy redirects/retry; forged usage/model; retry consumes both counters; failed requests not refunded; crash before reserve/after reserve/before send/after send/before receipt/after receipt; ledger loss and stale process lease; machine restart; kill switch with five in-flight; price increase; foreign credential/network bypass; duplicate permit; final provider mismatch. Every test captures fake transport call count and durable ledger state, not just response text. No such code is added/run here.

Before execution recommendation: lead supplies immutable implementation and offline logs, reviewer challenges all admission paths plus account protection evidence, Owner approves exact cost/data/access terms. “600 requests under $10” is **conditional engineering design**, not a measured or unconditional guarantee. Current request count is 0 for the experiment; runtime usage/cost metrics are NOT_RUN, not measured zero-token API receipts.
