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

import codework
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
    commands.add_parser("sync", help="Pull and push the shared branch for your current part")

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


def require_clean(root: Path) -> None:
    if codework.is_repo(root) and not codework.working_tree_clean(root):
        raise OrchestraError("Commit or stash your changes before moving onto shared code.")


def align_code(root: Path, payload: dict) -> list[str]:
    task = codework.active_task(payload)
    if not task:
        return []
    return [codework.sync_part(root, task["id"])]


def return_finished(root: Path, before_seq: int, payload: dict) -> list[str]:
    notes = []
    for task_id in codework.finished_task_ids(before_seq, payload):
        try:
            notes.append(codework.reunite(root, task_id))
        except OrchestraError as exc:
            repaired = liveclient._request(root, "POST", "/v1/reopen", {"task": task_id})
            codework.sync_part(root, task_id)
            raise OrchestraError(f"{exc}\n{repaired.get('text', '')}") from exc
    return notes


def show(payload: dict, extra: list[str] | None = None) -> None:
    text = payload.get("text") or ""
    if text:
        print(text)
    for line in extra or []:
        if line:
            print(line)


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
            payload = liveclient.join(args.name, args.agent, args.skill or [], root)
            show(payload, align_code(root, payload))
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
        if args.command == "sync":
            current = liveclient._request(root, "GET", "/v1/room")
            task = codework.active_task(current)
            if not task:
                raise OrchestraError("You have no active part to sync.")
            print(codework.sync_part(root, task["id"]))
            print(codework.push_part(root, task["id"]))
            return 0
        if args.command == "conduct":
            show(liveclient._request(root, "POST", "/v1/conduct", {"player": args.player}))
            return 0
        if args.command == "plan":
            spec = json.loads(Path(args.file).read_text(encoding="utf-8"))
            if not isinstance(spec, dict):
                raise OrchestraError("The plan file must be a JSON object.")
            payload = liveclient._request(root, "POST", "/v1/plan", spec)
            show(payload, align_code(root, payload))
            return 0
        if args.command == "say":
            show(liveclient._request(root, "POST", "/v1/say", {"text": message_text(args), "task": args.task, "files": args.file or []}))
            return 0
        if args.command == "leave":
            show(liveclient._request(root, "POST", "/v1/leave", {}))
            return 0
        if args.command == "finish":
            require_clean(root)
            before = liveclient._request(root, "GET", "/v1/room")
            current = codework.active_task(before)
            pushed = []
            if current:
                note = codework.push_part(root, current["id"])
                if note:
                    pushed.append(note)
            payload = liveclient._request(root, "POST", "/v1/finish", {"task": args.task, "approach": args.approach})
            notes = pushed + return_finished(root, int(before.get("seq") or 0), payload)
            notes.extend(align_code(root, payload))
            show(payload, notes)
            return 0
        if args.command == "help-on":
            require_clean(root)
            payload = liveclient._request(root, "POST", "/v1/help", {"task": args.task})
            show(payload, align_code(root, payload))
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
