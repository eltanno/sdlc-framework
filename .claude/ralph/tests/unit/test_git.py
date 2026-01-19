"""Unit tests for core/git.py - Git CLI wrapper module.

Tests cover:
- Branch creation and checkout
- Staging and committing changes
- Pushing to remote repositories
- Checking repository status (dirty, branch name)
- Error handling for git not installed

Following TDD: Write failing tests first, then implement.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestBranchOperations:
    """Tests for git branch operations."""

    def test_create_branch_success(self, mocker):
        """Given valid branch name, create_branch creates and checks out branch."""
        from core.git import create_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = create_branch("feature/test-branch")

        assert result is True
        # Should call git checkout -b
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "checkout" in call_args
        assert "-b" in call_args
        assert "feature/test-branch" in call_args

    def test_create_branch_failure(self, mocker):
        """Given branch creation fails, create_branch returns False."""
        from core.git import create_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: A branch named 'existing' already exists",
        )

        result = create_branch("existing")

        assert result is False

    def test_checkout_branch_success(self, mocker):
        """Given existing branch, checkout_branch switches to it."""
        from core.git import checkout_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = checkout_branch("main")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "checkout" in call_args
        assert "main" in call_args

    def test_checkout_branch_failure(self, mocker):
        """Given non-existent branch, checkout_branch returns False."""
        from core.git import checkout_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: pathspec 'missing' did not match"
        )

        result = checkout_branch("missing")

        assert result is False

    def test_get_current_branch(self, mocker):
        """Given a repo, get_current_branch returns current branch name."""
        from core.git import get_current_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="feature/my-branch\n", stderr=""
        )

        result = get_current_branch()

        assert result == "feature/my-branch"

    def test_get_current_branch_detached_head(self, mocker):
        """Given detached HEAD state, get_current_branch returns None."""
        from core.git import get_current_branch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="HEAD is not a symbolic ref"
        )

        result = get_current_branch()

        assert result is None

    def test_branch_exists(self, mocker):
        """Given branch name, branch_exists checks if it exists."""
        from core.git import branch_exists

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = branch_exists("main")

        assert result is True

    def test_branch_exists_remote(self, mocker):
        """Given remote branch, branch_exists checks origin."""
        from core.git import branch_exists

        mock_run = mocker.patch("core.git.subprocess.run")
        # First call (local) returns non-zero, second (remote) returns zero
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr=""),  # local check
            MagicMock(returncode=0, stdout="", stderr=""),  # remote check
        ]

        result = branch_exists("feature/remote-only", check_remote=True)

        assert result is True


class TestCommitOperations:
    """Tests for git commit operations."""

    def test_stage_all_changes(self, mocker):
        """Given changes exist, stage_all adds all changes."""
        from core.git import stage_all

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = stage_all()

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "add" in call_args
        assert "-A" in call_args or "." in call_args

    def test_commit_with_message(self, mocker):
        """Given staged changes, commit creates commit with message."""
        from core.git import commit

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = commit("feat: add new feature")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "commit" in call_args
        assert "-m" in call_args

    def test_commit_with_coauthor(self, mocker):
        """Given coauthor, commit includes Co-Authored-By."""
        from core.git import commit

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = commit("feat: add feature", coauthor="Claude <claude@anthropic.com>")

        assert result is True
        call_args = mock_run.call_args[0][0]
        # Message should include coauthor
        message_index = call_args.index("-m") + 1
        message = call_args[message_index]
        assert "Co-Authored-By" in message

    def test_commit_empty_fails(self, mocker):
        """Given no staged changes, commit fails gracefully."""
        from core.git import commit

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="nothing to commit"
        )

        result = commit("empty commit")

        assert result is False

    def test_get_last_commit_sha(self, mocker):
        """Given commits exist, get_last_commit_sha returns SHA."""
        from core.git import get_last_commit_sha

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="abc123def456\n", stderr=""
        )

        result = get_last_commit_sha()

        assert result == "abc123def456"


class TestPushOperations:
    """Tests for git push operations."""

    def test_push_success(self, mocker):
        """Given valid remote, push succeeds."""
        from core.git import push

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = push()

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "push" in call_args

    def test_push_with_upstream(self, mocker):
        """Given new branch, push with -u sets upstream."""
        from core.git import push

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = push(set_upstream=True, branch="feature/new")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "-u" in call_args
        assert "feature/new" in call_args

    def test_push_conflict(self, mocker):
        """Given remote changes, push fails with conflict."""
        from core.git import push

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="rejected: non-fast-forward"
        )

        result = push()

        assert result is False


class TestStatusOperations:
    """Tests for git status operations."""

    def test_is_dirty_with_changes(self, mocker):
        """Given uncommitted changes, is_dirty returns True."""
        from core.git import is_dirty

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M file.py\n?? new.py\n", stderr=""
        )

        result = is_dirty()

        assert result is True

    def test_is_dirty_clean_repo(self, mocker):
        """Given clean repo, is_dirty returns False."""
        from core.git import is_dirty

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = is_dirty()

        assert result is False

    def test_get_status_returns_file_statuses(self, mocker):
        """Given changes, get_status returns list of changed files."""
        from core.git import get_status

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M src/file.py\n?? new.py\nA  staged.py\n", stderr=""
        )

        result = get_status()

        assert len(result) == 3
        assert any("file.py" in f["file"] for f in result)


class TestDiffOperations:
    """Tests for git diff operations."""

    def test_get_diff_staged(self, mocker):
        """Given staged changes, get_diff returns diff content."""
        from core.git import get_diff

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="diff --git a/file.py b/file.py\n+new line",
            stderr="",
        )

        result = get_diff(staged=True)

        assert "diff --git" in result
        assert "+new line" in result

    def test_get_diff_between_refs(self, mocker):
        """Given two refs, get_diff returns diff between them."""
        from core.git import get_diff

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="diff content", stderr="")

        result = get_diff(ref1="main", ref2="feature")

        assert result == "diff content"
        call_args = mock_run.call_args[0][0]
        assert "main" in call_args
        assert "feature" in call_args


class TestLogOperations:
    """Tests for git log operations."""

    def test_get_recent_commits(self, mocker):
        """Given commits exist, get_recent_commits returns commit list."""
        from core.git import get_recent_commits

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123|feat: add feature|2026-01-19\ndef456|fix: bug fix|2026-01-18\n",
            stderr="",
        )

        result = get_recent_commits(limit=2)

        assert len(result) == 2
        assert result[0]["sha"] == "abc123"
        assert "add feature" in result[0]["message"]


class TestErrorHandling:
    """Tests for git error handling."""

    def test_git_not_installed(self, mocker):
        """Given git not installed, operations raise GitNotFoundError."""
        from core.git import get_current_branch, GitNotFoundError

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.side_effect = FileNotFoundError("git not found")

        with pytest.raises(GitNotFoundError):
            get_current_branch()

    def test_not_a_git_repo(self, mocker):
        """Given not in git repo, operations raise GitError."""
        from core.git import get_current_branch, GitError

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        with pytest.raises(GitError, match="not a git repository"):
            get_current_branch()


class TestFetchOperations:
    """Tests for git fetch operations."""

    def test_fetch_all(self, mocker):
        """Given remote exists, fetch updates local refs."""
        from core.git import fetch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = fetch()

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "fetch" in call_args

    def test_fetch_specific_remote(self, mocker):
        """Given specific remote, fetch only that remote."""
        from core.git import fetch

        mock_run = mocker.patch("core.git.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = fetch(remote="upstream")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "upstream" in call_args
