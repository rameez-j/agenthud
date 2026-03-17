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

# Extract the last paragraph (after the last blank line) and strip code blocks.
# This is where an actual question to the user would be — not buried in code or URLs.
LAST_PARA="$(printf '%s' "$LAST_MSG" | sed -E '
  /^```/,/^```/d
  /^`[^`]+`$/d
' | awk '
  BEGIN { para="" }
  /^[[:space:]]*$/ { para=""; next }
  { para = para " " $0 }
  END { print para }
')"

# Strip courtesy questions that don't need a response
CLEANED="$(printf '%s' "$LAST_PARA" | sed -E '
  s/[Ll]et me know if (you )?(need|want|have) [^?]*\?//g
  s/[Ww]ould you like me to [^?]*\?//g
  s/[Dd]oes that (help|make sense|work|look good)[^?]*\?//g
  s/[Aa]nything else[^?]*\?//g
  s/[Ss]hall I [^?]*\?//g
  s/[Ww]ant me to [^?]*\?//g
  s/[Mm]ake sense\?//g
  s/[Ss]ound good\?//g
  s/[Hh]ow does that (sound|look)\?//g
  s/[Rr]eady to [^?]*\?//g
  s/[Ii]s there anything [^?]*\?//g
  s/[Dd]o you want [^?]*\?//g
  s/[Cc]an I [^?]*\?//g
')"

# Strip URLs (contain ?) before checking
CLEANED="$(printf '%s' "$CLEANED" | sed -E 's|https?://[^ ]*\?[^ ]*||g')"

# Check if the cleaned last paragraph still contains a real question
if printf '%s' "$CLEANED" | grep -q '?'; then
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
