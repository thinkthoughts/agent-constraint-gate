"""
agent-constraint-gate: minimal constraint layer for autonomous agents.

This module provides a small, framework-agnostic gate that can sit between
agent reasoning and tool execution:

    reason -> verify -> act

It evaluates a proposed action against a simple policy and returns a decision
object explaining whether the action is allowed, blocked, or should be revised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


@dataclass
class Decision:
    """Structured result from a constraint check."""
    allow: bool
    reason: str
    action: str = "block"  # "allow", "block", or "revise"
    matched_rule: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "action": self.action,
            "matched_rule": self.matched_rule,
            "details": self.details,
        }


def _normalize_path(path: str) -> str:
    """Normalize a filesystem path into a stable POSIX-like form."""
    try:
        return str(PurePosixPath(path))
    except Exception:
        return path


def _path_is_within(path: str, allowed_prefixes: Iterable[str]) -> bool:
    """Return True if path is inside any allowed prefix."""
    normalized = _normalize_path(path)
    for prefix in allowed_prefixes:
        normalized_prefix = _normalize_path(prefix)
        if normalized == normalized_prefix or normalized.startswith(normalized_prefix.rstrip("/") + "/"):
            return True
    return False


def _extract_domain(url: str) -> Optional[str]:
    """Extract hostname from a URL."""
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def _domain_allowed(domain: Optional[str], allowed_domains: Iterable[str]) -> bool:
    """Return True if domain matches or is a subdomain of an allowed domain."""
    if not domain:
        return False

    domain = domain.lower()
    for allowed in allowed_domains:
        allowed = allowed.lower()
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


DEFAULT_POLICY: Dict[str, Any] = {
    "default_action": "block",
    "rules": [
        {
            "name": "allow_safe_file_reads",
            "tool": "file_read",
            "allowed_paths": ["/workspace", "/tmp", "./"],
            "on_match": "allow",
            "reason": "File read is limited to approved paths.",
        },
        {
            "name": "restrict_file_writes",
            "tool": "file_write",
            "allowed_paths": ["/workspace/output", "/tmp", "./output"],
            "on_match": "allow",
            "reason": "File write is limited to approved output paths.",
        },
        {
            "name": "allow_known_http_domains",
            "tool": "http_request",
            "allowed_domains": ["api.openai.com", "example.com"],
            "allowed_methods": ["GET", "POST"],
            "on_match": "allow",
            "reason": "HTTP request is limited to approved domains and methods.",
        },
        {
            "name": "block_shell_by_default",
            "tool": "shell",
            "on_match": "block",
            "reason": "Shell access is blocked by default.",
        },
    ],
}


def verify_action(
    action: Dict[str, Any],
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Verify a proposed agent action against a policy.

    Parameters
    ----------
    action:
        Dictionary describing the requested operation. Typical examples:
            {"tool": "file_write", "path": "/workspace/output/a.txt"}
            {"tool": "http_request", "url": "https://api.openai.com/v1/responses", "method": "POST"}
            {"tool": "shell", "command": "rm -rf /"}

    policy:
        Optional policy dictionary. If omitted, DEFAULT_POLICY is used.

    Returns
    -------
    dict
        A decision object:
            {
                "allow": bool,
                "reason": str,
                "action": "allow" | "block" | "revise",
                "matched_rule": str | None,
                "details": {...}
            }
    """
    policy = policy or DEFAULT_POLICY

    tool = action.get("tool")
    if not tool:
        return Decision(
            allow=False,
            reason="Action is missing required field: 'tool'.",
            action="revise",
            details={"missing_field": "tool"},
        ).to_dict()

    for rule in policy.get("rules", []):
        if rule.get("tool") != tool:
            continue

        decision = _evaluate_rule(action=action, rule=rule)
        if decision is not None:
            return decision.to_dict()

    default_action = policy.get("default_action", "block")
    if default_action == "allow":
        return Decision(
            allow=True,
            reason=f"No specific rule matched tool '{tool}'; default policy allows it.",
            action="allow",
        ).to_dict()

    return Decision(
        allow=False,
        reason=f"No policy rule matched tool '{tool}'; default policy blocks it.",
        action="block",
    ).to_dict()


