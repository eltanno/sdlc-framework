# PRD: Ralph PM Tool Integration Fix

**Date:** 2026-01-20
**Status:** APPROVED
**Discovery:** [Ralph Python Port Discovery](../discovery/2026-01-19-ralph-python-port.md)
**Plan:** [Ralph PM Tool Integration Plan](../plans/2026-01-20-ralph-pm-tool-integration.md)
**Owner:** TBD
**Stakeholders:** TBD

---

## Discovery Reference

**Note:** This PRD addresses a critical regression introduced during the Ralph Python port.

**Iteration Vision:**
The Ralph Python port aimed to maintain identical functionality while gaining testability and maintainability. The goal was feature parity with the legacy bash scripts.

**How This Feature Fits:**
During the Python port, a critical architectural error was introduced: the new Python implementation uses local `workflow-state.json` as the source of truth for ticket status, when the legacy design correctly used the configured PM tool (GitHub Issues) as the source of truth. This PRD addresses restoring the correct architecture.

---

## Executive Summary

### Problem Statement

The Ralph orchestrator Python port introduced a fundamental architectural regression:

| Aspect | Legacy (Correct) | Current (Broken) |
|--------|------------------|------------------|
| **Ticket Status Source** | PM tool (GitHub Issues) | Local `workflow-state.json` |
| **PM Tool Config** | Reads and uses `pm.tool` from `config.yaml` | Completely ignored |
| **Concurrency Control** | Label-based (`ralph-*` labels) for parallel instances | None - race conditions possible |
| **Dependency Checks** | Queries PM tool to check if dependencies are closed | Checks local state only |
| **State Reset** | Resets when PRD tickets don't match | No reset mechanism |

This breaks several critical workflows:
1. **Parallel execution** - Multiple Ralph instances will overwrite each other's state
2. **Resume capability** - Restarting Ralph loses PM tool state
3. **Dependency tracking** - Dependencies may appear satisfied locally but not in PM tool
4. **Multi-worktree** - Different worktrees have different local state files

### Solution Summary

Restore the legacy architecture where the PM tool (GitHub Issues) is the source of truth for ticket status, while local `workflow-state.json` stores only supplemental data (dependencies, attempt counts, ticket scope). Implement label-based concurrency control for safe parallel execution.

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| PM tool status queries | 0 | 100% of status checks | Code review |
| Parallel instance safety | Not supported | Full support | Integration tests |
| Config.yaml pm.tool usage | Ignored | Fully respected | Code review |
| State reset on mismatch | Not supported | Automatic | Integration tests |

---

## Requirements

### Functional Requirements

#### FR-1: PM Tool Configuration Loading

**Priority:** P1 (Must Have)

**Description:** Ralph must read and respect the `pm.tool` setting from `config.yaml`. Currently this setting is completely ignored.

**Acceptance Criteria:**
- [ ] Given `config.yaml` has `pm.tool: github`, when Ralph initializes, then it configures GitHub Issues as the ticket status source
- [ ] Given `config.yaml` has `pm.tool: none`, when Ralph initializes, then it falls back to local state only (degraded mode)
- [ ] Given `config.yaml` is missing or `pm.tool` is not set, then Ralph fails with a clear error message

#### FR-2: GitHub Issues as Status Source

**Priority:** P1 (Must Have)

**Description:** When `pm.tool: github`, Ralph must query GitHub Issues for ticket status instead of reading from local state. The legacy `get-next-ticket.sh` correctly implements this pattern.

**Acceptance Criteria:**
- [ ] Given a ticket exists in GitHub Issues as open, when `get_next_ticket()` runs, then it reports the ticket as pending/available
- [ ] Given a ticket is closed in GitHub Issues, when checking dependencies, then it's considered completed
- [ ] Given a ticket has the `blocked` label in GitHub Issues, when `get_next_ticket()` runs, then it skips the ticket
- [ ] Given GitHub API calls fail, when getting next ticket, then Ralph reports a clear error (not silent failure)

#### FR-3: Label-Based Concurrency Control

**Priority:** P1 (Must Have)

