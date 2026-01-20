# PRD: Asana PM Tool Integration

**Date:** 2026-01-20
**Status:** APPROVED
**Discovery:** docs/discovery/2026-01-20-asana-pm-tool-integration.md
**Plan:** [To be created]
**Owner:** TBD
**Stakeholders:** TBD

---

## Discovery Reference

**Note:** This PRD is for ONE feature/epic within this iteration. The discovery document contains the iteration's scope and vision.

**Iteration Vision:**
Native Asana integration for the SDLC framework, replacing all MCP tool references with direct Asana REST API calls to enable full Ralph orchestrator support and slash command parity with GitHub Issues.

**How This Feature Fits:**
This feature implements the `AsanaPM` class that allows Ralph to manage tickets in Asana (claim, complete, block, etc.) and updates all slash commands to support Asana as a first-class PM tool option. It enables teams using Asana to leverage the full SDLC framework automation.

---

## Executive Summary

### Problem Statement

The SDLC framework references "Asana MCP" (`mcp__asana__*`) in slash commands but no officially maintained Asana MCP exists. Teams using Asana cannot use the Ralph orchestrator or automated ticket management features. The framework needs direct Asana REST API integration to support Asana as a PM tool option.

### Solution Summary

Implement a native `AsanaPM` class that communicates directly with the Asana REST API using environment-configured credentials. This class will implement the existing `PMTool` Protocol, allowing Ralph and all slash commands to work seamlessly with Asana tasks. The solution uses Asana tags for claiming/blocking tickets, subtasks for acceptance criteria, and native dependencies for task ordering.

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Asana support | 0% | 100% | All PMTool Protocol methods implemented |
| Slash command coverage | 0 commands | 5 commands | `/ticket`, `/hotfix`, `/pr`, `/implement`, `/execution-report` support Asana |
| Test coverage | N/A | >80% | Unit tests + integration tests |
| MCP references removed | Multiple | 0 | No `mcp__asana__*` in codebase |

---

## Requirements

### Functional Requirements

#### FR-1: AsanaPM Class - Core Protocol Methods

**Priority:** P1 (Must Have)

**Description:** Create `AsanaPM` class in `.claude/ralph/core/asana_pm.py` implementing all methods from the `PMTool` Protocol to enable Ralph orchestrator integration.

**Acceptance Criteria:**

- [ ] Given Asana credentials are configured in environment, when `AsanaPM()` is instantiated, then it connects to the Asana API successfully
- [ ] Given an Asana task ID, when `get_ticket_status(task_id)` is called, then it returns `OPEN`, `CLOSED`, or `BLOCKED` based on task completion status and tags
- [ ] Given a task ID and "ralph-N" label, when `claim_ticket(task_id, label)` is called, then the corresponding tag is added to the Asana task
- [ ] Given a task ID, when `close_ticket(task_id)` is called, then the task is marked complete AND moved to the "Done" section
- [ ] Given a task ID and reason, when `add_blocked_label(task_id, reason)` is called, then the "blocked" tag is added AND a comment is posted with the reason
- [ ] Given a task ID, when `is_ticket_claimed(task_id)` is called, then it returns `(True, "ralph-N")` if any ralph-* tag exists, else `(False, None)`
- [ ] Given a list of task IDs, when `get_open_tickets(task_ids)` is called, then it returns `TicketInfo` objects for incomplete tasks
- [ ] Given a task ID and label, when `remove_label(task_id, label)` is called, then the corresponding tag is removed from the task
- [ ] Given a task ID, when `assign_to_self(task_id)` is called, then the task assignee is set to "me"

#### FR-2: Asana API HTTP Client

**Priority:** P1 (Must Have)

**Description:** Implement HTTP client wrapper for Asana REST API calls with proper authentication and error handling.

**Acceptance Criteria:**

