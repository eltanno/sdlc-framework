# SDLC Automation Framework

A repeatable software development lifecycle for Claude Code that enforces quality gates, maintains traceability, and produces working software through structured planning and automated execution.

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
│                          (Build & Ship)                                  │
│                                                                          │
│   For each ticket:                                                       │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ Branch ──→ TDD ──→ Implement ──→ PR ──→ Review ──→ Merge       │   │
│   │                                           ↓                     │   │
│   │                                    Claude reviews               │   │
│   │                                    Auto-merge on pass           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Output: Merged PRs, tested code, completed tickets                    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key principle:** Planning requires human judgment and approval. Execution follows the approved plan mechanically.

---

## Planning Cycle

Planning defines **what** to build and **how** to build it. Each phase produces an artifact that must be approved before proceeding.

### Phase 1: Discovery (`/discover`)

Interactive conversation to understand requirements.

- **Input:** User's idea or problem
- **Output:** `docs/discovery.md` - Living document capturing the full vision
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

Execution builds **what was planned**. It follows gitflow and TDD practices, producing one PR per ticket.

### For Each Ticket

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

---

## Full Lifecycle Example

### Version 1: User Authentication

```bash
# PLANNING
/discover                    # "I need user authentication"
# → Discuss requirements, approve discovery.md

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
/implement TICKET-101       # TDD implementation
# → Branch, test, implement, PR, review, merge

/implement TICKET-102       # Next ticket
# → Branch, test, implement, PR, review, merge

# ... continue until all tickets complete

# v1.0 shipped!
```

### Version 2: OAuth Integration

```bash
# PLANNING (new cycle)
/discover                    # "Add Google/GitHub OAuth"
# → Update discovery.md with OAuth requirements

/prd oauth-integration      # New PRD for OAuth scope
/plan oauth-integration     # Technical plan for OAuth
/ticket                     # New tickets
# → TICKET-201: OAuth provider abstraction
# → TICKET-202: Google OAuth flow
# → TICKET-203: GitHub OAuth flow

# EXECUTION
/implement TICKET-201
/implement TICKET-202
/implement TICKET-203

# v2.0 shipped!
```

---

## Commands Reference

### Planning Commands

| Command | Purpose | Output |
|---------|---------|--------|
| `/discover` | Interactive requirements gathering | `docs/discovery.md` |
| `/prd {name}` | Generate PRD with acceptance criteria | `docs/prds/YYYY-MM-DD-{name}.md` |
| `/plan {name}` | Generate technical implementation plan | `docs/plans/YYYY-MM-DD-{name}.md` |
| `/ticket` | Create tickets in PM tool | Ticket IDs in PM tool |

### Execution Commands

| Command | Purpose | Output |
|---------|---------|--------|
| `/implement {ticket}` | TDD implementation of ticket | Feature branch + PR |
| `/pr {ticket}` | Create pull request | Open PR linked to ticket |
| `/validate {ticket}` | Pre-merge validation | Pass/fail status |

### Utility Commands

| Command | Purpose |
|---------|---------|
| `/status` | Show current workflow state |
| `/whats-next` | Recommend next action |
| `/research {topic}` | Technical research (anytime) |
| `/hotfix` | Emergency fix (abbreviated flow) |
| `/guide` | Help and orientation |

---

## Quick Start

1. Clone/copy this framework into your project
2. Run the setup script:
   ```bash
   ./claude-setup.sh
   ```
3. Edit `.env` with your API keys
4. Configure your PM tool MCP in Claude Code
5. Run `/discover` to start your first planning cycle

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
│   ├── commands/           # Slash command definitions
│   ├── hooks/              # Security and audit hooks
│   └── scripts/            # Utility scripts
├── docs/
│   ├── discovery.md        # Living requirements document
│   ├── prds/               # PRD documents (one per feature)
│   ├── plans/              # Technical plans (one per feature)
│   └── research/           # Research findings
├── config.yaml             # Project configuration
├── .env                    # Secrets (gitignored)
├── CLAUDE.md               # Orchestrator instructions
├── WORKFLOW.md             # Detailed workflow reference
└── README.md               # This file
```

---

## Why This Works

1. **Separation of concerns** - Planning is creative; execution is mechanical
2. **Approval gates** - Humans approve direction; automation handles implementation
3. **Traceability** - Every line of code traces to a ticket, plan, PRD, and requirement
4. **Repeatability** - Same process for v1, v2, v3...
5. **Quality enforcement** - TDD and automated review catch issues early
6. **Reduced bottlenecks** - Claude reviews mean no waiting for humans on routine PRs

---

## License

MIT License - see [LICENSE](LICENSE) for details.
