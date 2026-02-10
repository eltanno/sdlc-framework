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
import logging
import re
import subprocess
import time
import urllib.parse
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
        GitLabError: if MR creation fails
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
    # Use glab api for JSON output (glab mr view --output json not supported in older versions)
    args = ["api", f"projects/:id/merge_requests/{mr_number}"]

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
    # Use glab api for JSON output (glab mr list --output json not supported in older versions)
    # Build query parameters
    params = []
    if head:
        params.append(f"source_branch={head}")
    if state:
        params.append(f"state={state}")

    endpoint = "projects/:id/merge_requests"
    if params:
        endpoint += "?" + "&".join(params)

    args = ["api", endpoint]

    result = _run_glab_command(args)
    return json.loads(result.stdout)


def merge_merge_request(
    mr_number: int,
    strategy: str = "squash",
    delete_branch: bool = False,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> None:
    """Merge a merge request with retry logic for transient failures.

    GitLab's API can return 405/422 errors when the MR state is still syncing
    after a push or rebase. This function retries with exponential backoff
    to handle these transient failures.

    Uses the GitLab REST API directly instead of 'glab mr merge' because
    the CLI command with --squash sets merge_when_pipeline_succeeds=true
    which blocks merging when pipelines are in manual/pending state.

    Args:
        mr_number: MR number (iid) to merge
        strategy: Merge strategy ('merge', 'squash', 'rebase')
        delete_branch: Delete source branch after merge
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 5.0)

    Raises:
        GitLabError: If merge fails after all retries
    """
    # Use direct API call instead of 'glab mr merge' to avoid auto-merge behavior
    # The CLI command sets merge_when_pipeline_succeeds=true which blocks on pipelines
    endpoint = f"projects/:id/merge_requests/{mr_number}/merge"
    args = ["api", "-X", "PUT", endpoint]

    if strategy == "squash":
        args.extend(["-f", "squash=true"])
    elif strategy == "rebase":
        # GitLab API uses merge_commit_message for rebase, but we just want to merge
        # Rebase merge is handled by setting squash=false (default)
        pass
    # "merge" is the default, no additional flags needed

    if delete_branch:
        args.extend(["-f", "should_remove_source_branch=true"])

    last_error = None
    for attempt in range(max_retries):
        try:
            result = _run_glab_command(args)
            # Verify the merge succeeded by checking the response
            try:
                response = json.loads(result.stdout)
                if response.get("state") == "merged":
                    return  # Success
                # If state is not merged, treat as failure
                raise GitLabError(
                    f"MR !{mr_number} not merged. State: {response.get('state')}",
                    command=["glab"] + args,
                    stderr=f"detailed_merge_status: {response.get('detailed_merge_status')}",
                )
            except json.JSONDecodeError:
                # If we can't parse the response but command succeeded, assume OK
                return
        except GitLabError as e:
            last_error = e
            error_str = str(e).lower()
            stderr = getattr(e, "stderr", "").lower() if hasattr(e, "stderr") else ""

            # Check if this is a retryable error (405/422 or "cannot be merged")
            is_retryable = (
                "405" in error_str
                or "422" in error_str
                or "method not allowed" in error_str
                or "cannot be merged" in error_str
                or "cannot be merged" in stderr
            )

            if is_retryable and attempt < max_retries - 1:
                delay = retry_delay * (2**attempt)  # Exponential backoff
                logger.warning(
                    f"Merge attempt {attempt + 1}/{max_retries} failed for MR !{mr_number}. "
                    f"Retrying in {delay:.1f}s: {e}"
                )
                time.sleep(delay)
            else:
                # Not retryable or out of retries
                raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error


def find_merged_mr(search_term: str) -> int | None:
    """Find a merged MR by searching its title.

    Args:
        search_term: Term to search for in MR titles

    Returns:
        MR number (iid) if found, None otherwise
    """
    # Use glab api for JSON output (glab mr list --output json not supported in older versions)
    # URL encode the search term for the query parameter
    encoded_search = urllib.parse.quote(search_term)

    args = [
        "api",
        f"projects/:id/merge_requests?state=merged&search={encoded_search}",
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
