# Discovery: Asana PM Tool Integration

**Last Updated:** 2026-01-20
**Status:** APPROVED
**Revisions:** 1

---

## Vision

### What We're Building

Native Asana integration for the SDLC framework, replacing all MCP tool references with direct Asana REST API calls. This includes:
1. Slash command support (`/ticket`, `/pr`, `/hotfix`, etc.)
2. Ralph orchestrator `AsanaPM` class implementing the PMTool Protocol
3. Full parity with GitHub Issues functionality

### Problem Statement

The current system references "Asana MCP" (`mcp__asana__*`) but no officially maintained Asana MCP exists. The framework needs direct API integration to support Asana as a PM tool option.

### Target Users

- Developers using Asana for project management who want automated ticket management
- Teams running Ralph orchestrator with Asana as their ticket tracking system

### Success Criteria

- [ ] `pm.tool: asana` works end-to-end for all slash commands
- [ ] Ralph can claim, complete, and block Asana tasks via tags
- [ ] All existing tests pass + new Asana-specific tests
- [ ] No MCP references remain for Asana

---

## Asana Mapping Decisions

| Ralph/GitHub Concept | Asana Implementation |
|---------------------|---------------------|
| Issue | Task |
| Labels (ralph-0, ralph-1, etc.) | Tags |
| "blocked" label | Tag named "blocked" |
| "task" label | Tag named "task" |
| Close issue | Mark task complete + move to "Done" section |
| Issue comment | Task comment |
| Issue title `[SDLC-0001] Title` | Task name `[SDLC-0001] Title` |
| Issue body | Task description (notes) |
| Acceptance criteria | Description + subtask checklist |
| Dependencies | Asana native dependencies + local state sync |
| Section/column movement | Skip for MVP |

---

## Scope

### In Scope (MVP)

#### Slash Commands to Update

| Command | Current State | Changes Needed |
|---------|--------------|----------------|
| `/ticket` | Has `mcp__asana__create_task` | Replace with direct API: create task, add tags, create subtasks for acceptance criteria |
| `/hotfix` | Hardcoded to Asana MCP | Make respect `pm.tool` config, use direct API |
| `/pr` | References "Update Asana Ticket" | Add PR link to task via API when pm.tool: asana |
| `/implement` | References "Ticket details from Asana" | Fetch task details via API when pm.tool: asana |
| `/execution-report` | GitHub-only ticket status | Add Asana task status query |
| `/validate` | No PM tool interaction | No changes needed |

#### Ralph `AsanaPM` Class

Create `.claude/ralph/core/asana_pm.py` implementing `PMTool` Protocol:

| Method | Asana API Equivalent |
|--------|---------------------|
| `get_ticket_status(task_id)` | `GET /tasks/{task_id}` - check completed + tags |
| `claim_ticket(task_id, label)` | `POST /tasks/{task_id}/addTag` with ralph-* tag |
| `close_ticket(task_id)` | `PUT /tasks/{task_id}` completed=true + move to Done section |
| `add_blocked_label(task_id, reason)` | `POST /tasks/{task_id}/addTag` + `POST /tasks/{task_id}/stories` (comment) |
| `is_ticket_claimed(task_id)` | `GET /tasks/{task_id}` - check for ralph-* tags |
| `get_open_tickets(task_ids)` | `GET /tasks` filtered by project + not completed |
| `remove_label(task_id, label)` | `POST /tasks/{task_id}/removeTag` |
| `assign_to_self(task_id)` | `PUT /tasks/{task_id}` assignee="me" |

#### Additional Asana Operations Needed

| Operation | API Call | Used By |
|-----------|----------|---------|
| Create task | `POST /tasks` | `/ticket`, `/hotfix` |
| Update task | `PUT /tasks/{task_id}` | `/pr`, `/hotfix` |
| Add comment | `POST /tasks/{task_id}/stories` | mark_blocked, `/pr` |
| Create subtask | `POST /tasks/{parent_id}/subtasks` | `/ticket` (acceptance criteria) |
| Create tag | `POST /workspaces/{workspace_id}/tags` | `/ticket` (setup) |
| Get tags | `GET /workspaces/{workspace_id}/tags` | `/ticket` (check existing) |
| Add dependency | `POST /tasks/{task_id}/addDependencies` | `/ticket` |
| Get project sections | `GET /projects/{project_id}/sections` | close_ticket (find Done section) |
| Move to section | `POST /sections/{section_id}/addTask` | close_ticket |

