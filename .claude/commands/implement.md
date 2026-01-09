# Implementation Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `engineer` agent.**

## Prerequisites Check

Before delegating, verify:
1. Ticket ID is provided (TASK-XXX)
2. PRD exists with this ticket ID

If no ticket ID provided:
- "Which ticket should I implement? Please provide the ticket ID (e.g., `/implement TASK-123`)"

## Gather Context for Engineer

Before delegating, collect:

1. **Ticket details** from Asana
2. **Acceptance criteria** from PRD
3. **Technical approach** from Plan (if relevant)
4. **Current branch status**

```bash
git branch --show-current
git status --short
```

## Delegation

```
Task({
  subagent_type: "engineer",
  model: "sonnet",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the engineer agent:

---

**ENGINEER AGENT TASK: TDD Implementation**

## Context

Ticket: $ARGUMENTS
Project location: /home/jim/workspace/test-sdlc-project

PRD: [path to PRD]
Acceptance Criteria:
[paste acceptance criteria for this ticket from PRD]

Technical Notes:
[any relevant technical context from plan]

## Objective

Implement this ticket using Test-Driven Development (TDD).

## Your Implementation Tasks

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/TASK-{id}-{short-description}
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

### 3. Verify Quality

```bash
# All tests pass
npm test

# Linting passes
npm run lint

# No console.logs in production code
grep -r "console.log" src/ --include="*.ts" --include="*.js"
```

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
- Tests: PASS
- Lint: PASS

Commits: [N] commits on branch

Next: Ready for /pr TASK-XXX
```

## Critical Rules

1. **Tests FIRST** - Write failing tests before implementation
2. **Small commits** - Commit logical chunks, not everything at once
3. **No broken tests** - Never commit if tests are failing
4. **Match acceptance criteria** - Every criterion should have a test

---

## After Agent Returns

1. **Verify** branch exists with commits
2. **Verify** tests pass
3. **Verify** acceptance criteria are covered
4. **Summarize** implementation for user
5. **Next step:** User can run `/pr TASK-XXX`

## Ticket to Implement

$ARGUMENTS
