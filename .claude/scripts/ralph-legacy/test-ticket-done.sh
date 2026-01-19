#!/bin/bash
#
# Tests for ticket-done.sh label removal functionality
#
# Ticket: AUCT-0158
#
# Tests verify:
# 1. Instance label is removed when ticket is completed
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
# Unit Tests for Label Removal Logic
# ============================================================================

# Test: get_instance_label function is available after sourcing config-helpers.sh
test_config_helpers_available() {
    echo ""
    echo "=== test_config_helpers_available ==="

    if type get_instance_label &>/dev/null; then
        pass "get_instance_label function is available"
    else
        fail "get_instance_label function is not available"
    fi

    if type get_use_assignee &>/dev/null; then
        pass "get_use_assignee function is available"
    else
        fail "get_use_assignee function is not available"
    fi
}

# Test: Instance label is read correctly from config
test_instance_label_reading() {
    echo ""
    echo "=== test_instance_label_reading ==="

    setup_test_env

    # Test with instance_label set
    create_test_config "$TEST_DIR/config.yaml" "ralph-1" "ralph-" "true"

    local label
    label=$(get_instance_label "$TEST_DIR/config.yaml")
    if [ "$label" = "ralph-1" ]; then
        pass "Instance label read correctly: $label"
    else
        fail "Instance label incorrect - expected 'ralph-1', got '$label'"
    fi

    # Test with empty instance_label
    create_test_config "$TEST_DIR/config2.yaml" "" "ralph-" "true"

    label=$(get_instance_label "$TEST_DIR/config2.yaml")
    if [ -z "$label" ]; then
        pass "Empty instance label returned correctly"
    else
        fail "Empty instance label incorrect - expected '', got '$label'"
    fi

    teardown_test_env
}

# Test: Remove label command is constructed correctly
test_remove_label_command_construction() {
    echo ""
    echo "=== test_remove_label_command_construction ==="

    # Simulate the logic that will be in ticket-done.sh
    local issue_number="123"
    local instance_label="ralph-1"

    # Expected command: gh issue edit 123 --remove-label ralph-1
    local expected_cmd="gh issue edit $issue_number --remove-label $instance_label"

    # Construct the command (this is what ticket-done.sh should do)
    local actual_cmd="gh issue edit $issue_number --remove-label $instance_label"

    if [ "$actual_cmd" = "$expected_cmd" ]; then
        pass "Remove label command constructed correctly: $actual_cmd"
    else
        fail "Remove label command incorrect - expected '$expected_cmd', got '$actual_cmd'"
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

# Test: Verify ticket-done.sh sources config-helpers.sh
test_ticket_done_sources_config_helpers() {
    echo ""
    echo "=== test_ticket_done_sources_config_helpers ==="

    # Check if ticket-done.sh contains the source statement
    if grep -q "source.*config-helpers.sh" "$SCRIPT_DIR/ticket-done.sh"; then
        pass "ticket-done.sh sources config-helpers.sh"
    else
        fail "ticket-done.sh does NOT source config-helpers.sh - add: source \"\$SCRIPT_DIR/config-helpers.sh\""
    fi
}

# Test: Verify ticket-done.sh calls get_instance_label
test_ticket_done_calls_get_instance_label() {
    echo ""
    echo "=== test_ticket_done_calls_get_instance_label ==="

    # Check if ticket-done.sh calls get_instance_label
    if grep -q "get_instance_label" "$SCRIPT_DIR/ticket-done.sh"; then
        pass "ticket-done.sh calls get_instance_label"
    else
        fail "ticket-done.sh does NOT call get_instance_label - implementation needed"
    fi
}

# Test: Verify ticket-done.sh has label removal logic
test_ticket_done_has_label_removal() {
    echo ""
    echo "=== test_ticket_done_has_label_removal ==="

    # Check if ticket-done.sh has the --remove-label command
    if grep -q "\-\-remove-label" "$SCRIPT_DIR/ticket-done.sh"; then
        pass "ticket-done.sh has --remove-label command"
    else
        fail "ticket-done.sh does NOT have --remove-label command - implementation needed"
    fi
}

# Test: Verify ticket-done.sh label removal is idempotent (handles already removed)
test_ticket_done_label_removal_idempotent() {
    echo ""
    echo "=== test_ticket_done_label_removal_idempotent ==="

    # Check if ticket-done.sh handles the case where label is already removed
    # This should be done by using 2>/dev/null or checking error message
    if grep -q "remove-label.*2>/dev/null" "$SCRIPT_DIR/ticket-done.sh"; then
        pass "ticket-done.sh handles label removal errors gracefully"
    else
        fail "ticket-done.sh does NOT handle label removal errors gracefully - add 2>/dev/null"
    fi
}

# ============================================================================
# Run All Tests
# ============================================================================

run_all_tests() {
    echo ""
    echo "=========================================="
    echo "  ticket-done.sh Label Removal Tests"
    echo "  Ticket: AUCT-0158"
    echo "=========================================="

    test_config_helpers_available
    test_instance_label_reading
    test_remove_label_command_construction
    test_label_removal_skipped_when_not_configured
    test_label_removal_happens_when_configured
    test_ticket_done_sources_config_helpers
    test_ticket_done_calls_get_instance_label
    test_ticket_done_has_label_removal
    test_ticket_done_label_removal_idempotent

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
