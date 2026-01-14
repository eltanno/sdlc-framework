#!/bin/bash
# Ralph Cleanup - Finalize ralph run
# Usage: cleanup.sh
#
# What this does:
# 1. Finalize workflow-state.json
# 2. Generate summary
# 3. Update status line
# 4. Output PRD_COMPLETE or summary

set -e

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

echo "=== Ralph Cleanup ==="

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found${NC}"
    exit 1
fi

# Get final counts
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
DONE_COUNT=$(jq '[.ralph.tickets[] | select(.status == "done")] | length' workflow-state.json)
BLOCKED_COUNT=$(jq '.ralph.blocked | length' workflow-state.json)
PENDING_COUNT=$(jq '[.ralph.tickets[] | select(.status == "pending")] | length' workflow-state.json)

# Determine completion status
if [ "$PENDING_COUNT" -eq 0 ] && [ "$BLOCKED_COUNT" -eq 0 ]; then
    STATUS="complete"
elif [ "$PENDING_COUNT" -eq 0 ]; then
    STATUS="complete_with_blocked"
else
    STATUS="incomplete"
fi

# Update workflow state
jq '
  .phase = "idle" |
  .completed = (.completed + ["ralph"] | unique)
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output summary
echo ""
echo "========================================"
echo "         RALPH RUN SUMMARY"
echo "========================================"
echo ""
echo -e "Total Tickets:    ${CYAN}$TOTAL${NC}"
echo -e "Completed:        ${GREEN}$DONE_COUNT${NC}"
echo -e "Blocked:          ${YELLOW}$BLOCKED_COUNT${NC}"
echo -e "Pending:          ${RED}$PENDING_COUNT${NC}"
echo ""

# List completed tickets
if [ "$DONE_COUNT" -gt 0 ]; then
    echo "Completed tickets:"
    jq -r '.ralph.tickets[] | select(.status == "done") | "  - \(.id)" + (if .pr then " (PR #\(.pr))" else "" end)' workflow-state.json
    echo ""
fi

# List blocked tickets
if [ "$BLOCKED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Blocked tickets:${NC}"
    jq -r '.ralph.blocked[] | "  - \(.id): \(.reason)"' workflow-state.json
    echo ""
fi

# List pending tickets
if [ "$PENDING_COUNT" -gt 0 ]; then
    echo -e "${RED}Pending tickets (not started):${NC}"
    jq -r '.ralph.tickets[] | select(.status == "pending") | "  - \(.id)"' workflow-state.json
    echo ""
fi

# Final status
echo "========================================"
case $STATUS in
    complete)
        echo -e "${GREEN}PRD_COMPLETE${NC}"
        echo "All tickets have been implemented!"
        ;;
    complete_with_blocked)
        echo -e "${YELLOW}PRD_COMPLETE_WITH_BLOCKED${NC}"
        echo "All possible tickets done. $BLOCKED_COUNT tickets need manual review."
        ;;
    incomplete)
        echo -e "${RED}PRD_INCOMPLETE${NC}"
        echo "$PENDING_COUNT tickets still pending."
        ;;
esac
echo "========================================"

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "status": "$STATUS",
  "total": $TOTAL,
  "done": $DONE_COUNT,
  "blocked": $BLOCKED_COUNT,
  "pending": $PENDING_COUNT,
  "completion_signal": "$([ "$STATUS" = "complete" ] && echo "PRD_COMPLETE" || echo "NEEDS_REVIEW")"
}
EOF

# Exit with appropriate code
case $STATUS in
    complete)
        exit 0
        ;;
    complete_with_blocked)
        exit 0
        ;;
    incomplete)
        exit 1
        ;;
esac
