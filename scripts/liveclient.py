#!/usr/bin/env python3
"""Client for the live Team Code Link room."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from orchestra import OrchestraError

CONFIG_NAME = "team-link-client.json"


def repo_root(start: Path | None = None) -> Path:
    probe = (start or Path.cwd()).resolve()
    result = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return probe


def config_path(root: Path | None = None) -> Path:
    root = root or repo_root()
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", CONFIG_NAME],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        path = Path(result.stdout.strip())
        if not path.is_absolute():
            path = root / path
        return path
    return root / f".{CONFIG_NAME}"


def load_link(root: Path | None = None) -> dict:
    path = config_path(root)
    if not path.exists():
        raise OrchestraError(
            "This computer is not linked to the live room. "
            "On the conductor's computer run python3 scripts/workspace.py serve, "
            "then on this computer run python3 scripts/workspace.py link <the live link>."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("url") or not data.get("room_token"):
        raise OrchestraError("The live link on this computer is incomplete. Link it again.")
    return data


def save_link(data: dict, root: Path | None = None) -> None:
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def parse_link(raw: str, token: str | None = None) -> tuple[str, str]:
    text = raw.strip()
    if "://" not in text:
        text = "http://" + text
    parsed = urlparse(text)
    if not parsed.hostname or not parsed.port and parsed.scheme not in {"http", "https"}:
        raise OrchestraError("Use the live link printed by the room, such as http://host:8765/?token=...")
    found = parse_qs(parsed.query).get("token", [None])[0]
    room_token = token or found
    if not room_token:
        raise OrchestraError("The live link needs its token. Paste the whole link from the conductor.")
    base = urlunparse((parsed.scheme or "http", parsed.netloc, "", "", "", ""))
    return base, room_token


def players(link: dict) -> dict:
    stored = link.get("players")
    if isinstance(stored, dict):
        return stored
    legacy = link.get("agent_token")
    key = link.get("player")
    if legacy and key:
        return {key: {"token": legacy, "key": key, "agent": link.get("agent"), "seat": link.get("seat")}}
    return {}


def select_player(link: dict) -> dict | None:
    roster = players(link)
    if not roster:
        return None
    wanted = (os.environ.get("TEAM_LINK_AGENT") or "").strip().lower()
    if wanted:
        if wanted in roster:
            return roster[wanted]
        matches = [
            player
            for player in roster.values()
            if player.get("agent") == wanted or player.get("key") == wanted
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(sorted(player["key"] for player in matches))
            raise OrchestraError(f"More than one player matches {wanted}: {names}.")
        known = ", ".join(sorted(roster))
        raise OrchestraError(f"This computer has no player named {wanted}. Joined: {known}.")
    active = link.get("active") or link.get("player")
    if active in roster:
        return roster[active]
    return next(iter(roster.values()))


def link_room(raw: str, token: str | None = None, root: Path | None = None) -> str:
    base, room_token = parse_link(raw, token)
    current = {}
    path = config_path(root)
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except json.JSONDecodeError:
            current = {}
    current["url"] = base
    current["room_token"] = room_token
    current.pop("agent_token", None)
    save_link(current, root)
    return f"Linked to {base}"


def _request(root: Path | None, method: str, path: str, body: dict | None = None, timeout: float = 30, agent: bool = True, token: str | None = None) -> dict:
    link = load_link(root)
    url = link["url"].rstrip("/") + path
    headers = {"Authorization": f"Bearer {link['room_token']}", "Accept": "application/json"}
    if token:
        headers["X-Agent-Token"] = token
    elif agent:
        player = select_player(link)
        if player and player.get("token"):
            headers["X-Agent-Token"] = player["token"]
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(detail).get("error") or detail
        except json.JSONDecodeError:
            message = detail or exc.reason
        raise OrchestraError(str(message)) from exc
    except urllib.error.URLError as exc:
        raise OrchestraError(
            "The live room is not reachable. The conductor runs python3 scripts/workspace.py serve, "
            "and this computer needs the link from that window."
        ) from exc
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise OrchestraError("The live room sent an unexpected response.")
    return parsed


def join(seat: str, agent: str | None, skills: list[str], root: Path | None = None) -> dict:
    chosen = agent or os.environ.get("TEAM_LINK_AGENT") or "agent"
    payload = _request(
        root,
        "POST",
        "/v1/join",
        {"seat": seat, "agent": chosen, "skills": skills},
        agent=False,
    )
    link = load_link(root)
    key = payload["agent"]
    agent_name = key.split("/", 1)[1]
    roster = players(link)
    roster[key] = {"token": payload["token"], "key": key, "agent": agent_name, "seat": seat}
    link["players"] = roster
    link["active"] = key
    link["player"] = key
    link["agent"] = agent_name
    link["seat"] = seat
    link["agent_token"] = payload["token"]
    save_link(link, root)
    return payload


def attach_agent(raw_url: str, seat: str, agent: str, agent_token: str, skills: list[str], root: Path | None = None) -> dict:
    """Save this computer's link and take the same seat the page just logged in as."""
    link_room(raw_url, root=root)
    chosen = agent or os.environ.get("TEAM_LINK_AGENT") or "agent"
    payload = _request(
        root,
        "POST",
        "/v1/join",
        {"seat": seat, "agent": chosen, "skills": skills},
        agent=False,
        token=agent_token or None,
    )
    link = load_link(root)
    key = payload["agent"]
    agent_name = key.split("/", 1)[1]
    roster = players(link)
    roster[key] = {"token": payload["token"], "key": key, "agent": agent_name, "seat": seat}
    link["players"] = roster
    link["active"] = key
    link["player"] = key
    link["agent"] = agent_name
    link["seat"] = seat
    link["agent_token"] = payload["token"]
    save_link(link, root)
    return payload


def room(root: Path | None = None) -> str:
    return _request(root, "GET", "/v1/room").get("text", "")


def wait(after: int, root: Path | None = None) -> dict:
    query = urlencode({"after": str(after)})
    return _request(root, "GET", f"/v1/wait?{query}", timeout=35)


def post(path: str, body: dict | None = None, root: Path | None = None) -> str:
    return _request(root, "POST", path, body or {}).get("text", "")
