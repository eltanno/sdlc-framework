# Research: Making the SDLC Framework Platform-Agnostic Across LLM CLI Tools

**Date:** 2026-02-26
**Status:** Complete
**Researcher:** Claude Opus 4.6

---

## Executive Summary

Making the SDLC framework platform-agnostic is **feasible but requires significant architectural restructuring**. The LLM CLI ecosystem has converged on several shared patterns -- AGENTS.md for project instructions, MCP for tool extension, and headless/non-interactive modes for automation -- but each tool has proprietary formats for custom commands, agent definitions, and subprocess spawning. The recommended approach is a **canonical format + generation layer**: maintain workflow definitions in a tool-neutral format and generate tool-specific configurations (`.claude/`, `.github/agents/`, `.codex/`, `.opencode/`, `.gemini/`) from a single source of truth.

---

## Tool-by-Tool Analysis

### 1. Claude Code CLI

**Current framework target. Baseline for comparison.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `CLAUDE.md` at project root (auto-loaded). Also `~/.claude/CLAUDE.md` for global. Hierarchical: home > project root > subdirectories. |
| **Custom Commands** | Markdown files in `.claude/commands/*.md`. Filename becomes `/command-name`. Supports `$ARGUMENTS` placeholder. Frontmatter optional. |
| **Agent Definitions** | Markdown files in `.claude/agents/*.md` with YAML frontmatter (name, description, model, permissions). Referenced via `--agent` flag or `Task()` delegation. |
| **Subagent Spawning** | Built-in `Task()` tool for delegation. Orchestrator delegates to agents by type. Ralph shells out via `claude -p "prompt" --agent engineer --model opus --output-format stream-json`. |
| **Headless Mode** | `claude -p "prompt"` for single-shot. `--output-format stream-json` for structured output. Full non-interactive support. |
| **Tools** | Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, TodoWrite, MultiEdit, NotebookEdit. `--allowedTools` flag to restrict. |
| **MCP Support** | Yes. `.mcp.json` at project root or `~/.claude/mcp.json` globally. Full MCP client. |
| **Config Format** | `.claude/settings.json` (permissions, model, statusLine, hooks). `config.yaml` for project-level SDLC settings. |

**Key Proprietary Elements:**
- `CLAUDE.md` naming convention (not AGENTS.md)
- `.claude/` directory structure
- `Task()` tool for in-process delegation
- `--agent`, `--allowedTools`, `--output-format stream-json` CLI flags
- TypeScript hooks in `.claude/hooks/`

---

### 2. GitHub Copilot CLI

