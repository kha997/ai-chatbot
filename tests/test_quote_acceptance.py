import json
import re
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path


EVAL = Path(__file__).resolve().parents[1] / "eval"
JSON_TYPES = {
    "array": (list,),
    "boolean": (bool,),
    "integer": (int,),
    "null": (type(None),),
    "number": (int, float),
    "object": (dict,),
    "string": (str,),
}


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(name):
    return json.loads(
        (EVAL / name).read_text(encoding="utf-8"),
        object_pairs_hook=no_duplicate_keys,
    )


def schema_errors(value, schema, root, path="$"):
    """Check the JSON Schema keywords used by the fixture contract."""
    if "$ref" in schema:
        name = schema["$ref"].removeprefix("#/$defs/")
        return schema_errors(value, root["$defs"][name], root, path)
    if "oneOf" in schema:
        matches = sum(not schema_errors(value, branch, root, path) for branch in schema["oneOf"])
        return [] if matches == 1 else [f"{path}: expected exactly one schema alternative"]

    kind = schema.get("type")
    if kind and type(value) not in JSON_TYPES[kind]:
        return [f"{path}: expected {kind}"]
    errors = []
    if "const" in schema:
        expected = schema["const"]
        if type(value) is not type(expected) or value != expected:
            errors.append(f"{path}: expected {expected!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: unexpected value {value!r}")
    if "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: invalid lexical form {value!r}")
    if "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: below minimum")
    if "minItems" in schema and len(value) < schema["minItems"]:
        errors.append(f"{path}: too few entries")
    if "properties" in schema:
        properties = schema["properties"]
        missing = set(schema.get("required", ())) - value.keys()
        extra = value.keys() - properties.keys()
        if missing:
            errors.append(f"{path}: missing {sorted(missing)}")
        if extra and schema.get("additionalProperties") is False:
            errors.append(f"{path}: unexpected {sorted(extra)}")
        for key in value.keys() & properties.keys():
            errors.extend(schema_errors(value[key], properties[key], root, f"{path}.{key}"))
    if "items" in schema:
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], root, f"{path}[{index}]"))
    return errors


def utc_timestamp(value):
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


class QuoteAcceptanceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = read_json("quote_acceptance.json")
        cls.schema = read_json("quote_acceptance.schema.json")
        cls.examples = read_json("examples.json")
        cls.sources = {source["source_id"]: source for source in cls.fixture["sources"]}
        cls.cases = {case["id"]: case for case in cls.fixture["cases"]}

    def test_fixture_conforms_to_schema(self):
        self.assertEqual(schema_errors(self.fixture, self.schema, self.schema), [])

    def test_non_answer_schema_rejects_total_or_citation_even_when_null(self):
        schema = self.schema["$defs"]["oracle"]
        for behavior, reason in (("refuse", "source_revoked"), ("clarify", "invalid_quantity")):
            for field in ("total", "citation", "currency"):
                with self.subTest(behavior=behavior, field=field):
                    oracle = {"behavior": behavior, "reason": reason, field: None}
                    self.assertTrue(schema_errors(oracle, schema, self.schema))

    def test_source_and_case_ids_are_unique(self):
        self.assertEqual(len(self.sources), len(self.fixture["sources"]))
        self.assertEqual(len(self.cases), len(self.fixture["cases"]))

    def test_sources_have_canonical_citations_and_valid_windows(self):
        for source in self.sources.values():
            with self.subTest(source=source["source_id"]):
                self.assertEqual(source["source_id"], f'{source["tenant"]}-pricing-v{source["version"]}')
                self.assertEqual(source["citation"], f'{source["source_id"]}#{source["paragraph_id"]}')
                self.assertLess(utc_timestamp(source["valid_from"]), utc_timestamp(source["valid_until"]))
                self.assertGreater(Decimal(source["unit_price"]), 0)

    def test_active_source_bindings_identify_exact_canonical_revisions(self):
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                keys = set()
                for binding in case["context"]["active_sources"]:
                    key = (binding["tenant"], binding["sku"])
                    self.assertNotIn(key, keys)
                    keys.add(key)
                    source = self.sources[binding["source_id"]]
                    for field in ("tenant", "sku", "version"):
                        self.assertEqual(binding[field], source[field])

    def test_baseline_totals_and_citations_preserve_golden_examples(self):
        totals = {"NHD": "600000", "HANU": "50000", "ZENA": "600000"}
        legacy_cases = {case["id"]: case for case in self.examples["cases"]}
        legacy_sources = {source["id"]: source for source in self.examples["documents"]}
        baseline = [case for case in self.cases.values() if "baseline_case_id" in case]
        self.assertEqual({case["baseline_case_id"] for case in baseline}, set(legacy_cases))
        self.assertEqual(len(baseline), len(legacy_cases))
        for case in baseline:
            with self.subTest(case=case["id"]):
                legacy_case = legacy_cases[case["baseline_case_id"]]
                source = self.sources[case["candidate"]["source_id"]]
                legacy_source = legacy_sources[source["source_id"]]
                oracle = case["oracle"]
                self.assertEqual(oracle["behavior"], "answer")
                self.assertEqual(case["context"]["tenant"], legacy_case["tenant"])
                self.assertEqual(case["request"]["quantity"], legacy_case["quantity"])
                self.assertIn(
                    {key: source[key] for key in ("tenant", "sku", "source_id", "version")},
                    case["context"]["active_sources"],
                )
                for key in ("sku", "unit", "currency"):
                    self.assertEqual(case["request"][key], source[key])
                for key in ("source_id", "version", "citation"):
                    self.assertEqual(case["candidate"][key], source[key])
                for key in ("unit", "currency", "unit_price", "version"):
                    self.assertEqual(source[key], legacy_source[key])
                self.assertEqual(source["minimum"], legacy_source.get("minimum", "0"))
                for key in ("total", "currency", "citation"):
                    self.assertEqual(oracle[key], legacy_case["oracle"][key])
                self.assertEqual(oracle["total"], totals[legacy_case["tenant"]])
                self.assertEqual(oracle["citation"], source["citation"])
                calculated = max(
                    Decimal(source["unit_price"]) * Decimal(case["request"]["quantity"]),
                    Decimal(source["minimum"]),
                )
                self.assertEqual(calculated, Decimal(oracle["total"]))

    def test_customer_input_failures_change_the_intended_field(self):
        baseline_request = self.cases["qa-NHD-price-01"]["request"]
        overrides = {
            "customer-tenant-override": {"requested_tenant": "HANU"},
            "unknown-sku": {"sku": "SYN-TILE-UNKNOWN"},
            "zero-quantity": {"quantity": "0"},
            "fractional-quantity": {"quantity": "1.5"},
            "nonnumeric-quantity": {"quantity": "several"},
            "wrong-currency": {"currency": "USD"},
            "wrong-unit": {"unit": "session"},
        }
        for case_id, changed in overrides.items():
            with self.subTest(case=case_id):
                self.assertEqual(self.cases[case_id]["request"], baseline_request | changed)
        unknown = self.cases["unknown-sku"]
        self.assertIsNone(unknown["candidate"])
        self.assertNotIn(unknown["request"]["sku"], {source["sku"] for source in self.sources.values()})

    def test_required_negative_cases_have_explicit_safe_oracles(self):
        expected = {
            "wrong-tenant-source": ("refuse", "source_tenant_mismatch"),
            "customer-tenant-override": ("refuse", "requested_tenant_mismatch"),
            "expired-source": ("refuse", "source_expired"),
            "revoked-source": ("refuse", "source_revoked"),
            "old-version": ("refuse", "source_revision_mismatch"),
            "mismatched-candidate-version": ("refuse", "source_revision_mismatch"),
            "unknown-sku": ("clarify", "unknown_sku"),
            "zero-quantity": ("clarify", "invalid_quantity"),
            "fractional-quantity": ("clarify", "invalid_quantity"),
            "nonnumeric-quantity": ("clarify", "invalid_quantity"),
            "wrong-currency": ("clarify", "currency_mismatch"),
            "forged-source": ("refuse", "source_unknown"),
            "cross-tenant-citation": ("refuse", "citation_mismatch"),
            "wrong-unit": ("clarify", "unit_mismatch"),
        }
        for case_id, (behavior, reason) in expected.items():
            with self.subTest(case=case_id):
                self.assertEqual(self.cases[case_id]["oracle"], {"behavior": behavior, "reason": reason})

    def test_negative_source_cases_represent_distinct_controls(self):
        at = utc_timestamp(self.fixture["as_of"])
        expired = self.sources[self.cases["expired-source"]["candidate"]["source_id"]]
        revoked = self.sources[self.cases["revoked-source"]["candidate"]["source_id"]]
        old_case = self.cases["old-version"]
        old_source = self.sources[old_case["candidate"]["source_id"]]
        trusted_current = self.sources[old_case["context"]["active_sources"][0]["source_id"]]
        self.assertEqual(expired["status"], "approved")
        self.assertEqual(utc_timestamp(expired["valid_until"]), at)
        self.assertEqual(revoked["status"], "revoked")
        self.assertLessEqual(utc_timestamp(revoked["valid_from"]), at)
        self.assertGreater(utc_timestamp(revoked["valid_until"]), at)
        self.assertEqual(old_source["status"], "approved")
        self.assertLessEqual(utc_timestamp(old_source["valid_from"]), at)
        self.assertGreater(utc_timestamp(old_source["valid_until"]), at)
        for key in ("tenant", "sku"):
            self.assertEqual(old_source[key], trusted_current[key])
        self.assertLess(old_source["version"], trusted_current["version"])
        self.assertEqual(trusted_current["status"], "approved")
        self.assertLessEqual(utc_timestamp(trusted_current["valid_from"]), at)
        self.assertGreater(utc_timestamp(trusted_current["valid_until"]), at)
        spoofed = self.cases["mismatched-candidate-version"]["candidate"]
        canonical = self.sources[spoofed["source_id"]]
        self.assertEqual(spoofed["citation"], canonical["citation"])
        self.assertNotEqual(spoofed["version"], canonical["version"])
        self.assertNotIn(self.cases["forged-source"]["candidate"]["source_id"], self.sources)
        cross_citation = self.cases["cross-tenant-citation"]["candidate"]["citation"]
        cross_source = self.sources[cross_citation.split("#")[0]]
        self.assertEqual(cross_source["citation"], cross_citation)
        self.assertNotEqual(cross_source["tenant"], self.cases["cross-tenant-citation"]["context"]["tenant"])


if __name__ == "__main__":
    unittest.main()
