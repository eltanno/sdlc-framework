# SDLC Workflow Reference

Detailed reference for the SDLC automation framework. For a quick overview, see `README.md`.

---

## Workflow Overview

```
PLANNING (human approval at each gate):
/discover → /prd → /plan → /ticket
    │         │       │        │
    ▼         ▼       ▼        ▼
 (self)   architect architect haiku
                                │
                      [Tickets ready in PM]
                                │
EXECUTION (autonomous):         ▼
/ralph-loop → /execution-report → /system-review → /release
     │               │                  │               │
     ▼               ▼                  ▼               ▼
  ralph           (self)             (self)          (self)
 parallel        document        process review   update README
```

**Planning** defines WHAT and HOW. Human approval required at each gate.
**Execution** builds and ships. Ralph runs autonomously; report/review/release are orchestrator tasks.

---

## Planning Phases

### 1. Discovery (`/discover`)

Interactive requirements gathering for an iteration.

- **Run by:** You (orchestrator) — interactive conversation with user
- **Input:** User's vision for this iteration
- **Output:** `docs/discovery/YYYY-MM-DD-{version}.md`
- **Status:** NOT STARTED → IN PROGRESS → READY FOR PLANNING
- **Gate:** User approves before proceeding to PRD

Each planning cycle gets its own discovery:
- `docs/discovery/2025-01-15-v1-core.md`
- `docs/discovery/2025-02-20-v1.1-oauth.md`

### 2. PRD (`/prd`)

Formal Product Requirements Document.

- **Run by:** Architect agent
- **Prerequisites:** Approved discovery (or explicit skip)
- **Output:** `docs/prds/YYYY-MM-DD-{feature}.md`
- **Status:** DRAFT → APPROVED
- **Contains:** Executive summary, functional/non-functional requirements, acceptance criteria, user stories, ticket definitions
- **Gate:** User approves before proceeding to Plan

**The PRD defines WHAT to build, not HOW.**

### 3. Plan (`/plan`)

Technical implementation plan.

- **Run by:** Architect agent
- **Prerequisites:** Approved PRD
- **Output:** `docs/plans/YYYY-MM-DD-{feature}.md`
- **Status:** DRAFT → APPROVED
- **Contains:** Architecture decisions, component breakdown, file structure, implementation phases, ticket breakdown with estimates, test strategy
- **Gate:** User approves before creating tickets

**The plan defines HOW to build what the PRD specified.**

### 4. Tickets (`/ticket`)

Create tasks in your PM tool.

- **Run by:** Haiku agent
- **Prerequisites:** Approved plan
- **Output:** Tasks in PM tool (Trello/Asana/GitHub Issues/Linear), plan updated with ticket IDs
- **Creates:** One task per ticket row in the plan

**This is the final planning phase.** Once tickets have IDs, execution can begin.

---

## Execution Phases

### 5. Ralph Loop (`/ralph-loop`)

Autonomous implementation of all tickets.

- **Run by:** Ralph orchestrator (1-4 parallel loops)
- **Prerequisites:** Plan with ticket IDs, clean git state
- **Output:** Feature branches, PRs, merged code

**How it works:**
1. Detects PRD and plan (or takes them as arguments)
2. Launches parallel loops using git worktrees
3. Each loop: get next ticket → invoke Claude engineer (TDD) → validate → create PR → auto-merge → repeat
4. Monitors progress, handles retries, blocks tickets that exceed max attempts
5. Updates `docs/SYSTEM.md` with completed work
6. Cleans up worktrees and git state

**Configuration** in `config.yaml`:
```yaml
ralph:
  sonnet_threshold: 2           # Complexity ≤2 = Sonnet, >2 = Opus
  max_attempts: 3               # Retries before blocking
  max_concurrent_loops: 4       # Parallel instances (1-4)
  engineer_timeout: 30          # Minutes per implementation
  validator_timeout: 10         # Minutes per validation
```

**Related:** `/ticket-reset {id}` resets blocked tickets for retry.

### 6. Execution Report (`/execution-report`)

Document what was implemented vs what was planned.

- **Run by:** You (orchestrator)
- **Prerequisites:** All tickets complete
- **Output:** `docs/execution-reports/YYYY-MM-DD-{feature}.md`
- **Documents:** Completed tasks, modified tasks, skipped tasks, challenges, divergences from plan

### 7. System Review (`/system-review`)

Analyze process effectiveness.

- **Run by:** You (orchestrator)
- **Prerequisites:** Execution report
- **Output:** `docs/system-reviews/YYYY-MM-DD-{feature}.md`
- **Analyzes:** Good/bad divergences, root causes, pattern compliance
- **Generates:** CLAUDE.md updates, command updates, template improvements

**"You're not looking for bugs in the code — you're looking for bugs in the process."**

### 8. Release (`/release`)

Update README and finalize the iteration.