- [ ] Given `ASANA_ACCESS_TOKEN` environment variable is set, when making API requests, then Bearer token authentication is used
- [ ] Given `ASANA_WORKSPACE_ID` environment variable is set, when workspace-scoped operations are needed, then the correct workspace is used
- [ ] Given `ASANA_PROJECT_ID` environment variable is set, when project-scoped operations are needed, then the correct project is used
- [ ] Given a valid API request, when the request succeeds, then the response JSON is returned
- [ ] Given an invalid token, when making any API request, then `PMAuthError` is raised with helpful message
- [ ] Given a non-existent task ID, when making a task request, then `PMError` is raised with "task not found" message
- [ ] Given API rate limiting (429 response), when a request fails, then `PMError` is raised with rate limit message (no retry for MVP)
- [ ] Given network failure, when making API request, then `PMError` is raised with connection error message

#### FR-3: Tag Management

**Priority:** P1 (Must Have)

**Description:** Manage Asana tags for Ralph claiming and blocking, creating tags if they don't exist.

**Acceptance Criteria:**

- [ ] Given tags "ralph-0" through "ralph-5" don't exist in workspace, when any claim operation is attempted, then the required tag is created automatically
- [ ] Given "blocked" tag doesn't exist in workspace, when `add_blocked_label()` is called, then the "blocked" tag is created automatically
- [ ] Given "task" tag doesn't exist in workspace, when ticket creation occurs, then the "task" tag is created automatically
- [ ] Given a tag already exists with matching name, when tag creation is attempted, then the existing tag is used (no duplicate created)
- [ ] Given tag lookup is needed, when `_get_or_create_tag(name)` is called, then tag GID is returned (creating if necessary)

#### FR-4: Section Management for Done State

**Priority:** P1 (Must Have)

**Description:** Move tasks to "Done" section when closed, handling section discovery.

**Acceptance Criteria:**

- [ ] Given a project has a "Done" section, when `close_ticket()` is called, then the task is moved to that section
- [ ] Given a project has no "Done" section, when `close_ticket()` is called, then the task is marked complete without section move (graceful degradation)
- [ ] Given multiple sections exist, when looking for "Done" section, then case-insensitive matching is used

#### FR-5: /ticket Slash Command Update

**Priority:** P1 (Must Have)

**Description:** Update `/ticket` command to create Asana tasks via direct API instead of MCP.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` in config.yaml, when `/ticket` is run, then tasks are created via Asana REST API
- [ ] Given a PRD with tickets table, when tasks are created, then each task has title format `[SDLC-XXXX] {title}`
- [ ] Given acceptance criteria in PRD, when task is created, then criteria are added as subtasks (checklist)
- [ ] Given ticket has dependencies listed, when task is created, then Asana native dependencies are set
- [ ] Given required tags don't exist, when first task is created, then "task", "blocked", and "ralph-0" through "ralph-5" tags are created

#### FR-6: /hotfix Slash Command Update

**Priority:** P1 (Must Have)

**Description:** Update `/hotfix` command to respect `pm.tool` config instead of assuming Asana MCP.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` in config.yaml, when `/hotfix` is run, then task is created via Asana REST API
- [ ] Given `pm.tool: github` in config.yaml, when `/hotfix` is run, then issue is created via gh CLI
- [ ] Given hotfix task is created, when title is set, then format is `[HOTFIX] {description}`
- [ ] Given hotfix is resolved, when task is updated, then PR link is added to task description

#### FR-7: /pr Slash Command Update

**Priority:** P2 (Should Have)

**Description:** Add Asana task update section to `/pr` command for linking PRs to tasks.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` in config.yaml, when `/pr` is run after implementation, then a comment is added to the Asana task with PR link
- [ ] Given PR is created successfully, when Asana update is attempted but fails, then warning is logged but PR creation succeeds

#### FR-8: /implement Slash Command Update

**Priority:** P2 (Should Have)

**Description:** Add Asana task fetch section to `/implement` command for retrieving ticket details.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` and a task ID, when `/implement` is run, then task details are fetched via Asana API
- [ ] Given task has subtasks (acceptance criteria), when details are fetched, then subtasks are included in context

#### FR-9: /execution-report Slash Command Update

