# Workflow Transition Guide: From LLM Orchestration to Human-Managed Parallel Sessions

**Date:** 2026-01-11
**Audience:** AI novice engineers transitioning from autonomous workflows
**Purpose:** Guide for adopting Boris Cherny-inspired workflow patterns

---

## 1. Executive Summary

### What's Changing

We are enhancing our workflow with **two-level planning** and adopting Boris Cherny's best practices while keeping what works.

| Before | After |
|--------|-------|
| Ralph dives straight into implementation | Ralph plans each ticket before coding |
| Single level of planning (/plan phase) | Strategic (human-reviewed) + Tactical (per-ticket) planning |
| Trust the agent to figure it out | Verify at every step |
| CLAUDE.md updated occasionally | CLAUDE.md as living document (updated weekly) |

**Two workflow options:**
1. **Improved Ralph** - Autonomous with two-level planning (good for well-defined PRDs)
2. **Boris-style Sessions** - Human-managed parallel sessions (good for complex/exploratory work)

### Why This Change

**Boris's insight:** "Most people ask: 'How do I get better outputs from AI?' Boris asks: 'How do I build a system where AI reliably produces what I need?'"

The autonomous approach works for simple, well-defined tasks but struggles with:
- Complex multi-step implementations
- Situations requiring judgment calls
- Recovery from unexpected errors
- Work that needs human context

### Benefits for Novice Engineers

1. **More control** - You always know what's happening
2. **Easier debugging** - Each session has one focused task
3. **Better learning** - You see how Claude approaches problems
4. **Lower risk** - Mistakes are contained to single sessions
5. **Gradual autonomy** - Start supervised, increase independence over time

---

## 2. Current vs Boris Workflow Comparison

### Side-by-Side Comparison

| Aspect | Current (Autonomous) | Boris (Human-Managed) |
|--------|---------------------|----------------------|
| **Control** | LLM orchestrates via `/ralph-prd` | Human orchestrates via multiple sessions |
| **Sessions** | Single long-running loop | 10-15 parallel focused sessions |
| **Task scope** | LLM picks next ticket | Human assigns specific task per session |
| **Verification** | LLM decides when done | Human verifies + Claude re-verifies |
| **Context** | Accumulates in one context | Fresh context per session |
| **Recovery** | `NEEDS_HUMAN_REVIEW` exit | Human redirects immediately |
| **Learning** | CLAUDE.md updated occasionally | CLAUDE.md updated multiple times/week |
| **Model** | Mixed (sonnet for implementation) | Opus 4.5 for everything |

### Key Philosophical Differences

**Current Approach:**
- "Set it and forget it" - delegate entire PRD to ralph
- Trust LLM to make good decisions
- Intervene only when blocked
- Workflow as automation

**Boris's Approach:**
- "Distribute cognition like compute" - many workers, human dispatcher
- Trust but verify at every step
- Proactively guide each session
- Workflow as force multiplication

### What Boris Does That We Don't

1. **Plan Mode First (Always)** - Every significant task starts in Plan Mode, iterating until satisfied before execution
2. **Separate Git Checkouts** - Each terminal session has its own checkout, not just branches
3. **Mobile Sessions** - Starts long-running tasks on mobile, checks back later
4. **Multi-Agent Code Review** - Multiple subagents check PRs from different angles
5. **Aggressive CLAUDE.md Updates** - Team tags `@.claude` on PRs to update continuously
6. **PostToolUse Hooks** - Auto-formatting after every edit

### What We Do That Boris Doesn't

1. **Formal Phase Gates** - Discovery -> PRD -> Plan -> Ticket -> Implement
2. **Document Hierarchy** - Structured discovery/PRD/plan/ticket flow
3. **Autonomous Implementation Loops** - ralph-prd for hands-off execution
4. **Execution Reports & System Reviews** - Post-completion process analysis
5. **Ticket Integration** - Trello/Asana integration throughout workflow

