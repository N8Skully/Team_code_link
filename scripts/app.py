#!/usr/bin/env python3
"""Team Code Link desktop entry. One program hosts or joins, and opens the board."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import attach
import agent_listen
import liveclient
import livehub
import share
import source_loop
import workspace
from orchestra import OrchestraError


def bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return HERE.parent


def tunnel_script() -> Path:
    return bundle_root() / "scripts" / "open_tunnel.ps1"


def start_tunnel(port: int) -> str:
    script = tunnel_script()
    if not script.is_file():
        raise OrchestraError("The tunnel script is missing from this program.")
    result = subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Port", str(port)],
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode != 0:
        raise OrchestraError("The internet link did not start.")
    url_file = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "team-code-link-tunnel.url"
    public = url_file.read_text(encoding="utf-8").strip() if url_file.exists() else ""
    if not public:
        raise OrchestraError("The tunnel did not return a public address.")
    return public


def stop_tunnel() -> None:
    temp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".")
    pid_file = temp / "team-code-link-tunnel.pid"
    if not pid_file.exists():
        return
    pid = pid_file.read_text(encoding="utf-8").strip()
    if pid.isdigit():
        subprocess.run(
            ["taskkill", "/PID", pid, "/F"],
            check=False,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    pid_file.unlink(missing_ok=True)
    url_file = temp / "team-code-link-tunnel.url"
    if url_file.exists():
        url_file.unlink(missing_ok=True)


def show_app() -> None:
    import webview

    class WindowApi:
        def pick_folder(self) -> str:
            if not webview.windows:
                return ""
            kind = getattr(webview, "FOLDER_DIALOG", None)
            if kind is None:
                kind = webview.FileDialog.FOLDER
            chosen = webview.windows[0].create_file_dialog(kind)
            if not chosen:
                return ""
            return str(chosen[0])

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
    webview.create_window("Team Code Link", "http://127.0.0.1:8770/", width=680, height=900, js_api=WindowApi())
    webview.start()


def wait_for_login() -> None:
    import urllib.request

    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8770/tailscale", timeout=0.4) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)


def serve_in_thread(host: str, port: int, data_dir: Path, public_url: str | None) -> threading.Thread:
    thread = threading.Thread(
        target=livehub.serve_forever,
        args=(host, port, data_dir, public_url),
        kwargs={"quiet": True},
        daemon=True,
        name="team-link-room",
    )
    thread.start()
    return thread


def wait_for_token(data_dir: Path) -> str:
    token_file = data_dir / "room.token"
    for _ in range(50):
        if token_file.exists():
            token = token_file.read_text(encoding="utf-8").strip()
            if token:
                return token
        time.sleep(0.1)
    raise OrchestraError("The room did not write its token.")


_host_started = False


def begin_host(port: int = 8765) -> str:
    """Start the room when the person chooses Host, and return the short room code."""
    global _host_started
    import secrets

    data = app_home() / "room"
    data.mkdir(parents=True, exist_ok=True)
    token_file = data / "room.token"
    code = token_file.read_text(encoding="utf-8").strip() if token_file.is_file() else ""
    if not code or len(code) > 12 or "://" in code:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        token_file.write_text(code + "\n", encoding="utf-8")
    if not _host_started:
        serve_in_thread("0.0.0.0", port, data, None)
        wait_for_token(data)
        for _ in range(30):
            if _room_answers(port, code):
                _host_started = True
                break
            time.sleep(0.1)
        if not _host_started:
            raise OrchestraError(
                "The room did not start. Close any other Team Code Link window, then choose Host and share again."
            )
    liveclient.link_room(f"http://127.0.0.1:{port}/?token={code}")
    attach.set_invite(code)
    return code


attach.begin_host = begin_host


def _room_answers(port: int, code: str) -> bool:
    import urllib.request

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/score",
        headers={"Authorization": f"Bearer {code}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=0.5) as response:
            return response.status == 200
    except OSError:
        return False


def use_saved_project() -> None:
    folder = str(share.load_settings().get("folder") or "").strip()
    if folder and Path(folder).is_dir():
        os.environ["TEAM_LINK_ROOT"] = str(Path(folder).resolve())


def run_window() -> int:
    use_saved_project()
    threading.Thread(target=attach.serve, daemon=True, name="team-link-attach").start()
    threading.Thread(target=source_loop.loop, daemon=True, name="team-link-source").start()
    threading.Thread(target=agent_listen.loop, daemon=True, name="team-link-listen").start()
    wait_for_login()
    show_app()
    return 0


def app_home() -> Path:
    """The frozen program keeps its room next to the user, not inside a git checkout."""
    if getattr(sys, "frozen", False):
        home = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Team Code Link"
        home.mkdir(parents=True, exist_ok=True)
        return home
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Team Code Link")
    parser.add_argument("--join", nargs="?", const="", default=None, help="Join a room with the share link")
    parser.add_argument("--local", action="store_true", help="Host on this network only")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--public-url")
    args = parser.parse_args(argv)
    os.environ["TEAM_LINK_APP"] = "1"
    if getattr(sys, "frozen", False):
        os.chdir(app_home())
    try:
        return run_window()
    except OrchestraError as exc:
        print(exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
