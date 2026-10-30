#!/usr/bin/env python3
"""Put every player on a part onto one git branch, and return that branch to main in one piece."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from orchestra import OrchestraError


def part_branch(task_id: str) -> str:
    if not task_id or "/" in task_id or task_id.startswith("-"):
        raise OrchestraError("That part has no shared branch.")
    return f"part/{task_id}"


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "git failed").strip()
        raise OrchestraError(detail)
    return result


def is_repo(root: Path) -> bool:
    result = _git(root, "rev-parse", "--is-inside-work-tree", check=False)
    return result.returncode == 0 and result.stdout.strip() == "true"


def working_tree_clean(root: Path) -> bool:
    return _git(root, "status", "--porcelain").stdout.strip() == ""


def _clean(root: Path) -> bool:
    return working_tree_clean(root)


def _ref_exists(root: Path, ref: str) -> bool:
    return _git(root, "rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0


def _ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode == 0


def _fetch(root: Path) -> None:
    fetched = _git(root, "fetch", "origin", check=False)
    if fetched.returncode != 0:
        detail = (fetched.stderr or fetched.stdout or "").strip()
        raise OrchestraError("Could not fetch origin, so the shared part could not be updated." + (f"\n{detail}" if detail else ""))


def _checkout_main(root: Path) -> None:
    if not _clean(root):
        raise OrchestraError("Commit or stash your changes before moving between the shared part and main.")
    _fetch(root)
    if not _ref_exists(root, "refs/remotes/origin/main"):
        raise OrchestraError("origin/main is missing. Push main before starting a part.")
    if _ref_exists(root, "refs/heads/main"):
        _git(root, "checkout", "main")
        merged = _git(root, "merge", "--ff-only", "origin/main", check=False)
        if merged.returncode != 0:
            raise OrchestraError("Local main has commits that are not on origin. Push or move them before reuniting a part.")
    else:
        _git(root, "checkout", "-b", "main", "origin/main")


def _merge_ref(root: Path, ref: str) -> None:
    merged = _git(root, "merge", "--no-edit", ref, check=False)
    if merged.returncode == 0:
        return
    _git(root, "merge", "--abort", check=False)
    raise OrchestraError(
        f"The shared code does not fit together at {ref}. "
        "Stay on this part branch and make the same files agree before it returns to main."
    )


def sync_part(root: Path, task_id: str) -> str:
    """Check out the one branch every player on this part shares."""
    if not is_repo(root):
        return "This folder is not a git clone, so the shared code branch was not checked out."
    if not _clean(root):
        raise OrchestraError("Commit or stash your changes before joining the shared part branch.")
    branch = part_branch(task_id)
    remote = f"refs/remotes/origin/{branch}"
    local = f"refs/heads/{branch}"
    _fetch(root)
    if _ref_exists(root, remote):
        if _ref_exists(root, local):
            _git(root, "checkout", branch)
        else:
            _git(root, "checkout", "--track", "-b", branch, remote)
        _merge_ref(root, remote)
        return f"Code branch: {branch}"
    _checkout_main(root)
    if _ref_exists(root, local):
        _git(root, "checkout", branch)
    else:
        _git(root, "checkout", "-b", branch)
    pushed = _git(root, "push", "-u", "origin", f"HEAD:refs/heads/{branch}", check=False)
    if pushed.returncode != 0:
        _fetch(root)
        if not _ref_exists(root, remote):
            detail = (pushed.stderr or pushed.stdout or "").strip()
            raise OrchestraError(f"Could not publish {branch}." + (f"\n{detail}" if detail else ""))
        ahead = _git(root, "rev-list", "--count", f"{remote}..HEAD", check=False)
        if ahead.returncode == 0 and ahead.stdout.strip() in ("", "0"):
            _git(root, "reset", "--hard", remote)
            _git(root, "branch", "--set-upstream-to", remote, check=False)
        else:
            _merge_ref(root, remote)
    return f"Code branch: {branch}"


def push_part(root: Path, task_id: str) -> str:
    if not is_repo(root):
        return ""
    branch = part_branch(task_id)
    if _git(root, "branch", "--show-current").stdout.strip() != branch:
        return ""
    if not _clean(root):
        raise OrchestraError("Commit the shared part before it can be passed to another player.")
    pushed = _git(root, "push", "-u", "origin", f"HEAD:refs/heads/{branch}", check=False)
    if pushed.returncode != 0:
        detail = (pushed.stderr or pushed.stdout or "").strip()
        raise OrchestraError(f"Could not push {branch}." + (f"\n{detail}" if detail else ""))
    return f"Pushed {branch}."


def reunite(root: Path, task_id: str) -> str:
    """Return a finished part to main as one piece. Refuse a conflicted stitch."""
    if not is_repo(root):
        raise OrchestraError("This folder is not a git clone, so the finished part could not return to main.")
    if not _clean(root):
        raise OrchestraError("Commit or stash your changes before the part returns to main.")
    branch = part_branch(task_id)
    remote = f"refs/remotes/origin/{branch}"
    _fetch(root)
    if not _ref_exists(root, remote):
        raise OrchestraError(f"{branch} is not on origin yet, so it cannot return to main.")
    if _ancestor(root, remote, "refs/remotes/origin/main"):
        return f"{branch} is already on main."
    _checkout_main(root)
    merged = _git(root, "merge", "--no-edit", remote, check=False)
    if merged.returncode != 0:
        _git(root, "merge", "--abort", check=False)
        if _ref_exists(root, f"refs/heads/{branch}"):
            _git(root, "checkout", branch)
        raise OrchestraError(
            f"{branch} does not fit back onto main. The same lines changed on both sides. "
            "The part stays open so those lines can be made to agree. Nothing conflicted was left on main."
        )
    pushed = _git(root, "push", "origin", "HEAD:refs/heads/main", check=False)
    if pushed.returncode != 0:
        detail = (pushed.stderr or pushed.stdout or "").strip()
        raise OrchestraError("The part merged locally, but main could not be pushed." + (f"\n{detail}" if detail else ""))
    return f"{branch} returned to main."


def active_task(payload: dict) -> dict | None:
    snapshot = payload.get("snapshot") or {}
    you = snapshot.get("you")
    if not you:
        return None
    for task in snapshot.get("tasks") or []:
        if task.get("status") == "active" and you in (task.get("members") or []):
            return task
    return None


def finished_task_ids(before_seq: int, payload: dict) -> list[str]:
    found = []
    for event in payload.get("events") or []:
        if event.get("type") == "done" and event.get("seq", 0) > before_seq and event.get("task"):
            if event["task"] not in found:
                found.append(event["task"])
    return found
