"""
agent-constraint-gate: minimal constraint layer for autonomous agents.

This module provides a small, framework-agnostic gate that can sit between
agent reasoning and tool execution:

    reason -> verify -> act

Core vocabulary used here:

- re-lift5:
    The verification layer combining numeric scoring + policy checks.

- constraint_score:
    A measurable pre-execution score in [0, 1] used to test whether a proposed
    action clears the minimum execution threshold.

- action:
    The external proposed tool call from an agent framework.

- left5:
    The normalized internal representation used by re-lift5 before a decision
    is returned.

This version enforces a clean 45° threshold:

    constraint_score >= 1 / sqrt(1^2 + 1^2) ~= 0.7071

Compatibility:
- Accepts `constraint_score` as the primary field.
- Also accepts `alignment_score` and `relift5_score` as aliases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse


FORTY_FIVE_DEGREE_THRESHOLD = 1 / sqrt(1**2 + 1**2)  # ~= 0.7071


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


def _coerce_score(raw_score: Any) -> Optional[float]:
    """Parse a numeric score into a float in [0, 1], or return None."""
    if raw_score is None:
        return None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None

    if not (0.0 <= score <= 1.0):
        return None
    return score


def _extract_constraint_score(action: Dict[str, Any]) -> tuple[Optional[float], Optional[str], Any]:
    """
    Extract score from preferred field names.

    Returns
    -------
    (score, source_field, raw_value)
    """
    score_fields = ("constraint_score", "alignment_score", "relift5_score")
    for field_name in score_fields:
        if field_name in action:
            raw_value = action.get(field_name)
            return _coerce_score(raw_value), field_name, raw_value
    return None, None, None


def normalize_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an external action into the internal left5 structure.

    left5 fields:
    - tool
    - params
    - constraint_score
    - score_source
    - raw
    """
    score, source_field, raw_value = _extract_constraint_score(action)

    params = {
        "path": action.get("path"),
        "url": action.get("url"),
        "method": action.get("method"),
        "command": action.get("command"),
        "content": action.get("content"),
    }

    return {
        "tool": action.get("tool"),
        "params": {k: v for k, v in params.items() if v is not None},
        "constraint_score": score,
        "score_source": source_field,
        "raw_score_value": raw_value,
        "raw": action,
    }


def _check_constraint(left5: Dict[str, Any]) -> Optional[Decision]:
    """
    Enforce the 45° constraint threshold when a score field is present.

    constraint_score:
        Float in [0, 1], interpreted as pre-execution constraint fitness.

    Returns
    -------
    Decision | None
        A revision decision when the score is invalid or below threshold.
        None means the action passes the numeric constraint layer or no score
        was provided.
    """
    source_field = left5.get("score_source")
    score = left5.get("constraint_score")
    raw_value = left5.get("raw_score_value")

    # Score is optional in this minimal implementation.
    if source_field is None:
        return None

    if score is None:
        return Decision(
            allow=False,
            reason=f"{source_field} must be a number between 0.0 and 1.0.",
            action="revise",
            details={
                "field": source_field,
                "value": raw_value,
            },
        )

    if score < FORTY_FIVE_DEGREE_THRESHOLD:
        return Decision(
            allow=False,
            reason=(
                "Constraint score below 45° threshold: "
                f"{score:.4f} < {FORTY_FIVE_DEGREE_THRESHOLD:.4f}"
            ),
            action="revise",
            details={
                "constraint_score": score,
                "threshold": FORTY_FIVE_DEGREE_THRESHOLD,
                "score_source": source_field,
                "constraint": "score >= 1/sqrt(1^2 + 1^2)",
            },
        )

    return None


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
    Verify a proposed agent action against re-lift5 scoring + policy rules.

    Pipeline:

        action -> left5 -> constraint check -> policy check -> decision

    Parameters
    ----------
    action:
        External action proposed by an agent framework.

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
    left5 = normalize_action(action)

    tool = left5.get("tool")
    if not tool:
        return Decision(
            allow=False,
            reason="Action is missing required field: 'tool'.",
            action="revise",
            details={"missing_field": "tool"},
        ).to_dict()

    constraint_decision = _check_constraint(left5)
    if constraint_decision is not None:
        return constraint_decision.to_dict()

    for rule in policy.get("rules", []):
        if rule.get("tool") != tool:
            continue

        decision = _evaluate_rule(left5=left5, rule=rule)
        if decision is not None:
            return decision.to_dict()

    default_action = policy.get("default_action", "block")
    if default_action == "allow":
        return Decision(
            allow=True,
            reason=f"No specific rule matched tool '{tool}'; default policy allows it.",
            action="allow",
            details={"left5": left5},
        ).to_dict()

    return Decision(
        allow=False,
        reason=f"No policy rule matched tool '{tool}'; default policy blocks it.",
        action="block",
        details={"left5": left5},
    ).to_dict()


