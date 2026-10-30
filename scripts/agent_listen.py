#!/usr/bin/env python3
"""Hear the conductor's instructions and answer on this computer."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import liveclient
import share
from orchestra import OrchestraError

_process: subprocess.Popen[str] | None = None
_key = ""
_error = ""
_log_handle = None

_BRIDGE = ("mcp_server.py", "liveclient.py", "orchestra.py")


def _hidden() -> int:
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def status() -> dict:
    """Whether the named agent program is running, not merely listed on the board."""
    running = _process is not None and _process.poll() is None
    return {"key": _key, "running": running, "error": _error}


def bind_folder(folder: Path) -> Path:
    """The app and the agent read the room link from this folder."""
    folder.mkdir(parents=True, exist_ok=True)
    resolved = folder.resolve()
    os.environ["TEAM_LINK_ROOT"] = str(resolved)
    ignore = folder / ".gitignore"
    line = ".team-link-client.json"
    current = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if line not in current.splitlines():
        with ignore.open("a", encoding="utf-8") as handle:
            if current and not current.endswith("\n"):
                handle.write("\n")
            handle.write(line + "\n")
    return resolved


def _script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "scripts"
    return Path(__file__).resolve().parent


def _python() -> str:
    if not getattr(sys, "frozen", False):
        return sys.executable
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    root = Path(os.environ.get("LOCALAPPDATA") or "") / "Programs" / "Python"
    if root.is_dir():
        copies = sorted(root.glob("Python*/python3.exe")) or sorted(root.glob("Python*/python.exe"))
        if copies:
            return str(copies[-1])
    raise OrchestraError("Python is required on this computer so the agent can open the room.")


def install_mcp(folder: Path, key: str) -> None:
    """Write the room tools into the project the agent will open."""
    source = _script_dir()
    bridge = folder / ".cursor" / "team-link"
    bridge.mkdir(parents=True, exist_ok=True)
    for name in _BRIDGE:
        origin = source / name
        if not origin.is_file():
            raise OrchestraError("The room tools for the agent are missing from this program.")
        shutil.copyfile(origin, bridge / name)
    mcp_path = folder / ".cursor" / "mcp.json"
    data: dict = {}
    if mcp_path.is_file():
        try:
            loaded = json.loads(mcp_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    servers["team-code-link"] = {
        "command": _python(),
        "args": [str(bridge / "mcp_server.py")],
        "env": {
            "TEAM_LINK_AGENT": key,
            "TEAM_LINK_ROOT": str(folder.resolve()),
        },
    }
    data["mcpServers"] = servers
    mcp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cursor_launch(base: list[str], folder: Path, prompt: str) -> list[str]:
    """Arguments that start the Cursor agent against one project folder."""
    return [
        *base,
        "-p",
        "--approve-mcps",
        "--trust",
        "--force",
        "--sandbox",
        "disabled",
        "--workspace",
        str(folder),
        prompt,
    ]


def _cursor_base() -> list[str] | None:
    root = Path(os.environ.get("LOCALAPPDATA") or "") / "cursor-agent" / "versions"
    versions = []
    if root.is_dir():
        versions = [
            path
            for path in root.iterdir()
            if path.is_dir() and (path / "node.exe").is_file() and (path / "index.js").is_file()
        ]
    if versions:
        latest = sorted(versions, key=lambda path: path.name)[-1]
        return [str(latest / "node.exe"), str(latest / "index.js")]
    found = shutil.which("agent")
    if found:
        return [found]
    return None


def _program(agent: str) -> list[str] | None:
    if agent == "cursor":
        return _cursor_base()
    found = shutil.which(agent)
    if found:
        return [found]
    return None


def connect_agent(key: str, folder: Path, prompt: str | None = None) -> dict:
    """Start the named agent in the project, using the same room link as this app."""
    global _process, _key, _error, _log_handle
    if _process is not None and _process.poll() is None:
        if _key == key:
            _error = ""
            return status()
        _process.terminate()
    _key = key
    folder = bind_folder(folder)
    os.environ["TEAM_LINK_AGENT"] = key
    try:
        install_mcp(folder, key)
    except OrchestraError as exc:
        _error = str(exc)
        return status()
    agent_name = key.split("/", 1)[1] if "/" in key else key
    base = _program(agent_name)
    if base is None:
        _error = f"The {agent_name} program is not installed on this computer."
        return status()
    text = prompt or (
        f"You are {key} in Team Code Link. "
        "The team-code-link tools are configured for this folder. "
        "Call room, then say in the room that you are connected and ready. "
        "Then call listen and answer when the conductor or a teammate speaks. "
        "Work only in this folder."
    )
    command = cursor_launch(base, folder, text) if agent_name == "cursor" else [*base, text]
    log_path = share.app_dir() / "agent-session.log"
    _log_handle = log_path.open("a", encoding="utf-8")
    _process = subprocess.Popen(
        command,
        cwd=str(folder),
        stdin=subprocess.DEVNULL,
        stdout=_log_handle,
        stderr=subprocess.STDOUT,
        creationflags=_hidden(),
        env={**os.environ, "TEAM_LINK_AGENT": key, "TEAM_LINK_ROOT": str(folder)},
    )
    time.sleep(1.5)
    if _process.poll() is not None:
        _error = _recent_log(log_path) or f"The {agent_name} program stopped before it joined the room."
    else:
        _error = ""
    return status()


def _recent_log(path: Path) -> str:
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    useful = [line.strip() for line in lines if line.strip()]
    return useful[-1] if useful else ""


def start_turn(you: str, task: dict, folder: Path) -> None:
    title = task.get("title") or "your part"
    text = task.get("approach") or task.get("brief") or ""
    liveclient._request(
        None,
        "POST",
        "/v1/say",
        {"task": task.get("id"), "text": f"Starting {title}. {text}"},
    )
    if not folder.is_dir():
        return
    if _process is not None and _process.poll() is None:
        return
    connect_agent(
        you,
        folder,
        (
            f"You are {you} in Team Code Link. "
            f"Your part is {title}. "
            f"Build it this way: {text} "
            "Work in this folder. When you change a file, say so in the Team Code Link room."
        ),
    )


def loop() -> None:
    heard: set[str] = set()
    while True:
        try:
            room = liveclient._request(None, "GET", "/v1/room")
        except OrchestraError:
            time.sleep(3)
            continue
        snap = room.get("snapshot") or {}
        you = snap.get("you")
        if not you:
            time.sleep(3)
            continue
        folder = share.working_folder(str(snap.get("project") or ""))
        for task in snap.get("tasks") or []:
            if task.get("status") != "active" or you not in (task.get("members") or []):
                continue
            text = task.get("approach") or ""
            mark = f"{task.get('id')}:{text}"
            if not text or mark in heard:
                continue
            mine = False
            for event in reversed(room.get("events") or []):
                if event.get("type") == "approach" and event.get("task") == task.get("id"):
                    mine = event.get("agent") == you
                    break
            heard.add(mark)
            if mine:
                continue
            try:
                start_turn(you, task, folder)
            except OrchestraError:
                pass
        time.sleep(3)
