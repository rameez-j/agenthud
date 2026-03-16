# AgentHUD

A TUI dashboard for monitoring Claude Code agent sessions in real-time.

```
● Working  ● Needs input  ● Done

┌─ Alpha ──────────────────────────────────── 5s ago ────┐
│ ● Working  moonpay-api / feature-branch  ⏱ 1h 23m      │
│ ───────────────────────────────────────────────────────│
│ Status                                                 │
│   12m ago  Investigating auth bug in login flow        │
│   8m ago   Running test suite for payments module      │
│   ▸ Refactoring user service to async                  │
│ ───────────────────────────────────────────────────────│
│ Activity                                               │
│   5s ago   Edited services/user.ts                     │
│   12s ago  Read models/auth.ts                         │
│   30s ago  Searched for 'authenticate'                 │
│ ───────────────────────────────────────────────────────│
│ working  │  ctx ██████░░░░ 60%  │  $4.03  │  +120 -45  │
└────────────────────────────────────────────────────────┘
```

## Why

Running multiple Claude Code agents is a black box. You have no way to know what stage an agent is at without switching terminals and scrolling. AgentHUD gives you a single dashboard showing all your agents at a glance — what they're doing, whether they need your input, and how much context they've used.

## Features

- **Auto-registration** — agents appear on the dashboard automatically when a Claude Code session starts
- **Three-state detection** — yellow (working), orange (needs your input), green (done)
- **Status history** — last 5 status updates with timestamps, so you can see what happened while you were away
- **Context window tracking** — progress bar showing how much context each agent has used
- **Cost tracking** — estimated session cost with model-aware pricing (Opus/Sonnet/Haiku)
- **Git diff stats** — lines added/removed per agent
- **Task tracking** — picks up Claude Code's internal TaskCreate/TaskUpdate
- **Agent names** — NATO phonetic names (Alpha, Bravo, Charlie...) shown in both the dashboard and Claude Code's status bar
- **No server, no database, no ports** — all state lives in `~/.agenthud/agents/` as JSON files

## How it works

AgentHUD uses [Claude Code hooks](https://code.claude.com/docs/en/hooks) to track agent activity:

| Hook                  | Purpose                                                                         |
|-----------------------|---------------------------------------------------------------------------------|
| **SessionStart**      | Auto-registers the agent, assigns a name, injects status reporting instructions |
| **SessionEnd**        | Removes the agent from the dashboard                                            |
| **PostToolUse**       | Updates heartbeat, recent actions, task list                                    |
| **Stop**              | Detects if the agent is done or asking a question (analyzes the response)       |
| **UserPromptSubmit**  | Marks the agent as working when you send a message                              |
| **PermissionRequest** | Marks the agent as needing input when waiting for permission                    |

The dashboard polls `~/.agenthud/agents/*.json` every 2 seconds and renders a responsive grid.

## Installation

Requires Python 3.10+ and [`jq`](https://jqlang.github.io/jq/).

```bash
pipx install agenthud
agenthud install
```

Or from source:

```bash
git clone https://github.com/rameez-j/agenthud.git
cd agenthud
pipx install .
agenthud install
```

### What `agenthud install` does

- Checks that `jq` is available
- Creates `~/.agenthud/agents/` and `~/.agenthud/hooks/`
- Copies hook scripts to `~/.agenthud/hooks/`
- Registers hooks in `~/.claude/settings.json`
- Grants sandbox write access to `~/.agenthud` so agents can update their status
- Sets up the statusline integration (agent names in Claude Code's status bar)

### Statusline integration

If you don't have an existing Claude Code statusline, `agenthud install` sets one up automatically. This shows the agent name (e.g. `[Alpha]`) in each Claude Code session's status bar, making it easy to match terminals to dashboard entries.

If you already have a custom statusline, the installer will skip it and show you how to integrate. Add this to your existing statusline script:

```bash
# AgentHUD: show agent name + sync metrics to dashboard
source ~/.agenthud/hooks/statusline.sh
```

The statusline integration also syncs **context window usage** and **estimated cost** to the dashboard. These metrics are read from the JSON that Claude Code provides to the statusline script — no extra configuration needed. If your statusline doesn't provide this data, the dashboard still works but those fields won't appear.

## Usage

### Open the dashboard

```bash
agenthud
```

Agents appear automatically when you start a Claude Code session. The dashboard adapts to your terminal width (1-3 columns).

### Keyboard shortcuts

| Key     | Action                |
|---------|-----------------------|
| `q`     | Quit                  |
| `d`     | Remove selected agent |
| `↑`/`k` | Previous agent        |
| `↓`/`j` | Next agent            |

### CLI commands

```bash
agenthud              # Launch the dashboard
agenthud install      # Set up hooks and auto-registration
agenthud uninstall    # Remove hooks and clean up
agenthud --version    # Show version
agenthud --help       # Show help
```

### Uninstall

```bash
agenthud uninstall
pipx uninstall agenthud
```

## Agent states

| Color   | State       | Meaning                                    |
|---------|-------------|--------------------------------------------|
| Yellow  | Working     | Agent is actively processing               |
| Orange  | Needs input | Agent asked a question or needs permission |
| Green   | Done        | Agent completed the task                   |

The state detection works by analyzing the agent's last response — if it contains a real question (not a courtesy "let me know if you need anything?"), it shows orange. Otherwise green.

## Project structure

```
agenthud/
  src/agenthud/
    app.py              # Textual app, CLI entry point (argparse)
    models.py           # AgentStatus dataclass, JSON parsing
    watcher.py          # Polls ~/.agenthud/agents/, git diff stats
    installer.py        # install/uninstall, hook registration
    register.py         # Agent registration, NATO name assignment
    widgets/
      agent_box.py      # Agent panel widget (sectioned layout)
      empty_state.py    # Empty state message
  hooks/
    session-start.sh    # Auto-register + inject status instructions
    session-end.sh      # Auto-unregister
    post-tool-use.sh    # Heartbeat, actions, tasks
    stop.sh             # Done vs asking detection
    user-prompt-submit.sh  # Mark as working
    permission-request.sh  # Mark as needs input
  tests/
    test_models.py
    test_watcher.py
```

## Development

```bash
git clone https://github.com/rameez-j/agenthud.git
cd agenthud
pip install -e ".[dev]"
pytest -v
```

## License

MIT
