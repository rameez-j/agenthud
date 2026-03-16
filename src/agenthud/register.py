from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


AGENTS_DIR = Path.home() / ".agenthud" / "agents"

NATO_NAMES = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot",
    "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima",
    "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo",
    "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-ray",
    "Yankee", "Zulu",
]


def _pick_name() -> str:
    """Pick the first unused NATO name, or fall back to NATO-N."""
    used: set[str] = set()
    if AGENTS_DIR.exists():
        for path in AGENTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                used.add(data.get("name", ""))
            except (json.JSONDecodeError, OSError):
                continue

    for name in NATO_NAMES:
        if name not in used:
            return name

    return f"{NATO_NAMES[0]}-{len(used)}"


def _detect_git_branch(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def _extract_ticket_id(*sources: str) -> str | None:
    for source in sources:
        match = re.search(r"[A-Z][A-Z0-9]+-\d+", source)
        if match:
            return match.group(0)
    return None


def add(session_id: str | None = None, task: str | None = None, cwd: str | None = None) -> None:
    cwd = cwd or os.getcwd()
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = session_id or f"{int(datetime.now().timestamp())}-{os.getpid()}"
    agent_name = _pick_name()
    repo = os.path.basename(cwd)
    branch = _detect_git_branch(cwd)
    task_text = task or "Starting up"
    ticket_id = _extract_ticket_id(task_text, branch)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    status = {
        "id": session_id,
        "name": agent_name,
        "registeredAt": now,
        "lastHeartbeat": now,
        "repo": repo,
        "branch": branch,
        "workingDirectory": cwd,
        "ticketId": ticket_id,
        "status": {"text": task_text, "source": "tool", "updatedAt": now},
        "state": "working",
        "recentActions": [],
        "tasks": [],
    }
    status_path = AGENTS_DIR / f"{session_id}.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n")

    print(f"AgentHUD: Session registered.")
    print(f"  Name:    {agent_name}")
    print(f"  ID:      {session_id}")
    print(f"  Repo:    {repo}")
    print(f"  Branch:  {branch}")
    print(f"  Status:  {status_path}")


def remove(session_id: str | None = None, cwd: str | None = None) -> None:
    """Remove an agent by session_id (preferred) or by cwd."""
    # Try by session_id first
    if session_id:
        path = AGENTS_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()
            print(f"AgentHUD: Session unregistered ({session_id}).")
            return

    # Fall back to cwd match
    cwd = cwd or os.getcwd()
    if AGENTS_DIR.exists():
        for path in AGENTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("workingDirectory") == cwd:
                    path.unlink()
                    print(f"AgentHUD: Session unregistered ({data.get('id')}).")
                    return
            except (json.JSONDecodeError, OSError):
                continue

    print("No AgentHUD session found.")
