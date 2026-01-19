# Ralph Loop Crash Recovery Guide

**Purpose:** Restore the system to a known good state after an unexpected shutdown or crash during ralph loop execution.

---

## Overview

When a PC shuts down or a ralph loop is forcibly terminated mid-execution, several things may be left in an inconsistent state:

1. **Uncommitted code changes** in the worktree
2. **GitHub labels** still claiming tickets (blocking other instances)
3. **Partial implementations** that may or may not be functional
4. **State files** that don't reflect reality

This guide provides a systematic procedure to recover from such situations.

---

## Recovery Procedure

**Important:** All recovery work should be done from a Claude instance in the **main worktree**. This ensures you have a clean context and can manage each crashed worktree systematically.

### Step 1: Identify Active Worktrees

From the main worktree, list all git worktrees:

```bash
git worktree list
```

Example output:
```
/home/jim/workspace/getstirrup.com/main     d8a7e32 [main]
/home/jim/workspace/getstirrup.com/ralph-1  967516f [feature/AUCT-0162-implementation]
/home/jim/workspace/getstirrup.com/ralph-2  d1eff99 [feature/AUCT-0163-implementation]
```

Note which worktrees are on feature branches - these were likely active during the crash.

### Step 2: Check GitHub for Claimed Tickets

Find tickets that still have ralph instance labels:

```bash
# Check for tickets claimed by ralph-1
gh issue list --label "ralph-1" --state open

# Check for tickets claimed by ralph-2
gh issue list --label "ralph-2" --state open

# List all tickets with any ralph label
gh issue list --label "ralph-1" --label "ralph-2" --state open
```

### Step 3: Assess Each Worktree

For each ralph worktree, check the current state:

```bash
# Check uncommitted changes
cd /home/jim/workspace/getstirrup.com/ralph-1
git status

# Check the current branch
git branch --show-current

# Check recent commits
git log --oneline -5

# Check state files for the ticket
ls -la docs/state/AUCT-XXXX/
```

### Step 4: Evaluate the Work Quality

Before deciding how to proceed, assess what was accomplished:

1. **Read the state files** to understand progress:
   ```bash
   cat docs/state/AUCT-XXXX/attempt-N/engineer-state.json
   cat docs/state/AUCT-XXXX/summary.md
   ```

