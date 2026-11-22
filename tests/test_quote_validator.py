import unittest
from copy import deepcopy
from decimal import DefaultContext, Overflow, localcontext

from scripts.quote_validator import validate_quote
from test_quote_acceptance import read_json


class QuoteValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = read_json("quote_acceptance.json")

    def inputs(self, case_id="qa-NHD-price-01"):
        case = next(case for case in self.fixture["cases"] if case["id"] == case_id)
        return deepcopy({
            "context": case["context"],
            "request": case["request"],
            "candidate": case["candidate"],
            "sources": self.fixture["sources"],
            "as_of": self.fixture["as_of"],
        })

    def test_all_accepted_fixture_cases(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                inputs = self.inputs(case["id"])
                before = deepcopy(inputs)
                self.assertEqual(validate_quote(**inputs), case["oracle"])
                self.assertEqual(inputs, before)

    def test_foreign_catalog_changes_cannot_change_an_nhd_outcome(self):
        for case_id in ("qa-NHD-price-01", "wrong-tenant-source", "cross-tenant-citation", "forged-source"):
            with self.subTest(case=case_id):
                inputs = self.inputs(case_id)
                expected = validate_quote(**inputs)
                inputs["sources"] = [source for source in inputs["sources"] if source["tenant"] == "NHD"]
                self.assertEqual(validate_quote(**inputs), expected)

    def test_foreign_binding_cannot_supply_a_missing_sku(self):
        inputs = self.inputs("unknown-sku")
        inputs["context"]["active_sources"].append(
            {"tenant": "HANU", "sku": inputs["request"]["sku"], "source_id": "HANU-pricing-v1", "version": 1}
        )
        self.assertEqual(validate_quote(**inputs), {"behavior": "clarify", "reason": "unknown_sku"})

    def test_raw_tenant_override_is_rejected(self):
        inputs = self.inputs()
        inputs["request"]["tenant"] = "HANU"
        self.assertEqual(
            validate_quote(**inputs), {"behavior": "refuse", "reason": "requested_tenant_mismatch"}
        )

    def test_ambiguous_binding_or_source_is_refused(self):
        for collection in ("active_sources", "sources"):
            with self.subTest(collection=collection):
                inputs = self.inputs()
                records = inputs["context"][collection] if collection == "active_sources" else inputs[collection]
                records.append(dict(records[0]))
                self.assertEqual(validate_quote(**inputs)["behavior"], "refuse")
                self.assertEqual(set(validate_quote(**inputs)), {"behavior", "reason"})

    def test_boolean_versions_never_match_integer_versions(self):
        for location in ("candidate", "binding", "source"):
            with self.subTest(location=location):
                inputs = self.inputs()
                records = {
                    "candidate": inputs["candidate"],
                    "binding": inputs["context"]["active_sources"][0],
                    "source": inputs["sources"][0],
                }
                records[location]["version"] = True
                self.assertEqual(validate_quote(**inputs)["behavior"], "refuse")

    def test_unsupported_quantity_and_invalid_amounts_fail_without_a_quote(self):
        for quantity in ("NaN", "Infinity", "1e2", 3, True, "3\n"):
            with self.subTest(quantity=quantity):
                inputs = self.inputs()
                inputs["request"]["quantity"] = quantity
                self.assertEqual(validate_quote(**inputs), {"behavior": "clarify", "reason": "invalid_quantity"})
        for value in ("NaN", "Infinity", "1e2", "-1", 0.5, True, None):
            with self.subTest(amount=value):
                inputs = self.inputs()
                inputs["sources"][0]["unit_price"] = value
                self.assertEqual(validate_quote(**inputs), {"behavior": "refuse", "reason": "source_price_missing"})

    def test_validity_window_is_utc_and_half_open(self):
        inputs = self.inputs()
        source = inputs["sources"][0]
        inputs["as_of"] = source["valid_from"]
        self.assertEqual(validate_quote(**inputs)["behavior"], "answer")
        for as_of in (source["valid_until"], "2029-12-31T23:59:59Z", "2030-02-30T00:00:00Z"):
            with self.subTest(as_of=as_of):
                inputs["as_of"] = as_of
                self.assertEqual(validate_quote(**inputs), {"behavior": "refuse", "reason": "source_expired"})

    def test_canonical_citation_must_agree_with_source_and_paragraph(self):
        inputs = self.inputs()
        inputs["sources"][0]["citation"] = "HANU-pricing-v1#p1"
        inputs["candidate"]["citation"] = "HANU-pricing-v1#p1"
        self.assertEqual(validate_quote(**inputs), {"behavior": "refuse", "reason": "citation_mismatch"})

    def test_prices_are_exact_independent_of_decimal_context(self):
        inputs = self.inputs()
        inputs["sources"][0]["unit_price"] = "99999999999999999999999999999.1"
        with localcontext() as ctx:
            ctx.prec = 3
            self.assertEqual(validate_quote(**inputs)["total"], "299999999999999999999999999997.3")

    def test_prices_are_exact_when_default_decimal_context_changes(self):
        inputs = self.inputs()
        previous_limit, previous_trap = DefaultContext.Emax, DefaultContext.traps[Overflow]
        try:
            DefaultContext.Emax = 3
            DefaultContext.traps[Overflow] = False
            self.assertEqual(validate_quote(**inputs)["total"], "600000")
        finally:
            DefaultContext.Emax, DefaultContext.traps[Overflow] = previous_limit, previous_trap

    def test_request_charges_and_candidate_totals_are_ignored(self):
        inputs = self.inputs()
        inputs["request"].update(vat="1000", shipping="1000", certification="1000", permit="1000")
        inputs["candidate"]["total"] = "1"
        self.assertEqual(validate_quote(**inputs)["total"], "600000")
