# Hotfix Phase - Orchestrator Instructions

> **MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Production emergencies only. Uses configured PM tool + engineer agent.**

## When to Use

**PRODUCTION EMERGENCIES ONLY:**
- Production is down
- Security vulnerability
- Critical bug affecting all users
- Data corruption risk

For non-emergencies, use standard workflow: `/discover` -> `/plan` -> etc.

## Abbreviated Workflow

```
/hotfix -> PM ticket (Asana API or GitHub CLI) -> engineer agent -> PR/MR (gh/glab CLI) -> merge
```

**Note:** Commands use `gh` (GitHub) or `glab` (GitLab) based on `repo.type` in `config.yaml`.

Skips Discovery, Plan, PRD but MUST still have:
- PM ticket (for tracking)
- Tests (prevent regression)
- PR (code review)

---

## Step 1: Read PM Tool Configuration

**First, read which PM tool is configured:**

Read `config.yaml` from project root:

```yaml
pm:
  tool: github    # asana | trello | github | linear | none
```

Store the value as `PM_TOOL`.

**Based on `pm.tool` value, follow the appropriate section below:**

| pm.tool | Action |
|---------|--------|
| `asana` | Use Asana REST API via AsanaPM class |
| `github` | Use gh CLI to create issue |
| `trello` | Use Trello MCP |
| `linear` | Use Linear MCP |
| `none` | Skip ticket creation (log only) |

---

## Step 2A: Create Emergency Ticket (pm.tool: asana)

**If pm.tool = asana, use the Asana REST API directly:**

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()

# Create the hotfix task with [HOTFIX] prefix
task_gid = pm.create_task(
    name="[HOTFIX] $ARGUMENTS",
    notes="""## Emergency

**Issue:** $ARGUMENTS

**Impact:** [To be documented]

**Created:** {current datetime ISO format}

## Status

- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Tests added
- [ ] PR created
- [ ] Deployed
- [ ] Verified""",
    add_task_tag=True,
)

# Get the task URL for reference
# Format: https://app.asana.com/0/{project_id}/{task_gid}
task_url = f"https://app.asana.com/0/{ASANA_PROJECT_ID}/{task_gid}"
```

**Store for later reference:**
- `TASK_ID = "ASANA-{task_gid}"` (e.g., ASANA-1234567890)
- `TASK_URL = "{task_url}"`

---

## Step 2B: Create Emergency Ticket (pm.tool: github)

**If pm.tool = github, use gh CLI directly:**

```bash
# Create GitHub issue with [HOTFIX] prefix
gh issue create \
  --title "[HOTFIX] $ARGUMENTS" \
  --body "## Emergency

**Issue:** $ARGUMENTS

**Impact:** [To be documented]

**Created:** $(date -Iseconds)

## Status

- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Tests added
- [ ] PR created
- [ ] Deployed
- [ ] Verified" \
  --label "task"
```

**Capture the issue number from output and store:**
- `TASK_ID = "GH-{issue_number}"` (e.g., GH-123)
- `TASK_URL = "https://github.com/{owner}/{repo}/issues/{issue_number}"`

---

## Step 2C: Create Emergency Ticket (pm.tool: trello)

**If pm.tool = trello, use Trello MCP:**

```
mcp__trello__add_card_to_list({
  listId: "<from TRELLO_LIST_ID or first list>",
  name: "[HOTFIX] $ARGUMENTS",
  description: "## Emergency\n\n**Issue:** $ARGUMENTS\n\n**Impact:** [To be documented]\n\n**Created:** {datetime}\n\n## Status\n\n- [ ] Root cause identified\n- [ ] Fix implemented\n- [ ] Tests added\n- [ ] PR created\n- [ ] Deployed\n- [ ] Verified"
})
```

**Store:**
- `TASK_ID = "TRELLO-{card_id}"`
- `TASK_URL = "{card_url}"`

---

## Step 2D: No PM Tool (pm.tool: none)

**If pm.tool = none:**

Log the hotfix locally but warn the user:

```
WARNING: No PM tool configured. Hotfix will not be tracked externally.
Consider configuring pm.tool in config.yaml for proper tracking.

Proceeding with local-only hotfix...
```

Use a local identifier:
- `TASK_ID = "LOCAL-HOTFIX-{timestamp}"`
- `TASK_URL = "N/A"`

---

## Step 3: Delegate to Engineer Agent

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

## URGENCY: Production Emergency

## Context

- **Issue:** $ARGUMENTS
- **Ticket:** {TASK_ID} - {TASK_URL}
- **Project:** [current project directory]

## Objective

Fix the production issue quickly while maintaining minimum quality standards.

## Required Steps

### 1. Create Hotfix Branch

```bash
git checkout main
git pull origin main
git checkout -b hotfix/{TASK_ID}-{short-description}
```

### 2. Reproduce -> Test -> Fix

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
git commit -m "[HOTFIX][{TASK_ID}] Fix: {description}

- Root cause: {explain}
- Fix: {what changed}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 5. Push and Create PR/MR

```bash
git push -u origin $(git branch --show-current)

