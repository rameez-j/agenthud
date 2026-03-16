from __future__ import annotations

import subprocess
from pathlib import Path

from agenthud.models import AgentStatus


class AgentWatcher:
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir

    def scan(self) -> dict[str, AgentStatus]:
        if not self.agents_dir.exists():
            return {}

        agents = {}
        for path in self.agents_dir.glob("*.json"):
            agent = AgentStatus.from_file(path)
            if agent is not None:
                self._enrich_git_diff(agent)
                agents[agent.id] = agent
        return agents

    @staticmethod
    def _enrich_git_diff(agent: AgentStatus) -> None:
        """Compute git diff stats if not already provided by hooks."""
        if agent.git_added or agent.git_removed:
            return
        cwd = agent.working_directory
        if not cwd or not Path(cwd).is_dir():
            return
        try:
            result = subprocess.run(
                ["git", "diff", "--no-ext-diff", "--numstat", "HEAD"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            cached = subprocess.run(
                ["git", "diff", "--no-ext-diff", "--cached", "--numstat"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            added = removed = 0
            for line in (result.stdout + cached.stdout).strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0] != "-":
                    added += int(parts[0])
                    removed += int(parts[1])
            agent.git_added = added
            agent.git_removed = removed
        except (subprocess.SubprocessError, ValueError, OSError):
            pass

    def remove_agent(self, agent_id: str) -> None:
        path = self.agents_dir / f"{agent_id}.json"
        if path.exists():
            path.unlink()
