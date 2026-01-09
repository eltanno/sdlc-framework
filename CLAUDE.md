# Project Development Workflow

This project follows a structured SDLC workflow to ensure quality, traceability, and team alignment.

## Workflow Overview

```
Discovery → Plan → PRD → Tickets → Branch → TDD → PR → Validate
```

Every feature, enhancement, or significant bug fix follows this workflow. Small fixes (typos, config tweaks) may use an abbreviated path.

---

## Phase Requirements

### 1. Discovery Phase (`/discover`)

**Purpose:** Research and document understanding before planning.

**When Required:** New features, significant changes, unfamiliar areas of codebase.

**Output:** `docs/discovery/YYYY-MM-DD-{topic}.md`

**Exit Criteria:** User explicitly approves the discovery document.

---

### 2. Planning Phase (`/plan`)

**Purpose:** Create detailed implementation plan with user approval.

**Prerequisites:**
- Approved discovery document (or user explicitly waives for small tasks)

**Output:** `docs/plans/YYYY-MM-DD-{feature}.md` with status APPROVED

**Exit Criteria:** User marks plan as APPROVED in the document.

---

### 3. PRD Phase (`/prd`)

**Purpose:** Create Product Requirements Document with acceptance criteria.

**Prerequisites:**
- Approved plan document

**Output:** `docs/prds/YYYY-MM-DD-{feature}.md`

**Exit Criteria:** PRD contains:
- Clear acceptance criteria (testable)
- Asana ticket placeholders ready to fill
- User approval

---

### 4. Tickets Phase (`/ticket`)

**Purpose:** Create Asana tasks from PRD.

**Prerequisites:**
- Completed PRD document

**Output:**
- Asana tasks created
- PRD updated with task IDs

**Exit Criteria:** All tasks exist in Asana with IDs recorded in PRD.

---

### 5. Implementation Phase (`/implement`)

**Purpose:** TDD implementation of the feature.

**Prerequisites:**
- PRD with Asana ticket IDs
- Feature branch created

**Process:**
1. Create feature branch: `feature/TASK-{id}-{description}`
2. Write failing tests first
3. Implement until tests pass
4. Refactor if needed

**Exit Criteria:** All tests pass, code complete.

---

### 6. Pull Request Phase (`/pr`)

**Purpose:** Create GitHub PR for review.

**Prerequisites:**
- All tests passing
- Code committed with proper messages
- Feature branch pushed

**Output:** GitHub PR with:
- Link to Asana ticket
- Link to PRD
- Summary of changes
- Test verification

---

### 7. Validation Phase (`/validate`)

**Purpose:** Final checks before merge.

**Checks:**
- [ ] All tests pass
- [ ] No linting errors
- [ ] PR has required approvals
- [ ] Asana ticket updated
- [ ] Documentation updated if needed

---

## Enforcement Rules

### NEVER Do These Without Prerequisites:
- Write implementation code without an approved plan
- Create a PR without passing tests
- Commit without a ticket reference (except docs/config)
- Merge without validation passing

### ALWAYS Do These:
- Check for existing artifacts before starting a phase
- Use exact naming conventions for all artifacts
- Update artifact status when a phase completes
- Link related artifacts together (discovery → plan → PRD → tickets)

### Abbreviated Workflow (Small Tasks < 2 hours)

For small fixes, the workflow can be abbreviated:
1. Create ticket directly (skip discovery/plan/PRD)
2. Branch, implement with TDD, PR
3. Must still have ticket reference in commits

Document the abbreviated workflow in the PR description.

---

## Git Conventions

### Branch Naming
```
feature/TASK-{id}-{short-description}
bugfix/TASK-{id}-{short-description}
hotfix/TASK-{id}-{short-description}
docs/TASK-{id}-{short-description}
```

### Commit Messages
```
[TASK-XXX] Brief description (50 chars max)

- Detail about what changed
- Another detail if needed

Co-Authored-By: Claude <noreply@anthropic.com>
```

### PR Title Format
```
[TASK-XXX] Brief description of the change
```

---

## Slash Commands

| Command | Purpose | Phase |
|---------|---------|-------|
| `/discover` | Research and document understanding | Discovery |
| `/plan` | Create implementation plan | Planning |
| `/prd` | Generate PRD document | PRD |
| `/ticket` | Create Asana tasks | Tickets |
| `/implement` | TDD implementation | Implementation |
| `/pr` | Create pull request | PR |
| `/validate` | Pre-merge validation | Validation |
| `/status` | Show current workflow status | Any |
| `/hotfix` | Emergency fix (abbreviated workflow) | Emergency |

---

## File Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| Discovery | `docs/discovery/YYYY-MM-DD-{topic}.md` | `docs/discovery/2026-01-08-auth-system.md` |
| Plan | `docs/plans/YYYY-MM-DD-{feature}.md` | `docs/plans/2026-01-08-oauth-login.md` |
| PRD | `docs/prds/YYYY-MM-DD-{feature}.md` | `docs/prds/2026-01-08-oauth-login.md` |
| Decision | `docs/decisions/YYYY-MM-DD-{topic}.md` | `docs/decisions/2026-01-08-db-choice.md` |

---

## Quality Standards

### Code
- All code must have tests
- Tests must pass before PR
- Follow existing code style
- No commented-out code
- No console.log/print statements in production code

### Documentation
- Update README if public API changes
- Update inline docs for complex logic
- Keep PRD updated with any scope changes

### Testing
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows

---

## Emergency Procedures

### Hotfix Process (`/hotfix`)

For production emergencies only:
1. Create `hotfix/TASK-{id}-{description}` branch from main
2. Fix the issue with tests
3. Create PR with `[HOTFIX]` prefix
4. Get expedited review
5. Merge and deploy
6. Create follow-up ticket for proper fix if needed

**Must still have:**
- Ticket reference
- Tests
- PR review (can be post-merge for critical issues)

---

## Templates

Templates are available in `docs/templates/`:
- `prd-template.md` - Product Requirements Document
- `plan-template.md` - Implementation Plan
- `discovery-template.md` - Discovery Document

Use these as starting points for all artifacts.
