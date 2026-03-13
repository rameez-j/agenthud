---
name: agenthud-remove
description: Unregister this agent session from AgentHUD
---

# AgentHUD Remove

Unregister the current agent session from the AgentHUD dashboard.

## Instructions

### 1. Find the agent's status file

Search `~/.agenthud/agents/` for a file whose `workingDirectory` matches the current directory:

```bash
for f in ~/.agenthud/agents/*.json; do
  dir=$(jq -r '.workingDirectory' "$f" 2>/dev/null)
  if [ "$dir" = "$(pwd)" ]; then echo "$f"; fi
done
```

If no match, inform user: "No AgentHUD session registered for this directory." and stop.

### 2. Extract session ID

Read the `id` field from the matched file for cleanup.

### 3. Delete status file

```bash
rm "<STATUS_FILE>"
```

### 4. Remove PostToolUse hook

Read `.claude/settings.local.json`. Remove any entry from `hooks.PostToolUse` whose `command` contains `post-tool-use.sh`.

- If `PostToolUse` array becomes empty, remove `PostToolUse` key
- If `hooks` object becomes empty, remove `hooks` key
- Preserve all other settings

### 5. Clean up system prompt

If `systemPrompt` in `.claude/settings.local.json` contains "AgentHUD", remove the AgentHUD instruction from it. If the systemPrompt becomes empty, remove the key.

### 6. Confirm

```
AgentHUD: Session unregistered.
  Removed: <STATUS_FILE>
  Hook:    removed
```
