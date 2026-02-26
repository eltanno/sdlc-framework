# SDLC Automation Framework

A repeatable software development lifecycle for Claude Code that enforces quality gates, maintains traceability, and produces working software through structured planning and automated execution.

## Quick Start

You plan it. Claude builds it. Six commands from idea to shipped software:

```
/discover          Tell Claude what you want to build. Interactive Q&A
                   produces a structured requirements document.

/prd               Generates a formal PRD with acceptance criteria
                   from the approved discovery.

/plan              Creates the technical implementation plan — architecture,
                   tickets, test strategy, dependency order.

/ticket            Creates actionable tickets in your PM tool from the
                   approved plan. One ticket per unit of work.

/ralph-loop        Executes the plan autonomously. Implements all tickets
                   in parallel, creates PRs, validates, and merges.

/execution-report  Documents what was built vs what was planned.

/system-review     Analyzes the process and captures lessons learned.
```

Before starting, configure `config.yaml` with your PM tool and dev commands, and `.env` with your API keys (copy from `.env.example`). Then run `/discover` to start.

---

## Commands Reference

### Core SDLC Commands

These are the main commands that drive the framework. They follow the workflow in order:

| Command | Phase | What It Does |
|---------|-------|-------------|
| `/discover` | Planning | Interactive conversation to gather requirements. You describe what you want to build, and it produces a structured discovery document capturing scope, users, features, and constraints. |
| `/prd {name}` | Planning | Generates a formal Product Requirements Document from the approved discovery. Includes user stories, acceptance criteria, and scope boundaries. |
| `/plan {name}` | Planning | Creates a technical implementation plan from the approved PRD. Breaks work into tickets with architecture decisions, file changes, test strategy, and dependency order. |
| `/ticket` | Planning | Creates actionable tickets in your PM tool (Trello/Asana/GitHub Issues) from the approved plan. One ticket per logical unit of work. |
| `/ralph-loop` | Execution | Launches the Ralph autonomous orchestrator. Takes the PRD and plan, implements all tickets in parallel (1-4 concurrent loops), creates PRs, validates, and merges. This is the primary execution method. |
| `/execution-report` | Finalize | Documents what was actually implemented vs what was planned. Records completed tasks, divergences, challenges, and modified approaches. |
| `/system-review` | Finalize | Analyzes the process itself — what worked, what didn't, template improvements, and lessons learned for the next cycle. |
| `/release` | Finalize | Updates the project README with shipped features and tags the git release. |

### Testing & Bug Fix Commands

| Command | What It Does |
|---------|-------------|
| `/playtest` | Runs a full Playwright browser playtest — page loads, auth, core features, state persistence, edge cases. Produces a cumulative bug report at `docs/todo/playtest-bugs.md`. Requires Playwright MCP. |
| `/playtest-loop` | Automated loop: playtest, fix bugs, retest. Repeats until no critical/major bugs remain (max 5 iterations). The primary way to find and fix bugs. Requires Playwright MCP. |
| `/fix-manual-bugs` | Reads annotated screenshots from `docs/todo/manual-test/` and fixes all reported issues. For when you've done manual QA and documented bugs with screenshots. Requires Playwright MCP. |
| `/rca {issue}` | Root cause analysis. Investigates an issue systematically before fixing — reproduces, identifies root cause, assesses impact, proposes fix. Creates `docs/rca/YYYY-MM-DD-{issue}.md`. |
| `/audit-tests` | Audits test files for meaningfulness. Classifies each test as meaningful, weak, tautological, implementation-coupled, or redundant. Produces a report with recommendations. |

### Utility Commands

| Command | What It Does |
|---------|-------------|
| `/whats-next` | Workflow dashboard — shows document status, git state, progress checklist, and recommends the next action. |
| `/research {topic}` | Autonomous technical research on any topic. Can be used anytime. Saves findings to `docs/research/`. |
| `/prime` | Loads comprehensive project context (structure, docs, git state, active work) before starting a task. |
| `/handover` | Generates a session handover document at `tmp/handover.md` to preserve context for the next session. |
| `/ticket-reset {id}` | Resets a blocked Ralph ticket back to pending so it can be retried. |
| `/analyze-codebase` | Deep read-only analysis of an existing codebase. Produces 8 structured documents covering architecture, patterns, tech debt, and more. For brownfield/legacy projects. |
| `/new-project {path}` | Creates a new project from the framework template. Sets up directory structure, config files, and git. |
| `/sync-framework {path}` | Updates an existing project with the latest framework files (commands, scripts, templates). |

### Manual Fallback Commands

These are the original per-ticket commands, now superseded by `/ralph-loop` and `/playtest-loop`. Still available if you need direct control over individual tickets or Ralph gets stuck mid-ticket.