**Priority:** P2 (Should Have)

**Description:** Add Asana task status query to `/execution-report` for ticket counts.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` in config.yaml, when `/execution-report` is run, then it queries Asana for open/closed/blocked task counts
- [ ] Given blocked tasks exist, when report is generated, then blocked task titles and reasons are listed

#### FR-10: Orchestrator Factory Integration

**Priority:** P1 (Must Have)

**Description:** Update `create_pm_tool()` factory in orchestrator to instantiate `AsanaPM` when configured.

**Acceptance Criteria:**

- [ ] Given `pm.tool: asana` in config.yaml, when `create_pm_tool()` is called, then `AsanaPM` instance is returned
- [ ] Given Asana credentials are missing, when `AsanaPM` is instantiated, then `PMAuthError` is raised with helpful message listing required env vars

### Non-Functional Requirements

#### NFR-1: API Compatibility

- Asana REST API version: 1.0 (stable)
- Base URL: `https://app.asana.com/api/1.0`
- Authentication: Bearer token via `ASANA_ACCESS_TOKEN`

#### NFR-2: Error Handling

- All API errors must fail operations with clear user feedback
- No silent degradation (except section move in close_ticket)
- Error messages must include actionable guidance
- Rate limit errors (429) should indicate retry not supported in MVP

#### NFR-3: Test Coverage

- Unit test coverage: >80% for `asana_pm.py`
- All API calls must be mockable via `httpx` transport
- Integration tests gated by `RUN_ASANA_INTEGRATION_TESTS` env var

#### NFR-4: Configuration

- No new config.yaml keys required (uses existing `pm.tool: asana`)
- Environment variables: `ASANA_ACCESS_TOKEN`, `ASANA_WORKSPACE_ID`, `ASANA_PROJECT_ID`

---

## User Stories

### US-1: Developer Using Asana for Project Management

**Story:** As a developer using Asana, I want Ralph to automatically manage my Asana tasks so that I don't have to manually update tickets during automated implementation.

**Acceptance Criteria:**
- [ ] Ralph can claim Asana tasks using tags
- [ ] Ralph can mark tasks complete when implementation succeeds
- [ ] Ralph can mark tasks blocked with a reason when implementation fails
- [ ] Multiple Ralph instances don't conflict via ralph-N tags

**Notes:** This is the primary use case for the AsanaPM implementation.

### US-2: Team Lead Creating Tickets

**Story:** As a team lead, I want to run `/ticket` and have tasks created in Asana so that my team can track work in our existing PM tool.

**Acceptance Criteria:**
- [ ] Running `/ticket` creates Asana tasks from PRD
- [ ] Tasks have proper SDLC-XXXX IDs in titles
- [ ] Acceptance criteria appear as subtasks
- [ ] Tasks are linked by dependencies

### US-3: Developer Running Hotfix

**Story:** As a developer responding to a production emergency, I want `/hotfix` to create an Asana task so that the fix is tracked in our system.

**Acceptance Criteria:**
- [ ] `/hotfix` creates task in Asana when `pm.tool: asana`
- [ ] Task is marked with [HOTFIX] prefix
- [ ] PR link is added when fix is complete

### US-4: Developer Getting Implementation Context

**Story:** As a developer starting implementation, I want `/implement` to fetch Asana task details so that I have full context without opening the Asana web app.

**Acceptance Criteria:**
- [ ] Task description is fetched from Asana
- [ ] Subtasks (acceptance criteria) are included
- [ ] Task dependencies are shown

---

## Technical Specifications

### Asana API Endpoints Required

