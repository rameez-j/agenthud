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
            "Run 'agenthud install' to set up auto-registration,\n"
            "then start a Claude Code session."
        )
