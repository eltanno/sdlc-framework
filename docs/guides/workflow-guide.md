# Workflow Guide

A practical guide to the SDLC workflow process - from idea to shipped code.

## The Big Picture

The workflow has two stages:

```
PLANNING (What & How)          EXECUTION (Build & Ship)
─────────────────────          ─────────────────────────
discover → prd → plan → ticket → implement → pr → validate → release
```

**Planning** defines what you're building. **Execution** builds and ships it.

## Quick Reference

| Phase | Command | Who Does It | Output |
|-------|---------|-------------|--------|
| Prime | `/prime` | Self | Context loaded |
| Discover | `/discover` | Self (interactive) | `docs/discovery/*.md` |
| PRD | `/prd` | Architect agent | `docs/prds/*.md` |
| Plan | `/plan` | Architect agent | `docs/plans/*.md` |
| Ticket | `/ticket` | Haiku agent | Tickets in PM tool |
| Implement | `/implement` | Engineer agent | Code on feature branch |
| PR | `/pr` | Haiku agent | Pull request |
| Validate | `/validate` | Engineer agent | Validation report |
| Release | `/release` | Self | Updated README |

---

## Planning Phases

### 1. Prime (`/prime`)

**What:** Load project context into Claude's memory.

**When:** Start of any session, or when switching tasks.

**How:**
```
/prime
```

Claude reads the codebase structure, documentation, and current state. This ensures Claude understands the project before making changes.

**Output:** Context summary (not saved to file).

---

### 2. Discover (`/discover`)

**What:** Interactive conversation to understand what you want to build.

**When:** Starting a new feature or iteration.

**How:**
```
/discover
```

Claude asks questions about:
- What problem are you solving?
- Who are the users?
- What's the scope?
- What are the constraints?

**Output:** `docs/discovery/YYYY-MM-DD-{name}.md`

**Example session:**
```
You: /discover
Claude: What would you like to build?
You: A user authentication system
Claude: What authentication methods do you need?
You: Email/password and Google OAuth
Claude: Any specific security requirements?
You: Yes, we need 2FA support
... (continues until requirements are clear)
```

**Status progression:** NOT STARTED → IN PROGRESS → READY FOR PLANNING

---

### 3. PRD (`/prd`)

**What:** Create a formal Product Requirements Document.

**When:** After discovery is approved.

**How:**
```
/prd
```

The architect agent creates a document with:
- Functional requirements
- Acceptance criteria (testable!)
- User stories
- Non-functional requirements
- Ticket definitions

**Output:** `docs/prds/YYYY-MM-DD-{feature}.md`

**Key point:** PRD defines **WHAT** to build, not HOW.

**Status progression:** DRAFT → APPROVED (you review and approve)

---

### 4. Plan (`/plan`)

**What:** Create a technical implementation plan.

**When:** After PRD is approved.

**How:**
```
/plan
```

The architect agent creates a document with:
- Technical architecture
- Design decisions with rationale
- File structure
- Dependencies
- Implementation phases
- Ticket breakdown with complexity estimates

**Output:** `docs/plans/YYYY-MM-DD-{feature}.md`

**Key point:** Plan defines **HOW** to build what the PRD specified.

**Status progression:** DRAFT → APPROVED (you review and approve)

---

### 5. Ticket (`/ticket`)

**What:** Create tasks in your project management tool.

**When:** After plan is approved.

**How:**
```
/ticket
```

Creates tickets from the plan's ticket table in:
- GitHub Issues
- Trello
- Asana
- Linear
- Or local PROGRESS.md

**Output:** Tickets with IDs, plan updated with ticket IDs.

**This marks the end of Planning.** You now have a roadmap with trackable tasks.

---

## Execution Phases

### 6. Implement (`/implement`)

**What:** Build the feature using TDD.

**When:** After tickets are created.

**How:**
```
/implement
```

Or for a specific ticket:
```
/implement TICKET-123
```

The engineer agent:
1. Creates a feature branch
2. Writes failing tests (RED)
3. Writes code to pass tests (GREEN)
4. Refactors while keeping tests green (REFACTOR)
5. Runs all validation (lint, tests, build)
6. Commits the work

**Output:** Code and tests on `feature/TICKET-{id}-{description}` branch.

**Key point:** Tests are written BEFORE implementation code.

---

### 7. PR (`/pr`)

**What:** Create a pull request.

**When:** After implementation passes validation.

**How:**
```
/pr
```

Creates a GitHub PR with:
- Description of changes
- Link to ticket
- Test results

**Output:** Open pull request.

---

### 8. Validate (`/validate`)

**What:** Final pre-merge validation.

**When:** After PR is created.

**How:**
```
/validate
```

The engineer agent checks:
- All tests pass
- Linting passes
- Acceptance criteria from PRD are met
- No security issues
- Documentation is complete

**Output:** Validation report (pass/fail with details).

---

### 9. Release (`/release`)

