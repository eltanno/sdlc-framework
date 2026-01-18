# Ticket Reset - Reset a blocked ticket to pending

**Reset a blocked or failed ticket so it can be worked on again.**

## Purpose

When a ticket has been marked as blocked (exceeded max attempts, validation failures, etc.), this command resets it back to a pending state so the Ralph loop can attempt it again.

## Arguments

$ARGUMENTS

The argument should be a ticket ID (e.g., `AUCT-0055`).

## Action

Run the ticket reset script:

```bash
.claude/scripts/ralph/ticket-reset.sh <ticket-id> --clean-state
```

### What This Does

1. **Removes from blocked array** - The ticket is no longer considered blocked
2. **Sets status to pending** - Ready to be picked up by the Ralph loop
3. **Resets attempts to 0** - Fresh start with full retry budget
4. **Cleans state files** - Removes previous attempt directories (optional with `--clean-state`)

## Options

- `--clean-state` - Also delete the state files in `docs/state/<ticket>/` for a completely fresh start

## When to Use

Use this command when:
- A ticket was blocked due to infrastructure issues (not code issues)
- You've fixed the underlying bug that caused failures
- You want to retry a ticket with updated prompts or configuration
- The ticket failed due to transient errors

## Example

```bash
# Reset AUCT-0055 and clean its state files
.claude/scripts/ralph/ticket-reset.sh AUCT-0055 --clean-state
```

## After Reset

After resetting, you can run the Ralph loop again:

```bash
.claude/scripts/ralph-prd.sh <prd-path> <plan-path>
```

The reset ticket will be picked up as the next pending ticket.
