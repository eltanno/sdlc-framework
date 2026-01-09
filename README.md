# SDLC Automation Framework for Claude Code

A complete Software Development Lifecycle (SDLC) automation framework designed for clean Claude Code installations. This framework provides a structured, phase-based workflow from requirements gathering through deployment.

## What This Is

This is an SDLC automation framework that guides Claude Code through professional software development workflows:

- **Interactive Requirements Gathering** - Discovery conversations to understand user needs
- **Formal Product Requirements** - PRDs with testable acceptance criteria
- **Technical Planning** - Detailed implementation plans with architecture decisions
- **Task Management** - Automatic ticket creation in Asana
- **Test-Driven Development** - TDD workflow with quality gates
- **Pull Request Automation** - Automated PR creation with validation
- **Pre-Merge Validation** - Comprehensive checks before merging

## The Workflow Explained

The framework enforces a phase-based workflow where each phase has clear inputs, outputs, and prerequisites:

```
┌──────────┐     ┌─────┐     ┌──────┐     ┌────────┐     ┌───────────┐     ┌────┐     ┌──────────┐
│ Discover │ --> │ PRD │ --> │ Plan │ --> │ Ticket │ --> │ Implement │ --> │ PR │ --> │ Validate │
└──────────┘     └─────┘     └──────┘     └────────┘     └───────────┘     └────┘     └──────────┘
```

### Phase Details

#### 1. Discovery (`/discover`)
**Interactive requirements gathering conversation**

- **Who runs it**: You (orchestrator) - interactive with user
- **Input**: User's vision and needs
- **Output**: `docs/discovery.md` - Living document capturing requirements
- **Status**: NOT STARTED → IN PROGRESS → READY FOR PLANNING
- **Purpose**: Understand what the user wants to build and why

#### 2. PRD (`/prd`)
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

#### 3. Plan (`/plan`)
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

#### 4. Ticket (`/ticket`)
**Create Asana tasks from plan**

- **Who runs it**: Haiku agent (fast, simple task)
- **Prerequisites**: Approved plan
- **Input**: Plan document with ticket table
- **Output**: Tasks created in Asana, plan updated with ticket IDs
- **Creates**: One Asana task per ticket row in the plan

#### 5. Implement (`/implement`)
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

#### 6. PR (`/pr`)
**Create GitHub pull request**

- **Who runs it**: Haiku agent (fast, simple task)
- **Prerequisites**: Committed code with passing tests
- **Input**: Feature branch, ticket ID
- **Output**: GitHub pull request linked to ticket
- **Creates**: PR with description, links to PRD/plan, test results

#### 7. Validate (`/validate`)
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

## Document Flow

The framework creates and maintains several key documents:

```
docs/
├── discovery.md                    # Living requirements document
├── prds/
│   └── YYYY-MM-DD-feature.md      # What to build
├── plans/
│   ├── YYYY-MM-DD-feature.md      # How to build it
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
Discovery
    ↓
   PRD (WHAT to build)
    ├── Features
    ├── Acceptance Criteria
    └── Ticket Definitions
         ↓
        Plan (HOW to build)
         ├── Technical Architecture
         ├── Implementation Phases
         └── Ticket Breakdown (with Asana IDs)
              ↓
             Implementation
```

## Prerequisites

### Required CLI Tools

