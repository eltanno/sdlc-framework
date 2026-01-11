# Guide - SDLC Framework Help

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Help users understand the workflow and find their next step.**

## Purpose

This command helps engineers who are new to Claude Code or this SDLC framework. It performs the same state analysis as `/whats-next`, but presents findings in a friendly, explanatory way.

**The difference:**
- `/whats-next` → Terse, action-focused output for experienced users
- `/guide` → Conversational, explains the "why" for new users

---

## The Analysis Process

Perform the exact same analysis as `/whats-next`:

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

**Discovery** (`docs/discovery.md`):
- Does it exist?
- What's the status field? (NOT STARTED / IN PROGRESS / READY FOR PLANNING)

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

Use the same mapping as `/whats-next`:

| Situation | You Are At | Next Action |
|-----------|------------|-------------|
| No discovery.md | Beginning | `/discover` |
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

---

## Output Format (Friendly Version)

Present findings conversationally, explaining the workflow as you go.

### Opening (Always Include)

```markdown
## SDLC Framework Guide

This framework helps you build features with Claude's assistance. You stay in control
of decisions while Claude handles implementation. Here's where things stand:
```

### Current State (Based on Analysis)

Adapt based on what you found:

**If fresh project (no discovery.md):**
```markdown
## Where You Are

You're at the very beginning - no features have been started yet.

### The Workflow

This framework follows a structured path:

1. **Discover** - Have a conversation about what you want to build
2. **PRD** - Claude writes formal requirements (you review)
3. **Plan** - Claude designs the technical approach (you review)
4. **Tickets** - Creates tasks in your project management tool
5. **Implement** - Claude writes code using test-driven development
6. **PR & Validate** - Code review and merge

### Your Next Step

Run `/discover` and describe what you want to build. Just talk naturally -
explain the feature, the problem it solves, who it's for. Claude will ask
clarifying questions.

**Example:** "I want to add user authentication with email/password login"
```

**If mid-discovery:**
```markdown
## Where You Are

You're in the **Discovery** phase - still gathering requirements for your feature.

The discovery document at `docs/discovery.md` has status: [STATUS]

### What This Means

Discovery is a conversation where you define what you're building. Once you've
covered the requirements, constraints, and scope, you'll mark it "READY FOR PLANNING"
and move to creating a formal PRD.

### Your Next Step

Continue the discovery conversation. Review `docs/discovery.md` to see what's
been captured so far. When you're satisfied, update the status to READY FOR PLANNING.
```

**If has PRD, needs plan:**
```markdown
## Where You Are

You have an approved PRD for **[feature name]** - requirements are defined!

Now you need a technical plan before implementation.

### What This Means

The PRD says *what* to build. The plan says *how* to build it - architecture,
file structure, which tickets to create. Claude will analyze the codebase and
design an approach.

### Your Next Step

Run `/plan [feature-name]` to generate the technical plan.

After reviewing it, mark it APPROVED to proceed.
```

**If has plan with tickets, ready to implement:**
```markdown
## Where You Are

You have an approved plan for **[feature name]** with [N] tickets ready.

You're at the implementation phase!

### What This Means

Each ticket is a focused piece of work. Claude implements them using TDD
(test-driven development) - tests first, then code to pass the tests.

### Your Tickets

[List tickets from plan/PROGRESS.md]

### Your Next Step

Run `/implement [TICKET-ID]` to start work on the next ticket.

Or, for hands-off implementation, run `/ralph-prd [prd-path]` to let Claude
work through all tickets autonomously.
```

**If on feature branch with uncommitted work:**
```markdown
## Where You Are

You're on branch `[branch-name]` with changes in progress.

**Modified files:** [count]
**Uncommitted:** [list or summary]

### What This Means

There's work in progress that hasn't been committed yet. You should either
continue working or commit what you have.

### Your Next Step

- Review the changes: `git diff`
- If ready, commit and continue to next ticket
- If not ready, continue implementation with `/implement [TICKET-ID]`
```

**If PR open:**
```markdown
## Where You Are

You have an open pull request: **[PR title]** (#[number])

### What This Means

The code is ready for review. The `/validate` command runs final checks
to ensure everything passes before merge.

### Your Next Step

Run `/validate` to run pre-merge checks. If everything passes, merge the PR.
```

### Always End With

```markdown
---

## Quick Reference

| Command | What It Does |
|---------|--------------|
| `/guide` | This help (you're here!) |
| `/whats-next` | Detailed status for experienced users |
| `/discover` | Start defining a new feature |
| `/status` | Quick project overview |

**Stuck?** Just describe your problem in plain English - Claude will help.

**More detail?** See `WORKFLOW.md` for complete documentation.
```

---

## Tone Guidelines

- **Friendly, not formal** - "You're in good shape" not "Status: nominal"
- **Explain the why** - Don't just say what to do, explain why that's the next step
- **Encouraging** - They're learning something new
- **Concise but complete** - Give them what they need, not everything possible
- **No jargon** - Avoid AI terminology (tokens, context, agents) unless necessary

## What NOT to Do

- Don't dump the entire WORKFLOW.md on them
- Don't show raw status tables (that's what `/whats-next` is for)
- Don't assume they know Claude Code commands
- Don't use unexplained technical terms
- Don't skip the state analysis - always check where they actually are

## Arguments

$ARGUMENTS

If they provide context (e.g., `/guide implement` or `/guide prd`), focus your explanation on that specific phase while still checking current state.
