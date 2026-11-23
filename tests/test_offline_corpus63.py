from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from unittest.mock import patch
import re
import unittest

from scripts import offline_corpus63 as corpus


ROOT = Path(__file__).resolve().parents[1] / "eval" / "offline63"
CLOCK = "2030-01-15T00:00:00Z"


class TripwireCatalog(dict):
    def get(self, key, default=None):
        raise AssertionError("foreign tenant caused a catalog read")


class OfflineCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = corpus.load_public(ROOT, ROOT.parent / "quote_acceptance.json")
        cls.sources = cls.package["sources"]["claims"]

    def test_frozen_development_negative_reasons_fit_public_schema(self):
        schema = corpus.read_json(ROOT / "public.schema.json")
        branch = next(item for item in schema["oneOf"] if "cases" in item["properties"])
        variants = branch["properties"]["cases"]["items"]["properties"]["oracle"]["oneOf"]
        pattern = variants[1]["properties"]["reason"]["pattern"]
        for case in self.package["dev"]["cases"]:
            if case["oracle"]["behavior"] != "answer":
                self.assertIsNotNone(re.fullmatch(pattern, case["oracle"]["reason"]), case["id"])

    def test_coverage_and_public_development_registry(self):
        self.assertEqual(len(self.package["coverage"]["slots"]), 60)
        self.assertEqual(len(self.package["dev"]["cases"]), 12)
        self.assertEqual(len(self.package["sources"]["products"]), 9)
        self.assertEqual(len({claim["family"] for claim in self.sources}), 8)

    def test_unreviewed_split_cannot_claim_a_private_freeze(self):
        coverage = deepcopy(self.package["coverage"])
        coverage["slots"][0]["expected_answer"] = "secret"
        with self.assertRaises(ValueError):
            corpus.validate_coverage(coverage)
        coverage = deepcopy(self.package["coverage"])
        coverage["state"] = "frozen"
        with self.assertRaises(ValueError):
            corpus.validate_coverage(coverage)

    def test_rephrasing_case_label_does_not_create_a_public_design_slot(self):
        coverage = deepcopy(self.package["coverage"])
        coverage["slots"][1]["focus"] = coverage["slots"][0]["focus"].upper() + "!"
        with self.assertRaises(ValueError):
            corpus.validate_coverage(coverage)

    def test_half_open_validity_and_pinned_citation(self):
        index = corpus.source_index(self.sources)
        ref = ("NHD-catalog-felt", 2, "p1")
        self.assertEqual(corpus.read_source(index, "NHD", ref, CLOCK)["value"], "dry")
        self.assertIsNone(corpus.read_source(index, "NHD", ref, "2031-01-01T00:00:00Z"))
        self.assertIsNone(corpus.read_source(index, "NHD", ("NHD-catalog-felt", 2, "p9"), CLOCK))

    def test_foreign_source_is_denied_before_lookup(self):
        for tenant in ("HANU", "ZENA"):
            self.assertIsNone(corpus.read_source(
                TripwireCatalog(), "NHD", (f"{tenant}-canary", 1, "p1"), CLOCK))

    def test_inactive_conflicting_and_unpublished_facts_never_answer(self):
        index = corpus.source_index(self.sources)
        for ref in [
            ("NHD-catalog-felt", 1, "p1"),
            ("NHD-policy-instruction", 1, "p1"),
            ("NHD-policy-voucher", 1, "p1"),
            ("NHD-availability-grid", 1, "p1"),
            ("NHD-prices-lock", 1, "p1"),
            ("NHD-availability-conflict", 1, "p1"),
        ]:
            with self.subTest(ref=ref):
                self.assertIsNone(corpus.read_source(index, "NHD", ref, CLOCK))

    def test_exact_quote_and_unknown_stock(self):
        quote = corpus.quote_draft(self.sources, "SYN-FOIL-B", "3", "roll", CLOCK)
        self.assertEqual(quote["amount"], "3901.50")
        self.assertEqual(quote["citation"], ("NHD-prices-foil", 1, "p1"))
        self.assertEqual(quote["effects"], [])
        self.assertIsNone(corpus.quote_draft(self.sources, "SYN-LOCK-D", "3", "box", CLOCK))
        self.assertIsNone(corpus.quote_draft(self.sources, "SYN-FOIL-B", "1.5", "roll", CLOCK))
        self.assertIsNone(corpus.lookup(self.sources, "SYN-FOIL-B", "available-count", CLOCK))
        self.assertEqual(corpus.quote_draft(self.sources, "SYN-FELT-B", "2", "sheet", CLOCK)["amount"],
                         "100.75")
        self.assertIsNone(corpus.quote_draft(self.sources, "SYN-GRID-C", "2", "pack", CLOCK))
        self.assertIsNone(corpus.quote_draft(self.sources, "SYN-MESH-E", "2", "strip", CLOCK))

    def test_public_facts_exercise_each_category_without_scored_question_text(self):
        # These are development invariants, not examples of the 60 private items.
        checks = {
            "offering": ("SYN-FOIL-D", "variant", "miếng phủ hổ phách mô phỏng"),
            "scope": ("SYN-MESH-E", "excluded", "Không chuyển đổi đơn vị dải sang đơn vị diện tích."),
            "price": ("SYN-FELT-B", "price-rule",
                      {"unit_price": "25.25", "minimum": "100.75", "currency": "VND", "unit": "sheet"}),
            "quote": ("SYN-GRID-C", "required-slots", ["sku", "variant", "unit", "quantity"]),
            "availability": ("SYN-FELT-B", "available-count", 6),
            "policy": ("sample-counter", "draft-cancel", "Bản nháp quầy mẫu được đóng vào cuối phiên giả lập."),
            "unknown": ("SYN-MESH-E", "delivery-date", None),
            "sources": ("SYN-FELT-A", "environment", "dry"),
            "injection": ("sample-counter", "discount", None),
        }
        for category, (subject, predicate, expected) in checks.items():
            with self.subTest(category=category):
                actual = corpus.lookup(self.sources, subject, predicate, CLOCK)
                self.assertEqual(None if actual is None else actual["value"], expected)
        aliases = corpus.alias_candidates(self.sources, "khung lưới thử", CLOCK)
        self.assertEqual(aliases, ("SYN-GRID-C", "SYN-GRID-D"))

    def test_public_manifest_detects_even_semantically_equivalent_byte_change(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            copytree(ROOT, bundle)
            path = bundle / "coverage.json"
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "noncanonical"):
                corpus.load_public(bundle, ROOT.parent / "quote_acceptance.json")

    def test_manifest_rejects_a_canonical_but_unapproved_revision(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            copytree(ROOT, bundle)
            path = bundle / "coverage.json"
            edited = corpus.read_json(path)
            edited["slots"][0]["focus"] = "proposed change"
            path.write_bytes(corpus.canonical(edited))
            self.assertNotEqual(sha256(path.read_bytes()).digest(),
                                sha256((ROOT / "coverage.json").read_bytes()).digest())
            with self.assertRaisesRegex(ValueError, "hash"):
                corpus.load_public(bundle, ROOT.parent / "quote_acceptance.json")

    def test_extra_artifact_rejected_before_any_public_or_extra_file_is_read(self):
        with TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            copytree(ROOT, bundle)
            (bundle / "extra.json").touch()
            with patch.object(Path, "read_bytes", side_effect=AssertionError("opened a file")):
                with self.assertRaisesRegex(ValueError, "unexpected artifact"):
                    corpus.load_public(bundle, ROOT.parent / "quote_acceptance.json")

    def test_answer_key_mutation_conflicts_with_existing_oracle(self):
        dev = deepcopy(self.package["dev"])
        dev["cases"][0]["oracle"]["total"] = "600001"
        historical = corpus.read_json(ROOT.parent / "quote_acceptance.json")
        with self.assertRaises(ValueError):
            corpus.validate_development(dev, historical)

    def test_unapproved_nested_fields_and_invalid_types_rejected(self):
        sources = deepcopy(self.package["sources"])
        sources["claims"][0]["hidden_oracle"] = "not public"
        with self.assertRaises(ValueError):
            corpus.validate_sources(sources)
        sources = deepcopy(self.package["sources"])
        sources["claims"][0]["version"] = True
        with self.assertRaises(ValueError):
            corpus.validate_sources(sources)


if __name__ == "__main__":
    unittest.main()
