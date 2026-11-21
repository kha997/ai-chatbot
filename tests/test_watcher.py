import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import github_watcher as watcher


class WatcherTests(unittest.TestCase):
    def test_routing_and_owner_approval(self):
        labels = [{"name": "agent:qoder"}, {"name": "work:approved"}]
        issue = dict(number=5, labels=labels, author_association="OWNER",
                     assignees=[{"login": "kha997"}], pull_request=None)
        pr = dict(number=6, requested_reviewers=[{"login": "kha997"}],
                  requested_teams=[], draft=False, head={"sha": "a" * 40})
        self.assertEqual(watcher.classify([issue], [pr]), [
            ["issue", 5, "codex", "approved", ""],
            ["issue", 5, "qoder", "triage", ""],
            ["review", 6, "codex", "review-requested", "a" * 40],
        ])
        issue["author_association"] = "NONE"
        self.assertEqual(watcher.classify([issue], [])[0][3], "triage")

    def test_gate_15_approval_cannot_be_spoofed_by_non_owner(self):
        issue = dict(number=8, labels=[{"name": "agent:codex"}],
                     author_association="OWNER", assignees=[],
                     pull_request=None)
        self.assertEqual(watcher.classify([issue], []),
                         [["issue", 8, "codex", "approved", ""]])
        issue["author_association"] = "NONE"
        self.assertEqual(watcher.classify([issue], []),
                         [["issue", 8, "codex", "triage", ""]])

    def test_review_label_routes_non_draft_pr_without_authorizing_work(self):
        issue = dict(number=6, labels=[{"name": "review:kilo"}],
                     assignees=[], pull_request={})
        pr = dict(number=6, requested_reviewers=[], requested_teams=[],
                  draft=False, head={"sha": "b" * 40})
        self.assertEqual(watcher.classify([issue], [pr]),
                         [["review", 6, "kilo", "review-requested", "b" * 40]])
        pr["draft"] = True
        self.assertEqual(watcher.classify([issue], [pr]), [])

    def test_restart_duplicates_and_failure_preserves_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            job = [["issue", 5, "qoder", "approved", ""]]
            self.assertEqual(watcher.poll(state, lambda: job, 100), 0)
            self.assertEqual(watcher.poll(state, lambda: job, 200), 0)
            self.assertEqual(json.loads((state / "state.json").read_text())["last_change"], 100)
            def fail():
                raise watcher.PollError("parse")
            self.assertEqual(watcher.poll(state, fail, 300), 1)
            self.assertEqual(watcher.poll(state, lambda: self.fail("backoff"), 301), 0)
            data = json.loads((state / "state.json").read_text())
            self.assertEqual(data["jobs"], job)
            self.assertEqual(data["last_success"], 200)
            self.assertEqual(watcher.poll(state, lambda: [], 2400), 0)
            self.assertEqual(json.loads((state / "state.json").read_text())["jobs"], [])

    def test_timeout_retry_parse_and_request_boundary(self):
        with patch.object(watcher, "get_page", side_effect=[TimeoutError(), b"[]"]) as get:
            self.assertEqual(watcher.page("issues", 1, sleep=lambda _: None), [])
            self.assertEqual(get.call_count, 2)
        with patch.object(watcher, "get_page", return_value=b"{invalid"):
            with self.assertRaises(watcher.PollError):
                watcher.page("pulls", 1)
        with self.assertRaises(ValueError):
            watcher.get_page("https://example.invalid", 1)
        request = watcher.request_for("issues", 2)
        self.assertEqual(request.method, "GET")
        self.assertTrue(request.full_url.startswith(
            "https://api.github.com/repos/kha997/ai-chatbot/issues?"))
        self.assertNotIn("Authorization", request.headers)

    def test_pause_and_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "paused").touch()
            self.assertEqual(watcher.run(folder, lambda: self.fail("paused")), 0)
            (folder / "paused").unlink()
            with watcher.exclusive(folder):
                self.assertEqual(watcher.run(folder, lambda: self.fail("overlap")), 0)
