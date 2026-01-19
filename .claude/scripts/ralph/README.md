# Ralph Scripts

Scripts to optimize the `/ralph-prd` loop by handling non-LLM work.

## Purpose

These scripts handle the mechanical parts of the ralph loop that don't require LLM intelligence:
- State management (GitHub Issues or workflow-state.json)
- Status line updates
- Git operations
- PR creation/merging
- Validation (tests, lint, build)

The LLM only needs to focus on:
- Planning implementation approach
- Writing code
- Fixing failures
- Validating acceptance criteria

## Source of Truth

Scripts check `config.yaml` for the PM tool setting:

```yaml
pm:
  tool: github  # github | asana | trello | none
```

### GitHub Mode (pm.tool: github)

When `pm.tool` is `github`, **GitHub Issues are the source of truth**:

- `setup.sh` - Fetches open issues from GitHub
- `get-next-ticket.sh` - Queries GitHub for unassigned issues
- `ticket-start.sh` - Assigns issue to current user (atomic - prevents race conditions)
- `ticket-done.sh` - Closes the GitHub issue
- `mark-blocked.sh` - Adds 'blocked' label and comment

**Benefits:**
- Multiple Ralph instances can run concurrently without conflicts
- Issue assignment is atomic (no race conditions)
- Ticket status is visible in GitHub Issues UI
- Any machine can resume work (not tied to local state)

### Local Mode (pm.tool: not github)

Falls back to `workflow-state.json` as source of truth (original behavior).

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

### GitHub Mode

```bash
# Setup (fetches issues from GitHub)
.claude/scripts/ralph/setup.sh

# Or filter by label
.claude/scripts/ralph/setup.sh --label "offline-first"

# Get next ticket (queries GitHub for unassigned issues)
.claude/scripts/ralph/get-next-ticket.sh
# Returns: AUCT-0133 (GitHub #51)

# Start ticket (assigns issue to you - prevents others from picking it)
.claude/scripts/ralph/ticket-start.sh AUCT-0133 --issue 51
# ... LLM implements ticket ...

# Done (closes the issue)
.claude/scripts/ralph/ticket-done.sh AUCT-0133 42 --issue 51  # 42 = PR number

# Mark blocked (adds label, unassigns, adds comment)
.claude/scripts/ralph/mark-blocked.sh AUCT-0133 "Tests failing" --issue 51
```

### Local Mode (Original Behavior)

```bash
# Setup (parses PRD/Plan for tickets)
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

## Ticket ID Format

GitHub issues must have ticket IDs in their titles:

```
[AUCT-0133] Implement user authentication
```

The scripts extract the ticket ID from the `[PREFIX-NNNN]` format.
The prefix is configured in `config.yaml`:

```yaml
tickets:
  prefix: "AUCT"
```

## Concurrency Safety

When using GitHub mode, multiple Ralph instances can run safely:

1. **Issue assignment is atomic** - When Ralph A assigns issue #51 to itself, GitHub ensures no race condition
2. **Unassigned query excludes assigned issues** - Ralph B won't see #51 after Ralph A claims it
3. **No local state conflicts** - Each Ralph works from GitHub's real-time state

## Output Format

All scripts output:
1. Human-readable summary (with colors)
2. `---JSON_OUTPUT---` marker
3. JSON for programmatic parsing

Example parsing in bash:
```bash
OUTPUT=$(.claude/scripts/ralph/get-next-ticket.sh)
JSON=$(echo "$OUTPUT" | sed -n '/---JSON_OUTPUT---/,$p' | tail -n +2)
TICKET=$(echo "$JSON" | jq -r '.next_ticket')
ISSUE=$(echo "$JSON" | jq -r '.issue_number')
```

## State File

Scripts maintain `workflow-state.json` as a backup/cache:

```json
{
  "phase": "ralph",
  "ralph": {
    "source": "github",
    "current": 3,
    "total": 21,
    "current_ticket": "AUCT-0136",
    "tickets": [
      {"id": "AUCT-0133", "issue_number": 51, "status": "done", "pr": "12", "attempts": 1},
      {"id": "AUCT-0134", "issue_number": 52, "status": "done", "pr": "13", "attempts": 1},
      {"id": "AUCT-0135", "issue_number": 53, "status": "blocked", "pr": null, "attempts": 4},
      {"id": "AUCT-0136", "issue_number": 54, "status": "in_progress", "pr": null, "attempts": 1}
    ],
    "blocked": [
      {"id": "AUCT-0135", "issue_number": 53, "reason": "Dependency issue", "timestamp": "..."}
    ],
    "tickets_done": ["AUCT-0133", "AUCT-0134"]
  }
}
```

**Note:** In GitHub mode, `workflow-state.json` is a cache. GitHub Issues are the source of truth.

## Integration with ralph-prd

The updated `/ralph-prd` command should call these scripts:

```
1. setup.sh → Initialize (fetches from GitHub or parses PRD/Plan)
2. Loop:
   a. get-next-ticket.sh → Get ticket ID and issue number
   b. ticket-start.sh $TICKET --issue $ISSUE → Assign issue to self
   c. [LLM] Plan & implement
   d. validate.sh → Check tests/lint/build
   e. If fail && attempts > 3: mark-blocked.sh
   f. If pass: pr-flow.sh → Commit/push/PR
   g. ticket-done.sh → Close issue
3. cleanup.sh → Finalize
```

## Requirements

- `gh` CLI - For GitHub mode (must be authenticated: `gh auth login`)
- `jq` - For JSON parsing
- `config.yaml` - Must have `pm.tool` and `tickets.prefix` configured

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

.claude/ralph/ralph run docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

# Options
--dry-run         # Show what would happen without invoking Claude
--max-attempts N  # Max attempts per ticket before blocking (default: 3)
--verbose         # Show debug output and stack traces
```

**Prerequisites:** Python 3.10 or higher

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
