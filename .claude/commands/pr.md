# Pull Request / Merge Request Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. This is coordination - delegate to haiku or do directly.**

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "pr"'
fi
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Prerequisites Check

Before proceeding, verify:
1. Feature branch exists with commits
2. Branch is pushed to remote (unless local-only repo)

```bash
# Check current branch
git branch --show-current

# Check for remote
git remote -v
```

---

## Quick Sanity Check

The engineer should have already verified all checks pass. Run the commands from `config.yaml` (`dev.typecheck_command`, `dev.lint_command`, `dev.test_command`, `dev.build_command`) as a sanity check.

**If any check fails:**
- STOP - Do not create PR
- Something went wrong during implementation
- Report the failure to the user
- They need to fix it before PR can be created

Note: These checks SHOULD pass since the engineer is required to verify them before marking implementation complete. A failure here indicates the engineer didn't follow the process.

---

## Local Repository (No Remote)

**If `git remote -v` returns empty, this is a local-only repository.**

For local repos, PR phase = merge to main/master:

```bash
# Get current branch and default branch
CURRENT_BRANCH=$(git branch --show-current)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "master")

# If on feature branch, merge to default branch
if [[ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" && "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
    git checkout $DEFAULT_BRANCH
    git merge $CURRENT_BRANCH
    echo "Merged $CURRENT_BRANCH → $DEFAULT_BRANCH"
fi
```

**Return for local repos:**

```
LOCAL MERGE COMPLETE

Branch: [feature-branch] → [main/master]
Commits: [N] commits merged

Next: Run /validate
```

Then skip to "Workflow State Update" section and mark PR complete.

---

## Remote Repository

Read `config.yaml` from project root for repo type:
```yaml
repo:
  type: github    # github | gitlab
```

### Authentication Check

Before creating PR/MR, verify the user is authenticated with the correct provider:

```bash
# Read repo type from config.yaml
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")

# Check authentication
if [ "$REPO_TYPE" = "gitlab" ]; then
  glab auth status || echo "Not authenticated. Run: glab auth login"
else
  gh auth status || echo "Not authenticated. Run: gh auth login"
fi
```

If not authenticated, guide user:
- **GitHub:** `gh auth login`
- **GitLab:** `glab auth login`

### Push Check

If not pushed: Push first with `git push -u origin $(git branch --show-current)`

## Task: Create PR/MR

This is simple enough for haiku or direct execution:

```
Task({
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

---

**TASK: Create Pull Request / Merge Request**

## Context

Ticket: $ARGUMENTS
Project: [current project directory]

## Objective

Create a PR (GitHub) or MR (GitLab) with proper documentation linking to the ticket and PRD.

## Steps

### 1. Read Configuration

Read settings from `config.yaml`:

```bash
# Repository type (github | gitlab)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")

# Target branch for PRs (main, develop, etc.)
TARGET_BRANCH=$(grep -E "^\s*target_branch:" config.yaml 2>/dev/null | awk '{print $2}' || echo "main")

# Auto-merge setting
AUTO_MERGE=$(grep -E "^\s*auto_merge:" config.yaml 2>/dev/null | awk '{print $2}' || echo "false")

# Merge method (merge | squash | rebase)
MERGE_METHOD=$(grep -E "^\s*merge_method:" config.yaml 2>/dev/null | awk '{print $2}' || echo "squash")

# Delete branch after merge
DELETE_BRANCH=$(grep -E "^\s*delete_branch_after_merge:" config.yaml 2>/dev/null | awk '{print $2}' || echo "true")
```

Use `gh` for GitHub, `glab` for GitLab.

### 2. Gather Information

```bash
# Current branch
BRANCH=$(git branch --show-current)

# Extract ticket ID from branch name
TICKET_ID=$(echo $BRANCH | grep -oP 'TASK-\d+')

# Get commit log for this branch
git log $TARGET_BRANCH..$BRANCH --oneline

# Find PRD with this ticket
grep -l "$TICKET_ID" docs/prds/*.md 2>/dev/null || echo "No PRD found"
```

### 3. Create PR/MR

**For GitHub (repo.type: github):**

```bash
gh pr create \
  --base $TARGET_BRANCH \
  --title "[$TICKET_ID] Description from ticket" \
  --body "$(cat <<'EOF'
## Summary

Brief description of what this PR does.

## Related

- **Ticket:** [TASK-XXX](asana-link)
- **PRD:** docs/prds/YYYY-MM-DD-feature.md

## Changes

### Added
- New feature/file

### Changed
- Modified behavior

## Testing

- [x] Unit tests added
- [x] All tests pass
- [ ] Manual testing completed

## Checklist

- [x] Tests pass
- [x] Lint passes
- [x] Ticket linked
- [x] Ready for review
EOF
)"
```

**For GitLab (repo.type: gitlab):**

```bash
glab mr create \
  --target-branch $TARGET_BRANCH \
  --title "[$TICKET_ID] Description from ticket" \
  --description "$(cat <<'EOF'
## Summary

Brief description of what this MR does.

## Related

- **Ticket:** [TASK-XXX](asana-link)
- **PRD:** docs/prds/YYYY-MM-DD-feature.md

## Changes

### Added
- New feature/file

### Changed
- Modified behavior

## Testing

- [x] Unit tests added
- [x] All tests pass
- [ ] Manual testing completed

## Checklist

- [x] Tests pass
- [x] Lint passes
- [x] Ticket linked
- [x] Ready for review
EOF
)"
```

### 4. Update Asana Ticket

Add PR/MR link to the Asana ticket.

## Deliverable

Return:

```
PR/MR CREATED

PR/MR: #[number] - [title]
URL: https://github.com/... or https://gitlab.com/...

Branch: feature/TASK-XXX-description → main

Linked:
- Ticket: TASK-XXX (updated with PR/MR link)
- PRD: docs/prds/YYYY-MM-DD-feature.md

Local Checks: ✅ Passed (typecheck, lint, tests, build)

Next: Get review, then /validate
```

---

## After Agent Returns

1. **Verify** PR/MR was created
2. **Provide** PR/MR link to user
3. **Next step:** Get review, then `/validate`

---

## ✅ FINAL ACTION (MANDATORY)

**After PR/MR is created, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["pr"] | unique)'
fi
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## Ticket for PR/MR

$ARGUMENTS
