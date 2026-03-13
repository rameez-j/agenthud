from __future__ import annotations

import shutil
from pathlib import Path


AGENTHUD_DIR = Path.home() / ".agenthud"
AGENTS_DIR = AGENTHUD_DIR / "agents"
HOOKS_DIR = AGENTHUD_DIR / "hooks"
SKILLS_DIR = Path.home() / ".claude" / "skills"


def _find_data_dir() -> Path:
    """Find the data directory containing hooks/ and skills/.

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
        "Could not find hooks/ and skills/ directories. "
        "Reinstall with: pipx install . or pip install -e ."
    )


def install() -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    data_dir = _find_data_dir()

    # Copy hook
    hook_src = data_dir / "hooks" / "post-tool-use.sh"
    hook_dst = HOOKS_DIR / "post-tool-use.sh"
    if hook_src.exists():
        shutil.copy2(hook_src, hook_dst)
        hook_dst.chmod(0o755)
        print(f"  Hook installed: {hook_dst}")
    else:
        print(f"  Warning: hook not found at {hook_src}")

    # Symlink skills
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skills_src = data_dir / "skills"
    for skill_dir in skills_src.iterdir():
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
