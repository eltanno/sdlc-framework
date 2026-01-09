#!/bin/bash
# SDLC Framework Setup Script
# Installs required dependencies for Linux/WSL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "SDLC Framework Setup"
echo "=================================="
echo ""

# Track what needs to be installed
MISSING_DEPS=()

# -----------------------------------------------------------------------------
# Check functions
# -----------------------------------------------------------------------------

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed ($(command -v $1))"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not installed"
        MISSING_DEPS+=("$1")
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Check required dependencies
# -----------------------------------------------------------------------------

echo "Checking required dependencies..."
echo ""

check_command git
check_command gh
check_command node
check_command bun
check_command jq

echo ""

# -----------------------------------------------------------------------------
# Check optional dependencies
# -----------------------------------------------------------------------------

echo "Checking optional dependencies..."
echo ""

if command -v ccusage &> /dev/null; then
    echo -e "${GREEN}✓${NC} ccusage is installed"
else
    echo -e "${YELLOW}○${NC} ccusage is not installed (optional - for token/cost display)"
fi

if command -v timeout &> /dev/null; then
    echo -e "${GREEN}✓${NC} timeout is installed"
else
    echo -e "${YELLOW}○${NC} timeout is not installed (optional - for cache timeout)"
fi

echo ""

# -----------------------------------------------------------------------------
# Install missing dependencies
# -----------------------------------------------------------------------------

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "=================================="
    echo "Installing missing dependencies..."
    echo "=================================="
    echo ""

    # Check if we can use apt
    if ! command -v apt &> /dev/null; then
        echo -e "${RED}Error: apt package manager not found.${NC}"
        echo "Please install the following manually: ${MISSING_DEPS[*]}"
        exit 1
    fi

    # Update package list
    echo "Updating package list..."
    sudo apt update

    for dep in "${MISSING_DEPS[@]}"; do
        case $dep in
            git)
                echo "Installing git..."
                sudo apt install -y git
                ;;
            gh)
                echo "Installing GitHub CLI..."
                # Add GitHub CLI repository
                type -p curl >/dev/null || sudo apt install curl -y
                curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
                sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
                sudo apt update
                sudo apt install -y gh
                ;;
            node)
                echo "Installing Node.js..."
                curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                sudo apt install -y nodejs
                ;;
            bun)
                echo "Installing Bun..."
                curl -fsSL https://bun.sh/install | bash
                # Add to current session
                export BUN_INSTALL="$HOME/.bun"
                export PATH="$BUN_INSTALL/bin:$PATH"
                ;;
            jq)
                echo "Installing jq..."
                sudo apt install -y jq
                ;;
        esac
    done

    echo ""
fi

# -----------------------------------------------------------------------------
# Install optional dependencies
# -----------------------------------------------------------------------------

echo "=================================="
echo "Optional: Install extras"
echo "=================================="
echo ""

read -p "Install ccusage for token/cost display in statusline? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing ccusage..."
    bun add -g ccusage
fi

echo ""

# -----------------------------------------------------------------------------
# Setup .env file
# -----------------------------------------------------------------------------

echo "=================================="
echo "Environment Setup"
echo "=================================="
echo ""

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created .env from .env.example"
        echo ""
        echo -e "${YELLOW}Important:${NC} Edit .env and add your API keys:"
        echo "  - ASANA_ACCESS_TOKEN"
        echo "  - ASANA_WORKSPACE_ID"
        echo "  - ASANA_PROJECT_ID"
    else
        echo -e "${YELLOW}Warning:${NC} .env.example not found"
    fi
else
    echo -e "${GREEN}✓${NC} .env already exists"
fi

echo ""

# -----------------------------------------------------------------------------
# Verify installation
# -----------------------------------------------------------------------------

echo "=================================="
echo "Verification"
echo "=================================="
echo ""

ALL_GOOD=true

for cmd in git gh node bun jq; do
    if command -v "$cmd" &> /dev/null; then
        VERSION=$($cmd --version 2>/dev/null | head -n1)
        echo -e "${GREEN}✓${NC} $cmd: $VERSION"
    else
        echo -e "${RED}✗${NC} $cmd: not found"
        ALL_GOOD=false
    fi
done

echo ""

if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}=================================="
    echo "Setup complete!"
    echo "==================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env with your API keys"
    echo "  2. Run 'gh auth login' to authenticate GitHub CLI"
    echo "  3. Configure Asana MCP in Claude Code settings"
    echo ""
    echo "See README.md for detailed configuration instructions."
else
    echo -e "${RED}=================================="
    echo "Setup incomplete"
    echo "==================================${NC}"
    echo ""
    echo "Some dependencies failed to install."
    echo "Please install them manually and re-run this script."
    exit 1
fi
