#!/usr/bin/env python3
"""Inject the shared room into a Cursor session."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import teamlink

sys.stdin.read()
try:
    repo = teamlink.resolve_repo()
    room = teamlink.render_room(repo, max_messages=15)
    text = (
        "You are in the Team Code Link room with up to five other computers. "
        "Use the team-code-link MCP tools room, listen, and say, or "
        "`python3 scripts/workspace.py`. Post before you edit files and mention "
        "the other computer with @name. "
        + teamlink.ROOM_BANNER
        + "\n\n"
        + room
    )
except Exception as exc:
    text = (
        "Team Code Link room is unavailable ("
        + teamlink.scrub(str(exc))
        + "). Continue the task. Use python3 scripts/workspace.py room when you need the other seats."
    )

json.dump({"additional_context": text}, sys.stdout)
sys.stdout.write("\n")
