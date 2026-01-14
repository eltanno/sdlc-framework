#!/bin/bash
# Ralph Validate - Run all validation checks
# Usage: validate.sh [--fix-lint]
#
# What this does:
# 1. Run tests (npm test)
# 2. Run linting (npm run lint)
# 3. Run build (npm run build)
# 4. Output structured results
#
# Returns exit code 0 if all pass, 1 if any fail

set -e

FIX_LINT=false
if [ "$1" = "--fix-lint" ]; then
    FIX_LINT=true
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Ralph Validation ==="

# Track results
TESTS_PASS=false
LINT_PASS=false
BUILD_PASS=false
TEST_OUTPUT=""
LINT_OUTPUT=""
BUILD_OUTPUT=""

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo -e "${YELLOW}Warning: No package.json found${NC}"
    echo "---JSON_OUTPUT---"
    echo '{"tests":"skipped","lint":"skipped","build":"skipped","overall":"skipped"}'
    exit 0
fi

# Run tests
echo ""
echo "--- Running Tests ---"
if npm test 2>&1 | tee /tmp/ralph-test-output.txt; then
    TESTS_PASS=true
    echo -e "${GREEN}Tests: PASS${NC}"
else
    echo -e "${RED}Tests: FAIL${NC}"
fi
TEST_OUTPUT=$(cat /tmp/ralph-test-output.txt | tail -20)

# Run lint (if script exists)
echo ""
echo "--- Running Lint ---"
if grep -q '"lint"' package.json; then
    if [ "$FIX_LINT" = true ]; then
        if npm run lint -- --fix 2>&1 | tee /tmp/ralph-lint-output.txt; then
            LINT_PASS=true
            echo -e "${GREEN}Lint: PASS (with fixes)${NC}"
        else
            echo -e "${RED}Lint: FAIL${NC}"
        fi
    else
        if npm run lint 2>&1 | tee /tmp/ralph-lint-output.txt; then
            LINT_PASS=true
            echo -e "${GREEN}Lint: PASS${NC}"
        else
            echo -e "${RED}Lint: FAIL${NC}"
        fi
    fi
    LINT_OUTPUT=$(cat /tmp/ralph-lint-output.txt | tail -20)
else
    LINT_PASS=true
    echo -e "${YELLOW}Lint: SKIPPED (no lint script)${NC}"
    LINT_OUTPUT="No lint script in package.json"
fi

# Run build (if script exists)
echo ""
echo "--- Running Build ---"
if grep -q '"build"' package.json; then
    if npm run build 2>&1 | tee /tmp/ralph-build-output.txt; then
        BUILD_PASS=true
        echo -e "${GREEN}Build: PASS${NC}"
    else
        echo -e "${RED}Build: FAIL${NC}"
    fi
    BUILD_OUTPUT=$(cat /tmp/ralph-build-output.txt | tail -20)
else
    BUILD_PASS=true
    echo -e "${YELLOW}Build: SKIPPED (no build script)${NC}"
    BUILD_OUTPUT="No build script in package.json"
fi

# Determine overall result
OVERALL="fail"
if [ "$TESTS_PASS" = true ] && [ "$LINT_PASS" = true ] && [ "$BUILD_PASS" = true ]; then
    OVERALL="pass"
fi

# Output summary
echo ""
echo "=== Validation Summary ==="
echo -e "Tests: $([ "$TESTS_PASS" = true ] && echo "${GREEN}PASS${NC}" || echo "${RED}FAIL${NC}")"
echo -e "Lint:  $([ "$LINT_PASS" = true ] && echo "${GREEN}PASS${NC}" || echo "${RED}FAIL${NC}")"
echo -e "Build: $([ "$BUILD_PASS" = true ] && echo "${GREEN}PASS${NC}" || echo "${RED}FAIL${NC}")"
echo -e "Overall: $([ "$OVERALL" = "pass" ] && echo "${GREEN}PASS${NC}" || echo "${RED}FAIL${NC}")"

# Output JSON for programmatic use
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "tests": "$([ "$TESTS_PASS" = true ] && echo "pass" || echo "fail")",
  "lint": "$([ "$LINT_PASS" = true ] && echo "pass" || echo "fail")",
  "build": "$([ "$BUILD_PASS" = true ] && echo "pass" || echo "fail")",
  "overall": "$OVERALL"
}
EOF

# Exit with appropriate code
if [ "$OVERALL" = "pass" ]; then
    exit 0
else
    exit 1
fi
