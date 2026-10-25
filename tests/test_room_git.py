#!/usr/bin/env python3
"""Git and MCP tests for the shared room."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import teamlink

CLI = ROOT / "scripts" / "workspace.py"
MCP = ROOT / "scripts" / "mcp_server.py"
HOOK = ROOT / ".cursor" / "hooks" / "room_context.py"
NOW = "2026-10-25T03:00:00Z"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result


class RoomGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_skip = os.environ.get("TEAM_LINK_SKIP_REMOTE_CHECK")
        os.environ["TEAM_LINK_SKIP_REMOTE_CHECK"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.restore_skip)
        root = Path(self.tmp.name)
        self.origin = root / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(self.origin)],
            check=True,
            capture_output=True,
            text=True,
        )
        seed = root / "seed"
        subprocess.run(
            ["git", "init", "-b", "main", str(seed)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.configure(seed)
        git(seed, "remote", "add", "origin", str(self.origin))
        (seed / "README.md").write_text("# Test\n", encoding="utf-8")
        git(seed, "add", "README.md")
        git(seed, "commit", "-m", "seed")
        git(seed, "push", "-u", "origin", "main")

    def restore_skip(self) -> None:
        if self.old_skip is None:
            os.environ.pop("TEAM_LINK_SKIP_REMOTE_CHECK", None)
        else:
            os.environ["TEAM_LINK_SKIP_REMOTE_CHECK"] = self.old_skip

    def configure(self, repo: Path) -> None:
        git(repo, "config", "user.name", "Test User")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "commit.gpgsign", "false")

    def make_clone(self, name: str) -> Path:
        dest = Path(self.tmp.name) / name
        subprocess.run(
            ["git", "clone", str(self.origin), str(dest)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.configure(dest)
        return dest

    def env(self, **extra: str) -> dict[str, str]:
        cloned = os.environ.copy()
        cloned["TEAM_LINK_SKIP_REMOTE_CHECK"] = "1"
        cloned["GIT_TERMINAL_PROMPT"] = "0"
        cloned.update(extra)
        return cloned

    def cli(self, repo: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=repo,
            env=self.env(**extra),
            text=True,
            capture_output=True,
            timeout=60,
        )

    def show(self, branch: str, filename: str) -> dict:
        result = git(self.origin, "show", f"{branch}:{filename}")
        return json.loads(result.stdout)

    def test_dry_run_does_not_claim_a_seat(self) -> None:
        home = self.make_clone("home")
        text = teamlink.claim_seat(home, "Home", dry_run=True, now=NOW)
        self.assertIn("Would claim seat home (1/6)", text)
        self.assertIsNone(teamlink.read_local_seat(home))
        missing = git(self.origin, "rev-parse", "--verify", "roster", check=False)
        self.assertNotEqual(missing.returncode, 0)

    def test_six_computers_and_a_freed_seat(self) -> None:
        names = ["home", "office", "laptop", "studio", "shop", "travel"]
        clones = []
        for name in names:
            clone = self.make_clone(name)
            clones.append(clone)
            teamlink.claim_seat(clone, name, now=NOW)
        spare = self.make_clone("spare")
        with self.assertRaises(teamlink.WorkspaceError) as caught:
            teamlink.claim_seat(spare, "spare", now="2026-10-25T03:05:00Z")
        self.assertIn("All 6 seats", str(caught.exception))
        teamlink.release_seat(clones[0], "home")
        teamlink.claim_seat(spare, "spare", now="2026-10-25T03:06:00Z")
        roster = self.show("roster", "seats.json")
        self.assertEqual(
            [seat["name"] for seat in roster["seats"]],
            ["laptop", "office", "shop", "spare", "studio", "travel"],
        )

    def test_rejoin_preserves_claim_time_on_origin(self) -> None:
        home = self.make_clone("home")
        teamlink.claim_seat(home, "home", now=NOW)
        teamlink.claim_seat(home, "home", now="2026-10-25T04:00:00Z")
        seat = self.show("roster", "seats.json")["seats"][0]
        self.assertEqual(seat["registeredAt"], NOW)
        self.assertEqual(seat["lastSeenAt"], "2026-10-25T04:00:00Z")

    def test_concurrent_joins_keep_both_seats(self) -> None:
        home = self.make_clone("home")
        office = self.make_clone("office")
        state = {"done": False}

        def other_join() -> None:
            if state["done"]:
                return
            state["done"] = True
            teamlink.claim_seat(office, "office", now="2026-10-25T03:01:00Z")

        teamlink.claim_seat(home, "home", now=NOW, before_push=other_join)
        self.assertEqual(
            [seat["name"] for seat in self.show("roster", "seats.json")["seats"]],
            ["home", "office"],
        )

    def test_agents_on_two_computers_talk(self) -> None:
        home = self.make_clone("home")
        office = self.make_clone("office")
        teamlink.claim_seat(home, "home", now=NOW)
        teamlink.claim_seat(office, "office", now=NOW)
        posted = teamlink.post_message(
            home,
            "Editing src/login.py @office",
            agent="claude",
            files=["src/login.py"],
            now="2026-10-25T03:10:00Z",
            suffix="aa11",
        )
        message_id = "20261025T031000Z-home-claude-aa11"
        self.assertIn(message_id, posted)
        teamlink.post_message(
            home,
            "I can review that.",
            agent="chatgpt",
            now="2026-10-25T03:11:00Z",
            suffix="aa12",
        )
        teamlink.post_message(
            office,
            "I will stay in scripts/ @home",
            agent="cursor",
            reply_to=message_id,
            now="2026-10-25T03:12:00Z",
            suffix="bb22",
        )
        room = teamlink.render_room(home)
        self.assertIn("home/claude", room)
        self.assertIn("home/chatgpt", room)
        self.assertIn("office/cursor", room)
        self.assertIn("src/login.py", room)
        self.assertIn(teamlink.ROOM_BANNER, room)
        self.assertFalse((home / "messages.json").exists())
        self.assertFalse((home / "seats.json").exists())
        index = Path(git(home, "rev-parse", "--absolute-git-dir").stdout.strip()) / "team-link.index"
        self.assertFalse(index.exists())
        self.assertEqual(git(home, "status", "--porcelain").stdout, "")

    def test_concurrent_messages_both_land(self) -> None:
        home = self.make_clone("home")
        office = self.make_clone("office")
        teamlink.claim_seat(home, "home", now=NOW)
        teamlink.claim_seat(office, "office", now=NOW)
        state = {"done": False}

        def other_say() -> None:
            if state["done"]:
                return
            state["done"] = True
            teamlink.post_message(
                office,
                "from office",
                agent="hermes",
                now="2026-10-25T03:21:00Z",
                suffix="bbbb",
            )

        teamlink.post_message(
            home,
            "from home",
            agent="claude",
            now="2026-10-25T03:20:00Z",
            suffix="aaaa",
            before_push=other_say,
        )
        raw = git(self.origin, "show", "talk:messages.json").stdout
        self.assertIn("from home", raw)
        self.assertIn("from office", raw)

    def test_say_before_join_is_refused(self) -> None:
        home = self.make_clone("home")
        result = self.cli(home, "say", "--agent", "claude", "--text", "hello")
        self.assertEqual(result.returncode, 1)
        self.assertIn("has not joined", result.stderr)

    def test_cli_join_checks_out_the_seat_branch(self) -> None:
        home = self.make_clone("home")
        result = self.cli(home, "join", "--name", "Home")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(home, "branch", "--show-current").stdout.strip(), "seat/home")
        self.assertIn("Claimed seat home (1/6)", result.stdout)

    def test_dirty_checkout_stays_put(self) -> None:
        home = self.make_clone("home")
        (home / "notes.txt").write_text("local\n", encoding="utf-8")
        result = self.cli(home, "join", "--name", "home")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(home, "branch", "--show-current").stdout.strip(), "main")
        self.assertIn("uncommitted", result.stdout)
        self.assertEqual(self.show("roster", "seats.json")["seats"][0]["name"], "home")

    def test_sync_brings_main_onto_the_seat(self) -> None:
        home = self.make_clone("home")
        other = self.make_clone("other")
        joined = self.cli(home, "join", "--name", "home")
        self.assertEqual(joined.returncode, 0, joined.stderr)
        (other / "README.md").write_text("# Test\n\nmore\n", encoding="utf-8")
        git(other, "commit", "-am", "more")
        git(other, "push", "origin", "main")
        synced = self.cli(home, "sync")
        self.assertEqual(synced.returncode, 0, synced.stderr)
        self.assertIn("more", (home / "README.md").read_text(encoding="utf-8"))

    def test_sync_aborts_a_conflict_and_leaves_a_clean_tree(self) -> None:
        home = self.make_clone("home")
        other = self.make_clone("other")
        self.assertEqual(self.cli(home, "join", "--name", "home").returncode, 0)
        (home / "README.md").write_text("seat\n", encoding="utf-8")
        git(home, "commit", "-am", "seat readme")
        git(home, "push")
        (other / "README.md").write_text("other\n", encoding="utf-8")
        git(other, "commit", "-am", "other readme")
        git(other, "push", "origin", "main")
        synced = self.cli(home, "sync")
        self.assertEqual(synced.returncode, 1)
        self.assertEqual(git(home, "status", "--porcelain").stdout, "")

    def test_unknown_seat_can_not_be_released(self) -> None:
        home = self.make_clone("home")
        teamlink.claim_seat(home, "home", now=NOW)
        with self.assertRaises(teamlink.WorkspaceError):
            teamlink.release_seat(home, "office")

    def test_remote_guard_does_not_print_tokens(self) -> None:
        home = self.make_clone("home")
        git(
            home,
            "remote",
            "set-url",
            "origin",
            "https://x-access-token:supersecret@github.com/other/repo.git",
        )
        env = os.environ.copy()
        env.pop("TEAM_LINK_SKIP_REMOTE_CHECK", None)
        result = subprocess.run(
            [sys.executable, str(CLI), "join", "--name", "home"],
            cwd=home,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        combined = result.stdout + result.stderr
        self.assertNotIn("supersecret", combined)
        self.assertIn("github.com/N8Skully/Team_code_link", result.stderr)

    def test_missing_cursor_cli_does_not_start_a_worker(self) -> None:
        home = self.make_clone("home")
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(teamlink.WorkerMissing):
                teamlink.claim_seat(home, "home", now=NOW, checkout=True, start_worker=True)

    def test_mcp_client_can_join_and_talk(self) -> None:
        studio = self.make_clone("studio")
        proc = subprocess.Popen(
            [sys.executable, str(MCP)],
            cwd=studio,
            env=self.env(TEAM_LINK_AGENT="hermes"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin is not None
        assert proc.stdout is not None
        try:
            def send(payload: dict, framed: bool = False) -> dict:
                raw = json.dumps(payload).encode()
                if framed:
                    proc.stdin.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
                else:
                    proc.stdin.write(raw + b"\n")
                proc.stdin.flush()
                ready, _unused, _errors = select.select([proc.stdout], [], [], 30)
                if not ready:
                    proc.kill()
                    stderr = b""
                    if proc.stderr is not None:
                        stderr = proc.stderr.read()
                    self.fail(f"MCP server timed out. {stderr.decode(errors='replace')}")
                line = proc.stdout.readline()
                if not line:
                    stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
                    self.fail(f"MCP server closed stdout. {stderr}")
                return json.loads(line.decode())

            started = send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
                framed=True,
            )
            self.assertEqual(started["result"]["serverInfo"]["name"], "team-code-link")
            proc.stdin.write(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}
                ).encode()
                + b"\n"
            )
            proc.stdin.flush()
            listed = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            names = {tool["name"] for tool in listed["result"]["tools"]}
            self.assertEqual(names, {"room", "listen", "say", "join", "leave"})
            joined = send(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "join", "arguments": {"name": "studio"}},
                }
            )
            self.assertNotIn("isError", joined["result"])
            self.assertIn("Claimed seat studio", joined["result"]["content"][0]["text"])
            said = send(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "say",
                        "arguments": {
                            "text": "Hermes is here @studio",
                            "agent": "hermes",
                            "files": ["README.md"],
                        },
                    },
                }
            )
            self.assertNotIn("isError", said["result"])
            self.assertIn("studio/hermes", said["result"]["content"][0]["text"])
            room = send(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "room", "arguments": {}},
                }
            )
            text = room["result"]["content"][0]["text"]
            self.assertIn("studio/hermes", text)
            self.assertIn(teamlink.ROOM_BANNER, text)
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_session_hook_adds_the_room(self) -> None:
        home = self.make_clone("home")
        teamlink.claim_seat(home, "home", now=NOW)
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            cwd=home,
            env=self.env(TEAM_LINK_REPO=str(home)),
            input="{}",
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("home", payload["additional_context"])
        self.assertIn(teamlink.ROOM_BANNER, payload["additional_context"])


if __name__ == "__main__":
    unittest.main()
