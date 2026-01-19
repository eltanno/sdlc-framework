"""Create and manage pull requests.

This module handles:
- Committing staged changes
- Pushing to remote branches
- Creating pull requests with proper linking
- Merging pull requests

This is a port of .claude/scripts/ralph/pr-flow.sh
"""

from dataclasses import dataclass

from core import git, github
from core.github import PullRequestResult


class PrFlowError(Exception):
    """Error during PR flow operations."""

    pass


@dataclass
class PrFlowResult:
    """Result of running the PR flow.

    Attributes:
        ticket_id: The ticket ID being processed
        branch: Branch name used for the PR
        commit_sha: SHA of the commit (if any changes were committed)
        pr_number: PR number (if PR was created or existed)
        pr_url: URL of the PR
        merged: Whether the PR was merged
        already_done: Whether the ticket was already complete (PR already merged)
    """

    ticket_id: str
    branch: str
    commit_sha: str | None
    pr_number: int | None
    pr_url: str | None
    merged: bool
    already_done: bool


def stage_and_commit(ticket_id: str, commit_message: str) -> str | None:
    """Stage all changes and create a commit.

    Args:
        ticket_id: Ticket ID for the commit
        commit_message: Commit message (ticket ID will be prefixed if not present)

    Returns:
        Commit SHA if changes were committed, None if no changes

    Raises:
        PrFlowError: If commit fails
    """
    if not git.is_dirty():
        return None

    git.stage_all()

    # Ensure ticket ID is in message
    if ticket_id not in commit_message:
        full_message = f"[{ticket_id}] {commit_message}"
    else:
        full_message = commit_message

    # Add co-author
    full_message = f"{full_message}\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

    try:
        return git.commit(full_message)
    except git.GitError as e:
        raise PrFlowError(f"Failed to commit: {e}")


def push_branch(branch: str) -> None:
    """Push branch to remote with upstream tracking.

    Args:
        branch: Branch name to push

    Raises:
        PrFlowError: If push fails
    """
    try:
        git.push(remote="origin", branch=branch, set_upstream=True)
    except git.GitError as e:
        raise PrFlowError(f"Failed to push: {e}")


def create_pr(ticket_id: str, commit_message: str) -> PullRequestResult:
    """Create a pull request for the ticket.

    Args:
        ticket_id: Ticket ID (used in title)
        commit_message: Description for the PR

    Returns:
        PullRequestResult with URL and number

    Raises:
        PrFlowError: If PR creation fails
    """
    # Find GitHub issue for linking
    issue_number = github.find_issue_by_title(ticket_id)

    # Build PR title
    # Clean commit message of ticket prefix if present
    clean_message = commit_message.replace(f"[{ticket_id}]", "").strip()
    if clean_message.startswith(ticket_id):
        clean_message = clean_message[len(ticket_id):].strip()
        clean_message = clean_message.lstrip("-").strip()

    if not clean_message:
        clean_message = "Implementation complete"

    title = f"[{ticket_id}] {clean_message}"

    # Build PR body
    body_parts = [
        "## Summary",
        "",
        f"Implementation for {ticket_id}",
        "",
    ]

    if issue_number:
        body_parts.extend([f"Closes #{issue_number}", ""])

    body_parts.extend([
        "## Changes",
        "",
        "See commit history for details.",
        "",
        "## Validation",
        "",
        "All validation checks passed:",
        "- TypeScript typecheck",
        "- Lint",
        "- Tests",
        "- Build",
        "",
        "_Note: Branch may contain WIP commits from implementation attempts. "
        "Squash merge will consolidate._",
    ])

    body = "\n".join(body_parts)

    try:
        return github.create_pull_request(title=title, body=body)
    except github.GitHubError as e:
        raise PrFlowError(f"Failed to create PR: {e}")


