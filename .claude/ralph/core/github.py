"""GitHub CLI (gh) wrapper for issue and pull request operations.

This module wraps the gh CLI to provide Python functions for:
- Listing and fetching issues
- Creating and managing pull requests
- Closing issues and updating labels

All functions use subprocess to call the gh CLI and parse JSON output.
External dependencies (subprocess calls) are isolated for easy mocking in tests.
"""

import json
import re
import subprocess
from dataclasses import dataclass

from core.errors import CLIError


class GitHubError(CLIError):
    """Base exception for GitHub operations.

    Attributes:
        message: Error message
        command: The command that failed (if available)
        stderr: Standard error output from the command
    """

    pass


class GitHubNotInstalledError(GitHubError):
    """Raised when gh CLI is not installed or not found."""

    pass


class GitHubAuthError(GitHubError):
    """Raised when gh CLI is not authenticated."""

    pass


@dataclass
class PullRequestResult:
    """Result of creating a pull request.

    Attributes:
        url: Full URL of the created PR
        number: PR number
    """

    url: str
    number: int


def _run_gh_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command and return the result.

    Args:
        args: Command arguments (without 'gh' prefix)
        check: If True, raise GitHubError on non-zero exit code
        capture_output: If True, capture stdout and stderr

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        GitHubNotInstalledError: If gh is not installed
        GitHubAuthError: If gh is not authenticated
        GitHubError: For other gh command failures
    """
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )
    except FileNotFoundError:
        raise GitHubNotInstalledError(
            "GitHub CLI (gh) is not installed. Please install it from https://cli.github.com/",
            command=cmd,
        )

    if check and result.returncode != 0:
        stderr = result.stderr if result.stderr else ""

        # Check for authentication errors
        if "GH_TOKEN" in stderr or "not logged in" in stderr or "authentication" in stderr.lower():
            raise GitHubAuthError(
                "GitHub CLI is not authenticated. Run 'gh auth login' to authenticate.",
                command=cmd,
                stderr=stderr,
            )

        raise GitHubError(
            f"GitHub CLI command failed with exit code {result.returncode}",
            command=cmd,
            stderr=stderr,
        )

    return result


def list_issues(
    state: str | None = None,
    label: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """List issues in the repository.

    Args:
        state: Filter by state ('open', 'closed', 'all')
        label: Filter by label
        search: Search string for issue titles

    Returns:
        List of issue dictionaries with number, title, state, labels

    Raises:
        GitHubError: If listing fails
    """
    args = ["issue", "list", "--json", "number,title,state,labels,body"]

    if state:
        args.extend(["--state", state])

    if label:
        args.extend(["--label", label])

    if search:
        args.extend(["--search", search])

    result = _run_gh_command(args)
    return json.loads(result.stdout)


def get_issue(issue_number: int) -> dict:
    """Get details of a specific issue.

    Args:
        issue_number: Issue number to fetch

    Returns:
        Issue dictionary with number, title, body, state, labels

    Raises:
        GitHubError: If issue not found or fetch fails
    """
    args = [
        "issue",
        "view",
        str(issue_number),
        "--json",
        "number,title,body,state,labels",
    ]

    result = _run_gh_command(args)
    return json.loads(result.stdout)


def close_issue(issue_number: int) -> None:
    """Close an issue.

    Args:
        issue_number: Issue number to close

    Raises:
        GitHubError: If closing fails
    """
    args = ["issue", "close", str(issue_number)]
    _run_gh_command(args)


def find_issue_by_title(search_term: str, state: str = "open") -> int | None:
    """Find an issue by searching its title.

    Args:
        search_term: Term to search for in issue titles
        state: State filter ('open', 'closed', 'all')

    Returns:
        Issue number if found, None otherwise
    """
    args = [
        "issue",
        "list",
        "--search",
        f"{search_term} in:title",
        "--state",
        state,
        "--json",
        "number",
    ]

    result = _run_gh_command(args, check=False)

    if result.returncode != 0:
        return None

    issues = json.loads(result.stdout)
    if issues:
        return issues[0]["number"]

    return None


def create_pull_request(
    title: str,
    body: str,
    base: str | None = None,
    head: str | None = None,
    draft: bool = False,
) -> PullRequestResult:
    """Create a pull request.

    Args:
        title: PR title
        body: PR body/description
        base: Base branch (default: repository default)
        head: Source branch name. Required when on detached HEAD
              (e.g. in git worktrees) so gh can determine the source branch.
        draft: Create as draft PR

    Returns:
        PullRequestResult with URL and number

    Raises:
        GitHubError: If PR creation fails
    """
    args = ["pr", "create", "--title", title, "--body", body]

    if base:
        args.extend(["--base", base])

    if head:
        args.extend(["--head", head])

    if draft:
        args.append("--draft")

    result = _run_gh_command(args)

    # Parse URL from output (e.g., "https://github.com/owner/repo/pull/123")
    url = result.stdout.strip()

    # Extract PR number from URL
    match = re.search(r"/pull/(\d+)", url)
    if match:
        pr_number = int(match.group(1))
    else:
        # Fallback: try to find any number at the end
        match = re.search(r"(\d+)$", url)
        pr_number = int(match.group(1)) if match else 0

    return PullRequestResult(url=url, number=pr_number)


def get_pull_request(pr_number: int) -> dict:
    """Get details of a specific pull request.

    Args:
        pr_number: PR number to fetch

    Returns:
        PR dictionary with number, title, state, url, mergeable

    Raises:
        GitHubError: If PR not found or fetch fails
    """
    args = [
        "pr",
        "view",
        str(pr_number),
        "--json",
        "number,title,state,url,mergeable,body",
    ]

    result = _run_gh_command(args)
    return json.loads(result.stdout)


def list_pull_requests(
    head: str | None = None,
    state: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """List pull requests.

    Args:
        head: Filter by head branch
        state: Filter by state ('open', 'closed', 'merged', 'all')
        search: Search string

    Returns:
        List of PR dictionaries

    Raises:
        GitHubError: If listing fails
    """
    args = ["pr", "list", "--json", "number,title,state,url,headRefName"]

    if head:
        args.extend(["--head", head])

    if state:
        args.extend(["--state", state])

    if search:
        args.extend(["--search", search])

    result = _run_gh_command(args)
    return json.loads(result.stdout)


def merge_pull_request(
    pr_number: int,
    strategy: str = "squash",
    delete_branch: bool = False,
) -> None:
    """Merge a pull request.

    Args:
        pr_number: PR number to merge
        strategy: Merge strategy ('merge', 'squash', 'rebase')
        delete_branch: Delete head branch after merge

    Raises:
        GitHubError: If merge fails
    """
    args = ["pr", "merge", str(pr_number)]

    if strategy == "squash":
        args.append("--squash")
    elif strategy == "rebase":
        args.append("--rebase")
    elif strategy == "merge":
        args.append("--merge")

    if delete_branch:
        args.append("--delete-branch")

    _run_gh_command(args)


def find_merged_pr(search_term: str) -> int | None:
    """Find a merged PR by searching its title.

    Args:
        search_term: Term to search for in PR titles

    Returns:
        PR number if found, None otherwise
    """
    args = [
        "pr",
        "list",
        "--search",
        f"{search_term} in:title",
        "--state",
        "merged",
        "--json",
        "number",
    ]

    result = _run_gh_command(args, check=False)

    if result.returncode != 0:
        return None

    prs = json.loads(result.stdout)
    if prs:
        return prs[0]["number"]

    return None


def delete_remote_branch(branch_name: str, remote: str = "origin") -> None:
    """Delete a remote branch.

    This uses git push to delete the remote branch since gh doesn't
    have a direct command for this.

    Args:
        branch_name: Name of the branch to delete
        remote: Remote name (default: origin)

    Raises:
        GitHubError: If deletion fails
    """
    # Use subprocess directly for git command
    cmd = ["git", "push", remote, "--delete", branch_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Don't raise error if branch doesn't exist remotely
        if result.returncode != 0 and "remote ref does not exist" not in result.stderr:
            raise GitHubError(
                f"Failed to delete remote branch {branch_name}",
                command=cmd,
                stderr=result.stderr,
            )
    except FileNotFoundError:
        raise GitHubError(
            "Git is not installed",
            command=cmd,
        )
