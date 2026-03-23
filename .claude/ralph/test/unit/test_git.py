"""Unit tests for the Git CLI wrapper module.

Tests cover:
- Branch creation and checkout
- Committing changes
- Pushing to remote
- Repository status checking
- Error handling for missing git
"""

from unittest.mock import MagicMock

import pytest


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    @pytest.mark.parametrize(
        "git_output,expected",
        [
            ("main\n", "main"),
            ("  feature/test  \n", "feature/test"),
            ("very-long-branch-name-123\n", "very-long-branch-name-123"),
            ("main", "main"),  # No newline
            ("  release/v1.0.0\n", "release/v1.0.0"),
            ("hotfix/urgent-fix  ", "hotfix/urgent-fix"),
        ],
    )
    def test_get_current_branch_parses_correctly(
        self, mock_git: MagicMock, git_output: str, expected: str
    ):
        """Given various git outputs, when getting current branch, then branch name is correctly parsed and stripped."""
        from core import git

        mock_git.return_value.stdout = git_output

        result = git.get_current_branch()

        assert result == expected


class TestCreateBranch:
    """Tests for create_branch function."""

    def test_create_branch_creates_new_branch(self, mock_git: MagicMock):
        """Given valid branch name, when creating branch, then branch is created."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = ""

        git.create_branch("feature/TASK-001-implementation")

        mock_git.assert_called_once_with(
            ["git", "checkout", "-b", "feature/TASK-001-implementation"],
            capture_output=True,
            text=True
        )

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

        mock_git.assert_called_once_with(
            ["git", "checkout", "main"],
            capture_output=True,
            text=True
        )

    def test_checkout_branch_raises_on_not_found(self, mock_git: MagicMock):
        """Given branch doesn't exist, when checking out, then error is raised with helpful message."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "error: pathspec 'nonexistent' did not match any file(s)"

        with pytest.raises(git.GitError) as exc_info:
            git.checkout_branch("nonexistent")

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "git checkout nonexistent" in error_msg
        assert "did not match" in error_msg


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

    def test_get_status_comprehensive_parsing(self, mock_git: MagicMock):
        """Given realistic git status output with multiple file types, when getting status, then all types are correctly parsed."""
        from core import git

        mock_git.return_value.stdout = (
            " M modified_unstaged.py\n"
            "M  modified_staged.py\n"
            "MM both_modified.py\n"
            "A  new_file.py\n"
            "D  deleted_staged.py\n"
            " D deleted_unstaged.py\n"
            "?? untracked.py\n"
        )

        result = git.get_status()

        assert not result.is_clean
        assert "modified_unstaged.py" in result.modified
        assert "deleted_unstaged.py" in result.modified
        assert "modified_staged.py" in result.staged
        assert "both_modified.py" in result.staged
        assert "both_modified.py" in result.modified
        assert "new_file.py" in result.staged
        assert "deleted_staged.py" in result.staged
        assert "untracked.py" in result.untracked


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

        mock_git.assert_called_once_with(
            ["git", "add", "file1.py", "file2.py"],
            capture_output=True,
            text=True
        )

    def test_stage_all_stages_everything(self, mock_git: MagicMock):
        """Given stage_all flag, when staging, then all files are staged."""
        from core import git

        mock_git.return_value.returncode = 0

        git.stage_all()

        mock_git.assert_called_once_with(
            ["git", "add", "-A"],
            capture_output=True,
            text=True
        )


class TestCommit:
    """Tests for commit function."""

    def test_commit_creates_commit_with_message(self, mock_git: MagicMock):
        """Given message, when committing, then commit is created."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = "[main abc1234] Test commit\n 1 file changed"

        result = git.commit("Test commit message")

        mock_git.assert_called_once_with(
            ["git", "commit", "-m", "Test commit message"],
            capture_output=True,
            text=True
        )

    @pytest.mark.parametrize(
        "git_output,expected_sha",
        [
            ("[main abc1234] message", "abc1234"),
            ("[feature/long-name 1234567] msg", "1234567"),
            ("[main abc1234def] msg\n 1 file changed", "abc1234def"),
            ("[develop f3e2a1b] Initial commit", "f3e2a1b"),
            # If no match, return full output
            ("No match here", "No match here"),
            ("Weird output without SHA", "Weird output without SHA"),
        ],
    )
    def test_commit_returns_commit_sha(
        self, mock_git: MagicMock, git_output: str, expected_sha: str
    ):
        """Given successful commit with various output formats, when committing, then SHA is correctly parsed."""
        from core import git

        mock_git.return_value.returncode = 0
        mock_git.return_value.stdout = git_output

        result = git.commit("Test message")

        assert result == expected_sha

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

        mock_git.assert_called_once_with(
            ["git", "commit", "-m", "Test message", "--author", "Test User <test@example.com>"],
            capture_output=True,
            text=True
        )


class TestPush:
    """Tests for push function."""

    def test_push_pushes_to_remote(self, mock_git: MagicMock):
        """Given branch, when pushing, then push to remote."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push()

        mock_git.assert_called_once_with(
            ["git", "push"],
            capture_output=True,
            text=True
        )

    def test_push_with_set_upstream(self, mock_git: MagicMock):
        """Given set_upstream flag, when pushing, then -u flag is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push(set_upstream=True)

        args, kwargs = mock_git.call_args
        assert args[0] == ["git", "push", "-u"]

    def test_push_to_specific_remote(self, mock_git: MagicMock):
        """Given remote and branch, when pushing, then they are used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.push(remote="origin", branch="feature/test")

        mock_git.assert_called_once_with(
            ["git", "push", "origin", "feature/test"],
            capture_output=True,
            text=True
        )

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

        mock_git.assert_called_once_with(
            ["git", "pull"],
            capture_output=True,
            text=True
        )


