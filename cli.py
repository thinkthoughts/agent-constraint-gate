"""
cli.py - simple command-line interface for agent-constraint-gate

Usage:
    python cli.py action.json
    python cli.py --stdin
    python cli.py --demo

Behavior:
- Loads a proposed action from JSON
- Runs verify_action(action)
- Prints normalized input (left5) and final decision as JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from constraint import normalize_action, verify_action


def load_action_from_file(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Action file not found: {path}")

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def load_action_from_stdin() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("No JSON received on stdin.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON on stdin: {exc}") from exc


def demo_action() -> Dict[str, Any]:
    return {
        "tool": "http_request",
        "url": "https://api.openai.com/v1/responses",
        "method": "POST",
        "constraint_score": 0.82,
    }


def print_json(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, sort_keys=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run re-lift5 constraint verification on a proposed action."
    )
    parser.add_argument(
        "action_file",
        nargs="?",
        help="Path to a JSON file containing an action object.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the action JSON object from standard input.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with a built-in demo action.",
    )

    args = parser.parse_args()

    try:
        if args.demo:
            action = demo_action()
        elif args.stdin:
            action = load_action_from_stdin()
        elif args.action_file:
            action = load_action_from_file(args.action_file)
        else:
            parser.print_help()
            return 1

        left5 = normalize_action(action)
        decision = verify_action(action)

        print_json("ACTION", action)
        print_json("LEFT5", left5)
        print_json("DECISION", decision)

        return 0

    except Exception as exc:
        error_payload = {
            "error": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
