"""Git CLI wrapper for repository operations.

This module wraps the git CLI to provide Python functions for:
- Branch creation and checkout
- Staging and committing changes
- Pushing to remote repositories
- Checking repository status
"""

from __future__ import annotations

import subprocess
from typing import Any


class GitError(Exception):
    """Base exception for git-related errors."""

    pass


class GitNotFoundError(GitError):
    """Raised when git CLI is not installed or not found."""

    pass


def _run_git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run a git command and return the result.

    Args:
        *args: Arguments to pass to git
        check: If True, raise GitError on non-zero return code

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        GitNotFoundError: If git is not installed
        GitError: If check=True and command returns non-zero
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
        )

        if check and result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            raise GitError(error_msg)

        return result
    except FileNotFoundError:
        raise GitNotFoundError("git is not installed or not found in PATH")


# ============================================================================
# Branch Operations
# ============================================================================


def create_branch(branch_name: str) -> bool:
    """Create and checkout a new branch.

    Args:
        branch_name: Name of the branch to create

    Returns:
        True if successful, False otherwise
    """
    result = _run_git("checkout", "-b", branch_name)
    return result.returncode == 0


def checkout_branch(branch_name: str) -> bool:
    """Checkout an existing branch.

    Args:
        branch_name: Name of the branch to checkout

    Returns:
        True if successful, False otherwise
    """
    result = _run_git("checkout", branch_name)
    return result.returncode == 0


def get_current_branch() -> str | None:
    """Get the name of the current branch.

    Returns:
        Branch name, or None if in detached HEAD state

    Raises:
        GitNotFoundError: If git is not installed
        GitError: If not in a git repository
    """
    result = _run_git("symbolic-ref", "--short", "HEAD")

    if result.returncode != 0:
        # Check if it's a "not a git repository" error
        if "not a git repository" in result.stderr.lower():
            raise GitError(result.stderr.strip())
        # Detached HEAD state
        return None

    return result.stdout.strip()


def branch_exists(branch_name: str, check_remote: bool = False) -> bool:
    """Check if a branch exists.

    Args:
        branch_name: Name of the branch to check
        check_remote: If True, also check remote branches

    Returns:
        True if branch exists, False otherwise
    """
    # Check local branch
    result = _run_git("show-ref", "--verify", f"refs/heads/{branch_name}")
    if result.returncode == 0:
        return True

    # Check remote if requested
    if check_remote:
        result = _run_git("show-ref", "--verify", f"refs/remotes/origin/{branch_name}")
        return result.returncode == 0

    return False


# ============================================================================
# Commit Operations
# ============================================================================


def stage_all() -> bool:
    """Stage all changes (including untracked files).

    Returns:
        True if successful, False otherwise
    """
    result = _run_git("add", "-A")
    return result.returncode == 0


def commit(message: str, coauthor: str | None = None) -> bool:
    """Create a commit with the given message.

    Args:
        message: Commit message
        coauthor: Optional co-author in format "Name <email>"

    Returns:
        True if successful, False otherwise
    """
    full_message = message
    if coauthor:
        full_message = f"{message}\n\nCo-Authored-By: {coauthor}"

    result = _run_git("commit", "-m", full_message)
    return result.returncode == 0


def get_last_commit_sha() -> str | None:
    """Get the SHA of the last commit.

    Returns:
        Full SHA of the last commit, or None if no commits
    """
    result = _run_git("rev-parse", "HEAD")
    if result.returncode != 0:
        return None
    return result.stdout.strip()


# ============================================================================
# Push Operations
# ============================================================================


def push(
    remote: str = "origin",
    branch: str | None = None,
    set_upstream: bool = False,
) -> bool:
    """Push commits to remote.

    Args:
        remote: Remote name (default: "origin")
        branch: Branch name (default: current branch)
        set_upstream: If True, set upstream tracking

    Returns:
        True if successful, False otherwise
    """
    args = ["push"]

    if set_upstream:
        args.append("-u")

    args.append(remote)

    if branch:
        args.append(branch)

    result = _run_git(*args)
    return result.returncode == 0


# ============================================================================
# Status Operations
# ============================================================================


def is_dirty() -> bool:
    """Check if the working tree has uncommitted changes.

    Returns:
        True if there are uncommitted changes, False if clean
    """
    result = _run_git("status", "--porcelain")
    return bool(result.stdout.strip())


def get_status() -> list[dict[str, str]]:
    """Get the status of all changed files.

    Returns:
        List of dicts with 'status' and 'file' keys
    """
    result = _run_git("status", "--porcelain")
    files = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2].strip()
        file_path = line[3:]
        files.append({"status": status, "file": file_path})

    return files


# ============================================================================
# Diff Operations
# ============================================================================


def get_diff(
    staged: bool = False,
    ref1: str | None = None,
    ref2: str | None = None,
) -> str:
    """Get diff output.

    Args:
        staged: If True, show staged changes only
        ref1: First reference for comparison
        ref2: Second reference for comparison

    Returns:
        Diff output as string
    """
    args = ["diff"]

    if staged:
        args.append("--staged")
    elif ref1 and ref2:
        args.extend([ref1, ref2])
    elif ref1:
        args.append(ref1)

    result = _run_git(*args)
    return result.stdout


# ============================================================================
# Log Operations
# ============================================================================


def get_recent_commits(limit: int = 10) -> list[dict[str, str]]:
    """Get recent commits.

    Args:
        limit: Maximum number of commits to return

    Returns:
        List of dicts with 'sha', 'message', and 'date' keys
    """
    result = _run_git(
        "log",
        f"-{limit}",
        "--pretty=format:%H|%s|%cd",
        "--date=short",
    )

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) >= 3:
            commits.append({
                "sha": parts[0],
                "message": parts[1],
                "date": parts[2],
            })

    return commits


# ============================================================================
# Fetch Operations
# ============================================================================


def fetch(remote: str | None = None) -> bool:
    """Fetch from remote.

    Args:
        remote: Remote name (default: all remotes)

    Returns:
        True if successful, False otherwise
    """
    args = ["fetch"]
    if remote:
        args.append(remote)
    else:
        args.append("--all")

    result = _run_git(*args)
    return result.returncode == 0
