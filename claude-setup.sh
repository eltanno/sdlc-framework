#!/bin/bash
# SDLC Framework Setup Script
# Installs all required dependencies for Linux/WSL
# Fully automated - no user input required

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=================================="
echo "SDLC Framework Setup"
echo "=================================="
echo ""

# -----------------------------------------------------------------------------
# Check functions
# -----------------------------------------------------------------------------

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

install_if_missing() {
    local cmd=$1
    local name=$2

    if check_command "$cmd"; then
        echo -e "${GREEN}✓${NC} $name already installed"
        return 0
    else
        echo -e "${BLUE}→${NC} Installing $name..."
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Check for apt
# -----------------------------------------------------------------------------

if ! command -v apt &> /dev/null; then
    echo -e "${RED}Error: apt package manager not found.${NC}"
    echo "This script requires a Debian/Ubuntu-based system."
    exit 1
fi

# -----------------------------------------------------------------------------
# Install dependencies
# -----------------------------------------------------------------------------

echo "Installing dependencies..."
echo ""

# Update apt once at the start
sudo apt update -qq

# Git
if ! install_if_missing git "git"; then
    sudo apt install -y git
    echo -e "${GREEN}✓${NC} git installed"
fi

# GitHub CLI
if ! install_if_missing gh "GitHub CLI"; then
    type -p curl >/dev/null || sudo apt install -y curl
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update -qq
    sudo apt install -y gh
    echo -e "${GREEN}✓${NC} GitHub CLI installed"
fi

# GitLab CLI
if ! install_if_missing glab "GitLab CLI"; then
    type -p curl >/dev/null || sudo apt install -y curl
    curl -fsSL https://raw.githubusercontent.com/upciti/wakemeops/main/assets/install_repository | sudo bash
    sudo apt install -y glab
    echo -e "${GREEN}✓${NC} GitLab CLI installed"
fi

# Node.js
if ! install_if_missing node "Node.js"; then
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt install -y nodejs
    echo -e "${GREEN}✓${NC} Node.js installed"
fi

# jq
if ! install_if_missing jq "jq"; then
    sudo apt install -y jq
    echo -e "${GREEN}✓${NC} jq installed"
fi

# Bun
if ! install_if_missing bun "Bun"; then
    npm install -g bun
    echo -e "${GREEN}✓${NC} Bun installed"
fi

# ccusage (for token/cost display)
if ! install_if_missing ccusage "ccusage"; then
    bun add -g ccusage
    echo -e "${GREEN}✓${NC} ccusage installed"
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

for cmd in git gh glab node bun jq ccusage; do
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
    echo "  1. Edit .env with your API keys (ASANA_ACCESS_TOKEN, etc.)"
    echo "  2. Authenticate your git provider:"
    echo "     - GitHub: gh auth login"
    echo "     - GitLab: glab auth login"
    echo ""
    echo "Asana MCP is pre-configured in .mcp.json"
    echo ""
    echo "See README.md for detailed configuration instructions."
else
    echo -e "${RED}=================================="
    echo "Setup incomplete"
    echo "==================================${NC}"
    echo ""
    echo "Some dependencies failed to install."
    echo "Please check the errors above and try again."
    exit 1
fi
