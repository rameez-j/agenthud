import json
from datetime import datetime, timezone, timedelta
from agenthud.models import AgentStatus, StatusInfo


def _make_agent_data(**overrides):
    """Helper to create valid agent JSON data with sensible defaults."""
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "id": "123-456",
        "registeredAt": now,
        "lastHeartbeat": now,
        "repo": "myrepo",
        "branch": "main",
        "workingDirectory": "/some/path",
        "ticketId": None,
        "status": {"text": "", "source": "tool", "updatedAt": now},
        "state": "working",
        "recentActions": [],
        "tasks": [],
        "statusHistory": [],
    }
    data.update(overrides)
    return data


class TestAgentStatus:
    def test_from_json_complete(self, tmp_path):
        data = _make_agent_data(
            repo="moonpay-api",
            branch="rameez-j/buen-1579",
            ticketId="BUEN-1579",
            status={
                "text": "Gathering context",
                "source": "explicit",
                "updatedAt": "2026-03-13T12:34:00Z",
            },
            recentActions=[
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Edit",
                    "summary": "Edited file.ts",
                }
            ],
        )
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
        data = _make_agent_data()
        del data["status"]
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)

        assert agent.status.text == ""
        assert agent.status.source == "tool"

    def test_is_stale_within_threshold(self, tmp_path):
        data = _make_agent_data()
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert not agent.is_stale(threshold_seconds=300)

    def test_from_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json")

        assert AgentStatus.from_file(f) is None

    def test_from_file_missing_required_keys(self, tmp_path):
        f = tmp_path / "missing.json"
        f.write_text(json.dumps({"repo": "r"}))

        assert AgentStatus.from_file(f) is None

    def test_display_status_prefers_explicit(self, tmp_path):
        data = _make_agent_data(
            status={
                "text": "Investigating auth bug",
                "source": "explicit",
                "updatedAt": "2026-03-13T12:34:00Z",
            },
            recentActions=[
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Grep",
                    "summary": "Searched for 'authenticate'",
                }
            ],
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "Investigating auth bug"

    def test_display_status_falls_back_to_action(self, tmp_path):
        data = _make_agent_data(
            recentActions=[
                {
                    "timestamp": "2026-03-13T12:35:00Z",
                    "tool": "Edit",
                    "summary": "Edited auth.ts",
                }
            ],
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "Edited auth.ts"

    def test_display_status_no_activity(self, tmp_path):
        data = _make_agent_data()
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.display_status == "(no recent activity)"

    def test_uptime_display(self, tmp_path):
        now = datetime.now(timezone.utc)
        registered = now - timedelta(hours=1, minutes=23)
        data = _make_agent_data(registeredAt=registered.isoformat())
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert "1h" in agent.uptime_display

    def test_heartbeat_ago_display(self, tmp_path):
        data = _make_agent_data()
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert "s" in agent.heartbeat_ago

    def test_state_field(self, tmp_path):
        for state in ["working", "asking", "done"]:
            data = _make_agent_data(state=state)
            f = tmp_path / "agent.json"
            f.write_text(json.dumps(data))
            agent = AgentStatus.from_file(f)
            assert agent.state == state

    def test_state_defaults_to_working(self, tmp_path):
        data = _make_agent_data()
        del data["state"]
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.state == "working"

    def test_status_history(self, tmp_path):
        data = _make_agent_data(
            statusHistory=[
                {"text": "First task", "source": "explicit", "updatedAt": "2026-03-13T12:00:00Z"},
                {"text": "Second task", "source": "explicit", "updatedAt": "2026-03-13T12:10:00Z"},
            ],
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert len(agent.status_history) == 2
        assert agent.status_history[0].text == "First task"

    def test_context_and_cost(self, tmp_path):
        data = _make_agent_data(
            contextWindow={"usedPct": 42.5},
            cost={"estimated": 1.23},
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.context_pct == 42.5
        assert agent.cost_usd == 1.23

    def test_context_and_cost_missing(self, tmp_path):
        data = _make_agent_data()
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.context_pct is None
        assert agent.cost_usd is None

    def test_git_diff(self, tmp_path):
        data = _make_agent_data(
            gitDiff={"added": 100, "removed": 50},
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent.git_added == 100
        assert agent.git_removed == 50

    def test_tasks(self, tmp_path):
        data = _make_agent_data(
            tasks=[
                {"id": "1", "subject": "Fix bug", "status": "completed"},
                {"id": "2", "subject": "Add tests", "status": "in_progress"},
                {"id": "3", "subject": "Deploy", "status": "pending"},
            ],
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert len(agent.tasks) == 3
        assert agent.tasks[0].status == "completed"
        assert agent.tasks[1].subject == "Add tests"

    def test_from_file_malformed_action_entries(self, tmp_path):
        data = _make_agent_data(
            recentActions=[{"summary": "partial entry"}],
        )
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert agent is not None
        assert len(agent.recent_actions) == 1
