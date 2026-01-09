# Implementation Phase

You are entering the Implementation phase.

## Prerequisites

Before starting this phase, verify:
- [ ] PRD exists with Asana ticket IDs
- [ ] You have a specific ticket ID to implement

If no ticket ID is provided, ask the user which ticket to implement.

## Purpose

TDD implementation of the feature following gitflow conventions.

## Your Task

1. Create feature branch
2. Write failing tests first
3. Implement until tests pass
4. Commit with proper message format

## Implementation Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/TASK-{id}-{short-description}
```

Branch naming:
- `feature/TASK-123-add-user-auth`
- `bugfix/TASK-456-fix-login-error`
- `hotfix/TASK-789-critical-security-fix`

### 2. TDD Cycle

#### Red Phase
Write failing tests that define the expected behavior:
- Unit tests for business logic
- Integration tests for API endpoints
- Test edge cases and error conditions

```bash
# Run tests - they should FAIL
npm test  # or your test command
```

#### Green Phase
Write the minimum code to make tests pass:
- Focus on making tests pass, not perfection
- Don't over-engineer

```bash
# Run tests - they should PASS
npm test
```

#### Refactor Phase
Clean up the code while keeping tests green:
- Remove duplication
- Improve naming
- Simplify logic

### 3. Commit Changes

Use the proper commit message format:

```
[TASK-XXX] Brief description (50 chars max)

- Detail about what changed
- Another detail if needed

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 4. Verify Before Pushing

- [ ] All tests pass
- [ ] Linting passes
- [ ] No console.log/print statements in production code
- [ ] No commented-out code
- [ ] Code follows existing patterns

## Exit Criteria

- [ ] Feature branch created with correct naming
- [ ] Tests written BEFORE implementation
- [ ] All tests pass
- [ ] Code committed with proper message format
- [ ] Ready for PR creation

## Commands

```bash
# Check test status
npm test

# Check lint status
npm run lint

# View changes
git status
git diff
```

## Important

- Write tests FIRST (TDD)
- Small, focused commits
- Don't commit broken tests
- Ask for help if stuck

---

**Ticket to implement:** $ARGUMENTS
