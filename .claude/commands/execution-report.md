# Execution Report

> **⚠ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Document what was implemented versus what was planned.**

---

## ⬇ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.phase = "report"'
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Purpose

After completing a feature implementation, create an execution report that captures:
- What was actually built
- How it differed from the plan
- What challenges were encountered
- What was learned

This creates a record for the `/system-review` process improvement phase.

**This command creates:** `docs/execution-reports/YYYY-MM-DD-{feature-name}.md`

## When to Use

- After completing `/implement` for a feature
- After `/hotfix` is deployed
- After any significant implementation work
- Before creating a PR (helps write better PR descriptions)

## The Execution Report Process

### Step 1: Gather Context

Identify:
- The plan that was followed (`docs/plans/YYYY-MM-DD-*.md`)
- The commits made (`git log --oneline` since branch creation)
- The files changed (`git diff --stat main..HEAD`)

### Step 1b: Check PM Tool for Ticket Status

Check `pm.tool` in config.yaml and use the appropriate method to get ticket counts.

**If `pm.tool: github` in config.yaml:**

```bash
# Get ticket counts from GitHub Issues
OPEN=$(gh issue list --state open --json number | jq 'length')
CLOSED=$(gh issue list --state closed --json number | jq 'length')
BLOCKED=$(gh issue list --state open --label blocked --json number | jq 'length')

echo "Tickets: $CLOSED closed, $OPEN open ($BLOCKED blocked)"

# List blocked tickets with reasons
gh issue list --state open --label blocked --json number,title,body --jq '.[] | "- #\(.number): \(.title)"'
```

**If `pm.tool: asana` in config.yaml:**

Use the AsanaPM class to query Asana for ticket counts:

```python
# Query Asana for ticket status counts
# Requires ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID env vars

from core.asana_pm import AsanaPM

pm = AsanaPM()
counts = pm.get_ticket_counts()

print(f"Tickets: {counts['closed']} closed, {counts['open']} open ({counts['blocked']} blocked)")

# List blocked tickets with titles
for task in counts['blocked_tasks']:
    print(f"- {task['gid']}: {task['name']}")
```

**Alternative: Direct Asana API call via curl (if Python is not available):**

```bash
# Get all tasks from the project
# Requires: ASANA_ACCESS_TOKEN, ASANA_PROJECT_ID

curl -s -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  "https://app.asana.com/api/1.0/projects/$ASANA_PROJECT_ID/tasks?opt_fields=gid,name,completed,tags.name" \
  | jq '{
    total: (.data | length),
    closed: ([.data[] | select(.completed == true)] | length),
    blocked: ([.data[] | select(.completed == false) | select(.tags[]?.name | ascii_downcase == "blocked")] | length),
    open: ([.data[] | select(.completed == false) | select((.tags[]?.name | ascii_downcase) != "blocked")] | length),
    blocked_tasks: [.data[] | select(.completed == false) | select(.tags[]?.name | ascii_downcase == "blocked") | {gid, name}]
  }'
```

Include this summary in the report.

### Step 2: Assess Completion

For each planned task:
- Was it completed?
- Was it modified from plan?
- Was it skipped? Why?

### Step 3: Document Challenges

What problems arose during implementation?
- Unexpected technical issues
- Missing information in plan
- Changed requirements
- Integration difficulties

### Step 4: Capture Validation Results

Run and document:
```bash
# Linting
npm run lint 2>&1 || ruff check . 2>&1

# Tests
npm test 2>&1 || pytest -v 2>&1

# Build
npm run build 2>&1
```

### Step 4b: Run Automated Scripted Checks (For Ralph Batches)

**If this execution report is for a Ralph batch execution**, run the automated scripted checks before proceeding to manual review.

The scripted checks framework validates:
1. **Merge commits** - All tickets have merge commits in git history
2. **Orphaned branches** - No unmerged feature branches remain
3. **Bypass language** - No bypass language patterns in state files
4. **State files exist** - State directories created for all tickets
5. **Validation files exist** - Validation.md files present for all tickets

**Run scripted checks via Python:**

```python
import sys
sys.path.insert(0, '/workspaces/ai-app-builder/.claude/ralph')

from pathlib import Path
from commands.scripted_checks import run_execution_report_checks

# Get ticket IDs from workflow-state.json or PRD
ticket_ids = ["AIUI-0049", "AIUI-0050", ...]  # List all tickets in batch

# Run scripted checks + agent review
result = run_execution_report_checks(
    ticket_ids=ticket_ids,
    state_dir=Path("docs/state"),
    review_model="opus",   # From config.yaml ralph.review_model
    review_timeout_minutes=5,  # From config.yaml ralph.review_timeout
    dry_run=False,
)

# Check results
if not result.scripted_checks_passed:
    print("SCRIPTED CHECKS FAILED!")
    print(result.scripted_checks_summary)
    print("\nAgent review NOT invoked - fix failures first")
else:
    print("SCRIPTED CHECKS PASSED:")
    print(result.scripted_checks_summary)
    print("\nAGENT REVIEW COMPLETED:")
    print(f"Status: {result.agent_review_status}")
    print(result.agent_review_findings)
```