| Command | What It Does |
|---------|-------------|
| `/implement {ticket}` | Manual TDD implementation of a single ticket. |
| `/pr {ticket}` | Creates a pull request for a completed ticket. |
| `/validate {ticket}` | Pre-merge validation — tests, lint, build, plan alignment. |
| `/bugfix {description}` | Manual single bug fix using TDD. |
| `/hotfix` | Emergency production fix with abbreviated workflow. |

---

## The Problem

Software development often suffers from:

- **Scope creep** - Requirements change mid-implementation without proper review
- **Untested code** - Pressure to ship bypasses test coverage
- **Review bottlenecks** - PRs sit waiting for human review
- **Lost context** - Decisions made in conversations disappear
- **Inconsistent process** - Each feature follows a different path

The result: technical debt, bugs in production, and frustrated teams.

## The Solution

This framework enforces a **two-stage development cycle** that separates thinking from doing:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            PLANNING                                      │
│                         (Define & Approve)                               │
│                                                                          │
│   Discover ──→ PRD ──→ Plan ──→ Tickets                                 │
│       ↓         ↓        ↓          ↓                                   │
│   [Approve] [Approve] [Approve]  [Ready]                                │
│                                                                          │
│   Output: Approved artifacts + actionable tickets in PM tool            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            EXECUTION                                     │
│                      (Build, Review & Ship)                              │
│                                                                          │
│   Primary — Autonomous (all tickets):                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ /ralph-loop ──→ implements all tickets ──→ PRs ──→ merges       │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Fallback — Manual (per ticket):                                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ Branch ──→ TDD ──→ Implement ──→ PR ──→ Validate ──→ Merge     │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   After all tickets complete:                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ Report ──→ Review ──→ Release                                   │   │
│   │    ↓          ↓          ↓                                      │   │
│   │ Document   Analyze   Update README                              │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Output: Merged PRs, tested code, updated README                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key principle:** Planning requires human judgment and approval. Execution follows the approved plan mechanically.

---

## Planning Cycle

Planning defines **what** to build and **how** to build it. Each phase produces an artifact that must be approved before proceeding.

### Phase 1: Discovery (`/discover`)

Interactive conversation to understand requirements for this iteration.

- **Input:** User's idea or problem for this version
- **Output:** `docs/discovery/YYYY-MM-DD-{version}.md` - Versioned document for this iteration
- **Gate:** User approves before proceeding to PRD

### Phase 2: PRD (`/prd`)

Formal Product Requirements Document with acceptance criteria.

- **Input:** Approved discovery
- **Output:** `docs/prds/YYYY-MM-DD-{feature}.md`
- **Contains:** User stories, acceptance criteria, scope boundaries, out-of-scope items
- **Gate:** User approves before proceeding to Plan

### Phase 3: Plan (`/plan`)

Technical implementation plan breaking the PRD into buildable chunks.

- **Input:** Approved PRD
- **Output:** `docs/plans/YYYY-MM-DD-{feature}.md`
- **Contains:** Architecture decisions, file changes, test strategy, implementation order
- **Gate:** User approves before creating tickets

### Phase 4: Tickets (`/ticket`)

Create actionable work items in your PM tool.

- **Input:** Approved plan
- **Output:** Tickets in Trello/Asana/GitHub Issues with IDs
- **Contains:** One ticket per logical unit of work, linked to plan sections
- **Gate:** Tickets ready = Planning complete

### Planning Produces Versions

Each complete planning cycle produces a version of your software:

```
Planning Cycle 1 → v1.0 (core features)
Planning Cycle 2 → v2.0 (enhanced features)
Planning Cycle 3 → v3.0 (advanced features)
```

You can run multiple planning cycles to incrementally build your product. Each cycle:
1. Starts with discovery (or updates existing discovery)
2. Produces a new PRD for the new scope
3. Creates a plan for that scope
4. Generates tickets for implementation

---

## Execution Cycle

Execution builds **what was planned**. The primary execution method is Ralph, the autonomous orchestrator. Manual execution is available as a fallback for individual tickets.

### Autonomous Execution with Ralph (`/ralph-loop`)

Ralph is the autonomous orchestrator that implements **all tickets from a plan** without human intervention. It takes a PRD and plan, iterates through every ticket, invokes Claude for implementation, validates the work, creates PRs, and merges them.

```
/ralph-loop
    │
    ├── Detect PRD and Plan (auto or from arguments)
    ├── Launch 1-4 parallel loops (configurable)
    │
    │   Each loop:
    │   ┌─────────────────────────────────────────┐
    │   │  Get next ticket (dependency-aware)       │
    │   │  → Invoke Claude engineer (TDD)           │
    │   │  → Validate against acceptance criteria   │
    │   │  → Create PR and auto-merge               │
    │   │  → Mark ticket done                       │
    │   │  → Repeat until no tickets remain         │
    │   └─────────────────────────────────────────┘
    │
    ├── Monitor progress (log files, stall detection)
    ├── Update docs/SYSTEM.md with completed work
    └── Cleanup (worktrees, git state)
```

