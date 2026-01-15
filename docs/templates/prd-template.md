# PRD: {Feature Name}

**Date:** YYYY-MM-DD
**Status:** DRAFT
**Discovery:** [Link to iteration's discovery doc in docs/discovery/]
**Plan:** [Link to plan document when created]
**Owner:** {name}
**Stakeholders:** {names}

---

## Discovery Reference

**Note:** This PRD is for ONE feature/epic within this iteration. The discovery document contains the iteration's scope and vision.

**Iteration Vision:**
_[1-2 sentences from the discovery doc describing this iteration's goal]_

**How This Feature Fits:**
_[2-3 sentences explaining how this specific feature supports the iteration scope from the discovery document]_

---

## Executive Summary

### Problem Statement

*Clear, concise description of the problem we're solving.*

### Solution Summary

*One paragraph describing the solution at a high level.*

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Metric 1 | X | Y | Method |
| Metric 2 | X | Y | Method |

---

## Requirements

### Functional Requirements

#### FR-1: {Requirement Name}

**Priority:** P1 (Must Have) / P2 (Should Have) / P3 (Nice to Have)

**Description:** *What the system must do.*

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected result]
- [ ] Given [context], when [action], then [expected result]

#### FR-2: {Requirement Name}

**Priority:** P1

**Description:** *What the system must do.*

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected result]

#### FR-3: {Requirement Name}

**Priority:** P2

**Description:** *What the system must do.*

**Acceptance Criteria:**
- [ ] Given [context], when [action], then [expected result]

### Non-Functional Requirements

#### NFR-1: Performance

- Response time: < X ms for Y operation
- Throughput: X requests per second

#### NFR-2: Reliability

- Uptime: X%
- Error rate: < X%

#### NFR-3: Security

- Authentication requirements
- Authorization requirements
- Data protection requirements

#### NFR-4: Scalability

- Expected load
- Growth projections

---

## User Stories

### US-1: {User Story Title}

**Story:** As a {role}, I want to {action} so that {benefit}.

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Notes:** *Additional context if needed.*

### US-2: {User Story Title}

**Story:** As a {role}, I want to {action} so that {benefit}.

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

---

## Technical Specifications

### API Changes

#### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/resource | Create resource |
| GET | /api/v1/resource/:id | Get resource |

#### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| /api/v1/existing | Description of change |

### Data Model Changes

#### New Models

```
Model: {Name}
Fields:
  - field1: type (constraints)
  - field2: type (constraints)
```

#### Modified Models

| Model | Change |
|-------|--------|
| ExistingModel | Added field X |

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| package-name | ^1.0.0 | Why needed |

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| TBD | Ticket 1 | Brief description | P1 | 3 | - |
| TBD | Ticket 2 | Brief description | P1 | 2 | Ticket 1 |
| TBD | Ticket 3 | Brief description | P2 | 4 | - |

*Note: IDs will be filled in after ticket creation via `/ticket`.*

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Model |
|-------|-------|-------|
| 1 | Trivial | Sonnet |
| 2 | Simple | Sonnet |
| 3 | Moderate | Opus |
| 4 | Complex | Opus |
| 5 | Very Hard | Opus |

---

## Testing Requirements

### Test Cases

| ID | Requirement | Description | Steps | Expected Result |
|----|-------------|-------------|-------|-----------------|
| TC-1 | FR-1 | Test description | 1. Step 1<br>2. Step 2 | Expected result |
| TC-2 | FR-2 | Test description | 1. Step 1<br>2. Step 2 | Expected result |

### Test Coverage Requirements

- Unit test coverage: > 80%
- Integration tests for all API endpoints
- E2E tests for critical user flows

---

## Rollout Plan

### Phase 1: Internal Testing

- Deploy to staging
- Internal team testing
- Bug fixes

### Phase 2: Beta

- Limited rollout to X% of users
- Monitor metrics
- Gather feedback

### Phase 3: General Availability

- Full rollout
- Documentation published
- Support team trained

---

## Rollback Plan

### Triggers

When to rollback:
- Error rate > X%
- Response time > X ms
- Critical bug discovered

### Process

1. Revert deployment
2. Restore previous database state (if applicable)
3. Notify stakeholders
4. Create incident ticket

---

## Open Questions

- [ ] Question 1
- [ ] Question 2

## Out of Scope

*Explicitly list what this PRD does NOT cover:*

- Item 1
- Item 2

---

## Approval

- [ ] **Product Approved by:** {name} on YYYY-MM-DD
- [ ] **Engineering Approved by:** {name} on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
