# Ralph-PRD Loop Analysis

**Purpose:** Detailed breakdown of `/ralph-prd` workflow with analysis of which steps need LLM vs can be scripted.

---

## Current Architecture

```
/ralph-prd docs/prds/YYYY-MM-DD-feature.md
    │
    ▼
┌─────────────────────────────────────────────┐
│  SETUP PHASE (One-time)                     │
│  1. Read PRD and Plan                       │
│  2. Get ticket list from plan/PM tool       │
│  3. Create local progress tracking file     │
│  4. Initialize workflow-state.json          │
│  5. Update status line                      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  LOOP (Per Ticket)                          │
│                                             │
│  1. Move ticket to In Progress              │
│  2. Update status line                      │
│  3. [LLM] Make plan (/planning mode)        │
│  4. [LLM] Validate plan                     │
│  5. [LLM] Execute plan (write code)         │
│  6. [LLM] Validate work (tests pass?)       │
│  7. Commit & push                           │
│  8. Create PR                               │
│  9. [LLM] Validate PR (acceptance criteria) │
│  10. Merge PR                               │
│  11. Move ticket to Done                    │
│  12. Update status line                     │
│                                             │
│  If blocked → mark ticket, skip to next     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  CLEANUP PHASE (One-time)                   │
│  1. Update workflow-state.json              │
│  2. Final status line update                │
│  3. Output PRD_COMPLETE                     │
└─────────────────────────────────────────────┘
```

---

## Detailed Step-by-Step Breakdown

### SETUP PHASE

| Step | Action | API/Tool | LLM? | Scriptable? |
|------|--------|----------|------|-------------|
| S1 | Read PRD document | `Read` file | No | Yes - file read |
| S2 | Read Plan document | `Read` file | No | Yes - file read |
| S3 | Get ticket list | Parse plan or PM API | No | Yes - regex/jq/API |
| S4 | Create progress tracking | `Write` file | No | Yes - template |
| S5 | Init workflow-state.json | `jq` via bash | No | Yes - script |
| S6 | Update status line | `.claude/scripts/statusline.sh` | No | Yes - existing script |

**Current API calls in setup:**
```bash
# Read files
Read(docs/prds/YYYY-MM-DD-feature.md)
Read(docs/plans/YYYY-MM-DD-feature.md)

# PM tool (if configured) - e.g., Trello
mcp__trello__get_cards_by_list_id({ listId: "ready-list-id" })

# Initialize state
.claude/scripts/update-workflow-state.sh '.phase = "ralph" | .ralph.current = 0 | .ralph.total = N'

# Status line
.claude/scripts/statusline.sh "Ralph: 0/N"
```

---

### PER-TICKET LOOP

| Step | Action | API/Tool | LLM? | Scriptable? |
|------|--------|----------|------|-------------|
| L1 | Move ticket to In Progress | PM API (Trello/Asana/etc) | No | **Yes - direct API** |
| L2 | Update status line | Bash script | No | **Yes - script** |
| L3 | Create implementation plan | LLM planning | **YES** | No |
| L4 | Validate plan | LLM review | **YES** | No |
| L5 | Execute plan (write code) | LLM + Edit/Write tools | **YES** | No |
| L6 | Run tests | `npm test` | No | **Yes - bash** |
| L7 | Run lint | `npm run lint` | No | **Yes - bash** |
| L8 | Check build | `npm run build` | No | **Yes - bash** |
| L9 | Analyze test results | LLM if failures | **Maybe** | Partial - pass/fail is scriptable |
| L10 | Git add & commit | `git` commands | No | **Yes - bash** |
| L11 | Git push | `git push` | No | **Yes - bash** |
| L12 | Create PR | `gh pr create` | No | **Yes - bash/API** |
| L13 | Validate acceptance criteria | LLM review | **YES** | No |
| L14 | Merge PR | `gh pr merge` | No | **Yes - bash** |
| L15 | Move ticket to Done | PM API | No | **Yes - direct API** |
| L16 | Update progress file | `Edit`/`jq` | No | **Yes - script** |
| L17 | Update status line | Bash script | No | **Yes - script** |

