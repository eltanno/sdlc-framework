# Ticket Creation Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. Create tickets using the configured PM tool (or local tracking if none).**

## Prerequisites Check

Before proceeding, verify:
1. PRD document exists and is APPROVED

```bash
# Check for approved PRD
grep -l "Status.*APPROVED" docs/prds/*.md 2>/dev/null
```

If no approved PRD exists:
- "No approved PRD found. Please run `/prd` first and get it approved."

## Read Configuration

**Step 1: Check which PM tool is configured**

Read `config.yaml` from project root:

```yaml
pm:
  tool: asana    # asana | trello | github | linear | none
```

**Step 2: Route to appropriate tool**

Based on `pm.tool` value:

| pm.tool | Connection Required (.env) | MCP/Tool |
|---------|---------------------------|----------|
| `asana` | ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID | Asana MCP |
| `trello` | TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID | Trello MCP |
| `github` | gh CLI authenticated | `gh issue create` |
| `linear` | LINEAR_API_KEY, LINEAR_TEAM_ID | Linear MCP |
| `none` | (none) | Local tracking only |

---

## Common Step: Parse PRD Tickets Table

Read the PRD and extract the tickets table:

```markdown
| ID | Title | Description | Priority | Estimate |
|----|-------|-------------|----------|----------|
| TBD | Ticket 1 | Description | P1 | M |
| TBD | Ticket 2 | Description | P2 | S |
```

---

## Tool-Specific Instructions

### If pm.tool = asana

Create tasks via Asana MCP:

```
mcp__asana__create_task({
  workspace_id: "<from ASANA_WORKSPACE_ID>",
  project_id: "<from ASANA_PROJECT_ID>",
  name: "[TASK] {title from PRD}",
  notes: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n## Description\n\n{description}\n\n## Acceptance Criteria\n\n{criteria from PRD}\n\n## Estimate\n\n{estimate}"
})
```

Update PRD with: `ASANA-{gid}`

### If pm.tool = trello

Create cards via Trello MCP:

```
mcp__trello__add_card_to_list({
  listId: "<from TRELLO_LIST_ID or first list>",
  name: "[TASK] {title from PRD}",
  description: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n## Description\n\n{description}\n\n## Acceptance Criteria\n\n{criteria from PRD}"
})
```

Update PRD with: `TRELLO-{card-id}`

### If pm.tool = github

Create issues via gh CLI:

```bash
gh issue create \
  --title "[TASK] {title from PRD}" \
  --body "## Context

PRD: docs/prds/YYYY-MM-DD-feature.md

## Description

{description}

## Acceptance Criteria

{criteria from PRD}

## Estimate

{estimate}" \
  --label "task"
```

Update PRD with: `GH-{issue-number}`

### If pm.tool = linear

Create issues via Linear MCP (if available) or API:

```
mcp__linear__create_issue({
  teamId: "<from LINEAR_TEAM_ID>",
  title: "[TASK] {title from PRD}",
  description: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n{description}\n\n## Acceptance Criteria\n\n{criteria}"
})
```

Update PRD with: `LINEAR-{issue-id}`

### If pm.tool = none (Local Tracking Only)

Create tickets in local tracking file:

```bash
# Create or update docs/plans/PROGRESS.md
```

Format:

```markdown
# Implementation Progress

## Tickets

| ID | Title | Status | Branch |
|----|-------|--------|--------|
| LOCAL-001 | Ticket 1 | pending | - |
| LOCAL-002 | Ticket 2 | pending | - |
```

Update PRD with: `LOCAL-001`, `LOCAL-002`, etc.

---

## Update PRD with Task IDs

For ALL pm.tool options, update the PRD's ticket table:

```
Edit({
  file_path: "docs/prds/YYYY-MM-DD-feature.md",
  old_string: "| TBD | Ticket 1 |",
  new_string: "| {TOOL}-{ID} | Ticket 1 |"
})
```

---

## Create Parent/Epic (if 3+ tickets)

If there are 3 or more tickets:

| pm.tool | Action |
|---------|--------|
| asana | Create parent task with subtasks |
| trello | Add checklist to a summary card |
| github | Create milestone or project |
| linear | Create parent issue |
| none | Group in PROGRESS.md under epic heading |

---

## Deliverable

Return structured output:

```
TICKETS CREATED

PM Tool: {pm.tool from config}
PRD: docs/prds/YYYY-MM-DD-feature.md (updated with task IDs)

## Tasks Created

| # | ID | Title | URL |
|---|-----|-------|-----|
| 1 | {TOOL}-001 | Ticket 1 | [link](...) |
| 2 | {TOOL}-002 | Ticket 2 | [link](...) |

Total: N tasks created

## Next Steps

Ready to implement. Run:
- `/implement {TOOL}-001` for Ticket 1
- `/implement {TOOL}-002` for Ticket 2
```

---

## Error Handling

### If PM tool not configured:

```
WARNING: No PM tool configured in config.yaml

Options:
1. Configure a PM tool:
   - Edit config.yaml: pm.tool: asana (or trello, github, linear)
   - Add credentials to .env

2. Use local tracking:
   - Edit config.yaml: pm.tool: none
   - Tickets tracked in docs/plans/PROGRESS.md

See README.md for setup instructions.
```

### If connection fails:

- Log the error
- Report which tasks succeeded/failed
- Don't update PRD for failed tasks
- Suggest: check credentials, retry, or switch to `pm.tool: none`

### If MCP not available for configured tool:

```
ERROR: {tool} MCP not available but pm.tool: {tool} in config.yaml

Options:
1. Install the MCP plugin: claude plugin install {tool}
2. Switch to a different tool in config.yaml
3. Use pm.tool: none for local tracking
```

---

## Workflow State Update

**Note:** If running as part of `/ralph-prd`, ralph manages the workflow state. Only update if NOT in ralph mode.

At the **start** of this phase (if not in ralph mode):

```bash
# Only set phase if not already in ralph mode
current_phase=$(jq -r '.phase' workflow-state.json)
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "ticket"'
fi
```

At the **end** of this phase (after tickets are created), mark complete (if not in ralph mode):

```bash
current_phase=$(jq -r '.phase' workflow-state.json)
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["ticket"] | unique)'
fi
```

## PRD to Process

$ARGUMENTS
