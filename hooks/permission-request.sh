#!/usr/bin/env bash
set -euo pipefail

# AgentHUD PermissionRequest hook
# Fires when the agent is waiting for the user to approve/deny a tool.
# Sets state to "asking" in the agent status file.

INPUT="$(cat)"

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // ""')"

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATUS_FILE="$HOME/.agenthud/agents/${SESSION_ID}.json"
if [[ ! -f "$STATUS_FILE" ]]; then
  exit 0
fi

NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

TEMP_FILE="$(mktemp "$HOME/.agenthud/agents/.tmp.XXXXXX")"
trap 'rm -f "$TEMP_FILE"' EXIT

jq --arg now "$NOW" '
  .state = "asking" |
  .lastHeartbeat = $now
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
