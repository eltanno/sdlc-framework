#!/bin/bash
# Ralph Cleanup - Finalize ralph run
# Usage: cleanup.sh
#
# What this does:
# 1. Finalize workflow-state.json
# 2. Generate summary from GitHub (source of truth)
# 3. Output PRD_COMPLETE or summary

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Use PROJECT_ROOT if passed from parent, otherwise use pwd
# This allows the same script to be used across multiple worktrees
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Ralph Cleanup ==="
echo "Source: GitHub (querying for final counts...)"

# Query GitHub for issue counts (GitHub is always source of truth)
TOTAL=$(gh issue list --state all --label task --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
DONE_COUNT=$(gh issue list --state closed --label task --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
BLOCKED_COUNT=$(gh issue list --state open --label blocked --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
OPEN_COUNT=$(gh issue list --state open --label task --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
PENDING_COUNT=$((OPEN_COUNT - BLOCKED_COUNT))

# Ensure non-negative
[ "$PENDING_COUNT" -lt 0 ] && PENDING_COUNT=0

# Determine completion status
if [ "$PENDING_COUNT" -eq 0 ] && [ "$BLOCKED_COUNT" -eq 0 ]; then
    STATUS="complete"
elif [ "$PENDING_COUNT" -eq 0 ]; then
    STATUS="complete_with_blocked"
else
    STATUS="incomplete"
fi

# Update workflow state (if file exists)
if [ -f "workflow-state.json" ]; then
    jq '
      .phase = "idle" |
      .completed = ((.completed // []) + ["ralph"] | unique)
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
fi

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

# List tickets from GitHub
if [ "$DONE_COUNT" -gt 0 ]; then
    echo "Completed tickets:"
    gh issue list --state closed --label task --json number,title --limit 1000 2>/dev/null | jq -r '.[] | "  - " + (.title | split("]")[0]) + "]"'
    echo ""
fi

if [ "$BLOCKED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Blocked tickets:${NC}"
    gh issue list --state open --label blocked --json number,title --limit 100 2>/dev/null | jq -r '.[] | "  - \(.title)"'
    echo ""
fi

if [ "$PENDING_COUNT" -gt 0 ]; then
    echo -e "${RED}Pending tickets (not started):${NC}"
    gh issue list --state open --label task --json number,title --limit 100 2>/dev/null | jq -r '.[] | "  - \(.title)"'
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

# Always exit 0 - cleanup is informational, not a pass/fail gate
# Other instances may still be working on remaining tickets
exit 0
