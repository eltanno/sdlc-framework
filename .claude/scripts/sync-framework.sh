#!/bin/bash
# SDLC Framework - Sync Framework to Existing Project
# Updates an existing project with the latest framework files

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory and framework root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------

usage() {
    echo "Usage: $0 <target-path> [options]"
    echo ""
    echo "Syncs the SDLC framework to an existing project."
    echo ""
    echo "Arguments:"
    echo "  target-path    Path to the existing project (required)"
    echo ""
    echo "Options:"
    echo "  --dry-run      Show what would be synced without making changes"
    echo "  --yes          Auto-confirm .claude/ directory sync"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Behavior:"
    echo "  - .claude/ directory: Synced automatically (framework internals)"
    echo "  - docs/templates/, docs/guides/: Synced automatically"
    echo "  - Other files (CLAUDE.md, config.yaml, etc.): Prompted per-file"
    echo "    - If you approve, existing file is backed up to {file}.old"
    echo ""
    echo "Examples:"
    echo "  $0 ~/projects/my-app"
    echo "  $0 ../other-project --dry-run"
}

# -----------------------------------------------------------------------------
# Parse arguments
# -----------------------------------------------------------------------------

TARGET_PATH=""
DRY_RUN=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --yes)
            AUTO_YES=true
            shift
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            exit 1
            ;;
        *)
            if [ -z "$TARGET_PATH" ]; then
                TARGET_PATH="$1"
            else
                echo -e "${RED}Error: Multiple paths specified${NC}"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$TARGET_PATH" ]; then
    echo -e "${RED}Error: Target path required${NC}"
    echo ""
    usage
    exit 1
fi

# -----------------------------------------------------------------------------
# Validate
# -----------------------------------------------------------------------------

# Expand path
TARGET_PATH="$(realpath -m "$TARGET_PATH")"

if [ ! -d "$TARGET_PATH" ]; then
    echo -e "${RED}Error: Target directory does not exist: $TARGET_PATH${NC}"
    echo ""
    echo "Use /new-project to create a new project instead."
    exit 1
fi

if [ "$TARGET_PATH" = "$FRAMEWORK_ROOT" ]; then
    echo -e "${RED}Error: Cannot sync framework to itself${NC}"
    exit 1
fi

echo "=================================="
echo "SDLC Framework - Sync"
echo "=================================="
echo ""
echo "Framework: $FRAMEWORK_ROOT"
echo "Target:    $TARGET_PATH"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Mode:      DRY RUN${NC}"
fi
echo ""

# -----------------------------------------------------------------------------
# Helper: Check if file is gitignored
# -----------------------------------------------------------------------------

is_gitignored() {
    local file_path="$1"
    cd "$FRAMEWORK_ROOT"
    git check-ignore -q "$file_path" 2>/dev/null
    local result=$?
    cd - > /dev/null
    return $result
}

# -----------------------------------------------------------------------------
# Helper: Sync file with prompt
# -----------------------------------------------------------------------------

sync_external_file() {
    local rel_path="$1"
    local src="$FRAMEWORK_ROOT/$rel_path"
    local dest="$TARGET_PATH/$rel_path"

    # Skip gitignored files
    if is_gitignored "$rel_path"; then
        echo -e "${BLUE}SKIP${NC} $rel_path (gitignored)"
        return 0
    fi

    # Source doesn't exist
    if [ ! -f "$src" ]; then
        return 0
    fi

    # Destination doesn't exist - just copy
    if [ ! -f "$dest" ]; then
        echo -e "${GREEN}NEW${NC} $rel_path"
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$(dirname "$dest")"
            cp "$src" "$dest"
        fi
        return 0
    fi

    # Both exist - check diff
    if diff -q "$src" "$dest" > /dev/null 2>&1; then
        echo -e "${CYAN}SAME${NC} $rel_path"
        return 0
    fi

    # Files differ - prompt user
    echo ""
    echo -e "${YELLOW}DIFFERS${NC} $rel_path"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo "  Would prompt for update (dry run)"
        return 0
    fi

    # Show diff summary
    echo "Changes:"
    diff --color=always -u "$dest" "$src" | head -30 || true
    DIFF_LINES=$(diff "$dest" "$src" | wc -l)
    if [ "$DIFF_LINES" -gt 30 ]; then
        echo "  ... ($DIFF_LINES total diff lines, showing first 30)"
    fi
    echo ""

    read -p "Update $rel_path? (existing will be saved as ${rel_path}.old) [y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mv "$dest" "${dest}.old"
        cp "$src" "$dest"
        echo -e "${GREEN}✓${NC} Updated (backup: ${rel_path}.old)"
    else
        echo -e "${BLUE}→${NC} Skipped"
    fi
}

