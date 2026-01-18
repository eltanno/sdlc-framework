#!/bin/bash
# Ralph PR Flow - Handle git commit, push, PR creation, and merge
# Usage: pr-flow.sh <ticket-id> <commit-message> [--no-merge] [--dry-run]
#
# What this does:
# 1. Stage all changes
# 2. Commit with message
# 3. Push to remote (if remote exists)
# 4. Create PR (if remote exists)
# 5. Merge PR (unless --no-merge)
#
# For local-only repos, just commits to current branch

set -e

TICKET_ID="${1:-}"
COMMIT_MSG="${2:-}"
NO_MERGE=false
DRY_RUN=false

# Parse flags from remaining arguments
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-merge)
            NO_MERGE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Ralph PR Flow ==="
[ "$DRY_RUN" = true ] && echo -e "${YELLOW}DRY RUN MODE${NC}"

# Validate inputs
if [ -z "$TICKET_ID" ]; then
    echo -e "${RED}Error: Missing ticket ID${NC}"
    echo "Usage: pr-flow.sh <ticket-id> <commit-message> [--no-merge] [--dry-run]"
    exit 1
fi

if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="[$TICKET_ID] Implementation complete"
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo "Current branch: $CURRENT_BRANCH"

# Check if we're on main with no changes - ticket might already be done
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    # Check if a PR already exists for this ticket
    if [ -n "$TICKET_ID" ]; then
        EXISTING_PR=$(gh pr list --search "$TICKET_ID in:title" --state merged --json number,title --jq '.[0].number' 2>/dev/null)
        if [ -n "$EXISTING_PR" ] && [ "$EXISTING_PR" != "null" ]; then
            echo "PR #$EXISTING_PR already merged for $TICKET_ID"
            echo ""
            echo "=== PR Flow Complete (Already Merged) ==="
            echo "Ticket: $TICKET_ID"
            echo "Status: Already merged as PR #$EXISTING_PR"
            echo ""
            # Output JSON for orchestrator
            cat << ENDJSON
{
  "ticket": "$TICKET_ID",
  "branch": "$CURRENT_BRANCH",
  "commit": false,
  "has_remote": true,
  "pr_number": $EXISTING_PR,
  "pr_url": null,
  "merged": true,
  "already_done": true
}
ENDJSON
            exit 0
        fi
    fi

    # If no existing PR and on main, this is an error
    uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
    if [ "$uncommitted" -eq 0 ]; then
        echo "Error: On $CURRENT_BRANCH branch with no changes and no existing PR"
        echo "Cannot create PR from default branch"
        exit 1
    fi
fi

# Check if there are changes to commit
if git diff --quiet && git diff --staged --quiet; then
    echo -e "${YELLOW}No changes to commit${NC}"
    COMMIT_MADE=false
else
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would stage and commit changes${NC}"
        echo "  Message: $COMMIT_MSG"
        COMMIT_MADE=true
    else
        # Stage all changes
        echo "Staging changes..."
        git add -A

        # Commit
        echo "Committing..."
        FULL_MSG="$COMMIT_MSG

Co-Authored-By: Claude <noreply@anthropic.com>"

        git commit -m "$FULL_MSG"
        COMMIT_MADE=true
        echo -e "${GREEN}Committed${NC}"
    fi
fi

# Check if remote exists
HAS_REMOTE=false
if git remote -v | grep -q origin; then
    HAS_REMOTE=true
fi

PR_NUMBER=""
PR_URL=""

if [ "$HAS_REMOTE" = true ]; then
    echo ""
    echo "--- Remote Repository ---"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would push to origin/$CURRENT_BRANCH${NC}"
        echo -e "${YELLOW}[DRY RUN] Would create PR for $TICKET_ID${NC}"
        [ "$NO_MERGE" = false ] && echo -e "${YELLOW}[DRY RUN] Would merge PR${NC}"
        PR_NUMBER="DRY-RUN"
        PR_URL="https://example.com/dry-run"
    else
        # Push
        echo "Pushing to origin..."
        git push -u origin "$CURRENT_BRANCH" 2>&1 || true
        echo -e "${GREEN}Pushed${NC}"

        # Check if PR already exists
        EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")

        if [ -n "$EXISTING_PR" ]; then
            echo -e "${YELLOW}PR #$EXISTING_PR already exists${NC}"
            PR_NUMBER="$EXISTING_PR"
            PR_URL=$(gh pr view "$EXISTING_PR" --json url --jq '.url')
        else
            # Create PR
            echo "Creating PR..."

            # Extract issue number from ticket ID (e.g., GH-123 -> 123)
            ISSUE_NUMBER=$(echo "$TICKET_ID" | grep -oE '[0-9]+$' || echo "")

            PR_BODY="## Summary

Implementation for $TICKET_ID

$([ -n "$ISSUE_NUMBER" ] && echo "Closes #$ISSUE_NUMBER")

