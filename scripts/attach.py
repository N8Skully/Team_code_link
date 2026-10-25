#!/usr/bin/env python3
"""Let the room page connect the agent on this computer.

Listens only on 127.0.0.1. launch.bat starts it on the host. Other computers
run connect.bat, then log in on the share link.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import liveclient
from orchestra import OrchestraError
from skills import discover_skills

PORT = 8770
PID_NAME = "team-code-link-attach.pid"


class AttachHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _cors(self) -> None:
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if url_path(self.path) != "/attach":
            self._send(404, {"error": "Not found."})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 100_000:
            self._send(400, {"error": "That request is too large."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "Send JSON."})
            return
        if not isinstance(payload, dict):
            self._send(400, {"error": "Send a JSON object."})
            return
        url = str(payload.get("url") or "").strip()
        seat = str(payload.get("seat") or "").strip()
        agent = str(payload.get("agent") or "").strip()
        agent_token = str(payload.get("agentToken") or "").strip()
        if not url or not seat or not agent or not agent_token:
            self._send(400, {"error": "Log in on the page first."})
            return
        root = liveclient.repo_root()
        typed = payload.get("skills") if isinstance(payload.get("skills"), list) else []
        skills = discover_skills(root)
        for item in typed:
            name = str(item).strip().lower()
            if name and name not in skills:
                skills.append(name)
        try:
            saved = liveclient.attach_agent(url, seat, agent, agent_token, skills, root)
        except OrchestraError as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(200, {"agent": saved.get("agent"), "skills": skills})


def url_path(raw: str) -> str:
    return raw.split("?", 1)[0]


def pid_path() -> Path:
    return Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp") / PID_NAME


def serve() -> int:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), AttachHandler)
    except OSError:
        print("The agent connection is already waiting on this computer.")
        print("Open the share link and log in.")
        return 0
    path = pid_path()
    path.write_text(str(os.getpid()), encoding="ascii")
    print("This computer can connect its agent.")
    print("Open the share link and log in. Leave this window open.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nThe agent connection stopped.")
    finally:
        server.server_close()
        if path.exists():
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