**Key features:**
- **Concurrency** — Run 1-4 parallel loops using git worktrees with label-based ticket claiming (no collisions)
- **Smart model selection** — Routes simple tickets to Sonnet, complex ones to Opus based on configurable complexity threshold
- **Retry logic** — Validator-only retries before full engineer re-runs, up to N max attempts per ticket
- **Dependency awareness** — Respects ticket dependencies, processes in correct order
- **Crash recovery** — See `docs/guides/ralph-loop-crash-recovery.md` for recovery procedures

**Configuration** in `config.yaml`:
```yaml
ralph:
  sonnet_threshold: 2           # Complexity ≤2 = Sonnet, >2 = Opus
  max_attempts: 3               # Retries before blocking a ticket
  max_concurrent_loops: 4       # Parallel instances (1-4)
  engineer_timeout: 30          # Minutes per implementation
  validator_timeout: 10         # Minutes per validation
```

**Related commands:**
- `/ticket-reset {id}` — Reset a blocked ticket so Ralph can retry it

### Manual Execution (Per Ticket)

For individual tickets or when you want direct control:

```
1. CREATE BRANCH
   git checkout -b feature/TICKET-123-description

2. WRITE TESTS FIRST (TDD)
   - Write failing tests based on acceptance criteria
   - Tests define "done"

3. IMPLEMENT
   - Write code to make tests pass
   - Follow the plan's technical decisions

4. CREATE PR
   - One PR per ticket
   - Links to ticket ID
   - Includes test evidence

5. CLAUDE REVIEW
   - Automated review checks:
     - Tests pass
     - Lint passes
     - Build succeeds
     - Code matches plan intent

6. MERGE OR BLOCK
   - Pass → Auto-merge, move to next ticket
   - Fail → Flag as blocked for human attention
```

### Gitflow Process

```
main
  │
  └── feature/TICKET-123-user-auth
  │     └── PR #1 → merge
  │
  └── feature/TICKET-124-login-form
  │     └── PR #2 → merge
  │
  └── feature/TICKET-125-session-mgmt
        └── PR #3 → merge
```

- **One branch per ticket** - Keeps changes isolated
- **One PR per ticket** - Makes review focused
- **Merge to main** - After review passes
- **No batching** - Each ticket is independently shippable

### TDD Process

```
RED    → Write a failing test
GREEN  → Write minimal code to pass
REFACTOR → Clean up while tests pass
```

Every ticket follows this cycle:
1. Read acceptance criteria from ticket
2. Translate criteria into test cases
3. Run tests (they fail - RED)
4. Implement feature code
5. Run tests (they pass - GREEN)
6. Refactor if needed (tests still pass)
7. Commit and PR

### Automated Review

Claude reviews each PR checking:

| Check | Pass Criteria |
|-------|---------------|
| Tests | All tests pass |
| Lint | No lint errors |
| Build | Build succeeds |
| Coverage | New code has tests |
| Plan Alignment | Changes match plan intent |

**On Pass:** Auto-merge and proceed to next ticket

**On Fail:** Mark ticket as blocked with reason, continue to next ticket, flag for human review

### After All Tickets: Report, Review, Release

Once all tickets are complete and merged:

#### Execution Report (`/execution-report`)
Document what was implemented vs what was planned:
- Completed tasks
- Modified tasks (what changed and why)
- Challenges encountered
- Divergences from plan

#### System Review (`/system-review`)
Analyze process effectiveness:
- What worked well
- What could improve
- Process updates needed
- Template improvements

#### Release (`/release`)
Finalize the iteration:
- Update README with new features
- Tag the release in git
- Mark iteration complete

---

## Full Lifecycle Example

### Version 1: User Authentication

```bash
# PLANNING
/discover                    # "I need user authentication"
# → Creates docs/discovery/2025-01-15-v1-auth.md

/prd user-auth              # Generate PRD from discovery
# → Review acceptance criteria, approve PRD

/plan user-auth             # Generate technical plan
# → Review architecture, approve plan

/ticket                     # Create tickets from plan
# → TICKET-101: User model
# → TICKET-102: Registration endpoint
# → TICKET-103: Login endpoint
# → TICKET-104: Session management

# EXECUTION
/ralph-loop                 # Ralph implements all tickets
# → Launches parallel loops, implements, PRs, merges
# → Monitors progress, reports when done

# Or manually (fallback):
# /implement TICKET-101     # One ticket at a time
# /implement TICKET-102     # Next ticket

# FINALIZE
/execution-report           # Document what was built
/system-review              # Analyze process effectiveness
/release                    # Update README, tag v1.0

# v1.0 shipped!
```

