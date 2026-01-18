# Multi-Instance Ralph Setup Guide

**Purpose:** Configure multiple Ralph instances to run concurrently using the same GitHub user account.

---

## Overview

By default, Ralph uses GitHub issue assignment to prevent multiple instances from working on the same ticket. This works well when each instance runs under a different GitHub user, but fails when multiple instances share the same account (e.g., running multiple Claude Code sessions with the same GitHub credentials).

This guide explains how to use **label-based concurrency control** to enable multiple Ralph instances to run simultaneously without conflicts.

---

## Prerequisites

Before setting up multi-instance Ralph:

1. **GitHub Repository Access** - Admin or maintainer access to create labels
2. **Ralph Scripts Installed** - The label-based concurrency scripts (AUCT-0154 through AUCT-0159)
3. **Separate config.yaml per Instance** - Each instance needs its own configuration

---

## Step 1: GitHub Label Creation

Create labels in your GitHub repository for each Ralph instance you plan to run.

### Via GitHub Web UI

1. Navigate to your repository on GitHub
2. Go to **Settings** > **Labels** (in the left sidebar under "Code and automation")
3. Click **New label**
4. Create a label for each instance:

| Label Name | Description | Suggested Color |
|------------|-------------|-----------------|
| `ralph-1` | Ralph instance 1 in-progress | Green (#0E8A16) |
| `ralph-2` | Ralph instance 2 in-progress | Blue (#1D76DB) |
| `ralph-3` | Ralph instance 3 in-progress | Purple (#5319E7) |

### Via GitHub CLI

```bash
# Create labels for multi-instance setup
gh label create "ralph-1" --description "Ralph instance 1 in-progress" --color "0E8A16"
gh label create "ralph-2" --description "Ralph instance 2 in-progress" --color "1D76DB"
gh label create "ralph-3" --description "Ralph instance 3 in-progress" --color "5319E7"
```

**Important:** Labels must be created before starting Ralph instances. The scripts will fail with a clear error if the configured label doesn't exist.

---

## Step 2: Configuration Settings

Configure each Ralph instance with unique label settings in `config.yaml`.

### Configuration Options

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| `ralph.instance_label` | string | This instance's unique label (e.g., `ralph-1`) | `""` (empty) |
| `ralph.instance_label_prefix` | string | Prefix to identify all instance labels | `"ralph-"` |
| `ralph.use_assignee` | boolean | Also assign issues to user (for visibility) | `true` |

### Single-Instance Configuration (Backward Compatible)

If you're running only one Ralph instance, no changes are needed. The default behavior uses assignee-based concurrency:

```yaml
# config.yaml - Single instance (default behavior)
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  # No instance_label configured - uses assignee-based behavior
```

### Multi-Instance Configuration

For multiple instances sharing the same GitHub user, configure each with a unique label:

**Instance 1 (`config.yaml`):**
```yaml
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  instance_label: "ralph-1"
  instance_label_prefix: "ralph-"
  use_assignee: false  # Disable since all instances share the same user
```

**Instance 2 (`config.yaml`):**
```yaml
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  instance_label: "ralph-2"
  instance_label_prefix: "ralph-"
  use_assignee: false
```

**Instance 3 (`config.yaml`):**
```yaml
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  instance_label: "ralph-3"
  instance_label_prefix: "ralph-"
  use_assignee: false
```

---

## How It Works

### Claiming a Ticket

When an instance starts work on a ticket:

1. **Old behavior (assignee):** `gh issue edit --add-assignee @me`
2. **New behavior (labels):** `gh issue edit --add-label ralph-1`

### Finding Next Ticket

When looking for the next available ticket:

1. Query issues with `status:pending` or similar
2. Filter out issues that have ANY label matching `ralph-*` prefix
3. Exception: Issues with THIS instance's label are "resume" candidates, not skipped

### Releasing a Ticket

When completing or blocking a ticket:

1. Remove the instance label: `gh issue edit --remove-label ralph-1`
2. This frees the ticket for other instances (if blocked) or marks it complete

---

## Troubleshooting

### Error: "Label 'ralph-X' does not exist"

**Cause:** The configured `instance_label` hasn't been created in the GitHub repository.

**Solution:**
1. Go to repository Settings > Labels
2. Create the missing label (e.g., `ralph-1`)
3. Restart the Ralph instance

### Ticket Stuck with Label After Crash

**Cause:** Ralph instance crashed or was terminated while working on a ticket.

**Solution:**
1. Find the stuck issue in GitHub
2. Manually remove the instance label (`ralph-1`, etc.)
3. The ticket will now be picked up by the next available instance

```bash
# Remove label manually
gh issue edit <issue-number> --remove-label ralph-1
```

### Two Instances Claimed Same Ticket

**Cause:** Race condition (extremely rare with GitHub's atomic operations)

**Solution:**
1. One instance should detect the conflict on next API call
2. If needed, manually remove one instance's label
3. Consider adding a small random delay between instance starts

### Instance Not Finding Any Tickets

**Cause:** All pending tickets may have `ralph-*` labels from other instances.

**Verify:**
```bash
# List issues with ralph labels
gh issue list --label "ralph-1" --label "ralph-2"

# List pending issues without ralph labels
gh issue list --label "status:pending" --search "-label:ralph-1 -label:ralph-2"
```

---

## Migration from Assignee-Based to Label-Based

If you're already running Ralph with assignee-based concurrency:

1. **Create labels** in the repository (Step 1 above)
2. **Update config.yaml** with `instance_label` settings
3. **Set `use_assignee: false`** if running multiple instances with same user
4. **Restart Ralph instances** - they'll begin using labels

**Rollback:** If issues occur, remove `instance_label` from config.yaml and Ralph will fall back to assignee-based behavior.

---

## Best Practices

1. **Color-code labels** - Makes it easy to see which instance is working on what
2. **Use sequential names** - `ralph-1`, `ralph-2`, etc. for clarity
3. **Monitor stuck labels** - Check periodically for orphaned labels from crashed instances
4. **Start instances staggered** - Add 5-10 second delays between starting instances to avoid initial race conditions

---

## Related Documentation

- [Implementation Plan: Ralph Label-Based Concurrency](../plans/2026-01-17-ralph-label-concurrency.md)
- [Ralph PRD Loop Analysis](./ralph-prd-loop-analysis.md)
- [Workflow Transition Guide](./workflow-transition-guide.md)
