# SDLC Workflow Project

Automated software development workflow using Claude Code with deterministic tooling.

## Prerequisites

### Required CLI Tools

| Tool | Purpose | Install | Verify |
|------|---------|---------|--------|
| `git` | Version control | [git-scm.com](https://git-scm.com) | `git --version` |
| `gh` | GitHub CLI for PRs | `brew install gh` | `gh --version` |
| Node.js | Runtime | [nodejs.org](https://nodejs.org) | `node --version` |

### Required MCPs

Configure these in your Claude Code MCP settings:

#### Asana MCP (Required)

```json
{
  "mcpServers": {
    "asana": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-asana"],
      "env": {
        "ASANA_ACCESS_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Get your Asana token:** [Asana Developer Console](https://app.asana.com/0/developer-console)

### Environment Variables

```bash
# Required for Asana MCP
export ASANA_ACCESS_TOKEN="your-asana-personal-access-token"
export ASANA_PROJECT_ID="your-project-id"
export ASANA_WORKSPACE_ID="your-workspace-id"
```

## Workflow

```
/discover → /plan → /prd → /ticket → /implement → /pr → /validate
```

| Phase | Description | Output |
|-------|-------------|--------|
| `/discover` | Interactive requirements gathering | `docs/discovery.md` |
| `/research` | Autonomous technical research | `docs/research/*.md` |
| `/plan` | Technical implementation plan | `docs/plans/*.md` |
| `/prd` | Formal requirements document | `docs/prds/*.md` |
| `/ticket` | Create Asana tasks | Tasks in Asana |
| `/implement` | TDD implementation | Code + tests |
| `/pr` | Create GitHub PR | PR on GitHub |
| `/validate` | Pre-merge validation | Validation report |

## Quick Start

1. **Clone and enter project**
   ```bash
   git clone <repo-url>
   cd <project>
   ```

2. **Verify prerequisites**
   ```bash
   git --version
   gh --version
   gh auth status
   ```

3. **Configure MCPs** (see above)

4. **Start discovery**
   ```
   /discover
   ```

## Configuration

Edit `.claude/config.yaml` to customize:
- PM tool (Asana/Trello/GitHub/Linear)
- Test/lint/build commands
- Git conventions

## File Structure

```
.
├── .claude/
│   ├── commands/          # Slash command definitions
│   │   ├── discover.md    # Interactive requirements
│   │   ├── research.md    # Autonomous research
│   │   ├── plan.md        # Technical planning
│   │   ├── prd.md         # PRD creation
│   │   ├── ticket.md      # Asana task creation
│   │   ├── implement.md   # TDD implementation
│   │   ├── pr.md          # PR creation
│   │   ├── validate.md    # Pre-merge validation
│   │   ├── status.md      # Workflow status
│   │   └── hotfix.md      # Emergency fixes
│   └── config.yaml        # Project configuration
├── docs/
│   ├── discovery.md       # Living requirements doc
│   ├── plans/             # Implementation plans
│   ├── prds/              # Product requirements
│   ├── research/          # Research findings
│   └── templates/         # Document templates
├── CLAUDE.md              # Main workflow instructions
└── README.md              # This file
```

## License

[Your license here]
