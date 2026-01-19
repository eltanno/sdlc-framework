# Running Multiple Ralph Instances

Run multiple ralph instances concurrently using git worktrees and label-based ticket claiming.

## Overview

Each ralph instance needs:
- Its own working directory (git worktree)
- A unique label (to claim tickets without collision)

Git worktrees provide isolated working directories sharing the same git database. Label-based claiming prevents multiple instances from working on the same ticket.

## Prerequisites

- Git 2.5+ (worktree support)
- GitHub CLI (`gh`) authenticated
- Repository admin access (to create labels)

## Setup

### 1. Create Directory Structure

If your repo is at `~/workspace/myproject`, restructure to contain worktrees:

```bash
cd ~/workspace

# Rename current repo temporarily
mv myproject myproject-temp

# Create project container
mkdir myproject

# Move repo into container as "main"
mv myproject-temp myproject/main
```

### 2. Create Worktrees

```bash
cd ~/workspace/myproject/main

# Create worktrees from origin/main (avoids checkout conflict)
git worktree add ../ralph-1 origin/main
git worktree add ../ralph-2 origin/main
```

**Result:**
```
~/workspace/myproject/
├── main/       <- your development work
├── ralph-1/    <- ralph instance 1
└── ralph-2/    <- ralph instance 2
```

### 3. Create GitHub Labels

Labels are created automatically on first run, but you can create them manually:

```bash
gh label create "ralph-1" --description "Ralph instance 1" --color "0E8A16"
gh label create "ralph-2" --description "Ralph instance 2" --color "1D76DB"
```

### 4. Configure Each Worktree

Create a `.env` file in each ralph worktree:

```bash
echo "RALPH_LABEL=ralph-1" > ~/workspace/myproject/ralph-1/.env
echo "RALPH_LABEL=ralph-2" > ~/workspace/myproject/ralph-2/.env
```

## Running Ralph

Open separate terminals for each instance:

```bash
# Terminal 1
cd ~/workspace/myproject/ralph-1
# Start ralph (RALPH_LABEL loaded from .env)

# Terminal 2
cd ~/workspace/myproject/ralph-2
# Start ralph (RALPH_LABEL loaded from .env)
```

### How It Works

1. **Startup:** Validates label format, creates label in GitHub if missing
2. **Ticket selection:** Queries GitHub for next available ticket, skipping those claimed by other instances
3. **Claiming:** Adds instance label to the issue being worked on
4. **Work:** Creates feature branch, implements, runs tests
5. **Completion:** Removes label, merges PR, moves to next ticket

## Updating Worktrees

When main is updated (by you or other instances), update worktrees:

```bash
cd ~/workspace/myproject/ralph-1 && git fetch origin && git reset --hard origin/main
cd ~/workspace/myproject/ralph-2 && git fetch origin && git reset --hard origin/main
```

Use `git reset --hard` to ensure clean state.

## Managing Worktrees

```bash
# List worktrees
git worktree list

# Add another worktree
git worktree add ../ralph-3 origin/main
echo "RALPH_LABEL=ralph-3" > ../ralph-3/.env

# Remove a worktree
git worktree remove ../ralph-3
```

## Concurrent Completion

When running multiple instances, they finish at different times:

- **First to finish:** Reports "incomplete" (tickets pending for other instances)
- **Last to finish:** Reports "complete" (all tickets done)

This is normal. Each instance reports its summary with accurate GitHub totals.

## Troubleshooting

### Ticket Stuck with Label After Crash

```bash
# Remove label manually
gh issue edit <issue-number> --remove-label ralph-1
```

### Branch Checkout Conflicts

Use `origin/main` instead of `main` when creating worktrees:
```bash
git worktree add ../ralph-1 origin/main
```

### Worktree Out of Sync

```bash
cd ~/workspace/myproject/ralph-1
git fetch origin && git reset --hard origin/main
```

### Instance Not Finding Tickets

All tickets may be claimed by other instances:
```bash
# Check which issues have ralph labels
gh issue list --state open --json number,title,labels | jq '.[] | select(.labels[].name | startswith("ralph-"))'
```

## Configuration Reference

### .env (per worktree)

| Variable | Description | Example |
|----------|-------------|---------|
| `RALPH_LABEL` | Unique instance identifier | `ralph-1` |

### config.yaml (shared)

```yaml
ralph:
  instance_label_prefix: "ralph-"  # Prefix for all instance labels
  max_attempts: 3
```

## Best Practices

1. **Use dedicated terminals** for each instance
2. **Don't share labels** - each instance needs a unique label
3. **Keep main for development** - use worktrees only for ralph
4. **Update before starting** - pull latest before starting ralph
5. **Monitor GitHub Issues** - see which tickets each instance is working on
