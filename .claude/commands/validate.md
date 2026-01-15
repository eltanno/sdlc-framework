# Validation Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. Delegate validation checks to the `engineer` agent.**

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "validate"'
fi
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Prerequisites Check

Before delegating, verify:
1. PR/MR exists and has been reviewed/approved

```bash
# Read repo type from config.yaml (defaults to github)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")

# Check PR/MR status
if [ "$REPO_TYPE" = "gitlab" ]; then
  glab mr list --state=open
else
  gh pr status
fi
```

If no PR/MR exists: "No open PR/MR found. Please run `/pr` first."

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

### 2. PR/MR Status Checks

```bash
# Read repo type from config.yaml (defaults to github)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")
```

**For GitHub (repo.type: github):**
```bash
gh pr checks
gh pr view --json reviews
gh pr view --json mergeable
```

**For GitLab (repo.type: gitlab):**
```bash
glab mr view
glab ci status
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

### Read Merge Settings

```bash
# Auto-merge setting from config.yaml
AUTO_MERGE=$(grep -E "^\s*auto_merge:" config.yaml 2>/dev/null | awk '{print $2}' || echo "false")

# Merge method (merge | squash | rebase)
MERGE_METHOD=$(grep -E "^\s*merge_method:" config.yaml 2>/dev/null | awk '{print $2}' || echo "squash")

# Delete branch after merge
DELETE_BRANCH=$(grep -E "^\s*delete_branch_after_merge:" config.yaml 2>/dev/null | awk '{print $2}' || echo "true")

# Repository type
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")
```

### If READY TO MERGE

**If `auto_merge: true`:**
- Proceed directly to merge without user confirmation
- Report: "Validation passed. Auto-merging PR..."

**If `auto_merge: false`:**
- Confirm with user before merging

**Merge Commands:**

**GitHub:**
```bash
# Build merge flags based on config
MERGE_FLAGS=""
if [ "$MERGE_METHOD" = "squash" ]; then
  MERGE_FLAGS="--squash"
elif [ "$MERGE_METHOD" = "rebase" ]; then
  MERGE_FLAGS="--rebase"
else
  MERGE_FLAGS="--merge"
fi

if [ "$DELETE_BRANCH" = "true" ]; then
  MERGE_FLAGS="$MERGE_FLAGS --delete-branch"
fi

gh pr merge $MERGE_FLAGS
```

**GitLab:**
```bash
# Build merge flags based on config
MERGE_FLAGS=""
if [ "$MERGE_METHOD" = "squash" ]; then
  MERGE_FLAGS="--squash"
elif [ "$MERGE_METHOD" = "rebase" ]; then
  MERGE_FLAGS="--rebase"
fi

if [ "$DELETE_BRANCH" = "true" ]; then
  MERGE_FLAGS="$MERGE_FLAGS --remove-source-branch"
fi

glab mr merge $MERGE_FLAGS
```

**After merge:**
1. Update ticket to "Done"
2. If more tickets: proceed to next `/implement`
3. If all tickets done: proceed to `/execution-report`

### If NEEDS FIXES

1. Report issues to user
2. Guide back to `/implement` to fix
3. Re-run `/validate` after fixes

---

## ✅ FINAL ACTION (MANDATORY)

**After validation passes and PR is merged, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["validate"] | unique)'
fi
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## PR to Validate

$ARGUMENTS