# -----------------------------------------------------------------------------
# Sync .claude/ directory (framework internals - no prompts)
# -----------------------------------------------------------------------------

echo "=== Syncing .claude/ directory ==="
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "Would sync:"
    rsync -avn --delete \
        --filter=':- .gitignore' \
        --exclude='settings.local.json' \
        --exclude='ralph/*.json' \
        "$FRAMEWORK_ROOT/.claude/" "$TARGET_PATH/.claude/" 2>/dev/null | grep -E "^[^.]" | head -30 || true
    echo ""
else
    rsync -av --delete \
        --filter=':- .gitignore' \
        --exclude='settings.local.json' \
        --exclude='ralph/*.json' \
        "$FRAMEWORK_ROOT/.claude/" "$TARGET_PATH/.claude/"
    echo -e "${GREEN}✓${NC} .claude/ synced"
fi

# -----------------------------------------------------------------------------
# Sync docs/templates/ and docs/guides/
# -----------------------------------------------------------------------------

echo ""
echo "=== Syncing docs/templates/ ==="
echo ""

if [ "$DRY_RUN" = true ]; then
    rsync -avn --delete \
        --filter=':- .gitignore' \
        "$FRAMEWORK_ROOT/docs/templates/" "$TARGET_PATH/docs/templates/" 2>/dev/null | grep -E "^[^.]" | head -20 || true
else
    mkdir -p "$TARGET_PATH/docs/templates"
    rsync -av --delete \
        --filter=':- .gitignore' \
        "$FRAMEWORK_ROOT/docs/templates/" "$TARGET_PATH/docs/templates/"
    echo -e "${GREEN}✓${NC} docs/templates/ synced"
fi

echo ""
echo "=== Syncing docs/guides/ ==="
echo ""

if [ "$DRY_RUN" = true ]; then
    rsync -avn --delete \
        --filter=':- .gitignore' \
        "$FRAMEWORK_ROOT/docs/guides/" "$TARGET_PATH/docs/guides/" 2>/dev/null | grep -E "^[^.]" | head -20 || true
else
    mkdir -p "$TARGET_PATH/docs/guides"
    rsync -av --delete \
        --filter=':- .gitignore' \
        "$FRAMEWORK_ROOT/docs/guides/" "$TARGET_PATH/docs/guides/"
    echo -e "${GREEN}✓${NC} docs/guides/ synced"
fi

# -----------------------------------------------------------------------------
# Sync external files (with prompts)
# -----------------------------------------------------------------------------

echo ""
echo "=== Checking project root files ==="
echo ""

EXTERNAL_FILES=(
    "docs/WORKFLOW.md"
    "CLAUDE.md"
    "config.yaml"
    "docs/coding-standards.md"
    ".gitignore"
    ".mcp.json"
)

for file in "${EXTERNAL_FILES[@]}"; do
    sync_external_file "$file"
done

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

echo ""
echo "=================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Dry run complete${NC}"
    echo "Run without --dry-run to apply changes"
else
    echo -e "${GREEN}Sync complete!${NC}"

    # Check for .old files
    OLD_FILES=$(find "$TARGET_PATH" -maxdepth 3 -name "*.old" 2>/dev/null | head -10)
    if [ -n "$OLD_FILES" ]; then
        echo ""
        echo -e "${YELLOW}Backup files created:${NC}"
        echo "$OLD_FILES"
        echo ""
        echo "Review these files to merge any customizations you want to keep,"
        echo "then delete the .old files manually when done."
    fi
fi
echo "=================================="
