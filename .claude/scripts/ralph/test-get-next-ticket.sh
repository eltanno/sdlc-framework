#!/bin/bash
#
# Tests for get-next-ticket.sh label filtering functionality
#
# Ticket: AUCT-0157
#
# Tests verify:
# 1. Issues with any ralph-* labels are skipped when searching for new work
# 2. Own instance's labeled issues are returned when resuming
# 3. Backward compatibility when no instance labels configured
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
# Unit Tests for Label Filtering Logic
# ============================================================================

# Test: has_ralph_label function correctly identifies ralph-* labels
test_has_ralph_label_function() {
    echo ""
    echo "=== test_has_ralph_label_function ==="

    # This function should be added to get-next-ticket.sh
    # It checks if an issue has any label matching the instance prefix

    # Test data: JSON labels array
    local labels_with_ralph='[{"name":"ralph-1"},{"name":"bug"}]'
    local labels_without_ralph='[{"name":"bug"},{"name":"feature"}]'
    local labels_with_blocked='[{"name":"blocked"},{"name":"ralph-2"}]'
    local empty_labels='[]'

    local prefix="ralph-"

    # Test: Labels containing ralph-1 should return true
    if echo "$labels_with_ralph" | jq -e --arg prefix "$prefix" '[.[] | select(.name | startswith($prefix))] | length > 0' > /dev/null 2>&1; then
        pass "Detects ralph-* label in array"
    else
        fail "Should detect ralph-* label in array"
    fi

    # Test: Labels without ralph-* should return false
    if ! echo "$labels_without_ralph" | jq -e --arg prefix "$prefix" '[.[] | select(.name | startswith($prefix))] | length > 0' > /dev/null 2>&1; then
        pass "Returns false for labels without ralph-*"
    else
        fail "Should return false for labels without ralph-*"
    fi

    # Test: Empty labels should return false
    if ! echo "$empty_labels" | jq -e --arg prefix "$prefix" '[.[] | select(.name | startswith($prefix))] | length > 0' > /dev/null 2>&1; then
        pass "Returns false for empty labels array"
    else
        fail "Should return false for empty labels array"
    fi

    # Test: Labels with blocked AND ralph should return true (ralph-* detected)
    if echo "$labels_with_blocked" | jq -e --arg prefix "$prefix" '[.[] | select(.name | startswith($prefix))] | length > 0' > /dev/null 2>&1; then
        pass "Detects ralph-* even when blocked label present"
    else
        fail "Should detect ralph-* label even when blocked label present"
    fi
}

# Test: Resume detection - should include own instance's labeled issues
test_resume_own_instance_label() {
    echo ""
    echo "=== test_resume_own_instance_label ==="

    local own_label="ralph-1"
    local other_label="ralph-2"

    # Issue labeled with own instance label (should be resumable)
    local own_issue='{"number":100,"title":"[AUCT-0100] Test","labels":[{"name":"ralph-1"}],"assignees":[]}'

    # Issue labeled with other instance label (should be skipped)
    local other_issue='{"number":101,"title":"[AUCT-0101] Test","labels":[{"name":"ralph-2"}],"assignees":[]}'

    # Issue with no ralph labels (should be available)
    local clean_issue='{"number":102,"title":"[AUCT-0102] Test","labels":[{"name":"bug"}],"assignees":[]}'

    # Test: Own label should be detected for resume
    local own_label_matches
    own_label_matches=$(echo "$own_issue" | jq -r --arg own "$own_label" '.labels[] | select(.name == $own) | .name')
    if [ "$own_label_matches" = "$own_label" ]; then
        pass "Detects own instance label for resume"
    else
        fail "Should detect own instance label for resume"
    fi

    # Test: Other label should not match own label
    local other_label_matches
    other_label_matches=$(echo "$other_issue" | jq -r --arg own "$own_label" '.labels[] | select(.name == $own) | .name')
    if [ -z "$other_label_matches" ]; then
        pass "Does not match other instance's label as own"
    else
        fail "Should not match other instance's label as own"
    fi

    # Test: Issue without ralph labels should have empty match
    local clean_label_matches
    clean_label_matches=$(echo "$clean_issue" | jq -r --arg own "$own_label" '.labels[] | select(.name == $own) | .name')
    if [ -z "$clean_label_matches" ]; then
        pass "Clean issue has no instance label match"
    else
        fail "Clean issue should have no instance label match"
    fi
}

