# Pull Request Phase

You are entering the PR (Pull Request) phase.

## Prerequisites

Before starting this phase, verify:
- [ ] Feature branch exists with commits
- [ ] All tests pass
- [ ] Linting passes
- [ ] Branch is pushed to remote

If tests aren't passing, go back to `/implement` first.

## Purpose

Create a GitHub PR with proper documentation linking back to tickets and PRD.

## Your Task

1. Push branch to remote (if not already)
2. Create PR with proper format
3. Link to Asana ticket and PRD

## Pre-PR Checklist

Run these checks before creating the PR:

```bash
# Ensure tests pass
npm test

# Ensure linting passes
npm run lint

# Check for uncommitted changes
git status

# Push to remote
git push -u origin $(git branch --show-current)
```

## PR Format

### Title

```
[TASK-XXX] Brief description of the change
```

### Body

```markdown
## Summary

Brief description of what this PR does.

- Bullet point of key change
- Another key change

## Related

- **Asana Ticket:** [TASK-XXX](link-to-asana-task)
- **PRD:** [docs/prds/YYYY-MM-DD-feature.md](link)

## Changes

### Added
- New feature or file

### Changed
- Modified behavior

### Fixed
- Bug that was fixed

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

### Test Commands

```bash
npm test
```

## Screenshots (if applicable)

Add screenshots for UI changes.

## Checklist

- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated (if needed)
- [ ] Asana ticket linked
- [ ] Ready for review
```

## Creating the PR

Use GitHub CLI:

```bash
gh pr create \
  --title "[TASK-XXX] Description" \
  --body "$(cat <<'EOF'
## Summary
...

## Related
- **Asana Ticket:** [TASK-XXX](link)
- **PRD:** docs/prds/YYYY-MM-DD-feature.md

...
EOF
)"
```

## Exit Criteria

- [ ] PR created with proper title format
- [ ] PR body includes Asana ticket link
- [ ] PR body includes PRD link
- [ ] All CI checks pass
- [ ] Ready for review

## After PR Creation

1. Copy PR link
2. Update Asana ticket with PR link
3. Request review from appropriate team members
4. Monitor CI status

---

**Ticket for this PR:** $ARGUMENTS