**Read config values:**

```bash
# Get review_model from config.yaml (defaults to opus)
REVIEW_MODEL=$(grep -E "^\s*review_model:" config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' || echo "opus")

# Get review_timeout from config.yaml (defaults to 5)
REVIEW_TIMEOUT=$(grep -E "^\s*review_timeout:" config.yaml 2>/dev/null | awk '{print $2}' || echo "5")
```

**Include scripted check results in the execution report** under a new "Automated Validation" section.

### Step 5: Note Divergences

Where did implementation differ from plan?
- Classify as intentional or unintentional
- Explain the reasoning

## Execution Report Template

Create `docs/execution-reports/YYYY-MM-DD-{feature-slug}.md`:

````markdown
# Execution Report: {Feature Name}

**Date:** YYYY-MM-DD
**Plan:** `docs/plans/YYYY-MM-DD-{feature}.md`
**Branch:** `feature/{branch-name}`
**Status:** COMPLETE | PARTIAL | BLOCKED

---

## Summary

**What was built:**
[1-2 sentence summary of the implementation]

**Commits:** [number]
**Files Changed:** [number]
**Lines:** +[added] / -[removed]

---

## Ticket Status (from PM Tool)

| Status | Count | Details |
|--------|-------|---------|
| Closed (Done) | [N] | Completed tickets |
| Open (Remaining) | [N] | Still to be implemented |
| Blocked | [N] | Requires investigation |

### Blocked Tickets

| Ticket | Issue | Reason |
|--------|-------|--------|
| [AUCI-XXXX] | [#NN] | [Reason from comment/label] |

---

## Implementation Details

### Completed Tasks

| Task | Status | Notes |
|------|--------|-------|
| [Task from plan] | Done | [any notes] |
| [Task from plan] | Done | [any notes] |

### Modified Tasks

| Task | Original Plan | Actual Implementation | Reason |
|------|---------------|----------------------|--------|
| [Task] | [what plan said] | [what was done] | [why] |

### Skipped Tasks

| Task | Reason | Follow-up Required |
|------|--------|-------------------|
| [Task] | [why skipped] | [yes/no - details] |

---

## Files Changed

---

```
[output of git diff --stat main..HEAD]
```

---

### Key Changes

- `path/to/file.py` - [what changed and why]
- `path/to/component.tsx` - [what changed and why]

---

## Validation Results

### Linting

---
```
[output of lint command]
```
---

**Status:** PASS / FAIL

### Tests

```
[output of test command]
```

**Status:** PASS / FAIL
**Coverage:** [X]%

### Build

```
[output of build command]
```

**Status:** PASS / FAIL

### Automated Validation (Ralph Batches Only)

**Scripted Checks:**

| Check | Status | Details |
|-------|--------|---------|
| Merge Commits | PASS/FAIL | [N] tickets verified |
| Orphaned Branches | PASS/FAIL | [N] branches checked |
| Bypass Language | PASS/FAIL | [N] state files scanned |
| State Files Exist | PASS/FAIL | [N] directories verified |
| Validation Files | PASS/FAIL | [N] validation.md files found |

**Overall:** PASS / FAIL
**Duration:** [X.XX] seconds

**Agent Review:** (only runs if scripted checks pass)
- Status: APPROVED / CONCERNS / NOT_RUN
- Findings: [summary of agent review findings]

---

## Challenges Encountered

### Challenge 1: [Title]
**Problem:** [Description]
**Resolution:** [How it was solved]
**Time Impact:** [Estimate]

### Challenge 2: [Title]
**Problem:** [Description]
**Resolution:** [How it was solved]
**Time Impact:** [Estimate]

---

## Divergences from Plan

### Intentional Divergences

| What Changed | Why | Category |
|-------------|-----|----------|
| [Change] | [Reason] | Optimization / Better Pattern / Requirement Change |

### Unintentional Divergences

| What Changed | Why | Should Plan Have Covered? |
|-------------|-----|--------------------------|
| [Change] | [Reason] | Yes / No - [explanation] |

---

## What Went Well

- [Specific success 1]
- [Specific success 2]
- [Specific success 3]

## What Could Be Improved

- [Issue 1] - [Suggested improvement]
- [Issue 2] - [Suggested improvement]

---

## Recommendations

### For This Feature
- [ ] [Follow-up task]
- [ ] [Technical debt to address]

### For Future Plans
- [Insight that would improve planning]
- [Pattern that should be documented]

### For SDLC Process
- [Process improvement suggestion]

---

## Ready for Review

- [ ] All tests passing
- [ ] Linting clean
- [ ] Build succeeds
- [ ] Documentation updated
- [ ] PR ready to create
````

## After Execution Report

1. **Create PR** - Use report to write PR description
2. **Run `/system-review`** - Analyze process effectiveness
3. **Update PROGRESS.md** - Mark tasks complete

---

## ✅ FINAL ACTION (MANDATORY)

**After the report is created, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.completed = (.completed + ["report"] | unique)'
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## Arguments

$ARGUMENTS

If a feature name is provided (e.g., `/execution-report user-auth`), use it for the report title.
If no arguments, prompt for the feature name or infer from current branch.
