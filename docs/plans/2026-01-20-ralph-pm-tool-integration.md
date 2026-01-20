# Implementation Plan: Ralph PM Tool Integration Fix

**Date:** 2026-01-20
**Status:** APPROVED
**PRD:** [docs/prds/2026-01-20-ralph-pm-tool-integration.md](../prds/2026-01-20-ralph-pm-tool-integration.md)
**Author:** Architect Agent

---

## Summary

This plan addresses a critical architectural regression in the Ralph Python port where ticket status is incorrectly read from local `workflow-state.json` instead of the PM tool (GitHub Issues). The fix restores the legacy architecture where GitHub is the source of truth for ticket status, while local state stores only supplemental data (dependencies, attempt counts, blocked reasons). The implementation introduces a PM tool abstraction layer, updates all status-querying code to use the PM tool, and implements label-based concurrency control for safe parallel execution.

## Goals

### Primary Goals

- Restore GitHub Issues as the authoritative source for ticket status
- Implement label-based concurrency control (`ralph-*` labels) for parallel instances
- Support the existing `pm.tool: github` configuration from `config.yaml`
- Migrate local state schema to v2 (supplemental data only)
- Maintain functional parity with legacy bash scripts

### Secondary Goals

- Improve error handling for GitHub API failures (rate limits, network errors)
- Add caching for GitHub API calls within a single operation
- Provide clear migration path for existing v1 state files

## Non-Goals

*What this plan explicitly does NOT cover.*

- **Trello/Linear/Asana support** - GitHub Issues only for this iteration
- **State migration tool** - Manual or automatic migration of existing v1 state files
- **New CLI commands** - Using existing interface
- **Performance optimization beyond basic caching** - Only per-operation caching

---

## Technical Approach

### Architecture Overview

The fix centers on introducing a PM tool abstraction layer that encapsulates all ticket status operations. This follows the Strategy pattern, allowing future PM tool implementations while ensuring the current GitHub implementation matches legacy behavior exactly.

```
                    +-------------------+
                    |   orchestrator.py |
                    +-------------------+
                            |
                            v
         +----------------------------------+
         |         PMTool Protocol          |
         | (get_status, claim, complete,    |
         |  mark_blocked, list_pending)     |
         +----------------------------------+
                    ^           ^
                    |           |
        +-----------+           +-----------+
        |                                   |
+---------------+                   +---------------+
|   GitHubPM    |                   |   LocalPM     |
| (via gh CLI)  |                   | (fallback)    |
+---------------+                   +---------------+

Local State (workflow-state.json v2):
- tickets: ["SDLC-001", "SDLC-002"]  # IDs only, no status
- dependencies: {"SDLC-002": ["SDLC-001"]}
- attempts: {"SDLC-001": 2}
- blocked: {"SDLC-003": "Test failures"}
```

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| `core/pm.py` | PM tool abstraction with Protocol and GitHubPM implementation | New |
| `core/state.py` | Workflow state management - v2 schema (supplemental only) | Modified |
| `core/config.py` | Config loading - add pm.tool reading | Modified |
| `commands/get_next.py` | Get next ticket - use PM tool for status | Modified |
| `commands/setup.py` | Initialize workflow - read pm.tool from config | Modified |
| `commands/ticket_done.py` | Complete ticket - update PM tool and local state | Modified |
| `commands/mark_blocked.py` | Block ticket - update PM tool and local state | Modified |
| `commands/orchestrator.py` | Main loop - use PM tool throughout | Modified |

### Key Technical Decisions

#### Decision 1: Use `gh` CLI for GitHub API calls

**Choice:** Continue using `gh` CLI (subprocess calls) rather than direct GitHub REST API or PyGithub library.

**Rationale:**
- Maintains consistency with legacy bash implementation
- `gh` CLI handles authentication automatically (respects `gh auth login`)
- No new dependencies required
- Simplifies mocking in tests (mock subprocess, not HTTP)
- Legacy scripts proven reliable in production

**Alternatives Considered:**
- PyGithub library - adds dependency, different auth mechanism
- Direct REST API - more code, auth handling complexity

#### Decision 2: Protocol-based PM tool abstraction

**Choice:** Use Python `Protocol` (structural typing) for PM tool interface.

**Rationale:**
- Clean separation of concerns
- Easy to test with mock implementations
- Supports future PM tools without modifying existing code
- No base class inheritance required (duck typing)

