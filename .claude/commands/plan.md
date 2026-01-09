# Planning Phase

You are entering the Planning phase. This follows an approved Discovery document.

## Prerequisites

Before starting this phase, verify:
- [ ] Discovery document exists and is APPROVED
- [ ] User has explicitly approved moving to planning

If no discovery document exists, ask the user if they want to:
1. Create a discovery document first (`/discover`)
2. Skip discovery for this small task (document the skip in the plan)

## Purpose

Create a detailed implementation plan with clear steps, technical approach, and acceptance criteria.

## Your Task

Create a plan document at: `docs/plans/YYYY-MM-DD-{feature}.md`

Use today's date and a kebab-case feature name.

## Plan Document Structure

```markdown
# Implementation Plan: {Feature}

**Date:** YYYY-MM-DD
**Status:** DRAFT | APPROVED
**Discovery:** [Link to discovery doc if applicable]

## Summary

One paragraph describing what we're building and why.

## Goals

- Primary goal
- Secondary goals

## Non-Goals

What this plan explicitly does NOT cover.

## Technical Approach

### Architecture

High-level approach and key decisions.

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| ... | ... | ... |

### Key Decisions

1. **Decision:** Why we chose this approach
2. **Decision:** Why we chose this approach

## Implementation Steps

### Phase 1: {Name}

1. Step with clear deliverable
2. Step with clear deliverable

### Phase 2: {Name}

1. Step with clear deliverable
2. Step with clear deliverable

## Test Strategy

### Unit Tests

- What will be unit tested

### Integration Tests

- What will be integration tested

### Manual Testing

- What requires manual verification

## Tickets

These will be created in Asana after plan approval:

1. **{Ticket Title}** - Description (estimate: S/M/L)
2. **{Ticket Title}** - Description (estimate: S/M/L)
3. ...

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ... | ... | ... | ... |

## Open Questions

- [ ] Question needing resolution before implementation
- [ ] Another question

## Dependencies

- External dependencies
- Internal dependencies
- Blocking items
```

## Exit Criteria

- [ ] Plan document created at correct path
- [ ] Technical approach is clear and justified
- [ ] Implementation steps are actionable
- [ ] Test strategy defined
- [ ] Tickets outlined for PRD phase
- [ ] User has reviewed and set status = APPROVED

## Important

Do NOT proceed to PRD or implementation until the user explicitly approves this plan.

---

**Feature for this plan:** $ARGUMENTS
