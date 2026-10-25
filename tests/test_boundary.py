#!/usr/bin/env python3
"""One agent cannot enter another computer or its database."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import boundary
import livehub
from orchestra import OrchestraError

HOOK = Path(__file__).resolve().parents[1] / ".cursor" / "hooks" / "boundary.py"


def request(method: str, url: str, body: dict | None = None, room: str = "", agent: str = "") -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if room:
        headers["Authorization"] = f"Bearer {room}"
    if agent:
        headers["X-Agent-Token"] = agent
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return exc.code, payload


class ShellBoundaryTests(unittest.TestCase):
    def test_remote_database_and_login_are_blocked(self) -> None:
        self.assertEqual(boundary.review_shell("psql -h 10.0.0.8 -U app")[0], "deny")
        self.assertEqual(boundary.review_shell("mysql --host=db.internal -u root")[0], "deny")
        self.assertEqual(boundary.review_shell("redis-cli -h 192.168.1.9")[0], "deny")
        self.assertEqual(boundary.review_shell("PGHOST=10.1.1.1 psql")[0], "deny")
        self.assertEqual(boundary.review_shell("ssh office@10.0.0.2")[0], "deny")
        self.assertEqual(boundary.review_shell("scp notes.txt office:/tmp/notes.txt")[0], "deny")
        self.assertEqual(boundary.review_shell("rsync -a ./ office:/srv/app")[0], "deny")

    def test_local_work_stays_allowed(self) -> None:
        self.assertEqual(boundary.review_shell("psql -h localhost -d app")[0], "allow")
        self.assertEqual(boundary.review_shell("git push origin part/t1")[0], "allow")
        self.assertEqual(boundary.review_shell("python3 scripts/workspace.py room")[0], "allow")

    def test_private_key_files_stay_on_the_machine(self) -> None:
        self.assertEqual(boundary.review_read("/home/office/.ssh/id_rsa")[0], "deny")
        self.assertEqual(boundary.review_read("/home/office/.pgpass")[0], "deny")
        self.assertEqual(boundary.review_read("/workspace/src/form.py")[0], "allow")

    def test_hook_denies_a_remote_database_command(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"command": "psql -h 10.0.0.8 -U app", "cwd": "/workspace", "sandbox": False}),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["permission"], "deny")


class RoomBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = livehub.make_server("127.0.0.1", 0, Path(self.tmp.name))
        self.addCleanup(self.server.hub.close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{port}"
        self.room = self.server.hub.room_token

    def test_another_computer_cannot_take_an_agent(self) -> None:
        status, joined = request("POST", self.base + "/v1/join", {"seat": "home", "agent": "claude", "skills": ["ui"]}, self.room)
        self.assertEqual(status, 200, joined)
        home_token = joined["token"]
        status, stolen = request("POST", self.base + "/v1/join", {"seat": "home", "agent": "claude", "skills": ["ui"]}, self.room)
        self.assertEqual(status, 400, stolen)
        self.assertIn("own computer", stolen["error"])
        self.assertNotIn("token", stolen)
        status, score = request("GET", self.base + "/v1/score?token=" + self.room)
        self.assertEqual(status, 200)
        self.assertNotIn(home_token, json.dumps(score))
        status, back = request(
            "POST",
            self.base + "/v1/join",
            {"seat": "home", "agent": "claude", "skills": ["ui"]},
            self.room,
            home_token,
        )
        self.assertEqual(status, 200, back)
        self.assertEqual(back["token"], home_token)

    def test_database_details_never_enter_the_room(self) -> None:
        status, joined = request("POST", self.base + "/v1/join", {"seat": "office", "agent": "cursor"}, self.room)
        self.assertEqual(status, 200, joined)
        status, said = request(
            "POST",
            self.base + "/v1/say",
            {"text": "use postgres://app:secret@10.0.0.8/prod"},
            self.room,
            joined["token"],
        )
        self.assertEqual(status, 400, said)
        self.assertIn("database", said["error"])
        status, room = request("GET", self.base + "/v1/room", room=self.room, agent=joined["token"])
        self.assertNotIn("postgres://", json.dumps(room))
        status, ok = request(
            "POST",
            self.base + "/v1/say",
            {"text": "The form calls the session API."},
            self.room,
            joined["token"],
        )
        self.assertEqual(status, 200, ok)

    def test_there_is_no_way_to_run_a_command_on_another_computer(self) -> None:
        for path in ("/v1/exec", "/v1/files", "/v1/database", "/v1/ssh"):
            status, payload = request("POST", self.base + path, {"command": "id"}, self.room)
            self.assertGreaterEqual(status, 400)
            status, payload = request("GET", self.base + path + "?token=" + self.room)
            self.assertGreaterEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
