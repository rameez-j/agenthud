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
