# Pull Request Phase - Orchestrator Instructions

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
```

If tests fail: "Tests are failing. Please fix before creating PR."
If not pushed: Push first with `git push -u origin $(git branch --show-current)`

## Task: Create GitHub PR

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

**TASK: Create GitHub Pull Request**

## Context

Ticket: $ARGUMENTS
Project: [current project directory]

## Objective

Create a GitHub PR with proper documentation linking to the ticket and PRD.

## Steps

### 1. Gather Information

```bash
# Current branch
BRANCH=$(git branch --show-current)

# Extract ticket ID from branch name
TICKET_ID=$(echo $BRANCH | grep -oP 'TASK-\d+')

# Get commit log for this branch
git log main..$BRANCH --oneline

# Find PRD with this ticket
grep -l "$TICKET_ID" docs/prds/*.md
```

### 2. Create PR

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

### 3. Update Asana Ticket

Add PR link to the Asana ticket.

## Deliverable

Return:

```
PR CREATED

PR: #[number] - [title]
URL: https://github.com/...

Branch: feature/TASK-XXX-description → main

Linked:
- Ticket: TASK-XXX (updated with PR link)
- PRD: docs/prds/YYYY-MM-DD-feature.md

CI Status: [pending/running]

Next: Wait for CI, get review, then /validate
```

---

## After Agent Returns

1. **Verify** PR was created
2. **Provide** PR link to user
3. **Next step:** Wait for CI checks and review, then `/validate`

## Ticket for PR

$ARGUMENTS
