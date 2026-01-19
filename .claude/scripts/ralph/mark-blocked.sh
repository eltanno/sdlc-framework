#!/bin/bash
# Ralph Mark Blocked - Mark a ticket as blocked and skip to next
# Usage: mark-blocked.sh <ticket-id> <reason> [--issue <number>]
#
# What this does:
# 1. Remove instance label (for multi-instance concurrency)
# 2. Add 'blocked' label and unassign
# 3. Add to blocked list in workflow-state.json
# 4. Output status
#
# Supports concurrent Ralph instances via label-based claiming
# GitHub Issues is the source of truth.

set -e

# Use PROJECT_ROOT if passed from parent, otherwise use pwd
# This allows the same script to be used across multiple worktrees
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: mark-blocked.sh <ticket-id> <reason> [--issue <number>]"
    exit 1
fi

# Check PM tool from config.yaml - must be github
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

if [ "$PM_TOOL" != "github" ]; then
    echo -e "${RED}Error: pm.tool must be 'github' in config.yaml${NC}"
    echo "GitHub Issues is the only supported PM tool for ralph."
    exit 1
fi

echo "=== Marking Blocked: $TICKET_ID ==="
echo "Reason: $REASON"

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI not found${NC}" >&2
    exit 1
fi

# If no issue number provided, look it up from GitHub
if [ -z "$ISSUE_NUMBER" ]; then
    echo "Looking up GitHub issue for $TICKET_ID..."
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
        if gh issue edit "$ISSUE_NUMBER" --remove-label "$INSTANCE_LABEL" 2>/dev/null; then
            echo -e "${GREEN}Removed label '$INSTANCE_LABEL' from issue #$ISSUE_NUMBER${NC}"
        else
            echo -e "${YELLOW}Label '$INSTANCE_LABEL' was not on issue #$ISSUE_NUMBER${NC}"
        fi
    fi

    # Try to add 'blocked' label
    if gh issue edit "$ISSUE_NUMBER" --add-label blocked 2>/dev/null; then
        echo -e "${GREEN}Added 'blocked' label to issue #$ISSUE_NUMBER${NC}"
    else
        echo -e "${YELLOW}Could not add 'blocked' label (label may not exist)${NC}"
    fi

    # Unassign the issue
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

# Get current timestamp
TIMESTAMP=$(date -Iseconds)

# Update local workflow state (just add to blocked list)
if [ -f "workflow-state.json" ]; then
    jq --arg id "$TICKET_ID" --arg reason "$REASON" --arg ts "$TIMESTAMP" --arg issue "${ISSUE_NUMBER:-null}" '
      .ralph.blocked = ((.ralph.blocked // []) + [{"id": $id, "reason": $reason, "timestamp": $ts, "issue_number": (if $issue == "null" then null else ($issue | tonumber) end)}])
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
fi

# Get counts from GitHub (source of truth)
BLOCKED_COUNT=$(gh issue list --state open --label blocked --json number --limit 1000 2>/dev/null | jq 'length' 2>/dev/null || echo "1")
TOTAL_OPEN=$(gh issue list --state open --label task --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
TOTAL_CLOSED=$(gh issue list --state closed --label task --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
TOTAL=$((TOTAL_OPEN + TOTAL_CLOSED))

# Output summary
echo ""
echo -e "${YELLOW}Ticket $TICKET_ID marked as BLOCKED${NC}"
[ -n "$ISSUE_NUMBER" ] && echo "GitHub Issue: #$ISSUE_NUMBER"
echo "Total blocked: $BLOCKED_COUNT"
echo ""
echo -e "${YELLOW}Run get-next-ticket.sh to find next issue${NC}"

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "blocked_ticket": "$TICKET_ID",
  "reason": "$REASON",
  "issue_number": $([ -n "$ISSUE_NUMBER" ] && echo "$ISSUE_NUMBER" || echo "null"),
  "blocked_count": $BLOCKED_COUNT,
  "total_open": $TOTAL_OPEN,
  "total": $TOTAL,
  "source": "github"
}
EOF
