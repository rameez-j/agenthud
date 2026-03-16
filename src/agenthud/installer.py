from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


AGENTHUD_DIR = Path.home() / ".agenthud"
AGENTS_DIR = AGENTHUD_DIR / "agents"
HOOKS_DIR = AGENTHUD_DIR / "hooks"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"

HOOK_FILES = ["session-start.sh", "session-end.sh", "post-tool-use.sh", "stop.sh", "user-prompt-submit.sh", "permission-request.sh", "statusline.sh"]
STATUSLINE_SCRIPT = AGENTHUD_DIR / "hooks" / "statusline.sh"

HOOK_CONFIG = {
    "SessionStart": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/session-start.sh",
                }
            ]
        }
    ],
    "SessionEnd": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/session-end.sh",
                }
            ]
        }
    ],
    "PostToolUse": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/post-tool-use.sh",
                }
            ]
        }
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/stop.sh",
                }
            ]
        }
    ],
    "UserPromptSubmit": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/user-prompt-submit.sh",
                }
            ]
        }
    ],
    "PermissionRequest": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "bash ~/.agenthud/hooks/permission-request.sh",
                }
            ]
        }
    ],
}


def _find_data_dir() -> Path:
    """Find the data directory containing hooks/.

    Checks two locations:
    1. Bundled package data (pipx install)
    2. Repo root (pip install -e for development)
    """
    # Bundled inside the package (pipx install)
    pkg_data = Path(__file__).parent / "data"
    if (pkg_data / "hooks").exists():
        return pkg_data

    # Development install: repo root
    repo_root = Path(__file__).parent.parent.parent
    if (repo_root / "hooks").exists():
        return repo_root

    raise FileNotFoundError(
        "Could not find hooks/ directory. "
        "Reinstall with: pipx install . or pip install -e ."
    )


def _read_settings() -> dict:
    if CLAUDE_SETTINGS.exists():
        try:
            return json.loads(CLAUDE_SETTINGS.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _write_settings(settings: dict) -> None:
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")


def _check_jq() -> bool:
    try:
        subprocess.run(["jq", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def install() -> None:
    if not _check_jq():
        print("Error: jq is required but not found.")
        print("  Install with: brew install jq (macOS) or apt install jq (Linux)")
        return

    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    data_dir = _find_data_dir()

    # Copy hook scripts
    for hook_file in HOOK_FILES:
        src = data_dir / "hooks" / hook_file
        dst = HOOKS_DIR / hook_file
        if src.exists():
            shutil.copy2(src, dst)
            dst.chmod(0o755)
            print(f"  Hook installed: {dst}")
        else:
            print(f"  Warning: hook not found at {src}")

    # Register hooks in global Claude settings
    settings = _read_settings()
    hooks = settings.setdefault("hooks", {})

    for event, config in HOOK_CONFIG.items():
        existing = hooks.get(event, [])
        # Check if agenthud hook already present
        already_installed = any(
            "~/.agenthud/hooks/" in h.get("command", "")
            for entry in existing
            for h in entry.get("hooks", [])
        )
        if not already_installed:
            existing.extend(config)
            hooks[event] = existing

    settings["hooks"] = hooks

    # Allow sandbox writes to ~/.agenthud so agents can update status directly
    sandbox = settings.setdefault("sandbox", {})
    filesystem = sandbox.setdefault("filesystem", {})
    allow_write = filesystem.get("allowWrite", [])
    if "~/.agenthud" not in allow_write:
        allow_write.append("~/.agenthud")
        filesystem["allowWrite"] = allow_write
    sandbox["filesystem"] = filesystem
    settings["sandbox"] = sandbox

    # Set up statusline integration for agent name display
    existing_statusline = settings.get("statusLine")
    if existing_statusline is None:
        # No statusline configured — install ours as a simple standalone
        settings["statusLine"] = {
            "type": "command",
            "command": f"bash {STATUSLINE_SCRIPT}",
        }
        print("  Statusline installed (agent names + metrics)")
    elif (
        isinstance(existing_statusline, dict)
        and "agenthud" not in existing_statusline.get("command", "")
    ):
        # User has their own statusline — tell them how to integrate
        print(f"  Statusline: existing config detected, skipped.")
        print(f"    To show agent names, add this to your statusline script:")
        print(f"    source ~/.agenthud/hooks/statusline.sh")

    _write_settings(settings)
    print("  Hooks registered in ~/.claude/settings.json")
    print("  Sandbox write access granted for ~/.agenthud")

    print("\nAgentHUD installed successfully.")
    print("  Sessions auto-register when Claude Code starts.")
    print("  Run agenthud in a terminal to open the dashboard.")


def uninstall() -> None:
    # Remove hook scripts
    for hook_file in HOOK_FILES:
        path = HOOKS_DIR / hook_file
        if path.exists():
            path.unlink()
            print(f"  Removed hook: {path}")

    # Remove hooks from global Claude settings
    settings = _read_settings()
    hooks = settings.get("hooks", {})

    for event in HOOK_CONFIG:
        existing = hooks.get(event, [])
        filtered = [
            entry for entry in existing
            if not any(
                "~/.agenthud/hooks/" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        if filtered:
            hooks[event] = filtered
        else:
            hooks.pop(event, None)

    if hooks:
        settings["hooks"] = hooks
    else:
        settings.pop("hooks", None)

    # Remove sandbox allowWrite entry
    sandbox = settings.get("sandbox", {})
    filesystem = sandbox.get("filesystem", {})
    allow_write = filesystem.get("allowWrite", [])
    if "~/.agenthud" in allow_write:
        allow_write.remove("~/.agenthud")
        if allow_write:
            filesystem["allowWrite"] = allow_write
        else:
            filesystem.pop("allowWrite", None)
        if filesystem:
            sandbox["filesystem"] = filesystem
        else:
            sandbox.pop("filesystem", None)
        if sandbox:
            settings["sandbox"] = sandbox
        else:
            settings.pop("sandbox", None)

    # Remove statusline if it's ours
    statusline = settings.get("statusLine", {})
    if isinstance(statusline, dict) and "agenthud" in statusline.get("command", ""):
        settings.pop("statusLine", None)
        print("  Statusline removed")

    _write_settings(settings)
    print("  Hooks removed from ~/.claude/settings.json")

    # Remove old skill symlinks if they exist
    skills_dir = Path.home() / ".claude" / "skills"
    for name in ["agenthud-add", "agenthud-remove"]:
        link = skills_dir / name
        if link.is_symlink():
            link.unlink()
            print(f"  Removed old skill: {link}")

    print("\nAgentHUD uninstalled.")
    print("  Agent status files in ~/.agenthud/agents/ were preserved.")
    print("  Run pipx uninstall agenthud to remove the CLI.")
