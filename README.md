# SDLC Automation Framework

Automated software development workflow for Claude Code.

## What This Is

A complete Software Development Lifecycle (SDLC) automation framework that guides Claude Code through professional software development workflows - from interactive requirements gathering, through formal PRDs and technical planning, to test-driven implementation and deployment. The framework enforces quality gates, maintains traceability, and integrates with Asana for task management.

## Quick Start

1. Clone/copy this framework into your project
2. Run the setup script:
   ```bash
   ./claude-setup.sh
   ```
3. Edit `.env` with your API keys
4. Configure Asana MCP in Claude Code (see below)
5. Run `/discover` to start

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

The setup script (`./claude-setup.sh`) will install these automatically on Linux/WSL.

### Required Tools

| Tool | Purpose | Verify |
|------|---------|--------|
| `git` | Version control | `git --version` |
| `gh` or `glab` | GitHub/GitLab CLI for PRs | `gh --version` or `glab --version` |
| `node` | Runtime | `node --version` |
| `bun` | Hooks runtime | `bun --version` |
| `jq` | JSON parsing (statusline) | `jq --version` |

The setup script will install `gh` (GitHub) or `glab` (GitLab) based on your selection.

### Optional Tools

| Tool | Purpose | Verify |
|------|---------|--------|
| `ccusage` | Token/cost display in statusline | `bunx ccusage --help` |

### Claude Code Plugins (Required)

Install the official plugins for Claude Code:

```bash
# Install plugins via CLI (for Docker/automation)
claude plugin install asana
claude plugin install playwright
claude plugin install github
claude plugin install gitlab
claude plugin install code-review
claude plugin install commit-commands
claude plugin install pr-review-toolkit
claude plugin install security-guidance
```

| Plugin | Purpose | SDLC Phase |
|--------|---------|------------|
| `asana` | Task management integration | `/ticket` |
| `playwright` | Browser automation | Testing |
| `github` | GitHub issues, PRs, actions | `/pr`, `/validate` |
| `gitlab` | GitLab issues, MRs, pipelines | `/pr`, `/validate` |
| `code-review` | Automated code review | `/validate` |
| `commit-commands` | Enhanced git commit workflow | `/implement` |
| `pr-review-toolkit` | PR review automation | `/pr`, `/validate` |
| `security-guidance` | Security best practices | `/implement` |

**Asana Setup:**
- Get your token: [Asana Developer Console](https://app.asana.com/0/developer-console)
- Set in environment: `export ASANA_ACCESS_TOKEN="your-token-here"`

**GitHub Setup:**
- Authenticate via: `gh auth login`

**GitLab Setup:**
- Authenticate via: `glab auth login`

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `ASANA_ACCESS_TOKEN` - Your Asana personal access token
- `ASANA_WORKSPACE_ID` - Your Asana workspace ID
- `ASANA_PROJECT_ID` - Your Asana project ID

See `.env.example` for all available configuration options.

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
│   ├── hooks/                     # Claude Code hooks
│   │   ├── security-validator.ts  # PreToolUse security validation
│   │   ├── capture-tool-output.ts # PostToolUse audit logging
│   │   ├── capture-session-summary.ts # SessionEnd summary generation
│   │   ├── capture-subagent-summary.ts # SubagentStop logging
│   │   └── validate-docs.ts       # Documentation link validator
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
├── .env.example                  # Environment variables template
├── .mcp.json                     # MCP server configuration (Asana)
├── claude-setup.sh               # Dependency installation script
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

## Hooks

The framework includes Claude Code hooks for security and auditing.

### Included Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `security-validator.ts` | PreToolUse (Bash) | Blocks dangerous commands (reverse shells, `rm -rf ~`, prompt injection) |
| `capture-tool-output.ts` | PostToolUse | Logs tool executions for auditing |
| `capture-session-summary.ts` | SessionEnd | Generates session summary documents |
| `capture-subagent-summary.ts` | SubagentStop | Logs sub-agent completions |
| `validate-docs.ts` | Manual | Validates markdown links before commits |

### Requirements

Hooks require [Bun](https://bun.sh) runtime:

```bash
# Install bun
curl -fsSL https://bun.sh/install | bash

# Verify
bun --version
```

### Log Locations

Logs are written to `.logs/` (git-ignored):

- `.logs/claude-security-events.jsonl` - Blocked security events
- `.logs/tool-outputs/YYYY-MM-DD-tool-outputs.jsonl` - Daily tool execution logs
- `.logs/history/sessions/YYYY-MM/YYYY-MM-DD-HHMMSS_session.md` - Session summaries
- `.logs/history/subagents/YYYY-MM-DD-subagents.jsonl` - Sub-agent completion logs

### Optional: Git Pre-Commit Validation

To validate documentation links before each commit, create a git hook:

```bash
# Create the hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
bun run .claude/hooks/validate-docs.ts
EOF

# Make it executable
chmod +x .git/hooks/pre-commit
```

Note: `.git/hooks/` is local and not shared. Each developer must set this up themselves.

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
