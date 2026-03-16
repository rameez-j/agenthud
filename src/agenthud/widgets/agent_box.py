from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Rule

from agenthud.models import AgentStatus, TaskItem


class AgentBox(Widget):
    can_focus = True

    DEFAULT_CSS = """
    AgentBox {
        layout: vertical;
        border: solid yellow;
        border-title-color: yellow;
        border-title-style: bold;
        border-subtitle-color: $text-muted;
        height: auto;
        min-height: 10;
        padding: 1 2;
    }
    AgentBox:focus {
        border: double yellow;
    }

    AgentBox .header-row {
        height: 1;
    }
    AgentBox .header-indicator {
        width: auto;
    }
    AgentBox .header-meta {
        width: 1fr;
        text-align: right;
        color: $text-muted;
    }

    AgentBox .section-rule {
        margin: 1 0 0 0;
        color: $foreground 40%;
    }
    AgentBox .section-heading {
        color: $text-muted;
        text-style: bold;
        margin-top: 1;
    }

    AgentBox .status-current {
        text-style: bold;
        color: $text;
    }
    AgentBox .status-past {
        color: $text-muted;
    }

    AgentBox .action-item {
        color: $text-muted;
    }

    AgentBox .task-item {
        color: $text;
    }
    AgentBox .task-completed {
        color: $text-muted;
    }
    AgentBox .task-overflow {
        color: $text-muted;
        text-style: italic;
    }

    AgentBox .statusbar {
        color: $text-muted;
        margin-top: 1;
    }

    AgentBox.asking {
        border: solid #ff8c00;
        border-title-color: #ff8c00;
    }

    AgentBox.done {
        border: solid green;
        border-title-color: green;
    }

    """

    STATE_CLASSES = ("asking", "done")

    def __init__(self, agent: AgentStatus) -> None:
        super().__init__()
        self.agent = agent
        self.agent_id = agent.id
        self._apply_state_class(agent)

    def compose(self) -> ComposeResult:
        agent = self.agent

        self.border_title = agent.name
        self.border_subtitle = f"{agent.heartbeat_ago} ago"

        # ── Header: indicator + repo/branch + uptime ──
        if agent.state == "asking":
            indicator = "[#ff8c00]● Needs input[/#ff8c00]"
        elif agent.state == "done":
            indicator = "[green]● Done[/green]"
        else:
            indicator = "[yellow]● Working[/yellow]"

        meta_parts = [f"{agent.repo} / {agent.branch}"]
        if agent.ticket_id:
            meta_parts.append(agent.ticket_id)
        meta_parts.append(f"⏱ {agent.uptime_display}")

        yield Horizontal(
            Static(indicator, classes="header-indicator"),
            Static("  ".join(meta_parts), classes="header-meta"),
            classes="header-row",
        )

        # ── Section: Status ──
        yield Rule(classes="section-rule")
        yield Static("[bold]Status[/bold]", classes="section-heading")
        history = list(reversed(agent.status_history[:4]))
        for entry in history:
            ago = self._time_ago(entry)
            ts = f"[dim]{ago:<8}[/dim]" if ago else ""
            yield Static(f"  {ts} [dim]{entry.text}[/dim]", classes="status-past")
        yield Static(f"  ▸ {agent.display_status}", classes="status-current")

        # ── Section: Activity ──
        if agent.recent_actions:
            yield Rule(classes="section-rule")
            yield Static("[bold]Activity[/bold]", classes="section-heading")
            for action in agent.recent_actions[:5]:
                ago = self._action_time_ago(action)
                yield Static(f"  [dim]{ago:<8}[/dim] {action.summary}", classes="action-item")

        # ── Section: Tasks ──
        if agent.tasks:
            total = len(agent.tasks)
            done = sum(1 for t in agent.tasks if t.status == "completed")
            yield Rule(classes="section-rule")
            yield Static(f"[bold]Tasks ({done}/{total})[/bold]", classes="section-heading")
            display_tasks = agent.tasks[:5]
            for task in display_tasks:
                cls = "task-completed" if task.status == "completed" else "task-item"
                yield Static(self._render_task(task), classes=cls)
            remaining = total - len(display_tasks)
            if remaining > 0:
                yield Static(f"  +{remaining} more", classes="task-overflow")

        # ── Statusbar: metrics ──
        statusbar = self._build_statusbar(agent)
        if statusbar:
            yield Rule(classes="section-rule")
            yield Static(statusbar, classes="statusbar")

    @staticmethod
    def _build_statusbar(agent: AgentStatus) -> str:
        parts = []

        # Mode
        if agent.state == "asking":
            parts.append("[#ff8c00]needs input[/#ff8c00]")
        elif agent.state == "done":
            parts.append("[green]done[/green]")
        else:
            parts.append("[yellow]working[/yellow]")

        # Context window
        if agent.context_pct is not None and agent.context_pct > 0:
            pct = int(agent.context_pct)
            bar_width = 10
            filled = pct * bar_width // 100
            empty = bar_width - filled
            if pct >= 85:
                color = "red"
            elif pct >= 60:
                color = "yellow"
            else:
                color = "green"
            bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]"
            parts.append(f"ctx {bar} [{color}]{pct}%[/{color}]")

        # Cost
        if agent.cost_usd is not None and agent.cost_usd > 0:
            parts.append(f"[green]${agent.cost_usd:.2f}[/green]")

        # Git diff
        if agent.git_added or agent.git_removed:
            diff_parts = []
            if agent.git_added:
                diff_parts.append(f"[green]+{agent.git_added}[/green]")
            if agent.git_removed:
                diff_parts.append(f"[red]-{agent.git_removed}[/red]")
            parts.append(" ".join(diff_parts))

        return "  │  ".join(parts) if parts else ""

    @staticmethod
    def _time_ago(status) -> str:
        if not status.updated_at:
            return ""
        delta = (datetime.now(timezone.utc) - status.updated_at).total_seconds()
        if delta < 60:
            return f"{int(delta)}s ago"
        minutes = int(delta) // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        return f"{hours}h ago"

    @staticmethod
    def _action_time_ago(action) -> str:
        if not action.timestamp:
            return ""
        delta = (datetime.now(timezone.utc) - action.timestamp).total_seconds()
        if delta < 60:
            return f"{int(delta)}s ago"
        minutes = int(delta) // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        return f"{hours}h ago"

    @staticmethod
    def _render_task(task: TaskItem) -> str:
        icons = {
            "completed": "[green]✓[/green]",
            "in_progress": "[yellow]▸[/yellow]",
            "pending": "[dim]○[/dim]",
        }
        icon = icons.get(task.status, icons["pending"])
        subject = task.subject[:50] + "..." if len(task.subject) > 50 else task.subject
        if task.status == "completed":
            return f"  {icon} [dim]{subject}[/dim]"
        return f"  {icon} {subject}"

    def _apply_state_class(self, agent: AgentStatus) -> None:
        self.remove_class(*self.STATE_CLASSES)
        if agent.state == "asking":
            self.add_class("asking")
        elif agent.state == "done":
            self.add_class("done")

    def update_agent(self, agent: AgentStatus) -> None:
        self.agent = agent
        self._apply_state_class(agent)
        self.query("Static, Rule, Horizontal").remove()
        for widget in self.compose():
            self.mount(widget)
