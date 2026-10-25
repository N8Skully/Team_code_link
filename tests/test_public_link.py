#!/usr/bin/env python3
"""The share link is what other networks open."""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import livehub


class PublicLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = livehub.make_server("127.0.0.1", 0, Path(self.tmp.name) / "hub")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def test_a_public_link_is_what_other_networks_open(self) -> None:
        token = self.server.hub.room_token
        text = livehub.describe_links(self.server, "https://room.example")
        self.assertIn(f"Share this link: https://room.example/?token={token}", text)
        self.assertIn("any network", text)
        local = livehub.describe_links(self.server, None)
        self.assertIn("this network", local)
        self.assertNotIn("https://room.example", local)


if __name__ == "__main__":
    unittest.main()
