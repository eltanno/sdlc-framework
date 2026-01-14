#!/bin/bash
# Ralph Ticket Start - Pre-work before LLM starts on a ticket
# Usage: ticket-start.sh <ticket-id>
#
# What this does:
# 1. Update workflow-state.json with current ticket
# 2. Update status line
# 3. Output ticket info for LLM
#
# Note: PM tool updates (move to In Progress) should be done via MCP
# This script handles local state only

set -e

TICKET_ID="${1:-}"

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
    echo "Usage: ticket-start.sh <ticket-id>"
    exit 1
fi

echo "=== Starting Ticket: $TICKET_ID ==="

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found. Run setup.sh first.${NC}"
    exit 1
fi

# Check if ticket exists in state
TICKET_EXISTS=$(jq --arg id "$TICKET_ID" '.ralph.tickets | map(select(.id == $id)) | length' workflow-state.json)
if [ "$TICKET_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Ticket $TICKET_ID not in workflow state, adding it${NC}"
    jq --arg id "$TICKET_ID" '
      .ralph.tickets += [{"id": $id, "status": "pending", "pr": null, "attempts": 0}]
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
fi

# Update ticket status to in_progress and increment attempts
jq --arg id "$TICKET_ID" '
  .ralph.current_ticket = $id |
  .ralph.tickets = (.ralph.tickets | map(
    if .id == $id then
      .status = "in_progress" | .attempts = (.attempts + 1)
    else . end
  ))
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Get current progress
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
ATTEMPTS=$(jq --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id) | .attempts' workflow-state.json)

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output
echo -e "Ticket: ${GREEN}$TICKET_ID${NC}"
echo -e "Progress: ${GREEN}$CURRENT/$TOTAL${NC}"
echo -e "Attempt: ${YELLOW}$ATTEMPTS${NC}"

if [ "$ATTEMPTS" -gt 3 ]; then
    echo -e "${RED}WARNING: This is attempt $ATTEMPTS. Consider marking as blocked.${NC}"
fi

echo ""
echo "---JSON_OUTPUT---"
jq -c --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id)' workflow-state.json
