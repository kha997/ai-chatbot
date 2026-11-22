import unittest

from run_opencode_sdk_mock import MODEL, PROMPT, RequestAudit


class RequestGateTests(unittest.TestCase):
    def test_one_exact_generation(self):
        task = {"model": MODEL, "stream": True, "max_tokens": 128,
                "messages": [{"role": "user", "content": PROMPT}]}
        gate = RequestAudit()
        for change in ({"tools": [{"type": "function"}]}, {"max_tokens": 129}, {"model": "wrong"}):
            self.assertEqual(RequestAudit().admit("POST", "/v1/chat/completions", task | change, 100), 403)
        self.assertEqual(gate.admit("POST", "/v1/chat/completions", task, 100), 200)
        self.assertTrue(gate.has_exact_exchange())
        self.assertEqual(gate.admit("GET", "/v1/models", None, 0), 200)
        self.assertFalse(gate.has_exact_exchange())
        self.assertEqual(gate.admit("POST", "/v1/chat/completions", task, 100), 409)

    def test_unknown_path_and_repeated_catalog(self):
        gate = RequestAudit()
        self.assertEqual(gate.admit("GET", "/v1/models", None, 0), 200)
        self.assertEqual(gate.admit("GET", "/v1/models", None, 0), 409)
        self.assertEqual(gate.admit("POST", "/api/generate", {}, 2), 404)