**Description:** Ralph must use label-based concurrency control to allow multiple instances to run safely in parallel. Each instance claims tickets by adding its unique label (`ralph-1`, `ralph-2`, etc.).

**Acceptance Criteria:**
- [ ] Given `RALPH_LABEL=ralph-1` in environment, when Ralph claims a ticket, then it adds the `ralph-1` label to the GitHub Issue
- [ ] Given an issue already has a `ralph-*` label from another instance, when this instance queries for next ticket, then it skips that issue
- [ ] Given two instances race to claim the same ticket, when both try to add labels, then only one succeeds and the other retries with next ticket
- [ ] Given a ticket is in-progress with this instance's label, when Ralph restarts, then it resumes that ticket first
- [ ] Given `ralph.use_assignee: true` in config, when claiming a ticket, then also assign to current user
- [ ] Given `ralph.use_assignee: false` in config, when claiming a ticket, then only use labels (not assignee)

#### FR-4: Local State for Supplemental Data Only

**Priority:** P1 (Must Have)

**Description:** Local `workflow-state.json` should store only supplemental data that isn't tracked in the PM tool: dependencies (parsed from plan), attempt counts, ticket scope (from PRD), and blocked reasons.

**Acceptance Criteria:**
- [ ] Given setup runs with a PRD, when state is initialized, then ticket IDs from PRD are stored in `ralph.tickets[]`
- [ ] Given dependencies are parsed from plan, when state is saved, then they're stored in `ralph.dependencies{}`
- [ ] Given a ticket fails validation, when attempt count increments, then it's stored in local state (not PM tool)
- [ ] Given ticket status is needed, when code queries status, then it queries PM tool (not local state `status` field)

#### FR-5: Dependency Checking Against PM Tool

**Priority:** P1 (Must Have)

**Description:** When checking if a ticket's dependencies are satisfied, Ralph must query the PM tool to see if dependency tickets are closed/completed.

**Acceptance Criteria:**
- [ ] Given ticket A depends on ticket B, when B is open in GitHub Issues, then A is not eligible for work
- [ ] Given ticket A depends on ticket B, when B is closed in GitHub Issues, then A is eligible for work
- [ ] Given a dependency ticket doesn't exist in GitHub, when checking dependencies, then log warning but treat as unmet
- [ ] Given multiple dependencies, when any is not closed, then ticket is not eligible

#### FR-6: State Reset on Ticket Mismatch

**Priority:** P2 (Should Have)

**Description:** When the tickets in the PRD don't match the tickets in local state (e.g., PRD was updated), Ralph should detect this and offer to reset state.

**Acceptance Criteria:**
- [ ] Given PRD has tickets [A, B, C] and local state has tickets [A, B, D], when setup runs, then detect mismatch
- [ ] Given a mismatch is detected, when running non-interactively, then warn and continue with PRD as source of truth
- [ ] Given a mismatch is detected, when running interactively, then prompt user to confirm reset
- [ ] Given reset is confirmed, then recreate local state from PRD (preserve attempt counts for matching tickets)

### Non-Functional Requirements

#### NFR-1: Performance

- GitHub API queries should be batched where possible (list issues once, not per-ticket)
- Cache issue list for duration of a single `get_next_ticket()` call
- Target: <2 seconds for `get_next_ticket()` with up to 100 tickets

#### NFR-2: Reliability

- Handle GitHub API rate limiting gracefully (retry with backoff)
- Handle network failures with clear error messages
- No data loss on process interruption (atomic state writes already implemented)

#### NFR-3: Backward Compatibility

