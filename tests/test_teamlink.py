#!/usr/bin/env python3
"""Unit tests for roster and room rules."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import teamlink


def sample_message(number: int, reply_to: str | None = None) -> dict:
    return {
        "id": teamlink.make_message_id(
            "2026-10-25T03:00:00Z", "home", "claude", f"{number:04x}"
        ),
        "from": "home",
        "agent": "claude",
        "at": "2026-10-25T03:00:00Z",
        "text": f"message {number}",
        "replyTo": reply_to,
        "mentions": [],
        "files": [],
    }


class RosterTests(unittest.TestCase):
    def test_name_and_agent_normalization(self) -> None:
        self.assertEqual(teamlink.normalize_name(" Home "), "home")
        self.assertEqual(teamlink.normalize_agent("ChatGPT"), "chatgpt")
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.normalize_name("my computer")
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.normalize_agent("Claude Opus")

    def test_capacity_is_six(self) -> None:
        roster = teamlink.empty_roster()
        moment = "2026-10-25T03:00:00Z"
        for name in ("home", "office", "laptop", "studio", "shop", "travel"):
            roster, _action, _message = teamlink.apply_join(roster, name, moment)
        with self.assertRaises(teamlink.WorkspaceError) as caught:
            teamlink.apply_join(roster, "spare", moment)
        self.assertIn("All 6 seats", str(caught.exception))
        self.assertIn("home", str(caught.exception))

    def test_rejoin_keeps_the_original_claim_time(self) -> None:
        roster, _action, _message = teamlink.apply_join(
            teamlink.empty_roster(), "home", "2026-10-25T03:00:00Z"
        )
        roster, action, _message = teamlink.apply_join(
            roster, "home", "2026-10-25T04:00:00Z"
        )
        self.assertEqual(action, "rejoined")
        self.assertEqual(roster["seats"][0]["registeredAt"], "2026-10-25T03:00:00Z")
        self.assertEqual(roster["seats"][0]["lastSeenAt"], "2026-10-25T04:00:00Z")

    def test_bad_capacity_is_rejected(self) -> None:
        roster = teamlink.empty_roster()
        roster["capacity"] = 7
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.parse_roster(json.dumps(roster))

    def test_scrub_keeps_the_repo_and_drops_the_token(self) -> None:
        raw = "https://x-access-token:supersecret@github.com/N8Skully/Team_code_link"
        cleaned = teamlink.scrub(raw)
        self.assertNotIn("supersecret", cleaned)
        self.assertIn("N8Skully/Team_code_link", cleaned)

    def test_clock_display_uses_eastern_time(self) -> None:
        self.assertEqual(
            teamlink.format_et("2026-10-25T03:00:00Z"),
            "Oct 24, 2026, 11:00 PM ET",
        )


class TalkTests(unittest.TestCase):
    def test_mentions_ignore_email_addresses(self) -> None:
        self.assertEqual(
            teamlink.extract_mentions("Ask @Office. Mail user@home.com"),
            ["office"],
        )

    def test_paths_stay_inside_the_repo(self) -> None:
        self.assertEqual(teamlink.normalize_files(["src/app.py"]), ["src/app.py"])
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.normalize_files(["../secrets"])
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.normalize_files(["/etc/passwd"])

    def test_history_keeps_the_newest_hundred_messages(self) -> None:
        doc = teamlink.empty_talk()
        for number in range(teamlink.MESSAGE_KEEP):
            doc = teamlink.deliver_message(doc, sample_message(number))
        extra = sample_message(teamlink.MESSAGE_KEEP)
        doc = teamlink.deliver_message(doc, extra)
        self.assertEqual(len(doc["messages"]), teamlink.MESSAGE_KEEP)
        self.assertEqual(doc["messages"][-1]["id"], extra["id"])
        self.assertNotEqual(doc["messages"][0]["id"], sample_message(0)["id"])

    def test_reply_must_point_at_a_message_still_in_the_room(self) -> None:
        missing = sample_message(2, reply_to=sample_message(9)["id"])
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.deliver_message(teamlink.empty_talk(), missing)

    def test_room_text_marks_messages_as_conversation(self) -> None:
        roster, _action, _message = teamlink.apply_join(
            teamlink.empty_roster(), "home", "2026-10-25T03:00:00Z"
        )
        talk = teamlink.deliver_message(teamlink.empty_talk(), sample_message(1))
        text = teamlink.format_room(
            roster,
            talk,
            local_seat="home",
            max_messages=20,
            offline=False,
        )
        self.assertIn(teamlink.ROOM_BANNER, text)
        self.assertIn("home/claude", text)
        self.assertIn("Claimed seats: 1/6", text)

    def test_worker_command_names_the_computer(self) -> None:
        command = teamlink.worker_argv("home", Path("/work/repo"), None, False)
        self.assertEqual(
            command,
            ["agent", "worker", "start", "--name", "home", "--worker-dir", "/work/repo"],
        )


if __name__ == "__main__":
    unittest.main()
