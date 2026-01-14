# Validation Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. Delegate validation checks to the `engineer` agent.**

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

### If READY TO MERGE

1. Confirm with user
2. Merge the PR/MR:

   **GitHub:**
   ```bash
   gh pr merge --squash --delete-branch
   ```

   **GitLab:**
   ```bash
   glab mr merge --squash --remove-source-branch
   ```
3. Update Asana ticket to "Done"
4. Celebrate!

### If NEEDS FIXES

1. Report issues to user
2. Guide back to `/implement` to fix
3. Re-run `/validate` after fixes

## Workflow State Update

**Note:** If running as part of `/ralph-prd`, ralph manages the workflow state. Only update if NOT in ralph mode.

At the **start** of this phase (if not in ralph mode):

```bash
# Only set phase if not already in ralph mode
current_phase=$(jq -r '.phase' workflow-state.json)
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "validate"'
fi
```

At the **end** of this phase (after validation passes and PR is merged), mark complete (if not in ralph mode):

```bash
current_phase=$(jq -r '.phase' workflow-state.json)
if [ "$current_phase" != "ralph" ]; then
    # Mark validate as complete
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["validate"] | unique)'

    # Reset for next feature (optional - keep completed as history or reset)
    # To reset: .claude/scripts/update-workflow-state.sh '.phase = "idle" | .completed = []'
fi
```

## PR to Validate

$ARGUMENTS
