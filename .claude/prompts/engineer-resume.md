# Engineer Task: Resume {TICKET_ID}

## Context

**Ticket:** {TICKET_ID}
**Attempt:** {ATTEMPT} of {MAX_ATTEMPTS}
**Branch:** `{EXISTING_BRANCH}` (already exists)

## Important: File Paths

**CRITICAL: All documentation and state files must be written to the REPOSITORY ROOT, not subdirectories.**

- State files go in: `{REPO_ROOT}/docs/state/{TICKET_ID}/...`
- Never write docs to `mobile/docs/` or `backend/docs/`
- If you `cd` into a subdirectory to run tests, use absolute paths or `cd` back to root before writing files
- The repository root is: `{REPO_ROOT}`

When writing state files, always use the full path from repository root:
```bash
# Good - explicit path from repo root
mkdir -p {REPO_ROOT}/docs/state/{TICKET_ID}/attempt-{ATTEMPT}

# Bad - relative path that depends on current directory
mkdir -p docs/state/{TICKET_ID}/attempt-{ATTEMPT}
```

## Previous Attempt

### Engineer State (Attempt {PREV_ATTEMPT})

```
{PREVIOUS_ENGINEER_STATE}
```

### Validation Report (Attempt {PREV_ATTEMPT})

```
{PREVIOUS_VALIDATION_REPORT}
```

## Your Task

Resume work on this ticket, focusing on the issues identified in the validation report.

### Step 1: Checkout Branch

```bash
git checkout {EXISTING_BRANCH}
git pull origin {EXISTING_BRANCH} 2>/dev/null || true
```

### Step 2: Review Previous State

The validation report above shows what failed. Focus on:
{PRIORITY_ORDER}

### Step 3: Fix Issues

Address the failures identified in the validation report.
Continue using TDD - write/fix tests as needed.

### Step 4: Run Full Validation

After fixes, run ALL checks:

```bash
{TYPECHECK_COMMAND}
{LINT_COMMAND}
{TEST_COMMAND}
{BUILD_COMMAND}
```

### Step 5: Write State File

Create `{REPO_ROOT}/docs/state/{TICKET_ID}/attempt-{ATTEMPT}/engineer-state.json` with:
- What you fixed
- Current validation results
- Any remaining issues

Also create the `.md` version.

Use this JSON schema:

```json
{
  "ticket_id": "{TICKET_ID}",
  "attempt": {ATTEMPT},
  "timestamp": "<ISO 8601 timestamp>",
  "status": "validation_passed | validation_failed",
  "branch": "{EXISTING_BRANCH}",
  "last_commit": "<commit SHA>",
  "validation_result": {
    "typecheck": "pass | fail | skip",
    "lint": "pass | fail | skip",
    "test": "pass | fail | skip",
    "build": "pass | fail | skip",
    "overall": "pass | fail"
  },
  "work_completed": ["<list of work done this attempt>"],
  "files_modified": ["<list of file paths>"],
  "tests_written": [
    {
      "file": "<test file path>",
      "tests": ["<test names>"]
    }
  ],
  "known_issues": ["<any remaining issues>"],
  "next_steps": ["<recommended next steps if resuming>"]
}
```

### Step 6: Commit Changes

**If validation PASSED:**
```bash
git add -A
git commit -m "[{TICKET_ID}] Fix validation issues

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**If validation FAILED:**
```bash
git add -A
git commit -m "[{TICKET_ID}] WIP - attempt {ATTEMPT}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 7: Report Result and EXIT

**CRITICAL: After outputting your result, you are DONE. STOP and EXIT immediately.**

**If validation passed:**
```
VALIDATION_PASSED

Ticket: {TICKET_ID}
Branch: {EXISTING_BRANCH}
Commit: <sha>
```

**If validation failed:**
```
VALIDATION_FAILED

Ticket: {TICKET_ID}
Branch: {EXISTING_BRANCH}
Commit: <sha>
State file: {REPO_ROOT}/docs/state/{TICKET_ID}/attempt-{ATTEMPT}/engineer-state.md
```

**After outputting VALIDATION_PASSED or VALIDATION_FAILED:**
1. **DO NOT make any more tool calls** - no Bash, no Read, no Edit, nothing
2. **DO NOT write any more text** - your response ends with the result block above
3. **Your task is complete** - the orchestrator will handle the rest

## Focus Areas

Based on the validation report, prioritize:
{SUGGESTED_FIXES}

## Rules

- Focus on fixing the identified issues first
- Continue using TDD - update tests if needed
- Run ALL validation checks before committing
- Always write state file before committing
- Always commit (even if failing) to preserve work
- Never create PR - orchestrator handles that
- Report VALIDATION_PASSED or VALIDATION_FAILED at the end, then STOP and EXIT
- Do NOT spawn subagents or delegate work - do everything yourself
- Do NOT continue after reporting your result