**GA as of 2026-02-25. Major player with deep GitHub integration.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `AGENTS.md` at repo root (primary). Also `.github/copilot-instructions.md`, `*.instructions.md` with `applyTo` glob frontmatter. `~/.copilot/copilot-instructions.md` for global. `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var for additional paths. |
| **Custom Commands** | **Not yet supported as custom slash commands.** Feature requests exist ([#618](https://github.com/github/copilot-cli/issues/618), [#1113](https://github.com/github/copilot-cli/issues/1113)). `.github/prompts/*.prompt.md` works in VS Code but NOT in CLI. Built-in slash commands only: `/help`, `/clear`, `/session`, `/delegate`, `/models`, etc. |
| **Agent Definitions** | `.github/agents/*.agent.md` or `~/.copilot/agents/*.agent.md`. Markdown with YAML frontmatter defining persona, tools, MCP servers. Agent orchestration is hierarchical (main agent + sub-agents). |
| **Subagent Spawning** | Automatic delegation to custom agents when task matches expertise. `/delegate` command sends to Copilot coding agent (cloud-based). Sub-agents are temporary, spun up for specific tasks. Agent Client Protocol (ACP) support via `--acp --stdio`. |
| **Headless Mode** | `-p` or `--prompt` for single-shot non-interactive. Approval CLI options for headless operation. JSON-RPC over stdio via `--acp --stdio`. **Breaking change in v0.0.410+**: `--headless --stdio` replaced by `--acp --stdio`. |
| **Tools** | Built-in GitHub MCP server (ships bundled). File read/write, bash, search. `--enable-all-github-mcp-tools` for full read-write GitHub API access. Custom MCP servers. |
| **MCP Support** | Yes. `~/.copilot/mcp-config.json` or `.copilot/mcp-config.json` at project level. Built-in GitHub MCP server. `instructions` field per server (v0.0.400+). `tools` field for selective tool exposure. Supports STDIO, SSE, Remote OAuth transports. |
| **Config Format** | `~/.copilot/config.json` for user settings. `.github/` directory for repo-level config. |

**Key Proprietary Elements:**
- `.github/agents/*.agent.md` naming convention
- No custom slash commands in CLI (yet)
- `/delegate` for cloud-based Copilot coding agent
- ACP protocol for editor/agent communication
- `mcp-config.json` format (different from Claude's `.mcp.json`)
- Plugin system: `/plugin install owner/repo`

**Critical Gap:** No custom slash commands means our `/implement`, `/plan`, `/prd` etc. workflow commands cannot be directly ported. Users would need to invoke via natural language or agent definitions would need to encode the workflow.

---

### 3. OpenAI Codex CLI

**Open-source (Rust), strong multi-agent and skills system.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `AGENTS.md` at repo root. Also `AGENTS.override.md` for overrides. `~/.codex/AGENTS.md` for global. Instruction chain built at startup: global scope -> project root -> working directory. |
| **Custom Commands** | **Skills system** replaces deprecated "custom prompts." A skill = directory with `SKILL.md` + optional scripts/resources. Invoked via `$skill-name` or `/skills`. `allow_implicit_invocation` controls auto-invocation. Built-in slash commands: `/model`, `/personality`, `/permissions`, `/agent`, `/status`, `/review`, `/fork`. |
| **Agent Definitions** | Multi-agent collaboration via `[agents]` in `config.toml`. Experimental feature for parallelizing tasks. Agent roles configured in config. |
| **Subagent Spawning** | Multi-agent workflows via Agents SDK. Experimental parallel task execution. `codex exec` for headless single-agent runs. |
| **Headless Mode** | `codex exec "prompt"` for non-interactive. `--json` flag for JSON Lines output to stdout. Elicitation requests auto-cancelled, approvals default to "Never". Clean separation: protocol events to stdout, warnings to stderr. |
| **Tools** | File read/write, bash, search. Standard coding tools. MCP server tools exposed alongside built-ins. |
| **MCP Support** | Yes. Configured in `~/.codex/config.toml` under MCP section. `codex mcp add/remove/list` CLI commands. Supports Stdio and StreamableHttp transports. `--env KEY=VALUE` for stdio transports. Auto-launched at session start. |
| **Config Format** | `~/.codex/config.toml` (global). `.codex/config.toml` (project, requires trust). TOML format. |

**Key Proprietary Elements:**
- TOML config format (vs JSON/YAML elsewhere)
- Skills system with `SKILL.md` files
- `$skill-name` invocation syntax
- `codex exec` for headless
- `codex mcp` CLI subcommands
- Agents SDK integration

**Notable:** Skills are the closest analog to Claude Code's `/commands/` -- a directory with a markdown file that defines a reusable workflow. The mapping is fairly direct but the format differs.

---

### 4. OpenCode CLI

**Open-source (Go), 75+ providers, strong agent/command system.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `AGENTS.md` at repo root (primary). Also `~/.config/opencode/AGENTS.md` for global. `/init` command generates project-specific instructions. "Rules" system for additional instructions. |
| **Custom Commands** | Markdown files in `.opencode/commands/` directory. Filename becomes command name. Supports `$ARGUMENTS` placeholder. Also configurable via `opencode.json` config file. Placeholders and special syntax supported. |
| **Agent Definitions** | Markdown files in `.opencode/agent/` directory. Filename becomes agent name. Also configurable in `opencode.json`. Supports custom system prompts, model overrides per agent. Two types: **primary agents** (direct interaction) and **subagents** (delegated tasks). |
| **Subagent Spawning** | Built-in Task tool for delegation. `permission.task` controls which subagents an agent can invoke (glob patterns). Subagent gets own session, tools, system prompt, and potentially different LLM. `@agent-name` for manual invocation. |
| **Headless Mode** | `opencode -p "prompt"` for non-interactive. `-f json` for JSON output. `opencode run --model provider/model "prompt"` for headless with model selection. HTTP server mode for API access. |
| **Tools** | File read/write, bash, search, glob, grep. MCP server tools exposed alongside built-ins. Tool management via config. |
| **MCP Support** | Yes. Configured in `opencode.json` under `mcp` key. Each MCP server gets a unique name. Supports STDIO transport. MCP tools available alongside built-in tools. |
| **Config Format** | `opencode.json` (project root or `~/.config/opencode/`). JSON format with schema at `opencode.ai/config.json`. |

**Key Proprietary Elements:**
- `.opencode/` directory structure
- `opencode.json` config format
- `.opencode/agent/` for agent definitions (vs `.claude/agents/`)
- `.opencode/commands/` for custom commands
- `@agent-name` invocation syntax
- `permission.task` glob patterns for delegation control

**Best Analog:** OpenCode's architecture is the **closest match** to our current framework. It has custom commands (markdown files), custom agents (markdown files with system prompts), subagent delegation via Task tool, and headless mode. The mapping would be nearly 1:1.

---

### 5. Gemini CLI

**Open-source by Google, strong custom commands, GEMINI.md system.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `GEMINI.md` at repo root. Also `~/.gemini/GEMINI.md` for global. `/init` command generates project-specific context. Hierarchical memory from GEMINI.md files. |
| **Custom Commands** | **TOML files** in `.gemini/commands/` (project) or `~/.gemini/commands/` (user). Sub-directories create namespaced commands (`dir/cmd` becomes `dir:cmd`). Features: `prompt` field, `description` field, `{{args}}` placeholder, `!{...}` inject syntax, `@{path/to/dir}` directory listing injection. `/commands reload` to pick up changes. |
| **Agent Definitions** | No dedicated agent definition system comparable to Claude Code's. Uses system prompts and MCP server configurations. Gemini Code Assist agent mode in VS Code powered by Gemini CLI. |
| **Subagent Spawning** | Not a first-class feature in the same way. ReAct loop with tools. No built-in Task delegation to named agents. |
| **Headless Mode** | Headless/scripting mode for automated workflows. Non-interactive invocation supported. |
| **Tools** | File read/write, bash, search. MCP server tools. ReAct (reason and act) loop. |
| **MCP Support** | Yes. `~/.gemini/settings.json` under `mcpServers` key. `gemini mcp add` CLI command for registration. Supports command, args, cwd, timeout per server. |
| **Config Format** | `~/.gemini/settings.json` (JSON). TOML for custom commands. |

**Key Proprietary Elements:**
- `GEMINI.md` naming (not AGENTS.md)
- TOML format for custom commands (unique among all tools)
- `.gemini/commands/` directory
- Namespace-based command naming with colons
- `{{args}}`, `!{...}`, `@{...}` template syntax
- `gemini mcp add` CLI subcommands

**Notable Gap:** No dedicated agent definitions or subagent delegation. This is a significant limitation for our orchestrator pattern.

---

### 6. Cline CLI 2.0

**VS Code extension turned CLI. Recent entrant (Feb 2026).**

| Capability | Implementation |
|---|---|
| **System Instructions** | Uses project-level instruction files. `.clinerules` or custom rule files. |
| **Custom Commands** | Markdown files dropped into custom workflows directory automatically become slash commands. E.g., `pr-review.md` becomes `/pr-review`. |
| **Agent Definitions** | Not a dedicated system. Cline operates as a single agent with MCP tool extensions. |
| **Subagent Spawning** | Not a first-class feature for named subagents. |
| **Headless Mode** | `-y`/`--yolo` for full autonomy. `--json` for structured output. Full stdin/stdout pipe support. Treats Cline as a Unix tool. |
| **Tools** | File create/edit, command execution, browser use. MCP extensions. Custom tools via MCP. |
| **MCP Support** | Yes. Full MCP client. Can create and install tools dynamically. |
| **ACP Support** | `--acp` flag turns Cline into ACP-compliant agent. Works with JetBrains, Zed, Neovim, Emacs. |
| **Config Format** | JSON-based settings. `/settings` command for mid-session changes. |

**Key Proprietary Elements:**
- `.clinerules` for instructions
- `--yolo` flag for full autonomy
- ACP-compliant agent mode
- Dynamic MCP tool creation

---

### 7. Goose (Block/Linux Foundation)

**Open-source, MCP-native, recipe-based workflows.**

| Capability | Implementation |
|---|---|
| **System Instructions** | Via Recipes (instructions + initial prompt + extensions). `~/.config/goose/config.yaml` for global settings. |
| **Custom Commands** | Recipe system. A Recipe = instructions (system prompt) + initial prompt + list of extensions (MCP servers) + parameters + sub-recipes. |
| **Agent Definitions** | Recipes serve as agent definitions. Sub-recipes enable sub-agent patterns. |
| **Subagent Spawning** | Sub-recipes run independently for parallel work. Each sub-agent can solve tasks independently. |
| **Headless Mode** | ACP agent server over stdio. Can run autonomous mode with pre-configured recipes. |
| **Tools** | MCP-native: all capabilities come from MCP servers. Built-in developer extensions. |
| **MCP Support** | Yes. Core architecture. `goose session --with-extension` for ad-hoc MCP servers. `~/.config/goose/config.yaml` for persistent config. |
| **Config Format** | `~/.config/goose/config.yaml` (YAML). |

**Key Proprietary Elements:**
- Recipe-based architecture (unique paradigm)
- Sub-recipes for parallel work
- MCP-native (everything is an MCP extension)
- YAML config
- Contributed to Linux Foundation's Agentic AI Foundation alongside MCP and AGENTS.md

---

### 8. Aider

**Popular open-source CLI (39K+ stars), git-focused.**

| Capability | Implementation |
|---|---|
| **System Instructions** | `CONVENTIONS.md` or files specified via `read:` in config YAML. `.aider.conf.yml` for configuration. |
| **Custom Commands** | No custom slash command system. Fixed set of in-chat commands (`/add`, `/drop`, `/run`, etc.). |
| **Agent Definitions** | No dedicated agent system. Single-agent architecture. |
| **Subagent Spawning** | No built-in delegation. Single-agent model. |
| **Headless Mode** | `--message "instruction"` for single-shot execution. Python scripting via `Coder.create()` API. |
| **Tools** | File editing (whole file or diff-based), git integration, shell commands. |
| **MCP Support** | **No native MCP support.** Community workarounds exist (MCPM-Aider). Feature requested but not implemented. |
| **Config Format** | `.aider.conf.yml` (YAML). |

**Key Proprietary Elements:**
- `.aider.conf.yml` YAML config
- `CONVENTIONS.md` for instructions
- Strong git integration (auto-commit with good messages)
- No MCP, no agents, no custom commands

**Assessment:** Aider is the **least compatible** with our framework. Its single-agent, no-custom-commands architecture means the orchestrator pattern cannot be replicated.

---

## Emerging Standards and Protocols

### AGENTS.md (De Facto Standard)

- **Adoption:** 60,000+ open-source projects. Supported by Codex, OpenCode, Gemini CLI (reads it), Copilot, Jules, Cursor, Factory, and others.
- **Status:** Formalized collaboration between OpenAI, Sourcegraph, and Google (announced July 2025).
- **Claude Code:** Does NOT natively support AGENTS.md. Uses CLAUDE.md instead. Feature request exists ([#6235](https://github.com/anthropics/claude-code/issues/6235)). Workaround: reference AGENTS.md from within CLAUDE.md, or use symlinks.
- **Content:** Build steps, test instructions, coding conventions, tool usage tips.
- **Our Strategy:** Maintain AGENTS.md as the canonical source. Generate/symlink to tool-specific files (CLAUDE.md, GEMINI.md) from it.

### Model Context Protocol (MCP)

- **Adoption:** Universal. Every tool except Aider supports MCP natively.
- **Standardization:** Created by Anthropic, adopted by OpenAI, Google, Microsoft, Block, and others.
- **Transport:** STDIO (subprocess) and StreamableHttp (HTTP endpoint) are the two main transports.
- **Our Strategy:** MCP is the strongest unification layer. A shared MCP server could expose SDLC workflow tools to any compliant CLI.

### Agent Client Protocol (ACP)

- **Purpose:** Standardizes editor-to-agent communication. Think LSP but for AI agents.
- **Adoption:** Copilot CLI, Claude Code, Codex CLI, Gemini, Goose, Cline. Supported by Zed, Neovim, JetBrains.
- **Transport:** JSON-RPC over stdio (local agents) or HTTP (remote agents).
- **Relevance:** Less relevant for our use case (we need CLI-to-CLI orchestration, not editor-to-agent), but the protocol's existence validates the multi-tool future.

---

## Common Ground (What Can Be Standardized)

### High Confidence (Shared Across Most Tools)

| Feature | Standard | Tools Supporting |
|---|---|---|
| Project instructions | AGENTS.md | Codex, OpenCode, Copilot, Gemini (partial), Goose, Cline |
| Tool extension | MCP servers | All except Aider |
| Headless execution | CLI flag (`-p`, `--prompt`, `exec`) | All tools |
| JSON output | JSON/JSON Lines format | All tools |
| File operations | Read/Write/Edit/Bash | All tools (core capabilities) |

### Medium Confidence (Shared Pattern, Different Syntax)

| Feature | Pattern | Variation |
|---|---|---|
| Custom commands | Markdown files in a directory | `.claude/commands/`, `.opencode/commands/`, `.gemini/commands/`, `.github/prompts/` |
| Agent definitions | Markdown files with metadata | `.claude/agents/`, `.github/agents/`, `.opencode/agent/` |
| Config files | JSON or YAML or TOML | Varies per tool |
| Argument passing | Template placeholders | `$ARGUMENTS`, `{{args}}`, varies |

### Low Confidence (Tool-Specific)

| Feature | Status |
|---|---|
| Subagent Task delegation | Only Claude Code and OpenCode have true named-agent delegation via Task tool |
| Hooks/Lifecycle events | Claude Code's `.claude/hooks/` is unique |
| Workflow state management | Our `workflow-state.json` pattern is custom |
| Orchestrator (Ralph) spawning | `claude -p --agent --allowedTools` is Claude-specific |

---

## Gaps and Blockers

### Critical Blockers

1. **No Universal Custom Command Standard**
   - Claude Code: `.claude/commands/*.md`
   - Copilot CLI: **No custom commands at all** (feature requested)
   - Codex: Skills with `SKILL.md` (different format)
   - OpenCode: `.opencode/commands/*.md` (closest to Claude)
   - Gemini: `.gemini/commands/*.toml` (TOML, not Markdown)
   - **Impact:** Our 25+ slash commands cannot be ported uniformly.

2. **No Universal Agent Definition Standard**
   - Claude Code: `.claude/agents/*.md` with YAML frontmatter
   - Copilot CLI: `.github/agents/*.agent.md` with different frontmatter
   - OpenCode: `.opencode/agent/*.md` with JSON config
   - Codex: `[agents]` section in `config.toml`
   - Gemini/Cline/Aider: No dedicated agent definitions
   - **Impact:** Our engineer/architect agent definitions need per-tool generation.

3. **Ralph's CLI Spawning is Claude-Specific**
   - Ralph shells out to `claude -p "prompt" --agent engineer --model opus --allowedTools "Bash,Read,Write,Edit,Glob,Grep,TodoWrite" --output-format stream-json`
   - Each tool has completely different CLI flags for headless mode
   - Output format parsing differs (stream-json vs JSON Lines vs plain text)
   - **Impact:** Ralph needs a CLI abstraction layer with per-tool adapters.

4. **No Universal Permissions/Tool Restriction Model**
   - Claude Code: `--allowedTools` flag, `.claude/settings.json` permissions
   - Codex: Approval modes, but no per-invocation tool restriction
   - Copilot: Agent-level tool configuration
   - **Impact:** Our security model (restricting engineer vs validator tools) needs per-tool implementation.

### Significant Gaps

5. **Instruction File Naming Fragmentation**
   - CLAUDE.md, AGENTS.md, GEMINI.md, .clinerules, CONVENTIONS.md
   - AGENTS.md is becoming the standard but Claude Code and Gemini don't use it natively
   - **Mitigation:** Generate all variants from one source + symlinks

6. **Config Format Fragmentation**
   - Claude: JSON (settings.json, .mcp.json)
   - Codex: TOML (config.toml)
   - OpenCode: JSON (opencode.json)
   - Gemini: JSON (settings.json) + TOML (commands)
   - Copilot: JSON (config.json, mcp-config.json)
   - Goose: YAML (config.yaml)
   - **Mitigation:** Our `config.yaml` stays as the source; generate tool-specific configs.

7. **MCP Config Location Fragmentation**
   - Claude: `.mcp.json`
   - Copilot: `.copilot/mcp-config.json` or `.github/mcp-config.json`
   - Codex: `~/.codex/config.toml` (inline)
   - OpenCode: `opencode.json` (inline under `mcp` key)
   - Gemini: `~/.gemini/settings.json` (inline under `mcpServers` key)
   - **Mitigation:** Generate per-tool MCP configs from a canonical definition.

### Minor Gaps

8. **Hooks/Lifecycle Events** - Only Claude Code supports pre/post hooks. Other tools may need MCP-based alternatives.
9. **Status Line** - Claude Code's statusLine feature is unique. Other tools don't have equivalent.
10. **Model naming** - "opus"/"sonnet"/"haiku" are Anthropic-specific. Other tools use different model identifiers.

---

## Recommended Architecture

### Approach: Canonical Source + Generation Layer

```
sdlc-framework/
  canonical/                    # Tool-neutral source of truth
    instructions.md             # Project instructions (generates CLAUDE.md, AGENTS.md, GEMINI.md)
    commands/                   # Workflow definitions (tool-neutral markdown)
      implement.md
      plan.md
      prd.md
      ...
    agents/                     # Agent definitions (tool-neutral)
      engineer.md
      architect.md
    config.yaml                 # Project settings (existing, stays)
    mcp-servers.yaml            # MCP server definitions (generates per-tool configs)

  generators/                   # Per-tool config generators
    generate.py                 # Main generation script
    adapters/
      claude.py                 # Generates .claude/ directory
      copilot.py                # Generates .github/agents/, AGENTS.md
      codex.py                  # Generates .codex/, AGENTS.md, skills/
      opencode.py               # Generates .opencode/, AGENTS.md
      gemini.py                 # Generates .gemini/, GEMINI.md
      goose.py                  # Generates goose config
      cline.py                  # Generates Cline config

  ralph/                        # Orchestrator (moved from .claude/ralph/)
    cli.py
    core/
      cli_adapter.py            # NEW: Abstract CLI interface
      adapters/
        claude_adapter.py       # claude -p ... --agent ...
        copilot_adapter.py      # gh copilot -p ...
        codex_adapter.py        # codex exec ...
        opencode_adapter.py     # opencode -p ...
        gemini_adapter.py       # gemini (headless) ...
    commands/
      orchestrator.py           # Uses cli_adapter instead of direct claude invocation
      ...

  output/                       # Generated tool-specific configs (gitignored or committed)
    .claude/                    # Generated Claude Code config
    .github/                    # Generated Copilot config
    .codex/                     # Generated Codex config
    .opencode/                  # Generated OpenCode config
    .gemini/                    # Generated Gemini config
```

### Key Design Decisions

#### 1. Canonical Command Format

```markdown
---
name: implement
description: TDD implementation of a ticket
arguments: TICKET_ID
agents: [engineer]
prerequisites: [plan, ticket]
---

# Implementation Phase

[Tool-neutral workflow instructions here, using template variables]

## Steps
1. Create feature branch from {{default_branch}}
2. TDD cycle: RED -> GREEN -> REFACTOR
3. Run quality checks: {{test_command}}, {{lint_command}}, {{typecheck_command}}
4. Commit with conventional format

## Agent Prompt
{{agent_prompt:engineer}}
```

#### 2. Canonical Agent Format

```markdown
---
name: engineer
description: Implementation, debugging, technical execution
model_preference: high  # maps to opus/gpt-4o/gemini-2.0-pro etc per tool
tools: [file_read, file_write, file_edit, bash, search, glob]
---

# Engineer Agent

You are the Engineer agent - responsible for implementation...

[Tool-neutral instructions]
```

#### 3. CLI Adapter Interface (Python)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class CLIResult:
    status: str          # "success", "failure", "timeout"
    output: str          # Parsed result text
    raw_output: str      # Full stdout+stderr
    exit_code: int

class CLIAdapter(ABC):
    """Abstract interface for LLM CLI tool invocation."""

    @abstractmethod
    def invoke(
        self,
        prompt: str,
        agent: str | None = None,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
        timeout_minutes: int = 30,
    ) -> CLIResult:
        """Invoke the CLI tool in headless mode."""
        ...

    @abstractmethod
    def parse_output(self, raw_output: str) -> str:
        """Parse tool-specific output format to extract result."""
        ...

    @abstractmethod
    def get_command(self, prompt: str, **kwargs) -> list[str]:
        """Build the CLI command without executing it."""
        ...
```

#### 4. MCP as the Unification Layer

The strongest cross-tool capability is MCP. Consider building an **SDLC MCP Server** that exposes workflow tools:

```
SDLC MCP Server Tools:
- sdlc_get_next_ticket      # Get next eligible ticket
- sdlc_mark_complete        # Mark ticket as done
- sdlc_mark_blocked         # Mark ticket as blocked
- sdlc_create_pr            # Create PR for current branch
- sdlc_validate             # Run validation checks
- sdlc_get_workflow_state   # Get current workflow state
- sdlc_update_system_doc    # Update SYSTEM.md
```

This MCP server would work with **any** MCP-compliant CLI tool, providing the workflow capabilities currently embedded in Ralph's Python code and Claude Code commands.

---

## Migration Effort Estimate

### What Changes

| Component | Effort | Notes |
|---|---|---|
| **CLAUDE.md -> canonical instructions.md** | Low | Extract tool-neutral content, add generation for CLAUDE.md/AGENTS.md/GEMINI.md |
| **`.claude/commands/` -> canonical commands/** | Medium | 25+ commands need tool-neutral format. OpenCode is nearly 1:1. Copilot has no equivalent. Codex needs Skills conversion. Gemini needs TOML conversion. |
| **`.claude/agents/` -> canonical agents/** | Medium | 2 agents. Frontmatter differs per tool. Need generation for each format. |
| **Ralph CLI invocation** | High | `invoke_claude()` and `invoke_validator()` need adapter pattern. Each tool has different flags, output formats, and agent invocation methods. |
| **Ralph output parsing** | Medium | `parse_stream_json_result()` is Claude-specific. Need per-tool parsers. |
| **`.claude/settings.json`** | Low | Generate per-tool permission/config files. |
| **`.mcp.json`** | Low | Generate per-tool MCP configs from canonical definition. |
| **`.claude/hooks/`** | Medium-High | TypeScript hooks are Claude-specific. No cross-tool equivalent. May need MCP-based alternatives. |
| **`.claude/prompts/`** | Low | Template prompts are just text. Minor per-tool formatting. |
| **Generator scripts** | High | New component. ~7 adapters to build and maintain. |
| **SDLC MCP Server** | High | New component. Would provide the strongest cross-tool unification. |
| **Documentation** | Medium | Getting started guides per tool. |

### What Stays the Same

| Component | Notes |
|---|---|
| `config.yaml` | Project settings remain the canonical config |
| `docs/` directory structure | Templates, guides, workflow docs are tool-neutral |
| `workflow-state.json` | State management is tool-neutral |
| `docs/WORKFLOW.md` | Process documentation is tool-neutral |
| Ralph core logic | Orchestration logic (get_next, mark_blocked, pr_flow) is tool-neutral |
| PM integrations | GitHub/Asana/GitLab PM tools are tool-neutral |
| Git operations | All git operations are tool-neutral |

### Estimated Timeline

| Phase | Duration | Description |
|---|---|---|
| Phase 1: Canonical format design | 1-2 weeks | Define canonical command/agent/instruction formats |
| Phase 2: Generator framework | 2-3 weeks | Build generation layer with Claude adapter (proving existing functionality) |
| Phase 3: OpenCode adapter | 1 week | Closest mapping, validates the approach |
| Phase 4: Codex adapter | 1-2 weeks | Skills conversion, TOML config generation |
| Phase 5: Copilot adapter | 1-2 weeks | Agent definitions, limited by no custom commands |
| Phase 6: Gemini adapter | 1 week | TOML commands, GEMINI.md generation |
| Phase 7: Ralph CLI abstraction | 2-3 weeks | Adapter pattern for all CLI invocations |
| Phase 8: SDLC MCP Server | 2-3 weeks | Optional but high-value cross-tool unification |
| Phase 9: Testing + docs | 1-2 weeks | Per-tool getting started guides, integration tests |

**Total: 12-19 weeks for full platform-agnostic support.**

### Recommended Phased Approach

1. **Phase 1 (Quick Win):** Generate AGENTS.md from CLAUDE.md content. Symlink approach for immediate multi-tool instruction support.
2. **Phase 2 (Foundation):** Build the canonical format and Claude adapter (proving no regression).
3. **Phase 3 (First New Tool):** OpenCode adapter (closest mapping, validates architecture).
4. **Phase 4 (High Value):** SDLC MCP Server (works with all MCP-compliant tools immediately).
5. **Phase 5+ (Expand):** Additional tool adapters as needed.

---

## Alternative Approaches Considered

### 1. MCP-Only Approach
Build everything as an MCP server and abandon CLI-specific configs entirely.
- **Pro:** Maximum portability, single implementation.
- **Con:** MCP can't replace system instructions (AGENTS.md/CLAUDE.md), custom commands, or agent definitions. Only covers tool/action layer.
- **Verdict:** MCP is part of the solution but not sufficient alone.

### 2. Lowest Common Denominator
Only use features available in ALL tools.
- **Pro:** Simplest implementation.
- **Con:** Loses most of our framework's value (no custom commands, no agent delegation, no orchestration).
- **Verdict:** Too limiting. The framework's value IS in the advanced features.

### 3. Polyglot Config Generation (Recommended)
Canonical format + per-tool generators.
- **Pro:** Full fidelity per tool, graceful degradation where features missing, single source of truth.
- **Con:** Maintenance burden of multiple generators.
- **Verdict:** Best balance of portability and capability.

---

## Sources

- [GitHub Copilot CLI GA Announcement](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/)
- [GitHub Copilot CLI Custom Instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [GitHub Copilot CLI Custom Agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli)
- [Copilot CLI Custom Slash Commands Feature Request #618](https://github.com/github/copilot-cli/issues/618)
- [Copilot CLI Custom Slash Commands Feature Request #1113](https://github.com/github/copilot-cli/issues/1113)
- [Copilot CLI MCP Server Configuration](https://deepwiki.com/github/copilot-cli/5.3-mcp-server-configuration)
- [Copilot CLI Enhanced Agents and Context Management](https://github.blog/changelog/2026-01-14-github-copilot-cli-enhanced-agents-context-management-and-new-ways-to-install/)
- [Copilot CLI Non-Interactive Mode Issue #1181](https://github.com/github/copilot-cli/issues/1181)
- [Copilot SDK --headless --stdio Breaking Change #530](https://github.com/github/copilot-sdk/issues/530)
- [OpenAI Codex CLI GitHub](https://github.com/openai/codex)
- [Codex CLI AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md/)
- [Codex CLI Config Basics](https://developers.openai.com/codex/config-basic/)
- [Codex CLI Advanced Configuration](https://developers.openai.com/codex/config-advanced/)
- [Codex CLI Non-Interactive Mode](https://developers.openai.com/codex/noninteractive/)
- [Codex CLI Skills](https://developers.openai.com/codex/skills)
- [Codex CLI Slash Commands](https://developers.openai.com/codex/cli/slash-commands/)
- [Codex CLI MCP Commands](https://deepwiki.com/openai/codex/6.3-mcp-cli-commands)
- [OpenCode CLI GitHub](https://github.com/opencode-ai/opencode)
- [OpenCode Agents Documentation](https://opencode.ai/docs/agents/)
- [OpenCode Commands Documentation](https://opencode.ai/docs/commands/)
- [OpenCode Config Documentation](https://opencode.ai/docs/config/)
- [OpenCode MCP Servers Documentation](https://opencode.ai/docs/mcp-servers/)
- [OpenCode Rules Documentation](https://opencode.ai/docs/rules/)
- [OpenCode Subagent Feature Request #1293](https://github.com/sst/opencode/issues/1293)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI Custom Slash Commands](https://geminicli.com/docs/cli/custom-commands/)
- [Gemini CLI Configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/configuration.md)
- [Cline CLI 2.0 Announcement](https://cline.bot/cli)
- [Cline CLI Overview](https://docs.cline.bot/cline-cli/overview)
- [Goose CLI GitHub](https://github.com/block/goose)
- [Goose MCP Setup Guide](https://skywork.ai/blog/how-to-use-goose-cli-with-mcp-servers-guide/)
- [Aider Documentation](https://aider.chat/docs/)
- [Aider Scripting](https://aider.chat/docs/scripting.html)
- [Aider Conventions](https://aider.chat/docs/usage/conventions.html)
- [Aider MCP Feature Request #4506](https://github.com/aider-ai/aider/issues/4506)
- [AGENTS.md Specification](https://agents.md/)
- [AGENTS.md GitHub](https://github.com/agentsmd/agents.md)
- [Claude Code AGENTS.md Feature Request #6235](https://github.com/anthropics/claude-code/issues/6235)
- [CLAUDE.md to AGENTS.md Migration Guide](https://solmaz.io/log/2025/09/08/claude-md-agents-md-migration-guide/)
- [Agent Client Protocol](https://agentclientprotocol.com/)
- [ACP Support in Copilot CLI](https://github.blog/changelog/2026-01-28-acp-support-in-copilot-cli-is-now-in-public-preview/)
- [The 2026 Guide to Coding CLI Tools](https://www.tembo.io/blog/coding-cli-tools-comparison)
- [10 Claude Code Alternatives](https://www.digitalocean.com/resources/articles/claude-code-alternatives)
