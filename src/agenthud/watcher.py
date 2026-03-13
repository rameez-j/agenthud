from __future__ import annotations

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
                agents[agent.id] = agent
        return agents

    def remove_agent(self, agent_id: str) -> None:
        path = self.agents_dir / f"{agent_id}.json"
        if path.exists():
            path.unlink()
