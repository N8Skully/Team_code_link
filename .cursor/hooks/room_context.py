#!/usr/bin/env python3
"""Inject the live orchestra into a Cursor session."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import liveclient
from orchestra import ROOM_BANNER

sys.stdin.read()
try:
    root = liveclient.repo_root()
    room = liveclient.room(root)
    text = (
        "You are a player in the live Team Code Link orchestra. "
        "Read your part and follow the lead's approach. "
        "Use the team-code-link tools room, say, finish, help, and listen. "
        + ROOM_BANNER
        + "\n\n"
        + room
    )
except Exception as exc:
    text = (
        "The live Team Code Link room is not connected ("
        + str(exc)
        + "). The conductor runs python3 scripts/workspace.py serve. "
        "This computer joins with python3 scripts/workspace.py link <live link>."
    )

json.dump({"additional_context": text}, sys.stdout)
sys.stdout.write("\n")
