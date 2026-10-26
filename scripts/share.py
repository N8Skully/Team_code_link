#!/usr/bin/env python3
"""One shared project folder. The source computer owns the files."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from orchestra import OrchestraError


def next_action(seat: str, project: str, source: dict, handoff: str, holding: str) -> str:
    """What this computer should do for the shared folder.

    commit: current source writes a local git commit before a handoff.
    copy: the next source copies the folder, then shares it.
    publish: this computer is the source and has not published a path yet.
    unshare: this computer still has the Windows share, and it is no longer the source.
    wait: nothing to do.
    """
    if not seat or not project:
        return "wait"
    owner = (source or {}).get("seat") or ""
    ready = bool((source or {}).get("ready"))
    path = (source or {}).get("path") or ""
    if handoff and owner == seat and not ready:
        return "commit"
    if handoff and handoff == seat and ready and path:
        return "copy"
    if not handoff and owner == seat and not path:
        return "publish"
    if holding and owner != seat:
        return "unshare"
    return "wait"


def project_folder(home: Path, name: str, room_repo: Path | None = None) -> Path:
    folder = (home / "Team Code Link Projects" / name).resolve()
    if room_repo is not None:
        repo = room_repo.resolve()
        if folder == repo or repo in folder.parents:
            raise OrchestraError("The shared project cannot live inside the Team Code Link repo.")
    return folder


def commit_folder(folder: Path, message: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    git = _git()
    if not (folder / ".git").exists():
        _run([git, "-C", str(folder), "init"])
    _run([git, "-C", str(folder), "add", "-A"])
    for secret in (".env", ".env.local"):
        _run([git, "-C", str(folder), "reset", "-q", "--", secret], check=False)
    status = _run([git, "-C", str(folder), "status", "--porcelain"])
    if not (status.stdout or "").strip():
        return "Already committed."
    _run([git, "-C", str(folder), "commit", "-m", message])
    return "Committed."


def copy_folder(src: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        raise OrchestraError("Copying the shared folder uses Windows.")
    result = subprocess.run(
        ["robocopy", src, str(dest), "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/R:1", "/W:1"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode >= 8:
        detail = (result.stderr or result.stdout or "robocopy failed").strip()
        raise OrchestraError(detail)


_LOGIN_URL = re.compile(r"https://login\.tailscale\.com/\S+")


def read_tailscale(installed: bool, returncode: int, stdout: str, host: str) -> dict:
    ip = ""
    for line in (stdout or "").splitlines():
        text = line.strip()
        if text.startswith("100."):
            ip = text
            break
    connected = installed and returncode == 0 and bool(ip)
    if not installed:
        login = "https://tailscale.com/download/windows"
    elif connected:
        login = ""
    else:
        login = "https://login.tailscale.com/"
    return {"installed": installed, "connected": connected, "ip": ip, "host": host, "loginUrl": login}


def tailscale_status() -> dict:
    host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or ""
    if shutil.which("tailscale") is None:
        return read_tailscale(False, 1, "", host)
    result = _run(["tailscale", "ip", "-4"], check=False)
    return read_tailscale(True, result.returncode, result.stdout or "", host)


def tailscale_login() -> str:
    """Start Tailscale sign-in and return the page the browser should open."""
    status = tailscale_status()
    if not status["installed"]:
        return status["loginUrl"]
    if status["connected"]:
        return ""
    import subprocess
    import time

    proc = subprocess.Popen(
        ["tailscale", "login"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    found = ""
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
            continue
        match = _LOGIN_URL.search(line)
        if match:
            found = match.group(0).rstrip(").,")
            break
    return found or "https://login.tailscale.com/"


def tailscale_hostname() -> str:
    if shutil.which("tailscale") is None:
        raise OrchestraError("Install Tailscale and sign in on this computer before sharing the project.")
    result = _run(["tailscale", "ip", "-4"], check=False)
    ip = (result.stdout or "").strip().splitlines()
    if result.returncode != 0 or not ip or not ip[0].startswith("100."):
        raise OrchestraError("Tailscale is installed, but this computer is not on the private network yet.")
    return os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "computer"


def share_unc(hostname: str, name: str) -> str:
    return f"\\\\{hostname}\\{name}"


def install_editor_hook(folder: Path) -> None:
    """Cursor refuses a second agent save while another seat holds the file."""
    hooks = folder / ".cursor" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    (hooks / "file_lock.py").write_text(LOCK_HOOK, encoding="utf-8")
    (folder / ".cursor" / "hooks.json").write_text(LOCK_HOOKS, encoding="utf-8")


LOCK_HOOKS = """{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "command": "python3 .cursor/hooks/file_lock.py",
        "matcher": "Write|StrReplace|Delete|EditNotebook",
        "failClosed": true,
        "timeout": 10
      }
    ]
  }
}
"""

LOCK_HOOK = r'''#!/usr/bin/env python3
"""Claim a project file before Cursor writes it. A second writer is refused."""
import json
import sys
import urllib.error
import urllib.request

def file_path(payload):
    tool = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool, dict):
        return ""
    for key in ("path", "file_path", "target_file", "file"):
        value = tool.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""

raw = sys.stdin.read()
try:
    payload = json.loads(raw or "{}")
except json.JSONDecodeError:
    payload = {}
path = file_path(payload)
if not path:
    json.dump({"permission": "allow"}, sys.stdout)
    raise SystemExit(0)
body = json.dumps({"path": path}).encode("utf-8")
request = urllib.request.Request(
    "http://127.0.0.1:8770/lock",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=8) as response:
        response.read()
except urllib.error.HTTPError as exc:
    detail = exc.read().decode("utf-8", errors="replace")
    try:
        message = json.loads(detail).get("error") or detail
    except json.JSONDecodeError:
        message = detail or "That file is already being edited."
    json.dump({
        "permission": "deny",
        "user_message": message,
        "agent_message": message,
    }, sys.stdout)
    raise SystemExit(0)
except urllib.error.URLError:
    json.dump({
        "permission": "deny",
        "user_message": "Team Code Link is not running on this computer, so the file was not claimed.",
        "agent_message": "Start Team Code Link.exe and log in, then edit the file again.",
    }, sys.stdout)
    raise SystemExit(0)
json.dump({"permission": "allow"}, sys.stdout)
'''



def ensure_share(name: str, folder: Path) -> None:
    if os.name != "nt":
        raise OrchestraError("Sharing the project folder uses Windows.")
    folder.mkdir(parents=True, exist_ok=True)
    script = """