def merge_pr(pr_number: int) -> None:
    """Merge a pull request using squash merge.

    Args:
        pr_number: PR number to merge

    Raises:
        PrFlowError: If merge fails
    """
    try:
        github.merge_pull_request(pr_number, strategy="squash")
    except github.GitHubError as e:
        raise PrFlowError(f"Failed to merge PR: {e}")


def checkout_detached_main(default_branch: str = "main") -> None:
    """Checkout detached HEAD at origin's default branch.

    This is worktree-safe since it doesn't checkout the branch itself,
    just a detached HEAD at that commit.

    Args:
        default_branch: Name of the default branch
    """
    try:
        git.fetch(remote="origin")
        # Use git checkout --detach to avoid worktree conflicts
        git._run_git_command(["checkout", "--detach", f"origin/{default_branch}"])
    except git.GitError:
        # Non-fatal - just log and continue
        pass


def find_existing_pr(branch: str) -> int | None:
    """Find an existing PR for a branch.

    Args:
        branch: Head branch name

    Returns:
        PR number if found, None otherwise
    """
    prs = github.list_pull_requests(head=branch)
    if prs:
        return prs[0]["number"]
    return None


def check_already_merged(ticket_id: str) -> int | None:
    """Check if a PR for this ticket was already merged.

    Args:
        ticket_id: Ticket ID to search for

    Returns:
        PR number if merged PR found, None otherwise
    """
    return github.find_merged_pr(ticket_id)


def pr_flow(
    ticket_id: str,
    commit_message: str,
    no_merge: bool = False,
    dry_run: bool = False,
) -> PrFlowResult:
    """Run the complete PR flow: commit, push, create PR, merge.

    This is the main entry point that orchestrates all PR operations.

    Args:
        ticket_id: Ticket ID being processed
        commit_message: Commit message / PR description
        no_merge: If True, don't merge the PR
        dry_run: If True, don't perform any real operations

    Returns:
        PrFlowResult with all operation details

    Raises:
        PrFlowError: If any operation fails
    """
    current_branch = git.get_current_branch()

    # Check if already merged (handles the case where we're on main and ticket is done)
    if current_branch in ("main", "master"):
        merged_pr = check_already_merged(ticket_id)
        if merged_pr:
            return PrFlowResult(
                ticket_id=ticket_id,
                branch=current_branch,
                commit_sha=None,
                pr_number=merged_pr,
                pr_url=None,
                merged=True,
                already_done=True,
            )

        # On main/master with no merged PR and no changes - error
        if not git.is_dirty():
            raise PrFlowError(
                f"On {current_branch} branch with no changes and no existing PR. "
                "Cannot create PR from default branch."
            )

    # Dry run mode - just return a mock result
    if dry_run:
        return PrFlowResult(
            ticket_id=ticket_id,
            branch=current_branch,
            commit_sha=None,
            pr_number=None,
            pr_url=None,
            merged=False,
            already_done=False,
        )

    # Stage and commit changes
    commit_sha = stage_and_commit(ticket_id, commit_message)

    # Push to remote
    push_branch(current_branch)

    # Check if PR already exists
    existing_pr = find_existing_pr(current_branch)

    if existing_pr:
        # Use existing PR
        pr_info = github.get_pull_request(existing_pr)
        pr_number = existing_pr
        pr_url = pr_info.get("url")
    else:
        # Create new PR
        pr_result = create_pr(ticket_id, commit_message)
        pr_number = pr_result.number
        pr_url = pr_result.url

    # Merge unless --no-merge
    merged = False
    if not no_merge and pr_number:
        merge_pr(pr_number)
        merged = True

        # Delete remote branch (if auto-delete isn't enabled on repo)
        try:
            github.delete_remote_branch(current_branch)
        except github.GitHubError:
            pass  # Non-fatal

        # Checkout detached at main
        checkout_detached_main()

    return PrFlowResult(
        ticket_id=ticket_id,
        branch=current_branch,
        commit_sha=commit_sha,
        pr_number=pr_number,
        pr_url=pr_url,
        merged=merged,
        already_done=False,
    )
