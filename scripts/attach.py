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

import agent_listen
import liveclient
import share
import source_loop
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
        if path == "/desk":
            self._send(200, desk())
            return
        if path in ("/", ""):
            body = _page_bytes()
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
        if path == "/start":
            payload = self._read_body()
            try:
                self._send(200, start_here(payload, str(payload.get("host") or "") in {"1", "true"}))
            except (OrchestraError, OSError) as exc:
                self._send(400, {"error": str(exc)})
            return
        if path == "/save":
            self._send(200, {"settings": share.save_settings(self._read_body())})
            return
        if path == "/instruct":
            payload = self._read_body()
            try:
                self._send(200, send_instructions(str(payload.get("task") or ""), str(payload.get("text") or "")))
            except OrchestraError as exc:
                self._send(400, {"error": str(exc)})
            return
        if path == "/talk":
            payload = self._read_body()
            try:
                self._send(200, agent_listen.talk_plan(str(payload.get("text") or "")))
            except OrchestraError as exc:
                self._send(400, {"error": str(exc)})
            return
        if path == "/plan-go":
            try:
                self._send(200, agent_listen.plan_is_a_go())
            except OrchestraError as exc:
                self._send(400, {"error": str(exc)})
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

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 100_000:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}


def start_here(payload: dict, hosting: bool) -> dict:
    """Save this computer's login, then join. Hosting starts the room and shows a short code."""
    seat = str(payload.get("seat") or "").strip()
    agent = str(payload.get("agent") or "cursor").strip()
    project = str(payload.get("project") or "Shared").strip()
    place = str(payload.get("place") or "tailscale").strip()
    folder = str(payload.get("folder") or "").strip()
    github = str(payload.get("github") or "").strip()
    code = _room_code(str(payload.get("link") or payload.get("code") or ""))
    share.save_settings(
        {
            "role": "host" if hosting else "join",
            "seat": seat,
            "agent": agent,
            "project": project,
            "place": place,
            "folder": folder,
            "github": github,
            "link": code,
        }
    )
    if not seat:
        seat = suggested_seat()
    chosen_folder = Path(folder) if folder else share.working_folder(project)
    agent_listen.bind_folder(chosen_folder)
    share.save_settings({"folder": str(chosen_folder)})
    root = liveclient.repo_root()
    if place == "github" and github:
        dest = chosen_folder
        dest.mkdir(parents=True, exist_ok=True)
        if not (dest / ".git").exists():
            share._run([share._git(), "clone", github, str(dest)])
    if hosting:
        if begin_host is None:
            raise OrchestraError("This window cannot host the room.")
        code = begin_host()
        set_invite(code)
    elif code:
        base = share.find_room(code)
        liveclient.link_room(f"{base}/?token={code}", root=root)
    skills = _chosen_skills(root, payload.get("skills"))
    share.save_settings({"skills": skills, "link": code})
    try:
        link = liveclient.load_link(root)
    except OrchestraError:
        link = {}
    key = f"{seat}/{agent}"
    saved = liveclient.players(link).get(key) if link else None
    token = (saved or {}).get("token") or ""
    if token and link.get("url") and link.get("room_token"):
        raw = str(link["url"]).rstrip("/") + "/?token=" + str(link["room_token"])
        liveclient.attach_agent(raw, seat, agent, token, skills, root)
    else:
        liveclient.join(seat, agent, skills, root)
    if hosting:
        try:
            liveclient._request(root, "POST", "/v1/conduct", {})
        except OrchestraError as exc:
            if "Only the conductor" in str(exc):
                raise
        liveclient._request(root, "POST", "/v1/project", {"name": project})
        liveclient._request(root, "POST", "/v1/source", {"seat": seat})
    launched = agent_listen.connect_agent(f"{seat}/{agent}", chosen_folder)
    source = ""
    share_error = ""
    if hosting:
        try:
            source = source_loop.publish_now(project, root)
        except OrchestraError as exc:
            share_error = str(exc)
            source_loop.note_share_error(share_error)
    return {
        "ok": True,
        "code": code,
        "agent": launched.get("key") or f"{seat}/{agent}",
        "agentRunning": bool(launched.get("running")),
        "agentError": launched.get("error") or "",
        "source": source,
        "shareError": share_error,
    }


def _chosen_skills(root: Path, picked) -> list[str]:
    found = discover_skills(root)
    if isinstance(picked, list) and picked:
        names = [str(item).strip().lower() for item in picked if str(item).strip()]
        return [name for name in names if name in found] or found
    saved = share.load_settings().get("skills")
    if isinstance(saved, list) and saved:
        return [name for name in found if name in saved] or found
    return found


def send_instructions(task: str, text: str) -> dict:
    liveclient._request(None, "POST", "/v1/approach", {"task": task, "text": text})
    liveclient._request(None, "POST", "/v1/say", {"task": task, "text": text})
    return {"ok": True}


def _room_code(raw: str) -> str:
    text = raw.strip()
    if "token=" in text:
        from urllib.parse import parse_qs, urlparse

        found = parse_qs(urlparse(text).query).get("token", [""])[0]
        if found:
            return found
    return text


