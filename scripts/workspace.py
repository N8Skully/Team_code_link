#!/usr/bin/env python3
"""CLI for the shared Team Code Link room."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import teamlink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workspace.py",
        description="Connect a computer to the shared project room and talk to the other agents.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    join = commands.add_parser("join", help="Claim one of the six computer seats")
    join.add_argument("--name", required=True)
    join.add_argument("--start", action="store_true", help="Also start a Cursor worker on this computer")
    join.add_argument("--pool", help="Cursor Enterprise pool name")
    join.add_argument("--computer-use", action="store_true")
    join.add_argument("--dry-run", action="store_true")

    leave = commands.add_parser("leave", help="Free a seat")
    leave.add_argument("--name", help="Defaults to this computer's seat")

    commands.add_parser("status", help="Show the claimed seats")

    room = commands.add_parser("room", help="Show seats and recent messages")
    room.add_argument("--max", type=int, default=20)

    listen = commands.add_parser("listen", help="Show messages")
    listen.add_argument("--max", type=int, default=20)
    listen.add_argument("--after", help="Only messages after this id")
    listen.add_argument("--mention", help="Only messages that mention this seat")
    listen.add_argument("--follow", action="store_true", help="Keep watching for new messages")

    say = commands.add_parser("say", help="Post a message to the other agents")
    say.add_argument("words", nargs="*", help="Message text")
    say.add_argument("--text", help="Message text")
    say.add_argument("--agent", help="claude, chatgpt, cursor, hermes, or another short name")
    say.add_argument("--reply-to", help="Message id to reply to")
    say.add_argument("--file", action="append", help="Repo path you are editing")

    commands.add_parser("sync", help="Merge origin/main into the current seat branch")
    return parser


def message_text(args: argparse.Namespace) -> str:
    words = args.words or []
    if args.text and words:
        raise teamlink.WorkspaceError("Pass the message either as words or with --text, not both.")
    if args.text:
        return args.text
    if words:
        return " ".join(words)
    raise teamlink.WorkspaceError("Pass a message to send.")


def follow(repo: Path, args: argparse.Namespace) -> int:
    print("Watching the room. Stop with Ctrl+C.", flush=True)
    last: str | None = None
    first = True
    while True:
        text = teamlink.render_listen(
            repo,
            max_messages=args.max,
            after=last or args.after,
            mention=args.mention,
        )
        if text and not text.startswith("(none yet)") and not text.startswith("Offline copy"):
            print(text, flush=True)
            # The last id is on the last header line we printed. Ask again from the end.
            talk_offline = teamlink.load_room_state(repo, required=False)
            messages = teamlink.select_messages(
                talk_offline[1],
                max_messages=teamlink.MESSAGE_KEEP,
                after=last or args.after,
                mention=args.mention,
            )
            if messages:
                last = messages[-1]["id"]
        elif first:
            print(text, flush=True)
        first = False
        time.sleep(3)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = teamlink.resolve_repo()
        if args.command == "join":
            text = teamlink.claim_seat(
                repo,
                args.name,
                checkout=True,
                start_worker=args.start,
                pool=args.pool,
                computer_use=args.computer_use,
                dry_run=args.dry_run,
            )
        elif args.command == "leave":
            text = teamlink.release_seat(repo, args.name)
        elif args.command == "status":
            text = teamlink.render_status(repo)
        elif args.command == "room":
            text = teamlink.render_room(repo, max_messages=args.max)
        elif args.command == "listen":
            if args.follow:
                return follow(repo, args)
            text = teamlink.render_listen(
                repo,
                max_messages=args.max,
                after=args.after,
                mention=args.mention,
            )
        elif args.command == "say":
            text = teamlink.post_message(
                repo,
                message_text(args),
                agent=args.agent,
                reply_to=args.reply_to,
                files=args.file or [],
            )
        elif args.command == "sync":
            text = teamlink.sync_seat(repo)
        else:
            parser.error(f"Unknown command {args.command}")
            return 2
        print(text)
        return 0
    except teamlink.WorkerMissing as exc:
        print(exc, file=sys.stderr)
        return 2
    except teamlink.WorkspaceError as exc:
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
