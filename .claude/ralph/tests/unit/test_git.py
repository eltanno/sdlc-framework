"""Unit tests for the Git CLI wrapper module.

Tests cover:
- Branch creation and checkout
- Committing changes
- Pushing to remote
- Repository status checking
- Error handling for missing git
"""

import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_get_current_branch_returns_branch_name(self, mock_git: MagicMock):
        """Given on a branch, when getting current branch, then branch name is returned."""
        from core import git

        mock_git.return_value.stdout = "main\n"

        result = git.get_current_branch()

        assert result == "main"

    def test_get_current_branch_strips_whitespace(self, mock_git: MagicMock):
        """Given branch name with whitespace, when getting current branch, then whitespace is stripped."""
        from core import git

        mock_git.return_value.stdout = "  feature/test  \n"

        result = git.get_current_branch()

        assert result == "feature/test"


class TestCreateBranch:
    """Tests for create_branch function."""

    def test_create_branch_creates_new_branch(self, mock_git: MagicMock):
        """Given valid branch name, when creating branch, then branch is created."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = ""

        git.create_branch("feature/TASK-001-implementation")

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "checkout" in call_args
        assert "-b" in call_args
        assert "feature/TASK-001-implementation" in call_args

    def test_create_branch_raises_on_failure(self, mock_git: MagicMock):
        """Given branch creation fails, when creating branch, then error is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "fatal: A branch named 'test' already exists"

        with pytest.raises(git.GitError) as exc_info:
            git.create_branch("test")

        assert "already exists" in str(exc_info.value)