# Read repo type from config.yaml (defaults to github)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")
```

**For GitHub (repo.type: github):**
```bash
gh pr create \
  --title "[HOTFIX][{TASK_ID}] {description}" \
  --body "## HOTFIX - Production Emergency
..."
```

**For GitLab (repo.type: gitlab):**
```bash
glab mr create \
  --title "[HOTFIX][{TASK_ID}] {description}" \
  --description "## HOTFIX - Production Emergency
..."
```

**PR/MR Body Content:**
```
## HOTFIX - Production Emergency

### Issue
{what was broken}

### Root Cause
{why it happened}

### Fix
{what this PR/MR does}

### Testing
- [x] Regression test added
- [x] All tests pass
- [x] Lint passes

### Rollback
git revert {commit-sha}

### Ticket
[{TASK_ID}]({TASK_URL})
```

## Deliverable

```
HOTFIX COMPLETE

Ticket: {TASK_ID}
URL: {TASK_URL}

Branch: hotfix/{TASK_ID}-{description}
PR: #{number} - {title}
PR URL: {pr_url}

Root Cause: {brief explanation}
Fix: {what was changed}

Tests: PASS
Lint: PASS

READY FOR EXPEDITED REVIEW
```

---

## Step 4: Update PM Ticket with PR Link

After engineer returns, update the ticket based on PM tool:

### If pm.tool = asana

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()

# Add a comment with the PR link
pm._post(
    f"/tasks/{task_gid}/stories",
    {"text": f"## Resolution\n\n- **PR:** {pr_url}\n- **Root Cause:** {root_cause}\n- **Fix:** {fix_description}"}
)
```

### If pm.tool = github

```bash
# Add comment to GitHub issue
gh issue comment {issue_number} --body "## Resolution

- **PR:** {pr_url}
- **Root Cause:** {root_cause}
- **Fix:** {fix_description}"
```

### If pm.tool = trello

```
mcp__trello__add_comment({
  cardId: "{card_id}",
  text: "## Resolution\n\n- **PR:** {pr_url}\n- **Root Cause:** {root_cause}\n- **Fix:** {fix_description}"
})
```

---

## Step 5: Expedited Review Process

1. **Notify reviewers directly** - Don't wait for normal cycle
2. **Single approval sufficient** - For hotfixes
3. **Merge immediately** after approval:

**GitHub:**
```bash
gh pr merge --squash --delete-branch
```

**GitLab:**
```bash
glab mr merge --squash --remove-source-branch
```

---

## Step 6: Post-Merge

1. **Deploy** to production
2. **Verify** fix in production
3. **Close the PM ticket:**

### If pm.tool = asana

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()
pm.close_ticket(task_gid)  # Marks complete and moves to Done section
```

### If pm.tool = github

```bash
gh issue close {issue_number}
```

### If pm.tool = trello

```
mcp__trello__move_card({
  cardId: "{card_id}",
  listId: "<done list id>"
})
```

4. **Create follow-up** if hotfix is a band-aid:

### If pm.tool = asana

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()
pm.create_task(
    name="[TECH-DEBT] Proper fix for {issue}",
    notes="## Context\n\nHotfix {TASK_ID} was a quick fix.\n\n## Needed\n\nProper implementation of {description}",
    add_task_tag=True,
)
```

### If pm.tool = github

```bash
gh issue create \
  --title "[TECH-DEBT] Proper fix for {issue}" \
  --body "## Context

Hotfix {TASK_ID} was a quick fix.

## Needed

Proper implementation of {description}" \
  --label "tech-debt"
```

---

## Error Handling

### If Asana credentials missing (pm.tool: asana):

```
ERROR: Missing Asana credentials

Asana requires environment variables:
- ASANA_ACCESS_TOKEN: Personal Access Token
- ASANA_WORKSPACE_ID: Workspace GID
- ASANA_PROJECT_ID: Project GID

Set these in .env and try again.

FALLBACK: Creating GitHub issue instead...
```

Then fall back to `gh issue create` if gh is available.

### If gh CLI not available (pm.tool: github):

```
ERROR: GitHub CLI (gh) not installed or not authenticated.

Install from: https://cli.github.com/
Then run: gh auth login

Proceeding WITHOUT ticket tracking (local only).
```

### If tests fail:
- Do NOT merge
- Fix tests first
- Speed doesn't justify breaking things

---

## Issue to Hotfix

$ARGUMENTS
