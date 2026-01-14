# What's Next - Workflow State & Recommendations

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Analyze current state and recommend next actions.**

## Purpose

This command works from a fresh context to:
1. Discover where we are in the SDLC workflow
2. Find outstanding or incomplete work
3. Recommend the next action to take

**Run this when:** Starting a new session, unsure what to work on, or need to orient yourself.

## The Analysis Process

### Step 1: Check Git State

```bash
# Current branch and uncommitted work
git branch --show-current
git status --short

# Recent commits
git log --oneline -5

# Open PRs
gh pr list --state open 2>/dev/null || echo "No GitHub CLI or not a repo"
```

### Step 2: Check Document State

Read and assess status of each artifact type:

**Discovery** (`docs/discovery/*.md`):
- Do any discovery docs exist?
- What's the status of each? (NOT STARTED / IN PROGRESS / READY FOR PLANNING)
- Is there an in-progress discovery for the current iteration?

**PRDs** (`docs/prds/`):
- List all PRDs
- Check status of each (DRAFT / APPROVED)
- Any approved PRDs without a corresponding plan?

**Plans** (`docs/plans/`):
- List all plans
- Check status of each (DRAFT / APPROVED)
- Do approved plans have ticket IDs populated?
- Check `PROGRESS.md` for in-progress work

**RCAs** (`docs/rca/`):
- Any open RCAs? (status = ANALYZING or FIX PROPOSED)
- Any that need implementation?

**Execution Reports** (`docs/execution-reports/`):
- Any recent implementations without execution reports?

**System Reviews** (`docs/system-reviews/`):
- Any execution reports without corresponding system reviews?

### Step 3: Identify Workflow Position

Based on artifacts, determine:

| Situation | You Are At | Next Action |
|-----------|------------|-------------|
| No discovery docs | Beginning | `/discover` |
| Discovery = IN PROGRESS | Discovery | Continue `/discover` |
| Discovery = READY, no PRDs | Pre-PRD | `/prd` |
| PRD = DRAFT | PRD review | Get approval or revise |
| PRD = APPROVED, no plan | Pre-planning | `/plan` |
| Plan = DRAFT | Plan review | Get approval or revise |
| Plan = APPROVED, no ticket IDs | Pre-tickets | `/ticket` |
| Plan has tickets, none started | Pre-implement | `/implement [ticket-id]` |
| Work in progress | Implementation | Continue `/implement` |
| Tests passing, no PR | Pre-PR | `/pr` |
| PR open | Validation | `/validate` |
| PR merged, no exec report | Post-merge | `/execution-report` |
| Exec report exists, no review | Post-report | `/system-review` |
| Open RCA | Bug workflow | `/hotfix` or continue RCA |

### Step 4: Output Recommendations

## Output Format

```markdown
## Current State

**Branch:** [current branch]
**Uncommitted Changes:** [yes/no - summary]
**Open PRs:** [count and titles]

## Document Status

| Document | Status | Notes |
|----------|--------|-------|
| Discovery | [status] | [notes] |
| PRDs | [count] DRAFT / [count] APPROVED | [notes] |
| Plans | [count] DRAFT / [count] APPROVED | [notes] |
| Active Tickets | [list from PROGRESS.md] | |
| Open RCAs | [count] | [notes] |

## Outstanding Work

1. [Incomplete item 1]
2. [Incomplete item 2]

## Recommended Next Action

**Run:** `/command-name [args]`

**Why:** [Brief explanation of why this is the logical next step]

## Alternative Actions

- `/alternative-1` - [when you'd choose this instead]
- `/alternative-2` - [when you'd choose this instead]
```

## DO NOT

- Make assumptions about priorities - present options if multiple paths exist
- Skip reading actual document status fields
- Recommend skipping phases without explicit user approval
- Start implementing without identifying the next logical step

## Arguments

$ARGUMENTS

If arguments provided (e.g., `/whats-next auth-feature`), focus analysis on that specific feature's workflow state.
