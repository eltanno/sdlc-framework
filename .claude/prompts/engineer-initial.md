# Engineer Task: Implement {TICKET_ID}

## Context

**Ticket:** {TICKET_ID}
**Attempt:** 1 of {MAX_ATTEMPTS}
**Branch:** Create `feature/{TICKET_ID}-implementation`

## Important: File Paths

**CRITICAL: All documentation and state files must be written to the REPOSITORY ROOT, not subdirectories.**

- State files go in: `{REPO_ROOT}/docs/state/{TICKET_ID}/...`
- Never write docs to `mobile/docs/` or `backend/docs/`
- If you `cd` into a subdirectory to run tests, use absolute paths or `cd` back to root before writing files
- The repository root is: `{REPO_ROOT}`

When writing state files, always use the full path from repository root:
```bash
# Good - explicit path from repo root
mkdir -p {REPO_ROOT}/docs/state/{TICKET_ID}/attempt-1

# Bad - relative path that depends on current directory
mkdir -p docs/state/{TICKET_ID}/attempt-1
```

## Required Reading

1. **PRD:** `{PRD_PATH}` - Find acceptance criteria for {TICKET_ID}
2. **Plan:** `{PLAN_PATH}` - Find technical approach for {TICKET_ID}
3. **Coding Standards:** `docs/coding-standards.md` - Follow all standards

## Your Task

Implement this ticket using Test-Driven Development:

### Step 1: Create Feature Branch

```bash
git fetch origin {DEFAULT_BRANCH}
git checkout -b feature/{TICKET_ID}-implementation origin/{DEFAULT_BRANCH}
```

Note: We branch directly from `origin/{DEFAULT_BRANCH}` without checking it out.
This allows multiple worktrees to create branches simultaneously.

### Step 2: TDD Implementation

For each piece of functionality:
1. **RED:** Write a failing test
2. **GREEN:** Write minimum code to pass
3. **REFACTOR:** Clean up while tests stay green

### Step 3: Run Validation and Fix Errors

After implementation, run ALL checks:

```bash
{TYPECHECK_COMMAND}
{LINT_COMMAND}
{TEST_COMMAND}
{BUILD_COMMAND}
```

**CRITICAL: If any check fails, FIX THE ERRORS before continuing.**

Do NOT report VALIDATION_FAILED just because you found errors. Instead:
1. Read the error messages carefully
2. Fix each error - even if it's in code you didn't write
3. Re-run validation
4. Repeat until ALL checks pass OR you've genuinely exhausted your options

Only report VALIDATION_FAILED when:
- You've tried to fix all errors but some remain truly unfixable
- The errors require changes outside this ticket's scope (e.g., infrastructure, missing dependencies)
- You've documented exactly what you tried and why it didn't work

**Pre-existing errors are NOT an excuse to skip validation.** If typecheck/lint/tests fail, fix them. The codebase must be in a passing state for your PR to be merged.

### Step 4: Write State File

Create `{REPO_ROOT}/docs/state/{TICKET_ID}/attempt-1/engineer-state.json` with:
- What you implemented
- Files modified
- Tests written
- Validation results
- Any known issues

Also create the `.md` version for readability.

Use this JSON schema:

```json
{
  "ticket_id": "{TICKET_ID}",
  "attempt": 1,
  "timestamp": "<ISO 8601 timestamp>",
  "status": "validation_passed | validation_failed",
  "branch": "feature/{TICKET_ID}-implementation",
  "last_commit": "<commit SHA>",
  "validation_result": {
    "typecheck": "pass | fail | skip",
    "lint": "pass | fail | skip",
    "test": "pass | fail | skip",
    "build": "pass | fail | skip",
    "overall": "pass | fail"
  },
  "work_completed": ["<list of completed items>"],
  "files_modified": ["<list of file paths>"],
  "tests_written": [
    {
      "file": "<test file path>",
      "tests": ["<test names>"]
    }
  ],
  "known_issues": ["<any issues encountered>"],
  "next_steps": ["<recommended next steps if resuming>"]
}
```

### Step 5: Commit Changes

**If validation PASSED:**
```bash
git add -A
git commit -m "[{TICKET_ID}] <description>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**If validation FAILED:**
```bash
git add -A
git commit -m "[{TICKET_ID}] WIP - validation failing

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 6: Report Result and EXIT

**CRITICAL: After outputting your result, you are DONE. STOP and EXIT immediately.**

**If validation passed:**
```
VALIDATION_PASSED

Ticket: {TICKET_ID}
Branch: feature/{TICKET_ID}-implementation
Commit: <sha>
```

**If validation failed:**
```
VALIDATION_FAILED

Ticket: {TICKET_ID}
Branch: feature/{TICKET_ID}-implementation
Commit: <sha>
State file: {REPO_ROOT}/docs/state/{TICKET_ID}/attempt-1/engineer-state.md
```

**After outputting VALIDATION_PASSED or VALIDATION_FAILED:**
1. **DO NOT make any more tool calls** - no Bash, no Read, no Edit, nothing
2. **DO NOT write any more text** - your response ends with the result block above
3. **Your task is complete** - the orchestrator will handle the rest

## Rules

- Follow TDD strictly - tests before implementation
- Run ALL validation checks before committing
- Always write state file before committing
- Always commit (even if failing) to preserve work
- Never create PR - orchestrator handles that
- Report VALIDATION_PASSED or VALIDATION_FAILED at the end, then STOP and EXIT
- Do NOT spawn subagents or delegate work - do everything yourself
- Do NOT continue after reporting your result
