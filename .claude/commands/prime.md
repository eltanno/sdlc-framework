# Prime - Context Loading

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Load comprehensive project context before any work begins.**

## Purpose

Prime ensures you understand the codebase, conventions, and current state before starting any task. This prevents "jumping in without understanding" - a common failure mode.

**Run this before:** `/plan`, `/implement`, `/hotfix`, or any significant work.

## The Prime Process

### Step 1: Project Structure

```bash
# Get file tree
git ls-files | head -100

# Directory structure
tree -L 3 -I 'node_modules|__pycache__|.git|dist|build|.next' 2>/dev/null || find . -type d -maxdepth 3 | grep -v 'node_modules\|__pycache__\|.git\|dist\|build'
```

### Step 2: Documentation Review

Read these files in order (if they exist):

1. `CLAUDE.md` - Project conventions and instructions
2. `README.md` - Project overview
3. `docs/discovery.md` - Product vision
4. `docs/prds/` - Latest PRD (most recent by date)
5. `docs/plans/` - Latest plan (most recent by date)
6. `config.yaml` - SDLC configuration (project root)

### Step 3: Technical Context

Identify and skim:

- Entry points (`main.py`, `index.ts`, `app.py`, etc.)
- Configuration files (`package.json`, `pyproject.toml`, `tsconfig.json`)
- Database schemas or models directory
- API routes or endpoints
- Test structure

### Step 4: Current State

```bash
# Current branch and status
git branch --show-current
git status --short

# Recent commits (context on recent work)
git log --oneline -10

# Any uncommitted work?
git diff --stat
```

### Step 5: Active Work

Check for in-progress work:

- `docs/plans/PROGRESS.md` - Implementation tracking
- Open PRs: `gh pr list` or `glab mr list`
- Recent branches: `git branch --sort=-committerdate | head -5`

## Output Format

After priming, provide this summary:

```markdown
## Context Loaded

**Project:** [Name from README or package.json]
**Tech Stack:** [Languages, frameworks, databases]
**Current Branch:** [branch-name]
**Recent Focus:** [What recent commits show]

### Key Files
- Entry: [main entry points]
- Config: [key config files]
- Tests: [test structure]

### Active Documents
- Discovery: [status - exists/missing]
- PRD: [latest or none]
- Plan: [latest or none]
- Progress: [in-progress items or none]

### Conventions (from CLAUDE.md)
- [Key convention 1]
- [Key convention 2]
- [Key convention 3]

### Ready For
Based on current state, you can:
- [Suggested next action based on what's found]
```

## When to Prime

| Situation | Action |
|-----------|--------|
| Starting new session | Always prime |
| Switching tasks | Prime if context changed |
| Before `/plan` | Prime to understand current state |
| Before `/implement` | Prime if >1 hour since last prime |
| Before `/hotfix` | Quick prime (steps 4-5 minimum) |

## Quick Prime (Abbreviated)

For minor tasks or recent context, use quick prime:

```bash
git status && git log --oneline -5
```

Then skim the most relevant doc for your task.

## DO NOT

- Skip priming and assume you remember the context
- Start implementation without understanding conventions
- Ignore existing in-progress work
- Miss active PRs or branches

## Arguments

$ARGUMENTS

If arguments provided, focus priming on that specific area of the codebase.
