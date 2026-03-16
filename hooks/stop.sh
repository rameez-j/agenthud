#!/usr/bin/env bash
set -euo pipefail

# AgentHUD Stop hook
# Fires when the agent finishes its turn.
# Sets state to "asking" (has question) or "done" (completed task).

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
LAST_MSG="$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // ""')"

# Strip common courtesy questions that don't actually need a response
CLEANED_MSG="$(printf '%s' "$LAST_MSG" | sed -E '
  s/[Ll]et me know if (you )?(need|want|have) .*\?//g
  s/[Ww]ould you like me to .*\?//g
  s/[Dd]oes that (help|make sense|work|look good).*\?//g
  s/[Aa]nything else.*\?//g
  s/[Ss]hall I .*\?//g
  s/[Ww]ant me to .*\?//g
  s/[Mm]ake sense\?//g
  s/[Ss]ound good\?//g
')"

# Check if the cleaned message still contains a real question
if printf '%s' "$CLEANED_MSG" | grep -q '?'; then
  STATE="asking"
else
  STATE="done"
fi

TEMP_FILE="$(mktemp "$HOME/.agenthud/agents/.tmp.XXXXXX")"
trap 'rm -f "$TEMP_FILE"' EXIT

jq --arg now "$NOW" --arg state "$STATE" '
  .state = $state |
  .lastHeartbeat = $now
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
