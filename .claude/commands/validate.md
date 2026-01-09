# Validation Phase

You are entering the Validation phase - final checks before merge.

## Prerequisites

Before starting this phase, verify:
- [ ] PR exists and is approved
- [ ] All CI checks have passed

## Purpose

Perform final validation to ensure the PR is ready to merge.

## Validation Checklist

### Code Quality

- [ ] All tests pass (run locally to confirm)
- [ ] No linting errors
- [ ] No TypeScript errors (if applicable)
- [ ] No console.log/print statements in production code
- [ ] No commented-out code
- [ ] No TODO comments without ticket references

### PR Status

- [ ] PR has required approvals
- [ ] All CI checks pass
- [ ] No merge conflicts
- [ ] Branch is up to date with main

### Documentation

- [ ] README updated (if public API changed)
- [ ] Inline documentation for complex logic
- [ ] PRD reflects final implementation (update if scope changed)

### Asana Ticket

- [ ] Ticket has PR link
- [ ] Ticket status is correct
- [ ] Acceptance criteria can be verified

### Testing Verification

Run these commands to verify:

```bash
# Pull latest main and rebase
git fetch origin main
git rebase origin/main

# Run full test suite
npm test

# Run linting
npm run lint

# Build (if applicable)
npm run build
```

## Acceptance Criteria Verification

For each acceptance criterion in the ticket/PRD:

| Criterion | Status | Verified By |
|-----------|--------|-------------|
| Given X, when Y, then Z | ✅ Pass | Test: test_name |
| Given A, when B, then C | ✅ Pass | Manual check |

## Final Steps

### If All Checks Pass

1. Merge the PR
2. Delete the feature branch
3. Update Asana ticket status to "Done"
4. Notify stakeholders if needed

```bash
# Merge via GitHub CLI
gh pr merge --squash --delete-branch

# Or merge via GitHub UI
```

### If Any Check Fails

1. Document what failed
2. Create fix commits
3. Re-run validation
4. Do NOT merge until all checks pass

## Exit Criteria

- [ ] All validation checks pass
- [ ] PR merged to main
- [ ] Feature branch deleted
- [ ] Asana ticket marked complete

---

**PR to validate:** $ARGUMENTS
