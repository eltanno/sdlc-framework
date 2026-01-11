# Ralph PRD - Autonomous PRD Implementation

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Drive a PRD to completion autonomously using ralph-wiggum.**

## Purpose

This command generates a ralph-loop prompt that will autonomously implement all tickets in a PRD, handling the full workflow: check status → implement ticket → validate → commit → PR → repeat until done.

## Prerequisites

- Approved PRD with status = APPROVED
- Approved plan with ticket IDs populated
- Clean git working tree
- Feature branch created (or will create)

## Usage

```bash
/ralph-prd docs/prds/YYYY-MM-DD-feature.md
```

## The Ralph Loop Prompt

Generate and run:

```bash
/ralph-loop "
## Objective: Complete PRD Implementation

You are autonomously implementing a PRD. Work methodically through each ticket until all are complete.

## PRD Context
- PRD: $ARGUMENTS
- Read the PRD and corresponding plan to understand the full scope

## Your Workflow Loop

### Step 1: Check Status
Run the /whats-next analysis to determine:
- Current workflow position
- Next ticket to implement
- Any blockers or incomplete work

### Step 2: Implement Next Ticket
Delegate to the engineer agent:
- Provide ticket ID, requirements, and technical approach from plan
- Engineer implements using TDD (tests first)
- Engineer commits with structured message

### Step 3: Validate
After engineer completes:
- Run full test suite
- Run linting
- Check acceptance criteria from PRD
- If validation fails, delegate fix to engineer

### Step 4: Create PR (if not exists)
- Push branch to remote
- Create PR linking to ticket
- Include test results in PR description

### Step 5: Check for Completion
Run /whats-next again:
- If more tickets remain → return to Step 2
- If all tickets complete → output: PRD_COMPLETE

## Delegation Pattern

When delegating to engineer:
\`\`\`
Task({
  subagent_type: \"engineer\",
  prompt: \"
    ## Ticket: [ID] - [Title]

    ## Context
    - PRD: [path]
    - Plan: [path]

    ## Requirements
    [Copy from PRD/plan]

    ## Technical Approach
    [Copy from plan]

    ## Definition of Done
    - [ ] Tests written (TDD)
    - [ ] Implementation complete
    - [ ] All tests pass
    - [ ] Lint passes
    - [ ] Committed with message: [TICKET-ID] description
  \",
  model: \"sonnet\"
})
\`\`\`

## Safety Rules

1. Never skip TDD - tests before implementation
2. Never commit failing tests
3. Never push to main directly
4. If stuck for 5+ iterations on same ticket, output: NEEDS_HUMAN_REVIEW
5. If engineer fails 3 times on same issue, output: NEEDS_HUMAN_REVIEW

## Completion Criteria

Output PRD_COMPLETE when:
- All tickets in plan show status = complete
- All tests pass
- All PRs created (or merged)
- /whats-next shows no remaining work for this PRD

## Status Tracking

After each ticket:
1. Update workflow-state.json with ralph progress
2. Update docs/plans/PROGRESS.md with ticket status
3. Log what was completed
4. Note any deviations from plan

### Workflow State Updates

At the START of ralph-prd, update workflow-state.json:
\`\`\`bash
# Set phase to ralph, initialize tracking, and reset post-implementation phases (replace N with ticket count from plan)
# Remove report/review from completed since they need to be re-run after this implementation cycle
.claude/scripts/update-workflow-state.sh '.phase = \"ralph\" | .ralph.current = 0 | .ralph.total = N | .ralph.current_ticket = null | .ralph.tickets_done = [] | .completed = (.completed - [\"report\", \"review\", \"ralph\"])'
\`\`\`

After EACH ticket completes:
\`\`\`bash
# Update ralph progress (replace TICKET-ID with actual ID)
.claude/scripts/update-workflow-state.sh '.ralph.current = (.ralph.current + 1) | .ralph.current_ticket = null | .ralph.tickets_done += [\"TICKET-ID\"]'
\`\`\`

Before STARTING a ticket:
\`\`\`bash
# Set current ticket being worked on
.claude/scripts/update-workflow-state.sh '.ralph.current_ticket = \"TICKET-ID\"'
\`\`\`

At the END (PRD_COMPLETE):
\`\`\`bash
# Mark ralph complete
.claude/scripts/update-workflow-state.sh '.phase = \"idle\" | .completed = (.completed + [\"ralph\"] | unique)'
\`\`\`

" --completion-promise "PRD_COMPLETE" --max-iterations 100
```

## What Gets Created

During the loop, ralph will:
- Implement each ticket via engineer delegation
- Create commits for each piece of work
- Create PRs for completed work
- Update PROGRESS.md with status

## Monitoring Progress

While ralph runs:
```bash
# Watch commits
git log --oneline -20

# Check PROGRESS.md
cat docs/plans/PROGRESS.md

# See current branch
git status
```

## Stopping Early

If you need to stop ralph:
```bash
/cancel-ralph
```

Then review:
```bash
git diff
git log --oneline -10
```

## Recovery

If ralph exits with NEEDS_HUMAN_REVIEW:
1. Check the last ticket it was working on
2. Review the error or blocker
3. Fix manually or provide guidance
4. Restart with `/ralph-prd` to continue

## Example

```bash
# Start autonomous implementation of auth feature
/ralph-prd docs/prds/2026-01-10-user-auth.md

# Ralph will:
# 1. Read PRD and plan
# 2. Check /whats-next → finds ticket TASK-001
# 3. Delegate to engineer: "Implement TASK-001..."
# 4. Validate, commit, push
# 5. Check /whats-next → finds ticket TASK-002
# 6. ... repeat until PRD_COMPLETE
```

## Arguments

$ARGUMENTS

The argument should be the path to an approved PRD document.

## Important Notes

- This runs ralph at the session level (not inside an agent)
- Ralph delegates implementation to engineer agents
- Each ticket is a separate engineer delegation
- Ralph handles the orchestration and validation loop
- Expect this to run for extended periods for large PRDs
