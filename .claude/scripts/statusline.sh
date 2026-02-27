#!/bin/bash
#
# Claude Code Statusline - Portable version
#
# Displays: model, version, directory, MCPs, Plugins, token usage/cost
#
# DEPENDENCIES:
#   Required:
#     - jq          JSON parsing (install: apt install jq / brew install jq)
#
#   Optional:
#     - ccusage     Token/cost display (install: bun add -g ccusage)
#     - timeout     Cache update timeout (usually pre-installed on Linux)
#     - gtimeout    macOS equivalent (install: brew install coreutils)
#
# CUSTOMIZATION:
#   - Set SIMPLE_COLORS=1 in settings.json env for basic ANSI colors
#     (fixes display issues on some terminals)
#

# Read JSON input from stdin
input=$(cat)

# Extract data from JSON input
current_dir=$(echo "$input" | jq -r '.workspace.current_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')
cc_version=$(echo "$input" | jq -r '.version // "unknown"')
context_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | awk '{printf "%.0f", $1}')

# Get directory name
dir_name=$(basename "$current_dir")

# Get git branch if in a repo
git_branch=""
if git -C "$current_dir" rev-parse --is-inside-work-tree &>/dev/null; then
    git_branch=$(git -C "$current_dir" branch --show-current 2>/dev/null)
fi

# Cache file and lock file for ccusage data
CACHE_FILE="/tmp/.claude_ccusage_cache"
LOCK_FILE="/tmp/.claude_ccusage.lock"
CACHE_AGE=30   # 30 seconds for more real-time updates

# Count MCPs - merge from both local .mcp.json and global ~/.claude.json
mcp_names_raw=""
mcps_count=0

# Collect MCPs from local project .mcp.json
local_mcps=""
if [ -f "$current_dir/.mcp.json" ]; then
    local_mcps=$(jq -r '.mcpServers | keys | join(" ")' "$current_dir/.mcp.json" 2>/dev/null)
fi

# Collect MCPs from global ~/.claude.json
global_mcps=""
if [ -f "$HOME/.claude.json" ]; then
    global_mcps=$(jq -r '.mcpServers | keys | join(" ")' "$HOME/.claude.json" 2>/dev/null)
fi

