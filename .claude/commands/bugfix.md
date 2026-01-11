# Bugfix Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Standard bug fixes where root cause is already known. Delegates to `engineer` agent.**

## When to Use

**STANDARD BUG FIXES:**
- Root cause is understood
- Fix approach is clear
- Not a production emergency (use `/hotfix` for emergencies)
- No PRD/plan needed (unlike `/implement`)

## Workflow

```
/bugfix → branch (if needed) → engineer agent → PR
```

## Prerequisites Check

Before delegating, verify:
1. Bug description is provided
2. Root cause is understood (ask if unclear)
3. On a bugfix branch (create if not)

If root cause unclear:
- "The root cause isn't clear yet. Should I run `/rca` to investigate first?"

## Step 1: Ensure Bugfix Branch

Check current branch:

```bash
git branch --show-current
git status --short
```

If not on a bugfix branch, create one:

```bash
git checkout -b bugfix/{short-description}
```

## Step 2: Gather Bug Context

Before delegating, clarify with user if needed:

1. **Bug description** - What's broken?
2. **Root cause** - Why is it broken?
3. **Proposed fix** - How should it be fixed?
4. **Affected files** - What needs to change?

## Step 3: Delegate to Engineer Agent

```
Task({
  subagent_type: "engineer",
  model: "opus",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the engineer agent:

---

**ENGINEER AGENT TASK: Bug Fix (TDD)**

## Context

- **Bug:** $ARGUMENTS
- **Branch:** [current bugfix branch]
- **Project:** [current project directory]

## Bug Details

**Description:**
[What's broken - from user or conversation]

**Root Cause:**
[Why it's broken - from analysis]

**Proposed Fix:**
[How to fix it - from discussion]

**Affected Files:**
[Files that need to change]

## Objective

Fix the bug using Test-Driven Development. Write a failing test that reproduces the bug, then fix it.

## Required Steps

### 1. Write Failing Test (RED)

First, write a test that reproduces the bug:

```bash
# Create test that demonstrates the bug
# Run tests - the new test should FAIL
npm test
```

The failing test proves:
- We understand the bug
- We'll know when it's fixed
- We prevent regression

### 2. Implement Fix (GREEN)

Fix the bug with minimum changes:

```bash
# Make the fix
# Run tests - should now PASS
npm test
```

### 3. Refactor (if needed)

Clean up while tests stay green:
- Remove duplication
- Improve naming
- Simplify logic

### 4. Verify Quality

```bash
# All tests pass
npm test

# Linting passes
npm run lint

# Build succeeds (if applicable)
npm run build
```

### 5. Commit Changes

```bash
git add -A
git commit -m "[BUGFIX] {brief description}

- Root cause: {explain}
- Fix: {what changed}
- Test: {what test was added}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Deliverable

After fixing, return:

```
BUGFIX COMPLETE

Branch: bugfix/{description}

Bug: {what was broken}
Root Cause: {why it was broken}
Fix: {what was changed}

Files Changed:
- file1.js: {what changed}
- file2.js: {what changed}

Test Added:
- {test name}: {what it verifies}

Verification:
- Tests: PASS (N total, M new)
- Lint: PASS

Commits: [N] commits on branch

Next: Ready for /pr
```

## Critical Rules

1. **Test FIRST** - Write failing test before fixing
2. **Minimal fix** - Don't refactor unrelated code
3. **No broken tests** - All tests must pass before commit
4. **Clear commit message** - Explain root cause and fix

---

## After Agent Returns

1. **Verify** tests pass
2. **Verify** the bug is actually fixed (manual check if needed)
3. **Summarize** fix for user
4. **Next step:** User can run `/pr` to create pull request

## Bug to Fix

$ARGUMENTS
