"""Tests for the synthetic result and one-use policy only."""

import unittest

from run_dispatcher_mock import MockDispatch, POLICY, ORACLE, verify_result


class MockContractTests(unittest.TestCase):
    def test_fixed_policy_rejects_providers_and_noninteger_caps_before_spawn(self):
        for change in ({"adapter": "qoder"}, {"incremental_vnd": False}, {"model_requests": 1},
                       {"expiry": "not-a-field"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                MockDispatch(POLICY | change)

    def test_oracle_rejects_duplicate_keys_bools_and_trailing_results(self):
        for raw in (b'{"catalog":2,"handoff":true,"total":3}',
                    b'{"catalog":2,"handoff":0,"handoff":1,"total":3}',
                    b'{"catalog":2,"handoff":1,"total":3}\n{"catalog":2,"handoff":1,"total":3}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                verify_result(raw)
        self.assertEqual(verify_result(b'{"catalog":2,"handoff":1,"total":3}\n'), ORACLE)
