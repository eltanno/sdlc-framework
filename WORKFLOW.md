# SDLC Workflow Reference

This document provides comprehensive workflow documentation for the SDLC automation framework.

## Workflow Overview

The framework enforces a phase-based workflow where each phase has clear inputs, outputs, and prerequisites:

```
┌──────────┐     ┌─────┐     ┌──────┐     ┌────────┐     ┌───────────┐     ┌────┐     ┌──────────┐
│ Discover │ --> │ PRD │ --> │ Plan │ --> │ Ticket │ --> │ Implement │ --> │ PR │ --> │ Validate │
└──────────┘     └─────┘     └──────┘     └────────┘     └───────────┘     └────┘     └──────────┘
```

```
/discover → /prd → /plan → /ticket → /implement → /pr → /validate
    │         │       │        │          │        │        │
    ▼         ▼       ▼        ▼          ▼        ▼        ▼
 (self)  architect architect haiku   engineer  haiku  engineer
interactive
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

## Prerequisites by Phase

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

**Check prerequisites before proceeding. If missing, guide user to correct phase.**

---

## Hotfix Workflow

For production emergencies, use the abbreviated hotfix workflow:

```bash
/hotfix "description of fix"
```

This skips discovery/PRD/plan but still requires:
- Ticket creation
- TDD implementation
- PR with tests
- Validation before merge

The hotfix workflow uses abbreviated flow:
- Skip discovery/plan/PRD
- Still requires: ticket, tests, PR
- Delegate to engineer with urgency flag

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
| PRD | `docs/prds/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | **One feature/epic per PRD** |
| Plan | `docs/plans/YYYY-MM-DD-{feature}.md` | DRAFT → APPROVED | Technical approach for one PRD |
| Tickets | Updated in plan (ticket IDs added) | IDs populated | Individual tasks from plan |

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

1. **Plan Before Code** - Never skip to implementation without a plan
2. **Test First** - Write failing tests before implementation
3. **Phase Gates** - Each phase requires approval before proceeding
4. **Document Everything** - All decisions captured in version-controlled docs
5. **Quality Gates** - Tests and linting must pass before merge
6. **Traceability** - Every commit links to a ticket, every ticket to a PRD

---

## Templates

Templates available in `docs/templates/`:
- `discovery-template.md` - Discovery document template
- `prd-template.md` - PRD template
- `plan-template.md` - Technical plan template

Agents should use these as starting points.
