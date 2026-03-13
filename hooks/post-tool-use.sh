#!/usr/bin/env bash
set -euo pipefail

# AgentHUD PostToolUse hook
# Receives JSON on stdin: {session_id, cwd, tool_name, tool_input, tool_result}
# Updates ~/.agenthud/agents/<SESSION_ID>.json

AGENTS_DIR="$HOME/.agenthud/agents"

INPUT="$(cat)"

eval "$(printf '%s' "$INPUT" | jq -r '
  @sh "STDIN_SESSION_ID=\(.session_id // "")",
  @sh "CWD=\(.cwd // "")",
  @sh "TOOL_NAME=\(.tool_name // "")"
')"

SESSION_ID="${AGENT_SESSION_ID:-$STDIN_SESSION_ID}"
TOOL_INPUT="$(printf '%s' "$INPUT" | jq -c '.tool_input // {}')"

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATUS_FILE="$AGENTS_DIR/${SESSION_ID}.json"
if [[ ! -f "$STATUS_FILE" ]]; then
  exit 0
fi

REPO="$(basename "${CWD:-unknown}")"
BRANCH="$(git -C "${CWD:-.}" branch --show-current 2>/dev/null || echo "unknown")"

case "$TOOL_NAME" in
  Edit)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Edited ${FILEPATH##*/}"
    ;;
  Write)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Created ${FILEPATH##*/}"
    ;;
  Read)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    SUMMARY="Read ${FILEPATH##*/}"
    ;;
  Bash)
    CMD="$(printf '%s' "$TOOL_INPUT" | jq -r '.command // ""')"
    SUMMARY="Ran: ${CMD:0:60}"
    ;;
  Grep)
    PATTERN="$(printf '%s' "$TOOL_INPUT" | jq -r '.pattern // ""')"
    SUMMARY="Searched for '${PATTERN:0:60}'"
    ;;
  Glob)
    PATTERN="$(printf '%s' "$TOOL_INPUT" | jq -r '.pattern // ""')"
    SUMMARY="Searched files '${PATTERN:0:60}'"
    ;;
  Agent)
    DESC="$(printf '%s' "$TOOL_INPUT" | jq -r '.description // ""')"
    SUMMARY="Launched subagent: ${DESC:0:60}"
    ;;
  Skill)
    SKILL="$(printf '%s' "$TOOL_INPUT" | jq -r '.skill // ""')"
    SUMMARY="Invoked skill: ${SKILL:0:60}"
    ;;
  TaskUpdate)
    ACTIVE_FORM="$(printf '%s' "$TOOL_INPUT" | jq -r '.activeForm // ""')"
    SUMMARY="Updated task"
    ;;
  *)
    SUMMARY="$TOOL_NAME"
    ;;
esac

NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

NEW_ACTION="$(jq -nc --arg ts "$NOW" --arg tool "$TOOL_NAME" --arg summary "$SUMMARY" \
  '{timestamp: $ts, tool: $tool, summary: $summary}')"

TEMP_FILE="$(mktemp "$AGENTS_DIR/.tmp.XXXXXX")"
trap 'rm -f "$TEMP_FILE"' EXIT

# Update status file:
# - Always update heartbeat, repo, branch, recent actions
# - If tool is TaskUpdate with activeForm AND current status source is not "explicit",
#   update status to task-derived
# - If current status source is "tool", update to latest action summary
jq --argjson action "$NEW_ACTION" --arg hb "$NOW" \
  --arg repo "$REPO" --arg branch "$BRANCH" --arg cwd "${CWD:-.}" \
  --arg tool_name "$TOOL_NAME" \
  --arg active_form "${ACTIVE_FORM:-}" \
  --arg action_summary "$SUMMARY" '
  .lastHeartbeat = $hb |
  .repo = $repo |
  .branch = $branch |
  .workingDirectory = $cwd |
  .recentActions = ([$action] + .recentActions)[:5] |
  if ($tool_name == "TaskUpdate" and $active_form != "" and .status.source != "explicit")
  then .status = {text: $active_form, source: "task", updatedAt: $hb}
  elif (.status.source == "tool")
  then .status = {text: $action_summary, source: "tool", updatedAt: $hb}
  else .
  end
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