begin_host = None


invite_url = ""


def set_invite(url: str) -> None:
    global invite_url
    invite_url = url


def desk() -> dict:
    """Tailscale plus the live room, for the window on this computer."""
    status = share.tailscale_status()
    try:
        payload = liveclient._request(None, "GET", "/v1/room")
    except OrchestraError:
        try:
            payload = liveclient._request(None, "GET", "/v1/score", agent=False)
        except OrchestraError as exc:
            return _desk(status, None, [], str(exc))
    return _desk(status, payload.get("snapshot"), (payload.get("events") or [])[-15:], "")


def _desk(status: dict, snapshot, events: list, error: str) -> dict:
    return {
        "tailscale": status,
        "snapshot": snapshot,
        "events": events,
        "seat": suggested_seat(),
        "invite": invite_url,
        "settings": share.load_settings(),
        "skills": discover_skills(liveclient.repo_root()),
        "board": _board_url(),
        "agent": agent_listen.status(),
        "agents": agent_listen.known_agents(),
        "shareError": source_loop.share_error,
        "error": error,
    }


def _board_url() -> str:
    try:
        link = liveclient.load_link()
    except OrchestraError:
        return ""
    return str(link.get("url") or "")


def suggested_seat() -> str:
    import socket

    raw = os.environ.get("COMPUTERNAME") or socket.gethostname() or "computer"
    cleaned = "".join(ch for ch in raw.lower() if ch.isalnum() or ch == "-").strip("-")
    if cleaned in {"", "unknown"}:
        cleaned = "computer"
    return cleaned


def _page_bytes() -> bytes:
    path = Path(__file__).resolve().parents[1] / "web" / "app.html"
    if getattr(sys, "frozen", False):
        path = Path(getattr(sys, "_MEIPASS")) / "web" / "app.html"
    if path.is_file():
        return path.read_bytes()
    return b"Team Code Link window is missing."


def url_path(raw: str) -> str:
    return raw.split("?", 1)[0]


def pid_path() -> Path:
    return Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp") / PID_NAME


