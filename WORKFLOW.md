# SDLC Workflow Reference

This document provides comprehensive workflow documentation for the SDLC automation framework.

## Workflow Overview

The framework enforces a phase-based workflow divided into two major stages:

### The Two Stages

| Stage | Phases | Purpose | Output |
|-------|--------|---------|--------|
| **Planning** | discover → prd → plan → ticket | Define WHAT and HOW | Approved plan + tickets in PM |
| **Execution** | implement → pr → validate → report → review → release | Build, review, ship | Merged code + updated README |

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              PLANNING                                                        │
│                                         (What & How)                                                         │
│                                                                                                              │
│   ┌───────┐     ┌──────────┐     ┌─────┐     ┌──────┐     ┌────────┐                                        │
│   │ Prime │ --> │ Discover │ --> │ PRD │ --> │ Plan │ --> │ Ticket │ ──────────────────────┐               │
│   └───────┘     └──────────┘     └─────┘     └──────┘     └────────┘                       │               │
│                                                                                             │               │
│   Outputs: docs/discovery/*.md, docs/prds/*.md, docs/plans/*.md, tickets in PM             │               │
│   Human approval required at: Discovery, PRD, Plan                                          │               │
└─────────────────────────────────────────────────────────────────────────────────────────────│───────────────┘
                                                                                              │
                                                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              EXECUTION                                                       │
│                                      (Build, Review & Ship)                                                  │
│                                                                                                              │
│   ┌───────────┐     ┌────┐     ┌──────────┐     ┌────────┐     ┌────────┐     ┌─────────┐                   │
│   │ Implement │ --> │ PR │ --> │ Validate │ --> │ Report │ --> │ Review │ --> │ Release │                   │
│   └───────────┘     └────┘     └──────────┘     └────────┘     └────────┘     └─────────┘                   │
│                                                                                     │                        │
│   Can be run autonomously (ralph) or human-managed                                  │                        │
│   Outputs: Feature branch, tests, code, merged PR, updated README                   │                        │
└─────────────────────────────────────────────────────────────────────────────────────│────────────────────────┘
                                                                                      │
                                                                                      ▼
                                                                           ┌──────────────────┐
                                                                           │  Next Iteration  │
                                                                           │   /discover...   │
                                                                           └──────────────────┘
```

### Key Boundary

**Planning ends when:** You have tickets with IDs in your PM tool (or PROGRESS.md)
**Execution begins when:** You pick up a ticket and start coding

### Command Flow

```
PLANNING PHASES:
/prime → /discover → /prd → /plan → /ticket
   │         │         │       │        │
   ▼         ▼         ▼       ▼        ▼
 (self)   (self)   architect architect haiku
context  interactive                    │
                                        ↓
                              [Tickets ready in PM]
                                        ↓
EXECUTION PHASES:
/implement → /pr → /validate → /execution-report → /system-review → /release
     │        │        │              │                   │              │
     ▼        ▼        ▼              ▼                   ▼              ▼
 engineer  haiku  engineer         (self)              (self)         (self)
                                  document       process review    update README
```

### Bug Fix Workflows

**Choose based on severity and complexity:**

```
CRITICAL (Production down):
/prime → /hotfix → /validate
   │        │          │
   ▼        ▼          ▼
context  engineer  engineer
   (abbreviated - fix first, document later)

COMPLEX (Root cause unclear):
/prime → /rca → ticket → branch → fix → /pr → /validate
   │       │       │        │       │      │        │
   ▼       ▼       ▼        ▼       ▼      ▼        ▼
context  analysis Trello  git   engineer haiku  engineer

STANDARD (Root cause clear):
ticket → branch → fix → /pr → /validate
   │        │       │      │        │
   ▼        ▼       ▼      ▼        ▼
 Trello   git   engineer haiku  engineer
```

### Autonomous Workflow (Ralph)

```
/ralph-prd [prd-path]
       │
       ▼
   ┌─────────────────────────────────────────────────┐
   │  RALPH LOOP                                     │
   │                                                 │
   │  /whats-next → delegate engineer → validate →  │
   │       ↑           (implement)        commit    │
   │       │                                 │      │
   │       └─────────── next ticket ─────────┘      │
   │                                                 │
   │  Exit: PRD_COMPLETE or NEEDS_HUMAN_REVIEW      │
   └─────────────────────────────────────────────────┘
```

---

## Document Hierarchy

The framework uses a clear hierarchy from iteration scope down to individual tasks:

### The Hierarchy Model

```
docs/discovery/
├── YYYY-MM-DD-v1-initial.md       ← v1 scope and requirements
├── YYYY-MM-DD-v1.1-oauth.md       ← v1.1 scope and requirements
└── YYYY-MM-DD-v2-admin.md         ← v2 scope and requirements
      ↓
    docs/prds/YYYY-MM-DD-*.md      ← Feature PRDs for each iteration
      ↓
    docs/plans/YYYY-MM-DD-*.md     ← Technical plans
```

| Document | Scope | Analogy | Status |
|----------|-------|---------|--------|
| **Discovery** | One iteration/version | "Volume" | Versioned (one per planning cycle) |
| **PRD** | One feature/epic | "Chapter" | Point-in-time (one per feature) |
| **Plan** | Technical approach for PRD | "Chapter outline" | Point-in-time (one per PRD) |
| **Tickets** | Individual tasks | "Paragraphs" | Created from plan |
| **README** | Current product state | "Cover summary" | Updated after each release |

### Key Principles

1. **One Discovery per iteration** - Each planning cycle (v1, v1.1, v2) has its own discovery
2. **Multiple PRDs per discovery** - Each PRD focuses on a single feature within that iteration
3. **PRDs reference Discovery** - Each PRD connects back to its iteration's discovery
4. **Plans implement PRDs** - Each plan defines how to build what a PRD specified
5. **README reflects reality** - After release, README is updated with what was shipped

### Document Flow

```
docs/
├── discovery/
│   ├── YYYY-MM-DD-v1-initial.md   # v1 scope (VOLUME 1)
│   ├── YYYY-MM-DD-v1.1-oauth.md   # v1.1 scope (VOLUME 1.1)
│   └── YYYY-MM-DD-v2-admin.md     # v2 scope (VOLUME 2)
├── prds/
│   ├── YYYY-MM-DD-feature-1.md    # Feature PRD (CHAPTER 1)
│   ├── YYYY-MM-DD-feature-2.md    # Feature PRD (CHAPTER 2)
│   └── YYYY-MM-DD-feature-3.md    # Feature PRD (CHAPTER 3)
├── plans/
│   ├── YYYY-MM-DD-feature-1.md    # How to build feature 1
│   ├── YYYY-MM-DD-feature-2.md    # How to build feature 2
│   └── PROGRESS.md                 # Implementation tracking
├── research/
│   └── YYYY-MM-DD-topic.md        # Technical research
├── legacy/                         # Output from /analyze-codebase
│   ├── STACK.md                   # Languages, frameworks, runtime
│   ├── ARCHITECTURE.md            # System patterns, data flow
│   ├── STRUCTURE.md               # Directory organization
│   ├── CONVENTIONS.md             # Code style standards
│   ├── TESTING.md                 # Test frameworks, coverage
│   ├── INTEGRATIONS.md            # External services, APIs
│   ├── CONCERNS.md                # Technical debt, fragile areas
│   └── NEXT-STEPS.md              # Prioritized improvements
├── rca/
│   └── YYYY-MM-DD-issue.md        # Root cause analysis for bugs
├── execution-reports/
│   └── YYYY-MM-DD-feature.md      # Implementation vs plan comparison
├── system-reviews/
│   └── YYYY-MM-DD-feature.md      # Process meta-analysis
└── templates/
    ├── discovery-template.md
    ├── prd-template.md
    └── plan-template.md
```

### Document Relationships

```
Discovery v1 (iteration scope)           Discovery v1.1 (next iteration)
    ↓                                          ↓
   PRD 1 (Feature A)     PRD 2 (Feature B)    PRD 3 (OAuth)
    ├── Features              ├── Features         ├── Features
    ├── Acceptance Criteria   ├── Acceptance       ├── Acceptance Criteria
    └── Ticket Definitions    └── Tickets          └── Ticket Definitions
         ↓                         ↓                    ↓
        Plan 1                   Plan 2               Plan 3
         ├── Technical Architecture
         ├── Implementation Phases
         └── Ticket Breakdown (with IDs)
              ↓
             Implementation
              ↓
             Release → Update README
```

---

## Phase Details

---

## PLANNING PHASES

> **Planning defines WHAT to build and HOW to build it.**
> Human approval is required at key gates (Discovery, PRD, Plan).
> Planning ends when tickets are created in your PM tool.

---

### 0. Prime Phase (`/prime`)

**Load project context before any work begins**

- **Who runs it**: You (orchestrator) - self-executed
- **Input**: Current project state
- **Output**: Context summary (displayed, not persisted)
- **Purpose**: Ensure understanding of codebase, conventions, and current state

**Prime is a context-loading step** - run before `/plan`, `/implement`, `/hotfix`, or any significant work.

**The Prime Process:**
1. Project structure (file tree, directories)
2. Documentation review (CLAUDE.md, README, discovery, PRDs, plans)
3. Technical context (entry points, configs, schemas)
4. Current state (git status, recent commits)
5. Active work (in-progress plans, open PRs)

**When to Prime:**
| Situation | Action |
|-----------|--------|
| Starting new session | Always prime |
| Switching tasks | Prime if context changed |
| Before `/plan` | Prime to understand current state |
| Before `/implement` | Prime if >1 hour since last prime |
| Before `/hotfix` | Quick prime (steps 4-5 minimum) |

---

### 1. Discovery Phase (`/discover`)

**Interactive requirements gathering conversation for an iteration**

- **Who runs it**: You (orchestrator) - interactive with user
- **Input**: User's vision and needs for this iteration/version
- **Output**: `docs/discovery/YYYY-MM-DD-{version-or-scope}.md` - Versioned document capturing iteration requirements
- **Status**: NOT STARTED → IN PROGRESS → READY FOR PLANNING
- **Purpose**: Understand what the user wants to build in this iteration and why

**Discovery is interactive** - you conduct it yourself as a conversation with the user. This is NOT delegated to an agent.

**Each planning cycle gets its own discovery:**
- `docs/discovery/2025-01-15-v1-core.md` - Initial v1 features
- `docs/discovery/2025-02-20-v1.1-oauth.md` - OAuth enhancement
- `docs/discovery/2025-04-10-v2-admin.md` - Admin dashboard

**Discovery vs Research:**

| `/discover` | `/research` |
|-------------|-------------|
| **Interactive** conversation | **Autonomous** investigation |
| You conduct it yourself | Delegate to general-purpose agent |
| User explains their vision | Agent explores topic independently |
| Output: `docs/discovery/YYYY-MM-DD-*.md` | Output: `docs/research/YYYY-MM-DD-*.md` |
| Versioned per iteration | Point-in-time findings |

---

### 2. PRD Phase (`/prd`)

**Create formal Product Requirements Document**

- **Who runs it**: Architect agent
- **Prerequisites**: Approved discovery (or explicit skip)
- **Input**: Discovery document, user requirements
- **Output**: `docs/prds/YYYY-MM-DD-{feature}.md`
- **Status**: DRAFT → APPROVED
- **Contains**:
  - Executive summary
  - Functional requirements with acceptance criteria
  - Non-functional requirements (performance, security)
  - User stories
  - Technical specifications
  - Ticket definitions (IDs = TBD)
  - Testing requirements
  - Rollout/rollback plan

**Key Principle**: The PRD defines **WHAT** to build, not **HOW** to build it.

---

### 3. Plan Phase (`/plan`)

**Create technical implementation plan**

- **Who runs it**: Architect agent
- **Prerequisites**: Approved PRD
- **Input**: PRD, codebase exploration
- **Output**: `docs/plans/YYYY-MM-DD-{feature}.md`
- **Status**: DRAFT → APPROVED
- **Contains**:
  - Technical architecture and approach
  - Key design decisions with rationale
  - Component breakdown
  - Data flow diagrams
  - File structure
  - Dependencies
  - Implementation phases with exit criteria
  - Ticket breakdown with estimates
  - Test strategy
  - Risks and mitigations

**Key Principle**: The plan defines **HOW** to build what the PRD specified.

---

### 4. Ticket Phase (`/ticket`)

**Create tasks from plan in your PM tool**

- **Who runs it**: Haiku agent (fast, simple task)
- **Prerequisites**: Approved plan
- **Input**: Plan document with ticket table
- **Output**: Tasks created in PM tool (Trello, Asana, GitHub, Linear, or local PROGRESS.md), plan updated with ticket IDs
- **Creates**: One task per ticket row in the plan

**This is the final Planning phase.** Once tickets exist with IDs, Execution can begin.

---

## EXECUTION PHASES

> **Execution builds and ships the planned work.**
> Can be run autonomously (ralph-prd) or human-managed (Boris-style parallel sessions).
> Execution ends when code is merged.

---

### 5. Implement Phase (`/implement`)

**TDD implementation of a ticket**

- **Who runs it**: Engineer agent
- **Prerequisites**: Ticket ID from plan
- **Input**: Ticket details, acceptance criteria from PRD, technical approach from plan
- **Output**: Code + tests on feature branch
- **Workflow**:
  1. Create feature branch (`feature/ASANA-{id}-{description}`)
  2. **RED**: Write failing tests
  3. **GREEN**: Write code to pass tests
  4. **REFACTOR**: Clean up while tests stay green
  5. Verify: tests pass, lint passes, no debug code
  6. Commit with structured message

**Key Principle**: Tests are written **before** implementation code. No exceptions.

---

### 6. PR Phase (`/pr`)

**Create GitHub pull request**

- **Who runs it**: Haiku agent (fast, simple task)
- **Prerequisites**: Committed code with passing tests
- **Input**: Feature branch, ticket ID
- **Output**: GitHub pull request linked to ticket
- **Creates**: PR with description, links to PRD/plan, test results

---

### 7. Validate Phase (`/validate`)

**Pre-merge validation**

- **Who runs it**: Engineer agent
- **Prerequisites**: Open pull request
- **Input**: PR details, acceptance criteria from PRD
- **Output**: Validation report
- **Checks**:
  - All tests pass
  - Linting passes
  - Acceptance criteria met
  - No security issues
  - Performance acceptable
  - Documentation complete

---

### 8. Execution Report (`/execution-report`)

**Document what was implemented versus what was planned**

- **Who runs it**: You (orchestrator) - self-executed
- **Prerequisites**: Completed implementation (after `/implement`)
- **Input**: Plan document, git history, files changed
- **Output**: `docs/execution-reports/YYYY-MM-DD-{feature}.md`
- **Documents**:
  - Completed tasks
  - Modified tasks (what changed and why)
  - Skipped tasks (and reasoning)
  - Validation results (lint, tests, build)
  - Challenges encountered
  - Divergences from plan (intentional vs unintentional)

**Key Principle**: Create a record for process improvement analysis.

---

### 9. System Review (`/system-review`)

**Analyze process effectiveness, not code quality**

- **Who runs it**: You (orchestrator) - self-executed
- **Prerequisites**: Execution report
- **Input**: Plan, PRD, execution report, git history
- **Output**: `docs/system-reviews/YYYY-MM-DD-{feature}.md`
- **Analyzes**:
  - Good divergences (keep/encourage)
  - Bad divergences (prevent in future)
  - Root cause categories (unclear planning, missing context, etc.)
  - Pattern compliance
- **Generates**:
  - CLAUDE.md updates
  - Command updates
  - Template updates
  - New automation
  - Reference docs

**Key Principle**: "You're not looking for bugs in the code - you're looking for bugs in the process."

---

### 10. Release Phase (`/release`)

**Update README and finalize the release**

- **Who runs it**: You (orchestrator) - self-executed
- **Prerequisites**: System review complete (or skipped with approval)
- **Input**: Discovery doc, PRD, execution report, what was actually shipped
- **Output**: Updated README.md reflecting current product state
- **Actions**:
  1. Review what was shipped in this iteration
  2. Update README.md with new features/changes
  3. Update any other user-facing documentation
  4. Tag the release in git (if applicable)
  5. Mark iteration as complete

**Why Release matters:**
- README is the "source of truth" for what the software actually does
- Discovery docs capture what was *planned* - README captures what *exists*
- New users/contributors read README first, not discovery docs
- Closes the loop: Plan → Build → Review → Document

**README update should include:**
- New features added
- Changed behaviors
- New configuration options
- Updated prerequisites (if any)
- Version bump (if using semver)

**Key Principle**: The iteration isn't complete until the documentation reflects reality.

---

## Prerequisites by Phase

### Utility Commands (No Prerequisites)

| Phase | Requires |
|-------|----------|
| `/guide` | None - help for new users anytime |
| `/whats-next` | None - run anytime to get oriented |
| `/prime` | None - run before any significant work |
| `/research` | None - can run anytime |
| `/analyze-codebase` | None - run on any existing codebase |
| `/rca` | Bug report or issue to investigate |

### Planning Phases

| Phase | Requires | Output |
|-------|----------|--------|
| `/discover` | None - can start anytime | `docs/discovery/YYYY-MM-DD-*.md` |
| `/prd` | Discovery status = READY FOR PLANNING (or explicit skip) | `docs/prds/*.md` |
| `/plan` | Approved PRD | `docs/plans/*.md` |
| `/ticket` | Approved plan | Tickets in PM tool |

### Execution Phases

| Phase | Requires | Output |
|-------|----------|--------|
| `/implement` | Plan with ticket IDs | Code + tests on branch |
| `/pr` | Passing tests, committed code | Pull request |
| `/validate` | Open PR | Validation report |
| `/execution-report` | All PRs merged, validation passed | `docs/execution-reports/*.md` |
| `/system-review` | Execution report | `docs/system-reviews/*.md` |
| `/release` | System review complete | Updated README.md |
| `/ralph-prd` | Approved plan with ticket IDs + clean git state | Autonomous execution |

**Check prerequisites before proceeding. If missing, guide user to correct phase.**

---

## Bug Handling Workflows

Bugs are handled differently based on severity and whether the root cause is known.

### Severity Classification

| Severity | Definition | Workflow |
|----------|------------|----------|
| **Critical** | Production down, data loss, security breach | `/hotfix` (abbreviated) |
| **Complex** | Root cause unclear, needs investigation | `/rca` → Standard |
| **Standard** | Root cause clear, straightforward fix | Standard (ticket → branch → fix) |

### Standard Bug Workflow

For bugs where the root cause is already understood:

```
1. Create ticket (Trello/Asana) documenting:
   - Bug description
   - Root cause
   - Proposed fix
   - Affected files

2. Create branch:
   git checkout -b bugfix/{ticket-id}-{short-description}

3. Implement fix:
   - Write failing test that reproduces bug
   - Fix the bug
   - Verify test passes
   - Run full test suite

4. Create PR and validate:
   /pr → /validate
```

**Branch naming:** `bugfix/BUG-{id}-{description}` or `bugfix/{description}` if no ticket system.

### Complex Bug Workflow (with RCA)

For bugs where root cause needs investigation:

```
/prime → /rca → (then Standard workflow)
```

1. **Root Cause Analysis (`/rca`)**
   - Gather issue details
   - Reproduce the issue
   - Identify root cause
   - Design the fix
   - Output: `docs/rca/YYYY-MM-DD-{issue}.md`

2. **Standard workflow** once RCA is complete

### Critical/Hotfix Workflow

For production emergencies only:

```
/prime → /hotfix → /validate
```

- Skip discovery/PRD/plan
- Still requires: tests, PR
- Document with RCA **after** fix is deployed
- Delegate to engineer with urgency flag

**Key Principle**: Separate analysis from implementation. Understand the problem before coding the fix.

### When to Use Each Workflow

| Situation | Use |
|-----------|-----|
| App crashes on button click, cause obvious from stack trace | Standard |
| Data corruption, unclear what's causing it | Complex (RCA) |
| Production site is down | Critical (Hotfix) |
| Test passes but feature doesn't work | Standard or Complex |
| Security vulnerability reported | Critical (Hotfix) |
| Performance degradation, unclear source | Complex (RCA) |

---

## Autonomous Workflow

For hands-off implementation of approved PRDs, use the ralph-driven autonomous workflow:

```
/ralph-prd docs/prds/YYYY-MM-DD-feature.md
```

**How it works:**

1. Ralph reads the PRD and corresponding plan
2. Runs `/whats-next` to find the next ticket
3. Delegates implementation to engineer agent
4. Validates (tests, lint) after each ticket
5. Commits, pushes, creates PR
6. Loops back to step 2 until all tickets complete

**When to use:**
- PRD is approved with clear acceptance criteria
- Plan has ticket IDs populated
- Tickets are well-defined with testable outcomes
- You can walk away and check back later

**When NOT to use:**
- Requirements are unclear or evolving
- Design decisions still needed
- First time implementing a new pattern
- Debugging production issues

**See:** `docs/guides/ralph-with-tickets.md` for detailed usage guide.

---

## Optional: Research Phase

The `/research` command can be used at any time for autonomous technical investigation:

```bash
/research "topic to investigate"
```

Output: `docs/research/YYYY-MM-DD-{topic}.md`

---

## Optional: Analyze Codebase

The `/analyze-codebase` command performs deep, non-destructive analysis of any existing codebase and produces comprehensive documentation for legacy project adoption.

```bash
/analyze-codebase
```

**Purpose:** Enable teams with existing codebases to understand what they have before planning improvements. This command produces structured documentation that serves as the foundation for SDLC adoption.

**How it works:**

1. **Optional Q&A** - Clarifying questions to focus the analysis (can be skipped)
   - "What's the main purpose of this project?"
   - "Any specific areas of concern or focus?"
   - "Known pain points or technical debt?"

2. **Parallel Analysis** - 7 independent analysis agents run concurrently:
   - Stack Analyzer → `docs/legacy/STACK.md`
   - Architecture Analyzer → `docs/legacy/ARCHITECTURE.md`
   - Structure Analyzer → `docs/legacy/STRUCTURE.md`
   - Conventions Analyzer → `docs/legacy/CONVENTIONS.md`
   - Testing Analyzer → `docs/legacy/TESTING.md`
   - Integrations Analyzer → `docs/legacy/INTEGRATIONS.md`
   - Concerns Analyzer → `docs/legacy/CONCERNS.md`

3. **Synthesis** - After all analyses complete, a synthesizer creates:
   - `docs/legacy/NEXT-STEPS.md` - Prioritized improvements (P1/P2/P3) and SDLC workflow guidance

**Output:** 8 Markdown documents in `docs/legacy/`

```
docs/legacy/
├── STACK.md           # Languages, frameworks, runtime
├── ARCHITECTURE.md    # System patterns, data flow
├── STRUCTURE.md       # Directory organization
├── CONVENTIONS.md     # Code style standards
├── TESTING.md         # Test frameworks, coverage
├── INTEGRATIONS.md    # External services, APIs
├── CONCERNS.md        # Technical debt, fragile areas
└── NEXT-STEPS.md      # Prioritized improvements + SDLC guidance
```

**Key characteristics:**
- **Non-destructive** - Read-only analysis, never modifies source files
- **Language-agnostic** - Works with any programming language
- **Parallel execution** - Independent analyses run concurrently for speed
- **Actionable output** - Each document includes recommendations
- **SDLC integration** - NEXT-STEPS.md guides users to `/discover` for improvements

**When to use:**
- Onboarding to a legacy codebase
- Planning SDLC adoption for existing projects
- Technical debt assessment
- Understanding unfamiliar code before modifications

**When NOT to use:**
- Greenfield projects (nothing to analyze yet)
- Projects already documented via SDLC workflow

---

## Document Locations (State Persistence)

Workflow state persists in files, not context:

| Phase | Artifact Location | Status Field | Scope |
|-------|-------------------|--------------|-------|
| Discovery | `docs/discovery/YYYY-MM-DD-{version}.md` | NOT STARTED → IN PROGRESS → READY FOR PLANNING | **One iteration/version** |
| Research | `docs/research/YYYY-MM-DD-{topic}.md` | (point-in-time) | Technical investigations |
| Analyze Codebase | `docs/legacy/*.md` (8 files) | (point-in-time) | Legacy codebase analysis |
| RCA | `docs/rca/YYYY-MM-DD-{issue}.md` | ANALYZING → FIX PROPOSED → VERIFIED | Bug investigation |
| PRD | `docs/prds/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | **One feature/epic per PRD** |
| Plan | `docs/plans/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | Technical approach for one PRD |
| Tickets | Updated in plan (ticket IDs added) | IDs populated | Individual tasks from plan |
| Release | `README.md` (updated) | (current product state) | What the software actually does |
| Execution Report | `docs/execution-reports/YYYY-MM-DD-{feature}.md` | COMPLETE / PARTIAL / BLOCKED | Implementation record |
| System Review | `docs/system-reviews/YYYY-MM-DD-{feature}.md` | (point-in-time) | Process improvement |

**Reading artifacts gives you state. Writing artifacts persists state.**

---

## Workflow Status Tracking

The framework maintains state in document status fields:

```markdown
**Status:** DRAFT | APPROVED
```

Prerequisites are enforced by checking these status fields before proceeding to the next phase.

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
Scope: component or area affected
Ticket: reference to task tracker (Trello, Jira, etc.)

Examples:
- feat(auth): add JWT token refresh endpoint [TASK-123]
- fix(api): handle null user in profile response [TASK-456]
- test(user): add integration tests for signup flow [TASK-789]
- refactor(db): extract connection pooling to module [TASK-101]
- docs(readme): update setup instructions
```

Note: Ticket ID is optional for docs/chore commits that aren't tied to a specific task.

---

## Key Principles

1. **Context First** - Always prime before significant work
2. **Plan Before Code** - Never skip to implementation without a plan
3. **Test First** - Write failing tests before implementation
4. **Phase Gates** - Each phase requires approval before proceeding
5. **Document Everything** - All decisions captured in version-controlled docs
6. **Quality Gates** - Tests and linting must pass before merge
7. **Traceability** - Every commit links to a ticket, every ticket to a PRD
8. **Analyze Before Fix** - Use RCA for bugs before implementing fixes
9. **Process Improvement** - Execution reports and system reviews close the feedback loop
10. **COMMIT ARTIFACTS IMMEDIATELY** - Every document must be committed before proceeding (see below)

---

## CRITICAL: Artifact Commit Rule

> **⚠️ MANDATORY: Every artifact MUST be committed immediately after creation.**

Artifacts are the foundation of the entire workflow. Untracked files are NOT persisted state - they can be lost during branch operations. This rule is NON-NEGOTIABLE.

### The Rule

| Phase | Creates | MUST Commit Before Proceeding |
|-------|---------|-------------------------------|
| `/discover` | `docs/discovery/*.md` | ✅ `git add docs/discovery/ && git commit` |
| `/prd` | `docs/prds/*.md` | ✅ `git add docs/prds/ && git commit` |
| `/plan` | `docs/plans/*.md` | ✅ `git add docs/plans/ && git commit` |
| `/research` | `docs/research/*.md` | ✅ `git add docs/research/ && git commit` |
| `/rca` | `docs/rca/*.md` | ✅ `git add docs/rca/ && git commit` |
| `/release` | `README.md` | ✅ `git add README.md && git commit` |

### Commit Message Format

```bash
git add docs/
git commit -m "docs({artifact-type}): create {name}"
```

Examples:
```bash
git commit -m "docs(discovery): create Local Todo App"
git commit -m "docs(prd): create todo-app-core-v1"
git commit -m "docs(plan): create plan for todo-app-core-v1"
```

### Pre-Implementation Verification

**Before delegating ANY implementation work**, verify documents are committed:

```bash
# Must show "nothing to commit" for docs/
git status docs/

# If untracked files exist, STOP and commit them first
git add docs/
git commit -m "docs(workflow): commit artifacts before implementation"
```

### Why This Matters

1. **Branch operations can lose untracked files** - When creating feature branches, untracked directories may not persist
2. **Agents work on feature branches** - Each engineer agent creates/switches branches
3. **Documents ARE the state** - If they're not committed, the workflow has no foundation
4. **Recovery is impossible** - Untracked files have no git history to recover from

### Enforcement

The orchestrator MUST:
1. Commit artifacts immediately after each phase completes
2. Verify `git status docs/` shows clean before delegating to engineers
3. Never proceed to `/implement` with uncommitted docs

Engineer agents MUST:
1. Check that required docs exist and are committed at start of work
2. Refuse to proceed if docs are missing (request orchestrator to fix)

**If you lose documents due to uncommitted state, you have violated this rule.**

---

## Templates

Templates available in `docs/templates/`:
- `discovery-template.md` - Discovery document template
- `prd-template.md` - PRD template
- `plan-template.md` - Technical plan template
- `rca-template.md` - Root cause analysis template
- `execution-report-template.md` - Execution report template
- `system-review-template.md` - System review template

Agents should use these as starting points.
