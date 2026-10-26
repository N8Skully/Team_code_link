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
import share
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

    def do_GET(self) -> None:  # noqa: N802
        path = url_path(self.path)
        if path == "/tailscale":
            self._send(200, share.tailscale_status())
            return
        if path in ("/", ""):
            body = LOGIN_PAGE.encode("utf-8")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        path = url_path(self.path)
        if path == "/tailscale/login":
            self._send(200, {"url": share.tailscale_login()})
            return
        if path == "/lock":
            self._proxy_lock("/v1/lock")
            return
        if path == "/unlock":
            self._proxy_lock("/v1/unlock")
            return
        if path != "/attach":
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

    def _proxy_lock(self, route: str) -> None:
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
        try:
            text = liveclient.post(route, {"path": str(payload.get("path") or "")})
        except OrchestraError as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(200, {"text": text})


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


LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Team Code Link</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #07060c; color: #f6f1ff; font: 16px/1.45 "Segoe UI", sans-serif; }
  main { width: min(420px, calc(100% - 32px)); padding: 28px; border: 1px solid rgba(186, 140, 255, 0.55); border-radius: 16px; background: rgba(16, 12, 24, 0.9); }
  h1 { margin: 0 0 8px; font-size: 22px; }
  p { color: #b7a9c9; }
  button, a.room { display: inline-block; margin-top: 8px; padding: 10px 14px; border-radius: 10px; border: 0; background: #c084fc; color: #1a1024; font: inherit; font-weight: 600; cursor: pointer; text-decoration: none; }
  .ok { color: #b6f3c8; font-size: 20px; font-weight: 650; }
  .wait { color: #f6f1ff; }
</style>
</head>
<body>
<main>
  <h1>Team Code Link</h1>
  <p id="detail">Checking Tailscale on this computer.</p>
  <p id="state" class="wait">Checking…</p>
  <button id="signin" type="button" hidden>Sign in with Tailscale</button>
  <a id="room" class="room" hidden>Open the room</a>
</main>
<script>
const state = document.getElementById("state");
const detail = document.getElementById("detail");
const button = document.getElementById("signin");
const room = document.getElementById("room");
const roomUrl = new URLSearchParams(location.search).get("room");
if (roomUrl) { room.href = roomUrl; room.hidden = false; }

function show(data) {
  if (data.connected) {
    state.className = "ok";
    state.textContent = "Connected";
    detail.textContent = data.host ? data.host + " · " + data.ip : data.ip;
    button.hidden = true;
    return;
  }
  state.className = "wait";
  state.textContent = data.installed ? "Not connected" : "Tailscale is not installed";
  detail.textContent = data.installed
    ? "Sign in, then this screen shows Connected."
    : "Install Tailscale, then come back and sign in.";
  button.hidden = false;
  button.textContent = data.installed ? "Sign in with Tailscale" : "Get Tailscale";
}

async function refresh() {
  const response = await fetch("/tailscale");
  show(await response.json());
}

button.addEventListener("click", async () => {
  button.disabled = true;
  try {
    const response = await fetch("/tailscale/login", { method: "POST" });
    const data = await response.json();
    if (data.url) window.open(data.url, "_blank");
  } finally {
    button.disabled = false;
    refresh().catch(() => {});
  }
});

refresh().catch(() => { state.textContent = "The app is not reachable."; });
setInterval(() => refresh().catch(() => {}), 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(serve())