---

## 3. What Stays the Same

### Existing Assets to Keep

Your current infrastructure is valuable and should be retained:

**Documents:**
- `CLAUDE.md` - Keep and enhance (make it a living document)
- `WORKFLOW.md` - Keep for reference and phase documentation
- `docs/templates/` - Keep all templates

**Agent Definitions:**
- `.claude/agents/engineer.md` - Keep, use for implementation tasks
- `.claude/agents/architect.md` - Keep, use for planning tasks
- Other specialized agents - Keep as needed

**Commands:**
- Keep most slash commands, but use them more intentionally
- `/prime` - Still valuable for context loading
- `/whats-next` - Use for manual status checks
- `/research` - Use for autonomous investigation tasks

### Practices That Align with Boris

You're already doing these well:

1. **TDD Workflow** - RED/GREEN/REFACTOR is the right approach
2. **Branch Naming** - `feature/TASK-{id}-{description}` convention
3. **Commit Messages** - Structured format with ticket references
4. **Document-Driven Development** - PRDs and plans before code
5. **Verification Steps** - Tests must pass before merge
6. **Artifact Persistence** - State in files, not conversation

### Commands That Remain Useful

| Command | When to Use |
|---------|-------------|
| `/prime` | Start of session, context loading |
| `/research` | Autonomous technical investigation |
| `/whats-next` | Manual status check |
| `/validate` | Pre-merge verification |
| `/execution-report` | Post-completion documentation |

---

## 4. What Changes

### Major Changes

#### 4.1. Improve `/ralph-prd` with Two-Level Planning

**What:** Keep ralph-prd but enhance it with a two-level planning approach.

**The Problem with Current Ralph:**
- Dives straight into implementation without explicit planning
- Non-deterministic decisions at each step
- No separation between "what to do" and "how to do it now"

**The Solution: Strategic + Tactical Planning**

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGIC PLANNING (/plan phase - human-reviewed)              │
│                                                                 │
│  Done BEFORE ralph runs. Saved to docs/plans/                   │
│  - Technical approach per ticket                                │
│  - Files to create/modify                                       │
│  - Key architectural decisions                                  │
│  - Acceptance criteria                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  TACTICAL PLANNING (per-ticket in ralph loop - autonomous)      │
│                                                                 │
│  Done at START of each ticket iteration:                        │
│  1. Read strategic plan from docs/plans/                        │
│  2. Check CURRENT codebase state                                │
│  3. Create micro-plan adapting to what exists now               │
│  4. Self-evaluate: Does plan address acceptance criteria?       │
│  5. If solid → execute. If not → revise first.                  │
└─────────────────────────────────────────────────────────────────┘
```

**Example Flow:**

```markdown
## Strategic Plan (from /plan phase, saved to ticket)
┌─────────────────────────────────────────────┐
│ TASK-123: User Login Endpoint               │
│                                             │
│ Approach: JWT with refresh tokens           │
│ Files: src/api/auth/login.ts, tests         │
│ Dependencies: jsonwebtoken package          │
│ Acceptance: Returns JWT, validates creds    │
└─────────────────────────────────────────────┘
         ↓ (saved to docs/plans/)

## Tactical Plan (in ralph loop, per-iteration)
┌─────────────────────────────────────────────┐
│ Read strategic plan for TASK-123            │
│ Check current state: What exists now?       │
│ Micro-plan:                                 │
│   1. jsonwebtoken already in package.json ✓ │
│   2. Create login.test.ts (RED)             │
│   3. Create login.ts (GREEN)                │
│   4. Run tests, iterate                     │
│ Self-check: Plan addresses all criteria? ✓  │
│ Execute...                                  │
└─────────────────────────────────────────────┘
```

**Why This Works:**
- Strategic plan is human-reviewed (quality gate)
- Tactical plan adapts to current state (flexibility)
- Each ticket gets explicit planning before coding
- Creates audit trail of intended approach

**Updated Ralph Loop:**

```
For each ticket:
  1. Read strategic plan from docs/plans/     ← NEW
  2. Generate tactical micro-plan             ← NEW
  3. Self-evaluate the plan                   ← NEW
  4. Execute implementation (TDD)
  5. Verify (tests, lint)
  6. Commit
  → Next ticket
