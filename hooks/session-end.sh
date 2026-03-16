#!/usr/bin/env bash
set -euo pipefail

# AgentHUD SessionEnd hook
# Receives JSON on stdin: {session_id, cwd, reason, ...}
# Removes agent status file

INPUT="$(cat)"

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // ""')"

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATUS_FILE="$HOME/.agenthud/agents/${SESSION_ID}.json"
if [[ -f "$STATUS_FILE" ]]; then
  rm -f "$STATUS_FILE"
fi
