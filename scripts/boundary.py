#!/usr/bin/env python3
"""Keep one agent off another computer and off another database."""

from __future__ import annotations

import re
import shlex

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DB_COMMANDS = {"psql", "mysql", "mariadb", "redis-cli", "mongosh", "mongo", "sqlcmd", "sqlplus"}
REMOTE_COMMANDS = {"ssh", "scp", "sftp", "sshpass"}
DB_URL = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|rediss|amqp|amqps)://(?:[^@/\s]+@)?([^/:?\s]+)",
    re.IGNORECASE,
)
DB_PORT = re.compile(r":(5432|3306|27017|6379|1433|1521)\b")
PRIVATE_FILES = (
    "/.ssh/",
    "/.aws/",
    "/.kube/",
    ".pgpass",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    ".mysql_history",
    ".psql_history",
    ".netrc",
)


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _host_after(tokens: list[str], index: int) -> str | None:
    token = tokens[index]
    if token in {"-h", "--host"} and index + 1 < len(tokens):
        return tokens[index + 1]
    if token.startswith("--host="):
        return token.split("=", 1)[1]
    return None


def _local(host: str) -> bool:
    name = host.strip().strip("[]").lower()
    return name in LOCAL_HOSTS


def review_shell(command: str) -> tuple[str, str]:
    """Return allow or deny for a command about to run on this computer."""
    deny = (
        "deny",
        "This command would reach another computer or its database. Stay on this machine.",
    )
    lowered = command.lower()
    tokens = _tokens(command)
    programs = {token.rsplit("/", 1)[-1] for token in tokens}
    if any(token.rsplit("/", 1)[-1] in REMOTE_COMMANDS or token.rsplit("/", 1)[-1] in {"nc", "ncat", "netcat", "socat"} for token in tokens):
        return deny
    if "rsync" in programs and re.search(r"\s\S+:\S", command):
        return deny
    for match in DB_URL.finditer(command):
        if not _local(match.group(1)):
            return deny
    if DB_PORT.search(command) and not any(_local(match.group(1)) for match in DB_URL.finditer(command)):
        if not re.search(r"localhost|127\.0\.0\.1|::1", lowered):
            return deny
    for index, token in enumerate(tokens):
        program = token.rsplit("/", 1)[-1]
        if program not in DB_COMMANDS:
            continue
        for later in range(index + 1, len(tokens)):
            host = _host_after(tokens, later)
            if host and not _local(host):
                return deny
    for match in re.finditer(r"\b(?:PGHOST|MYSQL_HOST|REDIS_HOST)\s*=\s*([^\s]+)", command, re.IGNORECASE):
        if not _local(match.group(1)):
            return deny
    return "allow", ""


def review_read(path: str) -> tuple[str, str]:
    lowered = path.replace("\\", "/").lower()
    for needle in PRIVATE_FILES:
        if needle in lowered:
            return (
                "deny",
                "That file can open another computer or a database. Leave it on this machine.",
            )
    return "allow", ""
