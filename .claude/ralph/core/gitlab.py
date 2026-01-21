"""GitLab CLI (glab) wrapper for merge request operations.

This module wraps the glab CLI to provide Python functions for:
- Creating and managing merge requests
- Listing and fetching merge requests
- Merging merge requests

All functions use subprocess to call the glab CLI and parse JSON output.
External dependencies (subprocess calls) are isolated for easy mocking in tests.

Note: Issue operations are NOT included - ticket management uses Asana/Trello,
not GitLab Issues.
"""

import json
import re
import subprocess
from dataclasses import dataclass


class GitLabError(Exception):
    """Base exception for GitLab operations.

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


class GitLabNotInstalledError(GitLabError):
    """Raised when glab CLI is not installed or not found."""

    pass


class GitLabAuthError(GitLabError):
    """Raised when glab CLI is not authenticated."""

    pass


@dataclass
class MergeRequestResult:
    """Result of creating a merge request.

    Attributes:
        url: Full URL of the created MR
        number: MR number (iid in GitLab terminology)
    """

    url: str
    number: int


def _run_glab_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a glab CLI command and return the result.

    Args:
        args: Command arguments (without 'glab' prefix)
        check: If True, raise GitLabError on non-zero exit code
        capture_output: If True, capture stdout and stderr

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        GitLabNotInstalledError: If glab is not installed
        GitLabAuthError: If glab is not authenticated
        GitLabError: For other glab command failures
    """
    cmd = ["glab"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )
    except FileNotFoundError:
        raise GitLabNotInstalledError(
            "GitLab CLI (glab) is not installed. Please install it from https://gitlab.com/gitlab-org/cli",
            command=cmd,
        )

    if check and result.returncode != 0:
        stderr = result.stderr if result.stderr else ""

        # Check for authentication errors
        if (
            "authenticate" in stderr.lower()
            or "not logged in" in stderr.lower()
            or "authorization" in stderr.lower()
            or "GITLAB_TOKEN" in stderr
        ):
            raise GitLabAuthError(
                "GitLab CLI is not authenticated. Run 'glab auth login' to authenticate.",
                command=cmd,
                stderr=stderr,
            )

        raise GitLabError(
            f"GitLab CLI command failed with exit code {result.returncode}",
            command=cmd,
            stderr=stderr,
        )

    return result


def create_merge_request(
    title: str,
    body: str,
    base: str | None = None,
    draft: bool = False,
) -> MergeRequestResult:
    """Create a merge request.

    Args:
        title: MR title
        body: MR body/description
        base: Base/target branch (default: repository default)
        draft: Create as draft MR

    Returns:
        MergeRequestResult with URL and number

    Raises:
        GitLabError: If MR creation fails
    """
    args = ["mr", "create", "--title", title, "--description", body]

    if base:
        args.extend(["--target-branch", base])

    if draft:
        args.append("--draft")

    result = _run_glab_command(args)

    # Parse URL from output (e.g., "https://gitlab.example.com/group/repo/-/merge_requests/123")
    url = result.stdout.strip()

    # Extract MR number from URL (GitLab uses iid)
    match = re.search(r"/merge_requests/(\d+)", url)
    if match:
        mr_number = int(match.group(1))
    else:
        # Fallback: try to find any number at the end
        match = re.search(r"(\d+)$", url)
        mr_number = int(match.group(1)) if match else 0

    return MergeRequestResult(url=url, number=mr_number)


def get_merge_request(mr_number: int) -> dict:
    """Get details of a specific merge request.

    Args:
        mr_number: MR number (iid) to fetch

    Returns:
        MR dictionary with iid, title, state, web_url

    Raises:
        GitLabError: If MR not found or fetch fails
    """
    args = ["mr", "view", str(mr_number), "--output", "json"]

    result = _run_glab_command(args)
    return json.loads(result.stdout)


def list_merge_requests(
    head: str | None = None,
    state: str | None = None,
) -> list[dict]:
    """List merge requests.

    Args:
        head: Filter by source branch
        state: Filter by state ('opened', 'closed', 'merged', 'all')

    Returns:
        List of MR dictionaries

    Raises:
        GitLabError: If listing fails
    """
    args = ["mr", "list", "--output", "json"]

    if head:
        args.extend(["--source-branch", head])

    if state:
        args.extend(["--state", state])

    result = _run_glab_command(args)
    return json.loads(result.stdout)


def merge_merge_request(
    mr_number: int,
    strategy: str = "squash",
    delete_branch: bool = False,
) -> None:
    """Merge a merge request.

    Args:
        mr_number: MR number (iid) to merge
        strategy: Merge strategy ('merge', 'squash', 'rebase')
        delete_branch: Delete source branch after merge

    Raises:
        GitLabError: If merge fails
    """
    args = ["mr", "merge", str(mr_number), "--yes"]

    if strategy == "squash":
        args.append("--squash")
    elif strategy == "rebase":
        args.append("--rebase")
    # "merge" is the default, no flag needed

    if delete_branch:
        args.append("--remove-source-branch")

    _run_glab_command(args)


def find_merged_mr(search_term: str) -> int | None:
    """Find a merged MR by searching its title.

    Args:
        search_term: Term to search for in MR titles

    Returns:
        MR number (iid) if found, None otherwise
    """
    args = [
        "mr",
        "list",
        "--state",
        "merged",
        "--search",
        search_term,
        "--output",
        "json",
    ]

    result = _run_glab_command(args, check=False)

    if result.returncode != 0:
        return None

    mrs = json.loads(result.stdout)
    if mrs:
        return mrs[0]["iid"]

    return None


def delete_remote_branch(branch_name: str, remote: str = "origin") -> None:
    """Delete a remote branch.

    This uses git push to delete the remote branch since glab doesn't
    have a direct command for this.

    Args:
        branch_name: Name of the branch to delete
        remote: Remote name (default: origin)

    Raises:
        GitLabError: If deletion fails (unless branch doesn't exist)
    """
    # Use subprocess directly for git command
    cmd = ["git", "push", remote, "--delete", branch_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Don't raise error if branch doesn't exist remotely
        if result.returncode != 0 and "remote ref does not exist" not in result.stderr:
            raise GitLabError(
                f"Failed to delete remote branch {branch_name}",
                command=cmd,
                stderr=result.stderr,
            )
    except FileNotFoundError:
        raise GitLabError(
            "Git is not installed",
            command=cmd,
        )