class TestCheckoutBranch:
    """Tests for checkout_branch function."""

    def test_checkout_branch_switches_to_branch(self, mock_git: MagicMock):
        """Given existing branch, when checking out, then branch is checked out."""
        from core import git

        mock_git.return_value.returncode = 0

        git.checkout_branch("main")

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "checkout" in call_args
        assert "main" in call_args

    def test_checkout_branch_raises_on_not_found(self, mock_git: MagicMock):
        """Given branch doesn't exist, when checking out, then error is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "error: pathspec 'nonexistent' did not match any file(s)"

        with pytest.raises(git.GitError):
            git.checkout_branch("nonexistent")


class TestBranchExists:
    """Tests for branch_exists function."""

    def test_branch_exists_returns_true_when_exists(self, mock_git: MagicMock):
        """Given branch exists, when checking, then True is returned."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "feature/test\n"

        result = git.branch_exists("feature/test")

        assert result is True

    def test_branch_exists_returns_false_when_not_exists(self, mock_git: MagicMock):
        """Given branch doesn't exist, when checking, then False is returned."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stdout = ""

        result = git.branch_exists("nonexistent")

        assert result is False


class TestGetStatus:
    """Tests for get_status function."""

    def test_get_status_returns_clean_when_no_changes(self, mock_git: MagicMock):
        """Given no uncommitted changes, when getting status, then clean is True."""
        from core import git

        mock_git.return_value.stdout = ""

        result = git.get_status()

        assert result.is_clean is True
        assert result.modified == []
        assert result.untracked == []

    def test_get_status_detects_modified_files(self, mock_git: MagicMock):
        """Given modified files, when getting status, then they are listed."""
        from core import git

        mock_git.return_value.stdout = " M src/file.py\n M src/other.py\n"

        result = git.get_status()

        assert result.is_clean is False
        assert "src/file.py" in result.modified
        assert "src/other.py" in result.modified

    def test_get_status_detects_untracked_files(self, mock_git: MagicMock):
        """Given untracked files, when getting status, then they are listed."""
        from core import git

        mock_git.return_value.stdout = "?? new_file.py\n?? another.py\n"

        result = git.get_status()

        assert result.is_clean is False
        assert "new_file.py" in result.untracked
        assert "another.py" in result.untracked

    def test_get_status_detects_staged_files(self, mock_git: MagicMock):
        """Given staged files, when getting status, then they are listed."""
        from core import git

        mock_git.return_value.stdout = "A  new_file.py\nM  modified.py\n"

        result = git.get_status()

        assert result.is_clean is False
        assert "new_file.py" in result.staged
        assert "modified.py" in result.staged


class TestIsDirty:
    """Tests for is_dirty function."""

    def test_is_dirty_returns_false_when_clean(self, mock_git: MagicMock):
        """Given clean working directory, when checking dirty, then False is returned."""
        from core import git

        mock_git.return_value.stdout = ""

        result = git.is_dirty()

        assert result is False

    def test_is_dirty_returns_true_when_changes_exist(self, mock_git: MagicMock):
        """Given uncommitted changes, when checking dirty, then True is returned."""
        from core import git

        mock_git.return_value.stdout = " M src/file.py\n"

        result = git.is_dirty()

        assert result is True


class TestStageFiles:
    """Tests for stage_files function."""

    def test_stage_files_stages_specific_files(self, mock_git: MagicMock):
        """Given file paths, when staging, then files are staged."""
        from core import git

        mock_git.return_value.returncode = 0

        git.stage_files(["file1.py", "file2.py"])

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "add" in call_args
        assert "file1.py" in call_args
        assert "file2.py" in call_args

    def test_stage_all_stages_everything(self, mock_git: MagicMock):
        """Given stage_all flag, when staging, then all files are staged."""
        from core import git

        mock_git.return_value.returncode = 0

        git.stage_all()

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "add" in call_args
        assert "-A" in call_args


class TestCommit:
    """Tests for commit function."""

    def test_commit_creates_commit_with_message(self, mock_git: MagicMock):
        """Given message, when committing, then commit is created."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "[main abc1234] Test commit\n 1 file changed"

        result = git.commit("Test commit message")

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "commit" in call_args
        assert "-m" in call_args

    def test_commit_returns_commit_sha(self, mock_git: MagicMock):
        """Given successful commit, when committing, then SHA is returned."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "[main abc1234] Test commit\n 1 file changed"

        result = git.commit("Test message")

        assert result is not None
        # Should return some commit info

    def test_commit_raises_on_nothing_to_commit(self, mock_git: MagicMock):
        """Given nothing staged, when committing, then error is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "nothing to commit, working tree clean"

        with pytest.raises(git.GitError) as exc_info:
            git.commit("Test message")

        assert "nothing to commit" in str(exc_info.value).lower()

    def test_commit_with_author(self, mock_git: MagicMock):
        """Given author specified, when committing, then author is set."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "[main abc1234] Test commit"

        git.commit("Test message", author="Test User <test@example.com>")

        call_args = mock_git.call_args[0][0]
        assert "--author" in call_args


class TestPush:
    """Tests for push function."""

    def test_push_pushes_to_remote(self, mock_git: MagicMock):
        """Given branch, when pushing, then push to remote."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push()

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "push" in call_args

    def test_push_with_set_upstream(self, mock_git: MagicMock):
        """Given set_upstream flag, when pushing, then -u flag is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push(set_upstream=True)

        call_args = mock_git.call_args[0][0]
        assert "-u" in call_args or "--set-upstream" in call_args

    def test_push_to_specific_remote(self, mock_git: MagicMock):
        """Given remote and branch, when pushing, then they are used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push(remote="origin", branch="feature/test")

        call_args = mock_git.call_args[0][0]
        assert "origin" in call_args
        assert "feature/test" in call_args

    def test_push_raises_on_conflict(self, mock_git: MagicMock):
        """Given remote has changes, when pushing, then error is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "! [rejected] feature/test -> feature/test (non-fast-forward)"

        with pytest.raises(git.GitError) as exc_info:
            git.push()

        assert "rejected" in str(exc_info.value).lower() or "conflict" in str(exc_info.value).lower()


class TestPull:
    """Tests for pull function."""

    def test_pull_fetches_and_merges(self, mock_git: MagicMock):
        """Given remote has updates, when pulling, then changes are merged."""
        from core import git

        mock_git.return_value.returncode = 0

        git.pull()

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "pull" in call_args


class TestGetLatestCommitSha:
    """Tests for get_latest_commit_sha function."""

    def test_get_latest_commit_sha_returns_sha(self, mock_git: MagicMock):
        """Given commits exist, when getting SHA, then SHA is returned."""
        from core import git

        mock_git.return_value.stdout = "abc123def456\n"

        result = git.get_latest_commit_sha()

        assert result == "abc123def456"


class TestGitError:
    """Tests for GitError exception class."""

    def test_git_error_contains_command(self):
        """Given error, when raised, then command is included."""
        from core import git

        error = git.GitError("Operation failed", command=["git", "commit", "-m", "test"])

        assert "git" in str(error)
        assert "commit" in str(error)

    def test_git_error_contains_stderr(self):
        """Given error with stderr, when raised, then stderr is accessible."""
        from core import git

        error = git.GitError("Failed", stderr="detailed error message")

        assert error.stderr == "detailed error message"


class TestGitNotInstalled:
    """Tests for git not installed scenario."""

    def test_raises_error_when_git_not_installed(self, mock_git: MagicMock):
        """Given git not installed, when any operation attempted, then clear error is raised."""
        from core import git

        mock_git.side_effect = FileNotFoundError("git not found")

        with pytest.raises(git.GitNotInstalledError) as exc_info:
            git.get_current_branch()

        assert "git" in str(exc_info.value).lower()
        assert "install" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


class TestHasRemoteBranch:
    """Tests for has_remote_branch function."""

    def test_has_remote_branch_returns_true_when_exists(self, mock_git: MagicMock):
        """Given remote branch exists, when checking, then True is returned."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "origin/feature/test\n"

        result = git.has_remote_branch("feature/test")

        assert result is True

    def test_has_remote_branch_returns_false_when_not_exists(self, mock_git: MagicMock):
        """Given remote branch doesn't exist, when checking, then False is returned."""
        from core import git

        mock_git.return_value.returncode = 2  # Not found
        mock_git.return_value.stdout = ""

        result = git.has_remote_branch("nonexistent")

        assert result is False


class TestFetch:
    """Tests for fetch function."""

    def test_fetch_updates_remote_refs(self, mock_git: MagicMock):
        """Given remote exists, when fetching, then refs are updated."""
        from core import git

        mock_git.return_value.returncode = 0

        git.fetch()

        call_args = mock_git.call_args[0][0]
        assert "git" in call_args
        assert "fetch" in call_args

    def test_fetch_prunes_stale_refs(self, mock_git: MagicMock):
        """Given prune option, when fetching, then --prune flag is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.fetch(prune=True)

        call_args = mock_git.call_args[0][0]
        assert "--prune" in call_args
