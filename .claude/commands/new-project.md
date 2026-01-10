# New Project - Orchestrator Direct Task

**You are the orchestrator. This is a coordination task - do it yourself.**

This command creates a new project folder with the SDLC framework files from the current project.

## Process

### 1. Ask for Target Location

Use `AskUserQuestion` to prompt the user for the target folder path:

```
"Where should the new project be created? Provide the full path."
```

### 2. Validate and Create Folder

```bash
# Check if folder already exists
if [ -d "$TARGET_PATH" ]; then
  echo "Warning: Folder already exists"
  # Ask user if they want to proceed
fi

# Create the folder
mkdir -p "$TARGET_PATH"
```

### 3. Copy SDLC Framework Files

Copy these files/folders to the new project:

```bash
# Core SDLC files
cp -r .claude "$TARGET_PATH/"
cp CLAUDE.md "$TARGET_PATH/"
cp WORKFLOW.md "$TARGET_PATH/"

# Templates only from docs
mkdir -p "$TARGET_PATH/docs/templates"
cp -r docs/templates/* "$TARGET_PATH/docs/templates/" 2>/dev/null || true

# Config file if present
cp config.yaml "$TARGET_PATH/" 2>/dev/null || true
```

**DO NOT copy:**
- `.git/` - New project gets fresh git
- `.env` - Contains secrets/project-specific config
- `docs/` (except templates) - Project-specific documents
- Any other project-specific files

### 4. Initialize Git

```bash
cd "$TARGET_PATH"
git init
echo "# New Project" > README.md
git add .
git commit -m "Initial commit: SDLC framework setup"
```

### 5. Confirm Completion

Report to user:

```markdown
## New Project Created

**Location:** $TARGET_PATH

**Files copied:**
- `.claude/` (agents, commands, scripts, settings)
- `CLAUDE.md`, `WORKFLOW.md`
- `docs/templates/`
- `config.yaml` (if present)

**Git initialized** with initial commit.

**Next steps:**
1. `cd $TARGET_PATH`
2. Run `/discover` to start requirements gathering
3. Or run `/status` to see available commands
```

## Error Handling

- If target path is invalid, ask for a valid path
- If folder exists and has files, warn user before proceeding
- If copy fails, report which files failed

## Notes

- This command creates a clean SDLC framework copy
- No project-specific content is transferred
- User starts fresh with empty docs/ (except templates)