- **Run by:** You (orchestrator)
- **Prerequisites:** System review complete
- **Output:** Updated `README.md`, git tag
- **Actions:** Update README with new features, tag the release, mark iteration complete

**The iteration isn't complete until documentation reflects reality.**

---

## Bug Fix Workflows

### Automated (`/playtest-loop`)

The primary bug fix workflow. Playtests the app, fixes bugs, retests — up to 5 iterations.

```
playtest → bugs found? → fix → retest → repeat until clean
```

- Requires Playwright MCP
- Produces cumulative bug report at `docs/todo/playtest-bugs.md`

### Root Cause Analysis (`/rca`)

For bugs where the root cause is unclear.

- **Output:** `docs/rca/YYYY-MM-DD-{issue}.md`
- Investigate first, then fix

### Manual Fallback

Legacy per-ticket commands still available:

| Command | Use When |
|---------|----------|
| `/bugfix {desc}` | Single known bug, TDD fix |
| `/hotfix` | Production emergency, abbreviated workflow |
| `/implement {ticket}` | Manual single-ticket implementation |
| `/pr {ticket}` | Create PR for a completed ticket |
| `/validate {ticket}` | Pre-merge validation |

---

## Document Hierarchy

```
docs/
├── discovery/              # One per iteration (v1, v1.1, v2)
│   └── YYYY-MM-DD-{version}.md
├── prds/                   # One per feature
│   └── YYYY-MM-DD-{feature}.md
├── plans/                  # One per PRD
│   └── YYYY-MM-DD-{feature}.md
├── execution-reports/      # One per execution cycle
│   └── YYYY-MM-DD-{feature}.md
├── system-reviews/         # One per execution cycle
│   └── YYYY-MM-DD-{feature}.md
├── research/               # Point-in-time investigations
│   └── YYYY-MM-DD-{topic}.md
├── rca/                    # Root cause analysis
│   └── YYYY-MM-DD-{issue}.md
├── legacy/                 # Output from /analyze-codebase
├── guides/                 # How-to guides
├── templates/              # Document templates
└── state/                  # Ralph state files (per ticket)
```

### Document Relationships

```
Discovery (iteration scope)
    ↓
   PRD (one feature)
    ↓
   Plan (technical approach)
    ↓
   Tickets (individual tasks)
    ↓
   Ralph Loop (implementation)
    ↓
   Execution Report → System Review → Release → README
```

### Status Fields

| Document | Statuses |
|----------|----------|
| Discovery | NOT STARTED → IN PROGRESS → READY FOR PLANNING |
| PRD | DRAFT → APPROVED |
| Plan | DRAFT → APPROVED |
| RCA | ANALYZING → FIX PROPOSED → VERIFIED |

**Reading artifacts gives you state. Writing artifacts persists state.**

---

## Prerequisites by Phase

### No Prerequisites

| Command | Purpose |
|---------|---------|
| `/whats-next` | Workflow status and next action |
| `/prime` | Load project context |
| `/research` | Technical investigation |
| `/analyze-codebase` | Legacy codebase analysis |
| `/rca` | Bug investigation |

### Planning Chain

| Phase | Requires |
|-------|----------|
| `/discover` | None |
| `/prd` | Discovery = READY FOR PLANNING (or explicit skip) |
| `/plan` | PRD = APPROVED |
| `/ticket` | Plan = APPROVED |

### Execution Chain

| Phase | Requires |
|-------|----------|
| `/ralph-loop` | Plan with ticket IDs, clean git state |
| `/execution-report` | All tickets complete |
| `/system-review` | Execution report |
| `/release` | System review complete |

**Check prerequisites before proceeding. If missing, guide user to correct phase.**

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
type(scope): description [TICKET-ID]

Types: feat, fix, docs, test, refactor, chore
```

---

## Artifact Commit Rule

> **Every artifact MUST be committed immediately after creation.**

| Phase | Creates | Commit |
|-------|---------|--------|
| `/discover` | `docs/discovery/*.md` | `git add docs/discovery/ && git commit` |
| `/prd` | `docs/prds/*.md` | `git add docs/prds/ && git commit` |
| `/plan` | `docs/plans/*.md` | `git add docs/plans/ && git commit` |
| `/research` | `docs/research/*.md` | `git add docs/research/ && git commit` |
| `/rca` | `docs/rca/*.md` | `git add docs/rca/ && git commit` |
| `/release` | `README.md` | `git add README.md && git commit` |

**Why:** Untracked files can be lost during branch operations. Documents ARE the state — if they're not committed, the workflow has no foundation.

**Before delegating implementation work**, verify: `git status docs/` shows clean.

---

## Templates

Available in `docs/templates/`:
- `discovery-template.md`
- `prd-template.md`
- `plan-template.md`
- `rca-template.md`
- `execution-report-template.md`
- `system-review-template.md`