| Tool | Purpose | Install | Verify |
|------|---------|---------|--------|
| `git` | Version control | [git-scm.com](https://git-scm.com) | `git --version` |
| `gh` | GitHub CLI for PRs | [cli.github.com](https://cli.github.com) | `gh --version` |
| Node.js | Runtime | [nodejs.org](https://nodejs.org) | `node --version` |

### Required MCP Server

Configure Asana MCP in your Claude Code settings:

**Using Claude Code Desktop App:**
1. Open Settings → MCP Servers
2. Add new server:
   - Name: `asana`
   - Command: `npx`
   - Args: `["-y", "@anthropic/mcp-asana"]`
   - Environment:
     ```json
     {
       "ASANA_ACCESS_TOKEN": "your-token-here"
     }
     ```

**Get your Asana token:** [Asana Developer Console](https://app.asana.com/0/developer-console)

### Environment Variables

```bash
# Required for Asana integration
export ASANA_ACCESS_TOKEN="your-asana-personal-access-token"
export ASANA_PROJECT_ID="your-project-id"
export ASANA_WORKSPACE_ID="your-workspace-id"
```

## Quick Start

### 1. Initial Setup

```bash
# Clone this framework into your project
git clone <this-repo-url> .

# Verify prerequisites
git --version
gh --version
gh auth status
node --version

# Verify Asana MCP is configured
# (Should see asana tools available in Claude Code)
```

### 2. Start Your First Feature

```bash
# Start with discovery
/discover

# After discovery is approved, create PRD
/prd {feature-name}

# After PRD is approved, create plan
/plan {feature-name}

# After plan is approved, create tickets
/ticket

# Implement each ticket
/implement ASANA-123

# Create PR after implementation
/pr ASANA-123

# Validate before merge
/validate ASANA-123
```

### 3. Check Status Anytime

```bash
/status
```

## File Structure

```
.
├── .claude/
│   ├── agents/                    # Agent definition files
│   │   ├── architect.md          # Architect agent responsibilities
│   │   └── engineer.md           # Engineer agent responsibilities
│   ├── commands/                  # Slash command definitions
│   │   ├── discover.md           # /discover - Interactive requirements
│   │   ├── prd.md                # /prd - PRD creation
│   │   ├── plan.md               # /plan - Technical planning
│   │   ├── ticket.md             # /ticket - Asana task creation
│   │   ├── implement.md          # /implement - TDD implementation
│   │   ├── pr.md                 # /pr - PR creation
│   │   ├── validate.md           # /validate - Pre-merge validation
│   │   ├── status.md             # /status - Workflow status
│   │   ├── research.md           # /research - Technical research
│   │   └── hotfix.md             # /hotfix - Emergency fixes
│   └── config.yaml               # Project configuration
├── docs/
│   ├── discovery.md              # Living requirements doc
│   ├── plans/                    # Implementation plans
│   │   ├── YYYY-MM-DD-*.md
│   │   └── PROGRESS.md           # Implementation tracking
│   ├── prds/                     # Product requirements
│   │   └── YYYY-MM-DD-*.md
│   ├── research/                 # Research findings
│   │   └── YYYY-MM-DD-*.md
│   └── templates/                # Document templates
│       ├── discovery-template.md
│       ├── prd-template.md
│       └── plan-template.md
├── CLAUDE.md                     # Main workflow instructions
└── README.md                     # This file
```

## Configuration

Edit `.claude/config.yaml` to customize:

```yaml
project:
  name: "Your Project Name"
  pm_tool: "asana"  # or "trello", "github", "linear"

commands:
  test: "npm test"
  lint: "npm run lint"
  build: "npm run build"

git:
  branch_prefix: "feature"  # or "feat", "dev"
  commit_format: "[ASANA-{id}] {message}"

asana:
  workspace_id: "your-workspace-id"
  project_id: "your-project-id"
```

## Agent Definitions

The framework uses specialized agents for different tasks:

- **Architect Agent** (`.claude/agents/architect.md`)
  - Creates PRDs and plans
  - Makes technical design decisions
  - Defines system architecture

- **Engineer Agent** (`.claude/agents/engineer.md`)
  - Implements features using TDD
  - Writes tests and code
  - Ensures code quality and standards
  - Performs validation

The orchestrator (main Claude instance) coordinates these agents but does not do the implementation work itself.

## Key Principles

1. **Plan Before Code** - Never skip to implementation without a plan
2. **Test First** - Write failing tests before implementation
3. **Phase Gates** - Each phase requires approval before proceeding
4. **Document Everything** - All decisions captured in version-controlled docs
5. **Quality Gates** - Tests and linting must pass before merge
6. **Traceability** - Every commit links to a ticket, every ticket to a PRD

## Workflow Status Tracking

The framework maintains state in document status fields:

```markdown
**Status:** DRAFT | APPROVED
```

Prerequisites are enforced by checking these status fields before proceeding to the next phase.

## Optional: Research Phase

The `/research` command can be used at any time for autonomous technical investigation:

```bash
/research "topic to investigate"
```

Output: `docs/research/YYYY-MM-DD-{topic}.md`

## Emergency: Hotfix Workflow

For production emergencies, use the abbreviated hotfix workflow:

```bash
/hotfix "description of fix"
```

This skips discovery/PRD/plan but still requires:
- Ticket creation
- TDD implementation
- PR with tests
- Validation before merge

## License

[Your license here]
