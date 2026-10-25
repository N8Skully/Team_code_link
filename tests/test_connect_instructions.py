#!/usr/bin/env python3
"""Connecting tells the agent to bring its own skills."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import mcp_server


class ConnectInstructionTests(unittest.TestCase):
    def test_connect_tells_the_agent_to_bring_its_skills(self) -> None:
        result = mcp_server.handle(Path("."), {"method": "initialize", "params": {}})
        text = result["instructions"].lower()
        self.assertIn("when you connect", text)
        self.assertIn("skill", text)
        self.assertIn("skill.md", text)
        join = next(tool for tool in mcp_server.TOOLS if tool["name"] == "join")
        self.assertIn("SKILL.md", join["description"])


if __name__ == "__main__":
    unittest.main()
