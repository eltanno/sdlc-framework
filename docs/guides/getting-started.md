# Getting Started with the SDLC Framework

Welcome to the SDLC automation framework. This guide will help you understand the system and get up and running quickly.

---

## What Is This?

This is an AI-assisted software development lifecycle (SDLC) framework that automates the journey from idea to shipped code. It uses Claude as the AI backbone with specialized agents for different phases of development.

**Key Features:**
- Phase-based workflow (discover → prd → plan → ticket → implement → validate → release)
- Automated ticket creation and tracking
- TDD-based implementation with validation
- Multi-instance parallel execution (ralph loops)
- State persistence through markdown artifacts

---

## Quick Start

### 1. Prerequisites

**Required:**
- **Claude Code CLI** - installed and authenticated
- **Git** - version control
- **GitHub CLI** (`gh`) - authenticated: `gh auth login`
- **jq** - JSON processor (used extensively by ralph scripts)
- **Node.js** and npm/bun (or your project's runtime)

**Optional:**
- **timeout** (Linux) or **gtimeout** (macOS via coreutils) - for engineer timeouts
- **ccusage** (`bunx ccusage`) - for usage/cost tracking

#### Installing Dependencies

```bash
# macOS (via Homebrew)
brew install jq gh coreutils   # coreutils provides gtimeout

# Ubuntu/Debian
sudo apt install jq gh

# Arch Linux
sudo pacman -S jq github-cli

# Verify installation
jq --version
gh --version
```

### 2. Configuration Files

Two files control the system:

**`config.yaml`** - Project settings (safe to commit):
```yaml
pm:
  tool: github              # Where tickets live

tickets:
  prefix: "PROJ"            # Your ticket prefix (e.g., PROJ-0001)
  counter: 1                # Starting ticket number

ralph:
  sonnet_threshold: 2       # Complexity 1-2 uses Sonnet, 3-5 uses Opus
  max_attempts: 3           # Retries before blocking a ticket
  engineer_timeout: 30      # Minutes per implementation attempt
```

**`.env`** - Instance-specific settings (do NOT commit):
```bash
RALPH_LABEL=ralph-1         # Unique label for this instance
```

### 3. Your First Workflow

Start a Claude session and run the planning phases:

```bash
claude
```

Then in Claude:
```
/discover
```

This begins an interactive discovery session to define what you're building.

---

## The Two Stages

### Planning Stage (Human-Guided)

| Phase | Command | What Happens | Output |
|-------|---------|--------------|--------|
| **Prime** | `/prime` | Load project context | Context in memory |
| **Discover** | `/discover` | Interactive requirements gathering | `docs/discovery/*.md` |
| **PRD** | `/prd` | Generate product requirements | `docs/prds/*.md` |
| **Plan** | `/plan` | Create technical implementation plan | `docs/plans/*.md` |
| **Ticket** | `/ticket` | Create tickets in PM tool | GitHub Issues |

**Human approval required** at Discovery, PRD, and Plan phases.

### Execution Stage (Can Be Automated)

| Phase | Command | What Happens | Output |
|-------|---------|--------------|--------|
| **Implement** | `/implement` | TDD implementation | Code on feature branch |
| **PR** | `/pr` | Create pull request | GitHub PR |
| **Validate** | `/validate` | Pre-merge validation | Validation report |
| **Release** | `/release` | Update README, close loop | Updated docs |

Execution can run manually (one ticket at a time) or via **ralph loops** (automated parallel execution).

---

## Running Ralph Loops

Ralph is the autonomous execution engine that processes tickets without human intervention.

### Single Instance

```bash
# From your project root
.claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md
```

### Multiple Instances (Parallel Execution)

For faster execution, run multiple ralph instances:

1. **Create worktrees** (use detached HEAD to avoid branch conflicts):
   ```bash
   git worktree add ../ralph-1 origin/main --detach
   git worktree add ../ralph-2 origin/main --detach
   ```

2. **Configure each instance** with unique `.env`:
   ```bash
   # In ralph-1/.env
   RALPH_LABEL=ralph-1

   # In ralph-2/.env
   RALPH_LABEL=ralph-2
   ```

3. **Start loops in separate terminals:**
   ```bash
   # Terminal 1
   cd ralph-1 && .claude/scripts/ralph-prd.sh ...

   # Terminal 2
   cd ralph-2 && .claude/scripts/ralph-prd.sh ...
   ```

See [Multi-Instance Setup Guide](./multi-instance-setup.md) for details.

---

## Key Concepts

### Artifacts

State is persisted in markdown files, not conversation context:

| Type | Location | Purpose |
|------|----------|---------|
| Discovery | `docs/discovery/*.md` | Product vision and requirements |
| PRD | `docs/prds/*.md` | Detailed feature specifications |
| Plan | `docs/plans/*.md` | Technical implementation approach |
| State | `docs/state/TICKET-ID/` | Engineer progress per ticket |
| Research | `docs/research/*.md` | Technical investigations |

### Ticket Lifecycle

```
pending → in_progress → (validation) → completed
                ↓
            blocked (after max_attempts failures)
```

### Complexity Ratings

Tickets have complexity 1-5:
- **1-2**: Simple tasks → Uses Sonnet (faster, cheaper)
- **3-5**: Complex tasks → Uses Opus (more capable)

Configure the threshold in `config.yaml` → `ralph.sonnet_threshold`

---

## Common Commands

### Workflow Commands

| Command | Purpose |
|---------|---------|
| `/prime` | Load project context |
| `/discover` | Start discovery session |
| `/prd` | Generate PRD from discovery |
| `/plan` | Create implementation plan |
| `/ticket` | Create tickets from plan |
| `/implement` | Implement a ticket |
| `/validate` | Validate implementation |
| `/status` | Check workflow state |
| `/whats-next` | Get recommended next action |

### Utility Commands

| Command | Purpose |
|---------|---------|
| `/research <topic>` | Autonomous technical research |
| `/rca` | Root cause analysis for bugs |
| `/hotfix` | Emergency fix workflow |
| `/bugfix` | Standard bug fix workflow |

---

## Directory Structure

```
project/
├── .claude/
│   ├── agents/              # Agent definitions
│   ├── scripts/
│   │   ├── ralph-prd.sh     # Main ralph orchestrator
│   │   └── ralph/           # Ralph helper scripts
│   └── skills/              # Skill definitions
├── docs/
│   ├── discovery/           # Discovery documents
│   ├── prds/                # Product requirements
│   ├── plans/               # Implementation plans
│   ├── state/               # Engineer state files
│   ├── research/            # Research documents
│   ├── guides/              # How-to guides (you are here)
│   └── templates/           # Document templates
├── config.yaml              # Project configuration
├── .env                     # Instance secrets (not committed)
└── workflow-state.json      # Current workflow state
```

---

## Troubleshooting

### "No tickets found"

- Ensure tickets exist in your PM tool with the correct prefix
- Check that tickets have the `task` label (for GitHub)
- Verify `config.yaml` has the correct `tickets.prefix`

### "Engineer timed out"

- Default timeout is 30 minutes
- Increase `ralph.engineer_timeout` in `config.yaml` for complex tickets
- Consider breaking large tickets into smaller ones

### "Validation failed"

- Check the state file: `docs/state/TICKET-ID/attempt-N/engineer-state.md`
- Review test output in the logs: `.logs/ralph/`
- Ticket will retry up to `max_attempts` times

### Ralph instance stuck

- Check for interactive prompts (now auto-resumed)
- See [Crash Recovery Guide](./ralph-loop-crash-recovery.md)

---

## Further Reading

### Core Documentation
- [WORKFLOW.md](../../WORKFLOW.md) - Complete workflow reference
- [CLAUDE.md](../../CLAUDE.md) - Orchestrator instructions

### Guides
- [Workflow Guide](./workflow-guide.md) - Detailed workflow walkthrough
- [Multi-Instance Setup](./multi-instance-setup.md) - Running parallel ralph loops
- [Crash Recovery](./ralph-loop-crash-recovery.md) - Recovering from failures
- [Ralph Loop Analysis](./ralph-prd-loop-analysis.md) - How ralph works internally

### Templates
- [Discovery Template](../templates/discovery-template.md)
- [PRD Template](../templates/prd-template.md)
- [Plan Template](../templates/plan-template.md)

---

## Getting Help

1. Run `/guide` in Claude for interactive help
2. Run `/status` to see current workflow state
3. Run `/whats-next` for recommended actions
4. Check logs in `.logs/ralph/` for debugging
