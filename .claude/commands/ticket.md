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
  tool: github    # asana | trello | github | linear | none
```

**⚠️ MANDATORY: If pm.tool is "none" or not set, STOP and prompt the user:**

```
PM tool not configured. Before creating tickets, please choose a tool:

1. **GitHub Issues** - Recommended if using GitHub (no extra setup)
2. **Trello** - Visual boards (requires Trello MCP + API credentials)
3. **Asana** - Full project management (requires ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID in .env)
4. **Linear** - Modern dev tool (requires Linear MCP + credentials)

Update config.yaml with your choice:
  pm:
    tool: github  # or trello, asana, linear

Then run /ticket again.
```

**Do NOT proceed with `pm.tool: none`** - tickets must be tracked in an external tool.

**Step 3: Route to appropriate tool**

Based on `pm.tool` value:

| pm.tool | Connection Required (.env) | Tool |
|---------|---------------------------|------|
| `github` | gh CLI authenticated | `gh issue create` |
| `trello` | TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID | Trello MCP |
| `asana` | ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID | Direct Asana REST API |
| `linear` | LINEAR_API_KEY, LINEAR_TEAM_ID | Linear MCP |

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

**Use the Asana REST API directly via the `AsanaPM` class.**

**Step 1: Ensure required tags exist (first run only)**

Before creating any tasks, ensure the required tags exist:

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()
pm.ensure_required_tags()  # Creates: task, blocked, ralph-0 through ralph-5
```

**Step 2: Create tasks via Asana REST API**

For each ticket in the PRD, create an Asana task:

```python
from core.asana_pm import AsanaPM

pm = AsanaPM()

# Create the task with title format: [{TICKET_PREFIX}-{N}] {title}
task_gid = pm.create_task(
    name="[{TICKET_PREFIX}-{N}] {title from PRD}",
    notes="""## Context

PRD: docs/prds/YYYY-MM-DD-feature.md

## Description

{description from PRD}

## Acceptance Criteria

{criteria from PRD - will be added as subtasks below}

## Estimate

{estimate from PRD}""",
    add_task_tag=True,  # Adds the 'task' tag for Ralph
)

# Store the task GID for dependency linking later
# task_gid is the Asana task ID (e.g., "1234567890")
```

**Step 3: Add acceptance criteria as subtasks**

For each acceptance criterion in the PRD, create a subtask:

```python
# Parse acceptance criteria from PRD
criteria_list = [
    "Given X, when Y, then Z",
    "Given A, when B, then C",
]

# Create subtasks for each criterion
for criterion in criteria_list:
    pm.create_subtask(
        parent_task_id=task_gid,
        name=criterion,
    )
```

**Step 4: Set dependencies between tasks**

If the PRD specifies dependencies between tickets, link them:

```python
# If ticket SDLC-0003 depends on SDLC-0001 and SDLC-0002
pm.add_dependencies(
    task_id=task_gid_for_0003,       # The dependent task
    dependency_ids=[                  # Tasks it depends on
        task_gid_for_0001,
        task_gid_for_0002,
    ],
)
```

**Note:** Track task GIDs during creation for dependency linking. The format is:
- PRD ticket ID (e.g., SDLC-0001) → Asana task GID (e.g., "1234567890")

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

**Step 1: Ensure required labels exist**

Before creating any issues, ensure the required labels exist in the repository (uses gh api for compatibility with older gh versions):

```bash
# Get repo name
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')

# Create 'task' label if missing (green - work items for Ralph)
gh api "repos/$REPO/labels" -f name="task" -f description="Work item for Ralph automation" -f color="0E8A16" 2>/dev/null || true

# Create 'blocked' label if missing (red - tickets that need manual intervention)
gh api "repos/$REPO/labels" -f name="blocked" -f description="Ticket is blocked and needs manual intervention" -f color="D93F0B" 2>/dev/null || true

# Create Ralph instance labels for parallel execution
# Read prefix from config.yaml (default: "ralph-")
RALPH_PREFIX=$(grep -E '^\s*instance_label_prefix:' config.yaml 2>/dev/null | sed 's/.*instance_label_prefix:\s*"\?\([^"#]*\)"\?.*/\1/' | tr -d ' ' | head -1)
RALPH_PREFIX="${RALPH_PREFIX:-ralph-}"
for i in {0..5}; do
    gh api "repos/$REPO/labels" -f name="${RALPH_PREFIX}$i" -f description="Ralph instance $i" -f color="0052CC" 2>/dev/null || true
done
```

**Step 2: Create issues via gh CLI**

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
| github | Create milestone or project |
| trello | Add checklist to a summary card |
| asana | Create parent task with subtasks |
| linear | Create parent issue |

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
ERROR: PM tool not configured in config.yaml

A PM tool is REQUIRED for ticket tracking. Please configure one:

1. GitHub Issues (recommended): pm.tool: github
2. Trello: pm.tool: trello (+ Trello MCP credentials)
3. Asana: pm.tool: asana (+ ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID in .env)
4. Linear: pm.tool: linear (+ Linear MCP credentials)

Update config.yaml and run /ticket again.
```

### If connection fails:

- Log the error
- Report which tasks succeeded/failed
- Don't update PRD for failed tasks
- Suggest: check credentials, retry, or switch to `pm.tool: none`

### If MCP not available for configured tool (Trello, Linear):

```
ERROR: {tool} MCP not available but pm.tool: {tool} in config.yaml

Options:
1. Install the MCP plugin: claude plugin install {tool}
2. Switch to a different tool in config.yaml
3. Use pm.tool: none for local tracking
```

### If Asana credentials missing:

```
ERROR: Missing Asana credentials

Asana requires environment variables to be set:
- ASANA_ACCESS_TOKEN: Personal Access Token from Asana
- ASANA_WORKSPACE_ID: Workspace GID
- ASANA_PROJECT_ID: Project GID where tasks will be created

Set these in your .env file and try again.
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
