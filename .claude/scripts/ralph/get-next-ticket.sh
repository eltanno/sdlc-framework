#!/bin/bash
# Ralph Get Next Ticket - Find the next pending ticket
# Usage: get-next-ticket.sh [--label <label>]
#
# What this does:
# 1. Check config.yaml for PM tool setting
# 2. If GitHub: Query GitHub Issues for next available ticket
#    - First: issues assigned to current user (resume in-progress)
#    - Then: oldest unassigned open issue
# 3. If not GitHub: Fall back to workflow-state.json
# 4. Output ticket info
#
# Supports concurrent Ralph instances - GitHub assignment is atomic

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

# Load .env if present (for RALPH_LABEL)
if [ -f .env ]; then
    set -a  # auto-export variables
    source .env
    set +a
fi

# Source config helpers for label-based concurrency
source "$SCRIPT_DIR/config-helpers.sh"

# Parse arguments
LABEL_FILTER=""
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

# Check PM tool from config.yaml
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

# Helper: Extract ticket ID from issue title (format: "[AUCT-0133] Description")
extract_ticket_id() {
    local title="$1"
    echo "$title" | grep -oE '\[[A-Z]+-[0-9]+\]' | tr -d '[]' | head -1
}

# Helper: Check if all dependencies for a ticket are satisfied (closed)
# Returns 0 if all deps are met, 1 if any dep is still open
check_dependencies_met() {
    local ticket_id="$1"

    # Get dependencies from workflow-state.json
    if [ ! -f "workflow-state.json" ]; then
        # No state file, assume no dependencies
        return 0
    fi

    local deps=$(jq -r --arg id "$ticket_id" '.ralph.dependencies[$id] // [] | .[]' workflow-state.json 2>/dev/null)

    if [ -z "$deps" ]; then
        # No dependencies
        return 0
    fi

    # Check each dependency
    for dep_id in $deps; do
        # Look up the GitHub issue number for this dependency
        # Search for issue with this ticket ID in title
        local dep_issue=$(gh issue list --state all --search "$dep_id in:title" --json number,state --limit 1 2>/dev/null)
        local dep_state=$(echo "$dep_issue" | jq -r '.[0].state // "OPEN"')

        if [ "$dep_state" != "CLOSED" ]; then
            # Dependency not yet closed
            echo -e "${YELLOW}  Dependency $dep_id is not closed (state: $dep_state)${NC}" >&2
            return 1
        fi
    done

    # All dependencies met
    return 0
}

# Helper: Get list of unmet dependencies for a ticket
get_unmet_dependencies() {
    local ticket_id="$1"
    local unmet=""

    if [ ! -f "workflow-state.json" ]; then
        return
    fi

    local deps=$(jq -r --arg id "$ticket_id" '.ralph.dependencies[$id] // [] | .[]' workflow-state.json 2>/dev/null)

    for dep_id in $deps; do
        local dep_issue=$(gh issue list --state all --search "$dep_id in:title" --json number,state --limit 1 2>/dev/null)
        local dep_state=$(echo "$dep_issue" | jq -r '.[0].state // "OPEN"')

        if [ "$dep_state" != "CLOSED" ]; then
            if [ -n "$unmet" ]; then
                unmet="$unmet, $dep_id"
            else
                unmet="$dep_id"
            fi
        fi
    done

    echo "$unmet"
}

