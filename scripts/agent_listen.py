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


def _bridge(folder: Path) -> Path:
    """Copy the room tools into the project and return the server script."""
    source = _script_dir()
    bridge = folder / ".cursor" / "team-link"
    bridge.mkdir(parents=True, exist_ok=True)
    for name in _BRIDGE:
        origin = source / name
        if not origin.is_file():
            raise OrchestraError("The room tools for the agent are missing from this program.")
        shutil.copyfile(origin, bridge / name)
    return bridge / "mcp_server.py"


def _mcp_entry(script: Path, key: str, folder: Path) -> dict:
    return {
        "command": _python(),
        "args": [str(script)],
        "env": {"TEAM_LINK_AGENT": key, "TEAM_LINK_ROOT": str(folder.resolve())},
    }


def _write_mcp_json(path: Path, script: Path, key: str, folder: Path) -> None:
    data: dict = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            data = {}
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    servers["team-code-link"] = _mcp_entry(script, key, folder)
    data["mcpServers"] = servers
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _toml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _write_codex(folder: Path, script: Path, key: str) -> None:
    """ChatGPT's coding program reads MCP servers from .codex/config.toml."""
    path = folder / ".codex" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    if "[mcp_servers.team-code-link]" in current:
        return
    block = (
        "\n[mcp_servers.team-code-link]\n"
        f"command = {_toml_quote(_python())}\n"
        f"args = [{_toml_quote(str(script))}]\n"
        "enabled = true\n\n"
        "[mcp_servers.team-code-link.env]\n"
        f"TEAM_LINK_AGENT = {_toml_quote(key)}\n"
        f"TEAM_LINK_ROOT = {_toml_quote(str(folder.resolve()))}\n"
    )
    if current and not current.endswith("\n"):
        current += "\n"
    path.write_text(current + block, encoding="utf-8")


def _write_hermes(script: Path, key: str, folder: Path, home: Path | None = None) -> None:
    """Hermes reads mcp_servers from its config.yaml."""
    path = (home or Path.home()) / ".hermes" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    if "team-code-link:" in current:
        return
    block = (
        "  team-code-link:\n"
        f"    command: {_toml_quote(_python())}\n"
        f"    args: [{_toml_quote(str(script))}]\n"
        "    enabled: true\n"
        "    env:\n"
        f"      TEAM_LINK_AGENT: {_toml_quote(key)}\n"
        f"      TEAM_LINK_ROOT: {_toml_quote(str(folder.resolve()))}\n"
    )
    if "mcp_servers:" in current:
        lines = current.splitlines(keepends=True)
        written: list[str] = []
        inserted = False
        for line in lines:
            written.append(line)
            if not inserted and line.startswith("mcp_servers:"):
                written.append(block)
                inserted = True
        path.write_text("".join(written), encoding="utf-8")
        return
    if current and not current.endswith("\n"):
        current += "\n"
    path.write_text(current + "mcp_servers:\n" + block, encoding="utf-8")


def install_mcp(folder: Path, key: str, agent: str = "cursor", home: Path | None = None) -> None:
    """Write the room tools for the agent that is about to start."""
    script = _bridge(folder)
    if agent == "claude":
        _write_mcp_json(folder / ".mcp.json", script, key, folder)
    elif agent == "chatgpt":
        _write_codex(folder, script, key)
    elif agent == "hermes":
        _write_hermes(script, key, folder, home)
    elif agent == "cursor":
        _write_mcp_json(folder / ".cursor" / "mcp.json", script, key, folder)
    else:
        _write_mcp_json(folder / ".cursor" / "mcp.json", script, key, folder)
        _write_mcp_json(folder / ".mcp.json", script, key, folder)


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


def _command(names: list[str], extra: list[Path] | None = None) -> list[str] | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return [found]
    for path in extra or []:
        if path.is_file():
            return [str(path)]
    return None


def _codex_base() -> list[str] | None:
    script = Path(os.environ.get("APPDATA") or "") / "npm" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    node = shutil.which("node")
    if script.is_file() and node:
        return [node, str(script)]
    return _command(["codex", "chatgpt"])


def _hermes_base() -> list[str] | None:
    local = Path(os.environ.get("LOCALAPPDATA") or "") / "hermes" / "bin" / "hermes.exe"
    return _command(["hermes"], [local])


def _claude_base() -> list[str] | None:
    local = Path.home() / ".local" / "bin" / "claude.exe"
    return _command(["claude"], [local])


def _program(agent: str) -> list[str] | None:
    if agent == "cursor":
        return _cursor_base()
    if agent == "claude":
        return _claude_base()
    if agent == "chatgpt":
        return _codex_base()
    if agent == "hermes":
        return _hermes_base()
    return _command([agent])


def known_agents() -> list[dict]:
    """The agents the Agent tab can start, and whether each program is on this computer."""
    return [
        {
            "id": "cursor",
            "title": "Cursor",
            "installed": _cursor_base() is not None,
            "how": "Install Cursor from cursor.com and sign in once. Connect starts Cursor's agent in the project folder.",
        },
        {
            "id": "claude",
            "title": "Claude",
            "installed": _claude_base() is not None,
            "how": "Install Claude Code so the claude command exists. Connect starts that program in the project folder.",
        },
        {
            "id": "chatgpt",
            "title": "ChatGPT",
            "installed": _codex_base() is not None,
            "how": "Install OpenAI's Codex program so the codex command exists. Connect starts it as the ChatGPT agent.",
        },
        {
            "id": "hermes",
            "title": "Hermes",
            "installed": _hermes_base() is not None,
            "how": "Install Hermes so the hermes command exists. Connect starts Hermes in the project folder.",
        },
    ]


def launch_argv(agent: str, base: list[str], folder: Path, prompt: str) -> list[str]:
    """Arguments that start one named agent in the project folder."""
    if agent == "cursor":
        return cursor_launch(base, folder, prompt)
    if agent == "claude":
        return [*base, "-p", "--permission-mode", "bypassPermissions", prompt]
    if agent == "chatgpt":
        return [*base, "exec", "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", prompt]
    if agent == "hermes":
        return [*base, "chat", "--oneshot", "-q", prompt]
    return [*base, prompt]


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
    agent_name = key.split("/", 1)[1] if "/" in key else key
    try:
        install_mcp(folder, key, agent_name)
    except OrchestraError as exc:
        _error = str(exc)
        return status()
    base = _program(agent_name)
    if base is None:
        guide = next((item["how"] for item in known_agents() if item["id"] == agent_name), "")
        if not guide:
            guide = f"Install a program whose command is {agent_name}, then connect again."
        _error = f"The {agent_name} program is not installed on this computer. {guide}"
        return status()
    text = prompt or (
        f"You are {key} in Team Code Link. "
        "The team-code-link tools are configured for this folder. "
        "Call room, then say in the room that you are connected and ready. "
        "Then call listen and answer when the conductor or a teammate speaks. "
        "Work only in this folder."
    )
    command = launch_argv(agent_name, base, folder, text)
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
