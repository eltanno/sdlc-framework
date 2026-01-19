#!/bin/bash
# Ralph Setup - Initialize ralph run before any LLM work
# Usage: setup.sh [<prd-path> <plan-path>] [--label <label>]
#
# What this does:
# 1. Check config.yaml for PM tool setting (must be github)
# 2. Validate GitHub access
# 3. Get initial ticket counts for display
# 4. Initialize workflow-state.json phase
#
# NOTE: This is intentionally lightweight for parallel execution.
# The loop uses get-next-ticket.sh which queries GitHub in real-time.
# GitHub Issues are always the source of truth.

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

# Use PROJECT_ROOT if passed from parent, otherwise use pwd
# This allows the same script to be used across multiple worktrees
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source config helpers for label functions
source "$SCRIPT_DIR/config-helpers.sh"

echo "=== Ralph Setup ==="

# Check PM tool from config.yaml - must be github
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

if [ "$PM_TOOL" != "github" ]; then
    echo -e "${RED}Error: pm.tool must be 'github' in config.yaml${NC}"
    echo "GitHub Issues is the only supported PM tool for ralph."
    exit 1
fi

# Detect ticket prefix from plan file (if provided), otherwise use config.yaml
TICKET_PREFIX=""
if [ -n "$PLAN_PATH" ] && [ -f "$PLAN_PATH" ]; then
    # Auto-detect prefix from plan file (first ticket ID found)
    FIRST_TICKET=$(grep -oE '[A-Z]+-[0-9]+' "$PLAN_PATH" 2>/dev/null | head -1)
    if [ -n "$FIRST_TICKET" ]; then
        TICKET_PREFIX=$(echo "$FIRST_TICKET" | sed 's/-[0-9]*$//')
        echo "Detected ticket prefix from plan: $TICKET_PREFIX"
    fi
fi
# Fall back to config.yaml if not detected from plan
if [ -z "$TICKET_PREFIX" ] && [ -f "config.yaml" ]; then
    TICKET_PREFIX=$(grep -E '^\s*prefix:' config.yaml | head -1 | sed 's/.*prefix:\s*"\?\([^"]*\)"\?.*/\1/' | tr -d ' "')
fi
if [ -z "$TICKET_PREFIX" ]; then
    echo -e "${RED}Error: No ticket prefix found in plan or config.yaml${NC}"
    echo "Either provide a plan file with ticket IDs, or add 'tickets.prefix' to config.yaml"
    exit 1
fi

echo "Using GitHub Issues as source of truth..."

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: gh CLI not found${NC}" >&2
    echo "Install gh CLI: https://cli.github.com/" >&2
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
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null)
if ! gh api "repos/$REPO/labels" --jq '.[].name' 2>/dev/null | grep -q "^${INSTANCE_LABEL}$"; then
    echo "Creating label '${INSTANCE_LABEL}'..."
    gh api "repos/$REPO/labels" -f name="$INSTANCE_LABEL" -f description="Ralph instance label" -f color="0052CC" >/dev/null 2>&1 || true
fi

# Check for existing in-progress work with this label
INSTANCE_OPEN_COUNT=$(gh issue list --label "$INSTANCE_LABEL" --state open --json number --jq 'length')

if [[ "$INSTANCE_OPEN_COUNT" -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Notice: Label '$INSTANCE_LABEL' has $INSTANCE_OPEN_COUNT open issue(s).${NC}"
    echo "Resuming existing work with this label..."
fi

# Get counts from GitHub (lightweight query - just for display)
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

# Set phase to ralph
jq '.phase = "ralph" | .ralph.source = "github"' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Parse and store ticket list AND dependencies from plan document (if provided)
if [ -n "$PLAN_PATH" ] && [ -f "$PLAN_PATH" ]; then
    echo "Parsing tickets and dependencies from plan..."
    # Get dependencies and compact to single line (avoids bash variable issues with newlines)
    DEPS_JSON=$("$SCRIPT_DIR/parse-plan-deps.sh" "$PLAN_PATH" "$TICKET_PREFIX" 2>/dev/null | jq -c '.' || echo "{}")

    if [ "$DEPS_JSON" != "{}" ]; then
        # Extract ticket IDs (the keys from dependencies object)
        TICKET_LIST=$(echo "$DEPS_JSON" | jq -c 'keys')
        TICKET_COUNT=$(echo "$DEPS_JSON" | jq 'length')

        # Store both ticket list AND dependencies in workflow-state.json
        jq --argjson deps "$DEPS_JSON" --argjson tickets "$TICKET_LIST" '
            .ralph.dependencies = $deps |
            .ralph.tickets = $tickets
        ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

        echo -e "${GREEN}Loaded $TICKET_COUNT tickets from plan${NC}"
    else
        echo -e "${YELLOW}No tickets found in plan (or parse failed)${NC}"
        echo "The loop will fall back to querying all 'task' labeled issues"
    fi
else
    echo -e "${YELLOW}No plan path provided - will query all 'task' labeled issues${NC}"
    echo "Tip: Pass plan path to scope the loop to specific tickets"
fi

# Get ticket count from stored list (or fall back to available count)
PLAN_TICKET_COUNT=$(jq -r '.ralph.tickets // [] | length' workflow-state.json 2>/dev/null || echo "0")

# Output summary
echo ""
echo "=== Setup Complete ==="
echo -e "Source: ${GREEN}GitHub Issues${NC}"
echo -e "Instance Label: ${GREEN}$INSTANCE_LABEL${NC}"
if [ "$PLAN_TICKET_COUNT" -gt 0 ]; then
    echo -e "Tickets from plan: ${GREEN}$PLAN_TICKET_COUNT${NC}"
    echo -e "In Progress: ${GREEN}$IN_PROGRESS_COUNT${NC} (tickets with '$INSTANCE_LABEL' label)"
else
    echo -e "Available: ${GREEN}$AVAILABLE_COUNT${NC} (tickets with 'task' label)"
    echo -e "In Progress: ${GREEN}$IN_PROGRESS_COUNT${NC} (tickets with '$INSTANCE_LABEL' label)"
    echo -e "Completed: ${GREEN}$COMPLETED_COUNT${NC}"
fi
echo ""
echo "Mode: Parallel-safe (GitHub is source of truth)"
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
