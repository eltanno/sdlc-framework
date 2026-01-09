# SDLC Automation Framework

Automated software development workflow for Claude Code.

## What This Is

A complete Software Development Lifecycle (SDLC) automation framework that guides Claude Code through professional software development workflows - from interactive requirements gathering, through formal PRDs and technical planning, to test-driven implementation and deployment. The framework enforces quality gates, maintains traceability, and integrates with Asana for task management.

## Quick Start

1. Clone/copy this framework into your project
2. Configure prerequisites (see below)
3. Run `/discover` to start

## Workflow

See [WORKFLOW.md](WORKFLOW.md) for detailed workflow documentation.

```
/discover → /prd → /plan → /ticket → /implement → /pr → /validate
```

**Phase Summary:**
- `/discover` - Interactive requirements gathering
- `/prd` - Formal Product Requirements Document
- `/plan` - Technical implementation plan
- `/ticket` - Create Asana tasks
- `/implement` - TDD implementation
- `/pr` - Create GitHub pull request
- `/validate` - Pre-merge validation

## Prerequisites

### CLI Tools

| Tool | Purpose | Install | Verify |
|------|---------|---------|--------|
| `git` | Version control | [git-scm.com](https://git-scm.com) | `git --version` |
| `gh` | GitHub CLI for PRs | [cli.github.com](https://cli.github.com) | `gh --version` |
| Node.js | Runtime | [nodejs.org](https://nodejs.org) | `node --version` |
| `jq` | JSON parsing (statusline) | `apt install jq` / `brew install jq` | `jq --version` |

### Optional Tools

| Tool | Purpose | Install | Verify |
|------|---------|---------|--------|
| `ccusage` | Token/cost display in statusline | `bun add -g ccusage` | `bunx ccusage --help` |
| `timeout` | Cache timeout (Linux, usually pre-installed) | - | `timeout --version` |
| `gtimeout` | Cache timeout (macOS) | `brew install coreutils` | `gtimeout --version` |

### Asana MCP (Required)

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
│   ├── scripts/                   # Utility scripts
│   │   └── statusline.sh         # Custom statusline display
│   ├── settings.json             # Claude Code settings
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
├── CLAUDE.md                     # Orchestrator instructions
├── WORKFLOW.md                   # Detailed workflow reference
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

## Example Usage

### Start Your First Feature

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

### Check Status Anytime

```bash
/status
```

## License

MIT License - see [LICENSE](LICENSE) for details.