### Version 2: OAuth Integration

```bash
# PLANNING (new cycle)
/discover                    # "Add Google/GitHub OAuth"
# → Creates docs/discovery/2025-02-20-v1.1-oauth.md

/prd oauth-integration      # New PRD for OAuth scope
/plan oauth-integration     # Technical plan for OAuth
/ticket                     # New tickets
# → TICKET-201: OAuth provider abstraction
# → TICKET-202: Google OAuth flow
# → TICKET-203: GitHub OAuth flow

# EXECUTION
/ralph-loop                 # Ralph handles all three tickets

# FINALIZE
/execution-report
/system-review
/release                    # Update README, tag v1.1

# v1.1 shipped!
```

---

## Prerequisites

### Required Tools

| Tool | Purpose | Install |
|------|---------|---------|
| `git` | Version control | `apt install git` |
| `gh` | GitHub CLI for PRs | `apt install gh` |
| `node` | Runtime | Via nvm or apt |
| `bun` | Hooks runtime | `curl -fsSL https://bun.sh/install \| bash` |
| `jq` | JSON parsing | `apt install jq` |
| `python3` | Ralph orchestrator | 3.10+ required |

### Optional Tools

| Tool | Purpose | Install |
|------|---------|---------|
| Playwright MCP | Browser playtesting (`/playtest`, `/playtest-loop`) | Configure in `.mcp.json` |

### PM Tool Configuration

Set your PM tool in `config.yaml`:

```yaml
pm:
  tool: trello  # trello | asana | github | linear | none
```

Then configure credentials in `.env`:

| Tool | Required Variables |
|------|-------------------|
| Trello | `TRELLO_API_KEY`, `TRELLO_TOKEN`, `TRELLO_BOARD_ID` |
| Asana | `ASANA_ACCESS_TOKEN`, `ASANA_WORKSPACE_ID`, `ASANA_PROJECT_ID` |
| GitHub | `gh auth login` (no env vars needed) |
| Linear | `LINEAR_API_KEY`, `LINEAR_TEAM_ID` |

---

## Configuration

### config.yaml

```yaml
pm:
  tool: trello                 # PM tool selection

dev:
  test_command: "npm test"     # Your test runner
  lint_command: "npm run lint" # Your linter
  build_command: "npm run build"

git:
  default_branch: main
  branch_prefix:
    feature: "feature/"

ralph:
  sonnet_threshold: 2          # Complexity ≤2 = Sonnet, >2 = Opus
  max_attempts: 3              # Retries before blocking
  max_concurrent_loops: 4      # Parallel instances (1-4)
  engineer_timeout: 30         # Minutes per implementation
  validator_timeout: 10        # Minutes per validation
```

### .env

```bash
# Copy from .env.example and fill in your values
cp .env.example .env
```

---

## File Structure

```
.
├── .claude/
│   ├── agents/             # Agent definitions (architect, engineer)
│   ├── commands/           # Slash command definitions
│   ├── hooks/              # Security and audit hooks
│   ├── ralph/              # Ralph autonomous orchestrator
│   │   ├── ralph           # Entry point (bash wrapper)
│   │   ├── cli.py          # CLI interface
│   │   ├── commands/       # Orchestrator, concurrency, PR flow, validation
│   │   └── core/           # State, PM tools, git, config
│   └── scripts/            # Utility scripts (create-project, sync-framework)
├── docs/
│   ├── discovery/          # Versioned discovery docs (one per iteration)
│   ├── prds/               # PRD documents (one per feature)
│   ├── plans/              # Technical plans (one per feature)
│   ├── execution-reports/  # Implementation vs plan records
│   ├── system-reviews/     # Process improvement analysis
│   ├── research/           # Research findings
│   ├── rca/                # Root cause analysis documents
│   ├── guides/             # How-to guides (crash recovery, multi-instance Ralph)
│   ├── templates/          # Document templates
│   └── state/              # Ralph state files (per ticket)
├── config.yaml             # Project configuration
├── .env                    # Secrets (gitignored)
├── CLAUDE.md               # Orchestrator instructions
├── WORKFLOW.md             # Detailed workflow reference
└── README.md               # This file (updated after each release)
```

---

## Why This Works

1. **Separation of concerns** - Planning is creative; execution is mechanical
2. **Approval gates** - Humans approve direction; automation handles implementation
3. **Traceability** - Every line of code traces to a ticket, plan, PRD, and requirement
4. **Repeatability** - Same process for v1, v2, v3...
5. **Quality enforcement** - TDD and automated review catch issues early
6. **Reduced bottlenecks** - Claude reviews mean no waiting for humans on routine PRs
7. **Autonomous execution** - Ralph can implement entire plans unattended with parallel processing

---

## License

MIT License - see [LICENSE](LICENSE) for details.
