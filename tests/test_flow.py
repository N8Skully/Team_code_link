#!/usr/bin/env python3
"""Regression tests: plans finish, dropped parts wait, seats cannot be taken with the share link alone."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import livehub
import orchestra


def room(players: int, parts: int) -> dict:
    state = orchestra.empty_state()
    for i in range(players):
        orchestra.join(state, f"c{i}", "claude")
    orchestra.conduct(state, "c0/claude")
    orchestra.publish_plan(
        state,
        "c0/claude",
        {"title": "T", "framework": "F", "tasks": [{"title": f"P{i}"} for i in range(parts)]},
    )
    return state


def all_done(state: dict) -> bool:
    return all(task["status"] == "done" for task in state["tasks"])


class PlanCompletes(unittest.TestCase):
    def test_every_size_finishes_in_member_order(self) -> None:
        for players in range(1, 7):
            for parts in range(1, 7):
                state = room(players, parts)
                for _ in range(200):
                    working = [k for k, v in state["agents"].items() if v["task"]]
                    if not working:
                        break
                    orchestra.finish(state, working[0])
                self.assertTrue(all_done(state), f"{players} players / {parts} parts did not finish")

    def test_finished_player_is_not_pulled_back_by_a_teammate(self) -> None:
        state = room(3, 1)
        orchestra.finish(state, "c0/claude")
        orchestra.finish(state, "c1/claude")
        self.assertIsNone(state["agents"]["c0/claude"]["task"])
        orchestra.finish(state, "c2/claude")
        self.assertTrue(all_done(state))


class DroppedPart(unittest.TestCase):
    def test_sole_player_leaving_makes_the_part_wait(self) -> None:
        state = room(2, 3)
        orchestra.leave(state, "c1/claude")
        dropped = [t for t in state["tasks"] if t["status"] == "waiting"]
        self.assertEqual(len(dropped), 1)
        self.assertFalse(any(t["status"] == "done" for t in state["tasks"]))

    def test_next_finisher_resumes_the_waiting_part(self) -> None:
        state = room(2, 2)
        orchestra.leave(state, "c1/claude")
        orchestra.finish(state, "c0/claude")
        self.assertEqual(state["agents"]["c0/claude"]["task"], "t2")
        self.assertEqual(state["tasks"][1]["status"], "active")

    def test_new_player_resumes_waiting_part(self) -> None:
        state = room(2, 2)
        orchestra.leave(state, "c1/claude")
        orchestra.join(state, "c9", "claude")
        self.assertEqual(state["agents"]["c9/claude"]["task"], "t2")

    def test_plan_cannot_replace_a_waiting_part(self) -> None:
        state = room(2, 2)
        orchestra.leave(state, "c1/claude")
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.publish_plan(state, "c0/claude", {"title": "N", "framework": "F", "tasks": [{"title": "X"}]})

    def test_conductor_can_complete_a_part(self) -> None:
        state = room(3, 1)
        orchestra.complete(state, "c0/claude", "t1")
        self.assertTrue(all_done(state))
        self.assertTrue(all(v["task"] is None for v in state["agents"].values()))

    def test_only_lead_or_conductor_completes(self) -> None:
        state = room(3, 1)
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.complete(state, "c2/claude", "t1")


class SeatSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = livehub.make_server("127.0.0.1", 0, Path(self.tmp.name) / "hub")
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.hub = self.server.hub

    def call(self, path: str, body: dict, agent: str = "", host: str = ""):
        headers = {"Authorization": f"Bearer {self.hub.room_token}", "Content-Type": "application/json"}
        if agent:
            headers["X-Agent-Token"] = agent
        if host:
            headers["X-Host-Token"] = host
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_share_link_alone_cannot_remove_or_retake_a_seat(self) -> None:
        _s, alice = self.call("/v1/join", {"seat": "alice", "agent": "claude"})
        self.call("/v1/conduct", {}, agent=alice["token"])
        status, _ = self.call("/v1/remove", {"player": "alice/claude"})
        self.assertEqual(status, 400)
        status, again = self.call("/v1/join", {"seat": "alice", "agent": "claude"})
        self.assertEqual(status, 400)
        self.assertNotIn("token", again)

    def test_another_player_cannot_remove_but_conductor_and_host_can(self) -> None:
        _s, alice = self.call("/v1/join", {"seat": "alice", "agent": "claude"})
        _s, bob = self.call("/v1/join", {"seat": "bob", "agent": "cursor"})
        _s, cara = self.call("/v1/join", {"seat": "cara", "agent": "claude"})
        self.call("/v1/conduct", {}, agent=alice["token"])
        self.assertEqual(self.call("/v1/remove", {"player": "alice/claude"}, agent=bob["token"])[0], 400)
        self.assertEqual(self.call("/v1/remove", {"player": "bob/cursor"}, agent=alice["token"])[0], 200)
        self.assertEqual(self.call("/v1/remove", {"player": "cara/claude"}, host=self.hub.host_token)[0], 200)


if __name__ == "__main__":
    unittest.main()
