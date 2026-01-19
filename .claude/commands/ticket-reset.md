# Ticket Reset - Reset a blocked ticket to pending

**Reset a blocked or failed ticket so it can be worked on again.**

## Purpose

When a ticket has been marked as blocked (exceeded max attempts, validation failures, etc.), this command resets it back to a pending state so the Ralph loop can attempt it again.

## Arguments

$ARGUMENTS

The argument should be a ticket ID (e.g., `SDLC-0055`).

## Action

Run the ticket reset command:

```bash
.claude/ralph/ralph reset <ticket-id>
```

### What This Does

1. **Validates ticket is blocked** - Only blocked tickets can be reset
2. **Sets status to pending** - Ready to be picked up by the Ralph loop
3. **Clears block reason** - Previous failure reason is removed
4. **Resets attempts to 0** - Fresh start with full retry budget
5. **Updates blocked count** - Decrements the blocked ticket counter

## Prerequisites

- Python 3.10 or higher
- Valid `workflow-state.json` file in the project root

## When to Use

Use this command when:
- A ticket was blocked due to infrastructure issues (not code issues)
- You've fixed the underlying bug that caused failures
- You want to retry a ticket with updated prompts or configuration
- The ticket failed due to transient errors

## Example

```bash
# Reset SDLC-0055 to pending status
.claude/ralph/ralph reset SDLC-0055
```

## After Reset

After resetting, you can run the Ralph loop again:

```bash
.claude/ralph/ralph run <prd-path> <plan-path>
```

The reset ticket will be picked up as the next pending ticket.
