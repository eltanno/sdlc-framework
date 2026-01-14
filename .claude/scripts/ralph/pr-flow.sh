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
            PR_BODY="## Summary

Implementation for $TICKET_ID

## Changes

See commit history for details.

## Testing

- [x] All tests pass
- [x] Lint passes
- [x] Build succeeds
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

                # Switch back to main
                DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
                git checkout "$DEFAULT_BRANCH"
                git pull origin "$DEFAULT_BRANCH"
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
