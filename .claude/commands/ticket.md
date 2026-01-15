# Ticket Creation Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. Create tickets using the configured PM tool (or local tracking if none).**

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "ticket"'
fi
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

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

**Step 1: Read ticket configuration**

Read `config.yaml` from project root:

```yaml
tickets:
  prefix: "SDLC"    # Project code prefix for all tickets
  counter: 0        # Current ticket count
```

Store these values:
- `TICKET_PREFIX` = tickets.prefix (e.g., "SDLC")
- `TICKET_COUNTER` = tickets.counter (e.g., 0)

**Step 2: Check which PM tool is configured**

```yaml
pm:
  tool: asana    # asana | trello | github | linear | none
```

**Step 3: Route to appropriate tool**

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

**Generate Ticket IDs:**

For each ticket in the table, generate an ID using the prefix and counter:
- First ticket: `{TICKET_PREFIX}-{TICKET_COUNTER + 1}` (e.g., SDLC-0001)
- Second ticket: `{TICKET_PREFIX}-{TICKET_COUNTER + 2}` (e.g., SDLC-0002)
- Use zero-padded 4-digit numbers (0001, 0002, etc.)

These IDs are used regardless of which PM tool is configured.

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

Update PRD with: `{TICKET_PREFIX}-{N}` (e.g., SDLC-0001)

### If pm.tool = trello

Create cards via Trello MCP:

```
mcp__trello__add_card_to_list({
  listId: "<from TRELLO_LIST_ID or first list>",
  name: "[TASK] {title from PRD}",
  description: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n## Description\n\n{description}\n\n## Acceptance Criteria\n\n{criteria from PRD}"
})
```

Update PRD with: `{TICKET_PREFIX}-{N}` (e.g., SDLC-0001)

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

Update PRD with: `{TICKET_PREFIX}-{N}` (e.g., SDLC-0001)

### If pm.tool = linear

Create issues via Linear MCP (if available) or API:

```
mcp__linear__create_issue({
  teamId: "<from LINEAR_TEAM_ID>",
  title: "[TASK] {title from PRD}",
  description: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n{description}\n\n## Acceptance Criteria\n\n{criteria}"
})
```

Update PRD with: `{TICKET_PREFIX}-{N}` (e.g., SDLC-0001)

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
| {TICKET_PREFIX}-0001 | Ticket 1 | pending | - |
| {TICKET_PREFIX}-0002 | Ticket 2 | pending | - |
```

Update PRD with: `{TICKET_PREFIX}-{N}` (e.g., SDLC-0001, SDLC-0002)

---

## Update PRD with Task IDs

For ALL pm.tool options, update the PRD's ticket table using the project prefix:

```
Edit({
  file_path: "docs/prds/YYYY-MM-DD-feature.md",
  old_string: "| TBD | Ticket 1 |",
  new_string: "| {TICKET_PREFIX}-0001 | Ticket 1 |"
})
```

## Update Ticket Counter

**CRITICAL: After creating tickets, update the counter in config.yaml**

Calculate the new counter value:
- `NEW_COUNTER = TICKET_COUNTER + number_of_tickets_created`

Update config.yaml:

```
Edit({
  file_path: "config.yaml",
  old_string: "counter: {TICKET_COUNTER}",
  new_string: "counter: {NEW_COUNTER}"
})
```

This ensures the next `/ticket` run starts from the correct number and avoids ID collisions.

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
Ticket Counter: {TICKET_COUNTER} → {NEW_COUNTER}

## Tasks Created

| # | ID | Title | URL |
|---|-----|-------|-----|
| 1 | {TICKET_PREFIX}-0001 | Ticket 1 | [link](...) |
| 2 | {TICKET_PREFIX}-0002 | Ticket 2 | [link](...) |

Total: N tasks created

## Next Steps

Ready to implement. Run:
- `/implement {TICKET_PREFIX}-0001` for Ticket 1
- `/implement {TICKET_PREFIX}-0002` for Ticket 2
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

---

## ✅ FINAL ACTION (MANDATORY)

**After tickets are created, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["ticket"] | unique)'
fi
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## PRD to Process

$ARGUMENTS
