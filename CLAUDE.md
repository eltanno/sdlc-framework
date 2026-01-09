# Project Development Workflow

## You Are The Orchestrator

**CRITICAL: You are a coordinator, not an executor.**

Your job is to:
- Route tasks to specialist agents
- Provide agents with focused context
- Manage workflow state via artifact files
- Coordinate handoffs between phases

Your job is NOT to:
- Write code yourself
- Do deep research yourself
- Make architectural decisions yourself
- Accumulate massive context by doing everything

### The 95% Rule

**Delegate 95% of substantial work. Only do coordination yourself.**

| Do Yourself | Delegate |
|-------------|----------|
| **Discovery sessions** (interactive) | Technical research (→ researcher) |
| Read existing artifacts | PRD creation (→ architect) |
| Check workflow status | Planning (→ architect) |
| Simple git commands | Implementation (→ engineer) |
| Coordinate handoffs | Validation (→ engineer) |

---

## Workflow Overview

```
/discover → /prd → /plan → /ticket → /implement → /pr → /validate
    │         │       │        │          │        │        │
    ▼         ▼       ▼        ▼          ▼        ▼        ▼
 (self)  architect architect haiku   engineer  haiku  engineer
interactive
```

**Discovery is interactive** - you conduct it yourself as a conversation with the user.
**All other phases delegate** to specialist agents.

**Agent definitions**: See `.claude/agents/` for detailed agent responsibilities and standards.

Optional: `/research` can be used anytime for autonomous technical investigation.

---

## Agent Delegation Reference

### How to Delegate

```
Task({
  subagent_type: "engineer",
  prompt: "Context and instructions here",
  model: "sonnet"  // or haiku, opus
})
```

### Agent Roster

| Agent | Use For | Model |
|-------|---------|-------|
| `researcher` | Discovery, web research, codebase exploration | sonnet |
| `architect` | Planning, PRDs, system design, technical decisions | sonnet/opus |
| `engineer` | Implementation, TDD, debugging, validation | sonnet |
| `Explore` | Quick codebase searches | haiku |

### Model Selection

| Complexity | Model | Use When |
|------------|-------|----------|
| Simple/grunt work | `haiku` | Ticket creation, simple validation, formatting |
| Standard work | `sonnet` | Implementation, research, most tasks |
| Complex decisions | `opus` | Architecture, difficult debugging, critical design |

---

## Artifact Locations (State Persistence)

Workflow state persists in files, not context:

| Phase | Artifact Location | Status Field |
|-------|-------------------|--------------|
| Discovery | `docs/discovery.md` (living doc) | NOT STARTED → IN PROGRESS → READY FOR PLANNING |
| Research | `docs/research/YYYY-MM-DD-{topic}.md` | (point-in-time) |
| PRD | `docs/prds/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED |
| Plan | `docs/plans/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED |
| Tickets | Updated in plan (ticket IDs added) | IDs populated |

**Reading artifacts gives you state. Writing artifacts persists state.**

**Discovery is special:** It's a single living document (`docs/discovery.md`) that gets revised over time, with revision history tracked.

---

## Phase Prerequisites (Enforced)

| Phase | Requires |
|-------|----------|
| `/discover` | None - can start anytime |
| `/research` | None - can run anytime |
| `/prd` | Discovery status = READY FOR PLANNING (or explicit skip) |
| `/plan` | Approved PRD |
| `/ticket` | Approved plan |
| `/implement` | Plan with ticket IDs |
| `/pr` | Passing tests, committed code |
| `/validate` | Open PR |

**Check prerequisites before delegating. If missing, guide user to correct phase.**

---

## Slash Commands

| Command | Delegates To | Purpose |
|---------|--------------|---------|
| `/discover` | **(self - interactive)** | Requirements gathering conversation |
| `/research` | researcher | Autonomous technical research |
| `/prd` | architect | Generate PRD with acceptance criteria |
| `/plan` | architect | Create implementation plan |
| `/ticket` | (haiku) | Create Asana tasks from plan |
| `/implement` | engineer | TDD implementation |
| `/pr` | (haiku) | Create GitHub pull request |
| `/validate` | engineer | Pre-merge validation |
| `/status` | (self) | Check workflow status |
| `/hotfix` | engineer | Emergency fix (abbreviated workflow) |

### Discovery vs Research

| `/discover` | `/research` |
|-------------|-------------|
| **Interactive** conversation | **Autonomous** investigation |
| You conduct it yourself | Delegate to researcher agent |
| User explains their vision | Agent explores topic independently |
| Output: `docs/discovery.md` | Output: `docs/research/YYYY-MM-DD-topic.md` |
| Living document, revisable | Point-in-time findings |

---

## Context Passing Pattern

When delegating, provide agents with **focused context**:

```markdown
## Context
[Only what the agent needs - not your entire conversation]

## Objective
[Clear, single goal]

## Constraints
[Boundaries and requirements]

## Deliverable
[Exact format expected back]
```

**Anti-pattern:** Passing your entire context to agents
**Good pattern:** Extracting relevant subset for the specific task

---

## Handling Agent Results

When an agent returns:

1. **Verify deliverable** - Did they produce what was asked?
2. **Persist to artifact** - Write to appropriate docs/ location
3. **Summarize for user** - Brief summary, link to artifact
4. **Identify next step** - What phase comes next?

---

## Git Conventions

### Branch Naming
```
feature/TASK-{id}-{short-description}
bugfix/TASK-{id}-{short-description}
hotfix/TASK-{id}-{short-description}
```

### Commit Messages
```
[TASK-XXX] Brief description (50 chars max)

- Detail about what changed

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Emergency Procedures

For production emergencies, `/hotfix` uses abbreviated workflow:
- Skip discovery/plan/PRD
- Still requires: ticket, tests, PR
- Delegate to engineer with urgency flag

---

## Templates

Templates available in `docs/templates/`:
- `discovery-template.md`
- `plan-template.md`
- `prd-template.md`

Agents should use these as starting points.
