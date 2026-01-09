# Pull Request / Merge Request Phase - Orchestrator Instructions

**You are the orchestrator. This is coordination - delegate to haiku or do directly.**

## Prerequisites Check

Before proceeding, verify:
1. Feature branch exists with commits
2. All tests pass
3. Branch is pushed to remote

```bash
# Check current branch
git branch --show-current

# Check test status
npm test

# Check if pushed
git status

# Check repo type from .env
grep REPO_TYPE .env
```

If tests fail: "Tests are failing. Please fix before creating PR/MR."
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

### 1. Determine Provider

```bash
# Read REPO_TYPE from .env (defaults to github)
REPO_TYPE=$(grep -E "^REPO_TYPE=" .env 2>/dev/null | cut -d= -f2 || echo "github")
echo "Repository type: $REPO_TYPE"
```

### 2. Gather Information

```bash
# Current branch
BRANCH=$(git branch --show-current)

# Extract ticket ID from branch name
TICKET_ID=$(echo $BRANCH | grep -oP 'TASK-\d+')

# Get commit log for this branch
git log main..$BRANCH --oneline

# Find PRD with this ticket
grep -l "$TICKET_ID" docs/prds/*.md 2>/dev/null || echo "No PRD found"
```

### 3. Create PR/MR

**For GitHub (REPO_TYPE=github):**

```bash
gh pr create \
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

**For GitLab (REPO_TYPE=gitlab):**

```bash
glab mr create \
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

CI Status: [pending/running]

Next: Wait for CI, get review, then /validate
```

---

## After Agent Returns

1. **Verify** PR/MR was created
2. **Provide** PR/MR link to user
3. **Next step:** Wait for CI checks and review, then `/validate`

## Ticket for PR/MR

$ARGUMENTS