**What:** Update documentation to reflect what was shipped.

**When:** After PR is merged.

**How:**
```
/release
```

Updates README.md with:
- New features
- Changed behaviors
- Configuration options

**Output:** Updated README.md.

**Key point:** README should always reflect the current state of the software.

---

## Optional Phases

### Research (`/research`)

**What:** Autonomous technical investigation.

**When:** Anytime you need to explore a topic.

**How:**
```
/research "how do WebSockets work in React Native"
```

The general-purpose agent investigates and documents findings.

**Output:** `docs/research/YYYY-MM-DD-{topic}.md`

**Different from discover:** Research is autonomous (agent works alone), discover is interactive (conversation with you).

---

### Hotfix (`/hotfix`)

**What:** Emergency fix for production issues.

**When:** Production is down or there's a critical bug.

**How:**
```
/hotfix
```

Abbreviated workflow:
1. Skip discovery/PRD/plan
2. Fix the issue
3. Still requires tests and PR
4. Document with RCA after fix is deployed

**Use sparingly** - only for genuine emergencies.

---

### RCA (`/rca`)

**What:** Root Cause Analysis for bugs.

**When:** Bug exists but cause is unclear.

**How:**
```
/rca
```

The agent:
1. Gathers issue details
2. Reproduces the problem
3. Identifies root cause
4. Proposes fix

**Output:** `docs/rca/YYYY-MM-DD-{issue}.md`

---

## Autonomous Mode (Ralph)

For hands-off implementation of an entire PRD:

```
/ralph-prd docs/prds/YYYY-MM-DD-feature.md
```

Ralph loops through:
1. Find next ticket
2. Implement it
3. Validate
4. Commit and PR
5. Repeat until done

**Best for:** Well-defined features with clear acceptance criteria.

**Not for:** Unclear requirements, new patterns, or debugging.

See `docs/guides/multiple-ralph-loops.md` for running multiple ralph instances.

---

## Typical Workflow Example

Building a user profile feature:

```bash
# 1. Load context
/prime

# 2. Discuss requirements (interactive)
/discover
# ... conversation about user profiles ...
# Claude creates docs/discovery/2026-01-18-user-profiles.md
# You review and approve

# 3. Create PRD (delegated to architect)
/prd
# Claude creates docs/prds/2026-01-18-user-profiles.md
# You review and approve

# 4. Create plan (delegated to architect)
/plan
# Claude creates docs/plans/2026-01-18-user-profiles.md
# You review and approve

# 5. Create tickets (delegated to haiku)
/ticket
# Creates AUCT-0161, AUCT-0162, AUCT-0163 in GitHub Issues

# 6. Implement each ticket (delegated to engineer)
/implement AUCT-0161
# ... engineer builds and tests ...

# 7. Create PR (delegated to haiku)
/pr

# 8. Validate (delegated to engineer)
/validate

# 9. Merge PR (you do this in GitHub)

# 10. Repeat 6-9 for remaining tickets

# 11. Update README (self)
/release
```

---

## Document Hierarchy

```
docs/
├── discovery/           # What we're building (per iteration)
│   └── YYYY-MM-DD-v1.md
├── prds/                # Requirements (per feature)
│   └── YYYY-MM-DD-feature.md
├── plans/               # Technical approach (per feature)
│   └── YYYY-MM-DD-feature.md
├── research/            # Technical investigations
│   └── YYYY-MM-DD-topic.md
├── rca/                 # Bug analysis
│   └── YYYY-MM-DD-issue.md
├── execution-reports/   # What was built vs planned
│   └── YYYY-MM-DD-feature.md
├── system-reviews/      # Process improvements
│   └── YYYY-MM-DD-feature.md
├── guides/              # How-to guides (like this one)
│   └── *.md
└── templates/           # Document templates
    └── *.md
```

---

## Key Rules

1. **Always prime first** - Load context before starting work
2. **Plan before code** - Don't skip to implementation
3. **Test before code** - TDD is mandatory
4. **Commit artifacts immediately** - Documents must be committed before proceeding
5. **Phase gates** - Each phase needs approval before the next
6. **Link everything** - Commits → tickets → PRD → discovery

---

## Common Mistakes

| Mistake | Why It's Bad | What To Do Instead |
|---------|--------------|-------------------|
| Skipping discover | Requirements unclear, rework later | Always start with `/discover` |
| Huge PRDs | Too much scope, never finishes | One feature per PRD |
| Vague acceptance criteria | Can't verify completion | Make criteria testable |
| Skipping tests | Bugs, regressions | Always write tests first |
| Not committing docs | Lost on branch switch | Commit immediately after creation |
| Implementing without plan | Chaotic, inconsistent | Get plan approved first |

---

## Getting Help

- `/guide` - Interactive help for new users
- `/status` - Check current workflow state
- `/whats-next` - Get recommendations for next step
- `WORKFLOW.md` - Full reference documentation
