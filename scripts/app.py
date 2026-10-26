#!/usr/bin/env python3
"""Team Code Link desktop entry. One program hosts or joins, and opens the board."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import attach
import liveclient
import livehub
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
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Port", str(port)],
        check=False,
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
        subprocess.run(["taskkill", "/PID", pid, "/F"], check=False, capture_output=True)
    pid_file.unlink(missing_ok=True)
    url_file = temp / "team-code-link-tunnel.url"
    if url_file.exists():
        url_file.unlink(missing_ok=True)


def open_board(url: str) -> None:
    webbrowser.open(url)


def serve_in_thread(host: str, port: int, data_dir: Path, public_url: str | None) -> threading.Thread:
    thread = threading.Thread(
        target=livehub.serve_forever,
        args=(host, port, data_dir, public_url),
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


def run_host(port: int, local: bool, public_url: str | None) -> int:
    root = liveclient.repo_root()
    data_dir = workspace.hub_dir(root, None)
    if not local and not public_url and os.name == "nt":
        public_url = start_tunnel(port)
    server = serve_in_thread("0.0.0.0", port, data_dir, public_url)
    try:
        token = wait_for_token(data_dir)
        local_url = f"http://127.0.0.1:{port}/?token={token}"
        liveclient.link_room(local_url, root=root)
        threading.Thread(target=attach.serve, daemon=True, name="team-link-attach").start()
        threading.Thread(target=source_loop.loop, args=(root,), daemon=True, name="team-link-source").start()
        open_board(f"http://127.0.0.1:{port}/")
        while server.is_alive():
            time.sleep(0.5)
        return 0
    finally:
        stop_tunnel()


def run_join(url: str) -> int:
    root = liveclient.repo_root()
    if url:
        print(liveclient.link_room(url, root=root))
    else:
        try:
            liveclient.load_link(root)
        except OrchestraError as exc:
            raise OrchestraError("Paste the share link: Team Code Link.exe --join https://the-link/?token=...") from exc
    threading.Thread(target=attach.serve, daemon=True, name="team-link-attach").start()
    threading.Thread(target=source_loop.loop, args=(root,), daemon=True, name="team-link-source").start()
    link = liveclient.load_link(root)
    open_board(link["url"] + "/")
    print("Leave this window open. Closing it stops the agent connection on this computer.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Team Code Link")
    parser.add_argument("--join", nargs="?", const="", default=None, help="Join a room with the share link")
    parser.add_argument("--local", action="store_true", help="Host on this network only")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--public-url")
    args = parser.parse_args(argv)
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)
    try:
        if args.join is not None:
            return run_join(args.join)
        return run_host(args.port, args.local, args.public_url)
    except OrchestraError as exc:
        print(exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
