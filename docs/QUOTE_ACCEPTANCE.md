# Synthetic quote acceptance fixtures

These fixtures define expected behavior for a deterministic, offline quote validator. The catalog prices, validity windows, customer inputs, and outcomes are synthetic. The fixture checks provide evidence about the dataset and its arithmetic. Validator execution is pending a separate change. [Owner scope approval](https://github.com/kha997/ai-chatbot/pull/48#issuecomment-7079372954).

## Baseline

The three answer cases are derived from the original [evaluation examples](../eval/examples.json) at commit `720a30ae25bc3a485c5d422e95edf17971d5b73a`.

| Scenario | Calculation | Expected total | Citation |
| --- | --- | ---: | --- |
| NHD, three boxes | 3 × 200,000 | 600,000 VND | `NHD-pricing-v1#p1` |
| HANU, 20 words | max(20 × 1,000, 50,000) | 50,000 VND | `HANU-pricing-v1#p1` |
| ZENA, two sessions | 2 × 300,000 | 600,000 VND | `ZENA-pricing-v1#p1` |

## Inputs and expected outcomes

The [fixtures](../eval/quote_acceptance.json) and [JSON Schema](../eval/quote_acceptance.schema.json) define three inputs to each case.

- `context` supplies the authenticated tenant and the trusted active source bindings. Each binding maps a tenant and SKU to an exact source ID and integer version. A binding must agree with the canonical record. A stale or revoked record can occur in the mapping when testing fail-closed behavior.
- `request` supplies the customer SKU, quantity, unit and currency. An optional `requested_tenant` is a customer claim. A tenant claim that disagrees with the authenticated tenant leads to refusal. In these scenarios the quantity is a positive whole count encoded as a string.
- `candidate` supplies a proposed source ID, version and citation. The validator resolves pricing from the canonical `sources` records. Amounts come from the canonical `unit_price` and `minimum` decimal strings. An accepted reference must match the tenant, SKU, active source ID and version, and the canonical citation. The source must be approved and satisfy `valid_from <= as_of < valid_until` at the fixed UTC fixture clock.

An `answer` returns `total`, `currency`, and `citation`. Compute the total as the larger of quantity times unit price and the minimum, with exact decimal arithmetic. The three tested totals require no rounding, tax, shipping or currency conversion. A `clarify` outcome covers an unknown SKU or an invalid quantity, unit, or currency. A `refuse` outcome covers a tenant conflict or a failed source eligibility or integrity check. Both outcomes contain only `behavior` and `reason`. The reason codes support assertions and can remain internal. These fixtures grant no side effects or binding quotes.

## Verification

The [fixture unit tests](../tests/test_quote_acceptance.py) check the schema, canonical source references, all three baseline totals and citations, and the declared failure cases. The tests use Python's standard library and a small check for the schema keywords this contract uses. GitHub Actions runs the quote-only test command on pull requests.

```bash
python3 -B -m unittest discover -s tests -p 'test_quote*.py' -v
```
