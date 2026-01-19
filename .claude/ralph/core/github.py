"""GitHub CLI (gh) wrapper for issue and pull request operations.

This module wraps the gh CLI to provide Python functions for:
- Listing and fetching issues
- Creating and managing pull requests
- Closing issues and updating labels
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class GitHubError(Exception):
    """Base exception for GitHub-related errors."""

    pass


class GitHubNotFoundError(GitHubError):
    """Raised when gh CLI is not installed or not found."""

    pass


class GitHubAuthError(GitHubError):
    """Raised when gh CLI is not authenticated."""

    pass


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded."""

    pass


def _run_gh(*args: str, check_auth: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result.

    Args:
        *args: Arguments to pass to gh
        check_auth: If True, check for auth/rate limit errors

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        GitHubNotFoundError: If gh is not installed
        GitHubAuthError: If not authenticated
        GitHubRateLimitError: If rate limit exceeded
    """
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
        )

        if check_auth and result.returncode != 0:
            stderr_lower = result.stderr.lower()
            if "auth login" in stderr_lower or "not logged" in stderr_lower:
                raise GitHubAuthError(
                    "GitHub CLI is not authenticated. Run 'gh auth login' to authenticate."
                )
            if "rate limit" in stderr_lower:
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded. Please wait before retrying."
                )

        return result
    except FileNotFoundError:
        raise GitHubNotFoundError("gh CLI is not installed or not found in PATH")


def _parse_json_output(stdout: str) -> Any:
    """Parse JSON output from gh CLI.

    Args:
        stdout: Raw stdout from gh command

    Returns:
        Parsed JSON data
    """
    if not stdout.strip():
        return None
    return json.loads(stdout)


# ============================================================================
# Issue Operations
# ============================================================================


def list_issues(
    labels: list[str] | None = None,
    assignee: str | None = None,
    state: str = "open",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List issues in the repository.

    Args:
        labels: Filter by labels
        assignee: Filter by assignee (use "@me" for current user)
        state: Filter by state (open, closed, all)
        limit: Maximum number of issues to return

    Returns:
        List of issue dictionaries

    Raises:
        GitHubAuthError: If not authenticated
        GitHubRateLimitError: If rate limit exceeded
    """
    args = ["issue", "list", "--json", "number,title,state,labels,assignees,body"]
    args.extend(["--state", state])
    args.extend(["--limit", str(limit)])

    if labels:
        for label in labels:
            args.extend(["--label", label])

    if assignee:
        args.extend(["--assignee", assignee])

    result = _run_gh(*args)

    if result.returncode != 0:
        return []

    return _parse_json_output(result.stdout) or []


def get_issue(issue_number: int) -> dict[str, Any] | None:
    """Get details of a specific issue.

    Args:
        issue_number: The issue number

    Returns:
        Issue dictionary, or None if not found
    """
    result = _run_gh(
        "issue", "view", str(issue_number),
        "--json", "number,title,body,state,labels,assignees,author,createdAt,url",
        check_auth=False,
    )

    if result.returncode != 0:
        return None

    return _parse_json_output(result.stdout)


def close_issue(issue_number: int, reason: str | None = None) -> bool:
    """Close an issue.

    Args:
        issue_number: The issue number
        reason: Optional close reason (completed, not_planned)

    Returns:
        True if successful, False otherwise
    """
    args = ["issue", "close", str(issue_number)]

    if reason:
        args.extend(["--reason", reason])

    result = _run_gh(*args, check_auth=False)
    return result.returncode == 0


# ============================================================================
# Label Operations
# ============================================================================


def add_label(issue_number: int, label: str) -> bool:
    """Add a label to an issue.

    Args:
        issue_number: The issue number
        label: The label to add

    Returns:
        True if successful, False otherwise
    """
    result = _run_gh(
        "issue", "edit", str(issue_number),
        "--add-label", label,
        check_auth=False,
    )
    return result.returncode == 0


def remove_label(issue_number: int, label: str) -> bool:
    """Remove a label from an issue.

    Args:
        issue_number: The issue number
        label: The label to remove

    Returns:
        True if successful, False otherwise
    """
    result = _run_gh(
        "issue", "edit", str(issue_number),
        "--remove-label", label,
        check_auth=False,
    )
    return result.returncode == 0


# ============================================================================
# Assignee Operations
# ============================================================================


def assign_issue(issue_number: int, username: str) -> bool:
    """Assign a user to an issue.

    Args:
        issue_number: The issue number
        username: The username to assign

    Returns:
        True if successful, False otherwise
    """
    result = _run_gh(
        "issue", "edit", str(issue_number),
        "--add-assignee", username,
        check_auth=False,
    )
    return result.returncode == 0


def unassign_issue(issue_number: int, username: str) -> bool:
    """Remove a user from an issue.

    Args:
        issue_number: The issue number
        username: The username to remove

    Returns:
        True if successful, False otherwise
    """
    result = _run_gh(
        "issue", "edit", str(issue_number),
        "--remove-assignee", username,
        check_auth=False,
    )
    return result.returncode == 0


# ============================================================================
# Pull Request Operations
# ============================================================================


def create_pr(
    title: str,
    body: str,
    base: str,
    head: str | None = None,
    draft: bool = False,
) -> dict[str, Any] | None:
    """Create a pull request.

    Args:
        title: PR title
        body: PR body/description
        base: Base branch to merge into
        head: Head branch (default: current branch)
        draft: If True, create as draft PR

    Returns:
        PR dictionary with number and url, or None if failed
    """
    args = ["pr", "create", "--title", title, "--body", body, "--base", base]

    if head:
        args.extend(["--head", head])

    if draft:
        args.append("--draft")

    result = _run_gh(*args, check_auth=False)

    if result.returncode != 0:
        return None

    # gh pr create returns JSON with --json flag, but by default returns URL
    # Try to get JSON format
    args.append("--json")
    args.append("number,url")

    # Re-run with JSON output - but actually the PR is already created
    # So we need to parse the output differently
    # The default output is just the URL
    url = result.stdout.strip()
    if url:
        # Extract PR number from URL
        try:
            pr_number = int(url.rstrip("/").split("/")[-1])
            return {"number": pr_number, "url": url}
        except (ValueError, IndexError):
            pass

    # Fallback: try to get the PR we just created
    return _parse_json_output(result.stdout)


def get_pr(pr_number: int) -> dict[str, Any] | None:
    """Get details of a specific pull request.

    Args:
        pr_number: The PR number

    Returns:
        PR dictionary, or None if not found
    """
    result = _run_gh(
        "pr", "view", str(pr_number),
        "--json", "number,title,state,body,mergeable,headRefName,baseRefName,url",
        check_auth=False,
    )

    if result.returncode != 0:
        return None

    return _parse_json_output(result.stdout)


def list_prs(
    state: str = "open",
    base: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """List pull requests in the repository.

    Args:
        state: Filter by state (open, closed, merged, all)
        base: Filter by base branch
        limit: Maximum number of PRs to return

    Returns:
        List of PR dictionaries
    """
    args = ["pr", "list", "--json", "number,title,state,headRefName,baseRefName"]
    args.extend(["--state", state])
    args.extend(["--limit", str(limit)])

    if base:
        args.extend(["--base", base])

    result = _run_gh(*args, check_auth=False)

    if result.returncode != 0:
        return []

    return _parse_json_output(result.stdout) or []


def merge_pr(
    pr_number: int,
    merge_method: str = "merge",
    delete_branch: bool = False,
) -> bool:
    """Merge a pull request.

    Args:
        pr_number: The PR number
        merge_method: merge, squash, or rebase
        delete_branch: If True, delete the head branch after merge

    Returns:
        True if successful, False otherwise
    """
    args = ["pr", "merge", str(pr_number)]

    if merge_method == "squash":
        args.append("--squash")
    elif merge_method == "rebase":
        args.append("--rebase")
    else:
        args.append("--merge")

    if delete_branch:
        args.append("--delete-branch")

    result = _run_gh(*args, check_auth=False)
    return result.returncode == 0


# ============================================================================
# User Operations
# ============================================================================


def get_current_user() -> str | None:
    """Get the username of the currently authenticated user.

    Returns:
        Username, or None if not authenticated
    """
    result = _run_gh("api", "user", "--jq", ".login", check_auth=False)

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


# ============================================================================
# Repository Operations
# ============================================================================


def get_repo_info() -> dict[str, Any] | None:
    """Get information about the current repository.

    Returns:
        Repository dictionary, or None if not in a repo
    """
    result = _run_gh(
        "repo", "view", "--json", "owner,name,defaultBranchRef",
        check_auth=False,
    )

    if result.returncode != 0:
        return None

    return _parse_json_output(result.stdout)
