#!/bin/bash
# Ralph Setup - Initialize ralph run before any LLM work
# Usage: setup.sh <prd-path> <plan-path>
#
# What this does:
# 1. Parse PRD/Plan for ticket list
# 2. Initialize workflow-state.json
# 3. Output ticket list for LLM to process

set -e

PRD_PATH="${1:-}"
PLAN_PATH="${2:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find project root (where workflow-state.json lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Ralph Setup ==="

# Validate inputs
if [ -z "$PRD_PATH" ] || [ -z "$PLAN_PATH" ]; then
    echo -e "${RED}Error: Missing arguments${NC}"
    echo "Usage: setup.sh <prd-path> <plan-path>"
    exit 1
fi

if [ ! -f "$PRD_PATH" ]; then
    echo -e "${RED}Error: PRD not found: $PRD_PATH${NC}"
    exit 1
fi

if [ ! -f "$PLAN_PATH" ]; then
    echo -e "${RED}Error: Plan not found: $PLAN_PATH${NC}"
    exit 1
fi

# Extract tickets from plan (look for LOCAL-XXX, TASK-XXX, TRELLO-XXX, etc.)
echo "Parsing tickets from plan..."
TICKETS=$(grep -oE '(LOCAL|TASK|TRELLO|GH|ASANA|LINEAR)-[0-9]+' "$PLAN_PATH" | sort -u -t'-' -k2 -n)
TICKET_COUNT=$(echo "$TICKETS" | grep -c . || echo "0")

if [ "$TICKET_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}Warning: No tickets found in plan${NC}"
    echo "Looking for patterns: LOCAL-XXX, TASK-XXX, TRELLO-XXX, GH-XXX"
    exit 1
fi

echo -e "${GREEN}Found $TICKET_COUNT tickets${NC}"

# Build ticket array for JSON
TICKET_JSON="["
FIRST=true
while IFS= read -r ticket; do
    if [ -n "$ticket" ]; then
        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            TICKET_JSON+=","
        fi
        TICKET_JSON+="{\"id\":\"$ticket\",\"status\":\"pending\",\"pr\":null,\"attempts\":0}"
    fi
done <<< "$TICKETS"
TICKET_JSON+="]"

# Initialize workflow-state.json
echo "Initializing workflow state..."

if [ ! -f "workflow-state.json" ]; then
    echo '{"phase":"idle","completed":[],"ralph":{"current":0,"total":0,"current_ticket":"","tickets":[],"blocked":[],"tickets_done":[]}}' > workflow-state.json
fi

# Check if there's existing ralph progress we should preserve
EXISTING_DONE=$(jq -r '.ralph.tickets_done // [] | length' workflow-state.json 2>/dev/null || echo "0")

if [ "$EXISTING_DONE" -gt 0 ]; then
    echo -e "${GREEN}Resuming existing run with $EXISTING_DONE tickets already done${NC}"
    # Just update phase, don't reset progress
    jq '.phase = "ralph"' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
else
    echo "Starting fresh run..."
    # Update workflow state with jq - full reset
    jq --argjson count "$TICKET_COUNT" --argjson tickets "$TICKET_JSON" '
      .phase = "ralph" |
      .ralph.current = 0 |
      .ralph.total = $count |
      .ralph.current_ticket = null |
      .ralph.tickets = $tickets |
      .ralph.blocked = [] |
      .ralph.tickets_done = [] |
      .completed = (.completed - ["report", "review", "ralph"])
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
fi

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output summary
echo ""
echo "=== Setup Complete ==="
echo -e "PRD: ${GREEN}$PRD_PATH${NC}"
echo -e "Plan: ${GREEN}$PLAN_PATH${NC}"
echo -e "Tickets: ${GREEN}$TICKET_COUNT${NC}"
echo ""
echo "Ticket list:"
echo "$TICKETS" | while read -r t; do echo "  - $t"; done
echo ""
echo "Next: LLM should start processing tickets"

# Output JSON for programmatic use
echo ""
echo "---JSON_OUTPUT---"
jq -c '.ralph' workflow-state.json
