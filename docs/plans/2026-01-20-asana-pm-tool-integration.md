# Implementation Plan: Asana PM Tool Integration

**Date:** 2026-01-20
**Status:** APPROVED
**PRD:** docs/prds/2026-01-20-asana-pm-tool-integration.md
**Discovery:** docs/discovery/2026-01-20-asana-pm-tool-integration.md
**Author:** Claude (Architect Agent)

---

## Summary

This plan details the implementation of native Asana REST API integration for the SDLC framework. The approach mirrors the existing `GitHubPM` implementation pattern, creating an `AsanaPM` class that implements the `PMTool` Protocol. The implementation is divided into three phases: Core AsanaPM foundation, Slash Command integration, and Testing/Documentation. This enables teams using Asana to leverage the full Ralph orchestrator automation.

## Goals

### Primary Goals

- Implement `AsanaPM` class with full `PMTool` Protocol compliance
- Enable Ralph orchestrator to manage Asana tasks (claim, complete, block)
- Update all slash commands to support Asana as a first-class PM tool option

### Secondary Goals

- Maintain architectural consistency with existing `GitHubPM` implementation
- Provide comprehensive test coverage (>80%)
- Remove all `mcp__asana__*` references from the codebase

## Non-Goals

*What this plan explicitly does NOT cover.*

- Trello integration updates (already has working MCP)
- Linear integration (no MCP, not requested)
- Asana webhooks for real-time updates
- Asana custom fields (use tags instead)
- Multi-project support (single project per config)
- Proactive rate limit throttling (fail on 429, no retry)
- OAuth authentication flow (uses Personal Access Token)

## Technical Approach

### Architecture Overview

The `AsanaPM` class will follow the same structural pattern as `GitHubPM`, but use HTTP calls instead of subprocess (gh CLI). This maintains consistency while leveraging Python's httpx library for API communication.

```
                    PMTool Protocol
                          │
            ┌─────────────┼─────────────┐
            │             │             │
        GitHubPM      AsanaPM       LocalPM
         (gh CLI)    (HTTP/REST)   (in-memory)
            │             │             │
            ▼             ▼             ▼
        GitHub API   Asana API    Local State
```

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| `.claude/ralph/core/asana_pm.py` | AsanaPM class implementing PMTool Protocol | New |
| `.claude/ralph/core/pm.py` | Export AsanaPM from module | Modified |
| `.claude/ralph/commands/orchestrator.py` | Factory function to instantiate AsanaPM | Modified |
| `.claude/commands/ticket.md` | Direct Asana API for task creation | Modified |
| `.claude/commands/hotfix.md` | Configurable PM tool support | Modified |
| `.claude/commands/pr.md` | Asana task comment with PR link | Modified |
| `.claude/commands/implement.md` | Asana task detail fetch | Modified |
| `.claude/commands/execution-report.md` | Asana task status query | Modified |
| `.claude/ralph/tests/unit/test_asana_pm.py` | Unit tests with mocked HTTP | New |
| `.claude/ralph/tests/integration/test_asana_flow.py` | Integration tests with real API | New |

### Key Technical Decisions

#### Decision 1: HTTP Library Choice

**Choice:** Use `httpx` for HTTP calls

**Rationale:**
- `httpx` is not currently in requirements.txt, but it's the modern Python HTTP client
- Supports both sync and async (future-proof)
- Better error handling and timeout support than `requests`
- Well-documented transport mocking for tests

**Alternatives Considered:**
- `requests`: More familiar, but `httpx` is more modern and has better async support
- `urllib3`: Too low-level, requires more boilerplate

**Update:** After checking requirements.txt, only `pyyaml` is listed. We will add `httpx` as a dependency.

#### Decision 2: Tag Management Strategy

**Choice:** Lazy tag creation with workspace-level caching

**Rationale:**
- Tags are workspace-scoped in Asana (not project-scoped)
- First API call per tag name checks existence, creates if missing
- Cache tag GIDs in memory during AsanaPM instance lifetime
- Avoid repeated tag lookups for same label

**Implementation:**
```python
class AsanaPM:
    def __init__(self, ...):
        self._tag_cache: dict[str, str] = {}  # name -> gid

    def _get_or_create_tag(self, name: str) -> str:
        if name in self._tag_cache:
            return self._tag_cache[name]
        # Query API, create if missing, cache result
        ...
```

#### Decision 3: Section Movement for close_ticket

**Choice:** Optional "Done" section movement with graceful degradation

**Rationale:**
- Not all Asana projects have a "Done" section
- Marking complete is the primary requirement
- Section movement is "nice to have" for board visualization

**Implementation:**
```python
def close_ticket(self, ticket_id: str) -> bool:
    # 1. Mark task complete (required)
    self._update_task(ticket_id, completed=True)

    # 2. Try to move to Done section (optional)
    try:
        done_section = self._find_done_section()
        if done_section:
            self._move_to_section(ticket_id, done_section)
    except PMError:
        pass  # Graceful degradation

    return True
```

