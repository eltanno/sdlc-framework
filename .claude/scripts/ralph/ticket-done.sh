#!/bin/bash
# Ralph Ticket Done - Post-work after ticket completes successfully
# Usage: ticket-done.sh <ticket-id> [pr-number] [--issue <number>]
#
# What this does:
# 1. Check config.yaml for PM tool setting
# 2. If GitHub: Remove instance label (for multi-instance concurrency)
# 3. If GitHub: Close the issue
# 4. Update workflow-state.json (mark complete, increment counter)
# 5. Output next ticket info
#
# Supports concurrent Ralph instances via label-based claiming
# Ticket: AUCT-0158

set -e

# Find project root and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Load .env if present (for RALPH_LABEL)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Source config helpers for label configuration
source "$SCRIPT_DIR/config-helpers.sh"

TICKET_ID="${1:-}"
PR_NUMBER="${2:-}"
ISSUE_NUMBER=""

# Parse additional arguments
shift 2 2>/dev/null || shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --issue)
            ISSUE_NUMBER="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root (SCRIPT_DIR already set when sourcing config-helpers.sh)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: ticket-done.sh <ticket-id> [pr-number] [--issue <number>]"
    exit 1
fi

echo "=== Completing Ticket: $TICKET_ID ==="

# Check PM tool from config.yaml
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

# GitHub-based issue closing
if [ "$PM_TOOL" = "github" ]; then
    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}Warning: gh CLI not found, skipping GitHub update${NC}"
    else
        # If no issue number provided, look it up from local state or GitHub
        if [ -z "$ISSUE_NUMBER" ] && [ -f "workflow-state.json" ]; then
            ISSUE_NUMBER=$(jq -r --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id) | .issue_number // empty' workflow-state.json)
        fi

        if [ -z "$ISSUE_NUMBER" ]; then
            echo "Looking up GitHub issue for $TICKET_ID..."
            # Search for issue with ticket ID in title
            ISSUE_NUMBER=$(gh issue list --state open --json number,title --limit 100 2>/dev/null | \
                jq -r --arg tid "$TICKET_ID" '.[] | select(.title | contains($tid)) | "\(.number)"' | head -1)

            # Also check closed issues (in case already closed)
            if [ -z "$ISSUE_NUMBER" ]; then
                ISSUE_NUMBER=$(gh issue list --state closed --json number,title --limit 100 2>/dev/null | \
                    jq -r --arg tid "$TICKET_ID" '.[] | select(.title | contains($tid)) | "\(.number)"' | head -1)
            fi
        fi

        if [ -n "$ISSUE_NUMBER" ]; then
            # Read label configuration
            INSTANCE_LABEL=$(get_instance_label)

            # Remove instance label if configured (for multi-instance concurrency)
            if [ -n "$INSTANCE_LABEL" ]; then
                echo "Removing instance label: $INSTANCE_LABEL"
                # Label removal is idempotent - safe if label already removed
                if gh issue edit "$ISSUE_NUMBER" --remove-label "$INSTANCE_LABEL" 2>/dev/null; then
                    echo -e "${GREEN}Removed label '$INSTANCE_LABEL' from issue #$ISSUE_NUMBER${NC}"
                else
                    # Label might already be removed or never existed on this issue
                    echo -e "${YELLOW}Label '$INSTANCE_LABEL' was not on issue #$ISSUE_NUMBER (already removed or not added)${NC}"
                fi
            fi

            echo "Closing GitHub issue #$ISSUE_NUMBER..."

            # Close the issue (idempotent - succeeds even if already closed)
            if gh issue close "$ISSUE_NUMBER" 2>/dev/null; then
                echo -e "${GREEN}Closed issue #$ISSUE_NUMBER${NC}"
            else
                # Check if already closed
                ISSUE_STATE=$(gh issue view "$ISSUE_NUMBER" --json state --jq '.state' 2>/dev/null || echo "")
                if [ "$ISSUE_STATE" = "CLOSED" ]; then
                    echo -e "${YELLOW}Issue #$ISSUE_NUMBER was already closed${NC}"
                else
                    echo -e "${YELLOW}Warning: Could not close issue #$ISSUE_NUMBER${NC}"
                fi
            fi
        else
            echo -e "${YELLOW}No GitHub issue found for $TICKET_ID${NC}"
        fi
    fi
fi

# Update local workflow-state.json (if it exists)
if [ -f "workflow-state.json" ]; then
    jq --arg id "$TICKET_ID" --arg pr "${PR_NUMBER:-null}" --arg issue "${ISSUE_NUMBER:-null}" '
      .ralph.current = (.ralph.current + 1) |
      .ralph.current_ticket = null |
      .ralph.tickets_done += [$id] |
      .ralph.tickets = (.ralph.tickets | map(
        if .id == $id then
          .status = "done" | .pr = (if $pr == "null" then null else $pr end) | .issue_number = (if $issue == "null" then .issue_number else ($issue | tonumber) end)
        else . end
      ))
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

    # Get updated progress
    CURRENT=$(jq -r '.ralph.current' workflow-state.json)
    TOTAL=$(jq -r '.ralph.total' workflow-state.json)
    REMAINING=$((TOTAL - CURRENT))

    # Find next pending ticket from local state
    NEXT_TICKET=$(jq -r '.ralph.tickets[] | select(.status == "pending") | .id' workflow-state.json | head -1)
else
    # No local state - use GitHub counts
    if [ "$PM_TOOL" = "github" ]; then
        TOTAL_OPEN=$(gh issue list --state open --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL_CLOSED=$(gh issue list --state closed --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL=$((TOTAL_OPEN + TOTAL_CLOSED))
        CURRENT=$TOTAL_CLOSED
        REMAINING=$TOTAL_OPEN
        NEXT_TICKET=""  # Will be determined by get-next-ticket.sh
    else
        echo -e "${YELLOW}Warning: workflow-state.json not found${NC}"
        CURRENT=0
        TOTAL=0
        REMAINING=0
        NEXT_TICKET=""
    fi
fi

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output summary
echo -e "${GREEN}Ticket $TICKET_ID completed!${NC}"
echo ""
echo "Progress: $CURRENT/$TOTAL ($REMAINING remaining)"
[ -n "$PR_NUMBER" ] && echo "PR: #$PR_NUMBER"
[ -n "$ISSUE_NUMBER" ] && echo "GitHub Issue: #$ISSUE_NUMBER (closed)"
echo ""

if [ -n "$NEXT_TICKET" ]; then
    echo -e "Next ticket: ${YELLOW}$NEXT_TICKET${NC}"
elif [ "$REMAINING" -gt 0 ]; then
    echo -e "${YELLOW}Run get-next-ticket.sh to find next issue${NC}"
else
    echo -e "${GREEN}All tickets complete!${NC}"
fi

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "completed_ticket": "$TICKET_ID",
  "pr": $([ -n "$PR_NUMBER" ] && echo "\"$PR_NUMBER\"" || echo "null"),
  "issue_number": $([ -n "$ISSUE_NUMBER" ] && echo "$ISSUE_NUMBER" || echo "null"),
  "progress": {
    "current": $CURRENT,
    "total": $TOTAL,
    "remaining": $REMAINING
  },
  "next_ticket": $([ -n "$NEXT_TICKET" ] && echo "\"$NEXT_TICKET\"" || echo "null"),
  "all_done": $([ "$REMAINING" -eq 0 ] && echo "true" || echo "false"),
  "source": "$([ "$PM_TOOL" = "github" ] && echo "github" || echo "local")"
}
EOF
