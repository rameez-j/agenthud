---
name: agenthud-add
description: Register this agent session with AgentHUD for live monitoring
argument-hint: "[--name AgentName] [task description]"
---

# AgentHUD Add

Register this agent session with AgentHUD.

## Instructions

Run this exact command and nothing else:

```bash
agenthud add $ARGUMENTS
```

`--name` gives the agent a label (e.g., `--name Alpha`). Auto-generated if omitted.

**IMPORTANT: `agenthud add` is a CLI tool that handles EVERYTHING automatically — status file, hook installation, and CLAUDE.md injection. Do NOT manually create files, edit settings, read configs, or write JSON. Just run the single command above and report its output. Any manual steps will break the registration.**
