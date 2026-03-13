import json
from datetime import datetime, timezone
from agenthud.watcher import AgentWatcher


class TestAgentWatcher:
    def test_scan_empty_directory(self, tmp_path):
        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()
        assert agents == {}

    def test_scan_finds_agents(self, tmp_path):
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "123-456",
            "registeredAt": now,
            "lastHeartbeat": now,
            "repo": "myrepo",
            "branch": "main",
            "workingDirectory": "/tmp/work",
            "ticketId": None,
            "status": {"text": "Working", "source": "explicit", "updatedAt": now},
            "recentActions": [],
        }
        (tmp_path / "123-456.json").write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()

        assert "123-456" in agents
        assert agents["123-456"].repo == "myrepo"

    def test_scan_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json")
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "good",
            "registeredAt": now,
            "lastHeartbeat": now,
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": now},
            "recentActions": [],
        }
        (tmp_path / "good.json").write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        agents = watcher.scan()

        assert len(agents) == 1
        assert "good" in agents

    def test_scan_nonexistent_directory(self):
        from pathlib import Path
        watcher = AgentWatcher(Path("/nonexistent/path"))
        agents = watcher.scan()
        assert agents == {}

    def test_remove_agent(self, tmp_path):
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": "123",
            "registeredAt": now,
            "lastHeartbeat": now,
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": now},
            "recentActions": [],
        }
        f = tmp_path / "123.json"
        f.write_text(json.dumps(data))

        watcher = AgentWatcher(tmp_path)
        watcher.remove_agent("123")

        assert not f.exists()
