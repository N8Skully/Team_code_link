#!/usr/bin/env python3
"""Finished work returns to main, and teammates edit one branch."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import codework
import livehub
from orchestra import OrchestraError

CLI = Path(__file__).resolve().parents[1] / "scripts" / "workspace.py"


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


def configure(repo: Path) -> None:
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "commit.gpgsign", "false")


class ReuniteTests(unittest.TestCase):
    def test_a_conflicted_part_does_not_get_stitched_onto_main(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        origin = Path(tmp.name) / "origin.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
        clone = Path(tmp.name) / "clone"
        subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True)
        configure(clone)
        (clone / "README.md").write_text("seed\n", encoding="utf-8")
        git(clone, "add", "README.md")
        git(clone, "commit", "-m", "seed")
        git(clone, "push", "-u", "origin", "main")
        git(clone, "checkout", "-b", "part/t1")
        (clone / "README.md").write_text("form\n", encoding="utf-8")
        git(clone, "commit", "-am", "form")
        git(clone, "push", "-u", "origin", "part/t1")
        git(clone, "checkout", "main")
        git(clone, "checkout", "-b", "part/t2")
        (clone / "README.md").write_text("api\n", encoding="utf-8")
        git(clone, "commit", "-am", "api")
        git(clone, "push", "-u", "origin", "part/t2")

        self.assertIn("returned to main", codework.reunite(clone, "t1"))
        self.assertEqual((clone / "README.md").read_text(encoding="utf-8"), "form\n")
        with self.assertRaises(OrchestraError) as caught:
            codework.reunite(clone, "t2")
        self.assertIn("does not fit", str(caught.exception))
        self.assertNotIn("<<<<<<<", (clone / "README.md").read_text(encoding="utf-8"))
        self.assertEqual(git(clone, "branch", "--show-current").stdout.strip(), "part/t2")
        main_readme = subprocess.run(
            ["git", "-C", str(origin), "show", "main:README.md"],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(main_readme.stdout, "form\n")


class SameCodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.origin = root / "origin.git"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(self.origin)], check=True, capture_output=True)
        seed = root / "seed"
        subprocess.run(["git", "init", "-b", "main", str(seed)], check=True, capture_output=True)
        configure(seed)
        git(seed, "remote", "add", "origin", str(self.origin))
        (seed / "README.md").write_text("seed\n", encoding="utf-8")
        git(seed, "add", "README.md")
        git(seed, "commit", "-m", "seed")
        git(seed, "push", "-u", "origin", "main")
        self.home = root / "home"
        self.office = root / "office"
        for dest in (self.home, self.office):
            subprocess.run(["git", "clone", str(self.origin), str(dest)], check=True, capture_output=True)
            configure(dest)
        self.server = livehub.make_server("127.0.0.1", 0, root / "hub")
        self.addCleanup(self.server.hub.close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        port = self.server.server_address[1]
        self.link = f"http://127.0.0.1:{port}/?token={self.server.hub.room_token}"

    def run_cli(self, repo: Path, *args: str, agent: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if agent:
            env["TEAM_LINK_AGENT"] = agent
        env["GIT_TERMINAL_PROMPT"] = "0"
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
        )

    def commit_file(self, repo: Path, relative: str, text: str, message: str) -> None:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(repo, "add", relative)
        git(repo, "commit", "-m", message)

    def test_a_finished_player_joins_the_same_branch_and_the_piece_returns_whole(self) -> None:
        self.assertEqual(self.run_cli(self.home, "link", self.link).returncode, 0)
        self.assertEqual(self.run_cli(self.office, "link", self.link).returncode, 0)
        self.assertEqual(self.run_cli(self.home, "join", "--name", "home", "--agent", "claude", "--skill", "ui").returncode, 0)
        self.assertEqual(self.run_cli(self.office, "join", "--name", "office", "--agent", "cursor", "--skill", "api").returncode, 0)
        self.assertEqual(self.run_cli(self.home, "conduct").returncode, 0)
        plan = Path(self.tmp.name) / "plan.json"
        plan.write_text(
            json.dumps(
                {
                    "title": "Ship login",
                    "summary": "One piece.",
                    "framework": "The form calls the session API. The API is the only writer of session state.",
                    "tasks": [
                        {"title": "Login form", "brief": "Draw the form", "skills": ["ui"], "connects": ["Session API"]},
                        {"title": "Session API", "brief": "Own the session", "skills": ["api"], "connects": ["Login form"]},
                    ],
                }
            ),
            encoding="utf-8",
        )
        planned = self.run_cli(self.home, "plan", "--file", str(plan))
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(git(self.home, "branch", "--show-current").stdout.strip(), "part/t1")
        self.commit_file(self.home, "src/form.py", "form\n", "form")

        synced = self.run_cli(self.office, "sync")
        self.assertEqual(synced.returncode, 0, synced.stderr)
        self.assertEqual(git(self.office, "branch", "--show-current").stdout.strip(), "part/t2")
        self.commit_file(self.office, "src/api.py", "session = {}\n", "api")
        pushed = self.run_cli(self.office, "sync")
        self.assertEqual(pushed.returncode, 0, pushed.stderr)

        finished = self.run_cli(self.home, "finish")
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertIn("part/t1 returned to main", finished.stdout)
        self.assertEqual(git(self.home, "branch", "--show-current").stdout.strip(), "part/t2")
        self.assertEqual((self.home / "src/api.py").read_text(encoding="utf-8"), "session = {}\n")
        self.assertFalse((self.home / "src/form.py").exists())

        self.commit_file(self.home, "src/api.py", "session = {}\nready = True\n", "home joins the api")
        self.assertEqual(self.run_cli(self.home, "sync").returncode, 0)
        office_sync = self.run_cli(self.office, "sync")
        self.assertEqual(office_sync.returncode, 0, office_sync.stderr)
        self.assertEqual((self.office / "src/api.py").read_text(encoding="utf-8"), "session = {}\nready = True\n")

        self.assertEqual(self.run_cli(self.home, "finish").returncode, 0)
        office_done = self.run_cli(self.office, "finish")
        self.assertEqual(office_done.returncode, 0, office_done.stderr)
        self.assertIn("part/t2 returned to main", office_done.stdout)
        self.assertEqual(
            subprocess.check_output(["git", "-C", str(self.origin), "show", "main:src/form.py"], text=True),
            "form\n",
        )
        self.assertEqual(
            subprocess.check_output(["git", "-C", str(self.origin), "show", "main:src/api.py"], text=True),
            "session = {}\nready = True\n",
        )
        self.assertNotIn("<<<<<<<", subprocess.check_output(["git", "-C", str(self.origin), "show", "main:src/api.py"], text=True))

    def test_a_quiet_player_keeps_the_part(self) -> None:
        self.server.hub.close()
        self.server.shutdown()
        self.server.server_close()
        self.server = livehub.make_server("127.0.0.1", 0, Path(self.tmp.name) / "hub-drop")
        self.addCleanup(self.server.hub.close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        port = self.server.server_address[1]
        link = f"http://127.0.0.1:{port}/?token={self.server.hub.room_token}"
        studio = Path(self.tmp.name) / "studio"
        subprocess.run(["git", "clone", str(self.origin), str(studio)], check=True, capture_output=True)
        configure(studio)

        self.assertEqual(self.run_cli(self.home, "link", link).returncode, 0)
        self.assertEqual(self.run_cli(self.office, "link", link).returncode, 0)
        self.assertEqual(self.run_cli(studio, "link", link).returncode, 0)
        self.assertEqual(self.run_cli(self.home, "join", "--name", "home", "--agent", "claude", "--skill", "ui").returncode, 0)
        self.assertEqual(self.run_cli(self.office, "join", "--name", "office", "--agent", "cursor", "--skill", "api").returncode, 0)
        plan = Path(self.tmp.name) / "plan-drop.json"
        plan.write_text(
            json.dumps(
                {
                    "title": "Ship login",
                    "summary": "One piece.",
                    "framework": "The form calls the session API.",
                    "tasks": [
                        {"title": "Login form", "brief": "Draw the form", "skills": ["ui"], "connects": ["Session API"]},
                        {"title": "Session API", "brief": "Own the session", "skills": ["api"], "connects": ["Login form"]},
                    ],
                }
            ),
            encoding="utf-8",
        )
        planned = self.run_cli(self.home, "conduct")
        self.assertEqual(planned.returncode, 0, planned.stderr)
        planned = self.run_cli(self.home, "plan", "--file", str(plan))
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.commit_file(self.home, "src/form.py", "half-done\n", "form in progress")
        self.assertEqual(self.run_cli(self.home, "sync").returncode, 0)
        office_sync = self.run_cli(self.office, "sync")
        self.assertEqual(office_sync.returncode, 0, office_sync.stderr)
        self.commit_file(self.office, "src/api.py", "session = {}\n", "api in progress")
        self.assertEqual(self.run_cli(self.office, "sync").returncode, 0)

        import time
        time.sleep(4)
        room = self.run_cli(self.office, "room")
        self.assertEqual(room.returncode, 0, room.stderr)
        self.assertNotIn("connection lost", room.stdout)
        self.assertIn("t1 Login form [active] home/claude", room.stdout)
        self.assertIn("Your part: t2 Session API", room.stdout)


if __name__ == "__main__":
    unittest.main()
