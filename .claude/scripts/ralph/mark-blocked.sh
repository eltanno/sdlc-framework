#!/bin/bash
# Ralph Mark Blocked - Mark a ticket as blocked and skip to next
# Usage: mark-blocked.sh <ticket-id> <reason> [--issue <number>]
#
# What this does:
# 1. Check config.yaml for PM tool setting
# 2. If GitHub: Remove instance label (for multi-instance concurrency)
# 3. If GitHub: Add 'blocked' label and unassign (if labels available)
# 4. Mark ticket as blocked in workflow-state.json
# 5. Add to blocked list with reason
# 6. Clear current_ticket
# 7. Output next pending ticket
#
# Supports concurrent Ralph instances via label-based claiming
# Ticket: AUCT-0159

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
REASON="${2:-Unknown reason}"
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
    echo "Usage: mark-blocked.sh <ticket-id> <reason> [--issue <number>]"
    exit 1
fi

echo "=== Marking Blocked: $TICKET_ID ==="
echo "Reason: $REASON"

# Check PM tool from config.yaml
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

# GitHub-based blocked marking
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
        fi

        if [ -n "$ISSUE_NUMBER" ]; then
            echo "Updating GitHub issue #$ISSUE_NUMBER..."

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

            # Try to add 'blocked' label (may fail if label doesn't exist)
            if gh issue edit "$ISSUE_NUMBER" --add-label blocked 2>/dev/null; then
                echo -e "${GREEN}Added 'blocked' label to issue #$ISSUE_NUMBER${NC}"
            else
                echo -e "${YELLOW}Could not add 'blocked' label (label may not exist)${NC}"
            fi

            # Unassign the issue so another Ralph can pick it up (if they want to retry later)
            if gh issue edit "$ISSUE_NUMBER" --remove-assignee @me 2>/dev/null; then
                echo -e "${GREEN}Unassigned issue #$ISSUE_NUMBER${NC}"
            else
                echo -e "${YELLOW}Could not unassign issue${NC}"
            fi

            # Add a comment with the blocking reason
            if gh issue comment "$ISSUE_NUMBER" --body "**Blocked by Ralph automation**

Reason: $REASON

This issue has been marked as blocked and unassigned." 2>/dev/null; then
                echo -e "${GREEN}Added blocking comment to issue #$ISSUE_NUMBER${NC}"
            fi
        else
            echo -e "${YELLOW}No GitHub issue found for $TICKET_ID${NC}"
        fi
    fi
fi

# Get current timestamp
TIMESTAMP=$(date -Iseconds)

# Update local workflow state (if it exists)
if [ -f "workflow-state.json" ]; then
    jq --arg id "$TICKET_ID" --arg reason "$REASON" --arg ts "$TIMESTAMP" --arg issue "${ISSUE_NUMBER:-null}" '
      .ralph.current_ticket = null |
      .ralph.blocked += [{"id": $id, "reason": $reason, "timestamp": $ts, "issue_number": (if $issue == "null" then null else ($issue | tonumber) end)}] |
      .ralph.tickets = (.ralph.tickets | map(
        if .id == $id then
          .status = "blocked" | .issue_number = (if $issue == "null" then .issue_number else ($issue | tonumber) end)
        else . end
      ))
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

    # Get counts from local state
    CURRENT=$(jq -r '.ralph.current' workflow-state.json)
    TOTAL=$(jq -r '.ralph.total' workflow-state.json)
    BLOCKED_COUNT=$(jq '.ralph.blocked | length' workflow-state.json)

    # Find next pending ticket from local state
    NEXT_TICKET=$(jq -r '.ralph.tickets[] | select(.status == "pending") | .id' workflow-state.json | head -1)
else
    # No local state - use GitHub counts
    if [ "$PM_TOOL" = "github" ]; then
        BLOCKED_COUNT=$(gh issue list --state open --label blocked --json number --limit 1000 2>/dev/null | jq 'length' 2>/dev/null || echo "1")
        TOTAL_OPEN=$(gh issue list --state open --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL_CLOSED=$(gh issue list --state closed --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL=$((TOTAL_OPEN + TOTAL_CLOSED))
        CURRENT=$TOTAL_CLOSED
        NEXT_TICKET=""  # Will be determined by get-next-ticket.sh
    else
        echo -e "${YELLOW}Warning: workflow-state.json not found${NC}"
        BLOCKED_COUNT=1
        CURRENT=0
        TOTAL=0
        NEXT_TICKET=""
    fi
fi

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output summary
echo ""
echo -e "${YELLOW}Ticket $TICKET_ID marked as BLOCKED${NC}"
[ -n "$ISSUE_NUMBER" ] && echo "GitHub Issue: #$ISSUE_NUMBER"
echo "Total blocked: $BLOCKED_COUNT"
echo ""

if [ -n "$NEXT_TICKET" ]; then
    echo -e "Next ticket: ${GREEN}$NEXT_TICKET${NC}"
    echo "Continuing with next ticket..."
elif [ "$PM_TOOL" = "github" ]; then
    echo -e "${YELLOW}Run get-next-ticket.sh to find next issue${NC}"
else
    echo -e "${YELLOW}No more pending tickets${NC}"
    echo "All remaining tickets are blocked or complete."
fi

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "blocked_ticket": "$TICKET_ID",
  "reason": "$REASON",
  "issue_number": $([ -n "$ISSUE_NUMBER" ] && echo "$ISSUE_NUMBER" || echo "null"),
  "blocked_count": $BLOCKED_COUNT,
  "next_ticket": $([ -n "$NEXT_TICKET" ] && echo "\"$NEXT_TICKET\"" || echo "null"),
  "source": "$([ "$PM_TOOL" = "github" ] && echo "github" || echo "local")"
}
EOF
