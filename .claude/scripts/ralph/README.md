# Ralph Scripts

Scripts to optimize the `/ralph-prd` loop by handling non-LLM work.

## Purpose

These scripts handle the mechanical parts of the ralph loop that don't require LLM intelligence:
- State management (workflow-state.json)
- Status line updates
- Git operations
- PR creation/merging
- Validation (tests, lint, build)

The LLM only needs to focus on:
- Planning implementation approach
- Writing code
- Fixing failures
- Validating acceptance criteria

## Scripts

| Script | Purpose | When to Call |
|--------|---------|--------------|
| `setup.sh` | Initialize ralph run | Start of `/ralph-prd` |
| `ticket-start.sh` | Mark ticket as in-progress | Before LLM works on ticket |
| `validate.sh` | Run tests/lint/build | After LLM writes code |
| `pr-flow.sh` | Commit, push, create/merge PR | After validation passes |
| `ticket-done.sh` | Mark ticket complete | After PR merged |
| `mark-blocked.sh` | Skip a failing ticket | When ticket can't be completed |
| `get-next-ticket.sh` | Find next pending ticket | Loop control |
| `cleanup.sh` | Finalize ralph run | End of `/ralph-prd` |
| `status.sh` | Show current state | Anytime |

## Usage

```bash
# Setup (once at start)
.claude/scripts/ralph/setup.sh docs/prds/2026-01-10-feature.md docs/plans/2026-01-10-feature.md

# Per-ticket loop
.claude/scripts/ralph/ticket-start.sh LOCAL-001
# ... LLM implements ticket ...
.claude/scripts/ralph/validate.sh
# If pass:
.claude/scripts/ralph/pr-flow.sh LOCAL-001 "[LOCAL-001] Implement feature"
.claude/scripts/ralph/ticket-done.sh LOCAL-001 42  # 42 = PR number
# If fail after 3+ attempts:
.claude/scripts/ralph/mark-blocked.sh LOCAL-001 "Tests failing - needs investigation"

# Check next ticket
.claude/scripts/ralph/get-next-ticket.sh

# Cleanup (once at end)
.claude/scripts/ralph/cleanup.sh

# Status anytime
.claude/scripts/ralph/status.sh
```

## Output Format

All scripts output:
1. Human-readable summary (with colors)
2. `---JSON_OUTPUT---` marker
3. JSON for programmatic parsing

Example parsing in bash:
```bash
OUTPUT=$(.claude/scripts/ralph/status.sh)
JSON=$(echo "$OUTPUT" | sed -n '/---JSON_OUTPUT---/,$p' | tail -n +2)
CURRENT=$(echo "$JSON" | jq -r '.current')
```

## State File

Scripts maintain `workflow-state.json`:

```json
{
  "phase": "ralph",
  "ralph": {
    "current": 3,
    "total": 10,
    "current_ticket": "LOCAL-004",
    "tickets": [
      {"id": "LOCAL-001", "status": "done", "pr": "12", "attempts": 1},
      {"id": "LOCAL-002", "status": "done", "pr": "13", "attempts": 1},
      {"id": "LOCAL-003", "status": "blocked", "pr": null, "attempts": 4},
      {"id": "LOCAL-004", "status": "in_progress", "pr": null, "attempts": 1}
    ],
    "blocked": [
      {"id": "LOCAL-003", "reason": "Dependency issue", "timestamp": "..."}
    ],
    "tickets_done": ["LOCAL-001", "LOCAL-002"]
  }
}
```

## Integration with ralph-prd

The updated `/ralph-prd` command should call these scripts:

```
1. setup.sh → Initialize
2. Loop:
   a. get-next-ticket.sh → Get ticket ID
   b. ticket-start.sh $TICKET → Mark in-progress
   c. [LLM] Plan & implement
   d. validate.sh → Check tests/lint/build
   e. If fail && attempts > 3: mark-blocked.sh
   f. If pass: pr-flow.sh → Commit/push/PR
   g. ticket-done.sh → Mark complete
3. cleanup.sh → Finalize
```

## PM Tool Integration

Note: These scripts handle LOCAL state only. Moving tickets in Trello/Asana/etc should still be done via MCP calls. The scripts update `workflow-state.json` which is the source of truth for ralph's cursor position.

---

## Orchestrator Script

The `orchestrator.sh` script runs **outside** of Claude and only invokes Claude for LLM-required work.

### Why Use the Orchestrator?

When Claude runs scripts via the Bash tool, each invocation still costs:
- An LLM turn to decide to call it
- API round-trip time
- An LLM turn to process the result

The orchestrator eliminates this overhead by running all mechanical work directly in your shell, only calling Claude when intelligence is actually needed.

### Usage

```bash
# From project root (not inside a Claude session!)
# Run /ralph-cmd in Claude to get the exact command

.claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

# Options
--dry-run         # Show what would happen without invoking Claude
--max-attempts N  # Max attempts per ticket before blocking (default: 3)
```

### What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (runs in your shell - no LLM)                │
│                                                             │
│  1. setup.sh         → Parse tickets, init state           │
│  2. Loop:                                                  │
│     a. get-next-ticket.sh → Find next pending              │
│     b. ticket-start.sh    → Mark in-progress               │
│                                                             │
│     ┌─────────────────────────────────────────────────┐    │
│     │  CLAUDE (LLM invocation via `claude -p`)        │    │
│     │  - Read PRD/Plan                                │    │
│     │  - Plan approach                                │    │
│     │  - Write tests (TDD)                            │    │
│     │  - Write implementation                         │    │
│     │  - Commit changes                               │    │
│     └─────────────────────────────────────────────────┘    │
│                                                             │
│     c. validate.sh    → Run tests/lint/build               │
│        If FAIL:                                            │
│        ┌─────────────────────────────────────────────┐    │
│        │  CLAUDE (LLM) - Analyze and fix failures    │    │
│        └─────────────────────────────────────────────┘    │
│                                                             │
│     d. pr-flow.sh     → Commit, push, PR, merge            │
│     e. ticket-done.sh → Update state                       │
│                                                             │
│  3. cleanup.sh       → Finalize, report results            │
└─────────────────────────────────────────────────────────────┘
```

### Estimated Savings

| Task | Without Orchestrator | With Orchestrator |
|------|---------------------|-------------------|
| Setup | 2-3 LLM turns | 0 LLM turns |
| Per-ticket overhead | 8-10 LLM turns | 1-2 LLM turns |
| 10-ticket PRD | ~100 LLM turns | ~20 LLM turns |

That's roughly **80% fewer API calls** for mechanical work.

### Requirements

- `claude` CLI must be in your PATH
- `jq` for JSON parsing
- `timeout` command (standard on Linux, install via `brew install coreutils` on macOS)
