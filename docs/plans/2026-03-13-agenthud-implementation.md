# AgentHUD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a TUI dashboard that monitors Claude Code agent sessions in real-time via file-based status updates.

**Architecture:** Python Textual app polls `~/.agenthud/agents/*.json` every 2 seconds and renders a responsive grid of agent boxes. A PostToolUse bash hook writes status files atomically after every tool call. Claude Code skills handle registration and deregistration.

**Tech Stack:** Python 3.10+, Textual, bash + jq (hook), Claude Code skills (markdown)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/agenthud/__init__.py`
- Create: `src/agenthud/app.py`
- Create: `src/agenthud/models.py`
- Create: `src/agenthud/watcher.py`
- Create: `src/agenthud/widgets/__init__.py`
- Create: `src/agenthud/widgets/agent_box.py`
- Create: `src/agenthud/widgets/empty_state.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agenthud"
version = "0.1.0"
description = "TUI dashboard for monitoring Claude Code agent sessions"
requires-python = ">=3.10"
dependencies = [
    "textual>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "textual-dev",
    "pytest",
    "pytest-asyncio",
]

[project.scripts]
agenthud = "agenthud.app:main"
```

**Step 2: Create empty `__init__.py` files**

- `src/agenthud/__init__.py` — empty
- `src/agenthud/widgets/__init__.py` — empty
- `tests/__init__.py` — empty

**Step 3: Create minimal app.py entry point**

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


class AgentHudApp(App):
    TITLE = "AgentHUD"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()


def main():
    app = AgentHudApp()
    app.run()


if __name__ == "__main__":
    main()
```

**Step 4: Install in dev mode and verify**

Run: `cd ~/Developer/Personal/agenthud && pip install -e ".[dev]"`
Run: `agenthud`
Expected: Textual app opens with header showing "AgentHUD" and footer showing "q Quit". Press q to exit.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with minimal Textual app"
```

---

### Task 2: Data Model

**Files:**
- Create: `tests/test_models.py`
- Create: `src/agenthud/models.py`

**Step 1: Write the failing tests**

```python
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
        data = {
            "id": "123",
            "registeredAt": "2026-03-13T10:00:00Z",
            "lastHeartbeat": "2026-03-13T11:23:00Z",
            "repo": "r",
            "branch": "b",
            "workingDirectory": "/p",
            "ticketId": None,
            "status": {"text": "", "source": "tool", "updatedAt": "2026-03-13T11:23:00Z"},
            "recentActions": [],
        }
        f = tmp_path / "agent.json"
        f.write_text(json.dumps(data))

        agent = AgentStatus.from_file(f)
        assert "1h" in agent.uptime_display

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
```

**Step 2: Run tests to verify they fail**

Run: `cd ~/Developer/Personal/agenthud && pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agenthud.models'` (or ImportError for AgentStatus)

**Step 3: Implement models.py**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class StatusInfo:
    text: str = ""
    source: str = "tool"  # "explicit" | "task" | "tool"
    updated_at: Optional[datetime] = None


@dataclass
class RecentAction:
    timestamp: datetime
    tool: str
    summary: str


