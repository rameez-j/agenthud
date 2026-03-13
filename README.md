# AgentHUD

A standalone TUI dashboard that monitors Claude Code agent sessions in real-time.

```
┌─ ● moonpay-api ─ rameez-j/buen-1579 ─ BUEN-1579 ──── 30s ─┐
│                                                               │
│  Restoring deleted queue tests and fixing CI                  │
│                                                               │
│  ↳ Edited DisputeEvidenceResolver.unit.test.ts                │
│  ↳ Ran: git push                                              │
│  ↳ Ran: gh pr checks 35389 --repo moonpay/moonpay-api        │
│                                                               │
│  Uptime: 1h 23m                                               │
└───────────────────────────────────────────────────────────────┘
```

## Why

Long-running Claude Code agents are a black box. You have no way to know what stage an agent is at without switching to that terminal and scrolling through output. AgentHUD gives you a single dashboard showing all your agents at a glance.

## How it works

- **No server, no database, no ports.** All state lives in `~/.agenthud/agents/<session-id>.json`.
- A **PostToolUse hook** runs after every tool call, updating heartbeat, recent actions, and status.
- The **dashboard** polls those files every 2 seconds and renders a responsive grid.
- Agents **autonomously report** what they're doing via a system prompt injection — no manual updates needed.

### Status resolution (layered fallback)

Each agent always shows something useful. Status is resolved from three sources in priority order:

1. **Explicit** (best) — Agent self-reports via system prompt. Example: *"Gathering context for BUEN-1579"*
2. **Task-derived** (good) — Derived from the current in-progress task. Example: *"Exploring project context"*
3. **Tool action** (baseline) — Last tool call summary. Example: *"Edited DisputeEvidenceResolver.ts"*

## Installation

Requires Python 3.10+ and `jq`.

```bash
# Clone and install
git clone git@github.com:rameez-j/agenthud.git
cd agenthud
pip install .        # or: pipx install .

# Set up hooks and skills
agenthud install
```

For development:

```bash
pip install -e ".[dev]"
```

### What `agenthud install` does

- Creates `~/.agenthud/agents/` and `~/.agenthud/hooks/`
- Copies the PostToolUse hook to `~/.agenthud/hooks/post-tool-use.sh`
- Symlinks the `/agenthud add` and `/agenthud remove` skills into `~/.claude/skills/`

## Usage

### Register an agent

In any Claude Code session:

```
/agenthud add Implementing auth middleware for BUEN-1579
```

This will:
- Create a status file in `~/.agenthud/agents/`
- Install a PostToolUse hook for automatic heartbeat and action tracking
- Inject a system prompt so the agent autonomously updates its status

### Open the dashboard

In a separate terminal:

```bash
agenthud
```

The dashboard shows all registered agents in a responsive grid that adapts to your terminal width (1-3 columns).

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `d` | Remove selected agent |
| `↑`/`k` | Previous agent |
| `↓`/`j` | Next agent |

### Unregister an agent

In the Claude Code session:

```
/agenthud remove
```

Or press `d` on the dashboard to remove an agent.

### Uninstall

```bash
agenthud uninstall    # Remove hooks and skill symlinks
pip uninstall agenthud  # Remove the CLI
```

## Project structure

```
agenthud/
  src/agenthud/
    app.py              # Textual app, layout, keybindings, CLI entry point
    models.py           # AgentStatus dataclass, JSON parsing
    watcher.py          # File watcher, polls ~/.agenthud/agents/
    installer.py        # install/uninstall commands
    widgets/
      agent_box.py      # Single agent panel widget
      empty_state.py    # "No agents registered" message
  hooks/
    post-tool-use.sh    # PostToolUse hook (bash + jq)
  skills/
    agenthud-add/       # /agenthud add skill
    agenthud-remove/    # /agenthud remove skill
  tests/
    test_models.py      # Data model tests
    test_watcher.py     # File watcher tests
```

## Running tests

```bash
pytest -v
```