def serve() -> int:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), AttachHandler)
    except OSError:
        if not os.environ.get("TEAM_LINK_APP"):
            print("The agent connection is already waiting on this computer.")
        return 0
    path = pid_path()
    path.write_text(str(os.getpid()), encoding="ascii")
    if not os.environ.get("TEAM_LINK_APP"):
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
  main { width: min(560px, calc(100% - 32px)); padding: 28px; border: 1px solid rgba(186, 140, 255, 0.55); border-radius: 16px; background: rgba(16, 12, 24, 0.9); }
  h1 { margin: 0 0 8px; font-size: 22px; }
  p { color: #b7a9c9; }
  button, a.room { display: inline-block; margin-top: 8px; margin-right: 8px; padding: 10px 14px; border-radius: 10px; border: 0; background: #c084fc; color: #1a1024; font: inherit; font-weight: 600; cursor: pointer; text-decoration: none; }
  [hidden] { display: none !important; }
  label { display: block; margin-top: 8px; color: #b7a9c9; font-size: 13px; }
  input { display: block; width: 100%; margin-top: 4px; padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(186, 140, 255, 0.55); background: #120e18; color: #f6f1ff; font: inherit; }
  #setup-error { color: #ffb4b4; }
  .list p { margin: 0 0 6px; color: #f6f1ff; }
  .ok { color: #b6f3c8; font-size: 20px; font-weight: 650; }
  .wait { color: #f6f1ff; }
</style>
</head>
<body>
<main>
  <h1>Team Code Link</h1>
  <p id="state" class="wait">Checking…</p>
  <p id="detail"></p>
  <button id="signin" type="button" hidden>Sign in with Tailscale</button>
  <button id="board" type="button" hidden>Board</button>
  <label id="invite-label" hidden>Room code
    <input id="invite" readonly>
  </label>
  <h2>Settings</h2>
  <form id="setup">
    <label>This computer
      <select id="role">
        <option value="host">Host the room</option>
        <option value="join">Join a room</option>
      </select>
    </label>
    <label id="join-label" hidden>Room code
      <input id="join-link" placeholder="Room code" autocomplete="off">
    </label>
    <label>Computer<input id="seat" autocomplete="off"></label>
    <label>Agent<input id="agent" value="cursor" autocomplete="off"></label>
    <label id="project-label">Project<input id="project" value="Shared" autocomplete="off"></label>
    <label>Project lives
      <select id="place">
        <option value="tailscale">On this computer, shared with Tailscale</option>
        <option value="github">In a GitHub repo, copied to a folder here</option>
      </select>
    </label>
    <label id="github-label" hidden>GitHub repo
      <input id="github" placeholder="https://github.com/you/project" autocomplete="off">
    </label>
    <label>Folder on this computer
      <input id="folder" placeholder="Choose where the project files go" autocomplete="off">
    </label>
    <button id="browse" type="button">Choose folder</button>
    <button id="go" type="submit">Share this computer</button>
    <p id="setup-error"></p>
  </form>
  <p id="source"></p>
  <h2>Agents</h2>
  <div id="agents" class="list"></div>
  <h2>Talking</h2>
  <div id="talk" class="list"></div>
</main>
<script>
const state = document.getElementById("state");
const detail = document.getElementById("detail");
const button = document.getElementById("signin");
const board = document.getElementById("board");
const roomUrl = new URLSearchParams(location.search).get("room");
if (roomUrl) board.hidden = false;
board.addEventListener("click", () => { if (roomUrl) location.href = roomUrl; });
const source = document.getElementById("source");
const agents = document.getElementById("agents");
const talk = document.getElementById("talk");
const setup = document.getElementById("setup");
const role = document.getElementById("role");
const place = document.getElementById("place");
let filled = false;

function applyRole() {
  const joining = role.value === "join";
  document.getElementById("join-label").hidden = !joining;
  document.getElementById("project-label").hidden = joining;
  document.getElementById("go").textContent = joining ? "Join" : "Share this computer";
  document.getElementById("github-label").hidden = place.value !== "github";
}
role.addEventListener("change", applyRole);
place.addEventListener("change", applyRole);
if (new URLSearchParams(location.search).get("host") === "1") role.value = "host";
applyRole();

document.getElementById("browse").addEventListener("click", async () => {
  if (!window.pywebview) return;
  const picked = await window.pywebview.api.pick_folder();
  if (picked) document.getElementById("folder").value = picked;
});

function line(text) {
  const row = document.createElement("p");
  row.textContent = text;
  return row;
}

function showTailscale(data) {
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
    ? "Sign in. This window stays here and shows the agents."
    : "Install Tailscale, then come back and sign in.";
  button.hidden = false;
  button.textContent = data.installed ? "Sign in with Tailscale" : "Get Tailscale";
}

function showRoom(snapshot) {
  agents.replaceChildren();
  talk.replaceChildren();
  if (!snapshot) {
    agents.append(line("This computer is not in a room yet."));
    return;
  }
  const share = snapshot.source || {};
  source.textContent = share.path
    ? "Shared folder " + share.path
    : (snapshot.project ? "Project " + snapshot.project + ". The source folder is not shared yet." : "No shared folder yet.");
  const locks = {};
  (snapshot.locks || []).forEach((lock) => { locks[lock.holder] = lock.file; });
  const people = snapshot.agents || [];
  if (!people.length) agents.append(line("No agents yet. Log in on the board."));
  people.forEach((player) => {
    const task = (snapshot.tasks || []).find((item) => (item.members || []).includes(player.key) && item.status === "active");
    const editing = locks[player.key] ? " · editing " + locks[player.key] : "";
    const part = task ? " · " + task.title : "";
    agents.append(line(player.key + part + editing));
  });
  const messages = (snapshot.messages || []).slice(-12);
  if (!messages.length) talk.append(line("No one has spoken yet."));
  messages.forEach((message) => {
    talk.append(line(message.agent + ": " + message.text));
  });
}

async function refresh() {
  const response = await fetch("/desk");
  const data = await response.json();
  showTailscale(data.tailscale || {});
  const seat = document.getElementById("seat");
  if (seat && !seat.value && data.seat) seat.value = data.seat;
  if (!filled && data.settings) {
    filled = true;
    const saved = data.settings;
    if (saved.role) role.value = saved.role;
    if (saved.seat) document.getElementById("seat").value = saved.seat;
    if (saved.agent) document.getElementById("agent").value = saved.agent;
    if (saved.project) document.getElementById("project").value = saved.project;
    if (saved.place) place.value = saved.place;
    if (saved.folder) document.getElementById("folder").value = saved.folder;
    if (saved.github) document.getElementById("github").value = saved.github;
    if (saved.link) document.getElementById("join-link").value = saved.link;
    applyRole();
  }
  const invite = document.getElementById("invite");
  const inviteLabel = document.getElementById("invite-label");
  if (data.invite) {
    invite.value = data.invite;
    inviteLabel.hidden = false;
  }
  if (data.board) {
    board.hidden = false;
    board.onclick = () => { location.href = data.board; };
  }
  showRoom(data.snapshot);
}

button.addEventListener("click", async () => {
  button.disabled = true;
  try {
    await fetch("/tailscale/login", { method: "POST" });
  } finally {
    button.disabled = false;
    refresh().catch(() => {});
  }
});

setup.addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = document.getElementById("setup-error");
  error.textContent = "";
  const response = await fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      host: role.value === "host" ? "1" : "",
      seat: document.getElementById("seat").value.trim(),
      agent: document.getElementById("agent").value.trim() || "cursor",
      project: document.getElementById("project").value.trim() || "Shared",
      place: place.value,
      folder: document.getElementById("folder").value.trim(),
      github: document.getElementById("github").value.trim(),
      link: document.getElementById("join-link").value.trim()
    })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) error.textContent = data.error || "Could not connect this computer.";
  refresh().catch(() => {});
});

refresh().catch(() => { state.textContent = "The app is not reachable."; });
setInterval(() => refresh().catch(() => {}), 2000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(serve())
