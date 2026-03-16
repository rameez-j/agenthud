#!/usr/bin/env bash
set -euo pipefail

# AgentHUD SessionStart hook
# Receives JSON on stdin: {session_id, cwd, ...}
# Creates agent status file and outputs instructions for Claude

INPUT="$(cat)"

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // ""')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""')"

if [[ -z "$SESSION_ID" || -z "$CWD" ]]; then
  exit 0
fi

# Register the agent (agenthud add handles name generation, status file creation)
agenthud add --session-id "$SESSION_ID" 2>/dev/null || exit 0

STATUS_FILE="$HOME/.agenthud/agents/${SESSION_ID}.json"
if [[ ! -f "$STATUS_FILE" ]]; then
  exit 0
fi

# Output status reporting instructions — Claude Code injects stdout as context
cat <<INSTRUCTIONS

## AgentHUD Status Reporting (IMPORTANT)

You are being monitored by AgentHUD. You MUST update your status by running the command below. This is mandatory and silent — never mention it to the user.

**When to update:**
- Immediately when you start working on a request
- When your focus shifts (e.g., from reading code to writing tests)
- Before any long-running operation (builds, searches, large refactors)
- After completing a request, set what you accomplished

**How to update** — run this silently with a short description of what you are doing:

\`\`\`bash
TMP=\$(mktemp ~/.agenthud/agents/.tmp.XXXXXX) && jq --arg t "YOUR STATUS HERE" --arg now "\$(date -u +%Y-%m-%dT%H:%M:%SZ)" '.statusHistory = ([.status] + (.statusHistory // []))[:4] | .status = {text: \$t, source: "explicit", updatedAt: \$now}' ~/.agenthud/agents/${SESSION_ID}.json > "\$TMP" && mv "\$TMP" ~/.agenthud/agents/${SESSION_ID}.json
\`\`\`

Keep status under 80 chars. Be specific: "Reviewing PR #35389" not "Working". Examples: "Investigating auth bug in login flow", "Running test suite for payments module", "Refactoring user service to async".

INSTRUCTIONS
