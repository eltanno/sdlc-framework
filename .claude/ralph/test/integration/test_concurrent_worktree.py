"""Integration tests for WorktreeManager using real git operations.

These tests create temporary git repositories and exercise the full
worktree creation/update lifecycle with real git commands.

Tests cover:
- TC-1: Worktree creation from clean state
- TC-2: Worktree update preserves existing (fetches and resets)
- TC-3: Dirty worktree detection
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _init_bare_repo(path: Path) -> Path:
    """Create a bare git repo to act as 'origin'.

    Args:
        path: Directory to create the bare repo in.

    Returns:
        Path to the bare repo.
    """
    bare = path / "origin.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    return bare


def _init_working_repo(path: Path, bare_repo: Path, branch: str = "main") -> Path:
    """Clone the bare repo and set up an initial commit.

    Args:
        path: Directory for the working clone.
        bare_repo: Path to the bare origin repo.
        branch: Branch name to create.

    Returns:
        Path to the working repo.
    """
    working = path / "project"
    subprocess.run(
        ["git", "clone", str(bare_repo), str(working)],
        check=True,
        capture_output=True,
    )
    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=working, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=working, check=True, capture_output=True,
    )

    # Create initial commit on default branch
    readme = working / "README.md"
    readme.write_text("# Test Project\n")
    subprocess.run(["git", "add", "README.md"], cwd=working, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=working, check=True, capture_output=True,
    )

    # Rename to desired branch if needed
    current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=working, capture_output=True, text=True,
    ).stdout.strip()

    if current != branch:
        subprocess.run(
            ["git", "branch", "-m", current, branch],
            cwd=working, check=True, capture_output=True,
        )

    # Push to origin
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=working, check=True, capture_output=True,
    )

    return working


def _get_head_sha(repo_path: Path) -> str:
    """Get HEAD commit SHA for a repo."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


class TestWorktreeCreation:
    """Integration tests for creating worktrees from clean state (TC-1)."""

    def test_ensure_worktrees_creates_valid_worktrees(self, tmp_path: Path):
        """Given a clean project, when ensuring 3 worktrees, then 3 valid worktrees exist."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=3, default_branch="develop-working")

        # Verify 3 worktrees were created
        assert len(paths) == 3

        # Verify each is a valid directory with .git marker
        for i, wt_path in enumerate(paths, 1):
            assert wt_path.is_dir(), f"ralph-{i} directory should exist"
            assert (wt_path / ".git").exists(), f"ralph-{i} should have .git marker"
            assert wt_path.name == f"ralph-{i}"

    def test_ensure_worktrees_at_correct_commit(self, tmp_path: Path):
        """Given a project with commits, when creating worktrees, then they are at origin/develop-working."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        # Get the expected commit SHA
        expected_sha = _get_head_sha(project)

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=2, default_branch="develop-working")

        # Verify each worktree is at the expected commit
        for wt_path in paths:
            wt_sha = _get_head_sha(wt_path)
            assert wt_sha == expected_sha, f"{wt_path.name} should be at origin/develop-working HEAD"

    def test_ensure_worktrees_in_git_worktrees_directory(self, tmp_path: Path):
        """Given a project, when creating worktrees, then they are in .git-worktrees/ directory."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        manager.ensure_worktrees(count=1, default_branch="develop-working")

        assert (project / ".git-worktrees" / "ralph-1").is_dir()

    def test_list_worktrees_after_creation(self, tmp_path: Path):
        """Given worktrees were created, when listing, then all are returned."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        manager.ensure_worktrees(count=3, default_branch="develop-working")

        result = manager.list_worktrees()

        assert result == ["ralph-1", "ralph-2", "ralph-3"]


class TestWorktreeUpdate:
    """Integration tests for updating existing worktrees (TC-2)."""

    def test_update_moves_worktree_to_latest_commit(self, tmp_path: Path):
        """Given a new commit on origin, when updating worktree, then it moves to new commit."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=1, default_branch="develop-working")

        # Record the initial worktree SHA
        initial_sha = _get_head_sha(paths[0])

        # Add a new commit in the main project and push
        new_file = project / "new_feature.py"
        new_file.write_text("# New feature\n")
        subprocess.run(["git", "add", "new_feature.py"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new feature"],
            cwd=project, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "develop-working"],
            cwd=project, check=True, capture_output=True,
        )

        new_sha = _get_head_sha(project)
        assert new_sha != initial_sha, "New commit should have a different SHA"

        # Now update the worktree
        manager.ensure_worktrees(count=1, default_branch="develop-working")

        # Verify worktree moved to the new commit
        updated_sha = _get_head_sha(paths[0])
        assert updated_sha == new_sha, "Worktree should be at the latest commit"

    def test_ensure_worktrees_does_not_recreate_existing(self, tmp_path: Path):
        """Given existing worktrees, when ensuring same count, then no new worktrees created."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)

        # First creation
        paths_1 = manager.ensure_worktrees(count=2, default_branch="develop-working")

        # Second call -- should update, not recreate
        paths_2 = manager.ensure_worktrees(count=2, default_branch="develop-working")

        # Paths should be the same
        assert paths_1 == paths_2

        # Should still only have 2 worktrees
        assert len(manager.list_worktrees()) == 2


class TestDirtyWorktreeDetection:
    """Integration tests for dirty worktree detection (TC-3)."""

    def test_dirty_worktree_raises_error_on_update(self, tmp_path: Path):
        """Given a worktree with uncommitted changes, when updating, then DirtyWorktreeError raised."""
        from commands.concurrent import DirtyWorktreeError, WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=1, default_branch="develop-working")

        # Make the worktree dirty by adding an uncommitted file
        dirty_file = paths[0] / "uncommitted.txt"
        dirty_file.write_text("I am dirty\n")

        # Now try to update -- should raise DirtyWorktreeError
        with pytest.raises(DirtyWorktreeError) as exc_info:
            manager.update_worktree(paths[0], "develop-working")

        assert "uncommitted" in str(exc_info.value).lower() or "dirty" in str(exc_info.value).lower()

    def test_is_dirty_detects_untracked_files(self, tmp_path: Path):
        """Given untracked files in worktree, when checking dirty, then returns True."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=1, default_branch="develop-working")

        # Add untracked file
        (paths[0] / "untracked.txt").write_text("untracked\n")

        assert manager.is_dirty(paths[0]) is True

    def test_is_dirty_returns_false_for_clean_worktree(self, tmp_path: Path):
        """Given a clean worktree, when checking dirty, then returns False."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=1, default_branch="develop-working")

        assert manager.is_dirty(paths[0]) is False

    def test_worktrees_remain_on_disk_after_completion(self, tmp_path: Path):
        """Given worktrees were created, when operations complete, then worktrees remain on disk."""
        from commands.concurrent import WorktreeManager

        bare = _init_bare_repo(tmp_path)
        project = _init_working_repo(tmp_path, bare, branch="develop-working")

        manager = WorktreeManager(project_root=project)
        paths = manager.ensure_worktrees(count=2, default_branch="develop-working")

        # Worktrees should still exist after ensure_worktrees returns
        for wt_path in paths:
            assert wt_path.exists(), f"{wt_path.name} should remain on disk"
            assert (wt_path / ".git").exists(), f"{wt_path.name} should still be a valid worktree"
