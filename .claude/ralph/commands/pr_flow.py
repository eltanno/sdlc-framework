"""Create and manage pull requests / merge requests.

This module handles:
- Committing staged changes
- Pushing to remote branches
- Creating pull requests (GitHub) or merge requests (GitLab) with proper linking
- Merging pull requests / merge requests

Supports both GitHub and GitLab based on repo.type configuration.

This is a port of .claude/scripts/ralph/pr-flow.sh
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from core import git
from core.config import get_repo_tool_type

logger = logging.getLogger(__name__)


def get_repo_module(config_path: str | Path = Path("config.yaml")) -> ModuleType:
    """Get the configured repository tool module.

    Reads repo.type from config and returns the appropriate module
    (github or gitlab). Defaults to github if not configured.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        The github or gitlab module based on configuration.

    Raises:
        ConfigError: If repo.type has an invalid value.
    """
    tool = get_repo_tool_type(config_path)

    if tool == "gitlab":
        from core import gitlab
        return gitlab
    else:
        from core import github
        return github


class PrFlowError(Exception):
    """Error during PR flow operations."""

    pass


class MergeError(PrFlowError):
    """Error specifically during merge operations."""

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


def push_branch(branch: str, refspec: bool = False, force: bool = False) -> None:
    """Push branch to remote with upstream tracking.

    Args:
        branch: Branch name to push
        refspec: If True, push using HEAD:refs/heads/<branch> refspec.
                 Required when on detached HEAD (e.g. in worktrees).
        force: If True, use --force-with-lease for safe force-push.
               Needed after rebase when branch was already pushed.

    Raises:
        PrFlowError: If push fails
    """
    try:
        if refspec:
            # Push detached HEAD to a named remote branch via refspec
            args = ["push"]
            if force:
                args.append("--force-with-lease")
            args.extend(["-u", "origin", f"HEAD:refs/heads/{branch}"])
            git._run_git_command(args)
        else:
            if force:
                # Force-push with lease for safety
                args = ["push", "--force-with-lease", "-u", "origin", branch]
                git._run_git_command(args)
            else:
                git.push(remote="origin", branch=branch, set_upstream=True)
    except git.GitError as e:
        raise PrFlowError(f"Failed to push: {e}")


def create_mr(ticket_id: str, commit_message: str, head: str | None = None, default_branch: str = ""):
    """Create a pull request (GitHub) or merge request (GitLab) for the ticket.

    Args:
        ticket_id: Ticket ID (used in title)
        commit_message: Description for the PR/MR
        head: Source branch name. Required when on detached HEAD
              (e.g. in git worktrees) so the CLI can determine the source branch.
        default_branch: Target branch for the PR/MR. If empty, uses repo default.

    Returns:
        PullRequestResult (GitHub) or MergeRequestResult (GitLab) with URL and number

    Raises:
        PrFlowError: If PR/MR creation fails
    """
    repo = get_repo_module()

    # Try to find linked issue (GitHub only - GitLab tickets are in Asana/Trello)
    issue_number = None
    if hasattr(repo, "find_issue_by_title") and repo.find_issue_by_title is not None:
        issue_number = repo.find_issue_by_title(ticket_id)

    # Build PR/MR title
    # Clean commit message of ticket prefix if present
    clean_message = commit_message.replace(f"[{ticket_id}]", "").strip()
    if clean_message.startswith(ticket_id):
        clean_message = clean_message[len(ticket_id):].strip()
        clean_message = clean_message.lstrip("-").strip()

    if not clean_message:
        clean_message = "Implementation complete"

    title = f"[{ticket_id}] {clean_message}"

    # Build PR/MR body
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
        # Both modules have create_pull_request/create_merge_request with same signature
        base = default_branch or None
        if hasattr(repo, "create_merge_request"):
            return repo.create_merge_request(title=title, body=body, head=head, base=base)
        else:
            return repo.create_pull_request(title=title, body=body, head=head, base=base)
    except Exception as e:
        raise PrFlowError(f"Failed to create PR/MR: {e}")


def merge_mr(pr_number: int) -> None:
    """Merge a pull request (GitHub) or merge request (GitLab) using squash merge.

    Args:
        pr_number: PR/MR number to merge

    Raises:
        PrFlowError: If merge fails
    """
    repo = get_repo_module()

    try:
        # Both modules have merge_pull_request/merge_merge_request with same signature
        if hasattr(repo, "merge_merge_request"):
            repo.merge_merge_request(pr_number, strategy="squash")
        else:
            repo.merge_pull_request(pr_number, strategy="squash")
    except Exception as e:
        raise MergeError(f"Failed to merge PR/MR: {e}")


def checkout_detached_default(default_branch: str) -> None:
    """Checkout detached HEAD at origin's default branch.

    This is worktree-safe since it doesn't checkout the branch itself,
    just a detached HEAD at that commit.

    Args:
        default_branch: Name of the default branch (required, no fallback)
    """
    try:
        git.fetch(remote="origin")
        # Use git checkout --detach to avoid worktree conflicts
        git._run_git_command(["checkout", "--detach", f"origin/{default_branch}"])
    except git.GitError:
        # Non-fatal - just log and continue
        pass


def sync_with_default(default_branch: str) -> None:
    """Sync current branch with latest default branch using rebase.

    Uses rebase instead of merge to produce a clean linear history
    and handle simple conflicts (non-overlapping changes) automatically.
    Fetches from origin first to get the latest remote state.

    Args:
        default_branch: Name of the default branch to sync with (required, no fallback)

    Raises:
        PrFlowError: If fetch or rebase fails (including true conflicts)
    """
    try:
        git.fetch(remote="origin")
    except git.GitError as e:
        raise PrFlowError(f"Failed to fetch origin: {e}")

    # Check if rebase is needed (is origin/default_branch already an ancestor of HEAD?)
    result = git._run_git_command(
        ["merge-base", "--is-ancestor", f"origin/{default_branch}", "HEAD"],
        check=False,
    )
    if result.returncode == 0:
        # Already up to date, no rebase needed
        return

    # Attempt rebase
    rebase_result = git._run_git_command(
        ["rebase", f"origin/{default_branch}"],
        check=False,
    )

    if rebase_result.returncode == 0:
        return  # Rebase succeeded

    # Rebase failed -- abort and raise
    git._run_git_command(["rebase", "--abort"], check=False)
    raise PrFlowError(
        f"Failed to rebase onto {default_branch}. "
        f"Merge conflicts need manual resolution: {rebase_result.stderr}"
    )


def find_existing_pr(branch: str) -> int | None:
    """Find an existing PR/MR for a branch.

    Args:
        branch: Head branch name

    Returns:
        PR/MR number if found, None otherwise
    """
    repo = get_repo_module()

    # Both modules have list_pull_requests/list_merge_requests with same signature
    if hasattr(repo, "list_merge_requests"):
        mrs = repo.list_merge_requests(head=branch)
        if mrs:
            # GitLab uses 'iid', GitHub uses 'number'
            return mrs[0].get("iid") or mrs[0].get("number")
    else:
        prs = repo.list_pull_requests(head=branch)
        if prs:
            return prs[0].get("number") or prs[0].get("iid")
    return None


def check_already_merged(ticket_id: str) -> int | None:
    """Check if a PR/MR for this ticket was already merged.

    Args:
        ticket_id: Ticket ID to search for

    Returns:
        PR/MR number if merged PR/MR found, None otherwise
    """
    repo = get_repo_module()

    # Both modules have find_merged_pr/find_merged_mr with same signature
    if hasattr(repo, "find_merged_mr"):
        return repo.find_merged_mr(ticket_id)
    else:
        return repo.find_merged_pr(ticket_id)


def pr_flow(
    ticket_id: str,
    commit_message: str,
    no_merge: bool = False,
    dry_run: bool = False,
    default_branch: str = "",
) -> PrFlowResult:
    """Run the complete PR flow: commit, push, create PR, merge.

    This is the main entry point that orchestrates all PR operations.

    Args:
        ticket_id: Ticket ID being processed
        commit_message: Commit message / PR description
        no_merge: If True, don't merge the PR
        dry_run: If True, don't perform any real operations
        default_branch: Name of the default branch (required — callers must pass explicitly)

    Returns:
        PrFlowResult with all operation details

    Raises:
        PrFlowError: If any operation fails or default_branch is not provided
    """
    if not default_branch:
        raise PrFlowError(
            "default_branch must be explicitly provided — "
            "read git.default_branch from config.yaml"
        )

    current_branch = git.get_current_branch()

    # Handle detached HEAD (common in worktrees after checkout_detached_default).
    # Set current_branch to a target name for PR operations. We stay on
    # detached HEAD and push via refspec later — avoids git worktree
    # constraints that prevent checking out a branch used elsewhere.
    _detached = current_branch == "HEAD"
    if _detached:
        current_branch = f"feature/{ticket_id}-implementation"

    # Check if already merged (handles the case where we're on default branch and ticket is done)
    if current_branch == default_branch:
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

    # Sync and push with retry (handles race when another loop merges between our sync and push)
    MAX_SYNC_RETRIES = 3
    for sync_attempt in range(1, MAX_SYNC_RETRIES + 1):
        try:
            sync_with_default(default_branch=default_branch)
            # After rebase on retry, branch may have been pushed already — force-push
            push_branch(
                current_branch,
                refspec=_detached,
                force=(sync_attempt > 1),
            )
            break  # Success
        except PrFlowError:
            if sync_attempt == MAX_SYNC_RETRIES:
                raise  # Final attempt failed
            # Another loop may have merged -- retry with fresh fetch
            logger.warning(
                "Sync attempt %d/%d failed for %s. Retrying after fresh fetch...",
                sync_attempt,
                MAX_SYNC_RETRIES,
                ticket_id,
            )

    # Check if PR already exists
    existing_pr = find_existing_pr(current_branch)

    repo = get_repo_module()

    if existing_pr:
        # Use existing PR/MR
        if hasattr(repo, "get_merge_request"):
            pr_info = repo.get_merge_request(existing_pr)
            pr_url = pr_info.get("web_url") or pr_info.get("url")
        else:
            pr_info = repo.get_pull_request(existing_pr)
            pr_url = pr_info.get("url") or pr_info.get("web_url")
        pr_number = existing_pr
    else:
        # Create new PR/MR (pass head when on detached HEAD so CLI knows the source branch)
        pr_result = create_mr(
            ticket_id, commit_message,
            head=current_branch if _detached else None,
            default_branch=default_branch,
        )
        pr_number = pr_result.number
        pr_url = pr_result.url

    # Merge unless --no-merge
    merged = False
    if not no_merge and pr_number:
        try:
            merge_mr(pr_number)
            merged = True
        except MergeError:
            # PR may not be mergeable because default branch advanced
            # Try updating the PR branch and retrying once
            try:
                sync_with_default(default_branch=default_branch)
                push_branch(current_branch, refspec=_detached, force=True)
                merge_mr(pr_number)
                merged = True
            except (PrFlowError, MergeError):
                raise MergeError(
                    f"Failed to merge PR #{pr_number} even after branch update. "
                    f"Manual resolution required."
                )

        if merged:
            # Delete remote branch (if auto-delete isn't enabled on repo)
            try:
                repo.delete_remote_branch(current_branch)
            except Exception:
                pass  # Non-fatal

            # Checkout detached at default branch
            checkout_detached_default(default_branch=default_branch)

    return PrFlowResult(
        ticket_id=ticket_id,
        branch=current_branch,
        commit_sha=commit_sha,
        pr_number=pr_number,
        pr_url=pr_url,
        merged=merged,
        already_done=False,
    )
