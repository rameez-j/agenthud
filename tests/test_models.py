import json
from datetime import datetime, timezone
from agenthud.models import AgentStatus, StatusInfo


class TestAgentStatus:
    def test_from_json_complete(self, tmp_path):
        data = {
            "id": "123-456",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "moonpay-api",
            "branch": "rameez-j/buen-1579",
            "workingDirectory": "/some/path",
            "ticketId": "BUEN-1579",
            "status": {
                "text": "Gathering context",
                "source": "explicit",
                "updatedAt": "2026-03-13T12:34:00Z",
            },
            "recentActions": [
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Edit",
                    "summary": "Edited file.ts",
                }
            ],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)

        assert agent.id == "123-456"
        assert agent.repo == "moonpay-api"
        assert agent.branch == "rameez-j/buen-1579"
        assert agent.ticket_id == "BUEN-1579"
        assert agent.status.text == "Gathering context"
        assert agent.status.source == "explicit"
        assert len(agent.recent_actions) == 1

    def test_from_json_missing_status(self, tmp_path):
        data = {
            "id": "123-456",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "moonpay-api",
            "branch": "main",
            "workingDirectory": "/some/path",
            "ticketId": None,
            "recentActions": [],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)

        assert agent.status.text == ""
        assert agent.status.source == "tool"

    def test_is_stale_within_threshold(self, tmp_path):
        now = datetime.now(timezone.utc)
        data = {
            "id": "123",
            "registeredAt": now.isoformat(),
            "lastHeartbeat": now.isoformat(),
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": now.isoformat()},
            "recentActions": [],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert not agent.is_stale(threshold_seconds=300)

    def test_from_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json")

        agent = AgentStatus.from_file(f)
        assert agent is None

    def test_display_status_prefers_explicit(self, tmp_path):
        data = {
            "id": "123",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {
                "text": "Investigating auth bug",
                "source": "explicit",
                "updatedAt": "2026-03-13T12:34:00Z",
            },
            "recentActions": [
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Grep",
                    "summary": "Searched for 'authenticate'",
                }
            ],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "Investigating auth bug"

    def test_display_status_falls_back_to_tool(self, tmp_path):
        data = {
            "id": "123",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": "2026-03-13T12:35:00Z"},
            "recentActions": [
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Edit",
                    "summary": "Edited auth.ts",
                }
            ],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "Edited auth.ts"

    def test_uptime_display(self, tmp_path):
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        registered = now - timedelta(hours=1, minutes=23)
        data = {
            "id": "123",
            "registeredAt": registered.isoformat(),
            "lastHeartbeat": now.isoformat(),
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": now.isoformat()},
            "recentActions": [],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert "1h" in agent.uptime_display

    def test_display_status_uses_most_recent_action(self, tmp_path):
        data = {
            "id": "123",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": "2026-03-13T12:35:00Z"},
            "recentActions": [
                {"timestamp": "2026-03-13T12:35:00Z", "tool": "Edit", "summary": "Edited newest.ts"},
                {"timestamp": "2026-03-13T12:34:00Z", "tool": "Read", "summary": "Read oldest.ts"},
            ],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "Edited newest.ts"

    def test_from_file_malformed_action_entries(self, tmp_path):
        data = {
            "id": "123",
            "registeredAt": "2026-03-13T12:00:00Z",
            "lastHeartbeat": "2026-03-13T12:35:00Z",
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": "2026-03-13T12:35:00Z"},
            "recentActions": [
                {"summary": "partial entry"},
            ],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent is not None
        assert len(agent.recent_actions) == 1

    def test_from_file_missing_required_keys(self, tmp_path):
        data = {"repo": "r"}
        f = tmp_path / "missing.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent is None

    def test_heartbeat_ago_display(self, tmp_path):
        now = datetime.now(timezone.utc)
        data = {
            "id": "123",
            "registeredAt": now.isoformat(),
            "lastHeartbeat": now.isoformat(),
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": now.isoformat()},
            "recentActions": [],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        display = agent.heartbeat_ago
        assert "s" in display  # Should show seconds
