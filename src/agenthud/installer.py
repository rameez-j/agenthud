from __future__ import annotations

import shutil
from pathlib import Path


AGENTHUD_DIR = Path.home() / ".agenthud"
AGENTS_DIR = AGENTHUD_DIR / "agents"
HOOKS_DIR = AGENTHUD_DIR / "hooks"
SKILLS_DIR = Path.home() / ".claude" / "skills"

# Resolve paths relative to package
PACKAGE_DIR = Path(__file__).parent.parent.parent
HOOKS_SRC = PACKAGE_DIR / "hooks"
SKILLS_SRC = PACKAGE_DIR / "skills"


def install() -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy hook
    hook_src = HOOKS_SRC / "post-tool-use.sh"
    hook_dst = HOOKS_DIR / "post-tool-use.sh"
    if hook_src.exists():
        shutil.copy2(hook_src, hook_dst)
        hook_dst.chmod(0o755)
        print(f"  Hook installed: {hook_dst}")
    else:
        print(f"  Warning: hook not found at {hook_src}")

    # Symlink skills
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    for skill_dir in SKILLS_SRC.iterdir():
        if skill_dir.is_dir():
            link = SKILLS_DIR / skill_dir.name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(skill_dir)
            print(f"  Skill linked: {link} -> {skill_dir}")

    print("\nAgentHUD installed successfully.")
    print("  Run /agenthud add in a Claude Code session to register.")
    print("  Run agenthud in a terminal to open the dashboard.")


def uninstall() -> None:
    # Remove hook
    hook = HOOKS_DIR / "post-tool-use.sh"
    if hook.exists():
        hook.unlink()
        print(f"  Removed hook: {hook}")

    # Remove skill symlinks
    for name in ["agenthud-add", "agenthud-remove"]:
        link = SKILLS_DIR / name
        if link.is_symlink():
            link.unlink()
            print(f"  Removed skill: {link}")

    print("\nAgentHUD uninstalled.")
    print("  Agent status files in ~/.agenthud/agents/ were preserved.")
    print("  Run pipx uninstall agenthud to remove the CLI.")
