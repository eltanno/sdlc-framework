# PRD Phase

You are entering the PRD (Product Requirements Document) phase.

## Prerequisites

Before starting this phase, verify:
- [ ] Plan document exists and is APPROVED

If no approved plan exists, direct the user to `/plan` first.

## Purpose

Create a formal PRD with testable acceptance criteria that will drive ticket creation and validation.

## Your Task

Create a PRD at: `docs/prds/YYYY-MM-DD-{feature}.md`

Use today's date and a kebab-case feature name.

## PRD Document Structure

```markdown
# PRD: {Feature Name}

**Date:** YYYY-MM-DD
**Status:** DRAFT | APPROVED
**Plan:** [Link to plan document]
**Owner:** {name}

## Overview

### Problem Statement

Clear description of the problem we're solving.

### Solution Summary

One paragraph describing the solution.

### Success Metrics

How will we know this is successful?

- Metric 1
- Metric 2

## Requirements

### Functional Requirements

#### FR-1: {Requirement Name}

**Description:** What the system must do.

**Acceptance Criteria:**
- [ ] Given X, when Y, then Z
- [ ] Given A, when B, then C

#### FR-2: {Requirement Name}

**Description:** What the system must do.

**Acceptance Criteria:**
- [ ] Given X, when Y, then Z

### Non-Functional Requirements

#### NFR-1: Performance

- Requirement with measurable threshold

#### NFR-2: Security

- Security requirements

## User Stories

### US-1: {As a user...}

**Story:** As a {role}, I want to {action} so that {benefit}.

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

## Technical Specifications

### API Changes

Describe any API changes.

### Data Model Changes

Describe any data model changes.

### Dependencies

External dependencies required.

## Tickets

| ID | Title | Description | Priority | Estimate |
|----|-------|-------------|----------|----------|
| TBD | Ticket 1 | Description | P1 | M |
| TBD | Ticket 2 | Description | P2 | S |

*Note: IDs will be filled in after Asana ticket creation.*

## Testing Requirements

### Test Cases

| ID | Description | Steps | Expected Result |
|----|-------------|-------|-----------------|
| TC-1 | ... | ... | ... |
| TC-2 | ... | ... | ... |

## Rollout Plan

How will this be deployed/released?

## Rollback Plan

How do we rollback if something goes wrong?
```

## Exit Criteria

- [ ] PRD created at correct path
- [ ] All functional requirements have acceptance criteria
- [ ] Acceptance criteria are testable (Given/When/Then format preferred)
- [ ] Ticket placeholders ready for Asana creation
- [ ] User has reviewed and set status = APPROVED

## Important

Do NOT create Asana tickets until the PRD is approved.

---

**Feature for this PRD:** $ARGUMENTS