**Alternatives Considered:**
- Abstract base class - requires explicit inheritance, less flexible
- Simple functions - harder to test, less organized

#### Decision 3: Atomic label claiming with race detection

**Choice:** Claim tickets by adding label, then verify no competing `ralph-*` labels exist.

**Rationale:**
- Matches legacy implementation exactly
- GitHub label operations are atomic
- Brief sleep + recheck catches race conditions
- Failed claim gracefully moves to next ticket

**Alternatives Considered:**
- GitHub issue assignment only - doesn't support multiple instances with same user
- External locking (Redis, file) - adds infrastructure dependency

#### Decision 4: Version bump to 2.0 for state schema

**Choice:** Increment state schema version to 2.0, removing ticket status from local state.

**Rationale:**
- Clear indication that state format changed
- Allows detection of old v1 files (could auto-migrate in future)
- Prevents mixing old/new formats

**Alternatives Considered:**
- Keep v1.0 with optional fields - confusing, validation complexity
- No version - harder to debug issues

---

## Implementation Phases

### Phase 1: Foundation (PM Tool Abstraction)

**Goal:** Create the PM tool abstraction layer and update config loading.

**Steps:**
1. Create `core/pm.py` with `PMTool` Protocol defining interface
2. Implement `GitHubPM` class using `gh` CLI calls
3. Implement `LocalPM` fallback class for `pm.tool: none`
4. Update `core/config.py` to load and validate `pm.tool` setting
5. Add factory function `get_pm_tool(config)` that returns appropriate implementation
6. Write unit tests for PM tool abstraction (mocked subprocess)

**Exit Criteria:**
- [ ] `PMTool` Protocol defines all required methods
- [ ] `GitHubPM` implements all Protocol methods using `gh` CLI
- [ ] `LocalPM` provides fallback behavior
- [ ] Config loading reads `pm.tool` and fails gracefully if missing
- [ ] Unit tests pass with mocked subprocess calls

### Phase 2: State Schema Migration

**Goal:** Update workflow state to v2 schema (supplemental data only).

**Steps:**
1. Update `core/state.py` dataclasses for v2 schema
2. Remove `status` field from `Ticket` dataclass
3. Add `RalphState` dataclass for supplemental data (tickets, dependencies, attempts, blocked)
4. Update `WorkflowState` to contain `RalphState`
5. Update `load_workflow_state` to handle both v1 and v2 formats
6. Update `save_workflow_state` to always write v2 format
7. Write migration tests (v1 input -> v2 output)

**Exit Criteria:**
- [ ] v2 schema implemented and documented
- [ ] Old v1 state files load correctly (auto-upgrade on read)
- [ ] New state files always written in v2 format
- [ ] Unit tests cover schema migration

### Phase 3: Get Next Ticket Refactor

**Goal:** Refactor `get_next.py` to query PM tool for ticket status.

**Steps:**
1. Inject PM tool instance into `get_next_ticket()`
2. Query PM tool for all open issues with ticket label
3. Filter out issues with other `ralph-*` labels (claimed by other instances)
4. Check if this instance has any in-progress (own label) - prioritize resume
5. Check dependencies against PM tool (closed = satisfied)
6. Claim ticket by adding instance label
7. Verify claim succeeded (no race condition)
8. Return claimed ticket or status (waiting_on_dependencies, complete, etc.)

**Exit Criteria:**
- [ ] `get_next_ticket` queries PM tool, not local state
- [ ] Label-based claiming implemented with race detection
- [ ] Dependency checking queries PM tool for closed issues
- [ ] In-progress resume works (own label prioritized)
- [ ] Integration tests with mocked GitHub

### Phase 4: Ticket Operations Update

**Goal:** Update ticket_done, mark_blocked, and setup to use PM tool.

**Steps:**
1. Update `ticket_done.py` to:
   - Remove instance label from issue
   - Close the issue via PM tool
   - Update local state (attempt count preservation)
2. Update `mark_blocked.py` to:
   - Add `blocked` label via PM tool
   - Remove instance label
   - Unassign issue (if use_assignee enabled)
   - Update local state with reason
3. Update `setup.py` to:
   - Read `pm.tool` from config
   - Initialize appropriate PM tool
   - Detect state/PRD ticket mismatch

**Exit Criteria:**
- [ ] `ticket_done` closes GitHub issue and removes label
- [ ] `mark_blocked` adds blocked label and comments
- [ ] `setup` validates pm.tool configuration
- [ ] State reset on mismatch implemented (warn or prompt)

