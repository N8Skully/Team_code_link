#!/usr/bin/env python3
"""CLI for the live Team Code Link orchestra."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import liveclient
import livehub
from orchestra import OrchestraError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workspace.py",
        description="Live orchestra for up to six computers and any agent.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Start the live room on this computer")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--public-url", help="Address other computers use, if this host is tunneled")
    serve.add_argument("--data-dir")

    link = commands.add_parser("link", help="Point this computer at the live room")
    link.add_argument("url")
    link.add_argument("--token")

    join = commands.add_parser("join", help="Take a seat and declare what this agent is good at")
    join.add_argument("--name", required=True)
    join.add_argument("--agent")
    join.add_argument("--skill", action="append", default=None)
    join.add_argument("--start", action="store_true", help="Also start a Cursor worker")

    commands.add_parser("leave", help="Leave the orchestra")
    conduct = commands.add_parser("conduct", help="Take the podium, or hand it to another player")
    conduct.add_argument("--player", help="Player key, such as office/cursor")
    commands.add_parser("room", help="Read the live score")
    commands.add_parser("status", help="Read the live score")

    plan = commands.add_parser("plan", help="Conductor: publish the group plan")
    plan.add_argument("--file", required=True, help="JSON plan with title, framework, and tasks")

    say = commands.add_parser("say", help="Speak in the live room")
    say.add_argument("words", nargs="*")
    say.add_argument("--text")
    say.add_argument("--task", help="Speak inside one part")
    say.add_argument("--file", action="append")

    listen = commands.add_parser("listen", help="Follow the live room")
    listen.add_argument("--after", type=int, default=0)

    finish = commands.add_parser("finish", help="Finish your part and take the next opening")
    finish.add_argument("--task")
    finish.add_argument("--approach", help="Approach for the next part, if you lead it")

    help_cmd = commands.add_parser("help-on", help="Jump in on a teammate's part")
    help_cmd.add_argument("--task", required=True)

    partition = commands.add_parser("partition", help="Hide a part from the rest of the orchestra")
    partition.add_argument("--task", required=True)
    partition.add_argument("--off", action="store_true")

    approach = commands.add_parser("approach", help="Lead: set the approach teammates follow")
    approach.add_argument("--task", required=True)
    approach.add_argument("--text", required=True)

    place = commands.add_parser("place", help="Conductor: move a player onto a part")
    place.add_argument("--player", required=True)
    place.add_argument("--task", required=True)
    return parser


def message_text(args: argparse.Namespace) -> str:
    words = args.words or []
    if args.text and words:
        raise OrchestraError("Pass the message either as words or with --text, not both.")
    if args.text:
        return args.text
    if words:
        return " ".join(words)
    raise OrchestraError("Pass a message to send.")


def hub_dir(root: Path, override: str | None) -> Path:
    if override:
        return Path(override)
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-dir"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        path = Path(result.stdout.strip())
        if not path.is_absolute():
            path = root / path
        return path / "team-link-hub"
    return root / ".team-link-hub"


def checkout_seat(root: Path, name: str) -> str:
    branch = f"seat/{name.strip().lower()}"
    result = subprocess.run(
        ["git", "-C", str(root), "checkout", "-B", branch],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return "Code stays on the current branch until this checkout is clean."
    return f"Code branch: {branch}"


def follow(root: Path, after: int) -> int:
    print("Listening to the live room. Stop with Ctrl+C.", flush=True)
    while True:
        payload = liveclient.wait(after, root)
        after = int(payload.get("seq") or after)
        for event in payload.get("events") or []:
            text = event.get("text")
            if text:
                print(text, flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = liveclient.repo_root()
        if args.command == "serve":
            livehub.serve_forever(args.host, args.port, hub_dir(root, args.data_dir), args.public_url)
            return 0
        if args.command == "link":
            print(liveclient.link_room(args.url, args.token, root))
            return 0
        if args.command == "join":
            text = liveclient.join(args.name, args.agent, args.skill or [], root)
            print(text)
            print(checkout_seat(root, args.name))
            if args.start:
                if shutil.which("agent") is None:
                    print(
                        "The Cursor CLI is not installed, so the worker did not start.\n"
                        "Install it with: curl https://cursor.com/install -fsS | bash\n"
                        "Then run: agent login",
                        file=sys.stderr,
                    )
                    return 2
                os.chdir(root)
                os.execvp("agent", ["agent", "worker", "start", "--name", args.name.strip().lower(), "--worker-dir", str(root)])
            return 0
        if args.command == "listen":
            return follow(root, args.after)
        if args.command in {"room", "status"}:
            print(liveclient.room(root))
            return 0
        if args.command == "conduct":
            print(liveclient.post("/v1/conduct", {"player": args.player}, root))
            return 0
        if args.command == "plan":
            spec = json.loads(Path(args.file).read_text(encoding="utf-8"))
            if not isinstance(spec, dict):
                raise OrchestraError("The plan file must be a JSON object.")
            print(liveclient.post("/v1/plan", spec, root))
            return 0
        if args.command == "say":
            print(liveclient.post("/v1/say", {"text": message_text(args), "task": args.task, "files": args.file or []}, root))
            return 0
        if args.command == "leave":
            print(liveclient.post("/v1/leave", {}, root))
            return 0
        if args.command == "finish":
            print(liveclient.post("/v1/finish", {"task": args.task, "approach": args.approach}, root))
            return 0
        if args.command == "help-on":
            print(liveclient.post("/v1/help", {"task": args.task}, root))
            return 0
        if args.command == "partition":
            print(liveclient.post("/v1/partition", {"task": args.task, "on": not args.off}, root))
            return 0
        if args.command == "approach":
            print(liveclient.post("/v1/approach", {"task": args.task, "text": args.text}, root))
            return 0
        if args.command == "place":
            print(liveclient.post("/v1/place", {"player": args.player, "task": args.task}, root))
            return 0
        parser.error(f"Unknown command {args.command}")
        return 2
    except OrchestraError as exc:
        print(exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
