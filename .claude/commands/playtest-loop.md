---
allowed-tools: Bash(*), mcp__playwright__*, Read, Write, Edit, Glob, Grep, Task, TaskCreate, TaskUpdate, TaskList
description: Automated playtest-fix-retest loop — finds bugs, fixes them, and retests until clean
---

You are an autonomous QA + engineering loop. Your job is to repeatedly playtest the AI-MUD app, fix any bugs found, and retest until there are no critical or major bugs remaining.

**CRITICAL RULE: The playtest must actually PLAY THE GAME.** This is not just a UI verification — the tester must navigate through pages using exits, explore areas, interact with NPCs/items, talk to the companion in different locations, and try to progress through the adventure. If the game cannot be played as a text adventure (can't move, can't navigate, nothing to do, stuck), that is a CRITICAL bug. The game should feel like a playable MUD.

## LOOP STRUCTURE

```
┌─────────────────────────────────────────────┐
│  1. START SERVERS                           │
│  2. PLAYTEST (subagent) → bug report        │
│  3. Any critical/major bugs? ──No──→ DONE   │
│       │ Yes                                 │
│  4. FIX BUGS (subagent) → committed code    │
│  5. RUN TESTS → all pass?                   │
│       │ No → fix test failures first        │
│       │ Yes                                 │
│  6. KILL SERVERS, go to step 1              │
└─────────────────────────────────────────────┘
```

## STEP 1: Start Servers

```bash
# Kill anything on the ports first
lsof -ti:3000 2>/dev/null | xargs -r kill
for port in $(seq 5173 5180); do lsof -ti:$port 2>/dev/null | xargs -r kill; done
sleep 2

# Start backend
cd /home/jim/workspace/ai-mud && npm run dev --workspace=backend > /tmp/backend.log 2>&1 &

# Start frontend
cd /home/jim/workspace/ai-mud && npm run dev --workspace=frontend > /tmp/frontend.log 2>&1 &

# Wait for ready
sleep 8
```

Verify both are running before proceeding. Check `/tmp/backend.log` and `/tmp/frontend.log` for the URLs.

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
2. The full playtest instructions (from `.claude/commands/playtest.md`):
   - Navigate to frontend URL
   - Register a new user (unique username with timestamp)
   - Complete all 4 onboarding steps (read `.env` for ANTHROPIC_API_KEY)
   - Verify onboarding fixes (intro text in chat, input disabled after companion confirmed)
   - Test all game page panels (left sidebar, chat, right panel tabs, header, footer, map)
   - **PLAY THE GAME**: Click exits to navigate between areas, explore 3-4+ different locations, talk to companion in different areas, check for NPCs/items, try to progress through the adventure. If stuck (no exits, can't move, nothing to do) — CRITICAL BUG.
   - Verify footer shows provider AND model name
   - Verify settings has "Change LLM Settings" option
   - Verify map shows actual visitable pages
   - Test returning user flow (logout → login → verify persistence + same area)
   - Test page refresh (F5 on game page → verify session survives)
   - Use `mcp__playwright__browser_snapshot` for page state, `mcp__playwright__browser_take_screenshot` for visual evidence
   - Include a "GAMEPLAY TEST" section in the report documenting areas visited, exits used, what worked/didn't

3. **Bug list update rules:**
   - READ the existing bug list first — do NOT start from scratch
   - Verify ALL previously-fixed bugs still work (regression check)
   - Verify ALL still-open bugs — mark as fixed if they're now resolved
   - Assign NEW bugs sequential IDs continuing from the highest existing number
   - Categorize each bug by severity: Critical, Major, Moderate, Low
   - Write the UPDATED cumulative report back to `docs/todo/playtest-bugs.md`
   - The file is a LIVING DOCUMENT — preserve history, don't overwrite it

## STEP 3: Evaluate Bug Report

Read `docs/todo/playtest-bugs.md` after the playtest subagent finishes.

**EXIT CONDITION:** If there are NO critical or major bugs remaining, the loop is done. Write a final summary and stop.

**CONTINUE CONDITION:** If there are critical or major bugs, proceed to Step 4.

## STEP 4: Fix Bugs (Delegate to Subagent)

Launch an `engineer` subagent to fix ALL critical and major bugs. Include in the prompt:

- The full content of `docs/todo/playtest-bugs.md`
- Instructions to fix critical bugs first, then major bugs
- Stay on the current branch
- Run `npm test --workspace=frontend` and `npm test --workspace=backend` after all fixes
- Commit changes with a descriptive message
- Do NOT modify test expectations unless the test was testing broken behavior

**IMPORTANT:** Only send ONE engineer subagent — multiple agents in the same workspace conflict.

## STEP 5: Verify Tests Pass

After the engineer subagent returns, verify all tests pass:

```bash
cd /home/jim/workspace/ai-mud && npm test --workspace=frontend 2>&1 | tail -5
cd /home/jim/workspace/ai-mud && npm test --workspace=backend 2>&1 | tail -5
```

If tests fail, send the failures back to an engineer subagent to fix.

## STEP 6: Loop

Kill the servers and go back to Step 1 for a fresh playtest.

```bash
lsof -ti:3000 2>/dev/null | xargs -r kill
for port in $(seq 5173 5180); do lsof -ti:$port 2>/dev/null | xargs -r kill; done
```

## LOOP LIMITS

- **Maximum iterations:** 5 (to prevent infinite loops)
- **Iteration counter:** Track and report which iteration you're on
- After each iteration, briefly summarize: what was found, what was fixed, what remains
- If stuck on the same bug for 2 iterations, flag it for human review and move on

## FINAL REPORT

When the loop exits (either clean or max iterations), write a summary to `docs/todo/playtest-summary.md`:

- Total iterations run
- Bugs found and fixed per iteration
- Remaining bugs (if any) with severity
- Overall app status assessment

## IMPORTANT NOTES

- Be patient with LLM responses during playtest — they take 10-30 seconds
- Password for test accounts: "TestPass123!"
- Read `.env` for the ANTHROPIC_API_KEY — do NOT hardcode it
- Use `mcp__playwright__browser_snapshot` (accessibility tree) over screenshots for verifying content
- Always kill servers between iterations for a clean state
- Each playtest should use a DIFFERENT username to avoid state contamination
