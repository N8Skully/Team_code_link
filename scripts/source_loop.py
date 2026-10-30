#!/usr/bin/env python3
"""Keep this computer's share matched to the room."""

from __future__ import annotations

import os
from pathlib import Path

import liveclient
import share
from orchestra import OrchestraError


def my_seat(root: Path | None = None) -> str:
    try:
        link = liveclient.load_link(root)
    except OrchestraError:
        return ""
    player = liveclient.select_player(link)
    if not player:
        return ""
    return str(player.get("seat") or "")


def holding_name(root: Path | None = None) -> str:
    try:
        link = liveclient.load_link(root)
    except OrchestraError:
        return ""
    return str(link.get("shared_name") or "")


share_error = ""


def remember_share(name: str, root: Path | None = None) -> None:
    link = liveclient.load_link(root)
    if name:
        link["shared_name"] = name
    else:
        link.pop("shared_name", None)
    liveclient.save_link(link, root)


def note_share_error(message: str) -> None:
    global share_error
    share_error = message


def clear_share_error() -> None:
    global share_error
    share_error = ""


def publish_now(project: str, root: Path | None = None) -> str:
    """Share this computer's project folder and record the path in the room."""
    folder = share.working_folder(project)
    host = share.tailscale_hostname()
    try:
        share.ensure_share(project, folder)
    except OrchestraError as exc:
        text = str(exc)
        if "Access is denied" in text or "administrator" in text.lower():
            text = "Run Team Code Link as administrator to share the folder. " + text
        raise OrchestraError(text) from exc
    share.install_editor_hook(folder)
    path = share.share_unc(host, project)
    liveclient._request(root, "POST", "/v1/source-path", {"path": path})
    remember_share(project, root)
    clear_share_error()
    return path


def tick(root: Path | None = None, home: Path | None = None) -> str:
    seat = my_seat(root)
    if not seat:
        return "wait"
    try:
        room = liveclient._request(root, "GET", "/v1/room")
    except OrchestraError:
        return "wait"
    snap = room.get("snapshot") or {}
    project = str(snap.get("project") or "")
    source = snap.get("source") or {}
    handoff = str(snap.get("handoff") or "")
    action = share.next_action(seat, project, source, handoff, holding_name(root))
    if action == "wait":
        return action
    folder = share.working_folder(project)
    if action == "commit":
        share.commit_folder(folder, f"Handoff {project} from {seat}.")
        liveclient._request(root, "POST", "/v1/source-ready", {})
        return action
    if action == "publish":
        host = share.tailscale_hostname()
        share.ensure_share(project, folder)
        share.install_editor_hook(folder)
        path = share.share_unc(host, project)
        liveclient._request(root, "POST", "/v1/source-path", {"path": path})
        remember_share(project, root)
        print(f"Sharing {folder} as {path}", flush=True)
        clear_share_error()
        return action
    if action == "copy":
        share.copy_folder(str(source.get("path") or ""), folder)
        host = share.tailscale_hostname()
        share.ensure_share(project, folder)
        share.install_editor_hook(folder)
        path = share.share_unc(host, project)
        liveclient._request(root, "POST", "/v1/source-path", {"path": path})
        remember_share(project, root)
        print(f"Copied the project to {folder} and shared {path}", flush=True)
        clear_share_error()
        return action
    if action == "unshare":
        share.remove_share(holding_name(root))
        remember_share("", root)
        print("Removed the old project share.", flush=True)
        return action
    return "wait"


def loop(root: Path | None = None, stop: "object | None" = None) -> None:
    import time

    while True:
        if stop is not None and getattr(stop, "is_set", lambda: False)():
            return
        try:
            tick(root)
        except (OrchestraError, OSError) as exc:
            note_share_error(str(exc))
        if os.environ.get("TEAM_LINK_SOURCE_ONCE"):
            return
        time.sleep(3)
