# Sync Framework - Update Existing Project

> **Direct execution - no delegation needed.**

## Usage

```
/sync-framework <target-path> [--dry-run]
```

## Arguments

- `target-path` - Path to the existing project to update (required)
- `--dry-run` - Show what would change without making changes

## Examples

```
/sync-framework ~/projects/my-app
/sync-framework ../other-project --dry-run
```

## What Gets Synced

| Location | Behavior |
|----------|----------|
| `.claude/` | Auto-synced (commands, scripts, agents) |
| `docs/templates/` | Auto-synced |
| `docs/guides/` | Auto-synced |
| `WORKFLOW.md` | Prompted if different |
| `CLAUDE.md` | Prompted if different |
| `config.yaml` | Prompted if different |
| `docs/coding-standards.md` | Prompted if different |
| `.gitignore` | Prompted if different |
| `.mcp.json` | Prompted if different |

For prompted files, if you approve the update:
- The existing file is backed up to `{filename}.old`
- The new framework version is copied in
- You can merge customizations from the `.old` file manually

## Execution

**Before running:** Confirm with the user that they understand files may be overwritten in the target directory.

Run the sync script:

```bash
.claude/scripts/sync-framework.sh $ARGUMENTS
```

## After Execution

Remind the user:
1. Check any `.old` files for customizations to merge back
2. Delete `.old` files when done reviewing
3. Test the project to ensure everything works

## Target Path

$ARGUMENTS
