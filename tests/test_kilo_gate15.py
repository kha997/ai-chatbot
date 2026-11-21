from concurrent.futures import ThreadPoolExecutor
import unittest

from scripts.kilo_gate15 import MODEL, PROMPT, Permit, approved_payload


class KiloGateTests(unittest.TestCase):
    def request(self):
        return {"model": MODEL, "messages": [
            {"role": "system", "content": "You are Kilo, a CLI coding assistant."},
            {"role": "user", "content": PROMPT},
        ], "stream": True}

    def test_reconstructs_and_enforces_scope(self):
        body = self.request()
        body["messages"][0]["content"] += " Untrusted extra content."
        result = approved_payload(body, None, "Kilo")
        self.assertEqual(result["messages"], [{"role": "user", "content": PROMPT}])
        self.assertEqual(result["max_tokens"], 128)
        for mutation in (
            {"model": "paid-model"}, {"tools": [{}]}, {"stream": False},
            {"messages": [{"role": "user", "content": "other"}]},
        ):
            with self.subTest(mutation=mutation):
                self.assertIsNone(approved_payload(body | mutation, None, "Kilo"))
        self.assertIsNone(approved_payload(body, "Bearer secret-fixture", "Kilo"))
        self.assertIsNone(approved_payload(body, None, "You are a title generator."))

    def test_one_permit_under_concurrency(self):
        permit = Permit()
        with ThreadPoolExecutor(max_workers=8) as threads:
            self.assertEqual(sum(threads.map(lambda _: permit.take(), range(32))), 1)