**Current API calls per ticket:**
```bash
# L1: Move ticket (Trello example)
mcp__trello__move_card({ cardId: "xxx", listId: "in-progress-list-id" })

# L2: Status line
.claude/scripts/statusline.sh "Ralph: 1/N - Implementing TASK-001"

# L3-L5: LLM implementation (delegated to engineer agent)
Task({
  subagent_type: "engineer",
  prompt: "Implement TASK-001...",
  model: "sonnet"
})

# L6-L8: Validation commands
npm test
npm run lint
npm run build

# L10-L11: Git
git add -A
git commit -m "[TASK-001] Description"
git push -u origin feature/TASK-001-description

# L12: PR creation
gh pr create --title "[TASK-001] Title" --body "..."

# L14: Merge
gh pr merge --squash --delete-branch

# L15: Move ticket
mcp__trello__move_card({ cardId: "xxx", listId: "done-list-id" })

# L16: Update progress
jq '.ralph.current = (.ralph.current + 1)' workflow-state.json > tmp && mv tmp workflow-state.json

# L17: Status line
.claude/scripts/statusline.sh "Ralph: 2/N"
```

---

### CLEANUP PHASE

| Step | Action | API/Tool | LLM? | Scriptable? |
|------|--------|----------|------|-------------|
| C1 | Finalize workflow-state.json | `jq` | No | Yes - script |
| C2 | Final status line | Bash script | No | Yes - script |
| C3 | Output completion | stdout | No | Yes |

---

## LLM vs Script Summary

### Requires LLM (Cannot Script)

| Step | Why LLM Required |
|------|------------------|
| L3: Create plan | Needs to understand requirements and design approach |
| L4: Validate plan | Needs judgment on completeness and correctness |
| L5: Execute plan | Actually writing code requires understanding |
| L9: Analyze failures | Understanding why tests fail (if they do) |
| L13: Validate acceptance | Mapping implementation to criteria needs judgment |

### Fully Scriptable (No LLM)

| Step | Implementation |
|------|----------------|
| S1-S2: Read docs | Simple file reads |
| S3: Get tickets | Parse MD table or PM API call |
| S4-S6: Init state | Template + jq + bash |
| L1: Move to In Progress | Direct PM API call |
| L2, L12, L17: Status updates | Bash scripts |
| L6-L8: Run tests/lint/build | npm commands |
| L10-L11: Git commit/push | git commands |
| L12: Create PR | gh CLI |
| L14: Merge PR | gh CLI |
| L15: Move to Done | Direct PM API call |
| L16: Update progress | jq/edit |
| C1-C3: Cleanup | Scripts |

---

## Optimization Recommendations

### 1. Progress Tracking: JSON vs Markdown

**Current:** Uses both `workflow-state.json` (machine) and `PROGRESS.md` (human)

**Recommendation:** Keep both, but with clear purposes:

```
workflow-state.json    → Machine state (ralph cursor, current ticket)
                         Fast to parse with jq
                         Used by scripts and status line

PROGRESS.md            → Human-readable log
                         Shows history and notes
                         Useful for debugging/review
```

**Suggested workflow-state.json enhancement:**

```json
{
  "phase": "ralph",
  "ralph": {
    "current": 2,
    "total": 10,
    "current_ticket": "LOCAL-003",
    "tickets": [
      { "id": "LOCAL-001", "status": "done", "pr": "#12" },
      { "id": "LOCAL-002", "status": "done", "pr": "#13" },
      { "id": "LOCAL-003", "status": "in_progress", "pr": null },
      { "id": "LOCAL-004", "status": "pending", "pr": null }
    ],
    "blocked": []
  }
}
```

This gives you:
- O(1) lookup for current state
- Easy jq queries for any ticket status
- No markdown parsing needed

### 2. Pre-Loop Script

Create `.claude/scripts/ralph-setup.sh`:

```bash
#!/bin/bash
# Ralph setup - runs BEFORE any LLM work

PRD_PATH=$1
PLAN_PATH=$2

# Extract ticket count from plan
TICKET_COUNT=$(grep -c "^| LOCAL-" "$PLAN_PATH" || echo "0")

# Initialize workflow state
jq --argjson count "$TICKET_COUNT" '
  .phase = "ralph" |
  .ralph.current = 0 |
  .ralph.total = $count |
  .ralph.current_ticket = null |
  .ralph.tickets_done = []
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Update status line
.claude/scripts/statusline.sh "Ralph: Starting ($TICKET_COUNT tickets)"

echo "Setup complete. $TICKET_COUNT tickets to process."
```