### Phase 5: Orchestrator Integration

**Goal:** Wire everything together in the orchestrator.

**Steps:**
1. Update `orchestrator.py` to:
   - Load PM tool at startup
   - Pass PM tool to all operations
   - Use PM tool for progress tracking
2. Update `load_config()` to include PM tool settings
3. Handle PM tool errors gracefully (retry with backoff for rate limits)
4. Add comprehensive logging for debugging

**Exit Criteria:**
- [ ] Orchestrator uses PM tool throughout
- [ ] Error handling for API failures
- [ ] Progress output matches legacy scripts
- [ ] Manual testing against real GitHub repo passes

### Phase 6: Testing and Documentation

**Goal:** Comprehensive testing and documentation.

**Steps:**
1. Write integration tests with mocked GitHub responses
2. Create comparison tests against legacy bash scripts (same inputs -> same outputs)
3. Test multi-instance concurrency scenarios
4. Update inline documentation and docstrings
5. Add example config snippets to docs

**Exit Criteria:**
- [ ] > 90% unit test coverage on modified modules
- [ ] Integration tests for all PM tool interactions
- [ ] Comparison tests with legacy scripts pass
- [ ] Multi-instance tests pass (simulated race conditions)

---

## Test Strategy

### Unit Tests

- [ ] `core/pm.py` - PMTool protocol conformance, GitHubPM methods with mocked subprocess
- [ ] `core/state.py` - v2 schema serialization, v1->v2 migration, atomic writes
- [ ] `core/config.py` - pm.tool loading, validation, defaults
- [ ] `commands/get_next.py` - ticket selection logic, dependency checking, claim logic
- [ ] `commands/ticket_done.py` - issue closing, label removal, state update
- [ ] `commands/mark_blocked.py` - blocked label, comment, state update

### Integration Tests

- [ ] Full workflow with mocked GitHub: setup -> get_next -> ticket_done
- [ ] Parallel instance simulation (two instances claiming tickets)
- [ ] Dependency satisfaction checking against closed issues
- [ ] State reset when PRD tickets mismatch

### End-to-End Tests

- [ ] Manual test: run against real GitHub repo with test issues
- [ ] Compare outputs with legacy bash scripts (identical behavior)

### Manual Testing

- [ ] Test with `pm.tool: github` - full workflow
- [ ] Test with `pm.tool: none` - graceful fallback
- [ ] Test multi-worktree scenario (different state files)
- [ ] Test resume after restart (in-progress detection)

---

## Tickets

