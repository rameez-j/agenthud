from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer, Static

from agenthud.watcher import AgentWatcher
from agenthud.widgets import AgentBox, EmptyState

AGENTS_DIR = Path.home() / ".agenthud" / "agents"
STALE_THRESHOLD = 300  # 5 minutes


class AgentHudApp(App):
    TITLE = "AgentHUD"
    SUB_TITLE = "No agents"

    CSS = """
    #legend {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
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

    LEGEND = "[yellow]●[/yellow] Working  [#ff8c00]●[/#ff8c00] Needs input  [green]●[/green] Done"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.LEGEND, id="legend")
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

        # Update subtitle with agent names
        if agents:
            names = [a.name for a in agents.values()]
            self.sub_title = " | ".join(sorted(names))
        else:
            self.sub_title = "No agents"

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
    elif command == "add":
        from agenthud.register import add
        session_id = None
        remaining = args[1:]
        if len(remaining) >= 2 and remaining[0] == "--session-id":
            session_id = remaining[1]
            remaining = remaining[2:]
        task = " ".join(remaining) if remaining else None
        add(session_id=session_id, task=task)
    elif command == "remove":
        from agenthud.register import remove
        session_id = None
        remaining = args[1:]
        if len(remaining) >= 2 and remaining[0] == "--session-id":
            session_id = remaining[1]
            remaining = remaining[2:]
        remove(session_id=session_id)
    else:
        print(f"Unknown command: {command}")
        print("Usage: agenthud [install|uninstall|add|remove]")
        sys.exit(1)


if __name__ == "__main__":
    main()
