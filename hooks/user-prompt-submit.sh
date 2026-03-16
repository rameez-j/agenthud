#!/usr/bin/env bash
set -euo pipefail

# AgentHUD UserPromptSubmit hook
# Fires when the user sends a message, meaning the agent is about to start working.
# Sets state to "working" in the agent status file.

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
  .state = "working" |
  .lastHeartbeat = $now
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
