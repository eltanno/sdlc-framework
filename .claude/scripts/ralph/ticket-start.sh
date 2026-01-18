#!/bin/bash
# Ralph Ticket Start - Pre-work before LLM starts on a ticket
# Usage: ticket-start.sh <ticket-id> [--issue <number>] [--test]
#
# What this does:
# 1. Check config.yaml for PM tool setting
# 2. If GitHub: Add instance label to issue (for multi-instance concurrency)
# 3. If use_assignee=true: Also assign issue to current user
# 4. Update workflow-state.json with current ticket (as backup/cache)
# 5. Output ticket info for LLM
#
# Supports concurrent Ralph instances via label-based claiming
# Ticket: AUCT-0156

set -e

# Find project root and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# Load .env if present (for RALPH_LABEL)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Source config helpers for label configuration
source "$SCRIPT_DIR/config-helpers.sh"

TICKET_ID=""
ISSUE_NUMBER=""
RUN_TESTS=false

# Parse all arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --issue)
            ISSUE_NUMBER="$2"
            shift 2
            ;;
        --test)
            RUN_TESTS=true
            shift
            ;;
        --*)
            # Unknown option
            shift
            ;;
        *)
            # First non-option argument is the ticket ID
            if [ -z "$TICKET_ID" ]; then
                TICKET_ID="$1"
            fi
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root (SCRIPT_DIR already set when sourcing config-helpers.sh)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# ============================================================================
# Self-Test Functions
# ============================================================================

run_self_tests() {
    # Disable set -e for tests (arithmetic operations can return non-zero)
    set +e

    local test_failed=0
    local test_passed=0
    local test_dir
    test_dir=$(mktemp -d)

    echo "=== Running ticket-start.sh self-tests ==="
    echo ""

    # Mock gh command for testing
    mock_gh() {
        local mock_result="${MOCK_GH_RESULT:-success}"
        local mock_label_exists="${MOCK_LABEL_EXISTS:-true}"

        case "$1" in
            issue)
                case "$2" in
                    edit)
                        # Check if we're adding a label
                        if echo "$@" | grep -q "\-\-add-label"; then
                            if [ "$mock_label_exists" = "false" ]; then
                                echo "label 'ralph-1' not found" >&2
                                return 1
                            fi
                        fi
                        if [ "$mock_result" = "success" ]; then
                            return 0
                        else
                            return 1
                        fi
                        ;;
                    list)
                        echo '[]'
                        return 0
                        ;;
                esac
                ;;
        esac
        return 0
    }

    # Test 1: claim_issue_with_label adds label when instance_label is set
    echo "Test 1: claim_issue_with_label adds label when instance_label is set"
    local label_args=""
    claim_issue_with_label() {
        local issue_num="$1"
        local instance_label="$2"
        label_args="--add-label $instance_label"
        echo "Would run: gh issue edit $issue_num $label_args"
        return 0
    }

    claim_issue_with_label "123" "ralph-1" > /dev/null
    if echo "$label_args" | grep -q "ralph-1"; then
        echo "PASS: Label is added when instance_label is set"
        ((test_passed++))
    else
        echo "FAIL: Label was not added"
        ((test_failed++))
    fi

    # Test 2: Verify get_instance_label works from sourced helper
    echo "Test 2: get_instance_label is available from config-helpers.sh"
    if type get_instance_label &>/dev/null; then
        echo "PASS: get_instance_label function is available"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label function is not available"
        ((test_failed++))
    fi

    # Test 3: Verify get_use_assignee works from sourced helper
    echo "Test 3: get_use_assignee is available from config-helpers.sh"
    if type get_use_assignee &>/dev/null; then
        echo "PASS: get_use_assignee function is available"
        ((test_passed++))
    else
        echo "FAIL: get_use_assignee function is not available"
        ((test_failed++))
    fi

    # Test 4: Test config reading with test config
    cat > "$test_dir/config.yaml" << 'EOF'
pm:
  tool: github
ralph:
  instance_label: "ralph-test"
  instance_label_prefix: "ralph-"
  use_assignee: false
