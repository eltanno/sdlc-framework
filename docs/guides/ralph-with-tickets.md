# Using Ralph with Tickets

A guide for autonomous ticket implementation using ralph-wiggum.

## Overview

Ralph creates a self-referential loop where Claude iterates on work until completion. Combined with your detailed plans and tickets, this enables autonomous implementation of well-defined tasks.

```
Your Workflow:
/discover → /prd → /plan → /ticket → [ralph implements each ticket] → /pr → /validate
```

## When to Use Ralph

| Good For | Not Good For |
|----------|--------------|
| Tickets with clear acceptance criteria | Vague requirements |
| Implementation work with testable outcomes | Design decisions |
| Tasks where "done" is measurable (tests pass) | Exploratory work |
| Greenfield features from detailed plans | Production debugging |
| Refactoring with existing test coverage | Tasks needing human judgment |

## The Basic Pattern

```bash
/ralph-loop "<prompt>" --completion-promise "<marker>" --max-iterations <n>
```

**Always include:**
- `--max-iterations` - Safety limit (start with 20-30)
- `--completion-promise` - Exact string that signals completion

## Prompt Structure for Tickets

Use this template when running ralph on a ticket:

```markdown
/ralph-loop "
## Ticket: [TICKET-ID] - [Title]

## Context
- Plan: docs/plans/YYYY-MM-DD-feature.md
- PRD: docs/prds/YYYY-MM-DD-feature.md

## Requirements
[Copy acceptance criteria from plan/PRD]

1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

## Technical Approach
[Copy relevant section from plan]

## Definition of Done
- [ ] All requirements implemented
- [ ] Tests written and passing
- [ ] Lint passes
- [ ] No debug code or console.logs

## Instructions
1. Read the plan and PRD for full context
2. Implement the requirements
3. Write tests first (TDD)
4. Run tests after each change
5. When all tests pass and lint is clean, output: TASK_COMPLETE

" --completion-promise "TASK_COMPLETE" --max-iterations 30
```

## Real Examples

### Example 1: API Endpoint

```bash
/ralph-loop "
## Ticket: TASK-042 - Add user authentication endpoint

## Context
- Plan: docs/plans/2026-01-10-auth.md
- PRD: docs/prds/2026-01-10-auth.md

## Requirements
1. POST /api/auth/login endpoint
2. Accept email and password in request body
3. Return JWT token on success
4. Return 401 with error message on failure
5. Rate limit: 5 attempts per minute per IP

## Technical Approach
- Use existing Express router pattern in src/routes/
- JWT signing with existing config in src/config/auth.ts
- Rate limiting via express-rate-limit middleware

## Definition of Done
- [ ] Endpoint implemented
- [ ] Input validation (email format, password min length)
- [ ] Unit tests for success and failure cases
- [ ] Integration test for rate limiting
- [ ] Tests passing, lint clean

Run: npm test && npm run lint
When complete, output: TASK_COMPLETE

" --completion-promise "TASK_COMPLETE" --max-iterations 30
```

### Example 2: UI Component

```bash
/ralph-loop "
## Ticket: TASK-043 - Create login form component

## Context
- Plan: docs/plans/2026-01-10-auth.md
- PRD: docs/prds/2026-01-10-auth.md

## Requirements
1. Email input with validation
2. Password input with show/hide toggle
3. Submit button with loading state
4. Error message display
5. Redirect to /dashboard on success

## Technical Approach
- React component in src/components/auth/
- Use existing form patterns from src/components/forms/
- Tailwind for styling, match existing design system

## Definition of Done
- [ ] Component renders correctly
- [ ] Form validation works
- [ ] Loading state displays
- [ ] Error handling works
- [ ] Tests passing

Run: npm test -- --grep LoginForm && npm run lint
When complete, output: TASK_COMPLETE

" --completion-promise "TASK_COMPLETE" --max-iterations 25
```

### Example 3: Refactoring

```bash
/ralph-loop "
## Ticket: TASK-044 - Refactor user service to use repository pattern

## Context
- Plan: docs/plans/2026-01-10-refactor.md

## Requirements
1. Extract database queries from UserService to UserRepository
2. UserService depends on repository interface, not implementation
3. All existing tests still pass
4. No behavior changes

## Files to Modify
- src/services/UserService.ts → uses repository
- src/repositories/UserRepository.ts → new file
- src/repositories/IUserRepository.ts → interface

## Definition of Done
- [ ] Repository pattern implemented
- [ ] UserService refactored
- [ ] All 47 existing user tests pass
- [ ] No new functionality added

Run: npm test -- --grep User && npm run lint
When complete, output: TASK_COMPLETE

" --completion-promise "TASK_COMPLETE" --max-iterations 40
```

