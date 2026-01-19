"""Git CLI wrapper for repository operations.

This module wraps the git CLI to provide Python functions for:
- Branch creation and checkout
- Staging and committing changes
- Pushing to remote repositories
- Checking repository status

All functions use subprocess to call the git CLI and parse output.
External dependencies (subprocess calls) are isolated for easy mocking in tests.
"""

import re
import subprocess
from dataclasses import dataclass


class GitError(Exception):
    """Base exception for Git operations.

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


class GitNotInstalledError(GitError):
    """Raised when git CLI is not installed or not found."""

    pass


@dataclass
class GitStatus:
    """Repository status information.

    Attributes:
        is_clean: True if no uncommitted changes
        modified: List of modified file paths
        staged: List of staged file paths
        untracked: List of untracked file paths
    """

    is_clean: bool
    modified: list[str]
    staged: list[str]
    untracked: list[str]


def _run_git_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git CLI command and return the result.

    Args:
        args: Command arguments (without 'git' prefix)
        check: If True, raise GitError on non-zero exit code
        capture_output: If True, capture stdout and stderr

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        GitNotInstalledError: If git is not installed
        GitError: For other git command failures
    """
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )
    except FileNotFoundError:
        raise GitNotInstalledError(
            "Git is not installed. Please install git to continue.",
            command=cmd,
        )

    if check and result.returncode != 0:
        stderr = result.stderr if result.stderr else ""

        raise GitError(
            f"Git command failed with exit code {result.returncode}",
            command=cmd,
            stderr=stderr,
        )

    return result


def get_current_branch() -> str:
    """Get the name of the current branch.

    Returns:
        Name of the current branch

    Raises:
        GitError: If not in a git repository or other error
    """
    result = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def create_branch(branch_name: str, start_point: str | None = None) -> None:
    """Create a new branch and check it out.

    Args:
        branch_name: Name of the branch to create
        start_point: Optional starting point (commit, branch, or tag)

    Raises:
        GitError: If branch already exists or other error
    """
    args = ["checkout", "-b", branch_name]
    if start_point:
        args.append(start_point)
    _run_git_command(args)


def checkout_branch(branch_name: str) -> None:
    """Checkout an existing branch.

    Args:
        branch_name: Name of the branch to checkout

    Raises:
        GitError: If branch doesn't exist or other error
    """
    _run_git_command(["checkout", branch_name])


def branch_exists(branch_name: str) -> bool:
    """Check if a local branch exists.

    Args:
        branch_name: Name of the branch to check

    Returns:
        True if branch exists, False otherwise
    """
    result = _run_git_command(
        ["rev-parse", "--verify", branch_name],
        check=False,
    )
    return result.returncode == 0


def get_status() -> GitStatus:
    """Get the current repository status.

    Returns:
        GitStatus with clean state and file lists

    Raises:
        GitError: If not in a git repository
    """
    result = _run_git_command(["status", "--porcelain"])
    output = result.stdout

    if not output.strip():
        return GitStatus(
            is_clean=True,
            modified=[],
            staged=[],
            untracked=[],
        )

    modified = []
    staged = []
    untracked = []

    for line in output.splitlines():
        if len(line) < 3:
            continue

        # First char is staged status, second is working tree status
        index_status = line[0]
        worktree_status = line[1]
        filename = line[3:]

        # Untracked files
        if index_status == "?" and worktree_status == "?":
            untracked.append(filename)
        # Staged files (added, modified, deleted in index)
        elif index_status in ("A", "M", "D", "R", "C"):
            staged.append(filename)
        # Modified in working tree
        if worktree_status in ("M", "D"):
            modified.append(filename)

    return GitStatus(
        is_clean=False,
        modified=modified,
        staged=staged,
        untracked=untracked,
    )


def is_dirty() -> bool:
    """Check if the working directory has uncommitted changes.

    Returns:
        True if there are uncommitted changes, False otherwise
    """
    status = get_status()
    return not status.is_clean


def stage_files(files: list[str]) -> None:
    """Stage specific files for commit.

    Args:
        files: List of file paths to stage

    Raises:
        GitError: If staging fails
    """
    _run_git_command(["add"] + files)


def stage_all() -> None:
    """Stage all changes for commit.

    Raises:
        GitError: If staging fails
    """
    _run_git_command(["add", "-A"])


def commit(message: str, author: str | None = None) -> str:
    """Create a commit with the staged changes.

    Args:
        message: Commit message
        author: Optional author in "Name <email>" format

    Returns:
        Commit SHA (short form)

    Raises:
        GitError: If nothing to commit or other error
    """
    args = ["commit", "-m", message]
    if author:
        args.extend(["--author", author])

    result = _run_git_command(args)

    # Parse commit SHA from output like "[main abc1234] message"
    match = re.search(r"\[[\w/.-]+ ([a-f0-9]+)\]", result.stdout)
    if match:
        return match.group(1)

    return result.stdout.strip()


def push(
    remote: str | None = None,
    branch: str | None = None,
    set_upstream: bool = False,
) -> None:
    """Push commits to remote repository.

    Args:
        remote: Remote name (default: origin)
        branch: Branch to push (default: current branch)
        set_upstream: If True, set upstream tracking

    Raises:
        GitError: If push fails (e.g., conflicts)
    """
    args = ["push"]

    if set_upstream:
        args.append("-u")

    if remote:
        args.append(remote)

    if branch:
        args.append(branch)

    _run_git_command(args)


def pull(remote: str | None = None, branch: str | None = None) -> None:
    """Pull changes from remote repository.

    Args:
        remote: Remote name (default: origin)
        branch: Branch to pull (default: current branch)

    Raises:
        GitError: If pull fails
    """
    args = ["pull"]

    if remote:
        args.append(remote)

    if branch:
        args.append(branch)

    _run_git_command(args)


def fetch(remote: str | None = None, prune: bool = False) -> None:
    """Fetch changes from remote repository.

    Args:
        remote: Remote name (default: all remotes)
        prune: If True, prune stale remote-tracking branches

    Raises:
        GitError: If fetch fails
    """
    args = ["fetch"]

    if prune:
        args.append("--prune")

    if remote:
        args.append(remote)

    _run_git_command(args)


def get_latest_commit_sha() -> str:
    """Get the SHA of the latest commit.

    Returns:
        Full commit SHA

    Raises:
        GitError: If no commits exist
    """
    result = _run_git_command(["rev-parse", "HEAD"])
    return result.stdout.strip()


def has_remote_branch(branch_name: str, remote: str = "origin") -> bool:
    """Check if a branch exists on the remote.

    Args:
        branch_name: Name of the branch to check
        remote: Remote name (default: origin)

    Returns:
        True if remote branch exists, False otherwise
    """
    result = _run_git_command(
        ["ls-remote", "--heads", remote, branch_name],
        check=False,
    )
    return bool(result.stdout.strip())


def merge(branch: str, no_edit: bool = True, message: str | None = None) -> None:
    """Merge a branch into the current branch.

    Args:
        branch: Branch or ref to merge (e.g., "origin/main")
        no_edit: If True, use default merge commit message
        message: Custom merge commit message (optional)

    Raises:
        GitError: If merge fails (including conflicts)
    """
    args = ["merge", branch]

    if no_edit:
        args.append("--no-edit")

    if message:
        args.extend(["-m", message])

    _run_git_command(args)