@dataclass
class AgentStatus:
    id: str
    registered_at: datetime
    last_heartbeat: datetime
    repo: str
    branch: str
    working_directory: str
    ticket_id: Optional[str]
    status: StatusInfo
    recent_actions: list[RecentAction] = field(default_factory=list)
    file_path: Optional[Path] = None

    @classmethod
    def from_file(cls, path: Path) -> Optional["AgentStatus"]:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        status_data = data.get("status", {})
        status = StatusInfo(
            text=status_data.get("text", ""),
            source=status_data.get("source", "tool"),
            updated_at=_parse_dt(status_data.get("updatedAt")),
        )

        actions = []
        for a in data.get("recentActions", []):
            actions.append(
                RecentAction(
                    timestamp=_parse_dt(a["timestamp"]),
                    tool=a["tool"],
                    summary=a["summary"],
                )
            )

        return cls(
            id=data["id"],
            registered_at=_parse_dt(data["registeredAt"]),
            last_heartbeat=_parse_dt(data["lastHeartbeat"]),
            repo=data.get("repo", "unknown"),
            branch=data.get("branch", "unknown"),
            working_directory=data.get("workingDirectory", ""),
            ticket_id=data.get("ticketId"),
            status=status,
            recent_actions=actions,
            file_path=path,
        )

    def is_stale(self, threshold_seconds: int = 300) -> bool:
        now = datetime.now(timezone.utc)
        delta = (now - self.last_heartbeat).total_seconds()
        return delta >= threshold_seconds

    @property
    def display_status(self) -> str:
        if self.status.text:
            return self.status.text
        if self.recent_actions:
            return self.recent_actions[-1].summary
        return "(no recent activity)"

    @property
    def uptime_display(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.registered_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        remaining_mins = minutes % 60
        return f"{hours}h {remaining_mins}m"

    @property
    def heartbeat_ago(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.last_heartbeat
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        return f"{hours}h"


def _parse_dt(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)
```

**Step 4: Run tests to verify they pass**

Run: `cd ~/Developer/Personal/agenthud && pytest tests/test_models.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add src/agenthud/models.py tests/test_models.py
git commit -m "feat: add AgentStatus data model with JSON parsing and display helpers"
```

---

### Task 3: File Watcher

**Files:**
- Create: `tests/test_watcher.py`
- Create: `src/agenthud/watcher.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `cd ~/Developer/Personal/agenthud && pytest tests/test_watcher.py -v`
Expected: FAIL — ImportError

**Step 3: Implement watcher.py**

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `cd ~/Developer/Personal/agenthud && pytest tests/test_watcher.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/agenthud/watcher.py tests/test_watcher.py
git commit -m "feat: add AgentWatcher for scanning and removing agent status files"
```

---

### Task 4: AgentBox Widget

**Files:**
- Create: `src/agenthud/widgets/agent_box.py`
- Create: `src/agenthud/dashboard.tcss`

**Step 1: Implement the AgentBox widget**

```python
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from agenthud.models import AgentStatus


class AgentBox(Widget):
    can_focus = True

    DEFAULT_CSS = """
    AgentBox {
        layout: vertical;
        border: solid $accent;
        height: auto;
        min-height: 8;
        padding: 1 2;
    }
    AgentBox:focus {
        border: double $accent-lighten-2;
    }
    AgentBox .header {
        text-style: bold;
    }
    AgentBox .status-line {
        text-style: bold;
        color: $text;
        margin: 1 0;
    }
    AgentBox .action {
        color: $text-muted;
    }
    AgentBox .uptime {
        color: $text-muted;
        margin-top: 1;
    }
    AgentBox.stale {
        border: solid $text-muted;
    }
    AgentBox.stale .header {
        color: $text-muted;
    }
    AgentBox.stale .status-line {
        color: $text-muted;
    }
    """

    def __init__(self, agent: AgentStatus) -> None:
        super().__init__()
        self.agent = agent
        self.agent_id = agent.id
        if agent.is_stale():
            self.add_class("stale")

    def compose(self) -> ComposeResult:
        agent = self.agent
        dot = "●" if not agent.is_stale() else "○"
        color = "green" if not agent.is_stale() else ""
        ticket = f" ─ {agent.ticket_id}" if agent.ticket_id else ""
        heartbeat = agent.heartbeat_ago
        heartbeat_label = "stale" if agent.is_stale() else heartbeat

        header = f"[{color}]{dot}[/] {agent.repo} ─ {agent.branch}{ticket} ── {heartbeat_label}"
        yield Static(header, classes="header")
        yield Static(agent.display_status, classes="status-line")

        for action in agent.recent_actions[-3:]:
            yield Static(f"  ↳ {action.summary}", classes="action")

        yield Static(f"Uptime: {agent.uptime_display}", classes="uptime")

    def update_agent(self, agent: AgentStatus) -> None:
        self.agent = agent
        was_stale = self.has_class("stale")
        is_stale = agent.is_stale()
        if is_stale and not was_stale:
            self.add_class("stale")
        elif not is_stale and was_stale:
            self.remove_class("stale")
        self.query(Static).remove()
        for widget in self.compose():
            self.mount(widget)
```

**Step 2: Create the EmptyState widget**

```python
# src/agenthud/widgets/empty_state.py
from textual.widget import Widget
from textual.app import ComposeResult
from textual.widgets import Static


class EmptyState(Widget):
    DEFAULT_CSS = """
    EmptyState {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }
    EmptyState Static {
        text-align: center;
        color: $text-muted;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "No agents registered.\n\n"
            "Run /agenthud add in a Claude Code session to get started."
        )
```

**Step 3: Update widgets/__init__.py**

```python
from agenthud.widgets.agent_box import AgentBox
from agenthud.widgets.empty_state import EmptyState

__all__ = ["AgentBox", "EmptyState"]
```

**Step 4: Verify import works**

Run: `cd ~/Developer/Personal/agenthud && python -c "from agenthud.widgets import AgentBox, EmptyState; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add src/agenthud/widgets/
git commit -m "feat: add AgentBox and EmptyState widgets"
```

---

### Task 5: Main App with Polling and Responsive Grid

**Files:**
- Modify: `src/agenthud/app.py`

**Step 1: Implement the full app**

```python
from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer

from agenthud.models import AgentStatus
from agenthud.watcher import AgentWatcher
from agenthud.widgets import AgentBox, EmptyState

AGENTS_DIR = Path.home() / ".agenthud" / "agents"
STALE_THRESHOLD = 300  # 5 minutes


class AgentHudApp(App):
    TITLE = "AgentHUD"

    CSS = """
    #agent-grid {
        layout: grid;
        grid-size: 1;
        grid-gutter: 1 2;
        padding: 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "remove_agent", "Remove"),
        ("down", "focus_next", "Next"),
        ("up", "focus_previous", "Previous"),
        ("j", "focus_next", "Next"),
        ("k", "focus_previous", "Previous"),
    ]

    def __init__(self):
        super().__init__()
        self.watcher = AgentWatcher(AGENTS_DIR)
        self._agent_boxes: dict[str, AgentBox] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(id="agent-grid")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_agents()
        self.set_interval(2, self._refresh_agents)

    def on_resize(self) -> None:
        grid = self.query_one("#agent-grid", Grid)
        width = self.size.width
        if width < 80:
            grid.styles.grid_size_columns = 1
        elif width < 160:
            grid.styles.grid_size_columns = 2
        else:
            grid.styles.grid_size_columns = 3

    def _refresh_agents(self) -> None:
        agents = self.watcher.scan()
        grid = self.query_one("#agent-grid", Grid)

        # Remove boxes for agents that no longer exist
        removed_ids = set(self._agent_boxes.keys()) - set(agents.keys())
        for agent_id in removed_ids:
            box = self._agent_boxes.pop(agent_id)
            box.remove()

        # Update existing boxes, add new ones
        for agent_id, agent in agents.items():
            if agent_id in self._agent_boxes:
                self._agent_boxes[agent_id].update_agent(agent)
            else:
                box = AgentBox(agent)
                self._agent_boxes[agent_id] = box
                grid.mount(box)

        # Handle empty state
        empty = self.query("EmptyState")
        if not agents and not empty:
            grid.mount(EmptyState())
        elif agents and empty:
            empty.first().remove()

    def action_remove_agent(self) -> None:
        focused = self.focused
        if isinstance(focused, AgentBox):
            agent_id = focused.agent_id
            self.watcher.remove_agent(agent_id)
            self._agent_boxes.pop(agent_id, None)
            focused.remove()
            # Show empty state if no agents left
            if not self._agent_boxes:
                self.query_one("#agent-grid", Grid).mount(EmptyState())


def main():
    app = AgentHudApp()
    app.run()


if __name__ == "__main__":
    main()
```

**Step 2: Test manually with fixture data**

Run: `mkdir -p ~/.agenthud/agents`

Create a test fixture:
```bash
cat > ~/.agenthud/agents/test-1.json << 'EOF'
{
  "id": "test-1",
  "registeredAt": "2026-03-13T10:00:00Z",
  "lastHeartbeat": "2026-03-13T12:34:00Z",
  "repo": "moonpay-api",
  "branch": "rameez-j/buen-1579",
  "workingDirectory": "/Users/rjhaveri/Developer/worktrees/rameez-j-buen-1579",
  "ticketId": "BUEN-1579",
  "status": {
    "text": "Restoring deleted queue tests and fixing CI",
    "source": "explicit",
    "updatedAt": "2026-03-13T12:34:00Z"
  },
  "recentActions": [
    {"timestamp": "2026-03-13T12:33:00Z", "tool": "Edit", "summary": "Edited DisputeEvidenceResolver.unit.test.ts"},
    {"timestamp": "2026-03-13T12:33:30Z", "tool": "Bash", "summary": "Ran: pnpm test --maxWorkers=1"},
    {"timestamp": "2026-03-13T12:34:00Z", "tool": "Bash", "summary": "Ran: git push"}
  ]
}
EOF
```

Run: `agenthud`
Expected: Dashboard shows one agent box with green dot, status line, recent actions, uptime. Arrow keys do nothing (only one box). Press `d` to remove it — box disappears, empty state shows. Press `q` to exit.

**Step 3: Test responsive layout**

Resize terminal to be narrow (<80 cols), medium (80-160), and wide (>160). Verify boxes reflow from 1 to 2 to 3 columns.

**Step 4: Commit**

```bash
git add src/agenthud/app.py
git commit -m "feat: main dashboard app with polling, responsive grid, and agent removal"
```

---

### Task 6: PostToolUse Hook

**Files:**
- Create: `hooks/post-tool-use.sh`

**Step 1: Implement the hook**

```bash
#!/usr/bin/env bash
set -euo pipefail

# AgentHUD PostToolUse hook
# Receives JSON on stdin: {session_id, cwd, tool_name, tool_input, tool_result}
# Updates ~/.agenthud/agents/<SESSION_ID>.json

AGENTS_DIR="$HOME/.agenthud/agents"

INPUT="$(cat)"

eval "$(printf '%s' "$INPUT" | jq -r '
  @sh "STDIN_SESSION_ID=\(.session_id // "")",
  @sh "CWD=\(.cwd // "")",
  @sh "TOOL_NAME=\(.tool_name // "")"
')"

SESSION_ID="${AGENT_SESSION_ID:-$STDIN_SESSION_ID}"
TOOL_INPUT="$(printf '%s' "$INPUT" | jq -c '.tool_input // {}')"

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATUS_FILE="$AGENTS_DIR/${SESSION_ID}.json"
if [[ ! -f "$STATUS_FILE" ]]; then
  exit 0
fi

REPO="$(basename "${CWD:-unknown}")"
BRANCH="$(git -C "${CWD:-.}" branch --show-current 2>/dev/null || echo "unknown")"

case "$TOOL_NAME" in
  Edit)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Edited ${FILEPATH##*/}"
    ;;
  Write)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Created ${FILEPATH##*/}"
    ;;
  Read)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Read ${FILEPATH##*/}"
    ;;
  Bash)
    CMD="$(printf '%s' "$TOOL_INPUT" | jq -r '.command // ""')"
    SUMMARY="Ran: ${CMD:0:60}"
    ;;
  Grep)
    PATTERN="$(printf '%s' "$TOOL_INPUT" | jq -r '.pattern // ""')"
    SUMMARY="Searched for '${PATTERN:0:60}'"
    ;;
  Glob)
    PATTERN="$(printf '%s' "$TOOL_INPUT" | jq -r '.pattern // ""')"
    SUMMARY="Searched files '${PATTERN:0:60}'"
    ;;
  Agent)
    DESC="$(printf '%s' "$TOOL_INPUT" | jq -r '.description // ""')"
    SUMMARY="Launched subagent: ${DESC:0:60}"
    ;;
  Skill)
    SKILL="$(printf '%s' "$TOOL_INPUT" | jq -r '.skill // ""')"
    SUMMARY="Invoked skill: ${SKILL:0:60}"
    ;;
  TaskUpdate)
    # Extract task activeForm for status fallback
    ACTIVE_FORM="$(printf '%s' "$TOOL_INPUT" | jq -r '.activeForm // ""')"
    SUMMARY="Updated task"
    ;;
  *)
    SUMMARY="$TOOL_NAME"
    ;;
esac

NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

NEW_ACTION="$(jq -nc --arg ts "$NOW" --arg tool "$TOOL_NAME" --arg summary "$SUMMARY" \
  '{timestamp: $ts, tool: $tool, summary: $summary}')"

TEMP_FILE="$(mktemp "$AGENTS_DIR/.tmp.XXXXXX")"
trap 'rm -f "$TEMP_FILE"' EXIT

# Update status file:
# - Always update heartbeat, repo, branch, recent actions
# - If tool is TaskUpdate with activeForm AND current status source is not "explicit",
#   update status to task-derived
# - If current status source is "tool", update to latest action summary
jq --argjson action "$NEW_ACTION" --arg hb "$NOW" \
  --arg repo "$REPO" --arg branch "$BRANCH" --arg cwd "${CWD:-.}" \
  --arg tool_name "$TOOL_NAME" \
  --arg active_form "${ACTIVE_FORM:-}" \
  --arg action_summary "$SUMMARY" '
  .lastHeartbeat = $hb |
  .repo = $repo |
  .branch = $branch |
  .workingDirectory = $cwd |
  .recentActions = ([$action] + .recentActions)[:5] |
  if ($tool_name == "TaskUpdate" and $active_form != "" and .status.source != "explicit")
  then .status = {text: $active_form, source: "task", updatedAt: $hb}
  elif (.status.source == "tool")
  then .status = {text: $action_summary, source: "tool", updatedAt: $hb}
  else .
  end
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
```

**Step 2: Make executable**

Run: `chmod +x hooks/post-tool-use.sh`

**Step 3: Test with mock input**

Create a test agent file, then pipe mock stdin:

```bash
mkdir -p ~/.agenthud/agents
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > ~/.agenthud/agents/hook-test.json << EOF
{
  "id": "hook-test",
  "registeredAt": "$NOW",
  "lastHeartbeat": "$NOW",
  "repo": "test",
  "branch": "main",
  "workingDirectory": "$(pwd)",
  "ticketId": null,
  "status": {"text": "", "source": "tool", "updatedAt": "$NOW"},
  "recentActions": []
}
EOF

echo '{"session_id":"hook-test","cwd":"'$(pwd)'","tool_name":"Edit","tool_input":{"file_path":"/tmp/test.ts"},"tool_result":{}}' \
  | AGENT_SESSION_ID=hook-test bash hooks/post-tool-use.sh

cat ~/.agenthud/agents/hook-test.json | jq .
```

Expected: Status file updated with `lastHeartbeat` refreshed, one entry in `recentActions` showing "Edited test.ts", status.text shows "Edited test.ts" with source "tool".

**Step 4: Clean up test fixture**

```bash
rm ~/.agenthud/agents/hook-test.json
```

**Step 5: Commit**

```bash
git add hooks/post-tool-use.sh
git commit -m "feat: add PostToolUse hook for heartbeat, actions, and status fallback"
```

---

### Task 7: `/agenthud add` Skill

**Files:**
- Create: `skills/agenthud-add/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: agenthud-add
description: Register this agent session with AgentHUD for live monitoring
argument-hint: "[task description]"
---

# AgentHUD Add

Register the current agent session so it appears on the AgentHUD dashboard.

**Arguments:** "$ARGUMENTS"

## Instructions

### 1. Ensure directory exists

```bash
mkdir -p ~/.agenthud/agents
```

### 2. Collect session metadata

```bash
pwd
basename "$(pwd)"
git branch --show-current 2>/dev/null || echo "unknown"
echo "$(date +%s)-$$"
```

Store:
- `WORK_DIR` — full working directory
- `REPO` — basename of working directory
- `BRANCH` — current git branch
- `SESSION_ID` — generated unique ID

### 3. Parse arguments

If `$ARGUMENTS` is non-empty, use as `TASK`. Otherwise set to `"Not yet described"`.

Extract ticket ID from `TASK` or `BRANCH` matching pattern `[A-Z][A-Z0-9]+-\d+`. Store first match as `TICKET_ID` or `null`.

### 4. Write initial status file

Create `~/.agenthud/agents/<SESSION_ID>.json`:

```json
{
  "id": "<SESSION_ID>",
  "registeredAt": "<ISO 8601 UTC>",
  "lastHeartbeat": "<ISO 8601 UTC>",
  "repo": "<REPO>",
  "branch": "<BRANCH>",
  "workingDirectory": "<WORK_DIR>",
  "ticketId": "<TICKET_ID or null>",
  "status": {
    "text": "<TASK>",
    "source": "explicit",
    "updatedAt": "<ISO 8601 UTC>"
  },
  "recentActions": []
}
```

### 5. Install PostToolUse hook

Locate the hook:
```bash
ls ~/.agenthud/hooks/post-tool-use.sh
```

If found, update `.claude/settings.local.json` in the current repo:

- Read the file if it exists, otherwise start with `{}`
- Add to `hooks.PostToolUse` array (append if array exists, create if not):
  ```json
  {
    "type": "command",
    "command": "AGENT_SESSION_ID=<SESSION_ID> bash ~/.agenthud/hooks/post-tool-use.sh"
  }
  ```
- Preserve all other settings

### 6. Inject system prompt instruction

In the same `.claude/settings.local.json`, add or update the `systemPrompt` field:

```
You are being monitored by AgentHUD. Autonomously update your status by writing to ~/.agenthud/agents/<SESSION_ID>.json whenever your focus changes. Use: jq --arg t "YOUR STATUS HERE" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '.status = {text: $t, source: "explicit", updatedAt: $now}' ~/.agenthud/agents/<SESSION_ID>.json > /tmp/agenthud-tmp.json && mv /tmp/agenthud-tmp.json ~/.agenthud/agents/<SESSION_ID>.json — Do this when starting a new phase of work. Never ask the user about this. Keep status under 80 characters.
```

### 7. Confirm

```
AgentHUD: Session registered.
  ID:      <SESSION_ID>
  Repo:    <REPO>
  Branch:  <BRANCH>
  Ticket:  <TICKET_ID or none>
  Status:  ~/.agenthud/agents/<SESSION_ID>.json
  Hook:    installed
```
```

**Step 2: Commit**

```bash
git add skills/agenthud-add/
git commit -m "feat: add /agenthud add skill for session registration"
```

---

### Task 8: `/agenthud remove` Skill

**Files:**
- Create: `skills/agenthud-remove/SKILL.md`

**Step 1: Write the skill**

```markdown
---
name: agenthud-remove
description: Unregister this agent session from AgentHUD
---

# AgentHUD Remove

Unregister the current agent session from the AgentHUD dashboard.

## Instructions

### 1. Find the agent's status file

Search `~/.agenthud/agents/` for a file whose `workingDirectory` matches the current directory:

```bash
for f in ~/.agenthud/agents/*.json; do
  dir=$(jq -r '.workingDirectory' "$f" 2>/dev/null)
  if [ "$dir" = "$(pwd)" ]; then echo "$f"; fi
done
```

If no match, inform user: "No AgentHUD session registered for this directory." and stop.

### 2. Extract session ID

Read the `id` field from the matched file for cleanup.

### 3. Delete status file

```bash
rm "<STATUS_FILE>"
```

### 4. Remove PostToolUse hook

Read `.claude/settings.local.json`. Remove any entry from `hooks.PostToolUse` whose `command` contains `post-tool-use.sh`.

- If `PostToolUse` array becomes empty, remove `PostToolUse` key
- If `hooks` object becomes empty, remove `hooks` key
- Preserve all other settings

### 5. Clean up system prompt

If `systemPrompt` in `.claude/settings.local.json` contains "AgentHUD", remove the AgentHUD instruction from it. If the systemPrompt becomes empty, remove the key.

### 6. Confirm

```
AgentHUD: Session unregistered.
  Removed: <STATUS_FILE>
  Hook:    removed
```
```

**Step 2: Commit**

```bash
git add skills/agenthud-remove/
git commit -m "feat: add /agenthud remove skill for session deregistration"
```

---

### Task 9: Install / Uninstall CLI Commands

**Files:**
- Modify: `src/agenthud/app.py`
- Create: `src/agenthud/installer.py`

**Step 1: Implement installer.py**

```python
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
```

**Step 2: Update app.py to support subcommands**

```python
from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer

from agenthud.models import AgentStatus
from agenthud.watcher import AgentWatcher
from agenthud.widgets import AgentBox, EmptyState

AGENTS_DIR = Path.home() / ".agenthud" / "agents"
STALE_THRESHOLD = 300


class AgentHudApp(App):
    TITLE = "AgentHUD"

    CSS = """
    #agent-grid {
        layout: grid;
        grid-size: 1;
        grid-gutter: 1 2;
        padding: 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "remove_agent", "Remove"),
        ("down", "focus_next", "Next"),
        ("up", "focus_previous", "Previous"),
        ("j", "focus_next", "Next"),
        ("k", "focus_previous", "Previous"),
    ]

    def __init__(self):
        super().__init__()
        self.watcher = AgentWatcher(AGENTS_DIR)
        self._agent_boxes: dict[str, AgentBox] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(id="agent-grid")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_agents()
        self.set_interval(2, self._refresh_agents)

    def on_resize(self) -> None:
        grid = self.query_one("#agent-grid", Grid)
        width = self.size.width
        if width < 80:
            grid.styles.grid_size_columns = 1
        elif width < 160:
            grid.styles.grid_size_columns = 2
        else:
            grid.styles.grid_size_columns = 3

    def _refresh_agents(self) -> None:
        agents = self.watcher.scan()
        grid = self.query_one("#agent-grid", Grid)

        removed_ids = set(self._agent_boxes.keys()) - set(agents.keys())
        for agent_id in removed_ids:
            box = self._agent_boxes.pop(agent_id)
            box.remove()

        for agent_id, agent in agents.items():
            if agent_id in self._agent_boxes:
                self._agent_boxes[agent_id].update_agent(agent)
            else:
                box = AgentBox(agent)
                self._agent_boxes[agent_id] = box
                grid.mount(box)

        empty = self.query("EmptyState")
        if not agents and not empty:
            grid.mount(EmptyState())
        elif agents and empty:
            empty.first().remove()

    def action_remove_agent(self) -> None:
        focused = self.focused
        if isinstance(focused, AgentBox):
            agent_id = focused.agent_id
            self.watcher.remove_agent(agent_id)
            self._agent_boxes.pop(agent_id, None)
            focused.remove()
            if not self._agent_boxes:
                self.query_one("#agent-grid", Grid).mount(EmptyState())


def main():
    args = sys.argv[1:]

    if not args:
        app = AgentHudApp()
        app.run()
        return

    command = args[0]

    if command == "install":
        from agenthud.installer import install
        install()
    elif command == "uninstall":
        from agenthud.installer import uninstall
        uninstall()
    else:
        print(f"Unknown command: {command}")
        print("Usage: agenthud [install|uninstall]")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 3: Test install**

Run: `agenthud install`
Expected: Creates directories, copies hook, symlinks skills. Output confirms each step.

**Step 4: Commit**

```bash
git add src/agenthud/installer.py src/agenthud/app.py
git commit -m "feat: add install/uninstall CLI commands"
```

---

### Task 10: End-to-End Test

**Files:** None new — manual integration test

**Step 1: Clean slate**

```bash
rm -rf ~/.agenthud/agents/*
```

**Step 2: Install**

```bash
cd ~/Developer/Personal/agenthud
pip install -e ".[dev]"
agenthud install
```

**Step 3: Open dashboard**

In a separate terminal:
```bash
agenthud
```

Expected: Empty state message shown.

**Step 4: Create test agent fixtures**

In another terminal, create 2-3 fixture JSON files in `~/.agenthud/agents/` with different states (active, stale, various statuses). Within 2 seconds, the dashboard should show them.

**Step 5: Test navigation**

- Arrow keys / j/k between agent boxes — focus border changes
- Press `d` on a box — it disappears
- When all removed — empty state returns

**Step 6: Test responsive layout**

Resize terminal: narrow (1 col) → medium (2 col) → wide (3 col).

**Step 7: Run all unit tests**

Run: `cd ~/Developer/Personal/agenthud && pytest -v`
Expected: All tests pass.

**Step 8: Final commit**

```bash
git add -A
git commit -m "chore: finalize v0.1.0"
```