$name = $env:TCL_SHARE_NAME
$path = $env:TCL_SHARE_PATH
$existing = Get-SmbShare -Name $name -ErrorAction SilentlyContinue
if ($existing) {
  if ($existing.Path -ne $path) { Remove-SmbShare -Name $name -Force }
}
if (-not (Get-SmbShare -Name $name -ErrorAction SilentlyContinue)) {
  New-SmbShare -Name $name -Path $path -FullAccess Everyone | Out-Null
}
$adapter = Get-NetAdapter | Where-Object { $_.InterfaceDescription -like '*Tailscale*' -or $_.Name -like '*Tailscale*' } | Select-Object -First 1
if ($adapter) {
  $rule = "Team Code Link SMB"
  Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
  New-NetFirewallRule -DisplayName $rule -Direction Inbound -Protocol TCP -LocalPort 445 -Action Allow -InterfaceAlias $adapter.Name | Out-Null
}
Set-NetFirewallRule -DisplayGroup "File and Printer Sharing" -Profile Public -Enabled False -ErrorAction SilentlyContinue
"""
    _powershell(script, {"TCL_SHARE_NAME": name, "TCL_SHARE_PATH": str(folder)})


def remove_share(name: str) -> None:
    if os.name != "nt" or not name:
        return
    script = """
$name = $env:TCL_SHARE_NAME
if (Get-SmbShare -Name $name -ErrorAction SilentlyContinue) {
  Remove-SmbShare -Name $name -Force
}
"""
    _powershell(script, {"TCL_SHARE_NAME": name})


def _git() -> str:
    found = shutil.which("git")
    if not found:
        raise OrchestraError("Git is required on the source computer so the folder can be committed before a handoff.")
    return found


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, check=False, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "command failed").strip()
        raise OrchestraError(detail)
    return result


def _powershell(script: str, env: dict[str, str]) -> None:
    merged = os.environ.copy()
    merged.update(env)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=merged,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Windows could not change the share.").strip()
        raise OrchestraError(detail)