| Operation | Method | Endpoint | Used By |
|-----------|--------|----------|---------|
| Get task | GET | `/tasks/{task_id}` | `get_ticket_status`, `is_ticket_claimed`, `get_open_tickets` |
| Update task | PUT | `/tasks/{task_id}` | `close_ticket`, `assign_to_self` |
| Add tag to task | POST | `/tasks/{task_id}/addTag` | `claim_ticket`, `add_blocked_label` |
| Remove tag from task | POST | `/tasks/{task_id}/removeTag` | `remove_label` |
| Create task | POST | `/tasks` | `/ticket`, `/hotfix` |
| Create subtask | POST | `/tasks/{parent_id}/subtasks` | `/ticket` (acceptance criteria) |
| Add comment (story) | POST | `/tasks/{task_id}/stories` | `add_blocked_label`, `/pr` |
| Get workspace tags | GET | `/workspaces/{workspace_id}/tags` | Tag lookup |
| Create tag | POST | `/workspaces/{workspace_id}/tags` | Tag creation |
| Get project sections | GET | `/projects/{project_id}/sections` | `close_ticket` |
| Move to section | POST | `/sections/{section_id}/addTask` | `close_ticket` |
| Add dependency | POST | `/tasks/{task_id}/addDependencies` | `/ticket` |

### New Files to Create

| File | Purpose |
|------|---------|
| `.claude/ralph/core/asana_pm.py` | AsanaPM class implementing PMTool Protocol |
| `.claude/ralph/tests/unit/test_asana_pm.py` | Unit tests with mocked HTTP |
| `.claude/ralph/tests/integration/test_asana_flow.py` | Integration tests with real API |

### Files to Modify

| File | Changes |
|------|---------|
| `.claude/ralph/core/pm.py` | Add import and export for AsanaPM |
| `.claude/ralph/commands/orchestrator.py` | Add AsanaPM to `create_pm_tool()` factory |
| `.claude/commands/ticket.md` | Replace `mcp__asana__create_task` with direct API section |
| `.claude/commands/hotfix.md` | Make PM tool configurable, add Asana API section |
| `.claude/commands/pr.md` | Add Asana task update section |
| `.claude/commands/implement.md` | Add Asana task fetch section |
| `.claude/commands/execution-report.md` | Add Asana task status query |

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| httpx | (existing) | HTTP client for API calls |
| (no new deps) | - | Use existing project dependencies |

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| SDLC-0052 | AsanaPM HTTP client and authentication | Implement base HTTP client with Bearer auth, error handling, and environment config loading | P1 | 3 | - |
| SDLC-0053 | AsanaPM tag management | Implement tag lookup/creation for ralph-*, blocked, and task tags | P1 | 2 | SDLC-0052 |
| SDLC-0054 | AsanaPM get_ticket_status method | Implement status check via task completion and blocked tag | P1 | 2 | SDLC-0052, SDLC-0053 |
| SDLC-0055 | AsanaPM claim_ticket and is_ticket_claimed | Implement claiming via ralph-* tags with race condition handling | P1 | 3 | SDLC-0052, SDLC-0053 |
| SDLC-0056 | AsanaPM close_ticket with section move | Implement task completion and Done section move | P1 | 3 | SDLC-0052, SDLC-0053 |
| SDLC-0057 | AsanaPM add_blocked_label with comment | Implement blocked tag and reason comment | P1 | 2 | SDLC-0052, SDLC-0053 |
| SDLC-0058 | AsanaPM remaining methods | Implement get_open_tickets, remove_label, assign_to_self | P1 | 2 | SDLC-0052 through SDLC-0057 |
| SDLC-0059 | Orchestrator factory integration | Update create_pm_tool() to instantiate AsanaPM | P1 | 1 | SDLC-0058 |
| SDLC-0060 | Update /ticket slash command | Replace MCP calls with direct API, add subtask creation for AC | P1 | 3 | SDLC-0059 |
| SDLC-0061 | Update /hotfix slash command | Make PM tool configurable, add Asana direct API path | P1 | 2 | SDLC-0059 |
| SDLC-0062 | Update /pr slash command | Add Asana task comment with PR link | P2 | 2 | SDLC-0059 |
| SDLC-0063 | Update /implement slash command | Add Asana task detail fetch | P2 | 2 | SDLC-0059 |
| SDLC-0064 | Update /execution-report command | Add Asana task status query for ticket counts | P2 | 2 | SDLC-0059 |
| SDLC-0065 | Unit tests for AsanaPM | Comprehensive mocked tests for all methods | P1 | 3 | SDLC-0052 through SDLC-0058 |
| SDLC-0066 | Integration tests for Asana flow | Real API tests gated by env var | P2 | 3 | SDLC-0065 |

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
| TC-1 | FR-1 | Get status of open task | 1. Create AsanaPM<br>2. Call get_ticket_status with valid task ID | Returns TicketStatus.OPEN |
| TC-2 | FR-1 | Get status of completed task | 1. Mock API to return completed task<br>2. Call get_ticket_status | Returns TicketStatus.CLOSED |
| TC-3 | FR-1 | Get status of blocked task | 1. Mock API to return task with blocked tag<br>2. Call get_ticket_status | Returns TicketStatus.BLOCKED |
| TC-4 | FR-1 | Claim ticket adds tag | 1. Call claim_ticket(id, "ralph-1")<br>2. Verify API called with addTag | Returns True, tag added |
| TC-5 | FR-1 | Close ticket marks complete | 1. Call close_ticket(id)<br>2. Verify API called with completed=true | Returns True, task completed |
| TC-6 | FR-2 | Invalid token raises auth error | 1. Set invalid ASANA_ACCESS_TOKEN<br>2. Make any API call | PMAuthError raised |
| TC-7 | FR-2 | Missing task raises error | 1. Call get_ticket_status with invalid ID<br>2. Verify error | PMError with "not found" |
| TC-8 | FR-3 | Tag created if missing | 1. Mock tags list without ralph-1<br>2. Call claim_ticket<br>3. Verify tag creation API called | Tag created, then used |
| TC-9 | FR-4 | Task moved to Done section | 1. Mock sections with "Done"<br>2. Call close_ticket<br>3. Verify addTask API called | Task in Done section |
| TC-10 | FR-10 | Factory creates AsanaPM | 1. Set pm.tool: asana in config<br>2. Call create_pm_tool() | AsanaPM instance returned |