*These will be created after plan approval:*

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| [SDLC-0038](https://github.com/eltanno/sdlc-framework/issues/74) | Create PM tool abstraction layer | Create `core/pm.py` with `PMTool` Protocol and `GitHubPM` implementation using `gh` CLI | P1 | 3 | 1 | - |
| [SDLC-0039](https://github.com/eltanno/sdlc-framework/issues/75) | Add pm.tool config loading | Update `core/config.py` to read and validate `pm.tool` from config.yaml | P1 | 2 | 1 | - |
| [SDLC-0040](https://github.com/eltanno/sdlc-framework/issues/76) | Implement LocalPM fallback | Create `LocalPM` class for `pm.tool: none` fallback mode | P2 | 2 | 1 | SDLC-0038 |
| [SDLC-0041](https://github.com/eltanno/sdlc-framework/issues/77) | Migrate workflow-state to v2 schema | Update `core/state.py` for v2 schema (supplemental data only, no status) | P1 | 3 | 2 | - |
| [SDLC-0042](https://github.com/eltanno/sdlc-framework/issues/78) | Add v1 to v2 state migration | Update `load_workflow_state` to auto-upgrade v1 format to v2 | P1 | 2 | 2 | SDLC-0041 |
| [SDLC-0043](https://github.com/eltanno/sdlc-framework/issues/79) | Refactor get_next to use PM tool | Update `get_next.py` to query GitHub for status instead of local state | P1 | 4 | 3 | SDLC-0038, SDLC-0041 |
| [SDLC-0044](https://github.com/eltanno/sdlc-framework/issues/80) | Implement label-based ticket claiming | Add claim logic with race detection to `get_next.py` | P1 | 3 | 3 | SDLC-0043 |
| [SDLC-0045](https://github.com/eltanno/sdlc-framework/issues/81) | Update dependency checking | Query PM tool to check if dependencies are closed | P1 | 3 | 3 | SDLC-0043 |
| [SDLC-0046](https://github.com/eltanno/sdlc-framework/issues/82) | Update ticket_done for PM tool | Close issue and remove label via PM tool on completion | P1 | 2 | 4 | SDLC-0038 |
| [SDLC-0047](https://github.com/eltanno/sdlc-framework/issues/83) | Update mark_blocked for PM tool | Add blocked label and comment via PM tool when blocking | P1 | 2 | 4 | SDLC-0038 |
| [SDLC-0048](https://github.com/eltanno/sdlc-framework/issues/84) | Add state reset on mismatch | Detect PRD/state ticket mismatch and handle reset | P2 | 3 | 4 | SDLC-0041 |
| [SDLC-0049](https://github.com/eltanno/sdlc-framework/issues/85) | Update orchestrator integration | Wire PM tool into orchestrator loop with error handling | P1 | 3 | 5 | SDLC-0038, SDLC-0043, SDLC-0046, SDLC-0047 |
| [SDLC-0050](https://github.com/eltanno/sdlc-framework/issues/86) | Integration tests for PM flow | End-to-end tests with mocked GitHub API | P1 | 4 | 6 | All above |
| [SDLC-0051](https://github.com/eltanno/sdlc-framework/issues/87) | Legacy comparison tests | Tests comparing Python output to legacy bash scripts | P2 | 3 | 6 | SDLC-0050 |

**Total: 14 tickets**

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, rename, add simple field | Sonnet |
| 2 | Simple | Basic function, simple validation, minor UI tweak | Sonnet |
| 3 | Moderate | New feature with tests, API endpoint, form with validation | Opus |
| 4 | Complex | Multi-component feature, significant refactor, integrations | Opus |
| 5 | Very Hard | Architectural change, complex algorithm, security-critical | Opus |

*Current threshold: 1-2 -> Sonnet, 3-5 -> Opus. Threshold adjustable based on performance metrics.*

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GitHub API rate limiting | Medium | High | Cache issue lists per operation; add exponential backoff retry |
| Race conditions in ticket claiming | Low | Medium | Brief sleep + recheck pattern (proven in legacy); retry with next ticket |
| Backward compatibility with v1 state | Low | Medium | Auto-detect version on load; graceful upgrade; log warning |
| `gh` CLI not installed | Low | High | Clear error message with install instructions; fail fast |
| Network failures during operations | Medium | Medium | Retry with backoff; atomic local state writes already implemented |
| Multi-instance state conflicts | Low | Medium | Each instance uses own label; no shared local state for status |

---

## Environment Considerations

### Local Development

- **Primary OS:** Linux (WSL2), macOS
- **Prerequisites:** `gh` CLI installed and authenticated (`gh auth login`)
- **Known Limitations:** Requires network access for GitHub API calls

### CI Environment

- **Platform:** GitHub Actions
- **Considerations:** `gh` CLI pre-installed; needs `GH_TOKEN` for API access
- **Test Strategy:** Mock all subprocess calls; no real GitHub API calls in CI

---

## Dependencies

### External Dependencies

- `gh` CLI (GitHub CLI) - for all GitHub API operations
- `pyyaml` - for config.yaml parsing (already installed)

### Internal Dependencies

- `core/state.py` - workflow state management
- `core/config.py` - configuration loading
- `core/github.py` - existing GitHub utilities (will be supplemented, not replaced)

### Blocking Items

- [ ] None - can begin implementation immediately

---

## Open Questions

*Questions that need answers (ideally before implementation):*

- [x] Should state reset be automatic or require confirmation? **Answer:** Warn and continue non-interactively; prompt interactively (from PRD)
- [ ] Should we add `pm.tool: local` as explicit option distinct from `none`? **Recommend:** Keep `none` for simplicity
- [ ] Cache duration for GitHub issue list? **Recommend:** Per-operation only (no persistent cache)

---

## Success Criteria

*How do we know we're done?*

- [ ] `pm.tool: github` config setting is read and respected
- [ ] Ticket status is always queried from GitHub, never from local state
- [ ] Label-based concurrency works (two instances don't conflict)
- [ ] Dependencies are checked against closed issues in GitHub
- [ ] State file v2 schema contains only supplemental data
- [ ] All existing unit tests pass
- [ ] New integration tests pass
- [ ] Comparison with legacy bash scripts shows identical behavior
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

- [ ] **Approved by:** TBD on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted.*
