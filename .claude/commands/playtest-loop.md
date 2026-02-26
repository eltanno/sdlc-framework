---
allowed-tools: Bash(*), mcp__playwright__*, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList
description: Automated playtest-fix-retest loop — finds bugs, fixes them, and retests until clean
---

You are an autonomous QA + engineering loop. Your job is to repeatedly playtest the application, fix any bugs found, and retest until there are no critical or major bugs remaining.

## STEP 0: Understand the Project

Read `docs/SYSTEM.md` to understand:
- What this application does and how it works
- The architecture (frontend, backend, services)
- Key user flows to test
- Known issues and fragile areas

Read `CLAUDE.md` for:
- How to start/stop the dev environment
- Project structure and conventions

This context will inform what to test and how to test it.

## LOOP STRUCTURE

```
┌──────────────────────────────────────────────────┐
│  1. START SERVERS (if not already running)        │
│  2. PLAYTEST (subagent) → bug report             │
│  3. Any critical/major bugs (BUG-XXX)?           │
│       │ Yes → 4. FIX BUGS (engineer)             │
│       │        5. RUN TESTS → all pass?           │
│       │             No → fix test failures        │
│       │ No ───────────────────────────→ DONE     │
│  6. KILL SERVERS, go to step 1                   │
└──────────────────────────────────────────────────┘
```

## STEP 1: Start Servers

Read `CLAUDE.md` for the correct dev startup procedure. Typical pattern:

1. Check if services are already running (docker-compose, background tasks)
2. Start any required service containers (databases, caches, etc.)
3. Start backend dev server (in background)
4. Start frontend dev server (in background)
5. Wait for both to be ready and verify by checking their output logs

**Determine the correct URLs** from the server output (e.g., frontend port, backend port).

If servers are already running from a previous iteration, verify they're still healthy before reusing them.

## STEP 1.5: Reset Bug List After a New Release

**Before each playtest loop**, check if a new PRD has been delivered since the last playtest run. Compare the PRD date/name in `docs/todo/playtest-bugs.md` header against the most recent PRD in `docs/prds/`.

**If a new PRD has been delivered (i.e., new feature work was completed):**
1. Archive the old bug list: `mv docs/todo/playtest-bugs.md docs/todo/playtest-bugs-$(date +%Y-%m-%d)-archive.md`
2. Start fresh — the subagent creates a new `docs/todo/playtest-bugs.md` from scratch with BUG-001
3. This is a clean slate — no regression checking of old bugs from the previous release cycle

**If NO new PRD has been delivered (i.e., continuing the same release cycle):**
- Keep the existing bug list and continue the cumulative approach as before

**Why:** Each release cycle is a fresh product state. Carrying forward bugs from a previous release pollutes the report and wastes time re-verifying things that may have been intentionally changed. A new PRD = a new playtest baseline.

## STEP 2: Playtest (Delegate to Subagent)

**Before launching the subagent**, read `docs/todo/playtest-bugs.md` yourself (if it exists) and include its full content in the subagent prompt. If the file was just reset (Step 1.5), tell the subagent this is a fresh playtest with no prior bug history.

If the file exists and has prior content, the subagent needs it to:
- Know which bugs were previously fixed (regression check)
- Know which bugs are still open (verify if still broken or now fixed)
- Assign correct sequential bug IDs to any NEW bugs (e.g., if last bug was BUG-015, next new one is BUG-016)

Launch a `general-purpose` subagent with access to Playwright tools. Give it:

1. **The full content of `docs/todo/playtest-bugs.md`** (the existing cumulative bug list)
2. **The content of `docs/SYSTEM.md`** (so it understands the app's architecture and user flows)
3. The full playtest instructions (from `.claude/commands/playtest.md`)

4. **Time allocation guidance:**
   - **~30% on regression/verification** — Quick pass/fail checks on existing bugs. Fixed bugs: confirm they still work. Open bugs: confirm they're still broken or now fixed. Don't spend excessive time on known issues — the fix either works or it doesn't.
   - **~70% on fresh exploratory testing** — The primary goal is to discover NEW bugs. Run all playtest phases thoroughly, testing different scenarios, pages, and flows than previous rounds. Try different edge cases. Don't just re-tread the same paths as last time.
   - **Vary your testing** — Navigate pages in different orders. Try features in combinations not previously tested.

6. **Bug list update rules:**
   - READ the existing bug list first — do NOT start from scratch
   - Verify ALL previously-fixed bugs still work (regression check)
   - Verify ALL still-open bugs — mark as fixed if they're now resolved
   - Assign NEW bugs sequential IDs continuing from the highest existing number
   - Categorize each bug by severity: Critical, Major, Moderate, Low
   - Write the UPDATED cumulative report back to `docs/todo/playtest-bugs.md`
   - The file is a LIVING DOCUMENT — preserve history, don't overwrite it

## STEP 3: Evaluate Bug Report

Read `docs/todo/playtest-bugs.md` after the playtest subagent finishes.

**EXIT CONDITION:** If there are NO critical or major bugs (BUG-XXX), the loop is done. Write a final summary and stop.

**CONTINUE with Step 4:** If there are critical or major bugs, fix them.

## STEP 4: Fix Bugs (Delegate to Subagent)

Launch an `engineer` subagent to fix ALL critical and major bugs (BUG-XXX).

Include in the prompt:

- The bugs from `docs/todo/playtest-bugs.md`
- The content of `docs/SYSTEM.md` for architectural context
- Instructions to fix critical bugs first, then major bugs
- Stay on the current branch
- Run the project's test commands after all fixes (read from `config.yaml` or `CLAUDE.md`)
- Commit changes with a descriptive message
- Do NOT modify test expectations unless the test was testing broken behavior

**IMPORTANT:** Only send ONE engineer subagent — multiple agents in the same workspace conflict.

## STEP 5: Verify Tests Pass

After the engineer subagent returns, verify all tests pass by running the project's test commands. Read `config.yaml` for the correct commands, or use:
- Backend tests (e.g., `cd backend && pytest`)
- Frontend tests (e.g., `cd frontend && npm test`)

If tests fail, send the failures back to an engineer subagent to fix.

## STEP 6: Loop

Kill the servers and go back to Step 1 for a fresh playtest.

Kill any background dev servers and service containers as appropriate for the project.

## LOOP LIMITS

- **Maximum iterations:** 5 (to prevent infinite loops)
- **Iteration counter:** Track and report which iteration you're on
- After each iteration, briefly summarize: what was found, what was fixed, what remains
- If stuck on the same bug for 2 iterations, flag it for human review and move on

## FINAL REPORT

When the loop exits (either clean or max iterations), write a summary to `docs/todo/playtest-summary.md`:

- Total iterations run
- Bugs found and fixed per iteration
- Remaining issues (if any) with severity
- Overall app status assessment

## IMPORTANT NOTES

- Read `docs/SYSTEM.md` and `CLAUDE.md` first — they tell you everything about the project
- Use `mcp__playwright__browser_snapshot` (accessibility tree) over screenshots for verifying content
- Use `mcp__playwright__browser_take_screenshot` for visual evidence of bugs
- Always kill servers between iterations for a clean state
- Each playtest should use a DIFFERENT username to avoid state contamination