def _evaluate_rule(action: Dict[str, Any], rule: Dict[str, Any]) -> Optional[Decision]:
    """Return a decision if the rule applies; otherwise None."""
    tool = action.get("tool")
    rule_name = rule.get("name")

    if tool == "file_read" or tool == "file_write":
        path = action.get("path")
        if not path:
            return Decision(
                allow=False,
                reason=f"Tool '{tool}' requires a 'path'.",
                action="revise",
                matched_rule=rule_name,
                details={"missing_field": "path"},
            )

        allowed_paths = rule.get("allowed_paths", [])
        if allowed_paths and _path_is_within(path, allowed_paths):
            return Decision(
                allow=rule.get("on_match", "allow") == "allow",
                reason=rule.get("reason", "Path allowed by policy."),
                action=rule.get("on_match", "allow"),
                matched_rule=rule_name,
                details={"path": path},
            )

        return Decision(
            allow=False,
            reason=f"Path '{path}' is outside approved locations.",
            action="block",
            matched_rule=rule_name,
            details={"path": path, "allowed_paths": allowed_paths},
        )

    if tool == "http_request":
        url = action.get("url")
        method = str(action.get("method", "GET")).upper()

        if not url:
            return Decision(
                allow=False,
                reason="HTTP request requires a 'url'.",
                action="revise",
                matched_rule=rule_name,
                details={"missing_field": "url"},
            )

        allowed_methods = [m.upper() for m in rule.get("allowed_methods", ["GET"])]
        if method not in allowed_methods:
            return Decision(
                allow=False,
                reason=f"HTTP method '{method}' is not allowed.",
                action="block",
                matched_rule=rule_name,
                details={"method": method, "allowed_methods": allowed_methods},
            )

        domain = _extract_domain(url)
        allowed_domains = rule.get("allowed_domains", [])
        if _domain_allowed(domain, allowed_domains):
            return Decision(
                allow=rule.get("on_match", "allow") == "allow",
                reason=rule.get("reason", "Domain allowed by policy."),
                action=rule.get("on_match", "allow"),
                matched_rule=rule_name,
                details={"url": url, "domain": domain, "method": method},
            )

        return Decision(
            allow=False,
            reason=f"Domain '{domain}' is not on the allowlist.",
            action="block",
            matched_rule=rule_name,
            details={"url": url, "domain": domain, "allowed_domains": allowed_domains},
        )

    if tool == "shell":
        return Decision(
            allow=rule.get("on_match", "block") == "allow",
            reason=rule.get("reason", "Shell policy applied."),
            action=rule.get("on_match", "block"),
            matched_rule=rule_name,
            details={"command": action.get("command")},
        )

    # Generic fallback for matched tool rules with no specialized checker.
    on_match = rule.get("on_match", "block")
    return Decision(
        allow=on_match == "allow",
        reason=rule.get("reason", f"Policy applied for tool '{tool}'."),
        action=on_match,
        matched_rule=rule_name,
        details={"tool": tool},
    )


if __name__ == "__main__":
    demo_actions: List[Dict[str, Any]] = [
        {"tool": "file_write", "path": "/workspace/output/report.txt", "content": "ok"},
        {"tool": "file_write", "path": "/etc/passwd", "content": "bad idea"},
        {"tool": "http_request", "url": "https://api.openai.com/v1/responses", "method": "POST"},
        {"tool": "http_request", "url": "https://evil.example.net/steal", "method": "POST"},
        {"tool": "shell", "command": "rm -rf /"},
    ]

    for item in demo_actions:
        print(item)
        print(verify_action(item))
        print("-" * 60)
