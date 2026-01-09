# Validation Phase - Orchestrator Instructions

**You are the orchestrator. Delegate validation checks to the `engineer` agent.**

## Prerequisites Check

Before delegating, verify:
1. PR exists and has been reviewed/approved

```bash
# Check PR status
gh pr status
```

If no PR exists: "No open PR found. Please run `/pr` first."

## Delegation

```
Task({
  subagent_type: "engineer",
  model: "haiku",  // Validation is verification, haiku is sufficient
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the engineer agent:

---

**ENGINEER AGENT TASK: Pre-Merge Validation**

## Context

PR: $ARGUMENTS (PR number or "current")
Project: [current project directory]

## Objective

Perform comprehensive validation before merge. Verify all checks pass and acceptance criteria are met.

## Validation Checklist

### 1. Code Quality Checks

```bash
# Run full test suite
npm test

# Run linting
npm run lint

# Build (if applicable)
npm run build

# Check for console.logs
grep -r "console.log" src/ --include="*.ts" --include="*.js" | grep -v test

# Check for TODOs without tickets
grep -r "TODO" src/ --include="*.ts" --include="*.js" | grep -v "TODO(TASK-"
```

### 2. PR Status Checks

```bash
# CI status
gh pr checks

# Review status
gh pr view --json reviews

# Merge conflicts
gh pr view --json mergeable
```

### 3. Branch Status

```bash
# Is branch up to date with main?
git fetch origin main
git log HEAD..origin/main --oneline
```

### 4. Acceptance Criteria Verification

Find the PRD and verify each acceptance criterion:

| Criterion | Status | Verification |
|-----------|--------|--------------|
| Given X, when Y, then Z | PASS/FAIL | How verified |

### 5. Documentation Check

- [ ] README updated (if public API changed)
- [ ] PRD reflects final implementation
- [ ] Inline docs for complex logic

## Deliverable

Return:

```
VALIDATION REPORT

PR: #[number]
Branch: feature/TASK-XXX → main

## Code Quality
- Tests: PASS/FAIL ([N] tests)
- Lint: PASS/FAIL
- Build: PASS/FAIL

## PR Status
- CI Checks: PASS/FAIL
- Reviews: [N] approved
- Mergeable: Yes/No

## Acceptance Criteria
- [x] Criterion 1 - verified by test_xxx
- [x] Criterion 2 - verified manually
- [ ] Criterion 3 - FAILED: reason

## Issues Found
- Issue 1 (if any)
- Issue 2 (if any)

## Recommendation
[READY TO MERGE / NEEDS FIXES]

Next Steps:
- If ready: Merge PR, update ticket to Done
- If issues: Fix and re-validate
```

---

## After Agent Returns

### If READY TO MERGE

1. Confirm with user
2. Merge the PR:
   ```bash
   gh pr merge --squash --delete-branch
   ```
3. Update Asana ticket to "Done"
4. Celebrate!

### If NEEDS FIXES

1. Report issues to user
2. Guide back to `/implement` to fix
3. Re-run `/validate` after fixes

## PR to Validate

$ARGUMENTS