### Test Coverage Requirements

- Unit test coverage: > 80% for `asana_pm.py`
- Integration tests for full workflow: create task -> claim -> complete
- All error paths covered (auth, not found, rate limit, network)

---

## Rollout Plan

### Phase 1: Core Implementation

- Implement AsanaPM class with all PMTool Protocol methods
- Add unit tests with mocked HTTP
- Update orchestrator factory

### Phase 2: Slash Commands

- Update /ticket, /hotfix, /pr, /implement, /execution-report
- Test each command manually with real Asana project

### Phase 3: Integration Testing

- Run integration tests with test Asana project
- Verify Ralph end-to-end flow with Asana

### Phase 4: Documentation

- Update README with Asana setup instructions
- Document environment variables
- Add troubleshooting guide

---

## Rollback Plan

### Triggers

When to rollback:
- AsanaPM causes orchestrator crashes
- API errors not handled gracefully
- Data corruption in Asana tasks

### Process

1. Revert to `pm.tool: github` or `pm.tool: none` in config.yaml
2. No database changes to revert (Asana is external)
3. Notify users of temporary Asana unavailability
4. Create issue to track fix

---

## Open Questions

All questions resolved during discovery session:
- [x] Tags vs custom fields -> Tags (simpler, sufficient for MVP)
- [x] Section movement -> Optional, graceful degradation
- [x] Retry on rate limit -> No retry for MVP
- [x] Single project vs multi-project -> Single project per config

## Out of Scope

*Explicitly list what this PRD does NOT cover:*

- Trello integration updates (already has working MCP)
- Linear integration (no MCP, not requested)
- Asana webhooks for real-time updates
- Asana custom fields (use tags instead)
- Multi-project support (single project per config)
- Proactive rate limit throttling (fail on 429, no retry)
- OAuth authentication flow (uses Personal Access Token)

---

## Approval

- [ ] **Product Approved by:** TBD on YYYY-MM-DD
- [ ] **Engineering Approved by:** TBD on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
