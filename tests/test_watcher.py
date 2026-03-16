import json
from datetime import datetime, timezone
from pathlib import Path

from agenthud.watcher import AgentWatcher


def _make_agent_data(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "id": "123-456",
        "registeredAt": now,
        "lastHeartbeat": now,
        "repo": "myrepo",
        "branch": "main",
        "workingDirectory": "/tmp/nonexistent",
        "ticketId": None,
        "status": {"text": "Working", "source": "explicit", "updatedAt": now},
        "state": "working",
        "recentActions": [],
        "tasks": [],
        "statusHistory": [],
    }
    data.update(overrides)
    return data


class TestAgentWatcher:
    def test_scan_empty_directory(self, tmp_path):
        watcher = AgentWatcher(tmp_path)
        assert watcher.scan() == {}

    def test_scan_nonexistent_directory(self):
        watcher = AgentWatcher(Path("/nonexistent/path"))
        assert watcher.scan() == {}

    def test_scan_finds_agents(self, tmp_path):
        data = _make_agent_data()
        (tmp_path / "123-456.json").write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()

        assert "123-456" in agents
        assert agents["123-456"].repo == "myrepo"

    def test_scan_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json")
        data = _make_agent_data(id="good")
        (tmp_path / "good.json").write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()

        assert len(agents) == 1
        assert "good" in agents

    def test_remove_agent(self, tmp_path):
        data = _make_agent_data(id="123")
        f = tmp_path / "123.json"
        f.write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        watcher.remove_agent("123")

        assert not f.exists()

    def test_remove_nonexistent_agent(self, tmp_path):
        watcher = AgentWatcher(tmp_path)
        watcher.remove_agent("doesnt-exist")  # Should not raise

    def test_scan_multiple_agents(self, tmp_path):
        for name in ["alpha", "bravo", "charlie"]:
            data = _make_agent_data(id=name, repo=f"repo-{name}")
            (tmp_path / f"{name}.json").write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()

        assert len(agents) == 3
        assert agents["bravo"].repo == "repo-bravo"
