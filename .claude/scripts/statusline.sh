#!/bin/bash
#
# Claude Code Statusline - Portable version
#
# Displays: model, version, directory, MCPs, token usage/cost
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

# Get directory name
dir_name=$(basename "$current_dir")

# Cache file and lock file for ccusage data
CACHE_FILE="/tmp/.claude_ccusage_cache"
LOCK_FILE="/tmp/.claude_ccusage.lock"
CACHE_AGE=30   # 30 seconds for more real-time updates

# Count MCPs - check local .mcp.json first, then fall back to global ~/.claude.json
mcp_names_raw=""
mcps_count=0

# Check local project .mcp.json first
if [ -f "$current_dir/.mcp.json" ]; then
    mcp_data=$(jq -r '.mcpServers | keys | join(" "), length' "$current_dir/.mcp.json" 2>/dev/null)
    if [ -n "$mcp_data" ] && [ "$mcp_data" != "null" ]; then
        mcp_names_raw=$(echo "$mcp_data" | head -1)
        mcps_count=$(echo "$mcp_data" | tail -1)
    fi
# Fall back to global ~/.claude.json
elif [ -f "$HOME/.claude.json" ]; then
    mcp_data=$(jq -r '.mcpServers | keys | join(" "), length' "$HOME/.claude.json" 2>/dev/null)
    if [ -n "$mcp_data" ] && [ "$mcp_data" != "null" ]; then
        mcp_names_raw=$(echo "$mcp_data" | head -1)
        mcps_count=$(echo "$mcp_data" | tail -1)
    fi
fi

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

SEPARATOR_COLOR='\033[38;2;140;152;180m'
DIR_COLOR='\033[38;2;135;206;250m'

MCP_DEFAULT="$LINE2_PRIMARY"

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

# Output the statusline
# LINE 1 - Greeting with version and model
printf "Claude Code v${cc_version} ${MODEL_PURPLE}${model_name}${RESET} ${DIR_COLOR}${dir_name}${RESET}\n"

# LINE 2 - MCPs
if [ -n "$mcp_names_formatted" ]; then
    printf "${LINE2_PRIMARY}MCPs${RESET}${SEPARATOR_COLOR}: ${RESET}${mcp_names_formatted}${RESET}\n"
fi

# LINE 3 - Tokens and cost
tokens_display="${daily_tokens:-N/A}"
cost_display="${daily_cost:-N/A}"
if [ -z "$daily_tokens" ]; then tokens_display="N/A"; fi
if [ -z "$daily_cost" ]; then cost_display="N/A"; fi

printf "${LINE3_PRIMARY}Tokens${RESET}${SEPARATOR_COLOR}: ${RESET}${LINE3_ACCENT}${tokens_display}${RESET}  ${LINE3_PRIMARY}Cost${RESET}${SEPARATOR_COLOR}: ${RESET}${COST_COLOR}${cost_display}${RESET}"

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
    printf "  ${SEPARATOR_COLOR}|${RESET}  ${LINE3_ACCENT}${block_messages}${RESET} msgs, ${LINE3_ACCENT}${block_percent}%%${RESET} used, resets in ${LINE3_ACCENT}${block_reset}${RESET}"
fi
printf "\n"
