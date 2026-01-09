# Ticket Creation Phase

You are entering the Ticket Creation phase.

## Prerequisites

Before starting this phase, verify:
- [ ] PRD document exists and is APPROVED
- [ ] PRD contains ticket placeholders in the Tickets table

If no approved PRD exists, direct the user to `/prd` first.

## Purpose

Create Asana tasks from the PRD and update the PRD with task IDs for traceability.

## Your Task

1. Read the approved PRD
2. Create Asana tasks for each ticket in the PRD
3. Update the PRD with the Asana task IDs

## Ticket Creation Checklist

For each ticket in the PRD:

### 1. Create Asana Task

Use the Trello/Asana MCP tools (or direct API) to create tasks with:

- **Title:** Clear, actionable title from PRD
- **Description:**
  ```
  ## Context
  Link to PRD: [docs/prds/YYYY-MM-DD-feature.md]

  ## Description
  {Description from PRD}

  ## Acceptance Criteria
  - [ ] Criterion 1
  - [ ] Criterion 2

  ## Technical Notes
  Any relevant technical context
  ```
- **Priority:** From PRD ticket table
- **Labels:** Feature area, type (feature/bug/chore)

### 2. Update PRD

After creating each task, update the PRD's ticket table:

```markdown
| ID | Title | Description | Priority | Estimate |
|----|-------|-------------|----------|----------|
| TASK-123 | Ticket 1 | Description | P1 | M |
| TASK-456 | Ticket 2 | Description | P2 | S |
```

### 3. Create Parent Task (if multiple tickets)

If there are 3+ tickets, create a parent/epic task that links to all child tasks.

## Exit Criteria

- [ ] All tickets from PRD created in Asana
- [ ] Each ticket has acceptance criteria from PRD
- [ ] PRD updated with actual task IDs
- [ ] Parent task created if applicable
- [ ] Summary provided to user with task links

## Output Format

After completion, report:

```
## Tickets Created

| PRD Ticket | Asana ID | Link |
|------------|----------|------|
| Ticket 1 | TASK-123 | [link] |
| Ticket 2 | TASK-456 | [link] |

PRD updated with task IDs: docs/prds/YYYY-MM-DD-feature.md
```

---

**PRD to process:** $ARGUMENTS
