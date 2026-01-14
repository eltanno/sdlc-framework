#!/bin/bash
# Ralph Ticket Done - Post-work after ticket completes successfully
# Usage: ticket-done.sh <ticket-id> [pr-number]
#
# What this does:
# 1. Update workflow-state.json (mark complete, increment counter)
# 2. Update status line
# 3. Output next ticket info
#
# Note: PM tool updates (move to Done) should be done via MCP
# This script handles local state only

set -e

TICKET_ID="${1:-}"
PR_NUMBER="${2:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: ticket-done.sh <ticket-id> [pr-number]"
    exit 1
fi

echo "=== Completing Ticket: $TICKET_ID ==="

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found${NC}"
    exit 1
fi

# Update workflow state
jq --arg id "$TICKET_ID" --arg pr "${PR_NUMBER:-null}" '
  .ralph.current = (.ralph.current + 1) |
  .ralph.current_ticket = null |
  .ralph.tickets_done += [$id] |
  .ralph.tickets = (.ralph.tickets | map(
    if .id == $id then
      .status = "done" | .pr = (if $pr == "null" then null else $pr end)
    else . end
  ))
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Get updated progress
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
REMAINING=$((TOTAL - CURRENT))

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Find next pending ticket
NEXT_TICKET=$(jq -r '.ralph.tickets[] | select(.status == "pending") | .id' workflow-state.json | head -1)

# Output summary
echo -e "${GREEN}Ticket $TICKET_ID completed!${NC}"
echo ""
echo "Progress: $CURRENT/$TOTAL ($REMAINING remaining)"
[ -n "$PR_NUMBER" ] && echo "PR: #$PR_NUMBER"
echo ""

if [ -n "$NEXT_TICKET" ]; then
    echo -e "Next ticket: ${YELLOW}$NEXT_TICKET${NC}"
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
  "progress": {
    "current": $CURRENT,
    "total": $TOTAL,
    "remaining": $REMAINING
  },
  "next_ticket": $([ -n "$NEXT_TICKET" ] && echo "\"$NEXT_TICKET\"" || echo "null"),
  "all_done": $([ -z "$NEXT_TICKET" ] && echo "true" || echo "false")
}
EOF
