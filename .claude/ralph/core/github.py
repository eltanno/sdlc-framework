"""GitHub CLI (gh) wrapper for issue and pull request operations.

This module wraps the gh CLI to provide Python functions for:
- Listing and fetching issues
- Creating and managing pull requests
- Closing issues and updating labels

All functions use subprocess to call the gh CLI and parse JSON output.
External dependencies (subprocess calls) are isolated for easy mocking in tests.
"""

import json
import subprocess
from typing import Any


class GitHubError(Exception):
    """Base exception for GitHub operations.

    Attributes:
        message: Error message
        command: The command that failed (if available)
        stderr: Standard error output from the command
    """

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        stderr: str | None = None,
    ):
        self.command = command
        self.stderr = stderr
        if command:
            full_message = f"{message}: {' '.join(command)}"
        else:
            full_message = message
        if stderr:
            full_message = f"{full_message}\n{stderr}"
        super().__init__(full_message)


class AuthenticationError(GitHubError):
    """Raised when gh CLI is not authenticated."""

    pass


class RateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded."""

    pass


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
        AuthenticationError: If gh is not authenticated
        RateLimitError: If API rate limit exceeded
        GitHubError: For other gh command failures
    """
    cmd = ["gh"] + args
    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
    )

    if check and result.returncode != 0:
        stderr = result.stderr.lower() if result.stderr else ""

        # Check for authentication errors
        if "auth" in stderr or "login" in stderr or "authentication" in stderr:
            raise AuthenticationError(
                "GitHub CLI not authenticated. Run 'gh auth login' to authenticate.",
                command=cmd,
                stderr=result.stderr,
            )

        # Check for rate limit errors
        if "rate limit" in stderr:
            raise RateLimitError(
                "GitHub API rate limit exceeded. Please wait and try again.",
                command=cmd,
                stderr=result.stderr,
            )

        # Generic error
        raise GitHubError(
            f"GitHub command failed with exit code {result.returncode}",
            command=cmd,
            stderr=result.stderr,
        )

    return result


def _parse_json_output(output: str) -> Any:
    """Parse JSON output from gh CLI.

    Args:
        output: JSON string from gh command

    Returns:
        Parsed JSON (dict, list, or primitive)

    Raises:
        GitHubError: If JSON parsing fails
    """
    try:
        return json.loads(output) if output.strip() else None
    except json.JSONDecodeError as e:
        raise GitHubError(f"Failed to parse gh output as JSON: {e}")


# Issue fields to request by default
_ISSUE_FIELDS = [
    "number",
    "title",
    "body",
    "state",
    "labels",
    "assignees",
    "url",
]

# PR fields to request by default
_PR_FIELDS = [
    "number",
    "title",
    "body",
    "state",
    "url",
    "headRefName",
    "baseRefName",
]


