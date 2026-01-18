#!/bin/bash
# Ralph Setup - Initialize ralph run before any LLM work
# Usage: setup.sh [<prd-path> <plan-path>] [--label <label>]
#
# What this does:
# 1. Check config.yaml for PM tool setting
# 2. Validate GitHub access (if GitHub mode)
# 3. Get initial ticket counts for display
# 4. Initialize workflow-state.json phase
#
# NOTE: This is intentionally lightweight for parallel execution.
# The loop uses get-next-ticket.sh which queries GitHub in real-time.
# No local ticket list is maintained - GitHub Issues are the source of truth.

set -e

# Load .env if present (for RALPH_LABEL and other config)
if [ -f .env ]; then
  set -a  # auto-export variables
  source .env
  set +a
fi

PRD_PATH="${1:-}"
PLAN_PATH="${2:-}"
LABEL_FILTER=""

# Parse additional arguments
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --label)
            LABEL_FILTER="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find project root (where workflow-state.json lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Source config helpers for label functions
source "$SCRIPT_DIR/config-helpers.sh"

echo "=== Ralph Setup ==="

# Check PM tool from config.yaml
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

# Read ticket prefix from config.yaml
TICKET_PREFIX=""
if [ -f "config.yaml" ]; then
    TICKET_PREFIX=$(grep -E '^\s*prefix:' config.yaml | head -1 | sed 's/.*prefix:\s*"\?\([^"]*\)"\?.*/\1/' | tr -d ' "')
fi
if [ -z "$TICKET_PREFIX" ]; then
    echo -e "${RED}Error: No ticket prefix found in config.yaml${NC}"
    echo "Add 'tickets.prefix' to your config.yaml (e.g., prefix: \"AUCT\")"
    exit 1
fi