### Out of Scope

- Trello integration updates (already has MCP that works)
- Linear integration (no MCP, but not requested)
- Asana webhooks (real-time updates)
- Asana custom fields (use tags instead)
- Multi-project support (single project per config)

---

## Technical Context

### Environment Variables

```bash
# .env
ASANA_ACCESS_TOKEN=2/450627955811/...  # Personal Access Token
ASANA_WORKSPACE_ID=450628873581
ASANA_PROJECT_ID=450628879752
```

### Configuration

```yaml
# config.yaml
pm:
  tool: asana  # asana | trello | github | linear | none
```

### Asana API

- Base URL: `https://app.asana.com/api/1.0`
- Auth: Bearer token via `ASANA_ACCESS_TOKEN`
- Rate limit: 1500 requests/minute (handle errors, no proactive throttling for MVP)

### Tag Setup (First Run)

When `/ticket` runs with `pm.tool: asana`, ensure these tags exist:
- `task` - Work item marker
- `blocked` - Blocked tickets
- `ralph-0` through `ralph-5` - Instance claiming

---

## Files to Modify

### Slash Commands (`.claude/commands/`)

| File | Changes |
|------|---------|
| `ticket.md` | Replace `mcp__asana__create_task` with direct API section |
| `hotfix.md` | Make PM tool configurable, add Asana API section |
| `pr.md` | Add Asana task update section |
| `implement.md` | Add Asana task fetch section |
| `execution-report.md` | Add Asana task status query |

### Ralph Python Code (`.claude/ralph/`)

| File | Changes |
|------|---------|
| `core/asana_pm.py` | **NEW** - AsanaPM class implementing PMTool Protocol |
| `core/pm.py` | Import and expose AsanaPM |
| `commands/orchestrator.py` | Add AsanaPM to `create_pm_tool()` factory |
| `core/config.py` | Already supports `asana` in VALID_PM_TOOLS |

### Tests (`.claude/ralph/tests/`)

| File | Changes |
|------|---------|
| `unit/test_asana_pm.py` | **NEW** - Mock API tests for AsanaPM |
| `integration/test_asana_flow.py` | **NEW** - Integration tests (real API optional) |

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Asana API unreachable | Fail operation with clear error message |
| Invalid token | Fail with auth error, suggest checking ASANA_ACCESS_TOKEN |
| Task not found | Fail with "task not found" error |
| Tag doesn't exist | Create it automatically |
| Rate limited | Fail with rate limit error (no retry for MVP) |

---

## Open Questions

All resolved during discovery session.

---

## Risks & Assumptions

### Assumptions

- Asana Personal Access Token is sufficient (vs OAuth)
- Single project per configuration is acceptable
- Tags are adequate for claiming/blocking (vs custom fields)
- "Done" section exists in the project (or can be created)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| API changes | Medium | Use stable v1.0 API, document version |
| Rate limits | Low | 1500/min is generous; fail gracefully |
| Token expiration | Medium | Document token refresh process |
| Missing "Done" section | Low | Create if missing, or just mark complete |

---

## Testing Strategy

### Unit Tests (Mocked)

- Mock all HTTP calls to Asana API
- Test each AsanaPM method in isolation
- Test error handling paths
- Test tag creation/lookup logic

### Integration Tests

- Use real Asana API with test project (optional, gated by env var)
- Test full workflow: create task -> claim -> complete
- Test race condition handling with tags
- Can be skipped in CI if no credentials

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-20 | Initial discovery session |

---

## Next Steps

After approval:
1. Run `/prd` to create detailed PRD with tickets
2. Run `/plan` to create technical implementation plan
3. Run `/ticket` to create Asana tasks (using GitHub until Asana is implemented)
4. Run `/implement` for each ticket