def list_issues(
    state: str | None = None,
    labels: list[str] | None = None,
    assignee: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List issues with optional filters.

    Args:
        state: Filter by state ('open', 'closed', 'all')
        labels: Filter by labels (all must match)
        assignee: Filter by assignee username
        search: Search term for title/body
        limit: Maximum number of issues to return

    Returns:
        List of issue dictionaries with full metadata

    Raises:
        AuthenticationError: If not authenticated
        RateLimitError: If rate limited
        GitHubError: For other failures
    """
    args = ["issue", "list", "--json", ",".join(_ISSUE_FIELDS)]

    if state:
        args.extend(["--state", state])

    if labels:
        for label in labels:
            args.extend(["--label", label])

    if assignee:
        args.extend(["--assignee", assignee])

    if search:
        args.extend(["--search", search])

    args.extend(["--limit", str(limit)])

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout) or []


def get_issue(issue_number: int) -> dict[str, Any]:
    """Get details for a single issue.

    Args:
        issue_number: The issue number to fetch

    Returns:
        Issue dictionary with full metadata

    Raises:
        GitHubError: If issue not found or other error
    """
    args = ["issue", "view", str(issue_number), "--json", ",".join(_ISSUE_FIELDS)]

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout)


def close_issue(issue_number: int) -> None:
    """Close an issue.

    Args:
        issue_number: The issue number to close

    Raises:
        GitHubError: If close fails
    """
    args = ["issue", "close", str(issue_number)]
    _run_gh_command(args)


def edit_issue(
    issue_number: int,
    add_labels: list[str] | None = None,
    remove_labels: list[str] | None = None,
    add_assignees: list[str] | None = None,
    remove_assignees: list[str] | None = None,
) -> None:
    """Edit an issue's labels and/or assignees.

    Args:
        issue_number: The issue number to edit
        add_labels: Labels to add
        remove_labels: Labels to remove
        add_assignees: Assignees to add (usernames or '@me')
        remove_assignees: Assignees to remove

    Raises:
        GitHubError: If edit fails
    """
    args = ["issue", "edit", str(issue_number)]

    if add_labels:
        for label in add_labels:
            args.extend(["--add-label", label])

    if remove_labels:
        for label in remove_labels:
            args.extend(["--remove-label", label])

    if add_assignees:
        for assignee in add_assignees:
            args.extend(["--add-assignee", assignee])

    if remove_assignees:
        for assignee in remove_assignees:
            args.extend(["--remove-assignee", assignee])

    _run_gh_command(args)


def comment_issue(issue_number: int, body: str) -> None:
    """Add a comment to an issue.

    Args:
        issue_number: The issue number to comment on
        body: The comment body text

    Raises:
        GitHubError: If comment fails
    """
    args = ["issue", "comment", str(issue_number), "--body", body]
    _run_gh_command(args)


def list_prs(
    state: str | None = None,
    head: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List pull requests with optional filters.

    Args:
        state: Filter by state ('open', 'closed', 'merged', 'all')
        head: Filter by head branch name
        search: Search term for title/body
        limit: Maximum number of PRs to return

    Returns:
        List of PR dictionaries with metadata

    Raises:
        AuthenticationError: If not authenticated
        RateLimitError: If rate limited
        GitHubError: For other failures
    """
    args = ["pr", "list", "--json", ",".join(_PR_FIELDS)]

    if state:
        args.extend(["--state", state])

    if head:
        args.extend(["--head", head])

    if search:
        args.extend(["--search", search])

    args.extend(["--limit", str(limit)])

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout) or []


def get_pr(pr_number: int) -> dict[str, Any]:
    """Get details for a single pull request.

    Args:
        pr_number: The PR number to fetch

    Returns:
        PR dictionary with full metadata

    Raises:
        GitHubError: If PR not found or other error
    """
    args = ["pr", "view", str(pr_number), "--json", ",".join(_PR_FIELDS)]

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout)


def create_pr(
    title: str,
    body: str,
    base: str = "main",
    head: str | None = None,
) -> dict[str, Any]:
    """Create a pull request.

    Args:
        title: PR title
        body: PR body/description
        base: Base branch (default: main)
        head: Head branch (default: current branch)

    Returns:
        Dictionary with 'number' and 'url' of created PR

    Raises:
        GitHubError: If creation fails (e.g., nothing to commit)
    """
    args = [
        "pr",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--base",
        base,
        "--json",
        "number,url",
    ]

    if head:
        args.extend(["--head", head])

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout)


def merge_pr(pr_number: int, squash: bool = True) -> None:
    """Merge a pull request.

    Args:
        pr_number: The PR number to merge
        squash: If True, use squash merge (default)

    Raises:
        GitHubError: If merge fails (e.g., conflicts)
    """
    args = ["pr", "merge", str(pr_number)]

    if squash:
        args.append("--squash")

    _run_gh_command(args)


def get_current_user() -> str:
    """Get the current authenticated user's login.

    Returns:
        Username of the authenticated user

    Raises:
        AuthenticationError: If not authenticated
    """
    args = ["api", "user", "--jq", ".login"]

    result = _run_gh_command(args)
    return result.stdout.strip()


def check_auth() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        get_current_user()
        return True
    except AuthenticationError:
        return False


def api_call(
    endpoint: str,
    method: str | None = None,
    fields: dict[str, Any] | None = None,
) -> Any:
    """Make a low-level API call to GitHub.

    Args:
        endpoint: API endpoint (e.g., 'repos/owner/repo/labels')
        method: HTTP method (GET, POST, etc.)
        fields: Fields to send (for POST/PATCH)

    Returns:
        Parsed JSON response

    Raises:
        GitHubError: If API call fails
    """
    args = ["api", endpoint]

    if method:
        args.extend(["-X", method])

    if fields:
        for key, value in fields.items():
            args.extend(["-f", f"{key}={value}"])

    result = _run_gh_command(args)
    return _parse_json_output(result.stdout)