```

**When Ralph Is Still OK (with this improvement):**
- PRDs with well-defined strategic plans
- Repetitive work you've done before
- You're available to monitor and intervene
- Sandboxed environment where mistakes are cheap

#### 4.2. Plan Mode Before Everything

**What:** Always start significant tasks in Plan Mode (Shift+Tab twice).

**Why:**
- "A good plan is really important!" - Boris
- Plans catch errors before code is written
- Forces explicit articulation of approach
- Creates alignment before execution

**Impact:**
- Slower start, faster finish
- More back-and-forth initially, less rework later
- Clear record of intended approach

**New Pattern:**
```
1. Enter Plan Mode (Shift+Tab twice)
2. Describe what you want
3. Review Claude's plan
4. Ask clarifying questions
5. Iterate until satisfied
6. Switch to auto-accept mode
7. Execute
```

#### 4.3. Multiple Focused Sessions

**What:** Run 3-5 parallel Claude Code sessions, each with a single focused task.

**Why:**
- Fresh context = better quality
- Parallel work = higher throughput
- Failure containment = easier recovery
- Separate checkouts = no conflicts

**Impact:**
- Need to manage multiple terminals/tabs
- Need to track which session is doing what
- Context switching overhead (but this is manageable)

**Start Small:** Begin with 2 sessions, add more as you get comfortable.

#### 4.4. Verification After Every Significant Step

**What:** Add explicit verification steps, not just end-of-task validation.

**Why:**
- "You don't trust; you instrument." - Boris
- Early error detection = cheaper fixes
- Builds confidence in outputs
- Creates verification habit

**Impact:**
- More commands to run
- Slightly slower individual tasks
- Significantly fewer errors to fix later

#### 4.5. CLAUDE.md as Living Document

**What:** Update CLAUDE.md multiple times per week, not just occasionally.

**Why:**
- "Anytime we see Claude do something incorrectly we add it to the CLAUDE.md" - Boris
- Mistakes become institutional memory
- Reduces repeated errors
- Compounds over time

**Impact:**
- Need to notice when Claude makes mistakes
- Need to formulate corrective guidance
- CLAUDE.md grows (but should stay ~2.5k tokens)

---

## 5. Adapted Workflow for Novices

This section provides a more structured version of Boris's fluid approach.

### Daily Workflow Structure

```
Morning:
1. Prime context (/prime)
2. Review what's in progress (git status, /whats-next)
3. Plan the day's work (what tickets, what order)

Per-Task (repeat for each ticket):
4. Open dedicated session for task
5. Enter Plan Mode, describe goal
6. Review plan, iterate if needed
7. Switch to execution mode
8. Verify incrementally (after each significant change)
9. Run tests, lint
10. Commit with structured message
11. Close session or repurpose for next task

End of Day:
12. Review all PRs created
13. Update CLAUDE.md if issues found
14. Note any open questions for tomorrow
```

### Task Assignment Pattern

**Before assigning a task to a session:**

1. **Define the scope** - What exactly should this session accomplish?
2. **Identify inputs** - What files/docs does it need to read?
3. **Specify outputs** - What deliverable do you expect?
4. **Set verification** - How will you know it's done correctly?

**Example Task Assignment:**

```
## Task: Implement user login endpoint

## Scope
Create POST /api/auth/login endpoint that validates credentials and returns JWT.

## Inputs
- Read: docs/prds/2026-01-10-auth.md (acceptance criteria)
- Read: docs/plans/2026-01-10-auth.md (technical approach)
- Read: src/api/auth/ (existing auth patterns)

