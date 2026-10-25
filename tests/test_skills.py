#!/usr/bin/env python3
"""Skill files on this computer become the names the room can match."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from skills import discover_skills


class SkillDiscoveryTests(unittest.TestCase):
    def test_a_skill_file_contributes_its_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / ".cursor" / "skills" / "blender-lighting"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("---\nname: blender-lighting\n---\nLight a scene.\n", encoding="utf-8")
            long_name = root / "skills" / "this-name-is-way-too-long-for-the-room"
            long_name.mkdir(parents=True)
            (long_name / "SKILL.md").write_text("# too long\n", encoding="utf-8")
            found = discover_skills(root, home=root / "empty-home")
        self.assertEqual(found, ["blender-lighting"])


if __name__ == "__main__":
    unittest.main()
