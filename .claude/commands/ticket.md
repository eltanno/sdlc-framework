# Ticket Creation Phase - Orchestrator Instructions

**You are the orchestrator. Use Asana MCP for deterministic task creation.**

## Prerequisites Check

Before proceeding, verify:
1. PRD document exists and is APPROVED
2. Asana MCP is configured and accessible

```bash
# Check for approved PRD
grep -l "Status.*APPROVED" docs/prds/*.md 2>/dev/null
```

If no approved PRD exists:
- "No approved PRD found. Please run `/prd` first and get it approved."

## Read Configuration

Load project config for Asana settings:
```yaml
# From .claude/config.yaml
pm:
  tool: asana
  asana:
    project_id: "${ASANA_PROJECT_ID}"
    workspace_id: "${ASANA_WORKSPACE_ID}"
```

## Task: Create Asana Tasks

### Step 1: Parse PRD Tickets Table

Read the PRD and extract the tickets table:

```markdown
| ID | Title | Description | Priority | Estimate |
|----|-------|-------------|----------|----------|
| TBD | Ticket 1 | Description | P1 | M |
| TBD | Ticket 2 | Description | P2 | S |
```

### Step 2: Create Tasks via Asana MCP

For each ticket in the PRD, execute:

```
mcp__asana__create_task({
  workspace_id: "<from config or env>",
  project_id: "<from config or env>",
  name: "[TASK] {title from PRD}",
  notes: "## Context\n\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n## Description\n\n{description}\n\n## Acceptance Criteria\n\n{criteria from PRD}\n\n## Estimate\n\n{estimate}",
  due_on: null,  // Or set if timeline defined
  assignee: null  // Or set if known
})
```

**Expected response:**
```json
{
  "gid": "1234567890",
  "name": "[TASK] Ticket title",
  "permalink_url": "https://app.asana.com/0/..."
}
```

### Step 3: Capture Task IDs

Store the returned task IDs:

| PRD # | Asana GID | Title | URL |
|-------|-----------|-------|-----|
| 1 | 1234567890 | Ticket 1 | https://app.asana.com/... |
| 2 | 1234567891 | Ticket 2 | https://app.asana.com/... |

### Step 4: Update PRD with Task IDs

Use the Edit tool to update the PRD's ticket table:

```
Edit({
  file_path: "docs/prds/YYYY-MM-DD-feature.md",
  old_string: "| TBD | Ticket 1 |",
  new_string: "| ASANA-1234567890 | Ticket 1 |"
})
```

Repeat for each ticket.

### Step 5: Create Parent Task (if 3+ tickets)

If there are 3 or more tickets, create a parent task:

```
mcp__asana__create_task({
  workspace_id: "<workspace>",
  project_id: "<project>",
  name: "[EPIC] {feature name}",
  notes: "## Feature\n\n{feature description}\n\n## PRD\n\ndocs/prds/YYYY-MM-DD-feature.md\n\n## Child Tasks\n\n- ASANA-123: Ticket 1\n- ASANA-456: Ticket 2\n- ASANA-789: Ticket 3"
})
```

## Deliverable

Return structured output:

```
TICKETS CREATED

PRD: docs/prds/YYYY-MM-DD-feature.md (updated with task IDs)

## Tasks Created

| # | Asana ID | Title | URL |
|---|----------|-------|-----|
| 1 | ASANA-1234567890 | Ticket 1 | [link](https://app.asana.com/0/...) |
| 2 | ASANA-1234567891 | Ticket 2 | [link](https://app.asana.com/0/...) |

Total: 2 tasks created

## Next Steps

Ready to implement. Run:
- `/implement ASANA-1234567890` for Ticket 1
- `/implement ASANA-1234567891` for Ticket 2
```

## Error Handling

### If Asana MCP not available:
```
ERROR: Asana MCP not configured.

To configure, add to your MCP settings:
{
  "mcpServers": {
    "asana": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-asana"],
      "env": {
        "ASANA_ACCESS_TOKEN": "your-token"
      }
    }
  }
}

See README.md for full setup instructions.
```

### If task creation fails:
- Log the error
- Report which tasks succeeded/failed
- Don't update PRD for failed tasks
- Suggest retry or manual creation

## PRD to Process

$ARGUMENTS