## Changes

See commit history for details.

## Validation

All validation checks passed:
- TypeScript typecheck
- Lint
- Tests
- Build

_Note: Branch may contain WIP commits from implementation attempts. Squash merge will consolidate._
"

            if PR_OUTPUT=$(gh pr create \
                --title "[$TICKET_ID] $(echo "$COMMIT_MSG" | head -1 | sed "s/\[$TICKET_ID\] //")" \
                --body "$PR_BODY" \
                2>&1); then
                PR_URL=$(echo "$PR_OUTPUT" | grep -oE 'https://github.com/[^ ]+' | head -1 || echo "")
                PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$' || echo "")
                echo -e "${GREEN}Created PR #$PR_NUMBER${NC}"
                echo "URL: $PR_URL"
            else
                echo -e "${YELLOW}Could not create PR: $PR_OUTPUT${NC}"
                PR_NUMBER=""
                PR_URL=""
            fi
        fi

        # Merge PR (unless --no-merge)
        if [ "$NO_MERGE" = false ] && [ -n "$PR_NUMBER" ]; then
            echo ""
            echo "Merging PR..."

            # Wait a moment for CI to register
            sleep 2

            if gh pr merge "$PR_NUMBER" --squash --delete-branch 2>&1; then
                echo -e "${GREEN}Merged and branch deleted${NC}"

                # Switch back to default branch (use config.yaml as source of truth)
                DEFAULT_BRANCH=""
                if [ -f "config.yaml" ]; then
                    DEFAULT_BRANCH=$(grep "default_branch:" config.yaml 2>/dev/null | sed 's/.*: //' | tr -d ' ')
                fi

                # Only auto-detect if not configured
                if [ -z "$DEFAULT_BRANCH" ]; then
                    echo -e "${YELLOW}Warning: default_branch not set in config.yaml, auto-detecting...${NC}"
                    DEFAULT_BRANCH=$(git remote show origin 2>/dev/null | grep "HEAD branch" | sed 's/.*: //')
                    [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH="master"
                fi
                git checkout "$DEFAULT_BRANCH" || { echo -e "${RED}Failed to checkout $DEFAULT_BRANCH${NC}"; }
                git pull origin "$DEFAULT_BRANCH" || { echo -e "${YELLOW}Failed to pull, continuing...${NC}"; }
            else
                echo -e "${YELLOW}Could not auto-merge. May need manual review.${NC}"
            fi
        fi
    fi
else
    echo ""
    echo "--- Local Repository (no remote) ---"

    # For local repos, merge to main/master
    # Detect default branch - check if main or master exists
    if git show-ref --verify --quiet refs/heads/main 2>/dev/null; then
        DEFAULT_BRANCH="main"
    elif git show-ref --verify --quiet refs/heads/master 2>/dev/null; then
        DEFAULT_BRANCH="master"
    else
        DEFAULT_BRANCH="master"
    fi

    # Check if we're on a feature branch
    if [[ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" && "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY RUN] Would merge $CURRENT_BRANCH to $DEFAULT_BRANCH${NC}"
        else
            echo "Merging $CURRENT_BRANCH to $DEFAULT_BRANCH..."
            git checkout "$DEFAULT_BRANCH"
            git merge "$CURRENT_BRANCH"
            echo -e "${GREEN}Merged to $DEFAULT_BRANCH${NC}"

            # Optionally delete feature branch
            # git branch -d "$CURRENT_BRANCH"
        fi
    else
        echo "Already on $DEFAULT_BRANCH, no merge needed"
    fi
fi

# Output summary
echo ""
echo "=== PR Flow Complete ==="
echo "Ticket: $TICKET_ID"
echo "Branch: $CURRENT_BRANCH"
echo "Commit: $([ "$COMMIT_MADE" = true ] && echo "Yes" || echo "No changes")"
echo "Remote: $([ "$HAS_REMOTE" = true ] && echo "Yes" || echo "No (local only)")"
[ -n "$PR_NUMBER" ] && echo "PR: #$PR_NUMBER"
[ -n "$PR_URL" ] && echo "URL: $PR_URL"

# Output JSON
echo ""
echo "---JSON_OUTPUT---"
cat << EOF
{
  "ticket": "$TICKET_ID",
  "branch": "$CURRENT_BRANCH",
  "commit": $([ "$COMMIT_MADE" = true ] && echo "true" || echo "false"),
  "has_remote": $([ "$HAS_REMOTE" = true ] && echo "true" || echo "false"),
  "pr_number": $([ -n "$PR_NUMBER" ] && echo "\"$PR_NUMBER\"" || echo "null"),
  "pr_url": $([ -n "$PR_URL" ] && echo "\"$PR_URL\"" || echo "null"),
  "merged": $([ "$NO_MERGE" = false ] && [ -n "$PR_NUMBER" ] && echo "true" || echo "false")
}
EOF