#### Decision 4: Error Handling Pattern

**Choice:** Fail-fast with descriptive exceptions

**Rationale:**
- PRD specifies "no silent degradation" (except section move)
- Users need clear feedback on API failures
- Consistent with existing `GitHubPM` error patterns

**Exceptions:**
- `PMAuthError`: Invalid/missing token
- `PMError`: API failures, task not found, rate limits

## Implementation Phases

### Phase 1: Core AsanaPM (Foundation)

**Goal:** Implement the `AsanaPM` class with all `PMTool` Protocol methods

**Steps:**
1. Add `httpx` to `requirements.txt`
2. Create `AsanaPM` class skeleton in `.claude/ralph/core/asana_pm.py`
3. Implement HTTP client wrapper with authentication
4. Implement tag management (get_or_create_tag)
5. Implement `get_ticket_status` method
6. Implement `claim_ticket` and `is_ticket_claimed` methods
7. Implement `close_ticket` with section move
8. Implement `add_blocked_label` with comment
9. Implement remaining methods (`get_open_tickets`, `remove_label`, `assign_to_self`)
10. Update `orchestrator.py` factory to instantiate `AsanaPM`

**Exit Criteria:**
- [ ] All `PMTool` Protocol methods implemented
- [ ] `create_pm_tool()` returns `AsanaPM` when `pm.tool: asana`
- [ ] Basic manual testing with real Asana project succeeds
- [ ] `PMAuthError` raised for missing credentials

### Phase 2: Slash Commands (Integration)

**Goal:** Update all slash commands to support Asana via direct API

**Steps:**
1. Update `/ticket` command to create tasks via API
2. Update `/hotfix` command to respect `pm.tool` config
3. Update `/pr` command to add PR link as Asana comment
4. Update `/implement` command to fetch Asana task details
5. Update `/execution-report` command to query Asana task status

**Exit Criteria:**
- [ ] `/ticket` creates Asana tasks with subtasks for acceptance criteria
- [ ] `/hotfix` works with both GitHub and Asana
- [ ] `/pr` adds comment to Asana task with PR link
- [ ] `/implement` fetches task details from Asana
- [ ] `/execution-report` shows Asana ticket counts

### Phase 3: Testing (Quality)

**Goal:** Comprehensive test coverage and documentation

**Steps:**
1. Create unit tests for all `AsanaPM` methods (mocked HTTP)
2. Create integration tests for full workflow (gated by env var)
3. Test error handling paths (auth, not found, rate limit)
4. Update documentation with Asana setup instructions

**Exit Criteria:**
- [ ] Unit test coverage >80% for `asana_pm.py`
- [ ] Integration tests pass with real Asana project
- [ ] All error paths have tests
- [ ] README includes Asana configuration section

## Test Strategy

### Unit Tests

Test files: `.claude/ralph/tests/unit/test_asana_pm.py`

Mock Strategy: Use `httpx` mock transport to simulate API responses

- [ ] Test `get_ticket_status` returns correct status for open/closed/blocked tasks
- [ ] Test `claim_ticket` adds tag and verifies claim
- [ ] Test `is_ticket_claimed` detects ralph-* tags
- [ ] Test `close_ticket` marks complete and moves to Done section
- [ ] Test `add_blocked_label` adds tag and posts comment
- [ ] Test `get_open_tickets` filters by completion status
- [ ] Test `remove_label` removes tag from task
- [ ] Test `assign_to_self` sets assignee
- [ ] Test tag creation when tag doesn't exist
- [ ] Test tag reuse when tag already exists
- [ ] Test `PMAuthError` raised for invalid token
- [ ] Test `PMError` raised for task not found
- [ ] Test `PMError` raised for rate limit (429)

### Integration Tests

Test files: `.claude/ralph/tests/integration/test_asana_flow.py`

Gated by: `RUN_ASANA_INTEGRATION_TESTS=1` environment variable

- [ ] Full workflow: create task -> claim -> complete
- [ ] Race condition: two labels added, verify correct winner
- [ ] Blocked flow: mark blocked, verify tag and comment
- [ ] Dependency satisfaction: verify dependency checking

### Manual Testing

- [ ] Run `/ticket` with `pm.tool: asana` and verify tasks created
- [ ] Run Ralph orchestrator with Asana project
- [ ] Verify all slash commands work end-to-end

## Tickets

