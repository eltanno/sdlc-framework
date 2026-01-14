#!/bin/bash
#
# Capture Workflow Changes
#
# Syncs SDLC framework files back to the source framework project.
#

set -e

SRC="/home/jim/projects/test-todo-claude"
DEST="/home/jim/workspace/test-sdlc-project"

echo "=== Capture Workflow Changes ==="
echo "Source: $SRC"
echo "Destination: $DEST"
echo ""

# Check destination exists
if [ ! -d "$DEST" ]; then
    echo "Error: Destination not found: $DEST"
    exit 1
fi

# Dry run first
echo "=== Changes to sync ==="
echo ""

# Directories to sync entirely
echo "--- .claude/ directory ---"
rsync -avn --delete \
    --exclude='settings.local.json' \
    "$SRC/.claude/" "$DEST/.claude/" 2>/dev/null | grep -v "^$" | head -50

echo ""
echo "--- docs/templates/ directory ---"
rsync -avn --delete \
    "$SRC/docs/templates/" "$DEST/docs/templates/" 2>/dev/null | grep -v "^$" | head -20

# Top-level framework files
echo ""
echo "--- docs/guides/ directory ---"
rsync -avn --delete \
    "$SRC/docs/guides/" "$DEST/docs/guides/" 2>/dev/null | grep -v "^$" | head -20

echo ""
echo "--- Top-level files ---"
for file in WORKFLOW.md CLAUDE.md config.yaml docs/coding-standards.md capture-workflow-changes.sh; do
    if [ -f "$SRC/$file" ]; then
        if [ ! -f "$DEST/$file" ]; then
            echo "$file (new)"
        elif ! diff -q "$SRC/$file" "$DEST/$file" > /dev/null 2>&1; then
            echo "$file (modified)"
        fi
    fi
done

echo ""
read -p "Proceed with sync? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Do the sync
echo ""
echo "=== Syncing ==="

# Sync .claude directory
rsync -av --delete \
    --exclude='settings.local.json' \
    "$SRC/.claude/" "$DEST/.claude/"

# Sync docs/templates
mkdir -p "$DEST/docs/templates"
rsync -av --delete \
    "$SRC/docs/templates/" "$DEST/docs/templates/"

# Sync docs/guides
mkdir -p "$DEST/docs/guides"
rsync -av --delete \
    "$SRC/docs/guides/" "$DEST/docs/guides/"

# Copy top-level files
for file in WORKFLOW.md CLAUDE.md config.yaml docs/coding-standards.md capture-workflow-changes.sh; do
    if [ -f "$SRC/$file" ]; then
        cp "$SRC/$file" "$DEST/$file"
        echo "Copied: $file"
    fi
done

echo ""
echo "=== Sync Complete ==="
echo ""
echo "Next: cd $DEST && git status"
