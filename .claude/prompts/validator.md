# Validator Task: Analyze Validation Failure

## Context

**Ticket:** {TICKET_ID}
**Attempt:** {ATTEMPT}
**Branch:** `{BRANCH}` (already checked out)

## Your Task

The engineer reported validation failure. Run the validation checks yourself, analyze the results, and produce a structured report for the next attempt.

### Step 0: Ensure Correct Branch

```bash
git checkout {BRANCH}
```

### Step 1: Run All Validation Checks

Run each check and capture output:

```bash
# TypeScript
{TYPECHECK_COMMAND} 2>&1 | tee /tmp/validation-typecheck.txt

# Lint
{LINT_COMMAND} 2>&1 | tee /tmp/validation-lint.txt

# Tests
{TEST_COMMAND} 2>&1 | tee /tmp/validation-test.txt

# Build
{BUILD_COMMAND} 2>&1 | tee /tmp/validation-build.txt
```

### Step 2: Parse Errors

For each check that failed, extract:
- File path
- Line number
- Error message
- Error code/rule (if applicable)

### Step 3: Identify Root Causes

Look for patterns:
- Are multiple errors caused by the same underlying issue?
- Is there a dependency chain (e.g., TS errors blocking build)?
- Are test failures related to a specific component or mock?

### Step 4: Suggest Fixes

Provide actionable suggestions:
- What specific code changes would fix each issue?
- What order should issues be addressed?

### Step 5: Write Report

Create `docs/state/{TICKET_ID}/attempt-{ATTEMPT}/validation.json` with the structured analysis.

Use this JSON schema:

```json
{
  "ticket_id": "{TICKET_ID}",
  "attempt": {ATTEMPT},
  "timestamp": "<ISO 8601 timestamp>",
  "overall_result": "fail",
  "checks": {
    "typecheck": {
      "status": "pass | fail | skip",
      "error_count": 0,
      "errors": [
        {
          "file": "<file path>",
          "line": 0,
          "message": "<error message>",
          "code": "<error code>"
        }
      ]
    },
    "lint": {
      "status": "pass | fail | skip",
      "error_count": 0,
      "warning_count": 0,
      "errors": [
        {
          "file": "<file path>",
          "line": 0,
          "rule": "<rule name>",
          "message": "<error message>",
          "severity": "error | warning"
        }
      ]
    },
    "test": {
      "status": "pass | fail | skip",
      "total": 0,
      "passed": 0,
      "failed": 0,
      "skipped": 0,
      "failures": [
        {
          "file": "<test file path>",
          "test_name": "<test name>",
          "error": "<error message>",
          "expected": "<expected value>",
          "received": "<received value>"
        }
      ]
    },
    "build": {
      "status": "pass | fail | skip",
      "error_count": 0,
      "errors": [
        {
          "file": "<file path>",
          "message": "<error message>"
        }
      ]
    }
  },
  "root_cause_analysis": "<your analysis of the root cause(s)>",
  "suggested_fixes": [
    "<specific fix suggestion 1>",
    "<specific fix suggestion 2>"
  ],
  "priority_order": [
    "<first thing to fix>",
    "<second thing to fix>"
  ]
}
```

Also create `docs/state/{TICKET_ID}/attempt-{ATTEMPT}/validation.md` for readability.

### Output Format

When complete, output:

```
VALIDATION_REPORT_COMPLETE

Report: docs/state/{TICKET_ID}/attempt-{ATTEMPT}/validation.md
```

## Important

- Be specific about file paths and line numbers
- Group related errors together
- Prioritize fixes that unblock other checks (e.g., fix TS errors before build)
- Keep the suggested fixes actionable and concise
- Focus on root causes, not symptoms