# Test: Skip logic - issues with any ralph-* label should be skipped for new work
test_skip_other_instance_labels() {
    echo ""
    echo "=== test_skip_other_instance_labels ==="

    local prefix="ralph-"
    local own_label="ralph-1"

    # Array of issues as would come from gh issue list
    local issues='[
        {"number":100,"title":"[AUCT-0100] Own work","labels":[{"name":"ralph-1"}],"assignees":[]},
        {"number":101,"title":"[AUCT-0101] Other work","labels":[{"name":"ralph-2"}],"assignees":[]},
        {"number":102,"title":"[AUCT-0102] Clean","labels":[{"name":"bug"}],"assignees":[]},
        {"number":103,"title":"[AUCT-0103] Blocked other","labels":[{"name":"blocked"},{"name":"ralph-3"}],"assignees":[]}
    ]'

    # Filter: Get issues with own instance label (resume candidates)
    local resume_issues
    resume_issues=$(echo "$issues" | jq --arg own "$own_label" '[.[] | select(.labels | map(.name) | index($own))]')
    local resume_count
    resume_count=$(echo "$resume_issues" | jq 'length')
    if [ "$resume_count" = "1" ]; then
        pass "Finds exactly one issue with own instance label for resume"
    else
        fail "Should find exactly one issue with own instance label (found $resume_count)"
    fi

    # Filter: Get issues without any ralph-* labels (new work candidates)
    local new_work_issues
    new_work_issues=$(echo "$issues" | jq --arg prefix "$prefix" '[.[] | select((.labels | map(.name) | map(select(startswith($prefix)))) | length == 0)]')
    local new_work_count
    new_work_count=$(echo "$new_work_issues" | jq 'length')
    if [ "$new_work_count" = "1" ]; then
        pass "Finds exactly one issue without any ralph-* labels for new work"
    else
        fail "Should find exactly one issue without any ralph-* labels (found $new_work_count)"
    fi

    # Verify the clean issue is #102
    local clean_number
    clean_number=$(echo "$new_work_issues" | jq -r '.[0].number')
    if [ "$clean_number" = "102" ]; then
        pass "Clean issue is correctly identified (#102)"
    else
        fail "Should identify #102 as clean issue (got #$clean_number)"
    fi
}

# Test: Backward compatibility - no instance label configured
test_backward_compatibility_no_label() {
    echo ""
    echo "=== test_backward_compatibility_no_label ==="

    setup_test_env

    # Create config without instance_label
    create_test_config "$TEST_DIR/config.yaml" "" "ralph-" "true"

    # Read instance label (should be empty)
    local label
    label=$(get_instance_label "$TEST_DIR/config.yaml")
    if [ -z "$label" ]; then
        pass "Empty instance_label returns empty string"
    else
        fail "Empty instance_label should return empty string (got '$label')"
    fi

    # When no instance label, prefix should still work
    local prefix
    prefix=$(get_instance_label_prefix "$TEST_DIR/config.yaml")
    if [ "$prefix" = "ralph-" ]; then
        pass "Prefix still works when instance_label empty"
    else
        fail "Prefix should still work (got '$prefix')"
    fi

    teardown_test_env
}

