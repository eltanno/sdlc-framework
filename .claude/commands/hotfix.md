# Hotfix Phase

You are entering the Hotfix phase - for production emergencies ONLY.

## When to Use

Use this ONLY for:
- Production is down
- Security vulnerability discovered
- Critical bug affecting all users
- Data corruption risk

For non-emergencies, use the standard workflow (`/discover` → `/plan` → etc.)

## Abbreviated Workflow

Hotfixes skip Discovery, Plan, and PRD phases but MUST still have:
- Ticket reference
- Tests
- PR review (can be post-merge for critical issues)

## Hotfix Process

### 1. Create Ticket

Even in emergencies, create an Asana ticket first:

```
Title: [HOTFIX] Brief description of the issue
Priority: P0 - Critical
Description:
- What is broken
- Impact on users
- Root cause (if known)
```

### 2. Create Hotfix Branch

```bash
# Branch from main (or current production)
git checkout main
git pull origin main
git checkout -b hotfix/TASK-{id}-{description}
```

### 3. Fix with Tests

Even hotfixes need tests:

```bash
# Write a test that reproduces the bug
# Then fix the bug
# Verify test passes
npm test
```

### 4. Create PR with [HOTFIX] Prefix

```bash
gh pr create \
  --title "[HOTFIX][TASK-XXX] Fix critical issue" \
  --body "$(cat <<'EOF'
## HOTFIX - Production Emergency

### Issue
What was broken and the impact.

### Root Cause
Why it happened.

### Fix
What this PR does to fix it.

### Testing
- [ ] Test added to prevent regression
- [ ] Manually verified fix

### Rollback Plan
How to rollback if this makes things worse.

### Asana Ticket
[TASK-XXX](link)
EOF
)"
```

### 5. Get Expedited Review

For critical issues:
- Tag reviewers directly
- Use Slack/communication channel
- Can merge with single approval in true emergencies

### 6. Merge and Deploy

```bash
# Merge immediately after approval
gh pr merge --squash

# Deploy to production
# (your deployment process)
```

### 7. Post-Incident Tasks

After the fire is out:

1. **Update Ticket:** Document what happened and the fix
2. **Create Follow-up:** If the hotfix is a band-aid, create a ticket for proper fix
3. **Post-mortem:** For major incidents, write a post-mortem document

## Exit Criteria

- [ ] Ticket exists with [HOTFIX] label
- [ ] Hotfix branch created from main
- [ ] Tests added for the fix
- [ ] PR created with [HOTFIX] prefix
- [ ] At least one review (can be post-merge for P0)
- [ ] Merged and deployed
- [ ] Ticket updated with resolution
- [ ] Follow-up ticket created if needed

## Post-Merge Review

Even if merged without full review:
- Get a full review within 24 hours
- Document any technical debt introduced
- Schedule time to do it "right" if needed

---

**Issue to hotfix:** $ARGUMENTS
