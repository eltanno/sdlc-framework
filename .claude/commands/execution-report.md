# Execution Report

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Document what was implemented versus what was planned.**

---

## ⚡ FIRST ACTION (MANDATORY)

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
- The files changed (`git diff --stat main...HEAD`)

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

### Step 5: Note Divergences

Where did implementation differ from plan?
- Classify as intentional or unintentional
- Explain the reasoning

## Execution Report Template

Create `docs/execution-reports/YYYY-MM-DD-{feature-slug}.md`:

```markdown
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

## Implementation Details

### Completed Tasks

| Task | Status | Notes |
|------|--------|-------|
| [Task from plan] | Done | [any notes] |
| [Task from plan] | Done | [any notes] |

### Modified Tasks

| Task | Original Plan | Actual Implementation | Reason |
|------|--------------|----------------------|--------|
| [Task] | [what plan said] | [what was done] | [why] |

### Skipped Tasks

| Task | Reason | Follow-up Required |
|------|--------|-------------------|
| [Task] | [why skipped] | [yes/no - details] |

---

## Files Changed

```
[output of git diff --stat main...HEAD]
```

### Key Changes

- `path/to/file.py` - [what changed and why]
- `path/to/component.tsx` - [what changed and why]

---

## Validation Results

### Linting
```
[output of lint command]
```
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
|--------------|-----|----------|
| [Change] | [Reason] | Optimization / Better Pattern / Requirement Change |

### Unintentional Divergences

| What Changed | Why | Should Plan Have Covered? |
|--------------|-----|--------------------------|
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
```

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