### 3. Per-Ticket Wrapper Script

Create `.claude/scripts/ralph-ticket-start.sh`:

```bash
#!/bin/bash
# Run BEFORE LLM starts working on a ticket

TICKET_ID=$1
LIST_ID_IN_PROGRESS=$2  # From config

# Move ticket to In Progress (Trello example)
# This would be a curl call or MCP wrapper
# curl -X PUT "https://api.trello.com/..."

# Update workflow state
jq --arg ticket "$TICKET_ID" '
  .ralph.current_ticket = $ticket
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Update status line
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
.claude/scripts/statusline.sh "Ralph: $CURRENT/$TOTAL - $TICKET_ID"
```

### 4. Post-Implementation Script

Create `.claude/scripts/ralph-ticket-done.sh`:

```bash
#!/bin/bash
# Run AFTER LLM finishes a ticket (tests pass, committed)

TICKET_ID=$1
PR_NUMBER=$2
LIST_ID_DONE=$3  # From config

# Move ticket to Done
# curl -X PUT "https://api.trello.com/..."

# Update workflow state
jq --arg ticket "$TICKET_ID" --arg pr "$PR_NUMBER" '
  .ralph.current = (.ralph.current + 1) |
  .ralph.current_ticket = null |
  .ralph.tickets_done += [$ticket]
' workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json

# Update status line
CURRENT=$(jq -r '.ralph.current' workflow-state.json)
TOTAL=$(jq -r '.ralph.total' workflow-state.json)
.claude/scripts/statusline.sh "Ralph: $CURRENT/$TOTAL"
```

---

## Optimized Loop Flow

```
┌─────────────────────────────────────────────────────────┐
│ SETUP (100% Script)                                     │
│                                                         │
│ ralph-setup.sh                                          │
│   ├── Parse PRD/Plan for tickets                        │
│   ├── Initialize workflow-state.json                    │
│   ├── Create progress file                              │
│   └── Set status line                                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ PER-TICKET LOOP                                         │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ PRE-WORK (Script)                                   │ │
│ │ ralph-ticket-start.sh TASK-001                      │ │
│ │   ├── Move ticket to In Progress (PM API)          │ │
│ │   ├── Update workflow-state.json                   │ │
│ │   └── Update status line                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                          │                              │
│                          ▼                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ LLM WORK (Requires Claude)                         │ │
│ │   ├── Plan implementation approach                 │ │
│ │   ├── Write tests (TDD)                            │ │
│ │   ├── Write implementation                         │ │
│ │   └── Fix any issues                               │ │
│ └─────────────────────────────────────────────────────┘ │
│                          │                              │
│                          ▼                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ VALIDATION (Script)                                │ │
│ │ ralph-validate.sh                                   │ │
│ │   ├── npm test                                     │ │
│ │   ├── npm run lint                                 │ │
│ │   ├── npm run build                                │ │
│ │   └── Return pass/fail                             │ │
│ └─────────────────────────────────────────────────────┘ │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │             │                       │
│                PASS           FAIL                      │
│                   │             │                       │
│                   ▼             ▼                       │
│ ┌─────────────────────┐  ┌─────────────────────┐       │
│ │ PR FLOW (Script)    │  │ FIX (LLM)           │       │
│ │ ralph-pr.sh         │  │ Analyze failure     │       │
│ │   ├── git commit    │  │ Fix code            │       │
│ │   ├── git push      │  │ Loop back to        │       │
│ │   ├── gh pr create  │  │ validation          │       │
│ │   └── gh pr merge   │  └─────────────────────┘       │
│ └─────────────────────┘                                 │
│                          │                              │
│                          ▼                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ POST-WORK (Script)                                 │ │
│ │ ralph-ticket-done.sh TASK-001 #PR                   │ │
│ │   ├── Move ticket to Done (PM API)                 │ │
│ │   ├── Update workflow-state.json                   │ │
│ │   └── Update status line                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                          │                              │
│                 More tickets?                           │
│                   │         │                           │
│                  YES        NO                          │
│                   │         │                           │
│                   ▼         ▼                           │
│              Loop back    Continue                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ CLEANUP (100% Script)                                   │
│                                                         │
│ ralph-cleanup.sh                                        │
│   ├── Finalize workflow-state.json                      │
│   ├── Update status line                                │
│   └── Output PRD_COMPLETE                               │
└─────────────────────────────────────────────────────────┘
```

