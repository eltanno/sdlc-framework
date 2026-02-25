# Implementation Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. Delegate this to the `engineer` agent.**

**Agent definition**: See `.claude/agents/engineer.md` for engineer responsibilities and coding standards.

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.phase = "implement"'
fi
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Prerequisites Check

Before delegating, verify:
1. Ticket ID is provided (TASK-XXX)
2. PRD exists with this ticket ID

If no ticket ID provided:
- "Which ticket should I implement? Please provide the ticket ID (e.g., `/implement TASK-123`)"

## Gather Context for Engineer

Before delegating, collect:

1. **Ticket details** from PM tool (see below)
2. **Acceptance criteria** from PRD
3. **Technical approach** from Plan (if relevant)
4. **Current branch status**

```bash
git branch --show-current
git status --short
```

### Fetch Ticket Details from PM Tool

**Read PM tool configuration:**

```bash
# Get PM tool from config.yaml
PM_TOOL=$(grep -E "^\s*tool:" config.yaml 2>/dev/null | head -1 | awk '{print $2}' || echo "github")
```

**For Asana (`pm.tool: asana`):**

Use the `AsanaPM.get_task_details()` method to fetch task details including subtasks (acceptance criteria):

```python
# Via Python (recommended - uses AsanaPM class)
from core.asana_pm import AsanaPM

try:
    pm = AsanaPM()
    # task_id is the Asana task GID (from the ticket)
    task_details = pm.get_task_details(task_id)

    # task_details includes:
    # - name: Task title
    # - notes: Task description
    # - subtasks: List of subtasks (acceptance criteria)
    # - tags: Task tags
    # - dependencies: Task dependencies
    # - completed: Completion status

    print(f"Task: {task_details['name']}")
    print(f"Description: {task_details['notes']}")

    if task_details.get('subtasks'):
        print("Acceptance Criteria (subtasks):")
        for subtask in task_details['subtasks']:
            status = "✓" if subtask.get('completed') else "○"
            print(f"  {status} {subtask['name']}")

    if task_details.get('dependencies'):
        print("Dependencies:")
        for dep in task_details['dependencies']:
            print(f"  - {dep['name']}")
except Exception as e:
    print(f"Warning: Could not fetch Asana task details: {e}")
    # Continue - PRD still has acceptance criteria
```

Or via Asana REST API directly:

```bash
# GET /tasks/{task_id} - task details
curl -s "https://app.asana.com/api/1.0/tasks/${TASK_ID}" \
  -H "Authorization: Bearer ${ASANA_ACCESS_TOKEN}" | jq '.data'

# GET /tasks/{task_id}/subtasks - acceptance criteria
curl -s "https://app.asana.com/api/1.0/tasks/${TASK_ID}/subtasks" \
  -H "Authorization: Bearer ${ASANA_ACCESS_TOKEN}" | jq '.data'
```

**For GitHub (`pm.tool: github`):**

```bash
# Get issue details
gh issue view $ISSUE_NUMBER --json title,body,labels
```

**Important:** Include both the PM tool task details AND the PRD acceptance criteria in the engineer context. The PM tool may have additional context (subtasks, dependencies) not in the PRD.

## Delegation

```
Task({
  subagent_type: "engineer",
  model: "opus",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the engineer agent:

---

**ENGINEER AGENT TASK: TDD Implementation**

## Context

Ticket: $ARGUMENTS
Project location: [current project directory]

PRD: [path to PRD]
Acceptance Criteria:
[paste acceptance criteria for this ticket from PRD]

Technical Notes:
[any relevant technical context from plan]

## Objective

Implement this ticket using Test-Driven Development (TDD).

## Your Implementation Tasks

### 1. Create Feature Branch

Read the default branch from `config.yaml` (`git.default_branch`):

```bash
DEFAULT_BRANCH=$(grep -A1 "^git:" config.yaml | grep "default_branch:" | awk '{print $2}')
git fetch origin $DEFAULT_BRANCH
git checkout -b feature/TASK-{id}-{short-description} origin/$DEFAULT_BRANCH
```

### 2. TDD Cycle

**RED Phase:**
- Write failing tests that define expected behavior
- Cover acceptance criteria from PRD
- Include edge cases

```bash
# Run tests - should FAIL
npm test
```

**GREEN Phase:**
- Write minimum code to make tests pass
- Focus on functionality, not perfection

```bash
# Run tests - should PASS
npm test
```

**REFACTOR Phase:**
- Clean up code while keeping tests green
- Remove duplication
- Improve naming

### 3. Verify Quality (ALL MUST PASS)

Read commands from `config.yaml` under `dev:` section and run them in order:

1. **Typecheck** - `dev.typecheck_command` - Must pass with no errors
2. **Lint** - `dev.lint_command` - Must pass with no errors
3. **Test** - `dev.test_command` - All tests must pass
4. **Build** - `dev.build_command` - Must succeed

Also check for debug statements (console.log, print, debugger, etc.) in production code.

**Do NOT proceed to commit if any check fails. Fix issues first.**

### 4. Commit Changes

```
[TASK-XXX] Brief description

- What was implemented
- Key changes

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Deliverable

After implementation, return:

```
IMPLEMENTATION COMPLETE

Ticket: TASK-XXX
Branch: feature/TASK-XXX-description

Changes:
- file1.ts: [what changed]
- file2.ts: [what changed]

Tests Added:
- test1: [what it tests]
- test2: [what it tests]

Acceptance Criteria Status:
- [x] Criterion 1 - covered by test_xxx
- [x] Criterion 2 - covered by test_xxx

Verification:
- Typecheck: PASS
- Lint: PASS
- Tests: PASS
- Build: PASS

Commits: [N] commits on branch

Next: Ready for /pr TASK-XXX
```

## Critical Rules

1. **Tests FIRST** - Write failing tests before implementation
2. **Small commits** - Commit logical chunks, not everything at once
3. **All checks pass** - Never commit if typecheck, lint, tests, or build fail
4. **Match acceptance criteria** - Every criterion should have a test

---

## After Agent Returns

1. **Verify** branch exists with commits
2. **Verify** tests pass
3. **Verify** acceptance criteria are covered
4. **Summarize** implementation for user
5. **Next step:** User can run `/pr TASK-XXX`

---

## ✅ FINAL ACTION (MANDATORY)

**After implementation is complete, update the workflow state (if not in ralph mode):**

```bash
current_phase=$(jq -r '.phase' workflow-state.json 2>/dev/null || echo "")
if [ "$current_phase" != "ralph" ]; then
    .claude/scripts/update-workflow-state.sh '.completed = (.completed + ["implement"] | unique)'
fi
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## Ticket to Implement

$ARGUMENTS
