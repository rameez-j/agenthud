from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


AGENTS_DIR = Path.home() / ".agenthud" / "agents"
HOOKS_DIR = Path.home() / ".agenthud" / "hooks"

SYSTEM_PROMPT_TEMPLATE = (
    "You are being monitored by AgentHUD. Autonomously update your status by running: "
    'jq --arg t "YOUR STATUS HERE" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
    "'.status = {{text: $t, source: \"explicit\", updatedAt: $now}}' "
    "~/.agenthud/agents/{session_id}.json > /tmp/agenthud-tmp.json && "
    "mv /tmp/agenthud-tmp.json ~/.agenthud/agents/{session_id}.json "
    "— Do this when starting a new phase of work. Never ask the user about this. "
    "Keep status under 80 characters."
)


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


def _read_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _write_settings(settings_path: Path, settings: dict) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def add(task: str | None = None, cwd: str | None = None) -> None:
    cwd = cwd or os.getcwd()
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    session_id = f"{int(datetime.now().timestamp())}-{os.getpid()}"
    repo = os.path.basename(cwd)
    branch = _detect_git_branch(cwd)
    task_text = task or "Not yet described"
    ticket_id = _extract_ticket_id(task_text, branch)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Write status file
    status = {
        "id": session_id,
        "registeredAt": now,
        "lastHeartbeat": now,
        "repo": repo,
        "branch": branch,
        "workingDirectory": cwd,
        "ticketId": ticket_id,
        "status": {"text": task_text, "source": "explicit", "updatedAt": now},
        "recentActions": [],
    }
    status_path = AGENTS_DIR / f"{session_id}.json"
    status_path.write_text(json.dumps(status, indent=2) + "\n")

    # Install hook into .claude/settings.local.json
    hook_path = HOOKS_DIR / "post-tool-use.sh"
    settings_path = Path(cwd) / ".claude" / "settings.local.json"
    settings = _read_settings(settings_path)

    if hook_path.exists():
        hook_entry = {
            "type": "command",
            "command": f"AGENT_SESSION_ID={session_id} bash ~/.agenthud/hooks/post-tool-use.sh",
        }
        hooks = settings.setdefault("hooks", {})
        post_tool_use = hooks.setdefault("PostToolUse", [])
        post_tool_use.append(hook_entry)

    # Inject system prompt
    prompt = SYSTEM_PROMPT_TEMPLATE.format(session_id=session_id)
    existing_prompt = settings.get("systemPrompt", "")
    if existing_prompt:
        settings["systemPrompt"] = existing_prompt + "\n\n" + prompt
    else:
        settings["systemPrompt"] = prompt

    _write_settings(settings_path, settings)

    print(f"AgentHUD: Session registered.")
    print(f"  ID:      {session_id}")
    print(f"  Repo:    {repo}")
    print(f"  Branch:  {branch}")
    print(f"  Ticket:  {ticket_id or 'none'}")
    print(f"  Status:  {status_path}")
    print(f"  Hook:    {'installed' if hook_path.exists() else 'not found (run agenthud install first)'}")


def remove(cwd: str | None = None) -> None:
    cwd = cwd or os.getcwd()

    # Find agent by working directory
    matched_file = None
    matched_id = None
    if AGENTS_DIR.exists():
        for path in AGENTS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("workingDirectory") == cwd:
                    matched_file = path
                    matched_id = data.get("id")
                    break
            except (json.JSONDecodeError, OSError):
                continue

    if not matched_file:
        print("No AgentHUD session registered for this directory.")
        return

    # Delete status file
    matched_file.unlink()

    # Clean up settings.local.json
    settings_path = Path(cwd) / ".claude" / "settings.local.json"
    if settings_path.exists():
        settings = _read_settings(settings_path)

        # Remove hook entries
        hooks = settings.get("hooks", {})
        post_tool_use = hooks.get("PostToolUse", [])
        post_tool_use = [
            h for h in post_tool_use
            if "post-tool-use.sh" not in h.get("command", "")
        ]
        if post_tool_use:
            hooks["PostToolUse"] = post_tool_use
        else:
            hooks.pop("PostToolUse", None)
        if not hooks:
            settings.pop("hooks", None)
        else:
            settings["hooks"] = hooks

        # Remove system prompt
        prompt = settings.get("systemPrompt", "")
        if "AgentHUD" in prompt:
            # Remove the AgentHUD paragraph
            lines = prompt.split("\n\n")
            lines = [l for l in lines if "AgentHUD" not in l]
            cleaned = "\n\n".join(lines).strip()
            if cleaned:
                settings["systemPrompt"] = cleaned
            else:
                settings.pop("systemPrompt", None)

        _write_settings(settings_path, settings)

    print(f"AgentHUD: Session unregistered.")
    print(f"  Removed: {matched_file}")
    print(f"  Hook:    removed")
