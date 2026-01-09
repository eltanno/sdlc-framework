# Ticket Creation Phase - Orchestrator Instructions

**You are the orchestrator. This is a simple coordination task - delegate to haiku or do directly.**

## Prerequisites Check

Before proceeding, verify:
1. PRD document exists and is APPROVED

```bash
# Check for approved PRD
grep -l "Status: APPROVED" docs/prds/*.md 2>/dev/null
```

If no approved PRD exists:
- "No approved PRD found. Please run `/prd` first and get it approved."

## Task: Create Asana Tickets

This phase is simple enough for haiku or direct execution:

```
Task({
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

---

**TASK: Create Asana Tickets from PRD**

## Context

PRD location: $ARGUMENTS (or find most recent approved PRD)
Project: /home/jim/workspace/test-sdlc-project

## Objective

Create Asana tasks for each ticket defined in the PRD's ticket table, then update the PRD with the actual ticket IDs.

## Steps

1. **Read the PRD** - Find the Tickets table

2. **For each ticket, create Asana task:**

   Use the Trello MCP tool (or Asana API):
   ```
   mcp__trello__add_card_to_list({
     listId: "<appropriate-list-id>",
     name: "[TASK] Ticket title from PRD",
     description: "## Context\nPRD: docs/prds/YYYY-MM-DD-feature.md\n\n## Description\n{description from PRD}\n\n## Acceptance Criteria\n{criteria from PRD}"
   })
   ```

3. **Record the ticket ID** returned from each creation

4. **Update the PRD** - Replace "TBD" with actual ticket IDs in the table

## Deliverable

Return:

```
TICKETS CREATED

PRD Updated: docs/prds/YYYY-MM-DD-feature.md

Tickets:
| PRD # | Asana ID | Title |
|-------|----------|-------|
| 1 | TASK-123 | Title |
| 2 | TASK-124 | Title |

Total: [N] tickets created

Next: Ready for /implement TASK-XXX
```

---

## After Agent Returns

1. **Verify** tickets were created
2. **Verify** PRD was updated with ticket IDs
3. **Summarize** for user with ticket links
4. **Next step:** User can now run `/implement TASK-XXX` for any ticket

## PRD to Process

$ARGUMENTS
