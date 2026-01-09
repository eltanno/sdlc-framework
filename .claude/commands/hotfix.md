# Hotfix Phase - Orchestrator Instructions

**Production emergencies only. Uses Asana MCP + engineer agent.**

## When to Use

**PRODUCTION EMERGENCIES ONLY:**
- Production is down
- Security vulnerability
- Critical bug affecting all users
- Data corruption risk

For non-emergencies, use standard workflow: `/discover` → `/plan` → etc.

## Abbreviated Workflow

```
/hotfix → Asana task (MCP) → engineer agent → PR (gh CLI) → merge
```

Skips Discovery, Plan, PRD but MUST still have:
- Asana ticket (for tracking)
- Tests (prevent regression)
- PR (code review)

## Step 1: Create Emergency Ticket via Asana MCP

**Execute immediately** (speed matters):

```
mcp__asana__create_task({
  workspace_id: "<from config>",
  project_id: "<from config>",
  name: "[HOTFIX] $ARGUMENTS",
  notes: "## Emergency\n\n**Issue:** $ARGUMENTS\n\n**Impact:** [To be documented]\n\n**Created:** $(date -Iseconds)\n\n## Status\n\n- [ ] Root cause identified\n- [ ] Fix implemented\n- [ ] Tests added\n- [ ] PR created\n- [ ] Deployed\n- [ ] Verified",
  due_on: "$(date -I)",  // Due today
  assignee: null
})
```

**Capture response:**
```json
{
  "gid": "1234567890",
  "permalink_url": "https://app.asana.com/0/..."
}
```

Store as `TASK_ID="ASANA-1234567890"`

## Step 2: Delegate to Engineer Agent

```
Task({
  subagent_type: "engineer",
  model: "opus",
  prompt: <see below>
})
```

### Engineer Agent Prompt

---

**ENGINEER AGENT TASK: URGENT HOTFIX**

## ⚠️ URGENCY: Production Emergency

## Context

- **Issue:** $ARGUMENTS
- **Ticket:** ASANA-{gid} - {permalink_url}
- **Project:** /home/jim/workspace/test-sdlc-project

## Objective

Fix the production issue quickly while maintaining minimum quality standards.

## Required Steps

### 1. Create Hotfix Branch

```bash
git checkout main
git pull origin main
git checkout -b hotfix/ASANA-{gid}-{short-description}
```

### 2. Reproduce → Test → Fix

```bash
# Write test that reproduces the bug
# Implement the fix
# Verify test passes

npm test
```

### 3. Verify Quality

```bash
npm test          # All tests pass
npm run lint      # No lint errors
```

### 4. Commit with Hotfix Tag

```bash
git add -A
git commit -m "[HOTFIX][ASANA-{gid}] Fix: {description}

- Root cause: {explain}
- Fix: {what changed}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 5. Push and Create PR

```bash
git push -u origin $(git branch --show-current)

gh pr create \
  --title "[HOTFIX][ASANA-{gid}] {description}" \
  --body "## 🚨 HOTFIX - Production Emergency

### Issue
{what was broken}

### Root Cause
{why it happened}

### Fix
{what this PR does}

### Testing
- [x] Regression test added
- [x] All tests pass
- [x] Lint passes

### Rollback
\`\`\`bash
git revert {commit-sha}
\`\`\`

### Ticket
[ASANA-{gid}]({permalink_url})"
```

## Deliverable

```
HOTFIX COMPLETE

Ticket: ASANA-{gid}
URL: {permalink_url}

Branch: hotfix/ASANA-{gid}-{description}
PR: #{number} - {title}
PR URL: {pr_url}

Root Cause: {brief explanation}
Fix: {what was changed}

Tests: PASS
Lint: PASS

READY FOR EXPEDITED REVIEW
```

---

## Step 3: Update Asana Task with PR Link

After engineer returns, update the task:

```
mcp__asana__update_task({
  task_id: "{gid}",
  notes: "{existing notes}\n\n## Resolution\n\n- **PR:** {pr_url}\n- **Root Cause:** {root_cause}\n- **Fix:** {fix_description}"
})
```

## Step 4: Expedited Review Process

1. **Notify reviewers directly** - Don't wait for normal cycle
2. **Single approval sufficient** - For hotfixes
3. **Merge immediately** after approval:

```bash
gh pr merge --squash --delete-branch
```

## Step 5: Post-Merge

1. **Deploy** to production
2. **Verify** fix in production
3. **Update Asana task:**

```
mcp__asana__update_task({
  task_id: "{gid}",
  completed: true
})
```

4. **Create follow-up** if hotfix is a band-aid:

```
mcp__asana__create_task({
  workspace_id: "<workspace>",
  project_id: "<project>",
  name: "[TECH-DEBT] Proper fix for {issue}",
  notes: "## Context\n\nHotfix ASANA-{gid} was a quick fix.\n\n## Needed\n\nProper implementation of {description}"
})
```

## Error Handling

### If Asana MCP unavailable:
- Create GitHub Issue as fallback: `gh issue create --title "[HOTFIX] {desc}" --body "..."`
- Document the issue number
- Continue with fix

### If tests fail:
- Do NOT merge
- Fix tests first
- Speed doesn't justify breaking things

## Issue to Hotfix

$ARGUMENTS
