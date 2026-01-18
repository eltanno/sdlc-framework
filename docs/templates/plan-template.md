# Implementation Plan: {Feature}

**Date:** YYYY-MM-DD
**Status:** DRAFT
**Discovery:** [Link to discovery doc if applicable]
**Author:** {name}

---

## Summary

*One paragraph describing what we're building and why.*

## Goals

### Primary Goals

- Goal 1
- Goal 2

### Secondary Goals

- Goal 1

## Non-Goals

*What this plan explicitly does NOT cover.*

- Non-goal 1
- Non-goal 2

## Technical Approach

### Architecture Overview

*High-level description of the approach.*

```
[Optional: ASCII diagram or description of components]
```

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| Component 1 | What it does | New |
| Component 2 | What it does | Modified |

### Key Technical Decisions

#### Decision 1: {What}

**Choice:** What we're doing

**Rationale:** Why we chose this

**Alternatives Considered:** What else we looked at

#### Decision 2: {What}

**Choice:** What we're doing

**Rationale:** Why we chose this

## Implementation Phases

### Phase 1: {Name} (Foundation)

**Goal:** What this phase achieves

**Steps:**
1. Step with clear deliverable
2. Step with clear deliverable
3. Step with clear deliverable

**Exit Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

### Phase 2: {Name} (Core Feature)

**Goal:** What this phase achieves

**Steps:**
1. Step with clear deliverable
2. Step with clear deliverable

**Exit Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

### Phase 3: {Name} (Polish)

**Goal:** What this phase achieves

**Steps:**
1. Step with clear deliverable
2. Step with clear deliverable

**Exit Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

## Test Strategy

### Unit Tests

- [ ] Test area 1
- [ ] Test area 2

### Integration Tests

- [ ] Test area 1
- [ ] Test area 2

### End-to-End Tests

- [ ] Critical user flow 1
- [ ] Critical user flow 2

### Manual Testing

- [ ] Scenario requiring manual verification

## Tickets

*These will be created after plan approval:*

| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | {Title} | Brief description | P1 | 1 | 1 | - |
| 2 | {Title} | Brief description | P1 | 2 | 1 | - |
| 3 | {Title} | Brief description | P2 | 3 | 2 | 1, 2 |
| 4 | {Title} | Brief description | P2 | 3 | 2 | 1, 2 |
| 5 | {Title} | Brief description | P3 | 4 | 3 | 3, 4 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, rename, add simple field | Sonnet |
| 2 | Simple | Basic function, simple validation, minor UI tweak | Sonnet |
| 3 | Moderate | New feature with tests, API endpoint, form with validation | Opus |
| 4 | Complex | Multi-component feature, significant refactor, integrations | Opus |
| 5 | Very Hard | Architectural change, complex algorithm, security-critical | Opus |

*Current threshold: 1-2 → Sonnet, 3-5 → Opus. Threshold adjustable based on performance metrics.*

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Risk 1 | High/Med/Low | High/Med/Low | Mitigation strategy |
| Risk 2 | High/Med/Low | High/Med/Low | Mitigation strategy |

## Environment Considerations

*Relevant for test infrastructure, CI/CD, or platform-specific features.*

### Local Development

- **Primary OS:** [Windows WSL2 / macOS / Linux]
- **Known Limitations:** [Any environment-specific issues to be aware of]

### CI Environment

- **Platform:** [GitHub Actions / GitLab CI / etc.]
- **Considerations:** [Browser support, resource limits, etc.]

## Dependencies

### External Dependencies

- Dependency 1
- Dependency 2

### Internal Dependencies

- Dependency 1

### Blocking Items

- [ ] Item that must be resolved before starting

## Open Questions

*Questions that need answers (ideally before implementation):*

- [ ] Question 1
- [ ] Question 2

## Success Criteria

*How do we know we're done?*

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All tests pass
- [ ] Documentation updated

---

## Pre-Implementation Checklist

**CRITICAL: Before delegating ANY implementation work, verify:**

- [ ] Discovery committed: `git log --oneline docs/discovery/`
- [ ] PRD committed: `git log --oneline docs/prds/`
- [ ] This plan committed: `git log --oneline docs/plans/`
- [ ] `git status docs/` shows "nothing to commit"

> **Why this matters:** Untracked files can be lost during branch operations. Documents ARE the state - if they're not committed, implementation has no foundation. See WORKFLOW.md "Artifact Commit Rule" for details.

---

## Post-Implementation Checklist

**After all tickets are complete:**

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code committed and pushed
- [ ] PR created and merged (or local merge for local repos)
- [ ] Create execution report: `/execution-report`
- [ ] Create system review: `/system-review`

---

## Approval

- [ ] **Approved by:** {name} on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted.*
