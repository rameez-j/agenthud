#!/usr/bin/env bash
set -euo pipefail

# AgentHUD PostToolUse hook
# Receives JSON on stdin: {session_id, cwd, tool_name, tool_input, tool_response}
# Updates ~/.agenthud/agents/<SESSION_ID>.json

AGENTS_DIR="$HOME/.agenthud/agents"

INPUT="$(cat)"

SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // ""')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""')"
TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""')"
TOOL_INPUT="$(printf '%s' "$INPUT" | jq -c '.tool_input // {}')"
TOOL_RESPONSE="$(printf '%s' "$INPUT" | jq -c '.tool_response // {}')"

if [[ -z "$SESSION_ID" ]]; then
  exit 0
fi

STATUS_FILE="$AGENTS_DIR/${SESSION_ID}.json"
if [[ ! -f "$STATUS_FILE" ]]; then
  exit 0
fi

REPO="$(basename "${CWD:-unknown}")"
BRANCH="$(git -C "${CWD:-.}" branch --show-current 2>/dev/null || echo "unknown")"

_short_path() {
  # Show last 2 path segments (e.g., "src/models.py")
  local p="$1"
  local base dir
  base="$(basename "$p")"
  dir="$(basename "$(dirname "$p")")"
  if [[ "$dir" != "." && "$dir" != "/" ]]; then
    echo "$dir/$base"
  else
    echo "$base"
  fi
}

_is_temp_file() {
  # Detect Claude Code temp files and /tmp/ paths
  local p="$1"
  local base
  base="$(basename "$p")"
  [[ "$base" == toolu_* ]] || [[ "$p" == /tmp/* ]] || [[ "$p" == /private/tmp/* ]]
}

case "$TOOL_NAME" in
  Edit)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    if _is_temp_file "$FILEPATH"; then exit 0; fi
    SUMMARY="Edited $(_short_path "$FILEPATH")"
    ;;
  Write)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    if _is_temp_file "$FILEPATH"; then exit 0; fi
    SUMMARY="Created $(_short_path "$FILEPATH")"
    ;;
  Read)
    FILEPATH="$(printf '%s' "$TOOL_INPUT" | jq -r '.file_path // ""')"
    if _is_temp_file "$FILEPATH"; then exit 0; fi
    SUMMARY="Read $(_short_path "$FILEPATH")"
    ;;
  Bash)
    CMD="$(printf '%s' "$TOOL_INPUT" | jq -r '.command // ""')"
    DESC="$(printf '%s' "$TOOL_INPUT" | jq -r '.description // ""')"
    if [[ -n "$DESC" ]]; then
      SUMMARY="${DESC:0:60}"
    else
      # Extract just the base command for a cleaner summary
      BASE_CMD="$(echo "$CMD" | awk '{print $1}' | sed 's|.*/||')"
      case "$BASE_CMD" in
        gh)     SUMMARY="GitHub CLI: ${CMD:3:55}" ;;
        git)    SUMMARY="Git: ${CMD:4:55}" ;;
        npm|pnpm|yarn) SUMMARY="${BASE_CMD}: ${CMD:${#BASE_CMD}+1:55}" ;;
        pytest|jest|vitest) SUMMARY="Testing: ${CMD:0:55}" ;;
        *)      SUMMARY="Ran: ${CMD:0:55}" ;;
      esac
    fi
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
  TaskCreate)
    TASK_SUBJECT="$(printf '%s' "$TOOL_INPUT" | jq -r '.subject // ""')"
    SUMMARY="Created task: ${TASK_SUBJECT:0:60}"
    ;;
  TaskUpdate)
    TASK_STATUS="$(printf '%s' "$TOOL_INPUT" | jq -r '.status // ""')"
    TASK_SUBJECT="$(printf '%s' "$TOOL_INPUT" | jq -r '.subject // ""')"
    ACTIVE_FORM="$(printf '%s' "$TOOL_INPUT" | jq -r '.activeForm // ""')"
    SUMMARY="Updated task"
    ;;
  mcp__*)
    # MCP tools: mcp__server__tool → "server: tool"
    MCP_PARTS="${TOOL_NAME#mcp__}"
    MCP_SERVER="${MCP_PARTS%%__*}"
    MCP_TOOL="${MCP_PARTS#*__}"
    # Clean up plugin prefixes (e.g., "plugin_linear_linear" → "linear")
    MCP_SERVER="${MCP_SERVER#plugin_}"
    MCP_SERVER="${MCP_SERVER%%_*}"
    SUMMARY="${MCP_SERVER}: ${MCP_TOOL}"
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

