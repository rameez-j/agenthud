from __future__ import annotations

import argparse
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer, Static

from agenthud.watcher import AgentWatcher
from agenthud.widgets import AgentBox, EmptyState

AGENTS_DIR = Path.home() / ".agenthud" / "agents"


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
        ("d", "toggle_remove", "Remove"),
        ("down", "focus_next", "Next"),
        ("up", "focus_previous", "Previous"),
        ("j", "focus_next", "Next"),
        ("k", "focus_previous", "Previous"),
        ("J", "move_down", "Move down"),
        ("K", "move_up", "Move up"),
    ]

    def __init__(self):
        super().__init__()
        self.watcher = AgentWatcher(AGENTS_DIR)
        self._agent_boxes: dict[str, AgentBox] = {}
        self._agent_order: list[str] = []

    LEGEND = "[yellow]●[/yellow] Working  [#ff8c00]●[/#ff8c00] Needs input  [green]●[/green] Done  [dim]│  j/k navigate  J/K reorder  d remove[/dim]"

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
            if agent_id in self._agent_order:
                self._agent_order.remove(agent_id)

        # Update existing boxes, add new ones
        for agent_id, agent in agents.items():
            if agent_id in self._agent_boxes:
                self._agent_boxes[agent_id].update_agent(agent)
            else:
                box = AgentBox(agent)
                self._agent_boxes[agent_id] = box
                self._agent_order.append(agent_id)
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

    def action_toggle_remove(self) -> None:
        if getattr(self, "_pending_remove", None) is not None:
            self.action_confirm_remove()
        else:
            self.action_remove_agent()

    def action_remove_agent(self) -> None:
        focused = self.focused
        if isinstance(focused, AgentBox):
            name = focused.agent.name
            self._pending_remove = focused
            self.notify(
                f"Remove {name}? You'll need to restart the Claude Code session to re-add it. Press [b]d[/b] again to confirm.",
                title="Confirm removal",
                timeout=5,
            )

    def _swap_agents(self, direction: int) -> None:
        focused = self.focused
        if not isinstance(focused, AgentBox):
            return
        agent_id = focused.agent_id
        if agent_id not in self._agent_order:
            return
        idx = self._agent_order.index(agent_id)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._agent_order):
            return
        # Swap in order list
        self._agent_order[idx], self._agent_order[new_idx] = (
            self._agent_order[new_idx], self._agent_order[idx],
        )
        # Re-mount all boxes in new order
        grid = self.query_one("#agent-grid", Grid)
        for box in self._agent_boxes.values():
            box.remove()
        for aid in self._agent_order:
            if aid in self._agent_boxes:
                grid.mount(self._agent_boxes[aid])
        # Restore focus
        self._agent_boxes[agent_id].focus()

    def action_move_up(self) -> None:
        self._swap_agents(-1)

    def action_move_down(self) -> None:
        self._swap_agents(1)

    def action_confirm_remove(self) -> None:
        box = getattr(self, "_pending_remove", None)
        if box is None:
            return
        agent_id = box.agent_id
        self.watcher.remove_agent(agent_id)
        self._agent_boxes.pop(agent_id, None)
        if agent_id in self._agent_order:
            self._agent_order.remove(agent_id)
        box.remove()
        self._pending_remove = None
        if not self._agent_boxes:
            self.query_one("#agent-grid", Grid).mount(EmptyState())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agenthud",
        description="TUI dashboard for monitoring Claude Code agent sessions",
    )
    from agenthud import __version__
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Set up hooks and auto-registration")
    sub.add_parser("uninstall", help="Remove hooks and clean up")

    add_parser = sub.add_parser("add", help="Manually register an agent session")
    add_parser.add_argument("--session-id", help="Claude Code session ID")
    add_parser.add_argument("task", nargs="*", help="Initial task description")

    remove_parser = sub.add_parser("remove", help="Manually unregister an agent session")
    remove_parser.add_argument("--session-id", help="Claude Code session ID")

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        app = AgentHudApp()
        app.run()
    elif args.command == "install":
        from agenthud.installer import install
        install()
    elif args.command == "uninstall":
        from agenthud.installer import uninstall
        uninstall()
    elif args.command == "add":
        from agenthud.register import add
        task = " ".join(args.task) if args.task else None
        add(session_id=args.session_id, task=task)
    elif args.command == "remove":
        from agenthud.register import remove
        remove(session_id=args.session_id)


if __name__ == "__main__":
    main()
