# Ralph Command - Output the command to start Ralph loop

**Output the shell command to run the Ralph orchestrator.**

## Purpose

This command outputs the exact shell command you should run **outside of Claude** to start the Ralph PRD implementation loop. The orchestrator runs in your terminal and only invokes Claude when LLM intelligence is needed.

## Action

Find the most recent approved PRD and its corresponding plan, then output the command.

### Step 1: Find PRD and Plan

```bash
# Find most recent approved PRD
ls -t docs/prds/*.md 2>/dev/null | head -5

# Check for corresponding plan
ls -t docs/plans/*.md 2>/dev/null | head -5
```

### Step 2: Output Command

If arguments provided, use those. Otherwise, identify the PRD/Plan from the files above.

**Output format:**

```
══════════════════════════════════════════════════════════════
  RALPH ORCHESTRATOR COMMAND
══════════════════════════════════════════════════════════════

Run this command in your terminal (NOT inside Claude):

  .claude/scripts/ralph-prd.sh <prd-path> <plan-path>

Example with detected files:

  .claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

Options:
  --dry-run         Preview without invoking Claude
  --max-attempts N  Max retries per ticket (default: 3)

══════════════════════════════════════════════════════════════

Copy and paste the command above into a NEW terminal window.
Do NOT run it inside this Claude session.
```

## Why Outside Claude?

Running the orchestrator outside Claude means:
- Zero LLM cost for mechanical work (state, validation, git, PRs)
- Claude only invoked for implementation and fixing failures
- ~80% fewer API calls compared to running everything through Claude

## Arguments

$ARGUMENTS

If a PRD path is provided, use it. Otherwise, detect from docs/prds/.
