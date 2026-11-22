"""Config and request gate regressions for the fixture."""

import unittest

from fixtures.ollama_local_client import verify_oracle
from run_ollama_local_mock import CONFIG, MODEL, PACKET, RequestGate, validate_config


class LocalContractTests(unittest.TestCase):
    def test_config_rejects_cloud_or_fallback(self):
        validate_config(CONFIG)
        for change in ({"model": "opencode/beam-free"}, {"enabled_providers": ["local-ollama", "opencode"]},
                       {"small_model": "opencode/beam-free"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_config(CONFIG | change)

    def test_exact_one_mock_post_and_no_tools(self):
        gate = RequestGate()
        self.assertEqual(gate.admit(PACKET | {"model": MODEL + "-other"}), 403)
        self.assertEqual(gate.admit(PACKET | {"tools": []}), 403)
        self.assertEqual(gate.admit(PACKET | {"stream": 0}), 403)
        self.assertEqual(gate.admit(PACKET | {"max_tokens": 128.0}), 403)
        self.assertEqual(gate.admit(PACKET), 200)
        self.assertEqual(gate.admit(PACKET), 409)

    def test_oracle_rejects_duplicate_fields(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_oracle('{"catalog":0,"catalog":2,"handoff":1,"total":3}')
