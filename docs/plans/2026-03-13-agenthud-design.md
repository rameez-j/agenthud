# AgentHUD Design

A standalone TUI dashboard that monitors Claude Code agent sessions in real-time.

## Problem

Long-running Claude Code agents (e.g., oneshot ticket execution, complex debugging) are a black box. Users have no way to know what stage an agent is at or what it's currently doing without switching to that terminal and scrolling through output.

## User Flow

1. In any Claude Code session: `/agenthud add`
2. In a separate terminal: `agenthud`
3. Dashboard shows all registered agents with real-time status
4. User never has to manually update status — it's fully autonomous

## Architecture

### File-Based Communication

All state lives in `~/.agenthud/agents/<session-id>.json`. No server process, no database, no ports.

- Agents write status files (via hook + system prompt instruction)
- Dashboard reads status files (via filesystem watcher)
- Atomic writes (temp file + mv) prevent partial reads
- Crash-safe: if dashboard dies, state persists. If agent dies, last status is readable

### Status Resolution (Layered Fallback)

The dashboard shows a single semantic status line per agent. The line is resolved from three sources in priority order:

1. **Explicit** (best) — Agent self-reports via system prompt instruction. Example: "Gathering context for BUEN-1579". Source is the agent writing directly to the status file when its focus changes.
2. **Task-derived** (good) — The PostToolUse hook reads the current in-progress task's `activeForm` field. Example: "Exploring project context". Automatic, no agent effort needed.
3. **Tool action** (baseline) — Last tool call summary. Example: "Edited DisputeEvidenceResolver.ts". Always available.

Every session always shows *something* useful. Sessions with explicit reporting show the best information.

### Autonomous Status Updates

The user never tells the agent to update its status. Two mechanisms ensure autonomy:

- **System prompt injection**: At registration, an instruction is added telling the agent to update its status file when focus changes. The agent does this naturally as part of its workflow.
- **PostToolUse hook**: Runs after every tool call. Handles heartbeat, recent actions, and task-derived status fallback automatically.

## Data Model

### Directory Layout

```
~/.agenthud/
  agents/
    <session-id>.json
  hooks/
    post-tool-use.sh
```

### Agent Status File Schema

```json
{
  "id": "1773161232-97590",
  "registeredAt": "2026-03-13T12:00:00Z",
  "lastHeartbeat": "2026-03-13T12:35:01Z",
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
    {
      "timestamp": "2026-03-13T12:35:01Z",
      "tool": "Edit",
      "summary": "Edited DisputeEvidenceResolver.unit.test.ts"
    }
  ]
}
```

- `status.source`: `"explicit"` | `"task"` | `"tool"` — tracks where the status came from
- `recentActions`: Capped at last 5 entries
- Session ID format: `<unix-timestamp>-<pid>`

## Registration Flow

When the user runs `/agenthud add`:

1. **Collect metadata** — Generate session ID, detect repo/branch/workdir from git, extract ticket ID from branch name (pattern: `[A-Z][A-Z0-9]+-\d+`)
2. **Create status file** — Write initial `~/.agenthud/agents/<id>.json`
3. **Install PostToolUse hook** — Add hook entry to `.claude/settings.local.json`: `AGENT_SESSION_ID=<id> bash ~/.agenthud/hooks/post-tool-use.sh`
4. **Inject system prompt** — Add instruction to `.claude/settings.local.json` telling the agent to autonomously update its status file

Deregistration (`/agenthud remove` or `d` key on dashboard) deletes the status file and removes the hook.

## PostToolUse Hook

`~/.agenthud/hooks/post-tool-use.sh` — runs after every tool call.

### Responsibilities

1. **Update heartbeat** — Set `lastHeartbeat` to current UTC timestamp
2. **Append recent action** — Build one-line summary from tool name/input, prepend to `recentActions`, keep last 5
3. **Task-derived status fallback** — If no explicit status was set recently, derive status from current task `activeForm` or fall back to last tool action summary

### Tool Summary Mapping

| Tool | Summary |
|------|---------|
| Edit/Write | "Edited <filename>" |
| Read | "Read <filename>" |
| Bash | "Ran: <command truncated to 60ch>" |
| Grep | "Searched for '<pattern>'" |
| Agent | "Launched subagent: <description>" |
| Skill | "Invoked skill: <name>" |
| Other | "<ToolName>" |

### Constraints

- Pure bash + jq — no dependencies beyond standard tools
- Atomic writes (temp file + mv)
- Target: <50ms per invocation

## Dashboard TUI

### Tech Stack

Python + Textual framework.

### Layout

Responsive grid of agent boxes:
- Narrow terminal: boxes stack vertically (one column)
- Wide terminal: boxes flow horizontally (2-3 columns, minimum box width ~50 chars)

### Agent Box

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

**Header**: Status dot (● green = active, ○ grey = stale), repo, branch, ticket ID, time since heartbeat
**Body**: Semantic status line (bold), recent actions (↳ prefixed), uptime
**Empty state**: "No agents registered. Run /agenthud add in a Claude Code session to get started."

### Interaction

- Arrow keys: navigate between agent boxes
- `d`: remove/unregister selected agent (with confirmation)
- `q`: quit

### Visual Indicators

- Active (heartbeat < 5 min): green dot, normal styling
- Stale (heartbeat >= 5 min): grey dot, dimmed text

### Data Refresh

- Poll `~/.agenthud/agents/` every 2 seconds via filesystem watcher with polling fallback
- Textual's reactive framework handles re-rendering

## Project Structure

Single repo, two deliverables:

```
agenthud/
  src/agenthud/
    app.py                  # Textual app, layout, keybindings
    widgets/
      agent_box.py          # Single agent panel widget
      empty_state.py        # "No agents registered" message
    models.py               # AgentStatus dataclass, JSON parsing
    watcher.py              # File watcher, polls ~/.agenthud/agents/
  hooks/
    post-tool-use.sh        # PostToolUse hook script
  skills/
    agenthud-add/SKILL.md   # /agenthud add skill
    agenthud-remove/SKILL.md # /agenthud remove skill
  pyproject.toml            # Package config, CLI entry point
```

## Installation

```bash
cd ~/Developer/Personal/agenthud
pipx install .
agenthud install
```

`agenthud install`:
- Creates `~/.agenthud/` and `~/.agenthud/agents/`
- Copies `post-tool-use.sh` to `~/.agenthud/hooks/`
- Symlinks skills into Claude Code's skill discovery path

`agenthud uninstall` reverses the above. `pipx uninstall agenthud` removes the CLI.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Communication | File-based | No server to manage, crash-safe, simple |
| Status source | Layered fallback (explicit > task > tool) | Always useful, best when agent cooperates |
| Status updates | Autonomous (system prompt + hook) | User never has to ask |
| TUI framework | Textual (Python) | Best widget library for dashboard-style TUIs, responsive layout |
| Layout | Responsive grid | Horizontal boxes on wide screens, vertical on narrow |
| Stale threshold | 5 minutes | Generous enough for slow operations |
| Slash commands | `/agenthud add`, `/agenthud remove` | Namespaced, clear |
| Repo location | Standalone at ~/Developer/Personal/agenthud | Self-contained, not coupled to any plugin ecosystem |
