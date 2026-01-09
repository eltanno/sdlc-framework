# Planning Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `architect` agent.**

## Prerequisites Check

Before delegating, verify:
1. Discovery document exists and is APPROVED, OR
2. User explicitly skips discovery for small tasks

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
  model: "sonnet",  // Use "opus" for complex architectural decisions
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the architect agent:

---

**ARCHITECT AGENT TASK: Implementation Planning**

## Context

Feature to plan: $ARGUMENTS
Project location: /home/jim/workspace/test-sdlc-project
Template location: docs/templates/plan-template.md

Discovery document (if exists): [include path or note if skipped]

## Objective

Create a detailed implementation plan with clear phases, technical approach, and ticket breakdown.

## Your Planning Tasks

1. **Review Context**
   - Read discovery document if it exists
   - Explore codebase to understand current architecture
   - Identify integration points

2. **Design Approach**
   - Define technical architecture
   - Make and document key decisions with rationale
   - Identify what's new vs modified

3. **Break Down Work**
   - Define implementation phases
   - Create ticket list with estimates (S/M/L)
   - Identify dependencies between tickets

4. **Plan Testing**
   - Unit test strategy
   - Integration test strategy
   - Manual testing requirements

5. **Assess Risks**
   - Technical risks
   - Mitigation strategies

## Deliverable

Create a plan document at: `docs/plans/{todays-date}-{feature-kebab-case}.md`

Use the template at `docs/templates/plan-template.md` as your structure.

**Required sections:**
- Summary
- Goals / Non-Goals
- Technical Approach
- Implementation Phases (with exit criteria)
- Ticket Breakdown (table with estimates)
- Test Strategy
- Risks and Mitigations

Set status to DRAFT (user will approve).

## Output Format

After creating the document, return:

```
PLAN COMPLETE

Document: docs/plans/YYYY-MM-DD-feature.md
Status: DRAFT (awaiting approval)

Summary: [2-3 sentence summary of approach]

Phases:
1. Phase 1 name - [brief description]
2. Phase 2 name - [brief description]

Tickets Proposed: [N] tickets
- [list ticket titles]

Key Decisions:
- Decision 1
- Decision 2

Next: User should review and approve, then run /prd
```

---

## After Agent Returns

1. **Verify** the plan document was created
2. **Summarize** approach for user
3. **Prompt** user to review and approve (change status to APPROVED)
4. **Next step:** Once approved, user can run `/prd`

## Feature for Planning

$ARGUMENTS
