#!/bin/bash
# Ralph Get Next Ticket - Find the next pending ticket
# Usage: get-next-ticket.sh
#
# What this does:
# 1. Read workflow-state.json
# 2. Find first pending ticket
# 3. Output ticket info
#
# Useful for loop control

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found${NC}" >&2
    exit 1
fi

# Get next ticket: prioritize in_progress (resume failed), then pending
NEXT_TICKET=$(jq -r '
  (.ralph.tickets[] | select(.status == "in_progress") | .id),
  (.ralph.tickets[] | select(.status == "pending") | .id)
' workflow-state.json | head -1)

# Get counts
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
# Count pending + in_progress (both need work)
PENDING=$(jq '[.ralph.tickets[] | select(.status == "pending" or .status == "in_progress")] | length' workflow-state.json)
BLOCKED=$(jq '.ralph.blocked | length' workflow-state.json)

if [ -n "$NEXT_TICKET" ]; then
    echo -e "Next: ${GREEN}$NEXT_TICKET${NC}"
    echo "Progress: $CURRENT/$TOTAL ($PENDING pending, $BLOCKED blocked)"

    echo ""
    echo "---JSON_OUTPUT---"
    cat << EOF
{
  "next_ticket": "$NEXT_TICKET",
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": $PENDING,
  "blocked": $BLOCKED,
  "has_more": true
}
EOF
    exit 0
else
    echo -e "${YELLOW}No pending or in-progress tickets${NC}"
    echo "Progress: $CURRENT/$TOTAL ($BLOCKED blocked)"

    echo ""
    echo "---JSON_OUTPUT---"
    cat << EOF
{
  "next_ticket": null,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": 0,
  "blocked": $BLOCKED,
  "has_more": false
}
EOF
    exit 0
fi
