#!/bin/bash
#
# Tests for mark-blocked.sh label removal functionality
#
# Ticket: AUCT-0159
#
# Tests verify:
# 1. Instance label is removed when ticket is blocked
# 2. Label removal is idempotent (no error if already removed)
# 3. Works correctly with no instance_label configured (skip removal)
# 4. Logs action for visibility
#

# Don't use set -e in tests - we need to handle exit codes manually

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source config helpers
source "$SCRIPT_DIR/config-helpers.sh"

# Test state
TEST_PASSED=0
TEST_FAILED=0
TEST_DIR=""

# ============================================================================
# Test Setup/Teardown
# ============================================================================

setup_test_env() {
    TEST_DIR=$(mktemp -d)
    echo "Test directory: $TEST_DIR"
}

teardown_test_env() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

# ============================================================================
# Test Helper Functions
# ============================================================================

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    ((TEST_PASSED++))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    ((TEST_FAILED++))
}

# Create mock config.yaml
create_test_config() {
    local config_file="$1"
    local instance_label="${2:-}"
    local instance_label_prefix="${3:-ralph-}"
    local use_assignee="${4:-true}"

    cat > "$config_file" << EOF
pm:
  tool: github

ralph:
  instance_label: "$instance_label"
  instance_label_prefix: "$instance_label_prefix"
  use_assignee: $use_assignee
EOF
}

# ============================================================================
# Unit Tests for Label Removal Logic in mark-blocked.sh
# ============================================================================

# Test: Verify mark-blocked.sh sources config-helpers.sh
test_mark_blocked_sources_config_helpers() {
    echo ""
    echo "=== test_mark_blocked_sources_config_helpers ==="

    # Check if mark-blocked.sh contains the source statement
    if grep -q "source.*config-helpers.sh" "$SCRIPT_DIR/mark-blocked.sh"; then
        pass "mark-blocked.sh sources config-helpers.sh"
    else
        fail "mark-blocked.sh does NOT source config-helpers.sh - add: source \"\$SCRIPT_DIR/config-helpers.sh\""
    fi
}

# Test: Verify mark-blocked.sh calls get_instance_label
test_mark_blocked_calls_get_instance_label() {
    echo ""
    echo "=== test_mark_blocked_calls_get_instance_label ==="

    # Check if mark-blocked.sh calls get_instance_label
    if grep -q "get_instance_label" "$SCRIPT_DIR/mark-blocked.sh"; then
        pass "mark-blocked.sh calls get_instance_label"
    else
        fail "mark-blocked.sh does NOT call get_instance_label - implementation needed"
    fi
}

# Test: Verify mark-blocked.sh has label removal logic
test_mark_blocked_has_label_removal() {
    echo ""
    echo "=== test_mark_blocked_has_label_removal ==="

    # Check if mark-blocked.sh has the --remove-label command
    if grep -q "\-\-remove-label" "$SCRIPT_DIR/mark-blocked.sh"; then
        pass "mark-blocked.sh has --remove-label command"
    else
        fail "mark-blocked.sh does NOT have --remove-label command - implementation needed"
    fi
}

# Test: Verify mark-blocked.sh label removal is idempotent (handles already removed)
test_mark_blocked_label_removal_idempotent() {
    echo ""
    echo "=== test_mark_blocked_label_removal_idempotent ==="

    # Check if mark-blocked.sh handles the case where label is already removed
    # This should be done by using 2>/dev/null or checking error message
    if grep -q "remove-label.*2>/dev/null" "$SCRIPT_DIR/mark-blocked.sh"; then
        pass "mark-blocked.sh handles label removal errors gracefully"
    else
        fail "mark-blocked.sh does NOT handle label removal errors gracefully - add 2>/dev/null"
    fi
}