## Outputs
- src/api/auth/login.ts (endpoint implementation)
- src/api/auth/login.test.ts (tests)
- Updated routes in src/api/index.ts

## Verification
- Test passes: npm test -- --grep "login"
- Lint passes: npm run lint
- Manual test with curl works
```

### Decision Points

**When to use single session:**
- Simple bug fix with known cause
- Documentation updates
- Small refactoring (< 1 file)
- Quick research questions

**When to use multiple parallel sessions:**
- Multi-ticket feature implementation
- You have independent pieces of work
- You're blocked waiting for tests to run
- You want to compare different approaches

**When to use Plan Mode:**
- Any task that changes more than one file
- Any task that takes > 30 minutes
- Any task where the approach isn't obvious
- First time implementing a pattern

**When to escalate to manual coding:**
- Claude is stuck after 3 attempts
- The task requires context Claude doesn't have
- Security-critical code paths
- You need to understand the code deeply

### Parallel Session Management (Simplified)

**For novices, start with this setup:**

```
Tab 1: Main session (planning, orchestration)
Tab 2: Implementation session
Tab 3: Testing/verification session
```

**Track sessions mentally or with notes:**

| Tab | Task | Status | Next Step |
|-----|------|--------|-----------|
| 1 | Planning next ticket | Waiting | Review plan |
| 2 | Implementing login | Running | Check when notification |
| 3 | Running test suite | Complete | Review results |

**Key habit:** Only switch attention when a session needs input. Let sessions run while you focus elsewhere.

---

## 6. New Practices to Adopt

### 6.1. Plan Mode First (Always)

**The Pattern:**

```bash
# Start Claude Code
claude

# Enter Plan Mode
[Shift+Tab twice]

# Describe goal
"I need to implement ticket TASK-123: user login endpoint.
Read the PRD and plan, then propose an implementation approach."

# Review plan
# Ask questions
# Iterate

# When satisfied, switch to execution
[Shift+Tab once - to auto-accept mode]

# Claude executes the plan
```

**Why It Works:**
- Forces explicit thinking about approach
- Creates alignment before expensive work
- Catches misunderstandings early
- Documents the intended approach

### 6.2. Verification Loops

**Incremental Verification Pattern:**

After each significant change:
```bash
# 1. Quick check - does it compile/parse?
npm run typecheck  # or equivalent

# 2. Unit tests for changed code
npm test -- --grep "component-name"

# 3. Lint check
npm run lint -- --fix

# 4. Full test suite before commit
npm test
```

**Verification in Claude:**

Ask Claude to verify its own work:
```
"Run the tests for what you just implemented.
If any fail, analyze why and fix them.
Don't proceed until tests pass."
```

**Boris's Insight:** "Give Claude a way to verify its work. If Claude has that feedback loop, it will 2-3x the quality."

### 6.3. CLAUDE.md as Living Document

**When to Update:**

- Claude makes a mistake you have to correct
- You notice a pattern of errors
- A new convention is established
- Something that worked before stops working

**Update Format:**

```markdown
## [Section Name]

### Do This
- Specific instruction
- Why it matters

### Don't Do This
- Anti-pattern to avoid
- What goes wrong if you do it
```

**Keep It Focused:**
- Target ~2.5k tokens
- Short, actionable items
- Remove outdated guidance
- No lengthy explanations

**Example Update:**

```markdown
## API Patterns

### Always
- Use validateRequest() middleware on all POST/PUT endpoints
- Return { success: boolean, data?: T, error?: string }