def _evaluate_rule(left5: Dict[str, Any], rule: Dict[str, Any]) -> Optional[Decision]:
    """Return a decision if the rule applies; otherwise None."""
    tool = left5.get("tool")
    rule_name = rule.get("name")
    params = left5.get("params", {})

    if tool in ("file_read", "file_write"):
        path = params.get("path")
        if not path:
            return Decision(
                allow=False,
                reason=f"Tool '{tool}' requires a 'path'.",
                action="revise",
                matched_rule=rule_name,
                details={"missing_field": "path", "left5": left5},
            )

        allowed_paths = rule.get("allowed_paths", [])
        if allowed_paths and _path_is_within(path, allowed_paths):
            return Decision(
                allow=rule.get("on_match", "allow") == "allow",
                reason=rule.get("reason", "Path allowed by policy."),
                action=rule.get("on_match", "allow"),
                matched_rule=rule_name,
                details={"path": path, "left5": left5},
            )

        return Decision(
            allow=False,
            reason=f"Path '{path}' is outside approved locations.",
            action="block",
            matched_rule=rule_name,
            details={"path": path, "allowed_paths": allowed_paths, "left5": left5},
        )

    if tool == "http_request":
        url = params.get("url")
        method = str(params.get("method", "GET")).upper()

        if not url:
            return Decision(
                allow=False,
                reason="HTTP request requires a 'url'.",
                action="revise",
                matched_rule=rule_name,
                details={"missing_field": "url", "left5": left5},
            )

        allowed_methods = [m.upper() for m in rule.get("allowed_methods", ["GET"])]
        if method not in allowed_methods:
            return Decision(
                allow=False,
                reason=f"HTTP method '{method}' is not allowed.",
                action="block",
                matched_rule=rule_name,
                details={"method": method, "allowed_methods": allowed_methods, "left5": left5},
            )

        domain = _extract_domain(url)
        allowed_domains = rule.get("allowed_domains", [])
        if _domain_allowed(domain, allowed_domains):
            return Decision(
                allow=rule.get("on_match", "allow") == "allow",
                reason=rule.get("reason", "Domain allowed by policy."),
                action=rule.get("on_match", "allow"),
                matched_rule=rule_name,
                details={"url": url, "domain": domain, "method": method, "left5": left5},
            )

        return Decision(
            allow=False,
            reason=f"Domain '{domain}' is not on the allowlist.",
            action="block",
            matched_rule=rule_name,
            details={"url": url, "domain": domain, "allowed_domains": allowed_domains, "left5": left5},
        )

    if tool == "shell":
        return Decision(
            allow=rule.get("on_match", "block") == "allow",
            reason=rule.get("reason", "Shell policy applied."),
            action=rule.get("on_match", "block"),
            matched_rule=rule_name,
            details={"command": params.get("command"), "left5": left5},
        )

    on_match = rule.get("on_match", "block")
    return Decision(
        allow=on_match == "allow",
        reason=rule.get("reason", f"Policy applied for tool '{tool}'."),
        action=on_match,
        matched_rule=rule_name,
        details={"tool": tool, "left5": left5},
    )


if __name__ == "__main__":
    demo_actions: List[Dict[str, Any]] = [
        {
            "tool": "file_write",
            "path": "/workspace/output/report.txt",
            "content": "ok",
            "constraint_score": 0.91,
        },
        {
            "tool": "file_write",
            "path": "/workspace/output/report.txt",
            "content": "legacy alias still accepted",
            "alignment_score": 0.84,
        },
        {
            "tool": "file_write",
            "path": "/workspace/output/report.txt",
            "content": "needs revision",
            "relift5_score": 0.65,
        },
        {
            "tool": "http_request",
            "url": "https://api.openai.com/v1/responses",
            "method": "POST",
            "constraint_score": 0.81,
        },
        {
            "tool": "http_request",
            "url": "https://evil.example.net/steal",
            "method": "POST",
            "constraint_score": 0.95,
        },
        {
            "tool": "shell",
            "command": "rm -rf /",
            "constraint_score": 0.99,
        },
    ]

    for item in demo_actions:
        print(item)
        print(verify_action(item))
        print("-" * 60)
