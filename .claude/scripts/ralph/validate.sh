#!/bin/bash
# Ralph Validate - Run all validation checks
# Usage: validate.sh [--fix-lint] [--no-cache]
#
# Supports both single-codebase and monorepo projects via config.yaml
#
# Single-codebase: Runs dev.* commands from project root
# Monorepo: Iterates dev.codebases.*, runs each codebase's commands
#
# Returns exit code 0 if all pass, 1 if any fail

set -e

FIX_LINT=false
NO_CACHE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --fix-lint) FIX_LINT=true ;;
        --no-cache) NO_CACHE=true ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Ralph Validation ==="

# Track overall results
OVERALL_PASS=true
declare -A CODEBASE_RESULTS

# Helper: Parse yaml value (simple single-line values only)
parse_yaml_value() {
    local file=$1
    local key=$2
    grep "^[[:space:]]*${key}:" "$file" 2>/dev/null | head -1 | sed 's/.*:[[:space:]]*//' | sed 's/[[:space:]]*$//' | sed 's/^"//' | sed 's/"$//'
}

# Helper: Check if codebases section exists in config.yaml
has_codebases() {
    grep -q "^[[:space:]]*codebases:" config.yaml 2>/dev/null
}

# Helper: Get list of codebase names
get_codebases() {
    # Extract codebase names (lines with exactly 4 spaces followed by name:)
    awk '/^  codebases:/{found=1; next} found && /^    [a-zA-Z]/{print $1} found && /^  [a-zA-Z]/ && !/codebases:/{exit}' config.yaml | sed 's/://'
}

# Helper: Get codebase config value
get_codebase_value() {
    local codebase=$1
    local key=$2
    # Find the codebase section and extract the value
    awk -v cb="$codebase" -v key="$key" '
        $0 ~ "^    "cb":" {found=1; next}
        found && /^    [a-zA-Z]/ && $0 !~ "^      " {exit}
        found && $0 ~ "^      "key":" {
            gsub(/^[[:space:]]*[a-zA-Z_]+:[[:space:]]*/, "")
            gsub(/^"/, ""); gsub(/"$/, "")
            print
            exit
        }
    ' config.yaml
}

# Helper: Run command and capture result
run_check() {
    local name=$1
    local cmd=$2
    local output_file="/tmp/ralph-${name}-output.txt"

    if [ -z "$cmd" ] || [ "$cmd" = '""' ]; then
        echo -e "${YELLOW}${name}: SKIPPED (no command)${NC}"
        return 0
    fi

    # Handle echo commands (skip checks)
    if [[ "$cmd" == echo* ]]; then
        echo -e "${YELLOW}${name}: SKIPPED${NC}"
        return 0
    fi

    echo "Running: $cmd"
    if eval "$cmd" 2>&1 | tee "$output_file"; then
        echo -e "${GREEN}${name}: PASS${NC}"
        return 0
    else
        echo -e "${RED}${name}: FAIL${NC}"
        return 1
    fi
}

# Validate a single codebase
validate_codebase() {
    local name=$1
    local path=$2
    local typecheck_cmd=$3
    local lint_cmd=$4
    local test_cmd=$5
    local build_cmd=$6

    echo ""
    echo -e "${BLUE}=== Codebase: ${name} (${path}) ===${NC}"

    # cd into codebase directory
    if [ ! -d "$path" ]; then
        echo -e "${RED}ERROR: Directory '$path' not found${NC}"
        return 1
    fi

    cd "$PROJECT_ROOT/$path"

    local codebase_pass=true

    # Run typecheck
    echo ""
    echo "--- Typecheck ---"
    if ! run_check "Typecheck" "$typecheck_cmd"; then
        codebase_pass=false
    fi

    # Run lint
    echo ""
    echo "--- Lint ---"
    if [ "$FIX_LINT" = true ] && [[ "$lint_cmd" == *"eslint"* ]]; then
        lint_cmd="$lint_cmd --fix"
    fi
    if ! run_check "Lint" "$lint_cmd"; then
        codebase_pass=false
    fi

    # Run tests
    echo ""
    echo "--- Tests ---"
    if ! run_check "Tests" "$test_cmd"; then
        codebase_pass=false
    fi

    # Run build
    echo ""
    echo "--- Build ---"
    if ! run_check "Build" "$build_cmd"; then
        codebase_pass=false
    fi

    cd "$PROJECT_ROOT"

    if [ "$codebase_pass" = true ]; then
        CODEBASE_RESULTS[$name]="pass"
        return 0
    else
        CODEBASE_RESULTS[$name]="fail"
        return 1
    fi
}

# Main validation logic
if [ ! -f "config.yaml" ]; then
    echo -e "${YELLOW}Warning: No config.yaml found, using defaults${NC}"
    # Fall back to npm-based validation
    if [ -f "package.json" ]; then
        validate_codebase "root" "." "npm run typecheck" "npm run lint" "npm test" "npm run build"
    else
        echo -e "${YELLOW}No package.json found either, skipping validation${NC}"
    fi
elif has_codebases; then
    # Monorepo mode
    echo -e "${BLUE}Monorepo detected - validating all codebases${NC}"

    for codebase in $(get_codebases); do
        path=$(get_codebase_value "$codebase" "path")
        typecheck=$(get_codebase_value "$codebase" "typecheck_command")
        lint=$(get_codebase_value "$codebase" "lint_command")
        test=$(get_codebase_value "$codebase" "test_command")
        build=$(get_codebase_value "$codebase" "build_command")

        if ! validate_codebase "$codebase" "$path" "$typecheck" "$lint" "$test" "$build"; then
            OVERALL_PASS=false
        fi
    done
else
    # Single codebase mode
    echo -e "${BLUE}Single codebase mode${NC}"

    typecheck=$(parse_yaml_value "config.yaml" "typecheck_command")
    lint=$(parse_yaml_value "config.yaml" "lint_command")
    test=$(parse_yaml_value "config.yaml" "test_command")
    build=$(parse_yaml_value "config.yaml" "build_command")

    if ! validate_codebase "root" "." "$typecheck" "$lint" "$test" "$build"; then
        OVERALL_PASS=false
    fi
fi

# Output summary
echo ""
echo "=== Validation Summary ==="
for codebase in "${!CODEBASE_RESULTS[@]}"; do
    result=${CODEBASE_RESULTS[$codebase]}
    if [ "$result" = "pass" ]; then
        echo -e "${codebase}: ${GREEN}PASS${NC}"
    else
        echo -e "${codebase}: ${RED}FAIL${NC}"
    fi
done

if [ "$OVERALL_PASS" = true ]; then
    echo -e "Overall: ${GREEN}PASS${NC}"
else
    echo -e "Overall: ${RED}FAIL${NC}"
fi

# Output JSON for programmatic use
echo ""
echo "---JSON_OUTPUT---"
echo "{"
first=true
for codebase in "${!CODEBASE_RESULTS[@]}"; do
    if [ "$first" = true ]; then
        first=false
    else
        echo ","
    fi
    echo -n "  \"${codebase}\": \"${CODEBASE_RESULTS[$codebase]}\""
done
echo ","
echo "  \"overall\": \"$([ "$OVERALL_PASS" = true ] && echo "pass" || echo "fail")\""
echo "}"

# Exit with appropriate code
if [ "$OVERALL_PASS" = true ]; then
    exit 0
else
    exit 1
fi