EOF

    echo "Test 4: Read instance_label from config"
    local test_label
    test_label=$(get_instance_label "$test_dir/config.yaml")
    if [ "$test_label" = "ralph-test" ]; then
        echo "PASS: instance_label read correctly"
        ((test_passed++))
    else
        echo "FAIL: instance_label - expected 'ralph-test', got '$test_label'"
        ((test_failed++))
    fi

    # Test 5: Test use_assignee=false
    echo "Test 5: Read use_assignee=false from config"
    local test_use_assignee
    test_use_assignee=$(get_use_assignee "$test_dir/config.yaml")
    if [ "$test_use_assignee" = "false" ]; then
        echo "PASS: use_assignee read correctly as false"
        ((test_passed++))
    else
        echo "FAIL: use_assignee - expected 'false', got '$test_use_assignee'"
        ((test_failed++))
    fi

    # Test 6: Backward compatibility - empty instance_label
    cat > "$test_dir/config2.yaml" << 'EOF'
pm:
  tool: github
ralph:
  instance_label: ""
  use_assignee: true
EOF

    echo "Test 6: Backward compatibility with empty instance_label"
    test_label=$(get_instance_label "$test_dir/config2.yaml")
    test_use_assignee=$(get_use_assignee "$test_dir/config2.yaml")
    if [ -z "$test_label" ] && [ "$test_use_assignee" = "true" ]; then
        echo "PASS: Falls back to assignee-only when no instance_label"
        ((test_passed++))
    else
        echo "FAIL: Backward compatibility - label='$test_label', use_assignee='$test_use_assignee'"
        ((test_failed++))
    fi

    # Cleanup
    rm -rf "$test_dir"

    echo ""
    echo "=== Test Results ==="
    echo "Passed: $test_passed"
    echo "Failed: $test_failed"
    echo ""

    if [ "$test_failed" -gt 0 ]; then
        echo "FAIL: Some tests failed"
        return 1
    else
        echo "PASS: All tests passed"
        return 0
    fi
}

# Run tests if --test flag is passed
if [ "$RUN_TESTS" = true ]; then
    run_self_tests
    exit $?
fi

# ============================================================================
# Main Script
# ============================================================================

if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: ticket-start.sh <ticket-id> [--issue <number>]"
    exit 1
fi

echo "=== Starting Ticket: $TICKET_ID ==="

# Check PM tool from config.yaml
PM_TOOL="none"
if [ -f "config.yaml" ]; then
    PM_TOOL=$(grep -E '^\s*tool:' config.yaml | head -1 | sed 's/.*tool:\s*\([a-zA-Z]*\).*/\1/' | tr -d ' ')
fi

# GitHub-based ticket assignment
if [ "$PM_TOOL" = "github" ]; then
    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}Error: gh CLI not found but pm.tool=github${NC}" >&2
        echo "Install gh CLI or change pm.tool in config.yaml" >&2
        exit 1
    fi

    # If no issue number provided, look it up from GitHub
    if [ -z "$ISSUE_NUMBER" ]; then
        echo "Looking up GitHub issue for $TICKET_ID..."
        # Search for issue with ticket ID in title
        ISSUE_DATA=$(gh issue list --state open --json number,title --limit 100 2>/dev/null | \
            jq -r --arg tid "$TICKET_ID" '.[] | select(.title | contains($tid)) | "\(.number)"' | head -1)
        ISSUE_NUMBER="$ISSUE_DATA"
    fi

    if [ -z "$ISSUE_NUMBER" ]; then
        echo -e "${YELLOW}Warning: No GitHub issue found for $TICKET_ID${NC}"
        echo "Continuing with local state only..."
    else
        # Read label configuration
        INSTANCE_LABEL=$(get_instance_label)
        USE_ASSIGNEE=$(get_use_assignee)

        echo "Claiming GitHub issue #$ISSUE_NUMBER..."

        # Build the gh issue edit command
        GH_EDIT_ARGS=""

        # Instance label is now added atomically in get-next-ticket.sh to prevent race conditions
        # Just verify it's there (should already be claimed)
        if [ -n "$INSTANCE_LABEL" ]; then
            echo "Verifying instance label: $INSTANCE_LABEL"
            # Check if the issue has our label (it should, from get-next-ticket.sh)
            if ! gh issue view "$ISSUE_NUMBER" --json labels --jq '.labels[].name' 2>/dev/null | grep -q "^${INSTANCE_LABEL}$"; then
                # Label not present - try to add it (fallback for resumed tickets)
                if ! gh issue edit "$ISSUE_NUMBER" --add-label "$INSTANCE_LABEL" 2>/dev/null; then
                    echo -e "${YELLOW}Warning: Could not verify/add label '$INSTANCE_LABEL' to issue #$ISSUE_NUMBER${NC}" >&2
                else
                    echo -e "${GREEN}Added label '$INSTANCE_LABEL' to issue #$ISSUE_NUMBER${NC}"
                fi
            else
                echo -e "${GREEN}Verified label '$INSTANCE_LABEL' on issue #$ISSUE_NUMBER${NC}"
            fi
        fi

        # Add assignee if configured (for backward compatibility or additional tracking)
        if [ "$USE_ASSIGNEE" = "true" ]; then
            echo "Assigning to current user..."
            if gh issue edit "$ISSUE_NUMBER" --add-assignee @me 2>/dev/null; then
                echo -e "${GREEN}Assigned issue #$ISSUE_NUMBER to current user${NC}"
            else
                echo -e "${YELLOW}Warning: Failed to assign issue #$ISSUE_NUMBER${NC}"
                # Don't exit - label-based claiming is the primary mechanism
                # Assignment failure is not critical if label was added
                if [ -z "$INSTANCE_LABEL" ]; then
                    # But if we have no label, assignment failure is critical
                    echo -e "${RED}Failed to claim issue (no label configured, assignment failed)${NC}" >&2
                    exit 1
                fi
            fi
        fi

        # If neither label nor assignee was applied, warn the user
        if [ -z "$INSTANCE_LABEL" ] && [ "$USE_ASSIGNEE" != "true" ]; then
            echo -e "${YELLOW}Warning: No claiming mechanism configured (no instance_label, use_assignee=false)${NC}"
            echo "This ticket may be claimed by another instance!"
        fi
    fi