class TestGetLatestCommitSha:
    """Tests for get_latest_commit_sha function."""

    @pytest.mark.parametrize(
        "git_output,expected",
        [
            ("abc123def456\n", "abc123def456"),
            ("a1b2c3d\n", "a1b2c3d"),
            ("  f3e2a1b99  \n", "f3e2a1b99"),
            ("1234567890abcdef", "1234567890abcdef"),  # No newline
        ],
    )
    def test_get_latest_commit_sha_returns_sha(
        self, mock_git: MagicMock, git_output: str, expected: str
    ):
        """Given commits exist with various output formats, when getting SHA, then SHA is correctly parsed."""
        from core import git

        mock_git.return_value.stdout = git_output

        result = git.get_latest_commit_sha()

        assert result == expected


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

        mock_git.assert_called_once_with(
            ["git", "fetch"],
            capture_output=True,
            text=True
        )

    def test_fetch_prunes_stale_refs(self, mock_git: MagicMock):
        """Given prune option, when fetching, then --prune flag is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.fetch(prune=True)

        mock_git.assert_called_once_with(
            ["git", "fetch", "--prune"],
            capture_output=True,
            text=True
        )


class TestMerge:
    """Tests for merge function."""

    def test_merge_calls_git_merge(self, mock_git: MagicMock):
        """Given a branch, when merging, then git merge is called."""
        from core import git

        mock_git.return_value.returncode = 0

        git.merge("origin/main")

        args, kwargs = mock_git.call_args
        assert args[0] == ["git", "merge", "origin/main", "--no-edit"]

    def test_merge_uses_no_edit_by_default(self, mock_git: MagicMock):
        """Given default options, when merging, then --no-edit is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.merge("origin/main")

        mock_git.assert_called_once_with(
            ["git", "merge", "origin/main", "--no-edit"],
            capture_output=True,
            text=True
        )

    def test_merge_with_custom_message(self, mock_git: MagicMock):
        """Given custom message, when merging, then -m flag is used."""
        from core import git

        mock_git.return_value.returncode = 0

        git.merge("origin/main", message="Merge main into feature")

        args, kwargs = mock_git.call_args
        # Message should include both -m and message, may or may not include --no-edit
        assert "git" == args[0][0]
        assert "merge" == args[0][1]
        assert "origin/main" in args[0]
        assert "-m" in args[0]
        assert "Merge main into feature" in args[0]

    def test_merge_raises_on_conflict(self, mock_git: MagicMock):
        """Given merge conflict, when merging, then GitError is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "CONFLICT (content): Merge conflict"

        with pytest.raises(git.GitError) as exc_info:
            git.merge("origin/main")

        assert "CONFLICT" in str(exc_info.value) or "Git command failed" in str(exc_info.value)


class TestRebase:
    """Tests for rebase function."""

    def test_rebase_calls_git_rebase(self, mock_git: MagicMock):
        """Given a target ref, when rebasing, then git rebase is called."""
        from core import git

        mock_git.return_value.returncode = 0

        git.rebase("origin/develop-working")

        mock_git.assert_called_once_with(
            ["git", "rebase", "origin/develop-working"],
            capture_output=True,
            text=True,
        )

    def test_rebase_raises_on_conflict(self, mock_git: MagicMock):
        """Given rebase conflict, when rebasing, then GitError is raised."""
        from core import git

        mock_git.return_value.returncode = 1
        mock_git.return_value.stderr = "CONFLICT (content): Merge conflict in file.py"

        with pytest.raises(git.GitError):
            git.rebase("origin/main")


class TestRebaseAbort:
    """Tests for rebase_abort function."""

    def test_rebase_abort_calls_git_rebase_abort(self, mock_git: MagicMock):
        """Given rebase in progress, when aborting, then git rebase --abort is called."""
        from core import git

        mock_git.return_value.returncode = 0

        git.rebase_abort()

        mock_git.assert_called_once_with(
            ["git", "rebase", "--abort"],
            capture_output=True,
            text=True,
        )

    def test_rebase_abort_does_not_raise_on_no_rebase(self, mock_git: MagicMock):
        """Given no rebase in progress, when aborting, then no error is raised (check=False)."""
        from core import git

        # Simulate "no rebase in progress" (non-zero exit but check=False)
        mock_git.return_value.returncode = 128
        mock_git.return_value.stderr = "fatal: No rebase in progress?"

        # Should not raise because check=False
        git.rebase_abort()
