#!/usr/bin/env bash
# AgentHUD statusline integration
# Source this from your Claude Code statusline script, or use it standalone.
#
# When used standalone, it shows: [AgentName] in the statusline.
# When context_window and token data are available, it also writes
# context % and estimated cost to the agent file for dashboard display.
#
# Input: JSON on stdin (provided by Claude Code)
# Output: Agent name label (to stdout, for statusline display)

input=$(cat)

session_id=$(printf '%s' "$input" | jq -r '.session_id // ""')

if [ -z "$session_id" ]; then
  exit 0
fi

agent_file="$HOME/.agenthud/agents/${session_id}.json"

if [ ! -f "$agent_file" ]; then
  exit 0
fi

# Read agent name for statusline display
agent_name=$(jq -r '.name // empty' "$agent_file" 2>/dev/null)

if [ -n "$agent_name" ]; then
  printf '\033[1;33m[%s]\033[0m' "$agent_name"
fi

# Optional: write context window + cost metrics to agent file
# These fields are provided by Claude Code in the statusline input
used_pct=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')
total_in=$(printf '%s' "$input" | jq -r '.context_window.total_input_tokens // 0')
total_out=$(printf '%s' "$input" | jq -r '.context_window.total_output_tokens // 0')
model=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "unknown"')

if [ -n "$used_pct" ] || [ "$total_in" -gt 0 ] 2>/dev/null; then
  # Model-aware pricing (per million tokens)
  case "$model" in
    *[Oo]pus*)   in_rate=3.00;  out_rate=15.00 ;;
    *[Ss]onnet*) in_rate=1.50;  out_rate=5.00 ;;
    *[Hh]aiku*)  in_rate=0.25;  out_rate=1.25 ;;
    *)           in_rate=3.00;  out_rate=15.00 ;;
  esac
  cost_val=$(awk -v i="$total_in" -v o="$total_out" -v ir="$in_rate" -v or_="$out_rate" \
    'BEGIN { printf "%.4f", (i/1000000)*ir + (o/1000000)*or_ }' 2>/dev/null || echo "0")
  tmp_agent=$(mktemp "$HOME/.agenthud/agents/.tmp.XXXXXX" 2>/dev/null)
  if [ -n "$tmp_agent" ]; then
    jq --argjson pct "${used_pct:-0}" --argjson cost "$cost_val" '
      .contextWindow = {usedPct: $pct} |
      .cost = {estimated: $cost}
    ' "$agent_file" > "$tmp_agent" 2>/dev/null && mv "$tmp_agent" "$agent_file" 2>/dev/null || rm -f "$tmp_agent"
  fi
fi