- `workflow-state.json` schema changes must be additive (don't break existing files)
- CLI interface (`ralph run <prd> <plan>`) remains unchanged
- Legacy shell scripts in `ralph-legacy/` remain functional for comparison testing

---

## User Stories

### US-1: Developer Running Multiple Ralph Instances

**Story:** As a developer with multiple worktrees, I want to run Ralph in parallel so that I can work on multiple ticket streams simultaneously.

**Acceptance Criteria:**
- [ ] Each Ralph instance claims tickets with its unique label
- [ ] No two instances work on the same ticket
- [ ] Each instance can resume its own in-progress work
- [ ] State files don't conflict across worktrees

**Notes:** This is a primary use case for label-based concurrency. The legacy scripts supported this via `RALPH_LABEL` environment variable.

### US-2: Developer Resuming After Restart

**Story:** As a developer, I want Ralph to resume my in-progress ticket when I restart so that I don't lose work.

**Acceptance Criteria:**
- [ ] Ralph checks for issues with this instance's label first
- [ ] In-progress ticket is resumed before picking new work
- [ ] Attempt count is preserved from local state

### US-3: Developer Updating PRD Mid-Workflow

**Story:** As a developer, I want to update my PRD with new tickets so that Ralph picks them up without manual state editing.

**Acceptance Criteria:**
- [ ] Ralph detects when PRD tickets differ from local state
- [ ] New tickets from PRD are added to scope
- [ ] Removed tickets are flagged but not errored

---

## Technical Specifications

### API Changes

No API changes - this is internal refactoring.

### Data Model Changes

#### Modified: workflow-state.json

Current schema stores ticket status locally (broken):

```json
{
  "version": "1.0",
  "prd_path": "...",
  "plan_path": "...",
  "tickets": [
    {"id": "SDLC-001", "title": "...", "status": "pending", "dependencies": [], "attempts": 0}
  ]
}
```

Corrected schema (status comes from PM tool, not stored locally):

```json
{
  "version": "2.0",
  "prd_path": "...",
  "plan_path": "...",
  "ralph": {
    "tickets": ["SDLC-001", "SDLC-002"],
    "dependencies": {
      "SDLC-002": ["SDLC-001"]
    },
    "attempts": {
      "SDLC-001": 1,
      "SDLC-002": 0
    },
    "blocked": {
      "SDLC-003": "Test failures - needs manual fix"
    },
    "source": "github"
  }
}
```

**Key Changes:**
- Remove `status` from tickets (queried from PM tool)
- Move to `ralph.*` namespace (matches legacy)
- Store only IDs, not full ticket objects
- Separate maps for attempts and blocked reasons

### Dependencies

No new dependencies required. Uses existing:
- `gh` CLI for GitHub API calls
- `pyyaml` for config loading
- Standard library for everything else

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| [SDLC-0038](https://github.com/eltanno/sdlc-framework/issues/74) | Create PM tool abstraction layer | Create `core/pm.py` with `PMTool` protocol and `GitHubPM` implementation | P1 | 3 | - |
| [SDLC-0039](https://github.com/eltanno/sdlc-framework/issues/75) | Add PM tool config loading | Load and validate `pm.tool` from config.yaml in setup.py | P1 | 2 | - |
| [SDLC-0040](https://github.com/eltanno/sdlc-framework/issues/76) | Implement LocalPM fallback | Create `LocalPM` class for `pm.tool: none` fallback mode | P2 | 2 | SDLC-0038 |
| [SDLC-0041](https://github.com/eltanno/sdlc-framework/issues/77) | Migrate workflow-state schema | Update state.py for v2 schema (supplemental data only) | P1 | 3 | - |
| [SDLC-0042](https://github.com/eltanno/sdlc-framework/issues/78) | Add v1 to v2 state migration | Auto-upgrade v1 format to v2 on load | P1 | 2 | SDLC-0041 |
| [SDLC-0043](https://github.com/eltanno/sdlc-framework/issues/79) | Refactor get_next to use PM tool | Query PM tool for status instead of local state | P1 | 4 | SDLC-0038, SDLC-0041 |
| [SDLC-0044](https://github.com/eltanno/sdlc-framework/issues/80) | Implement label-based ticket claiming | Add/check `ralph-*` labels when claiming/querying tickets | P1 | 3 | SDLC-0043 |
| [SDLC-0045](https://github.com/eltanno/sdlc-framework/issues/81) | Update dependency checking | Query PM tool to check if dependency tickets are closed | P1 | 3 | SDLC-0043 |
| [SDLC-0046](https://github.com/eltanno/sdlc-framework/issues/82) | Update ticket_done for PM tool | Close issue and remove label in PM tool on completion | P1 | 2 | SDLC-0038 |
| [SDLC-0047](https://github.com/eltanno/sdlc-framework/issues/83) | Update mark_blocked for PM tool | Add `blocked` label in PM tool when marking blocked | P1 | 2 | SDLC-0038 |
| [SDLC-0048](https://github.com/eltanno/sdlc-framework/issues/84) | Add state reset on mismatch | Detect PRD/state ticket mismatch and handle reset | P2 | 3 | SDLC-0041 |
| [SDLC-0049](https://github.com/eltanno/sdlc-framework/issues/85) | Update orchestrator integration | Wire everything together in orchestrator.py | P1 | 3 | SDLC-0038, SDLC-0043, SDLC-0046, SDLC-0047 |
| [SDLC-0050](https://github.com/eltanno/sdlc-framework/issues/86) | Integration tests for PM flow | End-to-end tests with mocked GitHub API | P1 | 4 | All above |
| [SDLC-0051](https://github.com/eltanno/sdlc-framework/issues/87) | Legacy comparison tests | Tests comparing Python output to legacy bash scripts | P2 | 3 | SDLC-0050 |

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
| TC-1 | FR-1 | Config loading respects pm.tool | 1. Set `pm.tool: github` in config<br>2. Run setup | GitHub PM initialized |
| TC-2 | FR-2 | Status from GitHub | 1. Create open issue<br>2. Query next ticket | Ticket returned as pending |
| TC-3 | FR-2 | Closed issues are complete | 1. Close issue in GitHub<br>2. Check dependencies | Dependency satisfied |
| TC-4 | FR-3 | Label claiming | 1. Set RALPH_LABEL=ralph-1<br>2. Claim ticket | Label added to issue |
| TC-5 | FR-3 | Label conflict | 1. Issue has ralph-2 label<br>2. ralph-1 queries | Issue skipped |
| TC-6 | FR-5 | Dependency check | 1. Ticket A depends on B<br>2. B is open<br>3. Query next | A is not returned |
| TC-7 | FR-6 | State reset | 1. PRD has [A,B,C]<br>2. State has [A,B,D]<br>3. Setup | Mismatch detected |

### Test Coverage Requirements

- Unit test coverage: > 90% on modified modules
- Integration tests for all PM tool interactions
- Mock tests for GitHub API edge cases (rate limits, network errors)
- Comparison tests against legacy bash scripts (same inputs, same outputs)

---

## Rollout Plan

### Phase 1: Implementation

1. Implement PM tool abstraction layer
2. Migrate state schema
3. Update all commands to use PM tool
4. Write comprehensive tests

### Phase 2: Testing

1. Run integration tests
2. Compare outputs with legacy scripts
3. Test parallel execution with multiple instances
4. Test state reset scenarios

### Phase 3: Release

1. Update documentation
2. Merge to main
3. Monitor for issues

---

## Rollback Plan

### Triggers

When to rollback:
- PM tool queries cause rate limiting issues
- Parallel execution causes data corruption
- Significant behavior differences from legacy

### Process

1. Legacy scripts remain in `.claude/scripts/ralph-legacy/`
2. Update shell wrapper to call legacy scripts
3. Document issue and create follow-up ticket

---

## Open Questions

- [ ] Should we support Trello as a PM tool? (MCP is available, but would add complexity)
- [ ] Should we support Linear/Asana? (Would require additional implementations)
- [ ] Should state reset be automatic or require `--reset` flag?

## Out of Scope

*Explicitly list what this PRD does NOT cover:*

- **Trello/Linear/Asana support** - GitHub Issues only for this iteration
- **New CLI commands** - Using existing interface
- **State migration tool** - Manual or automatic migration of existing v1 state files
- **Improved error messages** - General UX improvements beyond PM tool integration
- **Performance optimization** - Beyond basic caching for API calls

---

## Approval

- [ ] **Product Approved by:** TBD on YYYY-MM-DD
- [ ] **Engineering Approved by:** TBD on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