### Never
- Don't use res.json() directly - use sendSuccess() or sendError()
- Don't catch errors without logging them
```

### 6.4. Parallel Session Management

**Boris's Setup:** 5 terminal + 5-10 browser sessions, each with separate git checkout.

**Novice Adaptation:** Start simpler:

**Level 1 (Week 1-2):**
- 2 terminal sessions
- One for main work, one for verification/tests
- Same checkout, different tasks

**Level 2 (Week 3-4):**
- 3 terminal sessions
- Separate git worktrees per session
- Begin parallel implementation

**Level 3 (Month 2+):**
- 4-5 parallel sessions
- Full Boris-style parallelization
- Mobile sessions for long-running tasks

**Practical Setup:**

```bash
# Create git worktrees for parallel sessions
git worktree add ../project-session-2 -b feature/task-456
git worktree add ../project-session-3 -b feature/task-789

# Terminal 1: Main checkout
cd /path/to/project

# Terminal 2: Second worktree
cd /path/to/project-session-2

# Terminal 3: Third worktree
cd /path/to/project-session-3
```

### 6.5. Model Selection

**Boris's Choice:** Opus 4.5 with thinking for everything.

**His Reasoning:** "Even though it's bigger & slower than Sonnet, since you have to steer it less and it's better at tool use, it is almost always faster than using a smaller model."

**For Novices:**
- Use Opus 4.5 for planning, architecture, complex implementation
- Sonnet is OK for simple tasks where you'll verify anyway
- Never use a cheaper model to save money if it increases errors

---

## 7. Migration Path

### Phase 1: Foundation (Week 1-2)

**Goal:** Build new habits without disrupting current workflow.

**Actions:**
1. **Start using Plan Mode** for new tasks
   - Every task begins with planning
   - Practice the plan/review/iterate cycle

2. **Update CLAUDE.md** when you see mistakes
   - Keep a notepad of issues
   - Batch updates at end of day

3. **Add verification steps** to existing workflow
   - After each implementation, ask Claude to verify
   - Run tests more frequently

**Success Criteria:**
- [ ] Used Plan Mode for 10+ tasks
- [ ] Updated CLAUDE.md at least 3 times
- [ ] No commits without running tests

### Phase 2: Parallel Sessions (Week 3-4)

**Goal:** Begin managing multiple sessions.

**Actions:**
1. **Set up git worktrees** for 2-3 parallel sessions
2. **Practice session switching** - start task in one, verify in another
3. **Experiment with parallel implementation** on independent tickets
4. **Update ralph-prd** with two-level planning (strategic + tactical)

**Success Criteria:**
- [ ] Completed a feature using 2+ parallel sessions
- [ ] Successfully merged work from multiple worktrees
- [ ] Ran ralph-prd with two-level planning successfully

### Phase 3: Full Adoption (Month 2)

**Goal:** Operate like Boris (adapted for your skill level).

**Actions:**
1. **Increase to 4-5 parallel sessions** as comfortable
2. **Establish session assignment patterns** - what tasks go where
3. **Optimize CLAUDE.md** - remove stale guidance, add new patterns
4. **Measure and improve** - track completion rates, error rates

**Success Criteria:**
- [ ] Routine use of 3+ parallel sessions
- [ ] CLAUDE.md updated weekly
- [ ] Clear improvement in output quality vs. autonomous mode
- [ ] Comfortable managing parallel work

### What to Try First

**Easiest wins:**
1. Plan Mode for your next task (try it today)
2. Update CLAUDE.md after your next Claude mistake
3. Run tests after implementation, before commit

**Quick experiment:**
- Take a simple ticket
- Complete it with Plan Mode + verification loops
- Compare experience to autonomous mode

---

## 8. Guardrails for Novices

### Common Mistakes to Avoid

| Mistake | Why It's Bad | What to Do Instead |
|---------|--------------|-------------------|
| Skipping Plan Mode | "I know what I want" often isn't specific enough | Always plan, even for "simple" tasks |
| Too many parallel sessions | Cognitive overload, context switching costs | Start with 2, add gradually |
| Ignoring test failures | Creates technical debt, masks real problems | Fix immediately or document why deferred |
| Not updating CLAUDE.md | Same mistakes repeat forever | Spend 5 min updating after each session |
| Letting sessions run too long | Context degradation, diminishing returns | Check in every 30-60 min |
| Copying entire output blindly | May contain errors or artifacts | Always review, especially code |

### When to Ask for Help

**Ask a senior engineer when:**
- Claude's suggestions don't make sense and you can't tell if you or Claude is wrong
- You've tried 3 different approaches and none work
- The task involves security, payments, or other sensitive areas
- You're about to make a change you can't easily undo

**Ask Claude for clarification when:**
- The plan is unclear
- You're unsure about a specific implementation choice
- You want to understand why it chose an approach
- Something in the output doesn't match the plan

### Red Flags That Indicate Problems

**Stop and reassess if:**

1. **Claude keeps changing the same file repeatedly** - unclear requirements or approach
2. **Tests keep failing for the same reason** - fundamental misunderstanding
3. **Claude suggests ignoring errors** - never do this
4. **Implementation is much larger than planned** - scope creep
5. **You've been on the same task for 2+ hours with no progress** - stuck
6. **Claude's responses are getting shorter/vaguer** - context exhaustion

**Recovery Actions:**

1. **Start a fresh session** with clearer context
2. **Break the task into smaller pieces**
3. **Ask Claude to explain its approach** before continuing
4. **Review CLAUDE.md** - is there guidance that helps?
5. **Take a break** - fresh eyes help

### Safety Checklist

Before merging any PR:

- [ ] All tests pass (not skipped, actually pass)
- [ ] Lint passes (no warnings or errors)
- [ ] Changes match the plan from Plan Mode
- [ ] No hardcoded secrets, keys, or credentials
- [ ] No TODO comments that should be addressed now
- [ ] No debug code (console.log, debugger statements)
- [ ] Changes are scoped to the ticket (no scope creep)
- [ ] I understand what the code does

---

## Appendix A: Quick Reference Card

### Session Startup Sequence

```
1. claude                      # Start session
2. Shift+Tab twice            # Enter Plan Mode
3. "Read [docs], then plan [task]"
4. Review plan, iterate
5. Shift+Tab once             # Auto-accept mode
6. Monitor execution
7. Verify: tests, lint, review
8. Commit
```

### Verification Commands

```bash
npm run typecheck     # Type checking
npm test             # All tests
npm run lint         # Linting
git diff             # Review changes
```

### CLAUDE.md Update Template

```markdown
## [Area]