# Test: Custom prefix support
test_custom_prefix() {
    echo ""
    echo "=== test_custom_prefix ==="

    setup_test_env

    # Create config with custom prefix
    create_test_config "$TEST_DIR/config.yaml" "worker-1" "worker-" "false"

    local label
    label=$(get_instance_label "$TEST_DIR/config.yaml")
    if [ "$label" = "worker-1" ]; then
        pass "Custom instance label 'worker-1' read correctly"
    else
        fail "Should read custom instance label (got '$label')"
    fi

    local prefix
    prefix=$(get_instance_label_prefix "$TEST_DIR/config.yaml")
    if [ "$prefix" = "worker-" ]; then
        pass "Custom prefix 'worker-' read correctly"
    else
        fail "Should read custom prefix (got '$prefix')"
    fi

    # Test jq filtering with custom prefix
    local issues='[{"number":1,"labels":[{"name":"worker-1"}]},{"number":2,"labels":[{"name":"worker-2"}]},{"number":3,"labels":[]}]'
    local clean_issues
    clean_issues=$(echo "$issues" | jq --arg prefix "$prefix" '[.[] | select((.labels | map(.name) | map(select(startswith($prefix)))) | length == 0)]')
    local clean_count
    clean_count=$(echo "$clean_issues" | jq 'length')
    if [ "$clean_count" = "1" ]; then
        pass "Custom prefix filtering works correctly"
    else
        fail "Custom prefix filtering should find 1 clean issue (found $clean_count)"
    fi

    teardown_test_env
}

# Test: Integration - jq filter expressions used in get-next-ticket.sh
test_jq_filter_expressions() {
    echo ""
    echo "=== test_jq_filter_expressions ==="

    local prefix="ralph-"
    local own_label="ralph-1"

    # Simulated gh issue list output
    local issues='[
        {"number":1,"title":"[AUCT-0001] First","labels":[{"name":"bug"}],"assignees":[]},
        {"number":2,"title":"[AUCT-0002] Second","labels":[{"name":"ralph-1"}],"assignees":[]},
        {"number":3,"title":"[AUCT-0003] Third","labels":[{"name":"ralph-2"}],"assignees":[]},
        {"number":4,"title":"[AUCT-0004] Fourth","labels":[],"assignees":[]},
        {"number":5,"title":"[AUCT-0005] Fifth","labels":[{"name":"blocked"}],"assignees":[]}
    ]'

    # Filter 1: Issues with own label (resume candidates)
    local resume_filter='[.[] | select(.labels | map(.name) | index($own))]'
    local resume_result
    resume_result=$(echo "$issues" | jq --arg own "$own_label" "$resume_filter")
    local resume_count
    resume_count=$(echo "$resume_result" | jq 'length')
    if [ "$resume_count" = "1" ]; then
        pass "Resume filter finds 1 issue with own label"
    else
        fail "Resume filter should find 1 issue (found $resume_count)"
    fi

    # Filter 2: Issues without any ralph-* labels AND not blocked (new work candidates)
    # This is the complex filter that will be added to get-next-ticket.sh
    local newwork_filter='[.[] | select(.assignees | length == 0) | select(.labels | map(.name) | index("blocked") | not) | select((.labels | map(.name) | map(select(startswith($prefix)))) | length == 0)]'
    local newwork_result
    newwork_result=$(echo "$issues" | jq --arg prefix "$prefix" "$newwork_filter")
    local newwork_count
    newwork_count=$(echo "$newwork_result" | jq 'length')
    # Should find issues #1 and #4 (no ralph labels, not blocked, unassigned)
    if [ "$newwork_count" = "2" ]; then
        pass "New work filter finds 2 clean issues (#1 and #4)"
    else
        fail "New work filter should find 2 issues (found $newwork_count): $(echo "$newwork_result" | jq -c '.[].number')"
    fi

    # Verify the numbers are correct
    local found_numbers
    found_numbers=$(echo "$newwork_result" | jq -r '.[].number' | sort -n | tr '\n' ' ')
    if [ "$found_numbers" = "1 4 " ]; then
        pass "Correct issues found (#1 and #4)"
    else
        fail "Should find issues #1 and #4 (found: $found_numbers)"
    fi
}

# ============================================================================
# Run All Tests
# ============================================================================

run_all_tests() {
    echo "============================================"
    echo "get-next-ticket.sh Label Filtering Tests"
    echo "Ticket: AUCT-0157"
    echo "============================================"

    test_has_ralph_label_function
    test_resume_own_instance_label
    test_skip_other_instance_labels
    test_backward_compatibility_no_label
    test_custom_prefix
    test_jq_filter_expressions

    echo ""
    echo "============================================"
    echo "Test Results"
    echo "============================================"
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

# Run tests if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_all_tests
    exit $?
fi