*These will be created after plan approval:*

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| SDLC-0052 | AsanaPM HTTP client and authentication | Implement base HTTP client with Bearer auth, error handling, and environment config loading. Add httpx to requirements.txt. | P1 | 3 | 1 | - |
| SDLC-0053 | AsanaPM tag management | Implement tag lookup/creation for ralph-*, blocked, and task tags. Cache tag GIDs for performance. | P1 | 2 | 1 | SDLC-0052 |
| SDLC-0054 | AsanaPM get_ticket_status method | Implement status check via task completion state and blocked tag presence. | P1 | 2 | 1 | SDLC-0052, SDLC-0053 |
| SDLC-0055 | AsanaPM claim_ticket and is_ticket_claimed | Implement claiming via ralph-* tags with race condition handling via re-check pattern. | P1 | 3 | 1 | SDLC-0052, SDLC-0053 |
| SDLC-0056 | AsanaPM close_ticket with section move | Implement task completion and optional Done section move with graceful degradation. | P1 | 3 | 1 | SDLC-0052, SDLC-0053 |
| SDLC-0057 | AsanaPM add_blocked_label with comment | Implement blocked tag addition and reason comment posting via stories API. | P1 | 2 | 1 | SDLC-0052, SDLC-0053 |
| SDLC-0058 | AsanaPM remaining methods | Implement get_open_tickets, remove_label, assign_to_self. | P1 | 2 | 1 | SDLC-0052 through SDLC-0057 |
| SDLC-0059 | Orchestrator factory integration | Update create_pm_tool() to instantiate AsanaPM when pm.tool: asana. | P1 | 1 | 1 | SDLC-0058 |
| SDLC-0060 | Update /ticket slash command | Replace MCP calls with direct Asana API. Add subtask creation for acceptance criteria. Add dependency linking. | P1 | 3 | 2 | SDLC-0059 |
| SDLC-0061 | Update /hotfix slash command | Make PM tool configurable via config.yaml. Add Asana direct API path alongside GitHub. | P1 | 2 | 2 | SDLC-0059 |
| SDLC-0062 | Update /pr slash command | Add Asana task comment with PR link when pm.tool: asana. Handle failures gracefully. | P2 | 2 | 2 | SDLC-0059 |
| SDLC-0063 | Update /implement slash command | Add Asana task detail fetch when pm.tool: asana. Include subtasks in context. | P2 | 2 | 2 | SDLC-0059 |
| SDLC-0064 | Update /execution-report command | Add Asana task status query for ticket counts. List blocked tasks with reasons. | P2 | 2 | 2 | SDLC-0059 |
| SDLC-0065 | Unit tests for AsanaPM | Comprehensive mocked tests for all methods. Cover all error paths. Achieve >80% coverage. | P1 | 3 | 3 | SDLC-0052 through SDLC-0058 |
| SDLC-0066 | Integration tests for Asana flow | Real API tests gated by RUN_ASANA_INTEGRATION_TESTS env var. Test full workflow. | P2 | 3 | 3 | SDLC-0065 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, rename, add simple field | Sonnet |
| 2 | Simple | Basic function, simple validation, minor UI tweak | Sonnet |
| 3 | Moderate | New feature with tests, API endpoint, form with validation | Opus |
| 4 | Complex | Multi-component feature, significant refactor, integrations | Opus |
| 5 | Very Hard | Architectural change, complex algorithm, security-critical | Opus |

*Current threshold: 1-2 -> Sonnet, 3-5 -> Opus. Threshold adjustable based on performance metrics.*

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Asana API rate limiting during high activity | Low | Medium | Fail gracefully with clear error message; 1500 req/min is generous |
| Token expiration during long Ralph runs | Medium | High | Document token refresh process; detect 401 and raise `PMAuthError` |
| "Done" section missing in project | Medium | Low | Graceful degradation - just mark complete without move |
| Tag name collisions with existing tags | Low | Low | Use specific prefixes (ralph-*, blocked, task) |
| httpx not available in environment | Low | High | Add explicit dependency; test imports on startup |

## Environment Considerations

*Relevant for test infrastructure, CI/CD, or platform-specific features.*

### Local Development

- **Primary OS:** Windows WSL2 / macOS / Linux
- **Known Limitations:** Asana API requires network access; tests should mock HTTP
- **Required Setup:** `ASANA_ACCESS_TOKEN`, `ASANA_WORKSPACE_ID`, `ASANA_PROJECT_ID` in .env

### CI Environment

- **Platform:** GitHub Actions
- **Considerations:**
  - Unit tests run without Asana credentials (mocked)
  - Integration tests gated by `RUN_ASANA_INTEGRATION_TESTS` env var
  - CI secrets needed if integration tests enabled

## Dependencies

### External Dependencies

- `httpx` - HTTP client library (to be added to requirements.txt)
- Asana REST API v1.0 - External service

### Internal Dependencies

- `PMTool` Protocol (existing in `core/pm.py`)
- `PMError`, `PMAuthError` exceptions (existing)
- `TicketStatus`, `TicketInfo` types (existing)
- `get_pm_tool_type()` config helper (existing)

### Blocking Items

- [ ] None identified - all prerequisites are in place

## Open Questions

*Questions that need answers (ideally before implementation):*

All questions resolved during discovery - no open questions remain.

## Success Criteria

*How do we know we're done?*

- [ ] `pm.tool: asana` works end-to-end for all slash commands
- [ ] Ralph orchestrator can claim, complete, and block Asana tasks via tags
- [ ] All existing tests pass
- [ ] New Asana-specific unit tests pass with >80% coverage
- [ ] No `mcp__asana__*` references remain in codebase
- [ ] Documentation updated with Asana setup instructions

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