### Always
- Do X because Y

### Never
- Don't do Z because W
```

### Task Assignment Template

```markdown
## Task: [Name]
## Scope: [What exactly to do]
## Inputs: [What to read]
## Outputs: [Expected deliverables]
## Verification: [How to confirm success]
```

---

## Appendix B: Terminology Mapping

| Current Term | Boris Equivalent | Meaning |
|--------------|------------------|---------|
| ralph-prd | Parallel sessions | Autonomous vs human-managed implementation |
| Strategic plan | (in /plan phase) | Human-reviewed technical approach per ticket |
| Tactical plan | Plan Mode | Per-task planning before execution |
| Orchestrator | You (human) or ralph | Whoever decides what Claude does next |
| Phase gate | Plan Mode iteration | Checkpoint before proceeding |
| Agent delegation | Session assignment | Giving a task to a Claude session |
| Artifact | CLAUDE.md / output files | Persistent work product |

---

## Appendix C: Resources

### Boris Cherny Sources
- [Twitter Thread](https://twitter-thread.com/t/2007179832300581177)
- [Latent Space Podcast](https://www.latent.space/p/claude-code)
- [AI & I Podcast](https://every.to/podcast/how-to-use-claude-code-like-the-people-who-built-it)

### Your Current Documentation
- `WORKFLOW.md` - Phase documentation
- `CLAUDE.md` - Project instructions
- `.claude/agents/` - Agent definitions
- `docs/templates/` - Document templates

### Further Learning
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Boris's Command Config](https://github.com/0xquinto/bcherny-claude)