# GitHub-based setup (lightweight - just validate access)
if [ "$PM_TOOL" = "github" ]; then
    echo "Using GitHub Issues as source of truth..."

    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}Error: gh CLI not found but pm.tool=github${NC}" >&2
        echo "Install gh CLI or change pm.tool in config.yaml" >&2
        exit 1
    fi

    # Check if gh is authenticated
    if ! gh auth status &> /dev/null; then
        echo -e "${RED}Error: gh CLI not authenticated${NC}" >&2
        echo "Run: gh auth login" >&2
        exit 1
    fi

    # Get and validate instance label from environment
    INSTANCE_LABEL=$(get_instance_label) || exit 1
    echo "Instance label: $INSTANCE_LABEL"

    # Ensure label exists in GitHub (create if missing)
    # Using gh api since older gh versions don't have 'gh label' command
    REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null)
    if ! gh api "repos/$REPO/labels" --jq '.[].name' 2>/dev/null | grep -q "^${INSTANCE_LABEL}$"; then
        echo "Creating label '${INSTANCE_LABEL}'..."
        gh api "repos/$REPO/labels" -f name="$INSTANCE_LABEL" -f description="Ralph instance label" -f color="0052CC" >/dev/null 2>&1 || true
    fi

    # Check for existing in-progress work with this label
    INSTANCE_OPEN_COUNT=$(gh issue list --label "$INSTANCE_LABEL" --state open --json number --jq 'length')

    if [[ "$INSTANCE_OPEN_COUNT" -gt 0 ]]; then
        echo ""
        echo -e "${YELLOW}Warning: Label '$INSTANCE_LABEL' has $INSTANCE_OPEN_COUNT open issue(s).${NC}"
        echo "This may indicate another ralph instance is using this label."
        echo ""
        read -p "Resume existing work with this label? (y/n): " CONFIRM

        if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
            echo ""
            echo "Exiting. To use a different label, update RALPH_LABEL in your .env file."
            echo "Example: RALPH_LABEL=ralph-2"
            exit 1
        fi

        echo "Continuing with label '$INSTANCE_LABEL'..."
    fi

    # Get counts from GitHub (lightweight query - just for display)
    # Check for available tickets (task label) - these are what the loop will pick up
    echo "Checking GitHub Issues status..."
    echo "Instance label: $INSTANCE_LABEL"

    # Count tickets available to work on (have "task" label)
    AVAILABLE_COUNT=$(gh issue list --state open --label "task" --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")

    # Count tickets already claimed by this instance (have our ralph label)
    IN_PROGRESS_COUNT=$(gh issue list --state open --label "$INSTANCE_LABEL" --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")

    # Count completed by this instance
    COMPLETED_COUNT=$(gh issue list --state closed --label "$INSTANCE_LABEL" --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")

    TOTAL=$((AVAILABLE_COUNT + IN_PROGRESS_COUNT + COMPLETED_COUNT))

    if [ "$AVAILABLE_COUNT" -eq 0 ] && [ "$IN_PROGRESS_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}No open issues found${NC}"
        echo "Expected format: [${TICKET_PREFIX}-XXXX] Description"
        echo "Create issues with /ticket or manually"
        exit 1
    fi

    echo -e "${GREEN}Found $AVAILABLE_COUNT available tickets, $IN_PROGRESS_COUNT in-progress${NC}"

    # Initialize workflow-state.json (minimal - just set phase)
    if [ ! -f "workflow-state.json" ]; then
        echo '{"phase":"idle","completed":[],"ralph":{}}' > workflow-state.json
    fi

    # Set phase to ralph, preserve any existing data
    jq '.phase = "ralph" | .ralph.source = "github"' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

    # Parse and store dependencies from plan document (if provided)
    if [ -n "$PLAN_PATH" ] && [ -f "$PLAN_PATH" ]; then
        echo "Parsing ticket dependencies from plan..."
        DEPS_JSON=$("$SCRIPT_DIR/parse-plan-deps.sh" "$PLAN_PATH" "$TICKET_PREFIX" 2>/dev/null || echo "{}")

        if [ "$DEPS_JSON" != "{}" ]; then
            # Store dependencies in workflow-state.json
            jq --argjson deps "$DEPS_JSON" '.ralph.dependencies = $deps' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
            DEP_COUNT=$(echo "$DEPS_JSON" | jq 'length')
            echo -e "${GREEN}Loaded dependencies for $DEP_COUNT tickets${NC}"
        else
            echo -e "${YELLOW}No dependencies found in plan (or parse failed)${NC}"
        fi
    else
        echo -e "${YELLOW}No plan path provided - dependency checking disabled${NC}"
        echo "Tip: Pass plan path to enable dependency checking"
    fi

    # Output summary
    echo ""
    echo "=== Setup Complete (GitHub Mode) ==="
    echo -e "Source: ${GREEN}GitHub Issues${NC}"
    echo -e "Instance Label: ${GREEN}$INSTANCE_LABEL${NC}"
    echo -e "Available: ${GREEN}$AVAILABLE_COUNT${NC} (tickets with 'task' label)"
    echo -e "In Progress: ${GREEN}$IN_PROGRESS_COUNT${NC} (tickets with '$INSTANCE_LABEL' label)"
    echo -e "Completed: ${GREEN}$COMPLETED_COUNT${NC}"
    echo ""
    echo "Mode: Parallel-safe (no local ticket list)"
    echo "Next: Loop will query get-next-ticket.sh for each ticket"

    # Output JSON for programmatic use
    echo ""
    echo "---JSON_OUTPUT---"
    cat << EOF
{
  "available": $AVAILABLE_COUNT,
  "in_progress": $IN_PROGRESS_COUNT,
  "completed": $COMPLETED_COUNT,
  "total": $TOTAL,
  "source": "github",
  "instance_label": "$INSTANCE_LABEL",
  "parallel_safe": true
}
EOF

    exit 0
fi

# Fallback: Original PRD/Plan parsing mode (single-instance only)
# NOTE: This mode maintains a local ticket list and is NOT parallel-safe

# Validate inputs
if [ -z "$PRD_PATH" ] || [ -z "$PLAN_PATH" ]; then
    echo -e "${RED}Error: Missing arguments${NC}"
    echo "Usage: setup.sh <prd-path> <plan-path>"
    echo "       setup.sh --label <label>  (GitHub mode)"
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

# Build regex pattern using only the configured prefix
TICKET_PATTERN="${TICKET_PREFIX}-[0-9]+"

# Extract tickets from PRD (primary) and plan (fallback)
echo "Parsing tickets from PRD..."
TICKETS=$(grep -oE "$TICKET_PATTERN" "$PRD_PATH" 2>/dev/null | sort -u -t'-' -k2 -n)

if [ -z "$TICKETS" ]; then
    echo "No tickets in PRD, checking plan..."
    TICKETS=$(grep -oE "$TICKET_PATTERN" "$PLAN_PATH" 2>/dev/null | sort -u -t'-' -k2 -n)
fi

# Count tickets safely
if [ -z "$TICKETS" ]; then
    TICKET_COUNT=0
else
    TICKET_COUNT=$(echo "$TICKETS" | grep -c . 2>/dev/null || echo "0")
fi

if [ "$TICKET_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}Warning: No tickets found in PRD or plan${NC}"
    echo "Looking for pattern: $TICKET_PREFIX-XXXX"
    echo "Tip: Run /ticket to create tickets from the PRD"
    exit 1
fi

echo -e "${GREEN}Found $TICKET_COUNT tickets with prefix: $TICKET_PREFIX${NC}"

# Function to extract complexity for a ticket from markdown table
get_ticket_complexity() {
    local ticket_id="$1"
    local file="$2"

    local complexity=$(grep "$ticket_id" "$file" | head -1 | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $6); print $6}')

    if [[ "$complexity" =~ ^[1-5]$ ]]; then
        echo "$complexity"
    else
        echo "3"
    fi
}

# Build ticket array for JSON with complexity
TICKET_JSON="["
FIRST=true
while IFS= read -r ticket; do
    if [ -n "$ticket" ]; then
        COMPLEXITY=$(get_ticket_complexity "$ticket" "$PRD_PATH")
        if [ "$COMPLEXITY" = "3" ]; then
            PLAN_COMPLEXITY=$(get_ticket_complexity "$ticket" "$PLAN_PATH")
            if [ "$PLAN_COMPLEXITY" != "3" ]; then
                COMPLEXITY="$PLAN_COMPLEXITY"
            fi
        fi

        if [ "$FIRST" = true ]; then
            FIRST=false
        else
            TICKET_JSON+=","
        fi
        TICKET_JSON+="{\"id\":\"$ticket\",\"status\":\"pending\",\"pr\":null,\"attempts\":0,\"complexity\":$COMPLEXITY}"
    fi
done <<< "$TICKETS"
TICKET_JSON+="]"

# Initialize workflow-state.json
echo "Initializing workflow state..."

if [ ! -f "workflow-state.json" ]; then
    echo '{"phase":"idle","completed":[],"ralph":{"current":0,"total":0,"current_ticket":"","tickets":[],"blocked":[],"tickets_done":[]}}' > workflow-state.json
fi

# Get list of new ticket IDs
NEW_TICKET_IDS=$(echo "$TICKETS" | tr '\n' ',' | sed 's/,$//')
EXISTING_TICKET_IDS=$(jq -r '.ralph.tickets // [] | map(.id) | sort | join(",")' workflow-state.json 2>/dev/null || echo "")

FIRST_NEW_TICKET=$(echo "$TICKETS" | head -1)
FIRST_EXISTING_TICKET=$(jq -r '.ralph.tickets[0].id // ""' workflow-state.json 2>/dev/null || echo "")

NEW_PREFIX=$(echo "$FIRST_NEW_TICKET" | sed 's/-[0-9]*$//')
EXISTING_PREFIX=$(echo "$FIRST_EXISTING_TICKET" | sed 's/-[0-9]*$//')

TICKETS_CHANGED="false"
if [ "$NEW_PREFIX" != "$EXISTING_PREFIX" ]; then
    TICKETS_CHANGED="true"
    echo -e "${YELLOW}Different ticket prefix detected: $EXISTING_PREFIX → $NEW_PREFIX${NC}"
elif [ "$NEW_TICKET_IDS" != "$EXISTING_TICKET_IDS" ]; then
    TICKETS_CHANGED="true"
    echo -e "${YELLOW}Ticket list changed, starting fresh run${NC}"
fi

EXISTING_DONE=$(jq -r '.ralph.tickets_done // [] | length' workflow-state.json 2>/dev/null || echo "0")

if [ "$TICKETS_CHANGED" = "true" ]; then
    echo "Starting fresh run with new tickets..."
    jq --argjson count "$TICKET_COUNT" --argjson tickets "$TICKET_JSON" '
      .phase = "ralph" |
      .ralph.current = 0 |
      .ralph.total = $count |
      .ralph.current_ticket = null |
      .ralph.tickets = $tickets |
      .ralph.blocked = [] |
      .ralph.tickets_done = [] |
      .ralph.source = "local" |
      .completed = (.completed - ["report", "review", "ralph"])
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
elif [ "$EXISTING_DONE" -gt 0 ]; then
    echo -e "${GREEN}Resuming existing run with $EXISTING_DONE tickets already done${NC}"
    jq '.phase = "ralph" | .ralph.source = "local"' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
else
    echo "Starting fresh run..."
    jq --argjson count "$TICKET_COUNT" --argjson tickets "$TICKET_JSON" '
      .phase = "ralph" |
      .ralph.current = 0 |
      .ralph.total = $count |
      .ralph.current_ticket = null |
      .ralph.tickets = $tickets |
      .ralph.blocked = [] |
      .ralph.tickets_done = [] |
      .ralph.source = "local" |
      .completed = (.completed - ["report", "review", "ralph"])
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
fi

# Output summary
echo ""
echo "=== Setup Complete (Local Mode) ==="
echo -e "PRD: ${GREEN}$PRD_PATH${NC}"
echo -e "Plan: ${GREEN}$PLAN_PATH${NC}"
echo -e "Tickets: ${GREEN}$TICKET_COUNT${NC}"
echo ""
echo -e "${YELLOW}Warning: Local mode is NOT parallel-safe${NC}"
echo "Ticket list:"
echo "$TICKETS" | while read -r t; do echo "  - $t"; done
echo ""
echo "Next: LLM should start processing tickets"

# Output JSON for programmatic use
echo ""
echo "---JSON_OUTPUT---"
jq -c '.ralph' workflow-state.json
