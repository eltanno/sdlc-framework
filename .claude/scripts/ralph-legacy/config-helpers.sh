#!/bin/bash
#
# Config Helper Functions for Ralph Label-Based Concurrency
#
# Functions for reading label configuration from config.yaml
#
# Usage: source this file from other ralph scripts
#
# Ticket: AUCT-0155
#

# Find project root (used when sourced from different locations)
get_project_root() {
    local dir="${BASH_SOURCE[0]}"
    # Handle both direct invocation and sourcing
    if [ -z "$dir" ]; then
        dir="$0"
    fi
    cd "$(dirname "$dir")/../../.." && pwd
}

# ============================================================================
# Label Config Functions
# ============================================================================

# Get the instance label for this Ralph instance
# Usage: get_instance_label [config_file]
# Returns: instance label (e.g., "ralph-1"), or default "{prefix}1" if not set
# Exits with error if label doesn't match required pattern
get_instance_label() {
    local config_file="${1:-config.yaml}"

    # Read from environment variable, not config.yaml
    local label="${RALPH_LABEL:-}"
    local prefix
    prefix=$(get_instance_label_prefix "$config_file")

    # Default to {prefix}1 if not set
    if [[ -z "$label" ]]; then
        label="${prefix}1"
    fi

    # Validate format: must match {prefix}{number}
    if ! [[ "$label" =~ ^${prefix}[0-9]+$ ]]; then
        echo "Error: RALPH_LABEL must match pattern '${prefix}<number>' (e.g., ${prefix}1, ${prefix}2)" >&2
        return 1
    fi

    echo "$label"
}

# Get the instance label prefix (used to detect all instance labels)
# Usage: get_instance_label_prefix [config_file]
# Returns: prefix (e.g., "ralph-"), or "ralph-" as default
get_instance_label_prefix() {
    local config_file="${1:-config.yaml}"
    local default_prefix="ralph-"

    if [ ! -f "$config_file" ]; then
        echo "$default_prefix"
        return 0
    fi

    # Read instance_label_prefix from ralph section in config.yaml
    local prefix
    prefix=$(grep -E '^\s*instance_label_prefix:' "$config_file" 2>/dev/null | \
        sed 's/.*instance_label_prefix:\s*"\?\([^"#]*\)"\?.*/\1/' | \
        tr -d ' ' | \
        head -1)

    # Return default if not set or empty
    if [ -z "$prefix" ]; then
        echo "$default_prefix"
    else
        echo "$prefix"
    fi
}

# Check if use_assignee is enabled (for GitHub issue assignment)
# Usage: get_use_assignee [config_file]
# Returns: "true" or "false" (default: true for backward compatibility)
get_use_assignee() {
    local config_file="${1:-config.yaml}"
    local default_value="true"

    if [ ! -f "$config_file" ]; then
        echo "$default_value"
        return 0
    fi

    # Read use_assignee from ralph section in config.yaml
    local value
    value=$(grep -E '^\s*use_assignee:' "$config_file" 2>/dev/null | \
        sed 's/.*use_assignee:\s*"\?\([^"#]*\)"\?.*/\1/' | \
        tr -d ' ' | \
        head -1 | \
        tr '[:upper:]' '[:lower:]')

    # Normalize value
    case "$value" in
        true|yes|1)
            echo "true"
            ;;
        false|no|0)
            echo "false"
            ;;
        *)
            echo "$default_value"
            ;;
    esac
}

