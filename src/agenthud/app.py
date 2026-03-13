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
