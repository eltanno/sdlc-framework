# SDLC Workflow Reference

This document provides comprehensive workflow documentation for the SDLC automation framework.

## Workflow Overview

The framework enforces a phase-based workflow where each phase has clear inputs, outputs, and prerequisites:

```
┌───────┐     ┌──────────┐     ┌─────┐     ┌──────┐     ┌────────┐     ┌───────────┐     ┌────┐     ┌──────────┐
│ Prime │ --> │ Discover │ --> │ PRD │ --> │ Plan │ --> │ Ticket │ --> │ Implement │ --> │ PR │ --> │ Validate │
└───────┘     └──────────┘     └─────┘     └──────┘     └────────┘     └───────────┘     └────┘     └──────────┘
                                                                              │
                                                                              ▼
                                                              ┌──────────────────────────────┐
                                                              │ Execution Report → System    │
                                                              │ Review (Process Improvement) │
                                                              └──────────────────────────────┘
```

### The PIV Loop

The framework follows the **PIV Loop** methodology: **Prime → Implement → Validate**

```
/prime → /discover → /prd → /plan → /ticket → /implement → /pr → /validate
   │         │         │       │        │          │        │        │
   ▼         ▼         ▼       ▼        ▼          ▼        ▼        ▼
 (self)   (self)   architect architect haiku   engineer  haiku  engineer
context  interactive

                              After completion:
                    /execution-report → /system-review
                              │               │
                              ▼               ▼
                           (self)          (self)
                         document     process improvement
```

### Bug Fix Workflow

```
/prime → /rca → /hotfix → /validate
   │       │        │          │
   ▼       ▼        ▼          ▼
context  analysis  engineer  engineer
```

---

## Document Hierarchy

The framework uses a clear hierarchy from holistic vision down to individual tasks:

### The Hierarchy Model

```
docs/discovery.md              ← The whole app vision (living document)
  ├── docs/prds/auth.md        ← Feature PRD
  ├── docs/prds/sync-engine.md ← Feature PRD
  └── docs/prds/cli.md         ← Feature PRD
```

| Document | Scope | Analogy | Status |
|----------|-------|---------|--------|
| **Discovery** | Whole application | "The book" | Living document (revised over time) |
| **PRD** | One feature/epic | "A chapter" | Point-in-time (one per feature) |
| **Plan** | Technical approach for PRD | "Chapter outline" | Point-in-time (one per PRD) |
| **Tickets** | Individual tasks | "Paragraphs" | Created from plan |

### Key Principles

1. **One Discovery per application** - This is your holistic vision document that evolves over time
2. **Multiple PRDs per application** - Each PRD focuses on a single feature or epic
3. **PRDs reference Discovery** - Each PRD connects back to the overall vision
4. **Plans implement PRDs** - Each plan defines how to build what a PRD specified

### Document Flow

```
docs/
├── discovery.md                    # Living application vision (THE BOOK)
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
Discovery (whole app)
    ↓
   PRD 1 (Feature A - WHAT to build)      PRD 2 (Feature B)      PRD 3 (Feature C)
    ├── Features                              ├── Features              ├── Features
    ├── Acceptance Criteria                   ├── Acceptance Criteria   ├── Acceptance Criteria
    └── Ticket Definitions                    └── Ticket Definitions    └── Ticket Definitions
         ↓                                         ↓                         ↓
        Plan 1 (HOW to build Feature A)         Plan 2                    Plan 3
         ├── Technical Architecture
         ├── Implementation Phases
         └── Ticket Breakdown (with Asana IDs)
              ↓
             Implementation
```

---

## Phase Details

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

**Interactive requirements gathering conversation**

- **Who runs it**: You (orchestrator) - interactive with user
- **Input**: User's vision and needs
- **Output**: `docs/discovery.md` - Living document capturing requirements
- **Status**: NOT STARTED → IN PROGRESS → READY FOR PLANNING
- **Purpose**: Understand what the user wants to build and why

**Discovery is interactive** - you conduct it yourself as a conversation with the user. This is NOT delegated to an agent.

**Discovery vs Research:**

| `/discover` | `/research` |
|-------------|-------------|
| **Interactive** conversation | **Autonomous** investigation |
| You conduct it yourself | Delegate to general-purpose agent |
| User explains their vision | Agent explores topic independently |
| Output: `docs/discovery.md` | Output: `docs/research/YYYY-MM-DD-topic.md` |
| Living document, revisable | Point-in-time findings |

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

**Create Asana tasks from plan**

- **Who runs it**: Haiku agent (fast, simple task)
- **Prerequisites**: Approved plan
- **Input**: Plan document with ticket table
- **Output**: Tasks created in Asana, plan updated with ticket IDs
- **Creates**: One Asana task per ticket row in the plan

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

## Post-Completion Phases

After merging a feature, complete the feedback loop:

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

## Prerequisites by Phase

| Phase | Requires |
|-------|----------|
| `/prime` | None - run before any significant work |
| `/discover` | None - can start anytime |
| `/research` | None - can run anytime |
| `/rca` | Bug report or issue to investigate |
| `/prd` | Discovery status = READY FOR PLANNING (or explicit skip) |
| `/plan` | Approved PRD |
| `/ticket` | Approved plan |
| `/implement` | Plan with ticket IDs |
| `/pr` | Passing tests, committed code |
| `/validate` | Open PR |
| `/execution-report` | Completed implementation |
| `/system-review` | Execution report |

**Check prerequisites before proceeding. If missing, guide user to correct phase.**

---

## Hotfix Workflow

For production emergencies, use the abbreviated hotfix workflow:

```
/prime → /rca → /hotfix → /validate
```

**Two-Stage Bug Fix Process:**

1. **Root Cause Analysis (`/rca`)** - Investigate before fixing
   - Gather issue details
   - Reproduce the issue
   - Identify root cause
   - Design the fix
   - Output: `docs/rca/YYYY-MM-DD-{issue}.md`

2. **Hotfix (`/hotfix`)** - Implement the fix
   - Skip discovery/PRD/plan
   - Still requires: ticket, tests, PR
   - Delegate to engineer with urgency flag

**Key Principle**: Separate analysis from implementation. Understand the problem before coding the fix.

---

## Optional: Research Phase

The `/research` command can be used at any time for autonomous technical investigation:

```bash
/research "topic to investigate"
```

Output: `docs/research/YYYY-MM-DD-{topic}.md`

---

## Document Locations (State Persistence)

Workflow state persists in files, not context:

| Phase | Artifact Location | Status Field | Scope |
|-------|-------------------|--------------|-------|
| Discovery | `docs/discovery.md` (living doc) | NOT STARTED → IN PROGRESS → READY FOR PLANNING | **Whole application vision** |
| Research | `docs/research/YYYY-MM-DD-{topic}.md` | (point-in-time) | Technical investigations |
| RCA | `docs/rca/YYYY-MM-DD-{issue}.md` | ANALYZING → FIX PROPOSED → VERIFIED | Bug investigation |
| PRD | `docs/prds/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | **One feature/epic per PRD** |
| Plan | `docs/plans/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | Technical approach for one PRD |
| Tickets | Updated in plan (ticket IDs added) | IDs populated | Individual tasks from plan |
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
[TASK-XXX] Brief description (50 chars max)

- Detail about what changed

Co-Authored-By: Claude <noreply@anthropic.com>
```

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

---

## Templates

Templates available in `docs/templates/`:
- `discovery-template.md` - Discovery document template
- `prd-template.md` - PRD template
- `plan-template.md` - Technical plan template

Agents should use these as starting points.
