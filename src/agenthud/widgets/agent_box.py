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
        border: solid $foreground-muted;
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

        for action in agent.recent_actions[:3]:
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
