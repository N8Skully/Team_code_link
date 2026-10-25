#!/usr/bin/env python3
"""Stop an agent from reaching another computer or its database."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import boundary


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        json.dump(
            {
                "permission": "deny",
                "user_message": "The safety check could not read that request.",
                "agent_message": "The safety check could not read that request.",
            },
            sys.stdout,
        )
        return 0
    if not isinstance(payload, dict):
        payload = {}
    if payload.get("file_path") and "cwd" not in payload:
        permission, message = boundary.review_read(str(payload.get("file_path") or ""))
    elif "command" in payload and "tool_name" not in payload:
        permission, message = boundary.review_shell(str(payload.get("command") or ""))
    else:
        permission, message = "allow", ""
    result = {"permission": permission}
    if permission == "deny":
        result["user_message"] = message
        result["agent_message"] = message
    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
