# What's Next - Workflow State & Recommendations

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. This is a coordination task - do it yourself.**

Analyze current state, show workflow progress, and recommend next actions.

## Purpose

This command works from a fresh context to:
1. Discover where we are in the SDLC workflow
2. Show a status dashboard of all artifacts and git state
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

# Open PRs/MRs (check repo.type in config.yaml)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")
if [ "$REPO_TYPE" = "gitlab" ]; then
  glab mr list 2>/dev/null || echo "No GitLab remote"
else
  gh pr list 2>/dev/null || echo "No GitHub remote"
fi
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
| Plan has tickets, none started | Ready to execute | `/ralph-loop` |
| Ralph in progress / tickets open | Implementation | Monitor `/ralph-loop` or `/ticket-reset` if blocked |
| All tickets merged, no exec report | Post-merge | `/execution-report` |
| Exec report exists, no review | Post-report | `/system-review` |
| Review done, no release | Pre-release | `/release` |
| Bugs reported | Bug workflow | `/playtest-loop` or `/rca` then fix |

### Step 4: Output

## Output Format

```markdown
# Workflow Status

**Generated:** YYYY-MM-DD HH:MM
**Branch:** [current branch]
**Active Phase:** [Discovery / PRD / Plan / Tickets / Execution (Ralph) / Report / Review / Release / None]

## Workflow Progress

```
[x] Discovery   → document.md (APPROVED)
[x] PRD         → prd.md (APPROVED)
[x] Plan        → plan.md (APPROVED)
[x] Tickets     → TASK-123, TASK-124
[ ] Ralph Loop  → not started
[ ] Exec Report → not started
[ ] Review      → not started
[ ] Release     → not started
```

## Documents

| Type | Document | Status | Notes |
|------|----------|--------|-------|
| Discovery | topic.md | DRAFT/APPROVED | |
| PRD | feature.md | DRAFT/APPROVED | |
| Plan | feature.md | DRAFT/APPROVED | Tickets: TASK-XXX |

## Git

- **Uncommitted Changes:** Yes/No
- **Open PRs:** [list or none]
- **Recent Commits:** [last 3-5]

## Outstanding Work

1. [Incomplete item 1]
2. [Incomplete item 2]

## Recommended Next Action

**Run:** `/command-name [args]`

**Why:** [Brief explanation of why this is the logical next step]

## Alternative Actions

- `/alternative-1` - [when you'd choose this instead]
- `/alternative-2` - [when you'd choose this instead]

## Quick Commands

| Action | Command |
|--------|---------|
| Start discovery | `/discover {topic}` |
| Create PRD | `/prd {feature}` |
| Create plan | `/plan {feature}` |
| Create tickets | `/ticket` |
| Execute all tickets | `/ralph-loop` |
| Reset blocked ticket | `/ticket-reset {id}` |
| Document results | `/execution-report` |
| Review process | `/system-review` |
| Ship it | `/release` |
| Find & fix bugs | `/playtest-loop` |
```

## What to Watch For

### Red Flags
- DRAFT documents older than a week
- PRDs without ticket IDs
- Multiple features in progress simultaneously
- Blocked tickets with no resolution

### Good Signs
- Clear linear progression through phases
- All documents approved before moving on
- Tickets linked in plans
- Commits reference ticket IDs

## Tone

- Be conversational, not robotic — explain the "why" behind recommendations
- If this looks like a fresh project or new user, briefly explain what each phase does
- Keep it concise but helpful — don't dump the entire workflow docs

## DO NOT

- Make assumptions about priorities - present options if multiple paths exist
- Skip reading actual document status fields
- Recommend skipping phases without explicit user approval
- Start implementing without identifying the next logical step

## Arguments

$ARGUMENTS

If arguments provided (e.g., `/whats-next auth-feature`), focus analysis on that specific feature's workflow state.
