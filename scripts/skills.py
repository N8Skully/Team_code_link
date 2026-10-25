#!/usr/bin/env python3
"""Read the skill names this computer's agents already have."""

from __future__ import annotations

from pathlib import Path

from orchestra import SKILL_RE


def _front_name(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    for line in text[3:end].splitlines():
        if line.lower().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def discover_skills(root: Path, home: Path | None = None) -> list[str]:
    """Names from SKILL.md files. Names that do not fit the room are skipped."""
    base = home or Path.home()
    folders = [
        root / ".cursor" / "skills",
        root / ".claude" / "skills",
        root / "skills",
        base / ".cursor" / "skills",
        base / ".claude" / "skills",
        base / ".codex" / "skills",
        base / ".agents" / "skills",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*/SKILL.md")):
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            name = (_front_name(raw) or path.parent.name).strip().lower()
            if not SKILL_RE.fullmatch(name) or name in seen:
                continue
            seen.add(name)
            found.append(name)
            if len(found) >= 40:
                return found
    return found
