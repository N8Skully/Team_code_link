#!/usr/bin/env python3
"""The room is a live link, not a git poll."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import liveclient
import livehub


class LiveRoomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = livehub.make_server("127.0.0.1", 0, Path(self.tmp.name) / "hub")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        port = self.server.server_address[1]
        token = self.server.hub.room_token
        self.url = f"http://127.0.0.1:{port}/?token={token}"
        self.home = Path(self.tmp.name) / "home"
        self.office = Path(self.tmp.name) / "office"
        self.home.mkdir()
        self.office.mkdir()
        liveclient.link_room(self.url, root=self.home)
        liveclient.link_room(self.url, root=self.office)

    def test_a_message_arrives_while_the_other_agent_is_listening(self) -> None:
        liveclient.join("home", "claude", ["ui"], self.home)
        liveclient.join("office", "cursor", ["api"], self.office)
        current = liveclient._request(self.office, "GET", "/v1/room")
        after = current["seq"]
        found: dict = {}

        def listen() -> None:
            started = time.monotonic()
            found["payload"] = liveclient.wait(after, self.office)
            found["elapsed"] = time.monotonic() - started

        waiter = threading.Thread(target=listen)
        waiter.start()
        time.sleep(0.2)
        liveclient.post("/v1/say", {"text": "downbeat"}, self.home)
        waiter.join(3)
        self.assertFalse(waiter.is_alive())
        self.assertLess(found["elapsed"], 2)
        heard = " ".join(event.get("text", "") for event in found["payload"]["events"])
        self.assertIn("downbeat", heard)

    def test_the_live_page_shows_the_framework(self) -> None:
        liveclient.join("home", "claude", ["ui"], self.home)
        liveclient.post("/v1/conduct", {}, self.home)
        liveclient.post(
            "/v1/plan",
            {
                "title": "Opening",
                "summary": "One piece.",
                "framework": "The form calls the session API and nothing else writes the session.",
                "tasks": [
                    {"title": "Login form", "brief": "Draw it", "skills": ["ui"], "connects": ["Session API"]},
                ],
            },
            self.home,
        )
        port = self.server.server_address[1]
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode()
        self.assertIn("Team Code Link", page)
        score = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/score?token={self.server.hub.room_token}",
            timeout=5,
        ).read().decode()
        body = json.loads(score)
        self.assertIn("session API", body["snapshot"]["plan"]["framework"])
        self.assertEqual(body["snapshot"]["tasks"][0]["lead"], "home/claude")

    def test_two_agents_on_one_computer_keep_their_own_voices(self) -> None:
        liveclient.join("home", "claude", ["ui"], self.home)
        liveclient.join("home", "chatgpt", ["docs"], self.home)
        saved = json.loads((self.home / ".team-link-client.json").read_text(encoding="utf-8"))
        self.assertIn("home/claude", saved["players"])
        self.assertIn("home/chatgpt", saved["players"])
        os.environ["TEAM_LINK_AGENT"] = "claude"
        try:
            text = liveclient.post("/v1/say", {"text": "from claude"}, self.home)
        finally:
            os.environ.pop("TEAM_LINK_AGENT", None)
        self.assertIn("home/claude", text)
        self.assertIn("from claude", text)

    def test_mcp_player_can_join_the_live_room(self) -> None:
        import subprocess

        script = Path(__file__).resolve().parents[1] / "scripts" / "mcp_server.py"
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            cwd=self.home,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout

        def send(payload: dict) -> dict:
            proc.stdin.write(json.dumps(payload).encode() + b"\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            self.assertTrue(line, "MCP server closed")
            return json.loads(line.decode())

        try:
            started = send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                }
            )
            self.assertEqual(started["result"]["serverInfo"]["name"], "team-code-link")
            proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            proc.stdin.flush()
            joined = send(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "join",
                        "arguments": {"name": "home", "agent": "hermes", "skills": ["ui"]},
                    },
                }
            )
            self.assertNotIn("isError", joined["result"])
            self.assertIn("home/hermes", joined["result"]["content"][0]["text"])
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)
            proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
