#!/bin/bash
# Ralph Ticket Reset - Reset a blocked ticket to pending state
# Usage: ticket-reset.sh <ticket-id> [--clean-state]
#
# What this does:
# 1. Remove ticket from blocked array
# 2. Set ticket status back to "pending"
# 3. Reset attempts counter to 0
# 4. Optionally clean up state files for fresh start

set -e

TICKET_ID="${1:-}"
CLEAN_STATE=false

# Parse flags
for arg in "$@"; do
    case $arg in
        --clean-state)
            CLEAN_STATE=true
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Use PROJECT_ROOT if passed from parent, otherwise use pwd
# This allows the same script to be used across multiple worktrees
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: ticket-reset.sh <ticket-id> [--clean-state]"
    echo ""
    echo "Options:"
    echo "  --clean-state  Also delete state files (attempt directories)"
    exit 1
fi

echo "=== Resetting Ticket: $TICKET_ID ==="

# Validate workflow state exists
if [ ! -f "workflow-state.json" ]; then
    echo -e "${RED}Error: workflow-state.json not found${NC}"
    exit 1
fi

# Check if ticket exists
TICKET_EXISTS=$(jq -r --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id) | .id' workflow-state.json)
if [ -z "$TICKET_EXISTS" ]; then
    echo -e "${RED}Error: Ticket $TICKET_ID not found in workflow-state.json${NC}"
    exit 1
fi

# Get current status
CURRENT_STATUS=$(jq -r --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id) | .status' workflow-state.json)
echo "Current status: $CURRENT_STATUS"

# Update workflow state
jq --arg id "$TICKET_ID" '
  # Remove from blocked array
  .ralph.blocked = (.ralph.blocked | map(select(.id != $id))) |
  # Reset ticket to pending with 0 attempts
  .ralph.tickets = (.ralph.tickets | map(
    if .id == $id then
      .status = "pending" |
      .attempts = 0 |
      .pr = null
    else . end
  ))
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Clean up state files if requested
if [ "$CLEAN_STATE" = true ]; then
    STATE_DIR="docs/state/$TICKET_ID"
    if [ -d "$STATE_DIR" ]; then
        echo "Cleaning state directory: $STATE_DIR"
        rm -rf "$STATE_DIR"
        echo -e "${YELLOW}State files removed${NC}"
    else
        echo "No state directory found at $STATE_DIR"
    fi
fi

# Get updated counts
PENDING=$(jq '[.ralph.tickets[] | select(.status == "pending")] | length' workflow-state.json)
BLOCKED_COUNT=$(jq '.ralph.blocked | length' workflow-state.json)

# Output summary
echo ""
echo -e "${GREEN}Ticket $TICKET_ID reset to pending${NC}"
echo "Pending tickets: $PENDING"
echo "Blocked tickets: $BLOCKED_COUNT"

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "ticket": "$TICKET_ID",
  "previous_status": "$CURRENT_STATUS",
  "new_status": "pending",
  "state_cleaned": $CLEAN_STATE,
  "pending_count": $PENDING,
  "blocked_count": $BLOCKED_COUNT
}
EOF
