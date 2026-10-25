#!/usr/bin/env python3
"""Orchestra assignment, pairing, and partition rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import orchestra


NOW = "2026-10-25T04:00:00Z"


def players(state, *specs: tuple[str, str, list[str]]) -> None:
    for seat, agent, skills in specs:
        orchestra.join(state, seat, agent, skills, NOW)


def plan(state, conductor: str, tasks: list[dict], title: str = "Build the piece") -> None:
    orchestra.conduct(state, conductor, NOW)
    orchestra.publish_plan(
        state,
        conductor,
        {
            "title": title,
            "summary": "Ship the parts as one piece.",
            "framework": "Each part exposes the interface the next part calls.",
            "tasks": tasks,
        },
        NOW,
    )


def task_named(state, title: str) -> dict:
    for task in state["tasks"]:
        if task["title"] == title:
            return task
    raise AssertionError(title)


class OrchestraTests(unittest.TestCase):
    def test_six_computers_is_the_limit(self) -> None:
        state = orchestra.empty_state()
        for name in ("home", "office", "laptop", "studio", "shop", "travel"):
            orchestra.join(state, name, "claude", [], NOW)
        with self.assertRaises(orchestra.OrchestraError) as caught:
            orchestra.join(state, "spare", "claude", [], NOW)
        self.assertIn("All 6 computers", str(caught.exception))
        orchestra.join(state, "home", "cursor", ["ui"], NOW)
        self.assertEqual(len(state["seats"]), 6)

    def test_fewer_parts_become_pairs(self) -> None:
        state = orchestra.empty_state()
        players(
            state,
            ("home", "claude", ["ui"]),
            ("office", "cursor", ["api"]),
            ("studio", "hermes", ["ui"]),
            ("shop", "chatgpt", ["api"]),
        )
        plan(
            state,
            "home/claude",
            [
                {"title": "Login form", "brief": "Draw the form", "skills": ["ui"], "connects": ["Session API"], "interface": "calls Session API"},
                {"title": "Session API", "brief": "Own the session", "skills": ["api"], "connects": ["Login form"], "interface": "exports Session"},
            ],
        )
        form = task_named(state, "Login form")
        api = task_named(state, "Session API")
        self.assertEqual(form["members"], ["home/claude", "studio/hermes"])
        self.assertEqual(api["members"], ["office/cursor", "shop/chatgpt"])
        self.assertEqual(form["lead"], "home/claude")
        self.assertIn("calls Session API", form["interface"])

    def test_extra_parts_wait_and_the_first_free_player_leads_the_next(self) -> None:
        state = orchestra.empty_state()
        players(
            state,
            ("home", "claude", ["ui"]),
            ("office", "cursor", ["api"]),
        )
        plan(
            state,
            "home/claude",
            [
                {"title": "Login form", "brief": "Draw the form", "skills": ["ui"]},
                {"title": "Session API", "brief": "Own the session", "skills": ["api"]},
                {"title": "Docs", "brief": "Explain the seams", "skills": ["docs"]},
                {"title": "Notes", "brief": "Capture decisions", "skills": ["docs"]},
            ],
        )
        self.assertEqual(task_named(state, "Login form")["lead"], "home/claude")
        self.assertEqual(task_named(state, "Session API")["lead"], "office/cursor")
        self.assertEqual(task_named(state, "Docs")["status"], "open")
        orchestra.finish(state, "home/claude", next_approach="Write the seams in one page.", now=NOW)
        docs = task_named(state, "Docs")
        self.assertEqual(docs["status"], "active")
        self.assertEqual(docs["lead"], "home/claude")
        self.assertEqual(docs["approach"], "Write the seams in one page.")
        self.assertEqual(state["agents"]["office/cursor"]["task"], task_named(state, "Session API")["id"])
        orchestra.finish(state, "office/cursor", next_approach="Keep a decision log.", now=NOW)
        notes = task_named(state, "Notes")
        self.assertEqual(notes["lead"], "office/cursor")
        self.assertEqual(notes["approach"], "Keep a decision log.")
        orchestra.finish(state, "home/claude", now=NOW)
        self.assertEqual(state["agents"]["home/claude"]["task"], notes["id"])
        self.assertIn("office/cursor", notes["members"])
        self.assertIn(notes["approach"], orchestra.render_view(state, "home/claude"))
        self.assertIn("Follow this approach", " ".join(event["text"] for event in state["events"]))

    def test_partition_hides_a_section_from_the_other_players(self) -> None:
        state = orchestra.empty_state()
        players(
            state,
            ("home", "claude", ["ui"]),
            ("office", "cursor", ["api"]),
            ("studio", "hermes", []),
        )
        plan(
            state,
            "home/claude",
            [
                {"title": "Login form", "brief": "Private draft", "skills": ["ui"]},
                {"title": "Session API", "brief": "Public contract", "skills": ["api"]},
            ],
        )
        form = task_named(state, "Login form")
        api = task_named(state, "Session API")
        self.assertEqual(form["lead"], "home/claude")
        self.assertEqual(api["lead"], "office/cursor")
        self.assertIn("studio/hermes", form["members"])
        orchestra.set_partition(state, "home/claude", form["id"], True, NOW)
        orchestra.say(state, "home/claude", "secret chord", form["id"], now=NOW)
        home = orchestra.render_view(state, "home/claude")
        studio = orchestra.render_view(state, "studio/hermes")
        office = orchestra.render_view(state, "office/cursor")
        self.assertIn("secret chord", home)
        self.assertIn("secret chord", studio)
        self.assertNotIn("secret chord", office)
        self.assertIn("secret chord", orchestra.render_view(state, None))
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.say(state, "office/cursor", "I can hear you", form["id"], now=NOW)

    def test_finishing_a_shared_part_moves_you_to_another_part(self) -> None:
        state = orchestra.empty_state()
        players(
            state,
            ("home", "claude", []),
            ("office", "cursor", []),
            ("studio", "hermes", []),
            ("shop", "chatgpt", []),
        )
        plan(
            state,
            "home/claude",
            [
                {"title": "Login form", "brief": "Draw the form", "skills": []},
                {"title": "Session API", "brief": "Own the session", "skills": []},
            ],
        )
        orchestra.finish(state, "home/claude", now=NOW)
        self.assertNotEqual(state["agents"]["home/claude"]["task"], task_named(state, "Login form")["id"])
        self.assertEqual(state["agents"]["home/claude"]["task"], task_named(state, "Session API")["id"])
        self.assertEqual(task_named(state, "Login form")["lead"], "shop/chatgpt")
        self.assertEqual(task_named(state, "Login form")["status"], "active")

    def test_a_dropped_player_can_rejoin_and_a_new_player_can_enter(self) -> None:
        state = orchestra.empty_state()
        early = "2026-10-25T04:00:00Z"
        later = "2026-10-25T04:00:30Z"
        orchestra.join(state, "home", "claude", ["ui"], early)
        orchestra.join(state, "office", "cursor", ["api"], early)
        plan(
            state,
            "home/claude",
            [
                {"title": "Login form", "brief": "Draw the form", "skills": ["ui"]},
                {"title": "Session API", "brief": "Own the session", "skills": ["api"]},
            ],
        )
        state["agents"]["home/claude"]["lastSeen"] = later
        lost = orchestra.sweep(state, later, limit=20)
        self.assertEqual(lost, ["office/cursor"])
        self.assertFalse(state["agents"]["office/cursor"]["connected"])
        self.assertEqual(task_named(state, "Session API")["status"], "open")
        self.assertIn("connection lost", orchestra.render_view(state, "home/claude"))
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.say(state, "office/cursor", "still here", now=later)
        orchestra.join(state, "office", "cursor", ["api"], later)
        self.assertTrue(state["agents"]["office/cursor"]["connected"])
        self.assertEqual(state["agents"]["office/cursor"]["task"], task_named(state, "Session API")["id"])
        orchestra.join(state, "studio", "hermes", ["ui"], later)
        self.assertIsNotNone(state["agents"]["studio/hermes"]["task"])
        self.assertIn("Your part:", orchestra.render_view(state, "studio/hermes"))

    def test_only_the_conductor_publishes_the_plan(self) -> None:
        state = orchestra.empty_state()
        players(state, ("home", "claude", []), ("office", "cursor", []))
        orchestra.conduct(state, "home/claude", NOW)
        orchestra.conduct(state, "home/claude", NOW, successor="office/cursor")
        self.assertEqual(state["conductor"], "office/cursor")
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.conduct(state, "home/claude", NOW, successor="office/cursor")
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.publish_plan(
                state,
                "home/claude",
                {"title": "Nope", "framework": "No", "tasks": [{"title": "Part"}]},
                NOW,
            )


if __name__ == "__main__":
    unittest.main()