# Check if a label matches the instance label prefix pattern
# Usage: matches_instance_prefix <label> [prefix]
# Returns: 0 (true) if label matches prefix, 1 (false) otherwise
matches_instance_prefix() {
    local label="$1"
    local prefix="${2:-}"

    if [ -z "$label" ]; then
        return 1
    fi

    # If no prefix provided, read from config
    if [ -z "$prefix" ]; then
        prefix=$(get_instance_label_prefix)
    fi

    # Check if label starts with prefix
    case "$label" in
        "$prefix"*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ============================================================================
# Self-Test Functions (for validation)
# ============================================================================

# Run self-tests when script is executed directly (not sourced)
run_self_tests() {
    local test_failed=0
    local test_passed=0
    local test_dir
    test_dir=$(mktemp -d)

    echo "=== Running config-helpers.sh self-tests ==="
    echo ""

    # Test 1: get_instance_label with RALPH_LABEL environment variable
    cat > "$test_dir/config1.yaml" << 'EOF'
ralph:
  instance_label_prefix: "ralph-"
  use_assignee: false
EOF
    local result
    RALPH_LABEL="ralph-2" result=$(get_instance_label "$test_dir/config1.yaml")
    if [ "$result" = "ralph-2" ]; then
        echo "PASS: get_instance_label returns RALPH_LABEL env var value"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label - expected 'ralph-2', got '$result'"
        ((test_failed++))
    fi

    # Test 2: get_instance_label defaults to {prefix}1 when env not set
    cat > "$test_dir/config2.yaml" << 'EOF'
ralph:
  instance_label_prefix: "ralph-"
EOF
    unset RALPH_LABEL
    result=$(get_instance_label "$test_dir/config2.yaml")
    if [ "$result" = "ralph-1" ]; then
        echo "PASS: get_instance_label defaults to ralph-1 when RALPH_LABEL not set"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label default - expected 'ralph-1', got '$result'"
        ((test_failed++))
    fi

    # Test 3: get_instance_label validates format and returns error for invalid
    RALPH_LABEL="my-custom-label" result=$(get_instance_label "$test_dir/config2.yaml" 2>/dev/null) || true
    if [ -z "$result" ]; then
        echo "PASS: get_instance_label returns empty for invalid label format"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label invalid - expected empty (error), got '$result'"
        ((test_failed++))
    fi
    unset RALPH_LABEL

    # Test 4: get_instance_label_prefix with configured value
    result=$(get_instance_label_prefix "$test_dir/config1.yaml")
    if [ "$result" = "ralph-" ]; then
        echo "PASS: get_instance_label_prefix returns configured value"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label_prefix - expected 'ralph-', got '$result'"
        ((test_failed++))
    fi

    # Test 5: get_instance_label_prefix returns default for missing setting
    cat > "$test_dir/config3.yaml" << 'EOF'
ralph:
  use_assignee: true
EOF
    result=$(get_instance_label_prefix "$test_dir/config3.yaml")
    if [ "$result" = "ralph-" ]; then
        echo "PASS: get_instance_label_prefix returns default when not set"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label_prefix default - expected 'ralph-', got '$result'"
        ((test_failed++))
    fi

    # Test 6: get_instance_label_prefix with custom prefix
    cat > "$test_dir/config4.yaml" << 'EOF'
ralph:
  instance_label_prefix: "worker-"
EOF
    result=$(get_instance_label_prefix "$test_dir/config4.yaml")
    if [ "$result" = "worker-" ]; then
        echo "PASS: get_instance_label_prefix returns custom prefix"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label_prefix custom - expected 'worker-', got '$result'"
        ((test_failed++))
    fi

    # Test 6b: get_instance_label works with custom prefix
    RALPH_LABEL="worker-3" result=$(get_instance_label "$test_dir/config4.yaml")
    if [ "$result" = "worker-3" ]; then
        echo "PASS: get_instance_label works with custom prefix"
        ((test_passed++))
    else
        echo "FAIL: get_instance_label custom prefix - expected 'worker-3', got '$result'"
        ((test_failed++))
    fi
    unset RALPH_LABEL

    # Test 7: get_use_assignee returns false when configured
    result=$(get_use_assignee "$test_dir/config1.yaml")
    if [ "$result" = "false" ]; then
        echo "PASS: get_use_assignee returns false when configured"
        ((test_passed++))
    else
        echo "FAIL: get_use_assignee false - expected 'false', got '$result'"
        ((test_failed++))
    fi

    # Test 8: get_use_assignee returns true by default
    result=$(get_use_assignee "$test_dir/config3.yaml")
    if [ "$result" = "true" ]; then
        echo "PASS: get_use_assignee returns true by default"
        ((test_passed++))
    else
        echo "FAIL: get_use_assignee default - expected 'true', got '$result'"
        ((test_failed++))
    fi

    # Test 9: get_use_assignee with missing file
    result=$(get_use_assignee "$test_dir/nonexistent.yaml")
    if [ "$result" = "true" ]; then
        echo "PASS: get_use_assignee returns true for missing file"
        ((test_passed++))
    else
        echo "FAIL: get_use_assignee missing - expected 'true', got '$result'"
        ((test_failed++))
    fi

    # Test 10: matches_instance_prefix with matching label
    if matches_instance_prefix "ralph-1" "ralph-"; then
        echo "PASS: matches_instance_prefix returns true for matching label"
        ((test_passed++))
    else
        echo "FAIL: matches_instance_prefix matching - expected true"
        ((test_failed++))
    fi

    # Test 11: matches_instance_prefix with non-matching label
    if ! matches_instance_prefix "worker-1" "ralph-"; then
        echo "PASS: matches_instance_prefix returns false for non-matching label"
        ((test_passed++))
    else
        echo "FAIL: matches_instance_prefix non-matching - expected false"
        ((test_failed++))
    fi

    # Test 12: matches_instance_prefix with empty label
    if ! matches_instance_prefix "" "ralph-"; then
        echo "PASS: matches_instance_prefix returns false for empty label"
        ((test_passed++))
    else
        echo "FAIL: matches_instance_prefix empty - expected false"
        ((test_failed++))
    fi

    # Test 13: matches_instance_prefix with custom prefix from config
    cat > "$test_dir/config5.yaml" << 'EOF'
ralph:
  instance_label_prefix: "ci-"
EOF
    # Source config for this test
    local old_cwd
    old_cwd=$(pwd)
    cd "$test_dir"
    cp config5.yaml config.yaml
    if matches_instance_prefix "ci-agent-1"; then
        echo "PASS: matches_instance_prefix works with config prefix"
        ((test_passed++))
    else
        echo "FAIL: matches_instance_prefix config - expected true for 'ci-agent-1'"
        ((test_failed++))
    fi
    cd "$old_cwd"

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

# Run tests if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_self_tests
    exit $?
fi
