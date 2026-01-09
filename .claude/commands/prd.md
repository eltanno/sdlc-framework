# PRD Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `architect` agent.**

## Prerequisites Check

Before delegating, verify:
1. Plan document exists and is APPROVED

```bash
# Check for approved plan
grep -l "Status: APPROVED" docs/plans/*.md 2>/dev/null
```

If no approved plan exists:
- "No approved plan found. Please run `/plan` first and get it approved."

## Delegation

```
Task({
  subagent_type: "architect",
  model: "sonnet",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the architect agent:

---

**ARCHITECT AGENT TASK: PRD Creation**

## Context

Feature: $ARGUMENTS
Project location: /home/jim/workspace/test-sdlc-project
Template location: docs/templates/prd-template.md

Plan document: [include path to approved plan]

## Objective

Create a formal Product Requirements Document with testable acceptance criteria that will drive ticket creation and validation.

## Your PRD Tasks

1. **Review Plan**
   - Read the approved plan document
   - Understand technical approach and phases
   - Note the proposed tickets

2. **Define Requirements**
   - Convert plan items to formal requirements (FR-1, FR-2, etc.)
   - Write acceptance criteria in Given/When/Then format
   - Define non-functional requirements (performance, security)

3. **Create User Stories**
   - Write user stories for key functionality
   - Each story needs acceptance criteria

4. **Specify Technical Details**
   - API changes (if any)
   - Data model changes (if any)
   - Dependencies

5. **Define Tickets**
   - Create ticket table from plan
   - Each ticket needs: title, description, priority, estimate
   - Leave ID column as "TBD" (filled after Asana creation)

6. **Plan Rollout**
   - Deployment strategy
   - Rollback plan

## Deliverable

Create a PRD at: `docs/prds/{todays-date}-{feature-kebab-case}.md`

Use the template at `docs/templates/prd-template.md` as your structure.

**Required sections:**
- Executive Summary (problem, solution, success metrics)
- Functional Requirements with acceptance criteria
- Non-Functional Requirements
- User Stories
- Technical Specifications
- Tickets table (ID = TBD)
- Testing Requirements
- Rollout/Rollback Plan

Set status to DRAFT (user will approve).

## Critical: Acceptance Criteria Format

Every requirement MUST have testable acceptance criteria:

```
- [ ] Given [context], when [action], then [expected result]
```

These will be used for validation in `/validate` phase.

## Output Format

After creating the document, return:

```
PRD COMPLETE

Document: docs/prds/YYYY-MM-DD-feature.md
Status: DRAFT (awaiting approval)

Summary: [2-3 sentence summary]

Requirements: [N] functional, [N] non-functional
User Stories: [N] stories

Tickets Ready for Creation:
| # | Title | Priority | Estimate |
|---|-------|----------|----------|
| 1 | ... | P1 | M |

Acceptance Criteria: [N] testable criteria defined

Next: User should review and approve, then run /ticket
```

---

## After Agent Returns

1. **Verify** the PRD was created with all required sections
2. **Verify** acceptance criteria are testable (Given/When/Then)
3. **Summarize** for user
4. **Prompt** user to review and approve
5. **Next step:** Once approved, user can run `/ticket`

## Feature for PRD

$ARGUMENTS
