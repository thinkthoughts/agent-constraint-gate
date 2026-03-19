"""
Basic tests for agent-constraint-gate.

Run with:
    python -m unittest tests/test_constraint.py
"""

import unittest

from constraint import (
    FORTY_FIVE_DEGREE_THRESHOLD,
    normalize_action,
    score_action,
    verify_action,
)


class TestConstraintGate(unittest.TestCase):
    def test_normalize_action_keeps_tool_and_params(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "constraint_score": 0.82,
        }
        left5 = normalize_action(action)
        self.assertEqual(left5["tool"], "http_request")
        self.assertEqual(left5["params"]["url"], action["url"])
        self.assertEqual(left5["params"]["method"], "POST")
        self.assertEqual(left5["constraint_score"], 0.82)
        self.assertEqual(left5["score_source"], "constraint_score")

    def test_verify_action_missing_tool_revises(self):
        decision = verify_action({"url": "https://api.openai.com"})
        self.assertFalse(decision["allow"])
        self.assertEqual(decision["action"], "revise")
        self.assertIn("tool", decision["reason"])

    def test_safe_file_write_allowed(self):
        action = {
            "tool": "file_write",
            "path": "/workspace/output/report.txt",
            "content": "hello",
            "constraint_score": 0.95,
        }
        decision = verify_action(action)
        self.assertTrue(decision["allow"])
        self.assertEqual(decision["action"], "allow")

    def test_file_write_outside_allowed_path_blocked(self):
        action = {
            "tool": "file_write",
            "path": "/etc/passwd",
            "content": "oops",
            "constraint_score": 0.95,
        }
        decision = verify_action(action)
        self.assertFalse(decision["allow"])
        self.assertEqual(decision["action"], "block")
        self.assertIn("outside approved", decision["reason"])

    def test_low_constraint_score_revises_before_policy(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "constraint_score": 0.60,
        }
        decision = verify_action(action)
        self.assertFalse(decision["allow"])
        self.assertEqual(decision["action"], "revise")
        self.assertIn("45° threshold", decision["reason"])

    def test_allowed_http_domain_passes(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "constraint_score": 0.90,
        }
        decision = verify_action(action)
        self.assertTrue(decision["allow"])
        self.assertEqual(decision["action"], "allow")

    def test_blocked_http_domain_fails_policy(self):
        action = {
            "tool": "http_request",
            "url": "https://evil.example.net/steal",
            "method": "POST",
            "constraint_score": 0.95,
        }
        decision = verify_action(action)
        self.assertFalse(decision["allow"])
        self.assertEqual(decision["action"], "block")
        self.assertIn("allowlist", decision["reason"])

    def test_shell_blocked_even_with_high_score(self):
        action = {
            "tool": "shell",
            "command": "echo hello",
            "constraint_score": 0.99,
        }
        decision = verify_action(action)
        self.assertFalse(decision["allow"])
        self.assertEqual(decision["action"], "block")
        self.assertIn("Shell", decision["reason"])

    def test_alias_alignment_score_still_accepted(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "alignment_score": 0.85,
        }
        decision = verify_action(action)
        self.assertTrue(decision["allow"])
        self.assertEqual(decision["action"], "allow")

    def test_alias_relift5_score_still_accepted(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "relift5_score": 0.85,
        }
        decision = verify_action(action)
        self.assertTrue(decision["allow"])
        self.assertEqual(decision["action"], "allow")

    def test_score_action_computes_when_missing(self):
        action = {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
        }
        left5 = normalize_action(action)
        scored = score_action(left5)
        self.assertIn("constraint_score", scored)
        self.assertIn("score_breakdown", scored)
        self.assertTrue(0.0 <= scored["constraint_score"] <= 1.0)

    def test_computed_score_can_trigger_revision(self):
        action = {
            "tool": "shell",
            "command": "rm -rf /",
        }
        decision = verify_action(action)
        self.assertFalse(decision["allow"])
        self.assertIn(decision["action"], ("revise", "block"))

    def test_threshold_constant_is_expected(self):
        self.assertAlmostEqual(FORTY_FIVE_DEGREE_THRESHOLD, 0.70710678, places=6)


if __name__ == "__main__":
    unittest.main()
