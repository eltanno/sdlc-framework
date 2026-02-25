"""Unit tests for the WorktreeManager in concurrent.py.

Tests cover:
- Worktree path computation and naming
- Worktree creation (ensure_worktrees)
- Worktree update (update_worktree)
- Dirty worktree detection (is_dirty)
- Listing existing worktrees (list_worktrees)
- Error handling for git failures
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


class TestWorktreeManagerPathComputation:
    """Tests for worktree path computation and naming conventions."""

    def test_worktree_path_uses_git_worktrees_directory(self, tmp_path: Path):
        """Given a project root, when computing worktree path, then it uses .git-worktrees/ directory."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        path = manager.worktree_path("ralph-1")

        assert path == tmp_path / ".git-worktrees" / "ralph-1"

    def test_worktree_path_for_multiple_instances(self, tmp_path: Path):
        """Given multiple instance names, when computing paths, then each has correct path."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        for i in range(1, 5):
            path = manager.worktree_path(f"ralph-{i}")
            assert path == tmp_path / ".git-worktrees" / f"ralph-{i}"

    def test_worktree_names_follow_ralph_n_pattern(self, tmp_path: Path):
        """Given a count of N, when generating worktree names, then names follow ralph-1 through ralph-N."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        names = manager.worktree_names(3)

        assert names == ["ralph-1", "ralph-2", "ralph-3"]

    def test_worktree_names_never_include_ralph_0(self, tmp_path: Path):
        """Given any count, when generating names, then ralph-0 is never included (main dir is ralph-0)."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        for count in range(1, 5):
            names = manager.worktree_names(count)
            assert "ralph-0" not in names

    def test_worktree_names_zero_count_returns_empty(self, tmp_path: Path):
        """Given count of 0, when generating names, then empty list returned."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        names = manager.worktree_names(0)

        assert names == []

    def test_worktrees_base_dir(self, tmp_path: Path):
        """Given project root, when getting base dir, then it returns .git-worktrees/."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        assert manager.base_dir == tmp_path / ".git-worktrees"


class TestWorktreeManagerIsDirty:
    """Tests for dirty worktree detection."""

    def test_is_dirty_returns_false_when_clean(self, tmp_path: Path):
        """Given a clean worktree, when checking dirty, then returns False."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            result = manager.is_dirty(tmp_path / ".git-worktrees" / "ralph-1")

        assert result is False

    def test_is_dirty_returns_true_when_uncommitted_changes(self, tmp_path: Path):
        """Given a worktree with uncommitted changes, when checking dirty, then returns True."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=" M some_file.py\n", stderr=""
            )
            result = manager.is_dirty(tmp_path / ".git-worktrees" / "ralph-1")

        assert result is True

    def test_is_dirty_returns_true_when_untracked_files(self, tmp_path: Path):
        """Given a worktree with untracked files, when checking dirty, then returns True."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="?? new_file.py\n", stderr=""
            )
            result = manager.is_dirty(tmp_path / ".git-worktrees" / "ralph-1")

        assert result is True

    def test_is_dirty_calls_git_status_in_worktree_dir(self, tmp_path: Path):
        """Given a worktree path, when checking dirty, then git status runs in that directory."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            manager.is_dirty(wt_path)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        # Verify cwd is set to the worktree path
        assert call_kwargs.kwargs.get("cwd") == wt_path or call_kwargs[1].get("cwd") == wt_path


class TestWorktreeManagerEnsureWorktrees:
    """Tests for ensure_worktrees method."""

    def test_ensure_worktrees_creates_base_dir(self, tmp_path: Path):
        """Given base dir doesn't exist, when ensuring worktrees, then base dir is created."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        base = tmp_path / ".git-worktrees"

        assert not base.exists()

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            manager.ensure_worktrees(count=1, default_branch="develop-working")

        assert base.exists()

    def test_ensure_worktrees_creates_requested_count(self, tmp_path: Path):
        """Given count=3, when ensuring worktrees, then 3 worktrees are created."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        calls_made = []
        def track_calls(*args, **kwargs):
            calls_made.append((args, kwargs))
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("commands.concurrent.subprocess.run", side_effect=track_calls):
            manager.ensure_worktrees(count=3, default_branch="develop-working")

        # Should have at least 3 worktree add calls (plus potentially fetch)
        worktree_add_calls = [
            c for c in calls_made
            if "worktree" in str(c[0]) and "add" in str(c[0])
        ]
        assert len(worktree_add_calls) == 3

    def test_ensure_worktrees_fetches_before_creating(self, tmp_path: Path):
        """Given fresh start, when ensuring worktrees, then git fetch runs first."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        call_order = []
        def track_calls(*args, **kwargs):
            call_order.append(args[0] if args else kwargs.get("args", []))
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("commands.concurrent.subprocess.run", side_effect=track_calls):
            manager.ensure_worktrees(count=1, default_branch="develop-working")

        # First git call should be fetch
        assert any("fetch" in str(c) for c in call_order[:2])

    def test_ensure_worktrees_updates_existing_worktree(self, tmp_path: Path):
        """Given an existing worktree, when ensuring worktrees, then it updates instead of recreating."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        # Pre-create the worktree directory to simulate existing worktree
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"
        wt_path.mkdir(parents=True)
        # Create a .git file to mark it as a valid worktree
        (wt_path / ".git").write_text("gitdir: /fake/path")

        calls_made = []
        def track_calls(*args, **kwargs):
            calls_made.append((args, kwargs))
            # Return clean for is_dirty check
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("commands.concurrent.subprocess.run", side_effect=track_calls):
            manager.ensure_worktrees(count=1, default_branch="develop-working")

        # Should NOT have a "worktree add" call for ralph-1
        worktree_add_calls = [
            c for c in calls_made
            if "worktree" in str(c[0]) and "add" in str(c[0])
        ]
        assert len(worktree_add_calls) == 0

        # Should have a reset or checkout call for update
        update_calls = [
            c for c in calls_made
            if "reset" in str(c[0]) or "checkout" in str(c[0])
        ]
        assert len(update_calls) >= 1


class TestWorktreeManagerUpdateWorktree:
    """Tests for update_worktree method."""

    def test_update_worktree_resets_to_default_branch(self, tmp_path: Path):
        """Given an existing worktree, when updating, then it resets to origin/{default_branch}."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"

        calls_made = []
        def track_calls(*args, **kwargs):
            calls_made.append((args, kwargs))
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("commands.concurrent.subprocess.run", side_effect=track_calls):
            manager.update_worktree(wt_path, "develop-working")

        # Should have fetch + reset --hard to origin/develop-working
        reset_calls = [
            c for c in calls_made
            if "reset" in str(c[0]) and "origin/develop-working" in str(c[0])
        ]
        assert len(reset_calls) >= 1

    def test_update_worktree_runs_in_worktree_dir(self, tmp_path: Path):
        """Given a worktree path, when updating, then git commands run in that directory."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.update_worktree(wt_path, "develop-working")

        # All calls after fetch should have cwd=wt_path
        for c in mock_run.call_args_list:
            cmd = c[0][0] if c[0] else c.kwargs.get("args", [])
            # fetch runs from project root, reset/checkout run from worktree
            if "reset" in str(cmd):
                cwd = c.kwargs.get("cwd") or (c[1].get("cwd") if len(c) > 1 else None)
                assert cwd == wt_path

    def test_update_worktree_warns_on_dirty_state(self, tmp_path: Path):
        """Given a dirty worktree, when updating, then a warning is raised."""
        from commands.concurrent import WorktreeManager, DirtyWorktreeError

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"

        def fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "status" in str(cmd) and "--porcelain" in str(cmd):
                return MagicMock(returncode=0, stdout=" M dirty_file.py\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("commands.concurrent.subprocess.run", side_effect=fake_run):
            with pytest.raises(DirtyWorktreeError) as exc_info:
                manager.update_worktree(wt_path, "develop-working")

        assert "ralph-1" in str(exc_info.value) or "dirty" in str(exc_info.value).lower()


class TestWorktreeManagerListWorktrees:
    """Tests for list_worktrees method."""

    def test_list_worktrees_returns_empty_when_no_base_dir(self, tmp_path: Path):
        """Given no .git-worktrees/ directory, when listing, then empty list returned."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        result = manager.list_worktrees()

        assert result == []

    def test_list_worktrees_returns_existing_worktrees(self, tmp_path: Path):
        """Given existing worktree directories, when listing, then they are returned."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        # Create worktree directories with .git files
        base = tmp_path / ".git-worktrees"
        base.mkdir()
        for name in ["ralph-1", "ralph-2", "ralph-3"]:
            wt = base / name
            wt.mkdir()
            (wt / ".git").write_text("gitdir: /fake/path")

        result = manager.list_worktrees()

        assert sorted(result) == ["ralph-1", "ralph-2", "ralph-3"]

    def test_list_worktrees_ignores_non_ralph_directories(self, tmp_path: Path):
        """Given mixed directories in .git-worktrees/, when listing, then only ralph-N dirs returned."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        base = tmp_path / ".git-worktrees"
        base.mkdir()
        # Valid worktree
        wt = base / "ralph-1"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: /fake/path")
        # Non-worktree directory
        (base / "some-other-dir").mkdir()
        # File (not directory)
        (base / "some-file.txt").write_text("not a worktree")

        result = manager.list_worktrees()

        assert result == ["ralph-1"]

    def test_list_worktrees_only_returns_dirs_with_git_marker(self, tmp_path: Path):
        """Given directories without .git marker, when listing, then they are excluded."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        base = tmp_path / ".git-worktrees"
        base.mkdir()
        # Directory with .git (valid worktree)
        valid = base / "ralph-1"
        valid.mkdir()
        (valid / ".git").write_text("gitdir: /fake/path")
        # Directory without .git (not valid)
        invalid = base / "ralph-2"
        invalid.mkdir()

        result = manager.list_worktrees()

        assert result == ["ralph-1"]


class TestWorktreeManagerCreateWorktree:
    """Tests for _create_worktree internal method."""

    def test_create_worktree_calls_git_worktree_add(self, tmp_path: Path):
        """Given a name and branch, when creating worktree, then git worktree add is called."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager._create_worktree("ralph-1", "develop-working")

        # Find the worktree add call
        worktree_add_calls = [
            c for c in mock_run.call_args_list
            if "worktree" in str(c[0][0]) and "add" in str(c[0][0])
        ]
        assert len(worktree_add_calls) == 1

        # Verify the path and branch are correct
        cmd = worktree_add_calls[0][0][0]
        wt_path = str(tmp_path / ".git-worktrees" / "ralph-1")
        assert wt_path in cmd
        assert "origin/develop-working" in cmd

    def test_create_worktree_raises_on_git_failure(self, tmp_path: Path):
        """Given git worktree add fails, when creating, then error is raised."""
        from commands.concurrent import WorktreeManager, WorktreeError

        manager = WorktreeManager(project_root=tmp_path)

        with patch("commands.concurrent.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
                stderr="fatal: 'ralph-1' is already checked out"
            )
            with pytest.raises(WorktreeError):
                manager._create_worktree("ralph-1", "develop-working")


class TestWorktreeManagerWorktreeExists:
    """Tests for worktree_exists method."""

    def test_worktree_exists_returns_true_for_valid(self, tmp_path: Path):
        """Given a valid worktree directory with .git marker, when checking, then returns True."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"
        wt_path.mkdir(parents=True)
        (wt_path / ".git").write_text("gitdir: /fake/path")

        assert manager.worktree_exists("ralph-1") is True

    def test_worktree_exists_returns_false_when_missing(self, tmp_path: Path):
        """Given no worktree directory, when checking, then returns False."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)

        assert manager.worktree_exists("ralph-1") is False

    def test_worktree_exists_returns_false_without_git_marker(self, tmp_path: Path):
        """Given a directory without .git marker, when checking, then returns False."""
        from commands.concurrent import WorktreeManager

        manager = WorktreeManager(project_root=tmp_path)
        wt_path = tmp_path / ".git-worktrees" / "ralph-1"
        wt_path.mkdir(parents=True)
        # No .git file

        assert manager.worktree_exists("ralph-1") is False