# Merge and deduplicate MCP names
all_mcps="$local_mcps $global_mcps"
mcp_names_raw=$(echo "$all_mcps" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ' | sed 's/ $//')
mcps_count=$(echo "$mcp_names_raw" | wc -w)

# Count Plugins - merge ENABLED plugins from local and global settings
plugin_names_raw=""
plugins_count=0

# Collect plugins from local project settings
local_plugins=""
PROJECT_SETTINGS="$current_dir/.claude/settings.json"
if [ -f "$PROJECT_SETTINGS" ]; then
    # Extract plugin names (part before @) from enabledPlugins where value is true
    local_plugins=$(jq -r '.enabledPlugins // {} | to_entries | map(select(.value == true)) | .[].key | split("@")[0]' "$PROJECT_SETTINGS" 2>/dev/null | tr '\n' ' ')
fi

# Collect plugins from global ~/.claude/settings.json
global_plugins=""
GLOBAL_SETTINGS="$HOME/.claude/settings.json"
if [ -f "$GLOBAL_SETTINGS" ]; then
    global_plugins=$(jq -r '.enabledPlugins // {} | to_entries | map(select(.value == true)) | .[].key | split("@")[0]' "$GLOBAL_SETTINGS" 2>/dev/null | tr '\n' ' ')
fi

# Merge and deduplicate plugin names
all_plugins="$local_plugins $global_plugins"
plugin_names_raw=$(echo "$all_plugins" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ' | sed 's/ $//')
plugins_count=$(echo "$plugin_names_raw" | wc -w)

# Get cached ccusage data - SAFE VERSION without background processes
daily_tokens=""
daily_cost=""

# Check if cache exists and load it
if [ -f "$CACHE_FILE" ]; then
    source "$CACHE_FILE"
fi

# If cache is stale, missing, or we have no data, update it SYNCHRONOUSLY with timeout
cache_needs_update=false
if [ ! -f "$CACHE_FILE" ] || [ -z "$daily_tokens" ]; then
    cache_needs_update=true
elif [ -f "$CACHE_FILE" ]; then
    # Linux-compatible stat
    cache_age=$(($(date +%s) - $(stat -c%Y "$CACHE_FILE" 2>/dev/null || stat -f%m "$CACHE_FILE" 2>/dev/null || echo 0)))
    if [ $cache_age -ge $CACHE_AGE ]; then
        cache_needs_update=true
    fi
fi

if [ "$cache_needs_update" = true ]; then
    # Try to acquire lock (non-blocking)
    if mkdir "$LOCK_FILE" 2>/dev/null; then
        # We got the lock - update cache with timeout
        if command -v bunx >/dev/null 2>&1; then
            # Run ccusage with a timeout (5 seconds)
            if command -v timeout >/dev/null 2>&1; then
                ccusage_output=$(timeout 5 bunx ccusage 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep "│ Total" | head -1)
            elif command -v gtimeout >/dev/null 2>&1; then
                ccusage_output=$(gtimeout 5 bunx ccusage 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep "│ Total" | head -1)
            else
                # Fallback without timeout
                ccusage_output=$(bunx ccusage 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep "│ Total" | head -1)
            fi

            if [ -n "$ccusage_output" ]; then
                # Extract input/output tokens, removing commas
                daily_input=$(echo "$ccusage_output" | awk -F'│' '{print $4}' | sed 's/[^0-9]//g' | head -c 10)
                daily_output=$(echo "$ccusage_output" | awk -F'│' '{print $5}' | sed 's/[^0-9]//g' | head -c 10)
                # Extract cost, keep the dollar sign
                daily_cost=$(echo "$ccusage_output" | awk -F'│' '{print $9}' | sed 's/^ *//;s/ *$//')

                if [ -n "$daily_input" ] && [ -n "$daily_output" ]; then
                    daily_total=$((daily_input + daily_output))
                    daily_tokens=$(printf "%'d" "$daily_total" 2>/dev/null || echo "$daily_total")

                    # Write to cache file
                    echo "daily_tokens=\"$daily_tokens\"" > "$CACHE_FILE"
                    printf "daily_cost=\"%s\"\n" "${daily_cost//$/\\$}" >> "$CACHE_FILE"
                    echo "cache_updated=\"$(date)\"" >> "$CACHE_FILE"
                fi
            fi
        fi

        # Always remove lock when done
        rmdir "$LOCK_FILE" 2>/dev/null
    else
        # Someone else is updating - check if lock is stale (older than 30 seconds)
        if [ -d "$LOCK_FILE" ]; then
            lock_age=$(($(date +%s) - $(stat -c%Y "$LOCK_FILE" 2>/dev/null || stat -f%m "$LOCK_FILE" 2>/dev/null || echo 0)))
            if [ $lock_age -gt 30 ]; then
                rmdir "$LOCK_FILE" 2>/dev/null
            fi
        fi

        # Just use cached data if available
        if [ -f "$CACHE_FILE" ]; then
            source "$CACHE_FILE"
        fi
    fi
fi

# Read workflow state (create default if missing)
WORKFLOW_STATE_FILE="$current_dir/workflow-state.json"
workflow_phase="idle"
workflow_completed=""
ralph_current=0
ralph_total=0
ralph_current_ticket=""

# Create default workflow-state.json if it doesn't exist
if [ ! -f "$WORKFLOW_STATE_FILE" ]; then
    cat > "$WORKFLOW_STATE_FILE" << 'DEFAULTSTATE'
{
  "phase": "idle",
  "completed": [],
  "ralph": {
    "current": 0,
    "total": 0,
    "current_ticket": ""
  }
}
DEFAULTSTATE
fi

if [ -f "$WORKFLOW_STATE_FILE" ]; then
    workflow_phase=$(jq -r '.phase // "idle"' "$WORKFLOW_STATE_FILE" 2>/dev/null)
    workflow_completed=$(jq -r '.completed // [] | join(" ")' "$WORKFLOW_STATE_FILE" 2>/dev/null)
    ralph_current=$(jq -r '.ralph.current // 0' "$WORKFLOW_STATE_FILE" 2>/dev/null)
    ralph_total=$(jq -r '.ralph.total // 0' "$WORKFLOW_STATE_FILE" 2>/dev/null)
    ralph_current_ticket=$(jq -r '.ralph.current_ticket // ""' "$WORKFLOW_STATE_FILE" 2>/dev/null)
fi

# Tokyo Night Storm Color Scheme (24-bit RGB)
BRIGHT_PURPLE='\033[38;2;187;154;247m'
BRIGHT_BLUE='\033[38;2;122;162;247m'
DARK_BLUE='\033[38;2;100;140;200m'
BRIGHT_GREEN='\033[38;2;158;206;106m'
DARK_GREEN='\033[38;2;130;170;90m'
BRIGHT_CYAN='\033[38;2;125;207;255m'

# Line-specific colors
LINE1_PRIMARY="$BRIGHT_PURPLE"
MODEL_PURPLE='\033[38;2;138;99;210m'

LINE2_PRIMARY="$DARK_BLUE"
LINE2_ACCENT='\033[38;2;110;150;210m'

LINE3_PRIMARY="$DARK_GREEN"
LINE3_ACCENT='\033[38;2;140;180;100m'
COST_COLOR="$LINE3_ACCENT"
CTX_LOW='\033[38;2;158;206;106m'      # Green  (0-59%)
CTX_MED='\033[38;2;224;175;104m'      # Amber  (60-79%)
CTX_HIGH='\033[38;2;247;118;142m'     # Red    (80-100%)
CTX_BAR_BG='\033[38;2;80;80;100m'     # Dim grey for empty bar

SEPARATOR_COLOR='\033[38;2;140;152;180m'
DIR_COLOR='\033[38;2;135;206;250m'

MCP_DEFAULT="$LINE2_PRIMARY"
PLUGIN_COLOR='\033[38;2;255;180;100m'
GIT_BRANCH_COLOR='\033[38;2;255;150;100m'

# Workflow line colors
WORKFLOW_COMPLETED='\033[38;2;158;206;106m'  # Bright green
WORKFLOW_ACTIVE='\033[1;38;2;255;255;255m'   # Bold white
WORKFLOW_PENDING='\033[38;2;100;100;120m'    # Dim grey
WORKFLOW_ARROW='\033[38;2;80;80;100m'        # Darker grey for arrows

RESET='\033[0m\033[49m'

# Simple colors mode - set SIMPLE_COLORS=1 if you have terminal display issues
if [ "${SIMPLE_COLORS:-0}" = "1" ]; then
    BRIGHT_PURPLE='\033[35m'
    BRIGHT_BLUE='\033[34m'
    DARK_BLUE='\033[34m'
    BRIGHT_GREEN='\033[32m'
    DARK_GREEN='\033[32m'
    BRIGHT_CYAN='\033[36m'
    LINE1_PRIMARY='\033[35m'
    MODEL_PURPLE='\033[35m'
    LINE2_PRIMARY='\033[34m'
    LINE2_ACCENT='\033[34m'
    LINE3_PRIMARY='\033[32m'
    LINE3_ACCENT='\033[32m'
    COST_COLOR='\033[32m'
    SEPARATOR_COLOR='\033[37m'
    DIR_COLOR='\033[36m'
    MCP_DEFAULT='\033[34m'
    PLUGIN_COLOR='\033[33m'
    GIT_BRANCH_COLOR='\033[33m'
    CTX_LOW='\033[32m'
    CTX_MED='\033[33m'
    CTX_HIGH='\033[31m'
    CTX_BAR_BG='\033[90m'
    WORKFLOW_COMPLETED='\033[32m'
    WORKFLOW_ACTIVE='\033[1;37m'
    WORKFLOW_PENDING='\033[90m'
    WORKFLOW_ARROW='\033[90m'
fi

# Format MCP names
mcp_names_formatted=""
for mcp in $mcp_names_raw; do
    formatted="${MCP_DEFAULT}${mcp^}${RESET}"

    if [ -z "$mcp_names_formatted" ]; then
        mcp_names_formatted="$formatted"
    else
        mcp_names_formatted="$mcp_names_formatted${SEPARATOR_COLOR}, ${formatted}"
    fi
done

# Format Plugin names
plugin_names_formatted=""
for plugin in $plugin_names_raw; do
    formatted="${PLUGIN_COLOR}${plugin}${RESET}"

    if [ -z "$plugin_names_formatted" ]; then
        plugin_names_formatted="$formatted"
    else
        plugin_names_formatted="$plugin_names_formatted${SEPARATOR_COLOR}, ${formatted}"
    fi
done

# Output the statusline
# LINE 1 - Greeting with version, model, directory, and git branch
git_info=""
if [ -n "$git_branch" ]; then
    git_info=" ${GIT_BRANCH_COLOR}🔱 ${git_branch}${RESET}"
fi
printf "👋 Claude Code v${cc_version} ${MODEL_PURPLE}🧠 ${model_name}${RESET} ${DIR_COLOR}📁 ${dir_name}${RESET}${git_info}\n"

# LINE 2 - MCPs and Plugins
line2_parts=""

if [ -n "$mcp_names_formatted" ]; then
    line2_parts="${LINE2_PRIMARY}🔌 MCPs${RESET}${SEPARATOR_COLOR}: ${RESET}${mcp_names_formatted}"
fi

if [ -n "$plugin_names_formatted" ]; then
    if [ -n "$line2_parts" ]; then
        line2_parts="${line2_parts}  ${SEPARATOR_COLOR}|${RESET}  "
    fi
    line2_parts="${line2_parts}${PLUGIN_COLOR}🧩 Plugins${RESET}${SEPARATOR_COLOR}: ${RESET}${plugin_names_formatted}"
fi

if [ -n "$line2_parts" ]; then
    printf "${line2_parts}${RESET}\n"
fi

# LINE 3 - Tokens and cost
tokens_display="${daily_tokens:-N/A}"
cost_display="${daily_cost:-N/A}"
if [ -z "$daily_tokens" ]; then tokens_display="N/A"; fi
if [ -z "$daily_cost" ]; then cost_display="N/A"; fi

# Build context bar: 10 chars wide, filled proportionally
ctx_color="$CTX_LOW"
if [ "$context_pct" -ge 80 ] 2>/dev/null; then ctx_color="$CTX_HIGH"
elif [ "$context_pct" -ge 60 ] 2>/dev/null; then ctx_color="$CTX_MED"; fi

ctx_filled=$(( (context_pct + 5) / 10 ))  # round to nearest 10th
[ "$ctx_filled" -gt 10 ] && ctx_filled=10
ctx_empty=$(( 10 - ctx_filled ))
ctx_bar="${ctx_color}"
for ((i=0; i<ctx_filled; i++)); do ctx_bar="${ctx_bar}█"; done
ctx_bar="${ctx_bar}${CTX_BAR_BG}"
for ((i=0; i<ctx_empty; i++)); do ctx_bar="${ctx_bar}░"; done

printf "${LINE3_PRIMARY}💎 Tokens${RESET}${SEPARATOR_COLOR}: ${RESET}${LINE3_ACCENT}${tokens_display}${RESET}  ${LINE3_PRIMARY}Cost${RESET}${SEPARATOR_COLOR}: ${RESET}${COST_COLOR}${cost_display}${RESET}  ${LINE3_PRIMARY}Ctx${RESET}${SEPARATOR_COLOR}: ${RESET}${ctx_bar}${RESET} ${ctx_color}${context_pct}%%${RESET}"

# Rate limit info
BLOCK_CACHE_FILE="/tmp/.claude_block_cache"
BLOCK_CACHE_AGE=60

block_messages=""
block_percent=""
block_reset=""

if [ -f "$BLOCK_CACHE_FILE" ]; then
    source "$BLOCK_CACHE_FILE"
fi

block_cache_needs_update=false
if [ ! -f "$BLOCK_CACHE_FILE" ] || [ -z "$block_messages" ]; then
    block_cache_needs_update=true
elif [ -f "$BLOCK_CACHE_FILE" ]; then
    block_cache_age=$(($(date +%s) - $(stat -c%Y "$BLOCK_CACHE_FILE" 2>/dev/null || stat -f%m "$BLOCK_CACHE_FILE" 2>/dev/null || echo 0)))
    if [ $block_cache_age -ge $BLOCK_CACHE_AGE ]; then
        block_cache_needs_update=true
    fi
fi

if [ "$block_cache_needs_update" = true ]; then
    if command -v bunx >/dev/null 2>&1; then
        if command -v timeout >/dev/null 2>&1; then
            block_json=$(timeout 10 bunx ccusage blocks --active --json 2>/dev/null | grep -v "\[ccusage\]")
        else
            block_json=$(bunx ccusage blocks --active --json 2>/dev/null | grep -v "\[ccusage\]")
        fi

        if [ -n "$block_json" ]; then
            block_messages=$(echo "$block_json" | jq -r '.blocks[0].entries // 0')
            block_tokens=$(echo "$block_json" | jq -r '.blocks[0].totalTokens // 0')
            remaining_mins=$(echo "$block_json" | jq -r '.blocks[0].projection.remainingMinutes // 0')

            max_tokens=77000000
            if [ "$block_tokens" -gt 0 ] && [ "$max_tokens" -gt 0 ]; then
                block_percent=$(awk "BEGIN {printf \"%.1f\", ($block_tokens / $max_tokens) * 100}")
            else
                block_percent="0.0"
            fi

            if [ -n "$remaining_mins" ] && [ "$remaining_mins" != "null" ] && [ "$remaining_mins" -gt 0 ]; then
                reset_hrs=$((remaining_mins / 60))
                reset_mins=$((remaining_mins % 60))
                block_reset="${reset_hrs}h ${reset_mins}m"
            else
                block_reset="N/A"
            fi

            echo "block_messages=\"$block_messages\"" > "$BLOCK_CACHE_FILE"
            echo "block_percent=\"$block_percent\"" >> "$BLOCK_CACHE_FILE"
            echo "block_reset=\"$block_reset\"" >> "$BLOCK_CACHE_FILE"
        fi
    fi
fi

if [ -n "$block_messages" ] && [ "$block_messages" != "0" ]; then
    printf "  ${SEPARATOR_COLOR}|${RESET}  📊 ${LINE3_ACCENT}${block_messages}${RESET} msgs, ${LINE3_ACCENT}${block_percent}%%${RESET} used, resets in ${LINE3_ACCENT}${block_reset}${RESET}"
fi
printf "\n"

# LINE 4 - Workflow progress
# Two-section workflow: Plan phases + Execute phases
PLAN_PHASES="discover prd plan ticket"
EXECUTE_PHASES="ralph report review release"

# Helper to check if phase is completed
is_completed() {
    echo " $workflow_completed " | grep -q " $1 "
}

# Helper to generate progress bar
# Args: current, total, has_in_progress (0 or 1)
# Uses: ✓ for completed, ○ for in progress, • for not started
progress_bar() {
    local current=$1
    local total=$2
    local has_in_progress=${3:-0}

    if [ "$total" -eq 0 ]; then
        # No tickets yet - empty bar
        printf "••••••••••"
        return
    fi

    local result=""
    local i

    # Add completed ticks
    for ((i=0; i<current; i++)); do
        result="${result}✓"
    done

    # Add in-progress marker if there is one
    if [ "$has_in_progress" -eq 1 ] && [ "$current" -lt "$total" ]; then
        result="${result}○"
        current=$((current + 1))
    fi

    # Add pending dots
    for ((i=current; i<total; i++)); do
        result="${result}•"
    done

    printf "%s" "$result"
}

# Helper to format a phase
format_phase() {
    local phase=$1
    local display_name

    # Determine phase display name (capitalize)
    case "$phase" in
        prd) display_name="PRD" ;;
        ralph) display_name="Ralph" ;;
        release) display_name="Release" ;;
        report) display_name="Report" ;;
        review) display_name="Review" ;;
        *) display_name=$(echo "$phase" | sed 's/\b\(.\)/\u\1/') ;;
    esac

    # Determine state and format
    if is_completed "$phase"; then
        printf "${WORKFLOW_COMPLETED}✓${display_name}${RESET}"
    elif [ "$workflow_phase" = "$phase" ]; then
        printf "${WORKFLOW_ACTIVE}●${display_name}${RESET}"
        # Add progress bar for ralph phase
        if [ "$phase" = "ralph" ] && [ "$ralph_total" -gt 0 ]; then
            # Check if there's a ticket in progress
            has_in_progress=0
            if [ -n "$ralph_current_ticket" ] && [ "$ralph_current_ticket" != "null" ]; then
                has_in_progress=1
            fi
            bar=$(progress_bar "$ralph_current" "$ralph_total" "$has_in_progress")
            printf "${WORKFLOW_PENDING} [${WORKFLOW_COMPLETED}${bar}${WORKFLOW_PENDING}] ${WORKFLOW_ACTIVE}${ralph_current}/${ralph_total}${RESET}"
        fi
    else
        printf "${WORKFLOW_PENDING}${display_name}${RESET}"
    fi
}

# Build Plan section
plan_line=""
first=true
for phase in $PLAN_PHASES; do
    if [ "$first" = true ]; then
        first=false
    else
        plan_line="${plan_line}${WORKFLOW_ARROW} → ${RESET}"
    fi
    plan_line="${plan_line}$(format_phase "$phase")"
done

# Build Execute section
execute_line=""
first=true
for phase in $EXECUTE_PHASES; do
    if [ "$first" = true ]; then
        first=false
    else
        execute_line="${execute_line}${WORKFLOW_ARROW} → ${RESET}"
    fi
    execute_line="${execute_line}$(format_phase "$phase")"
done

printf "📋 ${LINE3_PRIMARY}Plan${RESET}${SEPARATOR_COLOR}: ${RESET}${plan_line}${SEPARATOR_COLOR}. ${RESET}${LINE3_PRIMARY}Execute${RESET}${SEPARATOR_COLOR}: ${RESET}${execute_line}\n"