# Extract task ID from tool_response for TaskCreate
# tool_response may be a string like "Task #5 created..." or an object
TASK_ID=""
TASK_SUBJECT_FROM_RESPONSE=""
if [[ "$TOOL_NAME" == "TaskCreate" ]]; then
  # tool_response is {"task": {"id": "20", "subject": "..."}}
  TASK_ID="$(printf '%s' "$TOOL_RESPONSE" | jq -r '.task.id // empty' 2>/dev/null || true)"
  TASK_SUBJECT_FROM_RESPONSE="$(printf '%s' "$TOOL_RESPONSE" | jq -r '.task.subject // empty' 2>/dev/null || true)"
  # Use response subject if tool_input didn't have one
  if [[ -z "$TASK_SUBJECT" && -n "$TASK_SUBJECT_FROM_RESPONSE" ]]; then
    TASK_SUBJECT="$TASK_SUBJECT_FROM_RESPONSE"
  fi
elif [[ "$TOOL_NAME" == "TaskUpdate" ]]; then
  TASK_ID="$(printf '%s' "$TOOL_INPUT" | jq -r '.taskId // ""')"
fi

# Update status file:
# - Always update heartbeat, repo, branch, recent actions
# - TaskCreate: append to tasks array
# - TaskUpdate: update existing task status/subject
# - If tool is TaskUpdate with activeForm AND current status source is not "explicit",
#   update status to task-derived
# - If current status source is "tool", update to latest action summary
jq --argjson action "$NEW_ACTION" --arg hb "$NOW" \
  --arg repo "$REPO" --arg branch "$BRANCH" --arg cwd "${CWD:-.}" \
  --arg tool_name "$TOOL_NAME" \
  --arg active_form "${ACTIVE_FORM:-}" \
  --arg action_summary "$SUMMARY" \
  --arg task_id "${TASK_ID:-}" \
  --arg task_subject "${TASK_SUBJECT:-}" \
  --arg task_status "${TASK_STATUS:-}" \
  '
  .state = "working" |
  .lastHeartbeat = $hb |
  .repo = $repo |
  .branch = $branch |
  .workingDirectory = $cwd |
  .recentActions = ([$action] + .recentActions)[:5] |
  # Task list management
  if ($tool_name == "TaskCreate" and $task_id != "")
  then .tasks = ((.tasks // []) + [{id: $task_id, subject: $task_subject, status: "pending"}])
  elif ($tool_name == "TaskUpdate" and $task_id != "")
  then .tasks = ((.tasks // []) | map(
    if .id == $task_id then
      (if $task_status != "" then .status = $task_status else . end) |
      (if $task_subject != "" then .subject = $task_subject else . end)
    else . end
  ) | [.[] | select(.status != "deleted")])
  else .
  end |
  # Status text management with history
  # Only update status for task updates — tool summaries stay in recentActions
  if ($tool_name == "TaskUpdate" and $active_form != "" and .status.source != "explicit")
  then
    .statusHistory = ([.status] + (.statusHistory // []))[:4] |
    .status = {text: $active_form, source: "task", updatedAt: $hb}
  else .
  end
' "$STATUS_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$STATUS_FILE"
