# Ralph Legacy Scripts

> **DEPRECATED**: These shell scripts have been superseded by the Python implementation in `.claude/ralph/`.
>
> This directory contains backup copies for rollback purposes only.

## Status

- **Superseded by:** `.claude/ralph/` (Python 3.10+)
- **Migration Date:** 2026-01-19
- **Reason:** Python port provides testability, maintainability, and reliability

## Use the New Python Version

```bash
# Run the orchestrator (Python version)
.claude/ralph/ralph run docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

# Reset a blocked ticket
.claude/ralph/ralph reset SDLC-0055

# Check status
.claude/ralph/ralph status
```

## Rollback Procedure

If critical issues are found with the Python version:

1. **Restore shell wrapper:**
   ```bash
   # Edit .claude/ralph/ralph to call legacy scripts
   # Replace content with:
   #!/bin/bash
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   exec "$SCRIPT_DIR/../scripts/ralph-legacy/ralph-prd.sh" "$@"
   ```

2. **Verify rollback:**
   ```bash
   .claude/ralph/ralph docs/prds/test.md docs/plans/test.md --dry-run
   ```

3. **Document the issue:** Create a GitHub issue describing the rollback reason

## Legacy Script Inventory

| Script | Lines | Purpose |
|--------|-------|---------|
| `ralph-prd.sh` | ~1,400 | Main orchestrator loop |
| `ralph-prd-commands.sh` | ~900 | Commands version of orchestrator |
| `config-helpers.sh` | ~350 | Configuration loading |
| `state-utils.sh` | ~600 | State file management |
| `setup.sh` | ~250 | Initialize ralph run |
| `get-next-ticket.sh` | ~400 | Find next pending ticket |
| `ticket-start.sh` | ~400 | Start work on ticket |
| `ticket-done.sh` | ~280 | Complete ticket |
| `mark-blocked.sh` | ~170 | Block ticket with reason |
| `ticket-reset.sh` | ~100 | Reset blocked ticket |
| `validate.sh` | ~200 | Run validation checks |
| `pr-flow.sh` | ~270 | PR creation/merge |
| `status.sh` | ~100 | Display status |
| `cleanup.sh` | ~120 | Finalize run |
| `parse-plan-deps.sh` | ~220 | Parse dependencies |
| `test-*.sh` | ~900 | Test scripts |

**Total:** ~5,830 lines (16 shell scripts)

## Python Equivalents

| Legacy Script | Python Module |
|--------------|---------------|
| `config-helpers.sh` | `core/config.py` |
| `state-utils.sh` | `core/state.py` |
| `ralph-prd.sh` | `commands/orchestrator.py` |
| `get-next-ticket.sh` | `commands/get_next.py` |
| `ticket-start.sh` | `commands/ticket_start.py` |
| `ticket-done.sh` | `commands/ticket_done.py` |
| `mark-blocked.sh` | `commands/mark_blocked.py` |
| `ticket-reset.sh` | `commands/ticket_reset.py` |
| `validate.sh` | `commands/validate.py` |
| `pr-flow.sh` | `commands/pr_flow.py` |
| `setup.sh` | `commands/setup.py` |
| `status.sh` | `commands/status.py` |
| `cleanup.sh` | `commands/cleanup.py` |
| `parse-plan-deps.sh` | `commands/parse_deps.py` |

## Why These Scripts Were Replaced

1. **Testability:** Shell scripts had 0% unit test coverage; Python achieves >90%
2. **Maintainability:** Complex control flow in shell is hard to debug
3. **Type Safety:** Python type hints catch errors before runtime
4. **Portability:** Python works consistently across Linux/macOS/WSL
5. **Reliability:** Atomic file operations, proper error handling

## DO NOT USE These Scripts Directly

These scripts are preserved only for:
- Rollback in case of critical Python issues
- Reference for behavior comparison
- Historical documentation

**Always use the Python version** at `.claude/ralph/` for normal operation.

---

*Last updated: 2026-01-19*
