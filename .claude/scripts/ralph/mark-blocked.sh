#!/bin/bash
# Ralph Mark Blocked - Mark a ticket as blocked and skip to next
# Usage: mark-blocked.sh <ticket-id> <reason>
#
# What this does:
# 1. Mark ticket as blocked in workflow-state.json
# 2. Add to blocked list with reason
# 3. Clear current_ticket
# 4. Output next pending ticket

set -e

TICKET_ID="${1:-}"
REASON="${2:-Unknown reason}"

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
    echo "Usage: mark-blocked.sh <ticket-id> <reason>"
    exit 1
fi

echo "=== Marking Blocked: $TICKET_ID ==="
echo "Reason: $REASON"

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found${NC}"
    exit 1
fi

# Get current timestamp
TIMESTAMP=$(date -Iseconds)

# Update workflow state
jq --arg id "$TICKET_ID" --arg reason "$REASON" --arg ts "$TIMESTAMP" '
  .ralph.current_ticket = null |
  .ralph.blocked += [{"id": $id, "reason": $reason, "timestamp": $ts}] |
  .ralph.tickets = (.ralph.tickets | map(
    if .id == $id then
      .status = "blocked"
    else . end
  ))
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Get counts
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
BLOCKED_COUNT=$(jq '.ralph.blocked | length' workflow-state.json)

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Find next pending ticket
NEXT_TICKET=$(jq -r '.ralph.tickets[] | select(.status == "pending") | .id' workflow-state.json | head -1)

# Output summary
echo ""
echo -e "${YELLOW}Ticket $TICKET_ID marked as BLOCKED${NC}"
echo "Total blocked: $BLOCKED_COUNT"
echo ""

if [ -n "$NEXT_TICKET" ]; then
    echo -e "Next ticket: ${GREEN}$NEXT_TICKET${NC}"
    echo "Continuing with next ticket..."
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
  "blocked_count": $BLOCKED_COUNT,
  "next_ticket": $([ -n "$NEXT_TICKET" ] && echo "\"$NEXT_TICKET\"" || echo "null")
}
EOF