2. **Check if tests pass** (if there's code):
   ```bash
   npm test  # or appropriate test command
   ```

3. **Review uncommitted changes**:
   ```bash
   git diff
   git diff --cached
   ```

### Step 5: Choose Recovery Path

Based on your assessment, choose one of these paths:

#### Path A: Work is Complete or Nearly Complete

If the implementation looks good and tests pass:

1. **Commit the changes properly**:
   ```bash
   git add -A
   git commit -m "[AUCT-XXXX] Complete implementation (recovered from crash)

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

2. **Run validation manually**:
   ```bash
   npm test
   npm run build
   npm run lint
   ```

3. **Create PR if ready**:
   ```bash
   gh pr create --title "[AUCT-XXXX] Feature description" --body "..."
   ```

4. **Release the GitHub label**:
   ```bash
   gh issue edit XXXX --remove-label ralph-1
   ```

#### Path B: Work is Partial but Salvageable

If there's useful progress but it's incomplete:

1. **Commit as WIP**:
   ```bash
   git add -A
   git commit -m "[AUCT-XXXX] WIP - recovered from crash

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

2. **Option 1: Continue manually** - Start a Claude session in that worktree and finish the work:
   ```bash
   cd /home/jim/workspace/getstirrup.com/ralph-1
   claude
   # Then: "Continue implementing AUCT-XXXX based on the existing work"
   ```

3. **Option 2: Let ralph retry** - Leave the label in place and restart the loop. Ralph will see the in-progress ticket and continue from where it left off.

#### Path C: Work is Broken or Minimal

If the changes are problematic:

1. **Discard uncommitted changes**:
   ```bash
   git checkout -- .
   git clean -fd
   ```

2. **Release the GitHub label** so another attempt can be made:
   ```bash
   gh issue edit XXXX --remove-label ralph-1
   ```

3. **Optionally reset to a known good commit**:
   ```bash
   git log --oneline -10  # Find a good commit
   git reset --hard <commit-hash>
   ```

### Step 6: Clean Up GitHub State

After handling all worktrees, ensure GitHub is clean:

```bash
# Verify no orphaned labels remain
gh issue list --label "ralph-1" --state open
gh issue list --label "ralph-2" --state open

# If any remain that shouldn't, remove them:
gh issue edit <number> --remove-label ralph-1
```

### Step 7: Sync Branches with Main

Before restarting loops, ensure branches are up to date:

```bash
# For each worktree
cd /home/jim/workspace/getstirrup.com/ralph-1
git fetch origin
git merge origin/main -m "Merge main before restart"
git push origin HEAD
```

### Step 8: Restart the Loops

Once everything is clean:

```bash
# In ralph-1 terminal
cd /home/jim/workspace/getstirrup.com/ralph-1
.claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md

# In ralph-2 terminal
cd /home/jim/workspace/getstirrup.com/ralph-2
.claude/scripts/ralph-prd.sh docs/prds/YYYY-MM-DD-feature.md docs/plans/YYYY-MM-DD-feature.md
```

---

## Quick Reference Commands

```bash
# === From main worktree ===

# List all worktrees
git worktree list

# Check status of a specific worktree
git -C /path/to/ralph-1 status

# Check claimed tickets
gh issue list --label "ralph-1" --state open

# Release a ticket
gh issue edit <number> --remove-label ralph-1

# === In a ralph worktree ===

# Check current state
git status
git log --oneline -5
cat workflow-state.json | jq '.ralph'

# Discard all changes
git checkout -- . && git clean -fd

# Commit WIP
git add -A && git commit -m "[AUCT-XXXX] WIP - crash recovery"

# Sync with main
git fetch origin && git merge origin/main
```

---

## Prevention Tips

1. **Use UPS** - Uninterruptible power supply prevents sudden shutdowns
2. **Frequent commits** - Ralph commits after each successful validation
3. **State files** - Check `docs/state/AUCT-XXXX/` for progress tracking
4. **Monitor logs** - Logs are in `.logs/ralph/` with timestamps

---

## Troubleshooting

### "Another ralph instance is using this label"

After a crash, the label remains on the ticket. Either:
- Remove the label manually: `gh issue edit <num> --remove-label ralph-1`
- Or the script will now auto-resume (as of recent fix)

### Worktree shows "detached HEAD"

This is **expected behavior** for ralph worktrees. They run in detached HEAD mode to avoid conflicts with the main workspace (which always has `main` checked out).

After a PR merge, the worktree should automatically checkout detached at `origin/main`. If it's stuck on a deleted feature branch:

```bash
# Reset to latest main (detached)
git fetch origin main
git checkout --detach origin/main
```

### "fatal: 'main' is already checked out"

This error occurs when a script tries to checkout `main` in a worktree, but `main` is already checked out in the main workspace. Git doesn't allow the same branch to be checked out in multiple worktrees.

**Solution:** Worktrees should always use detached HEAD mode:
```bash
# Instead of: git checkout main
git checkout --detach origin/main
```

This has been fixed in `pr-flow.sh` but may appear in older recovery attempts.

### GitHub issues not auto-closing after PR merge

If PRs merge but the corresponding GitHub issues stay open, the issue wasn't linked correctly. This can happen if the PR body had the wrong issue number.

**To identify orphaned issues:**
```bash
# Find issues that should be closed (have ralph labels but PR was merged)
gh issue list --label "ralph-1" --state open
gh issue list --label "ralph-2" --state open

# Check if a PR exists for a ticket
gh pr list --search "AUCT-XXXX in:title" --state merged
```

**To fix:**
```bash
# Close the issue and remove the label
gh issue close <number>
gh issue edit <number> --remove-label ralph-1
```

### Loop exits immediately after picking up a ticket

If the loop picks up a ticket that was already completed (PR merged) but the issue is still open with a ralph label:

1. The worktree may be on detached HEAD with no branch
2. The script tries to push an empty branch name
3. PR creation fails with "not on any branch"

**Solution:**
```bash
# 1. Close the orphaned issue
gh issue close <number>

# 2. Remove the ralph label
gh issue edit <number> --remove-label ralph-1

# 3. Reset the worktree
cd /path/to/ralph-1
git fetch origin main
git checkout --detach origin/main
```

### Merge conflicts after syncing with main

Resolve manually or abort and start fresh:
```bash
# To abort
git merge --abort

# To start fresh on the ticket
git checkout main
git pull
git checkout -b feature/AUCT-XXXX-implementation
```

---

## Related Documentation

- [Multi-Instance Setup Guide](./multi-instance-setup.md)
- [Ralph PRD Loop Analysis](./ralph-prd-loop-analysis.md)
- [Workflow Guide](./workflow-guide.md)