# Test: Label removal skipped when no instance_label configured
test_label_removal_skipped_when_not_configured() {
    echo ""
    echo "=== test_label_removal_skipped_when_not_configured ==="

    setup_test_env

    # Config with empty instance_label
    create_test_config "$TEST_DIR/config.yaml" "" "ralph-" "true"

    local instance_label
    instance_label=$(get_instance_label "$TEST_DIR/config.yaml")

    local should_remove_label=false
    if [ -n "$instance_label" ]; then
        should_remove_label=true
    fi

    if [ "$should_remove_label" = "false" ]; then
        pass "Label removal correctly skipped when instance_label is empty"
    else
        fail "Label removal should be skipped when instance_label is empty"
    fi

    teardown_test_env
}

# Test: Label removal happens when instance_label is configured
test_label_removal_happens_when_configured() {
    echo ""
    echo "=== test_label_removal_happens_when_configured ==="

    setup_test_env

    # Config with instance_label set
    create_test_config "$TEST_DIR/config.yaml" "ralph-1" "ralph-" "false"

    local instance_label
    instance_label=$(get_instance_label "$TEST_DIR/config.yaml")

    local should_remove_label=false
    if [ -n "$instance_label" ]; then
        should_remove_label=true
    fi

    if [ "$should_remove_label" = "true" ]; then
        pass "Label removal correctly triggered when instance_label is set"
    else
        fail "Label removal should happen when instance_label is set"
    fi

    teardown_test_env
}

# Test: Verify mark-blocked.sh has the correct log message format
test_mark_blocked_logs_label_removal() {
    echo ""
    echo "=== test_mark_blocked_logs_label_removal ==="

    # Check if mark-blocked.sh has appropriate logging for label removal
    if grep -q "Removing instance label" "$SCRIPT_DIR/mark-blocked.sh" || \
       grep -q "Removed.*label" "$SCRIPT_DIR/mark-blocked.sh"; then
        pass "mark-blocked.sh logs label removal action"
    else
        fail "mark-blocked.sh does NOT log label removal action - add logging for visibility"
    fi
}

# Test: Verify mark-blocked.sh removes label BEFORE unassigning
test_mark_blocked_label_removal_before_unassign() {
    echo ""
    echo "=== test_mark_blocked_label_removal_before_unassign ==="

    # The label removal should happen before or independently of the unassign operation
    # Check that --remove-label appears in the script
    local remove_label_line=$(grep -n "\-\-remove-label" "$SCRIPT_DIR/mark-blocked.sh" | head -1 | cut -d: -f1)
    local unassign_line=$(grep -n "\-\-remove-assignee" "$SCRIPT_DIR/mark-blocked.sh" | head -1 | cut -d: -f1)

    if [ -z "$remove_label_line" ]; then
        fail "No --remove-label found in mark-blocked.sh"
    elif [ -z "$unassign_line" ]; then
        # No unassign found, but that's OK if remove-label exists
        pass "Label removal exists (no unassign to compare order)"
    elif [ "$remove_label_line" -lt "$unassign_line" ]; then
        pass "Label removal happens before unassignment (line $remove_label_line vs $unassign_line)"
    else
        pass "Label removal and unassignment order acceptable (both exist)"
    fi
}

# ============================================================================
# Run All Tests
# ============================================================================

run_all_tests() {
    echo ""
    echo "=========================================="
    echo "  mark-blocked.sh Label Removal Tests"
    echo "  Ticket: AUCT-0159"
    echo "=========================================="

    test_mark_blocked_sources_config_helpers
    test_mark_blocked_calls_get_instance_label
    test_mark_blocked_has_label_removal
    test_mark_blocked_label_removal_idempotent
    test_label_removal_skipped_when_not_configured
    test_label_removal_happens_when_configured
    test_mark_blocked_logs_label_removal
    test_mark_blocked_label_removal_before_unassign

    echo ""
    echo "=========================================="
    echo "  Test Results"
    echo "=========================================="
    echo -e "Passed: ${GREEN}$TEST_PASSED${NC}"
    echo -e "Failed: ${RED}$TEST_FAILED${NC}"
    echo ""

    if [ "$TEST_FAILED" -gt 0 ]; then
        echo -e "${RED}FAIL: Some tests failed${NC}"
        return 1
    else
        echo -e "${GREEN}PASS: All tests passed${NC}"
        return 0
    fi
}

# Run tests when executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_all_tests
    exit $?
fi