---

## Time Savings Estimate

| Phase | Current | Optimized | Savings |
|-------|---------|-----------|---------|
| Setup | LLM reads files, inits state | Script does all | ~30-60s per run |
| Ticket start | LLM calls PM API, updates state | Script does all | ~10-20s per ticket |
| Validation | LLM runs npm commands | Script runs all, returns result | ~5-10s per ticket |
| PR flow | LLM runs git/gh commands | Script does all | ~15-30s per ticket |
| Ticket end | LLM calls PM API, updates state | Script does all | ~10-20s per ticket |

**Per ticket savings:** ~40-80 seconds
**10 ticket PRD savings:** ~7-13 minutes

**Plus:** Reduces LLM context usage, fewer API calls, more reliable.

---

## Missing from Current Implementation

Based on your proposed list, here's what's missing or could be improved:

| Your Step | Current State | Gap |
|-----------|---------------|-----|
| Get ticket list | Reads from Plan MD | Could also query PM API for live state |
| JSON progress file | Uses MD + JSON hybrid | Could consolidate to JSON-primary |
| Loop blocking | Mentions NEEDS_HUMAN_REVIEW | No automatic skip-to-next |
| Plan validation | Implicit | Should be explicit step |
| PR validation | Part of /validate | Could be more structured |

### Recommended Additions

1. **Automatic blocker handling:**
   ```bash
   if [ "$ATTEMPT_COUNT" -gt 3 ]; then
     ralph-mark-blocked.sh "$TICKET_ID" "Failed 3 attempts"
     continue  # Skip to next ticket
   fi
   ```

2. **Plan validation checkpoint:**
   - After engineer proposes plan, quick LLM review
   - Or: structured plan output that can be validated

3. **PR acceptance check:**
   - Script can verify: tests pass, lint clean, build works
   - LLM only needed for: acceptance criteria mapping

---

## Implementation

Scripts have been created in `.claude/scripts/ralph/`:

| Script | Purpose |
|--------|---------|
| `setup.sh` | Parse tickets, init workflow-state.json |
| `ticket-start.sh` | Mark ticket in-progress, update status |
| `validate.sh` | Run tests/lint/build |
| `pr-flow.sh` | Commit, push, create/merge PR |
| `ticket-done.sh` | Mark complete, find next ticket |
| `mark-blocked.sh` | Skip failing ticket |
| `get-next-ticket.sh` | Loop control |
| `cleanup.sh` | Finalize run |
| `status.sh` | Show current state |
| `orchestrator.sh` | **Master script - runs outside Claude** |

## Usage

### Preferred: Orchestrator (runs outside Claude)

```bash
# Run /ralph-cmd in Claude to get the exact command, then run in your terminal:
.claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

# Options
--dry-run         # Preview without invoking Claude
--max-attempts 3  # Max retries before marking blocked
```

The orchestrator:
1. Runs all mechanical work directly in your shell (zero LLM cost)
2. Only invokes `claude -p` for implementation and fixing failures
3. Handles the full loop automatically

### Alternative: Manual with ! prefix

If you want finer control, run scripts manually between Claude interactions:

```bash
# In your shell (not Claude)
!.claude/scripts/ralph/setup.sh docs/prds/... docs/plans/...
!.claude/scripts/ralph/ticket-start.sh LOCAL-001

# Then ask Claude to implement
# "Implement LOCAL-001 using TDD, commit when done"

# Back in shell
!.claude/scripts/ralph/validate.sh
!.claude/scripts/ralph/pr-flow.sh LOCAL-001 "[LOCAL-001] Implementation"
!.claude/scripts/ralph/ticket-done.sh LOCAL-001
```

## Why This Matters

Every Bash tool call from Claude costs LLM turns. The orchestrator eliminates ~80% of those calls by running mechanical work directly.

| Approach | LLM Turns (10 tickets) |
|----------|------------------------|
| Original /ralph-prd | ~100+ turns |
| Orchestrator | ~20 turns |
