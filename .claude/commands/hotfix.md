# Hotfix Phase - Orchestrator Instructions

**You are the orchestrator. Delegate to `engineer` agent with URGENCY flag.**

## When to Use

**PRODUCTION EMERGENCIES ONLY:**
- Production is down
- Security vulnerability
- Critical bug affecting all users
- Data corruption risk

For non-emergencies, use standard workflow: `/discover` → `/plan` → etc.

## Abbreviated Workflow

Hotfix skips Discovery, Plan, PRD but MUST still have:
- Ticket (for tracking)
- Tests (prevent regression)
- PR (code review)

```
/hotfix → ticket → engineer (urgent) → PR → merge
```

## Orchestrator Steps

### 1. Create Emergency Ticket

Do this directly (speed matters):

```bash
# Create ticket via Trello MCP
mcp__trello__add_card_to_list({
  listId: "<urgent-list-id>",
  name: "[HOTFIX] $ARGUMENTS",
  description: "## Emergency\n\nDescription of issue and impact.\n\n## Created\n$(date)"
})
```

### 2. Delegate to Engineer

```
Task({
  subagent_type: "engineer",
  model: "sonnet",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

---

**ENGINEER AGENT TASK: URGENT HOTFIX**

## ⚠️ URGENCY: This is a production emergency

## Context

Issue: $ARGUMENTS
Project: /home/jim/workspace/test-sdlc-project
Ticket: [TASK-XXX created above]

## Objective

Fix the production issue as quickly as possible while maintaining minimum quality standards.

## Your Tasks

### 1. Create Hotfix Branch (from main)

```bash
git checkout main
git pull origin main
git checkout -b hotfix/TASK-{id}-{description}
```

### 2. Reproduce and Fix

- Identify root cause
- Write a test that reproduces the bug
- Fix the bug
- Verify test passes

### 3. Minimal Testing

```bash
# Run tests (at minimum, the new test + related tests)
npm test

# Quick lint check
npm run lint
```

### 4. Commit with [HOTFIX] Tag

```
[HOTFIX][TASK-XXX] Fix critical issue

- Root cause: X
- Fix: Y

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 5. Create PR Immediately

```bash
git push -u origin $(git branch --show-current)

gh pr create \
  --title "[HOTFIX][TASK-XXX] Fix: description" \
  --body "## HOTFIX - Production Emergency

### Issue
What was broken.

### Root Cause
Why it happened.

### Fix
What this PR does.

### Testing
- [x] Regression test added
- [x] Tests pass

### Rollback
How to rollback if needed.

Ticket: TASK-XXX"
```

## Deliverable

Return:

```
HOTFIX COMPLETE

Ticket: TASK-XXX
Branch: hotfix/TASK-XXX-description
PR: #[number] - [HOTFIX] title

Root Cause: [brief explanation]
Fix: [what was changed]

Tests: PASS
PR URL: https://github.com/...

READY FOR EXPEDITED REVIEW

Post-merge:
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Create follow-up ticket if proper fix needed
```

## Critical Rules

1. **Speed matters** but don't skip tests
2. **One test minimum** - reproduce the bug
3. **Small fix** - don't refactor, just fix
4. **Document** - future you needs to understand

---

## After Agent Returns

### Expedited Review Process

1. **Tag reviewers directly** - Don't wait for normal review cycle
2. **Get single approval** - One approval is enough for hotfix
3. **Merge immediately** after approval

```bash
gh pr merge --squash
```

### Post-Merge

1. **Deploy** to production
2. **Monitor** for 15-30 minutes
3. **Update ticket** with resolution
4. **Create follow-up** if hotfix is a band-aid

### If True P0 (Production Down)

Can merge with post-hoc review:
1. Merge immediately
2. Get review within 24 hours
3. Document in incident report

## Issue to Hotfix

$ARGUMENTS
