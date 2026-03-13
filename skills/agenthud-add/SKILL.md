---
name: agenthud-add
description: Register this agent session with AgentHUD for live monitoring
argument-hint: "[task description]"
---

# AgentHUD Add

Register the current agent session so it appears on the AgentHUD dashboard.

## Instructions

Run this single command:

```bash
agenthud add $ARGUMENTS
```

This handles everything: creates the status file, installs the PostToolUse hook, and injects the system prompt. No further steps needed.
