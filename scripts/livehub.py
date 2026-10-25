#!/usr/bin/env python3
"""Live room server. One computer runs it; the others open the link."""

from __future__ import annotations

import json
import os
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import orchestra

TOKEN_NAME = "room.token"
STATE_NAME = "room.json"


class Hub:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cond = threading.Condition()
        self.room_token = ""
        self.state = orchestra.empty_state()
        self._closed = False
        self._caller = threading.local()
        self._load()
        self._sweeper = threading.Thread(target=self._sweep_loop, daemon=True)
        self._sweeper.start()

    def close(self) -> None:
        self._closed = True

    def _sweep_loop(self) -> None:
        while not self._closed:
            time.sleep(1)
            with self.cond:
                if self._closed:
                    return
                self._sweep_locked()

    def _heartbeat_locked(self, viewer: str | None) -> None:
        if not viewer:
            return
        player = self.state["agents"].get(viewer)
        if player and player.get("connected", True):
            player["lastSeen"] = orchestra.utc_now()

    def _sweep_locked(self) -> None:
        before = self.state["seq"]
        orchestra.sweep(self.state)
        if self.state["seq"] != before:
            self._save()
            self.cond.notify_all()

    def _load(self) -> None:
        token_path = self.data_dir / TOKEN_NAME
        state_path = self.data_dir / STATE_NAME
        if token_path.exists():
            self.room_token = token_path.read_text(encoding="utf-8").strip()
        if not self.room_token:
            self.room_token = secrets.token_urlsafe(24)
            token_path.write_text(self.room_token + "\n", encoding="utf-8")
        if state_path.exists():
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("version") == 1:
                self.state = loaded

    def _save(self) -> None:
        path = self.data_dir / STATE_NAME
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.state), encoding="utf-8")
        temporary.replace(path)

    def authorized(self, token: str) -> bool:
        if not token or not self.room_token:
            return False
        return secrets.compare_digest(token, self.room_token)

    def player_key(self, agent_token: str) -> str | None:
        if not agent_token:
            return None
        for player in self.state["agents"].values():
            stored = player.get("token") or ""
            if stored and len(stored) == len(agent_token) and secrets.compare_digest(stored, agent_token):
                return player["key"]
        return None

    def update(self, fn):
        with self.cond:
            self._heartbeat_locked(getattr(self._caller, "viewer", None))
            self._sweep_locked()
            result = fn(self.state)
            self._save()
            self.cond.notify_all()
            return result

    def view(self, viewer: str | None) -> dict:
        with self.cond:
            self._heartbeat_locked(viewer)
            self._sweep_locked()
            return {
                "text": orchestra.render_view(self.state, viewer),
                "snapshot": orchestra.public_state(self.state, viewer),
                "seq": self.state["seq"],
            }

    def wait(self, after: int, viewer: str | None, reveal_all: bool, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        with self.cond:
            self._heartbeat_locked(viewer)
            self._sweep_locked()
            while True:
                visible = [
                    event
                    for event in self.state["events"]
                    if event["seq"] > after and orchestra.event_visible(self.state, event, viewer, reveal_all)
                ]
                if visible or time.monotonic() >= deadline:
                    if viewer and viewer in self.state["agents"]:
                        self.state["agents"][viewer]["lastSeen"] = orchestra.utc_now()
                    return {
                        "seq": self.state["seq"],
                        "events": visible,
                        "text": orchestra.render_view(self.state, viewer),
                    }
                remaining = deadline - time.monotonic()
                self.cond.wait(remaining if remaining > 0 else 0.01)


def lan_ip() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def live_link(base: str, token: str) -> str:
    clean = base.rstrip("/")
    return f"{clean}/?token={token}"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt: str, *args) -> None:
        if os.environ.get("TEAM_LINK_DEBUG"):
            super().log_message(fmt, *args)

    @property
    def hub(self) -> Hub:
        return self.server.hub  # type: ignore[attr-defined]

    def _token(self) -> str:
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        query = parse_qs(urlparse(self.path).query)
        values = query.get("token") or []
        return values[0] if values else ""

    def _agent_token(self) -> str:
        return self.headers.get("X-Agent-Token", "").strip()

    def _query(self) -> dict[str, str]:
        parsed = parse_qs(urlparse(self.path).query)
        return {key: values[0] for key, values in parsed.items() if values}

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 1_000_000:
            raise orchestra.OrchestraError("That request is too large.")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise orchestra.OrchestraError("Send JSON.") from exc
        if not isinstance(payload, dict):
            raise orchestra.OrchestraError("Send a JSON object.")
        return payload

    def _send(self, code: int, payload: dict | str, content_type: str = "application/json") -> None:
        if isinstance(payload, str):
            raw = payload.encode("utf-8")
        else:
            raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _guard(self) -> bool:
        if self.hub.authorized(self._token()):
            return True
        self._send(401, {"error": "This live link was refused. Check the token from the conductor."})
        return False

    def _viewer(self) -> str | None:
        return self.hub.player_key(self._agent_token())

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/":
                self._send(200, PAGE, "text/html; charset=utf-8")
                return
            if not self._guard():
                return
            if path == "/v1/score":
                self._send(200, self.hub.view(None))
                return
            if path == "/v1/room":
                viewer = self._viewer()
                if not viewer:
                    raise orchestra.OrchestraError("Join the room before reading it.")
                self._send(200, self.hub.view(viewer))
                return
            if path == "/v1/wait":
                viewer = self._viewer()
                if not viewer:
                    raise orchestra.OrchestraError("Join the room before listening.")
                after = int(self._query().get("after", "0") or "0")
                self._send(200, self.hub.wait(after, viewer, False, 20))
                return
            if path == "/v1/events":
                self._stream()
                return
            self._send(404, {"error": "Not found."})
        except orchestra.OrchestraError as exc:
            self._send(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if not self._guard():
                return
            payload = self._read_json()
            if path == "/v1/join":
                self._send(200, self._join(payload))
                return
            viewer = self._viewer()
            self._caller_set(viewer)
            try:
                if not viewer:
                    raise orchestra.OrchestraError("Join the room before playing.")
                if not self._dispatch(path, viewer, payload):
                    self._send(404, {"error": "Not found."})
                    return
                self._send(200, self.hub.view(viewer))
            finally:
                self._caller_set(None)
            return
        except orchestra.OrchestraError as exc:
            self._send(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            return

    def _caller_set(self, viewer: str | None) -> None:
        self.hub._caller.viewer = viewer

    def _dispatch(self, path: str, viewer: str, payload: dict) -> bool:
        if path == "/v1/leave":
            self.hub.update(lambda state: orchestra.leave(state, viewer))
        elif path == "/v1/conduct":
            self.hub.update(lambda state: orchestra.conduct(state, viewer, successor=payload.get("player") or None))
        elif path == "/v1/plan":
            self.hub.update(lambda state: orchestra.publish_plan(state, viewer, payload))
        elif path == "/v1/say":
            self.hub.update(
                lambda state: orchestra.say(
                    state,
                    viewer,
                    payload.get("text", ""),
                    payload.get("task") or None,
                    payload.get("files") or [],
                )
            )
        elif path == "/v1/finish":
            self.hub.update(
                lambda state: orchestra.finish(
                    state,
                    viewer,
                    payload.get("task") or None,
                    payload.get("approach") or None,
                )
            )
        elif path == "/v1/help":
            self.hub.update(lambda state: orchestra.help_on(state, viewer, payload.get("task", "")))
        elif path == "/v1/partition":
            self.hub.update(
                lambda state: orchestra.set_partition(
                    state, viewer, payload.get("task", ""), bool(payload.get("on", True))
                )
            )
        elif path == "/v1/approach":
            self.hub.update(
                lambda state: orchestra.set_approach(state, viewer, payload.get("task", ""), payload.get("text", ""))
            )
        elif path == "/v1/place":
            self.hub.update(
                lambda state: orchestra.place(state, viewer, payload.get("player", ""), payload.get("task", ""))
            )
        else:
            return False
        return True

    def _join(self, payload: dict) -> dict:
        seat = payload.get("seat") or payload.get("name") or ""
        agent = payload.get("agent") or "agent"

        def apply(state: dict) -> dict:
            player = orchestra.join(state, seat, agent, payload.get("skills") or [])
            if not player.get("token"):
                player["token"] = secrets.token_urlsafe(24)
            return {"token": player["token"], "agent": player["key"]}

        identity = self.hub.update(apply)
        viewed = self.hub.view(identity["agent"])
        viewed.update(identity)
        return viewed

    def _stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        after = int(self._query().get("after", "0") or "0")
        self.wfile.write(b": live\n\n")
        self.wfile.flush()
        while True:
            payload = self.hub.wait(after, None, True, 15)
            after = payload["seq"]
            if payload["events"]:
                data = json.dumps({"seq": after})
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            else:
                self.wfile.write(b": keep\n\n")
            self.wfile.flush()


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Team Code Link</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; background: #f3efe6; color: #1d1a16; font: 18px/1.45 Georgia, "Iowan Old Style", serif; }
  main { max-width: 920px; margin: 0 auto; padding: 36px 20px 96px; }
  h1 { font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; font-size: 22px; margin: 0 0 8px; }
  h2 { font: 13px/1.2 ui-sans-serif, sans-serif; letter-spacing: 0.14em; text-transform: uppercase; color: #6d6458; margin: 28px 0 8px; }
  p { margin: 0 0 10px; }
  .live { font: 13px/1.2 ui-sans-serif, sans-serif; color: #0c6b3c; letter-spacing: 0.08em; text-transform: uppercase; }
  .framework { font-size: 22px; }
  .part { display: grid; grid-template-columns: 92px 1fr; gap: 8px 16px; padding: 14px 0; border-top: 1px solid #ddd4c6; }
  .status { font: 13px/1.3 ui-sans-serif, sans-serif; color: #6d6458; }
  form { display: flex; gap: 8px; margin-top: 16px; }
  input { font: 16px/1.3 ui-sans-serif, sans-serif; padding: 8px 10px; border: 1px solid #c8bfb1; background: #fff; flex: 1; }
  button { font: 15px/1.2 ui-sans-serif, sans-serif; padding: 8px 14px; background: #1d1a16; color: #f3efe6; border: 0; }
  #log p { font: 15px/1.4 ui-sans-serif, sans-serif; margin: 0 0 8px; }
</style>
</head>
<body>
<main>
  <p class="live" id="presence">Live room</p>
  <h1>Team Code Link</h1>
  <div id="gate"></div>
  <div id="score" hidden></div>
</main>
<script>
const gate = document.getElementById("gate");
const score = document.getElementById("score");
const presence = document.getElementById("presence");
const params = new URLSearchParams(location.search);
let token = params.get("token") || sessionStorage.getItem("team-link-token") || "";

function node(tag, text) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  return el;
}

function showGate() {
  score.hidden = true;
  gate.replaceChildren(node("p", "Paste the live link from the computer running the room, or the token printed next to it."));
  const form = document.createElement("form");
  const input = document.createElement("input");
  input.placeholder = "Token or full live link";
  input.autocomplete = "off";
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Connect";
  form.append(input, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const raw = input.value.trim();
    const found = raw.match(/token=([^&]+)/);
    token = found ? decodeURIComponent(found[1]) : raw;
    sessionStorage.setItem("team-link-token", token);
    connect();
  });
  gate.append(form);
}

function render(data) {
  const snap = data.snapshot;
  score.hidden = false;
  gate.replaceChildren();
  score.replaceChildren();
  const plan = snap.plan;
  score.append(node("h2", "Conductor"));
  score.append(node("p", snap.conductor || "The podium is open."));
  score.append(node("p", "Computers " + snap.seatCount + "/" + snap.capacity + " · " + (snap.agents.map((player) => player.key).join(", ") || "no players yet")));
  score.append(node("h2", "Framework"));
  score.append(node("p", plan ? plan.framework : "The conductor has not published a plan yet."));
  if (plan && plan.summary) score.append(node("p", plan.summary));
  score.append(node("h2", "Parts"));
  if (!snap.tasks.length) score.append(node("p", "No parts yet."));
  snap.tasks.forEach((task) => {
    const row = node("div");
    row.className = "part";
    const meta = node("div");
    meta.className = "status";
    meta.textContent = task.status + (task.partitioned ? " · partitioned" : "");
    const body = node("div");
    body.append(node("p", task.title));
    const people = task.lead ? ("Lead " + task.lead + (task.members.length > 1 ? " · with " + task.members.filter((member) => member !== task.lead).join(", ") : "")) : "Waiting for a player";
    body.append(node("p", people));
    if (task.approach && task.status !== "done") body.append(node("p", "Approach: " + task.approach));
    if (task.connects && task.connects.length) body.append(node("p", "Connects to " + task.connects.join(", ")));
    row.append(meta, body);
    score.append(row);
  });
  score.append(node("h2", "Room"));
  const log = node("div");
  log.id = "log";
  const messages = snap.messages || [];
  if (!messages.length) log.append(node("p", "No one has spoken yet."));
  messages.slice(-20).forEach((message) => {
    log.append(node("p", message.agent + ": " + message.text));
  });
  score.append(log);
}

async function refresh() {
  const response = await fetch("/v1/score?token=" + encodeURIComponent(token));
  if (!response.ok) {
    presence.textContent = "Link refused";
    showGate();
    return;
  }
  presence.textContent = "Live";
  render(await response.json());
}

function connect() {
  if (!token) {
    showGate();
    return;
  }
  refresh().catch(() => { presence.textContent = "Reconnecting"; });
  if (window._link) window._link.close();
  const source = new EventSource("/v1/events?token=" + encodeURIComponent(token));
  window._link = source;
  source.onmessage = () => refresh().catch(() => {});
  source.onerror = () => { presence.textContent = "Reconnecting"; };
  clearInterval(window._poll);
  window._poll = setInterval(() => refresh().catch(() => {}), 5000);
}

connect();
</script>
</body>
</html>
"""


def make_server(host: str, port: int, data_dir: Path) -> ThreadingHTTPServer:
    hub = Hub(data_dir)
    server = ThreadingHTTPServer((host, port), Handler)
    server.hub = hub  # type: ignore[attr-defined]
    return server


def describe_links(server: ThreadingHTTPServer, public_url: str | None = None) -> str:
    host, port = server.server_address[:2]
    token = server.hub.room_token  # type: ignore[attr-defined]
    lines = ["Team Code Link is live.", ""]
    local = live_link(f"http://127.0.0.1:{port}", token)
    lines.append(f"This computer: {local}")
    found = lan_ip()
    share = public_url.rstrip("/") if public_url else f"http://{(found if found and found != '127.0.0.1' else '127.0.0.1')}:{port}"
    if share != f"http://127.0.0.1:{port}":
        lines.append("Share this link: " + live_link(share, token))
    lines.append(
        "Other computers open that link. Across the internet, this computer must be reachable "
        f"on port {port}, or pass --public-url with a tunnel address."
    )
    lines.append("")
    lines.append("On each other computer:")
    lines.append(f"  python3 scripts/workspace.py link {live_link(share, token)}")
    return "\n".join(lines)


def serve_forever(host: str, port: int, data_dir: Path, public_url: str | None = None) -> None:
    server = make_server(host, port, data_dir)
    print(describe_links(server, public_url), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nThe live room stopped.", flush=True)
    finally:
        server.hub.close()  # type: ignore[attr-defined]
        server.server_close()