## Best Practices

### 1. Copy Context from Plan

Don't make ralph search for requirements. Copy the relevant sections directly:

```markdown
## Requirements
[Paste from plan's ticket breakdown]

## Technical Approach
[Paste from plan's architecture section]
```

### 2. Make "Done" Measurable

**Good:**
```
When all tests pass and lint is clean, output: TASK_COMPLETE
```

**Bad:**
```
When it looks good, you're done.
```

### 3. Include Verification Commands

Tell ralph exactly how to check its work:

```markdown
## Verify
Run these commands - all must pass:
- npm test -- --grep "AuthService"
- npm run lint
- npm run build
```

### 4. Start with Lower Iterations

Start with 20-30 iterations. Increase if needed:

| Task Complexity | Suggested Max |
|-----------------|---------------|
| Simple (1 file) | 15-20 |
| Medium (2-4 files) | 25-35 |
| Complex (5+ files) | 40-50 |

### 5. One Ticket = One Ralph Loop

Don't combine tickets. Run ralph once per ticket:

```bash
# Good - one ticket at a time
/ralph-loop "Ticket TASK-042..." --max-iterations 30
# Wait for completion
/ralph-loop "Ticket TASK-043..." --max-iterations 30

# Bad - multiple tickets
/ralph-loop "Do TASK-042 and TASK-043 and TASK-044..."
```

### 6. Use Git for Safety

Always run in a git-tracked directory:

```bash
# Before ralph
git checkout -b feature/TASK-042-auth-endpoint
git status  # clean working tree

# After ralph (if something went wrong)
git diff    # see what changed
git reset --hard HEAD  # nuclear option
```

## Handling Failures

### Ralph Gets Stuck

If ralph keeps iterating without progress:

1. Run `/cancel-ralph`
2. Check what was accomplished: `git diff`
3. Identify the blocker
4. Either fix manually or refine the prompt

### Tests Won't Pass

Add explicit debugging instructions:

```markdown
If tests fail after 10 iterations:
1. Read the test failure output carefully
2. Check if the test expectations match requirements
3. If test is wrong, fix the test
4. If implementation is wrong, fix the implementation
5. Output current status for human review: NEEDS_REVIEW
```

### Wrong Approach Taken

Ralph can read its own git history. Add course-correction:

```markdown
After each iteration, check:
- Am I following the technical approach from the plan?
- Am I using existing patterns from the codebase?
- If I've gone off-track, reset and try again
```

## Workflow Integration

### Before Ralph

1. Ensure plan is approved (`docs/plans/` status = APPROVED)
2. Ensure tickets have clear acceptance criteria
3. Create feature branch
4. Run `/prime` to load context

### Running Ralph

```bash
# One ticket at a time
/ralph-loop "[ticket prompt]" --completion-promise "TASK_COMPLETE" --max-iterations 30
```

### After Ralph

1. Review changes: `git diff`
2. Run full test suite: `npm test`
3. Create execution report: `/execution-report`
4. Create PR: `/pr`
5. Validate: `/validate`

## Completion Promise Patterns

| Pattern | Use Case |
|---------|----------|
| `TASK_COMPLETE` | Standard ticket completion |
| `ALL_TESTS_PASS` | Test-focused tasks |
| `REFACTOR_DONE` | Refactoring tasks |
| `READY_FOR_REVIEW` | When human check needed |

The promise must appear exactly in Claude's output. Keep it simple and unique.

## Safety Checklist

Before running ralph on any ticket:

- [ ] Working in a git branch (not main)
- [ ] Clean working tree (`git status`)
- [ ] `--max-iterations` is set
- [ ] Completion promise is clear and unique
- [ ] Requirements are copied from plan (not vague)
- [ ] Verification commands are included
- [ ] You can walk away and check later

## Quick Reference

```bash
# Standard ticket implementation
/ralph-loop "
## Ticket: [ID] - [Title]
## Context: [plan/PRD paths]
## Requirements: [paste from plan]
## Definition of Done: [checklist]
## Verify: [test commands]
When complete: TASK_COMPLETE
" --completion-promise "TASK_COMPLETE" --max-iterations 30

# Cancel if needed
/cancel-ralph

# Check progress
git log --oneline -10
git diff --stat
```
