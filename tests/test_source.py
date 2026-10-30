#!/usr/bin/env python3
"""The conductor names the project and one switchable source computer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import orchestra
import share


NOW = "2026-10-25T04:00:00Z"


def room() -> dict:
    state = orchestra.empty_state()
    orchestra.join(state, "nate", "cursor", ["ui"], NOW)
    orchestra.join(state, "office", "cursor", ["ui"], NOW)
    orchestra.conduct(state, "nate/cursor", NOW)
    return state


class SourceTests(unittest.TestCase):
    def test_the_conductor_names_the_project_and_source(self) -> None:
        state = room()
        orchestra.set_project(state, "nate/cursor", "ToolsProject", NOW)
        orchestra.choose_source(state, "nate/cursor", "nate", NOW)
        self.assertEqual(state["project"], "ToolsProject")
        self.assertEqual(state["source"]["seat"], "nate")
        self.assertEqual(state["source"]["path"], "")
        view = orchestra.render_view(state, "office/cursor")
        self.assertIn("Project: ToolsProject", view)
        self.assertIn("Source: nate", view)

    def test_another_player_cannot_name_the_project(self) -> None:
        state = room()
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.set_project(state, "office/cursor", "ToolsProject", NOW)

    def test_handoff_waits_for_a_commit_then_the_new_path(self) -> None:
        state = room()
        orchestra.set_project(state, "nate/cursor", "ToolsProject", NOW)
        orchestra.choose_source(state, "nate/cursor", "nate", NOW)
        orchestra.publish_source(state, "nate/cursor", r"\\NATE-PC\ToolsProject", NOW)
        orchestra.choose_source(state, "nate/cursor", "office", NOW)
        self.assertEqual(state["handoff"], "office")
        self.assertFalse(state["source"]["ready"])
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.publish_source(state, "office/cursor", r"\\OFFICE-PC\ToolsProject", NOW)
        orchestra.mark_source_ready(state, "nate/cursor", NOW)
        orchestra.publish_source(state, "office/cursor", r"\\OFFICE-PC\ToolsProject", NOW)
        self.assertEqual(state["source"]["seat"], "office")
        self.assertEqual(state["source"]["path"], r"\\OFFICE-PC\ToolsProject")
        self.assertEqual(state["handoff"], "")
        self.assertIn("Source: office", orchestra.render_view(state, "nate/cursor"))

    def test_one_agent_holds_a_file(self) -> None:
        state = room()
        orchestra.claim_file(state, "nate/cursor", "src/app.py", NOW)
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.claim_file(state, "office/cursor", r"src\app.py", NOW)
        orchestra.claim_file(state, "nate/cursor", "src/app.py", NOW)
        self.assertIn("Editing: nate/cursor src/app.py", orchestra.render_view(state, "office/cursor"))
        orchestra.release_file(state, "nate/cursor", "src/app.py", NOW)
        self.assertEqual(state["locks"], {})

    def test_leaving_releases_the_file(self) -> None:
        state = room()
        orchestra.claim_file(state, "office/cursor", "src/app.py", NOW)
        orchestra.leave(state, "office/cursor", NOW)
        self.assertEqual(state["locks"], {})

    def test_a_bad_share_path_is_refused(self) -> None:
        state = room()
        orchestra.set_project(state, "nate/cursor", "ToolsProject", NOW)
        orchestra.choose_source(state, "nate/cursor", "nate", NOW)
        with self.assertRaises(orchestra.OrchestraError):
            orchestra.publish_source(state, "nate/cursor", r"C:\ToolsProject", NOW)

    def test_the_share_action_follows_the_handoff(self) -> None:
        source = {"seat": "nate", "path": r"\\NATE-PC\ToolsProject", "ready": False}
        self.assertEqual(share.next_action("nate", "ToolsProject", source, "office", ""), "commit")
        source["ready"] = True
        self.assertEqual(share.next_action("office", "ToolsProject", source, "office", ""), "copy")
        self.assertEqual(share.next_action("nate", "ToolsProject", {"seat": "office", "path": r"\\OFFICE-PC\ToolsProject", "ready": False}, "", "ToolsProject"), "unshare")
        self.assertEqual(share.next_action("nate", "ToolsProject", {"seat": "nate", "path": "", "ready": False}, "", ""), "publish")

    def test_tailscale_status_reads_the_address(self) -> None:
        connected = share.read_tailscale(True, 0, "100.64.1.2\n", "NATE-PC")
        self.assertTrue(connected["connected"])
        self.assertEqual(connected["ip"], "100.64.1.2")
        waiting = share.read_tailscale(True, 1, "", "NATE-PC")
        self.assertFalse(waiting["connected"])
        self.assertEqual(waiting["loginUrl"], "https://login.tailscale.com/")
        missing = share.read_tailscale(False, 1, "", "NATE-PC")
        self.assertIn("download", missing["loginUrl"])

    def test_an_unknown_computer_name_uses_the_tailscale_address(self) -> None:
        self.assertEqual(share.share_host("UNKNOWN", "100.1.2.3"), "100.1.2.3")
        self.assertEqual(share.share_host("office", "100.1.2.3"), "office")

    def test_the_room_link_follows_the_project_folder(self) -> None:
        import os
        import tempfile

        import liveclient

        with tempfile.TemporaryDirectory() as raw:
            previous = os.environ.get("TEAM_LINK_ROOT")
            os.environ["TEAM_LINK_ROOT"] = raw
            try:
                self.assertEqual(liveclient.repo_root(), Path(raw).resolve())
            finally:
                if previous is None:
                    os.environ.pop("TEAM_LINK_ROOT", None)
                else:
                    os.environ["TEAM_LINK_ROOT"] = previous

    def test_the_cursor_agent_starts_in_the_project_folder(self) -> None:
        import agent_listen

        command = agent_listen.cursor_launch(["node", "index.js"], Path("C:/work/Shared"), "hello")
        self.assertIn("--workspace", command)
        self.assertIn("--approve-mcps", command)
        self.assertEqual(command[command.index("--workspace") + 1], "C:\\work\\Shared")
        self.assertEqual(command[-1], "hello")

    def test_each_named_agent_has_its_own_start_command(self) -> None:
        import agent_listen

        claude = agent_listen.launch_argv("claude", ["claude"], Path("C:/work/Shared"), "hello")
        self.assertEqual(claude[:3], ["claude", "-p", "--permission-mode"])
        chatgpt = agent_listen.launch_argv("chatgpt", ["node", "codex.js"], Path("C:/work/Shared"), "hello")
        self.assertIn("exec", chatgpt)
        self.assertEqual(chatgpt[-1], "hello")
        hermes = agent_listen.launch_argv("hermes", ["hermes"], Path("C:/work/Shared"), "hello")
        self.assertEqual(hermes[:4], ["hermes", "chat", "--oneshot", "-q"])
        names = [item["id"] for item in agent_listen.known_agents()]
        self.assertEqual(names, ["cursor", "claude", "chatgpt", "hermes"])


if __name__ == "__main__":
    unittest.main()