# GitHub-based ticket lookup
if [ "$PM_TOOL" = "github" ]; then
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

    # Get current GitHub user
    CURRENT_USER=$(gh api user --jq '.login' 2>/dev/null || echo "")

    # Get label-based concurrency settings
    INSTANCE_LABEL=$(get_instance_label)
    INSTANCE_LABEL_PREFIX=$(get_instance_label_prefix)
    USE_ASSIGNEE=$(get_use_assignee)

    # Build label filter for gh command
    LABEL_ARG=""
    if [ -n "$LABEL_FILTER" ]; then
        LABEL_ARG="--label $LABEL_FILTER"
    fi

    # PHASE 1: Check for issues with OWN instance label (resume in-progress work)
    # This takes priority - if we started something, finish it
    if [ -n "$INSTANCE_LABEL" ]; then
        OWN_LABELED_ISSUE=$(gh issue list --state open --label "$INSTANCE_LABEL" $LABEL_ARG --json number,title --limit 1 2>/dev/null || echo "[]")
        OWN_LABELED_NUMBER=$(echo "$OWN_LABELED_ISSUE" | jq -r '.[0].number // empty')
        OWN_LABELED_TITLE=$(echo "$OWN_LABELED_ISSUE" | jq -r '.[0].title // empty')

        if [ -n "$OWN_LABELED_NUMBER" ]; then
            TICKET_ID=$(extract_ticket_id "$OWN_LABELED_TITLE")
            ISSUE_NUMBER="$OWN_LABELED_NUMBER"
            echo -e "${YELLOW}Resuming own labeled issue #$ISSUE_NUMBER (label: $INSTANCE_LABEL)${NC}"
        fi
    fi

    # PHASE 2: Check for issues assigned to current user (resume in-progress work)
    # Only if use_assignee is enabled and we didn't find own labeled issue
    if [ -z "$ISSUE_NUMBER" ] && [ "$USE_ASSIGNEE" = "true" ] && [ -n "$CURRENT_USER" ]; then
        ASSIGNED_ISSUE=$(gh issue list --state open --assignee "$CURRENT_USER" $LABEL_ARG --json number,title --limit 1 2>/dev/null || echo "[]")
        ASSIGNED_NUMBER=$(echo "$ASSIGNED_ISSUE" | jq -r '.[0].number // empty')
        ASSIGNED_TITLE=$(echo "$ASSIGNED_ISSUE" | jq -r '.[0].title // empty')

        if [ -n "$ASSIGNED_NUMBER" ]; then
            TICKET_ID=$(extract_ticket_id "$ASSIGNED_TITLE")
            ISSUE_NUMBER="$ASSIGNED_NUMBER"
            echo -e "${YELLOW}Resuming assigned issue #$ISSUE_NUMBER${NC}"
        fi
    fi

    # PHASE 3: If no in-progress issue, find oldest available open issue
    # Filters: unassigned, not blocked, AND no ralph-* labels (to avoid other instances' work)
    if [ -z "$ISSUE_NUMBER" ]; then
        # Get blocked ticket IDs from local state (to skip them)
        BLOCKED_IDS=""
        if [ -f "workflow-state.json" ]; then
            BLOCKED_IDS=$(jq -r '.ralph.blocked[]?.id // empty' workflow-state.json 2>/dev/null | tr '\n' '|' | sed 's/|$//')
        fi

        # Get all open issues, sorted by created (oldest first)
        # Filter for:
        # 1. Unassigned (if use_assignee is true) OR all (if use_assignee is false)
        # 2. No "blocked" label
        # 3. No ralph-* labels (skip issues claimed by any Ralph instance)
        ALL_ISSUES_JSON=$(gh issue list --state open $LABEL_ARG --json number,title,assignees,labels --limit 100 2>/dev/null || echo "[]")

        # Build jq filter based on use_assignee setting
        if [ "$USE_ASSIGNEE" = "true" ]; then
            # Filter out assigned issues
            JQ_FILTER='[.[] | select(.assignees | length == 0) | select(.labels | map(.name) | index("blocked") | not) | select((.labels | map(.name) | map(select(startswith($prefix)))) | length == 0)] | sort_by(.number) | .[] | "\(.number)\t\(.title)"'
        else
            # Don't filter by assignee (multi-instance mode with same user)
            JQ_FILTER='[.[] | select(.labels | map(.name) | index("blocked") | not) | select((.labels | map(.name) | map(select(startswith($prefix)))) | length == 0)] | sort_by(.number) | .[] | "\(.number)\t\(.title)"'
        fi

        ALL_AVAILABLE=$(echo "$ALL_ISSUES_JSON" | jq -r --arg prefix "$INSTANCE_LABEL_PREFIX" "$JQ_FILTER" 2>/dev/null || echo "")

        # Track if we skipped any tickets due to unmet dependencies
        SKIPPED_FOR_DEPS=0

        # Find first non-blocked ticket with met dependencies
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            CANDIDATE_NUMBER=$(echo "$line" | cut -f1)
            CANDIDATE_TITLE=$(echo "$line" | cut -f2-)
            CANDIDATE_ID=$(extract_ticket_id "$CANDIDATE_TITLE")

            # Skip if this ticket is in the blocked list
            if [ -n "$BLOCKED_IDS" ] && echo "$CANDIDATE_ID" | grep -qE "^($BLOCKED_IDS)$"; then
                echo -e "${YELLOW}Skipping blocked ticket: $CANDIDATE_ID (#$CANDIDATE_NUMBER)${NC}" >&2
                continue
            fi

            # Check if dependencies are met
            if ! check_dependencies_met "$CANDIDATE_ID"; then
                UNMET=$(get_unmet_dependencies "$CANDIDATE_ID")
                echo -e "${YELLOW}Skipping $CANDIDATE_ID (#$CANDIDATE_NUMBER) - waiting on: $UNMET${NC}" >&2
                SKIPPED_FOR_DEPS=$((SKIPPED_FOR_DEPS + 1))
                continue
            fi

            # Found a valid ticket - CLAIM IT IMMEDIATELY by adding our label
            # This prevents race conditions where another instance picks the same ticket
            if gh issue edit "$CANDIDATE_NUMBER" --add-label "$INSTANCE_LABEL" 2>/dev/null; then
                # Verify we're the ONLY ralph-* label (another instance may have also claimed it)
                sleep 0.5  # Brief pause to let any concurrent claim settle
                OTHER_RALPH_LABELS=$(gh issue view "$CANDIDATE_NUMBER" --json labels --jq ".labels[].name | select(startswith(\"$INSTANCE_LABEL_PREFIX\")) | select(. != \"$INSTANCE_LABEL\")" 2>/dev/null)

                if [ -n "$OTHER_RALPH_LABELS" ]; then
                    # Another instance also claimed this - we lost the race
                    # Remove our label and try the next ticket
                    echo -e "${YELLOW}Race condition: #$CANDIDATE_NUMBER also has label '$OTHER_RALPH_LABELS', removing ours...${NC}" >&2
                    gh issue edit "$CANDIDATE_NUMBER" --remove-label "$INSTANCE_LABEL" 2>/dev/null || true
                    continue
                fi

                ISSUE_NUMBER="$CANDIDATE_NUMBER"
                ISSUE_TITLE="$CANDIDATE_TITLE"
                TICKET_ID="$CANDIDATE_ID"
                echo -e "${GREEN}Claimed ticket #$CANDIDATE_NUMBER with label '$INSTANCE_LABEL'${NC}" >&2
                break
            else
                # Failed to claim - another instance may have grabbed it, try next
                echo -e "${YELLOW}Failed to claim #$CANDIDATE_NUMBER, trying next...${NC}" >&2
                continue
            fi
        done <<< "$ALL_AVAILABLE"
    fi

    # Get counts from GitHub
    TOTAL_OPEN=$(gh issue list --state open $LABEL_ARG --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
    TOTAL_CLOSED=$(gh issue list --state closed $LABEL_ARG --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
    TOTAL=$((TOTAL_OPEN + TOTAL_CLOSED))
    CURRENT=$TOTAL_CLOSED
    PENDING=$TOTAL_OPEN

    # Count blocked (issues with 'blocked' label - may not exist)
    BLOCKED=$(gh issue list --state open --label blocked $LABEL_ARG --json number --limit 1000 2>/dev/null | jq 'length' 2>/dev/null || echo "0")

    if [ -n "$TICKET_ID" ] && [ -n "$ISSUE_NUMBER" ]; then
        echo -e "Next: ${GREEN}$TICKET_ID${NC} (GitHub #$ISSUE_NUMBER)"
        echo "Progress: $CURRENT/$TOTAL ($PENDING pending, $BLOCKED blocked)"

        echo ""
        echo "---JSON_OUTPUT---"
        cat << EOF
{
  "next_ticket": "$TICKET_ID",
  "issue_number": $ISSUE_NUMBER,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": $PENDING,
  "blocked": $BLOCKED,
  "has_more": true,
  "status": "ready",
  "source": "github"
}
EOF
        exit 0
    elif [ "${SKIPPED_FOR_DEPS:-0}" -gt 0 ]; then
        # Tickets exist but are waiting on dependencies
        echo -e "${YELLOW}All available tickets are waiting on dependencies${NC}"
        echo "Skipped $SKIPPED_FOR_DEPS ticket(s) due to unmet dependencies"
        echo "Progress: $CURRENT/$TOTAL ($BLOCKED blocked)"

        echo ""
        echo "---JSON_OUTPUT---"
        cat << EOF
{
  "next_ticket": null,
  "issue_number": null,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": $PENDING,
  "blocked": $BLOCKED,
  "has_more": true,
  "status": "waiting_on_dependencies",
  "skipped_for_deps": $SKIPPED_FOR_DEPS,
  "source": "github"
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
  "issue_number": null,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": 0,
  "blocked": $BLOCKED,
  "has_more": false,
  "status": "complete",
  "source": "github"
}
EOF
        exit 0
    fi
fi

# Fallback: Use workflow-state.json (original behavior)
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
  "issue_number": null,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": $PENDING,
  "blocked": $BLOCKED,
  "has_more": true,
  "status": "ready",
  "source": "local"
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
  "issue_number": null,
  "current": $CURRENT,
  "total": $TOTAL,
  "pending": 0,
  "blocked": $BLOCKED,
  "has_more": false,
  "status": "complete",
  "source": "local"
}
EOF
    exit 0
fi
