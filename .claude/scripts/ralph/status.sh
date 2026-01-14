#!/bin/bash
# Ralph Status - Show current ralph state
# Usage: status.sh
#
# What this does:
# 1. Read workflow-state.json
# 2. Display formatted status
# 3. Output JSON for programmatic use

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${YELLOW}No workflow-state.json found${NC}"
    echo "Ralph has not been initialized."
    echo ""
    echo "---JSON_OUTPUT---"
    echo '{"initialized": false}'
    exit 0
fi

# Get state
PHASE=$(jq -r '.phase' workflow-state.json)
CURRENT=$(jq -r '.ralph.current // 0' workflow-state.json)
TOTAL=$(jq -r '.ralph.total // 0' workflow-state.json)
CURRENT_TICKET=$(jq -r '.ralph.current_ticket // "none"' workflow-state.json)

# Count by status
DONE=$(jq '[.ralph.tickets // [] | .[] | select(.status == "done")] | length' workflow-state.json)
IN_PROGRESS=$(jq '[.ralph.tickets // [] | .[] | select(.status == "in_progress")] | length' workflow-state.json)
PENDING=$(jq '[.ralph.tickets // [] | .[] | select(.status == "pending")] | length' workflow-state.json)
BLOCKED=$(jq '.ralph.blocked // [] | length' workflow-state.json)

echo "========================================"
echo "         RALPH STATUS"
echo "========================================"
echo ""
echo -e "Phase:            ${CYAN}$PHASE${NC}"
echo -e "Progress:         ${GREEN}$CURRENT${NC}/${TOTAL}"
echo -e "Current Ticket:   ${YELLOW}$CURRENT_TICKET${NC}"
echo ""
echo "Ticket Status:"
echo -e "  Done:           ${GREEN}$DONE${NC}"
echo -e "  In Progress:    ${YELLOW}$IN_PROGRESS${NC}"
echo -e "  Pending:        ${CYAN}$PENDING${NC}"
echo -e "  Blocked:        ${RED}$BLOCKED${NC}"
echo ""

# Show current ticket details if any
if [ "$CURRENT_TICKET" != "none" ] && [ "$CURRENT_TICKET" != "null" ] && [ -n "$CURRENT_TICKET" ]; then
    echo "Current Ticket Details:"
    jq --arg id "$CURRENT_TICKET" '.ralph.tickets // [] | .[] | select(.id == $id)' workflow-state.json 2>/dev/null || echo "  (no details)"
    echo ""
fi

# Show blocked tickets if any
if [ "$BLOCKED" -gt 0 ]; then
    echo -e "${RED}Blocked Tickets:${NC}"
    jq -r '.ralph.blocked[] | "  \(.id): \(.reason)"' workflow-state.json
    echo ""
fi

echo "========================================"

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
jq '{
  phase: .phase,
  current: .ralph.current,
  total: .ralph.total,
  current_ticket: .ralph.current_ticket,
  done: ([.ralph.tickets // [] | .[] | select(.status == "done")] | length),
  in_progress: ([.ralph.tickets // [] | .[] | select(.status == "in_progress")] | length),
  pending: ([.ralph.tickets // [] | .[] | select(.status == "pending")] | length),
  blocked: (.ralph.blocked // [] | length)
}' workflow-state.json
