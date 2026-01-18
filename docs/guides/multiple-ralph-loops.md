# Running Multiple Concurrent Ralph Loops

This guide explains how to run multiple ralph instances simultaneously using git worktrees.

## Overview

Each ralph instance needs:
- Its own working directory (to avoid file conflicts)
- A unique label (to claim tickets without collision)

Git worktrees provide isolated working directories that share the same git database, making them ideal for this use case.

## Prerequisites

- Git 2.5+ (worktree support)
- GitHub CLI (`gh`) authenticated
- Existing ralph-enabled repository

## Setup

### 1. Restructure for Worktrees

If your repo is at `~/workspace/getstirrup.com`, restructure to contain worktrees:

```bash
cd ~/workspace

# Rename current repo temporarily
mv getstirrup.com getstirrup-temp

# Create project container
mkdir getstirrup.com

# Move repo into container as "main"
mv getstirrup-temp getstirrup.com/main
```

### 2. Create Worktrees

```bash
cd ~/workspace/getstirrup.com/main

# Create worktrees from origin/main (not the branch - avoids checkout conflict)
git worktree add ../ralph-1 origin/main
git worktree add ../ralph-2 origin/main
```

**Result:**
```
~/workspace/getstirrup.com/
├── main/       <- your development work
├── ralph-1/    <- ralph instance 1
└── ralph-2/    <- ralph instance 2
```

### 3. Configure Each Worktree

Create a `.env` file in each ralph worktree:

```bash
# ralph-1/.env
echo "RALPH_LABEL=ralph-1" > ~/workspace/getstirrup.com/ralph-1/.env

# ralph-2/.env
echo "RALPH_LABEL=ralph-2" > ~/workspace/getstirrup.com/ralph-2/.env
```

The label format must match `{prefix}{number}` (e.g., `ralph-1`, `ralph-2`).

## Running Ralph

### Start Each Instance

Open separate terminals for each ralph instance:

```bash
# Terminal 1
cd ~/workspace/getstirrup.com/ralph-1
./start-ralph.sh   # RALPH_LABEL loaded from .env

# Terminal 2
cd ~/workspace/getstirrup.com/ralph-2
./start-ralph.sh   # RALPH_LABEL loaded from .env
```

Alternatively, pass the label inline (overrides .env):

```bash
RALPH_LABEL=ralph-3 ./start-ralph.sh
```

### How It Works

1. **Startup:** Ralph validates the label format and ensures the label exists in GitHub (creates if missing)
2. **Conflict check:** If open issues already have this label, prompts for confirmation
3. **Ticket selection:** Queries GitHub for next available ticket, skipping those claimed by other instances
4. **Claiming:** Adds the instance label to the issue being worked on
5. **Branching:** Creates feature branch from `origin/main` (no checkout conflict)
6. **Completion:** Removes label, merges PR, moves to next ticket

## Updating Worktrees

When main is updated (by you or other ralph instances), update your worktrees:

```bash
# Update all worktrees
cd ~/workspace/getstirrup.com/ralph-1 && git fetch origin main && git checkout origin/main
cd ~/workspace/getstirrup.com/ralph-2 && git fetch origin main && git checkout origin/main
```

Or from the main repo:

```bash
cd ~/workspace/getstirrup.com/main
git pull origin main  # Updates shared git database
```

The worktrees will see the new commits when they next `git fetch`.

## Managing Worktrees

### List Worktrees

```bash
cd ~/workspace/getstirrup.com/main
git worktree list
```

### Add Another Worktree

```bash
cd ~/workspace/getstirrup.com/main
git worktree add ../ralph-3 origin/main
echo "RALPH_LABEL=ralph-3" > ../ralph-3/.env
```

### Remove a Worktree

```bash
cd ~/workspace/getstirrup.com/main
git worktree remove ../ralph-3
```

## Configuration Reference

### .env Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RALPH_LABEL` | Unique identifier for this instance | `ralph-1` |

### config.yaml (Shared)

```yaml
ralph:
  instance_label_prefix: "ralph-"  # Shared prefix for all instances
  # instance_label is NOT set here - use .env per worktree
```

## Database Isolation

When running backend tests, each ralph instance uses a separate test database to avoid collisions.

**How it works:**
- `RALPH_LABEL=ralph-1` → test database: `test_stirrup_ralph_1`
- `RALPH_LABEL=ralph-2` → test database: `test_stirrup_ralph_2`
- No label → test database: `test_stirrup` (default)

This is configured in `backend/config/settings/base.py` and happens automatically when `RALPH_LABEL` is set in the environment.

**Requirements:**
- PostgreSQL must be running (via docker-compose)
- The postgres user must have permission to create databases
- Each test database is created/destroyed automatically by pytest-django

## Troubleshooting

### "Label already in use" Warning

If you see this on startup, another ralph instance may be using the same label:

```
Warning: Label 'ralph-1' has 1 open issue(s).
Resume existing work with this label? (y/n):
```

Options:
- **Yes:** Resume the existing work (useful if previous instance crashed)
- **No:** Exit and update `RALPH_LABEL` in `.env` to use a different label

### Branch Checkout Conflicts

If you see:
```
fatal: 'main' is already checked out at '/path/to/main'
```

Use `origin/main` instead of `main` when creating worktrees:
```bash
git worktree add ../ralph-1 origin/main
```

### Worktrees Out of Sync

If a worktree is behind:
```bash
cd ~/workspace/getstirrup.com/ralph-1
git fetch origin main
git checkout origin/main
```

## Best Practices

1. **Use dedicated terminals:** Each ralph instance should run in its own terminal
2. **Monitor progress:** Check GitHub Issues to see which tickets each instance is working on
3. **Don't share labels:** Each concurrent instance must have a unique label
4. **Keep main for development:** Use the `main/` worktree for your manual development work
5. **Pull before starting:** Update worktrees before starting ralph to get latest merged changes