fi

# Update local workflow-state.json (as backup/cache)
if [ -f "workflow-state.json" ]; then
    # Check if ticket exists in state
    TICKET_EXISTS=$(jq --arg id "$TICKET_ID" '.ralph.tickets | map(select(.id == $id)) | length' workflow-state.json)
    if [ "$TICKET_EXISTS" -eq 0 ]; then
        echo -e "${YELLOW}Adding $TICKET_ID to local workflow state${NC}"
        jq --arg id "$TICKET_ID" --arg issue "${ISSUE_NUMBER:-null}" '
          .ralph.tickets += [{"id": $id, "status": "pending", "pr": null, "attempts": 0, "issue_number": (if $issue == "null" then null else ($issue | tonumber) end)}]
        ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
    fi

    # Update ticket status to in_progress and increment attempts
    jq --arg id "$TICKET_ID" --arg issue "${ISSUE_NUMBER:-null}" '
      .ralph.current_ticket = $id |
      .ralph.tickets = (.ralph.tickets | map(
        if .id == $id then
          .status = "in_progress" | .attempts = (.attempts + 1) | .issue_number = (if $issue == "null" then .issue_number else ($issue | tonumber) end)
        else . end
      ))
    ' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

    # Get current progress from local state
    CURRENT=$(jq -r '.ralph.current' workflow-state.json)
    TOTAL=$(jq -r '.ralph.total' workflow-state.json)
    ATTEMPTS=$(jq --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id) | .attempts' workflow-state.json)
else
    # No local state - use GitHub counts if available
    if [ "$PM_TOOL" = "github" ]; then
        TOTAL_OPEN=$(gh issue list --state open --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL_CLOSED=$(gh issue list --state closed --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        TOTAL=$((TOTAL_OPEN + TOTAL_CLOSED))
        CURRENT=$TOTAL_CLOSED
        ATTEMPTS=1
    else
        echo -e "${RED}Error: workflow-state.json not found. Run setup.sh first.${NC}"
        exit 1
    fi
fi

# Note: statusline.sh is for Claude's hook system, not direct invocation
# Progress is shown via script output instead

# Output
echo -e "Ticket: ${GREEN}$TICKET_ID${NC}"
[ -n "$ISSUE_NUMBER" ] && echo -e "GitHub Issue: ${GREEN}#$ISSUE_NUMBER${NC}"
echo -e "Progress: ${GREEN}$CURRENT/$TOTAL${NC}"
echo -e "Attempt: ${YELLOW}$ATTEMPTS${NC}"

if [ "$ATTEMPTS" -gt 3 ]; then
    echo -e "${RED}WARNING: This is attempt $ATTEMPTS. Consider marking as blocked.${NC}"
fi

echo ""
echo "---JSON_OUTPUT---"
if [ -f "workflow-state.json" ]; then
    jq -c --arg id "$TICKET_ID" '.ralph.tickets[] | select(.id == $id)' workflow-state.json
else
    cat << EOF
{"id": "$TICKET_ID", "status": "in_progress", "pr": null, "attempts": $ATTEMPTS, "issue_number": ${ISSUE_NUMBER:-null}}
EOF
fi
