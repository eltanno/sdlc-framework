# Planning Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `architect` agent.**

**Agent definition**: See `.claude/agents/architect.md` for architect responsibilities.

## Template

Use the template at `docs/templates/plan-template.md` when creating plan documents at `docs/plans/YYYY-MM-DD-{feature}.md`.

**IMPORTANT**: Plan requires an APPROVED PRD. The PRD defines WHAT to build (requirements), the plan defines HOW to build it (technical approach).

## Prerequisites Check

Before delegating, verify:
1. PRD document exists and is APPROVED

```bash
# Check for approved PRD
grep -l "Status: APPROVED" docs/prds/*.md 2>/dev/null
```

If no approved PRD exists:
- "No approved PRD found. Please run `/prd` first and get it approved."

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

**ARCHITECT AGENT TASK: Implementation Planning**

## Context

Feature to plan: $ARGUMENTS
Project location: [current project directory]
Template location: docs/templates/plan-template.md

PRD document: [include path to approved PRD]

## Objective

Create a detailed implementation plan with clear phases, technical approach, and ticket breakdown.

## Your Planning Tasks

1. **Review Context**
   - Read approved PRD to understand requirements
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

Next: User should review and approve, then run /ticket
```

---

## After Agent Returns

1. **Verify** the plan document was created
2. **Summarize** approach for user
3. **Prompt** user to review and approve (change status to APPROVED)
4. **Next step:** Once approved, user can run `/ticket`

## Workflow State Update

At the **start** of this phase, update `workflow-state.json`:

```bash
jq '.phase = "plan"' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
```

At the **end** of this phase (after plan is created and verified), mark complete:

```bash
jq '.completed = (.completed + ["plan"] | unique)' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
```

## Feature for Planning

$ARGUMENTS
