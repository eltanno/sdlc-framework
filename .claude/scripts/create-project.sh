#!/bin/bash
# SDLC Framework - Create New Project
# Copies the framework into a new project folder

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------

usage() {
    echo "Usage: $0 <project-path> [options]"
    echo ""
    echo "Creates a new project with the SDLC framework."
    echo ""
    echo "Arguments:"
    echo "  project-path    Path to create the new project (required)"
    echo ""
    echo "Options:"
    echo "  --no-git        Don't initialize git repository"
    echo "  --pm <tool>     Set PM tool (asana|trello|github|linear|none)"
    echo "  --repo <type>   Set repo type (github|gitlab)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 ~/projects/my-new-app"
    echo "  $0 ./my-app --pm trello --repo gitlab"
    echo "  $0 /path/to/project --no-git"
}

# -----------------------------------------------------------------------------
# Parse arguments
# -----------------------------------------------------------------------------

PROJECT_PATH=""
INIT_GIT=true
PM_TOOL=""
REPO_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        --no-git)
            INIT_GIT=false
            shift
            ;;
        --pm)
            PM_TOOL="$2"
            shift 2
            ;;
        --repo)
            REPO_TYPE="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            exit 1
            ;;
        *)
            if [ -z "$PROJECT_PATH" ]; then
                PROJECT_PATH="$1"
            else
                echo -e "${RED}Error: Multiple paths specified${NC}"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$PROJECT_PATH" ]; then
    echo -e "${RED}Error: Project path required${NC}"
    echo ""
    usage
    exit 1
fi

# -----------------------------------------------------------------------------
# Validate
# -----------------------------------------------------------------------------

# Expand path
PROJECT_PATH="$(realpath -m "$PROJECT_PATH")"
PROJECT_NAME="$(basename "$PROJECT_PATH")"

if [ -e "$PROJECT_PATH" ]; then
    echo -e "${RED}Error: $PROJECT_PATH already exists${NC}"
    exit 1
fi

echo "=================================="
echo "SDLC Framework - New Project"
echo "=================================="
echo ""
echo "Project: $PROJECT_NAME"
echo "Path: $PROJECT_PATH"
echo ""

# -----------------------------------------------------------------------------
# Create project
# -----------------------------------------------------------------------------

echo -e "${BLUE}→${NC} Creating project directory..."
mkdir -p "$PROJECT_PATH"

echo -e "${BLUE}→${NC} Copying framework files..."

# Copy framework files (exclude git, node_modules, project-specific content)
# Note: --filter=':- .gitignore' respects .gitignore patterns
rsync -a \
    --filter=':- .gitignore' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='workflow-state.json' \
    --exclude='.logs' \
    --exclude='.mcp.json' \
    --exclude='.claude/settings.local.json' \
    --exclude='docs/discovery.md' \
    --exclude='docs/discovery/*' \
    --exclude='docs/prds/*' \
    --exclude='docs/plans/*.md' \
    --exclude='docs/research/*' \
    --exclude='docs/rca/*' \
    --exclude='docs/execution-reports/*' \
    --exclude='docs/system-reviews/*' \
    "$PROJECT_ROOT/" "$PROJECT_PATH/"

echo -e "${GREEN}✓${NC} Framework files copied"

# -----------------------------------------------------------------------------
# Configure
# -----------------------------------------------------------------------------

cd "$PROJECT_PATH"

# Update PM tool if specified
if [ -n "$PM_TOOL" ]; then
    echo -e "${BLUE}→${NC} Setting PM tool to: $PM_TOOL"
    sed -i "s/tool: asana/tool: $PM_TOOL/" config.yaml
fi

# Update repo type if specified
if [ -n "$REPO_TYPE" ]; then
    echo -e "${BLUE}→${NC} Setting repo type to: $REPO_TYPE"
    sed -i "s/type: github/type: $REPO_TYPE/" config.yaml
fi

# Create .env from example
if [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Created .env from template"
fi

# -----------------------------------------------------------------------------
# Initialize git
# -----------------------------------------------------------------------------

if [ "$INIT_GIT" = true ]; then
    echo -e "${BLUE}→${NC} Initializing git repository..."
    git init -q
    git add .
    git commit -q -m "Initial commit: SDLC Framework

Co-Authored-By: Claude <noreply@anthropic.com>"
    echo -e "${GREEN}✓${NC} Git repository initialized"
fi

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

echo ""
echo -e "${GREEN}=================================="
echo "Project created successfully!"
echo "==================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. cd $PROJECT_PATH"
echo ""
echo "  2. Edit config.yaml:"
echo "     - pm.tool: Your PM tool (asana, trello, github, linear, none)"
echo "     - repo.type: Your git provider (github, gitlab)"
echo "     - pr.auto_merge: Set to true for automated merging"
echo ""
echo "  3. Edit .env with your API keys"
echo ""
echo "  4. Authenticate your git provider:"
echo "     - GitHub: gh auth login"
echo "     - GitLab: glab auth login"
echo ""
echo "  5. Run ./claude-setup.sh to install dependencies (optional)"
echo ""
echo "  6. Start with: /discover"
echo ""
