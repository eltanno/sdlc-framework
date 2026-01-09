# PRD Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `architect` agent.**

**Agent definition**: See `.claude/agents/architect.md` for architect responsibilities.

## Template

Use the template at `docs/templates/prd-template.md` when creating PRD documents at `docs/prds/YYYY-MM-DD-{feature}.md`.

**IMPORTANT HIERARCHY CONCEPTS:**

1. **PRD Scope**: PRDs are **per-feature/epic**, NOT whole-application documents
2. **Discovery Reference**: Each PRD should reference `docs/discovery.md` (the whole app vision)
3. **Multiple PRDs Expected**: Real applications will have multiple PRDs, one for each major feature
4. **PRD comes BEFORE plan**: The PRD defines WHAT to build, the plan defines HOW to build it

### PRD Granularity Guidance

**Good PRD scope (one feature/epic):**
- "User Authentication System"
- "Offline Sync Engine"
- "Command Line Interface"
- "Real-time Collaboration"

**Too broad (multiple PRDs needed):**
- "Complete Application" → Split into feature-specific PRDs
- "Full Platform" → Split by major feature areas

**Too narrow (should be tickets, not PRDs):**
- "Add login button" → This is a ticket within an auth PRD
- "Fix password validation" → This is a bug fix ticket

## Prerequisites Check

Before delegating, verify:
1. Discovery document exists and is APPROVED (or user explicitly skips discovery)

```bash
# Check for approved discovery
grep -l "Status: APPROVED" docs/discovery/*.md 2>/dev/null
```

If no approved discovery exists, ask user:
- "No approved discovery found. Should I run `/discover` first, or skip discovery for this task?"

## Delegation

```
Task({
  subagent_type: "architect",
  model: "opus",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the architect agent:

---

**ARCHITECT AGENT TASK: PRD Creation**

## Context

Feature: $ARGUMENTS
Project location: [current project directory]
Template location: docs/templates/prd-template.md

Discovery document: docs/discovery.md [include path or note if skipped]

**CRITICAL: PRD Scope**
- This PRD is for ONE feature/epic, NOT the whole application
- The discovery document contains the holistic application vision
- This PRD should focus on the specific feature: $ARGUMENTS
- Reference the discovery document to show how this feature fits into the bigger picture

## Objective

Create a formal Product Requirements Document with testable acceptance criteria for a SINGLE FEATURE that will drive ticket creation and validation.

## Your PRD Tasks

1. **Review Discovery**
   - Read the discovery document if it exists
   - Understand user needs and business context
   - Identify key features and requirements

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
- **Discovery Reference** - Link to docs/discovery.md and explain how this feature fits the bigger picture
- Executive Summary (problem, solution, success metrics)
- Functional Requirements with acceptance criteria
- Non-Functional Requirements
- User Stories
- Technical Specifications
- Tickets table (ID = TBD)
- Testing Requirements
- Rollout/Rollback Plan

Set status to DRAFT (user will approve).

**Remember:** This PRD is for ONE feature, not the whole application. Keep scope focused.

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

Next: User should review and approve, then run /plan
```

---

## After Agent Returns

1. **Verify** the PRD was created with all required sections
2. **Verify** acceptance criteria are testable (Given/When/Then)
3. **Summarize** for user
4. **Prompt** user to review and approve
5. **Next step:** Once approved, user can run `/plan`

## Feature for PRD

$ARGUMENTS
