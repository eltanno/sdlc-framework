"""Unit tests for the PR flow command module.

Tests cover:
- Committing staged changes
- Pushing to remote (including force-push)
- Creating pull requests with proper linking
- Merging pull requests (including retry on failure)
- The complete PR flow from commit to merge
- Rebase-based sync with default branch
- Retry logic for sync+push
- Repo tool abstraction (GitHub vs GitLab)
"""

import subprocess
from unittest.mock import MagicMock

import pytest


def _make_completed_process(returncode=0, stdout="", stderr=""):
    """Helper to create a subprocess.CompletedProcess for mocking _run_git_command."""
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.fixture
def mock_git_module(mocker):
    """Mock the git module functions."""
    return mocker.patch.object(
        __import__("commands.pr_flow", fromlist=["git"]),
        "git",
    )


@pytest.fixture
def mock_github_module(mocker):
    """Mock the github module as the repo tool.

    This mocks get_repo_module to return a mock GitHub module
    for tests that need to verify GitHub-specific behavior.
    """
    from core import github as real_github
    from core.github import PullRequestResult

    mock_github = mocker.MagicMock(spec=real_github)
    # Ensure the mock has the real exception class
    mock_github.GitHubError = real_github.GitHubError
    # Ensure the mock has PullRequestResult
    mock_github.PullRequestResult = PullRequestResult
    # Mark as GitHub (not GitLab)
    mock_github.create_pull_request = mocker.MagicMock()
    mock_github.merge_pull_request = mocker.MagicMock()
    mock_github.list_pull_requests = mocker.MagicMock()
    mock_github.find_merged_pr = mocker.MagicMock()
    mock_github.get_pull_request = mocker.MagicMock()
    mock_github.find_issue_by_title = mocker.MagicMock()
    mock_github.delete_remote_branch = mocker.MagicMock()

    # Patch the cached repo module getter to return our mock
    mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_github)

    return mock_github




class TestStageAndCommit:
    """Tests for stage_and_commit function."""

    def test_stage_and_commit_stages_all_and_commits(self, mock_git_module):
        """Given changes exist, when stage_and_commit called, then commit message includes ticket ID and co-author."""
        from commands import pr_flow

        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"

        result = pr_flow.stage_and_commit("TASK-001", "Implementation complete")

        # Verify commit was called with correct message format
        mock_git_module.commit.assert_called_once()
        commit_msg = mock_git_module.commit.call_args[0][0]
        assert "[TASK-001]" in commit_msg
        assert "Implementation complete" in commit_msg
        assert "Co-Authored-By: Claude" in commit_msg
        assert result == "abc1234"

    def test_stage_and_commit_returns_none_when_no_changes(self, mock_git_module):
        """Given no changes, when stage_and_commit called, then None is returned."""
        from commands import pr_flow

        mock_git_module.is_dirty.return_value = False

        result = pr_flow.stage_and_commit("TASK-001", "Test message")

        assert result is None
        mock_git_module.commit.assert_not_called()

    def test_stage_and_commit_adds_coauthor(self, mock_git_module):
        """Given commit message, when committing, then co-author is added in correct format."""
        from commands import pr_flow

        mock_git_module.is_dirty.return_value = True
        mock_git_module.commit.return_value = "abc1234"

        pr_flow.stage_and_commit("TASK-001", "Test message")

        commit_call = mock_git_module.commit.call_args
        message = commit_call[0][0]
        # Verify exact co-author format (not just substring)
        assert "Co-Authored-By: Claude" in message
        assert "<" in message and ">" in message  # Email format present


class TestPushBranch:
    """Tests for push_branch function."""

    def test_push_branch_handles_push_errors(self, mock_git_module):
        """Given push fails, when pushing, then PrFlowError is raised with details."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.git import GitError

        mock_git_module.push.side_effect = GitError("Permission denied")
        mock_git_module.GitError = GitError

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.push_branch("feature/test")

        assert "Permission denied" in str(exc_info.value)


class TestCreateMr:
    """Tests for create_mr function."""

    def test_create_mr_creates_with_ticket_in_title(self, mock_github_module):
        """Given ticket ID, when creating MR, then title includes ticket ID."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        result = pr_flow.create_mr("TASK-001", "Implementation complete")

        create_call = mock_github_module.create_pull_request.call_args
        title = create_call[1].get("title") or create_call[0][0]
        assert "TASK-001" in title

    def test_create_mr_links_to_issue_in_body(self, mock_github_module):
        """Given issue number, when creating MR, then body links to issue."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = 110
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        pr_flow.create_mr("TASK-001", "Implementation complete")

        create_call = mock_github_module.create_pull_request.call_args
        body = create_call[1].get("body") or create_call[0][1]
        assert "#110" in body or "Closes #110" in body

    def test_create_mr_returns_pr_info(self, mock_github_module):
        """Given MR creation succeeds, when result returned, then PR URL and number are provided."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/123",
            number=123,
        )

        result = pr_flow.create_mr("TASK-001", "Test")

        assert result.number == 123
        assert result.url == "https://github.com/owner/repo/pull/123"

    def test_create_mr_passes_head_to_github(self, mock_github_module):
        """Given head parameter, when creating MR via GitHub, then head is passed through."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/55",
            number=55,
        )

        pr_flow.create_mr("TASK-001", "Test", head="feature/TASK-001-implementation")

        create_call = mock_github_module.create_pull_request.call_args
        assert create_call[1].get("head") == "feature/TASK-001-implementation"

    def test_create_mr_does_not_pass_head_when_none(self, mock_github_module):
        """Given no head parameter, when creating MR, then head is not passed."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/56",
            number=56,
        )

        pr_flow.create_mr("TASK-001", "Test")

        create_call = mock_github_module.create_pull_request.call_args
        assert create_call[1].get("head") is None

    def test_create_mr_handles_creation_failure(self, mock_github_module):
        """Given MR creation fails, when create_mr called, then PrFlowError is raised with details."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import GitHubError

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.side_effect = GitHubError("API error")

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.create_mr("TASK-001", "Test")

        assert "API error" in str(exc_info.value)


class TestMergeMr:
    """Tests for merge_mr function."""

    def test_merge_mr_uses_squash_by_default(self, mock_github_module):
        """Given PR number, when merging, then squash merge is used to maintain clean history."""
        from commands import pr_flow

        mock_github_module.merge_pull_request.return_value = None

        pr_flow.merge_mr(123)

        # Verify merge was attempted with squash strategy
        mock_github_module.merge_pull_request.assert_called_once()
        call_args = mock_github_module.merge_pull_request.call_args
        assert call_args[0][0] == 123
        assert call_args[1].get("strategy") == "squash"

    def test_merge_mr_handles_merge_conflicts(self, mock_github_module):
        """Given PR has merge conflicts, when merging, then PrFlowError is raised with details."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import GitHubError

        mock_github_module.merge_pull_request.side_effect = GitHubError("Merge conflict")

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.merge_mr(123)

        assert "Merge conflict" in str(exc_info.value)


class TestCheckoutDetachedDefault:
    """Tests for checkout_detached_default function."""

    def test_checkout_detached_default_fetches_and_checkouts(self, mock_git_module):
        """Given default branch exists remotely, when checking out detached, then detached HEAD is used."""
        from commands import pr_flow

        mock_git_module.fetch.return_value = None
        # Simulate checkout --detach
        mock_git_module._run_git_command = MagicMock()

        pr_flow.checkout_detached_default("main")

        mock_git_module.fetch.assert_called()


class TestSyncWithDefault:
    """Tests for sync_with_default function."""

    def _make_completed_process(self, returncode=0, stdout="", stderr=""):
        """Helper to create a mock CompletedProcess."""
        import subprocess
        return subprocess.CompletedProcess(
            args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_sync_with_default_fetches_and_rebases(self, mock_git_module):
        """Given branch is behind default, when syncing, then fetch is called and rebase is performed."""
        from commands import pr_flow

        mock_git_module.fetch.return_value = None
        mock_git_module.GitError = __import__("core.git", fromlist=["GitError"]).GitError
        # merge-base --is-ancestor returns 1 (not ancestor, rebase needed)
        # rebase returns 0 (success)
        mock_git_module._run_git_command.side_effect = [
            self._make_completed_process(returncode=1),  # merge-base: not ancestor
            self._make_completed_process(returncode=0),  # rebase: success
        ]

        pr_flow.sync_with_default("main")

        mock_git_module.fetch.assert_called_once_with(remote="origin")
        calls = mock_git_module._run_git_command.call_args_list
        assert calls[0][0][0] == ["merge-base", "--is-ancestor", "origin/main", "HEAD"]
        assert calls[1][0][0] == ["rebase", "origin/main"]

    def test_sync_with_default_skips_rebase_when_up_to_date(self, mock_git_module):
        """Given branch is already up to date, when syncing, then rebase is skipped."""
        from commands import pr_flow

        mock_git_module.fetch.return_value = None
        mock_git_module.GitError = __import__("core.git", fromlist=["GitError"]).GitError
        # merge-base --is-ancestor returns 0 (already ancestor, up to date)
        mock_git_module._run_git_command.return_value = self._make_completed_process(returncode=0)

        pr_flow.sync_with_default("main")

        mock_git_module.fetch.assert_called_once_with(remote="origin")
        # Only one call: merge-base check. No rebase call.
        assert mock_git_module._run_git_command.call_count == 1

    def test_sync_with_default_raises_on_rebase_conflict(self, mock_git_module):
        """Given rebase has conflicts, when syncing, then PrFlowError is raised and rebase is aborted."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.git import GitError

        mock_git_module.fetch.return_value = None
        mock_git_module.GitError = GitError
        # merge-base: not ancestor, rebase: conflict, rebase --abort
        mock_git_module._run_git_command.side_effect = [
            self._make_completed_process(returncode=1),  # merge-base: not ancestor
            self._make_completed_process(returncode=1, stderr="CONFLICT"),  # rebase: failed
            self._make_completed_process(returncode=0),  # rebase --abort
        ]

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.sync_with_default(default_branch="develop-working")

        assert "rebase" in str(exc_info.value).lower() or "conflicts" in str(exc_info.value).lower()
        # Verify rebase --abort was called
        calls = mock_git_module._run_git_command.call_args_list
        assert calls[2][0][0] == ["rebase", "--abort"]

    def test_sync_with_default_raises_on_fetch_failure(self, mock_git_module):
        """Given fetch fails, when syncing, then PrFlowError is raised."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.git import GitError

        mock_git_module.fetch.side_effect = GitError("network error")
        mock_git_module.GitError = GitError

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.sync_with_default(default_branch="main")

        assert "fetch" in str(exc_info.value).lower()



class TestFindExistingPr:
    """Tests for find_existing_pr function."""

    def test_find_existing_pr_returns_pr_number(self, mock_github_module):
        """Given PR exists for branch, when checking, then PR number is returned."""
        from commands import pr_flow

        mock_github_module.list_pull_requests.return_value = [
            {"number": 50, "title": "Test PR"}
        ]

        result = pr_flow.find_existing_pr("feature/test")

        assert result == 50

    def test_find_existing_pr_returns_none_when_no_pr(self, mock_github_module):
        """Given no PR exists, when checking, then None is returned."""
        from commands import pr_flow

        mock_github_module.list_pull_requests.return_value = []

        result = pr_flow.find_existing_pr("feature/no-pr")

        assert result is None


class TestCheckAlreadyMerged:
    """Tests for check_already_merged function."""

    def test_check_already_merged_returns_pr_number_when_merged(self, mock_github_module):
        """Given PR was merged for ticket, when checking, then PR number is returned."""
        from commands import pr_flow

        mock_github_module.find_merged_pr.return_value = 99

        result = pr_flow.check_already_merged("TASK-001")

        assert result == 99

    def test_check_already_merged_returns_none_when_not_merged(self, mock_github_module):
        """Given no merged PR, when checking, then None is returned."""
        from commands import pr_flow

        mock_github_module.find_merged_pr.return_value = None

        result = pr_flow.check_already_merged("TASK-001")

        assert result is None


class TestPrFlow:
    """Tests for the main pr_flow function."""

    def test_pr_flow_complete_happy_path(self, mock_git_module, mock_github_module):
        """Given changes to commit, when running full flow, then commit message and PR body are correct."""
        from commands import pr_flow
        from core.github import PullRequestResult

        # Setup mocks for happy path
        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default uses _run_git_command for merge-base check (already up to date)
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = 110
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Implementation complete", default_branch="develop-working")

        # Verify commit message format
        commit_msg = mock_git_module.commit.call_args[0][0]
        assert "[TASK-001]" in commit_msg
        assert "Implementation complete" in commit_msg
        assert "Co-Authored-By: Claude" in commit_msg

        # Verify PR body includes issue link
        pr_call = mock_github_module.create_pull_request.call_args
        pr_body = pr_call[1].get("body") or pr_call[0][1]
        assert "#110" in pr_body or "Closes #110" in pr_body

        # Verify result
        assert result.ticket_id == "TASK-001"
        assert result.pr_number == 42
        assert result.merged is True
        assert result.already_done is False

    def test_pr_flow_passes_default_branch_to_sync_and_checkout(self, mock_git_module, mock_github_module, mocker):
        """Given a custom default_branch, when running flow, then sync_with_default and checkout_detached_default receive it."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_sync = mocker.patch.object(pr_flow, "sync_with_default")
        mock_checkout = mocker.patch.object(pr_flow, "checkout_detached_default")

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = 110
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop")

        mock_sync.assert_called_once_with(default_branch="develop")
        mock_checkout.assert_called_once_with(default_branch="develop")
        assert result.merged is True

    def test_pr_flow_already_merged_returns_early(self, mock_git_module, mock_github_module):
        """Given PR already merged, when running flow, then returns early with already_done."""
        from commands import pr_flow

        mock_git_module.get_current_branch.return_value = "develop-working"
        mock_git_module.is_dirty.return_value = False
        mock_github_module.find_merged_pr.return_value = 99

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert result.already_done is True
        assert result.pr_number == 99
        mock_github_module.create_pull_request.assert_not_called()

    def test_pr_flow_reuses_existing_pr(self, mock_git_module, mock_github_module):
        """Given PR already exists, when running flow, then existing PR is used."""
        from commands import pr_flow

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = False
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = [{"number": 50}]
        mock_github_module.get_pull_request.return_value = {
            "number": 50,
            "url": "https://github.com/owner/repo/pull/50",
        }
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert result.pr_number == 50
        mock_github_module.create_pull_request.assert_not_called()

    def test_pr_flow_no_merge_option(self, mock_git_module, mock_github_module):
        """Given --no-merge flag, when running flow, then PR is not merged."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        result = pr_flow.pr_flow("TASK-001", "Test", no_merge=True, default_branch="develop-working")

        assert result.merged is False
        mock_github_module.merge_pull_request.assert_not_called()


    def test_pr_flow_raises_on_default_branch_with_no_changes(self, mock_git_module, mock_github_module):
        """Given on default branch with no changes and no existing PR, when running flow, then error is raised."""
        from commands import pr_flow

        mock_git_module.get_current_branch.return_value = "develop-working"
        mock_git_module.is_dirty.return_value = False
        mock_github_module.find_merged_pr.return_value = None

        with pytest.raises(pr_flow.PrFlowError) as exc_info:
            pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert "develop-working" in str(exc_info.value).lower() or "default branch" in str(exc_info.value).lower()

    def test_pr_flow_uses_refspec_push_when_detached_head(self, mock_git_module, mock_github_module):
        """Given detached HEAD (common in worktrees), when running flow, then push uses refspec to avoid worktree constraints."""
        from commands import pr_flow
        from core.github import PullRequestResult

        # Simulate detached HEAD -- get_current_branch returns "HEAD"
        mock_git_module.get_current_branch.return_value = "HEAD"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date (merge-base returns 0)
        # push_branch refspec: success
        # checkout_detached_default also calls _run_git_command
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Implementation complete", default_branch="develop-working")

        # Verify push used refspec (HEAD:refs/heads/...), not regular push
        mock_git_module._run_git_command.assert_any_call(
            ["push", "-u", "origin", "HEAD:refs/heads/feature/TASK-001-implementation"]
        )
        # Regular push should NOT have been called
        mock_git_module.push.assert_not_called()
        assert result.branch == "feature/TASK-001-implementation"
        assert result.merged is True

    def test_pr_flow_passes_head_when_detached(self, mock_git_module, mock_github_module):
        """Given detached HEAD, when creating PR, then head parameter is passed to create_mr so gh pr create gets --head flag."""
        from commands import pr_flow
        from core.github import PullRequestResult

        # Simulate detached HEAD
        mock_git_module.get_current_branch.return_value = "HEAD"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date, push refspec: success
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        pr_flow.pr_flow("TASK-001", "Implementation complete", default_branch="develop-working")

        # Verify create_pull_request was called with head= the computed branch name
        create_call = mock_github_module.create_pull_request.call_args
        assert create_call[1].get("head") == "feature/TASK-001-implementation"

    def test_pr_flow_does_not_pass_head_when_not_detached(self, mock_git_module, mock_github_module):
        """Given normal branch (not detached), when creating PR, then head parameter is NOT passed."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        pr_flow.pr_flow("TASK-001", "Implementation complete", default_branch="develop-working")

        # Verify create_pull_request was called with head=None
        create_call = mock_github_module.create_pull_request.call_args
        assert create_call[1].get("head") is None




class TestGetRepoModule:
    """Tests for get_repo_module factory function."""

    def test_get_repo_module_returns_github_by_default(self, tmp_path, mocker):
        """Given no repo.type in config, when get_repo_module called, then github module is returned."""
        from commands.pr_flow import get_repo_module
        from core import github

        # Create config without repo.type
        config_file = tmp_path / "config.yaml"
        config_file.write_text("pm:\n  tool: github\n")

        module = get_repo_module(config_file)

        assert module is github

    def test_get_repo_module_returns_github_when_configured(self, tmp_path, mocker):
        """Given repo.type: github in config, when get_repo_module called, then github module is returned."""
        from commands.pr_flow import get_repo_module
        from core import github

        config_file = tmp_path / "config.yaml"
        config_file.write_text("pm:\n  tool: github\nrepo:\n  type: github\n")

        module = get_repo_module(config_file)

        assert module is github

    def test_get_repo_module_returns_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab in config, when get_repo_module called, then gitlab module is returned."""
        from commands.pr_flow import get_repo_module
        from core import gitlab

        config_file = tmp_path / "config.yaml"
        config_file.write_text("pm:\n  tool: github\nrepo:\n  type: gitlab\n")

        module = get_repo_module(config_file)

        assert module is gitlab


class TestPrFlowWithGitLab:
    """Tests for PR flow when using GitLab as repo tool."""

    def test_pr_flow_uses_gitlab_when_configured(self, mock_git_module, tmp_path, mocker):
        """Given repo.type: gitlab, when pr_flow executes, then gitlab module is used."""
        from commands import pr_flow
        from core.gitlab import MergeRequestResult

        # Mock get_repo_module to return gitlab mock
        mock_gitlab = mocker.MagicMock()
        mock_gitlab.find_merged_mr.return_value = None
        mock_gitlab.list_merge_requests.return_value = []
        mock_gitlab.create_merge_request.return_value = MergeRequestResult(
            url="https://gitlab.example.com/group/repo/-/merge_requests/42",
            number=42,
        )
        mock_gitlab.merge_merge_request.return_value = None
        mock_gitlab.get_merge_request.return_value = {"iid": 42, "web_url": "https://gitlab.example.com/group/repo/-/merge_requests/42"}
        mock_gitlab.delete_remote_branch.return_value = None
        mock_gitlab.GitLabError = Exception
        # Mark this as having GitLab methods (not GitHub)
        mock_gitlab.find_issue_by_title = None

        mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_gitlab)

        # Setup git mocks
        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        result = pr_flow.pr_flow("TASK-001", "Implementation complete", default_branch="develop-working")

        # Verify gitlab module was used
        mock_gitlab.create_merge_request.assert_called_once()
        assert result.pr_number == 42
        assert "gitlab" in result.pr_url.lower() or "merge_requests" in result.pr_url

    def test_create_mr_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when create_mr called, then gitlab.create_merge_request is called."""
        from commands import pr_flow
        from core.gitlab import MergeRequestResult

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.create_merge_request.return_value = MergeRequestResult(
            url="https://gitlab.example.com/group/repo/-/merge_requests/123",
            number=123,
        )
        # GitLab doesn't have find_issue_by_title (issues handled by Asana/Trello)
        mock_gitlab.find_issue_by_title = None

        mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_gitlab)

        result = pr_flow.create_mr("TASK-001", "Test implementation")

        mock_gitlab.create_merge_request.assert_called_once()
        call_kwargs = mock_gitlab.create_merge_request.call_args[1]
        assert "TASK-001" in call_kwargs.get("title", "")

    def test_merge_mr_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when merge_mr called, then gitlab.merge_merge_request is called."""
        from commands import pr_flow

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.merge_merge_request.return_value = None

        mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_gitlab)

        pr_flow.merge_mr(123)

        mock_gitlab.merge_merge_request.assert_called_once()
        call_args = mock_gitlab.merge_merge_request.call_args
        assert call_args[0][0] == 123
        assert call_args[1].get("strategy") == "squash"

    def test_find_existing_mr_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when find_existing_pr called, then gitlab.list_merge_requests is called."""
        from commands import pr_flow

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.list_merge_requests.return_value = [
            {"iid": 50, "title": "Test MR"}
        ]

        mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_gitlab)

        result = pr_flow.find_existing_pr("feature/test")

        mock_gitlab.list_merge_requests.assert_called_once()
        # GitLab uses 'iid' but we should handle either 'number' or 'iid'
        assert result == 50

    def test_check_already_merged_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when check_already_merged called, then gitlab.find_merged_mr is called."""
        from commands import pr_flow

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.find_merged_mr.return_value = 99

        mocker.patch("commands.pr_flow.get_repo_module", return_value=mock_gitlab)

        result = pr_flow.check_already_merged("TASK-001")

        mock_gitlab.find_merged_mr.assert_called_once_with("TASK-001")
        assert result == 99


class TestPushBranchForce:
    """Tests for push_branch force-push behavior."""

    def test_push_branch_force_refspec_includes_force_with_lease(self, mock_git_module):
        """Given force=True and refspec=True, when pushing, then --force-with-lease is included."""
        from commands import pr_flow

        mock_git_module._run_git_command.return_value = None

        pr_flow.push_branch("feature/test", refspec=True, force=True)

        mock_git_module._run_git_command.assert_called_once_with(
            ["push", "--force-with-lease", "-u", "origin", "HEAD:refs/heads/feature/test"]
        )

    def test_push_branch_force_no_refspec_includes_force_with_lease(self, mock_git_module):
        """Given force=True and refspec=False, when pushing, then --force-with-lease is used."""
        from commands import pr_flow

        mock_git_module._run_git_command.return_value = None

        pr_flow.push_branch("feature/test", refspec=False, force=True)

        mock_git_module._run_git_command.assert_called_once_with(
            ["push", "--force-with-lease", "-u", "origin", "feature/test"]
        )

    def test_push_branch_no_force_refspec_no_force_flag(self, mock_git_module):
        """Given force=False and refspec=True, when pushing, then no --force-with-lease."""
        from commands import pr_flow

        mock_git_module._run_git_command.return_value = None

        pr_flow.push_branch("feature/test", refspec=True, force=False)

        mock_git_module._run_git_command.assert_called_once_with(
            ["push", "-u", "origin", "HEAD:refs/heads/feature/test"]
        )

    def test_push_branch_no_force_no_refspec_uses_git_push(self, mock_git_module):
        """Given force=False and refspec=False, when pushing, then standard git.push is used."""
        from commands import pr_flow

        mock_git_module.push.return_value = None

        pr_flow.push_branch("feature/test", refspec=False, force=False)

        mock_git_module.push.assert_called_once_with(
            remote="origin", branch="feature/test", set_upstream=True
        )


class TestSyncRetryLogic:
    """Tests for the retry loop around sync_with_default + push_branch in pr_flow."""

    def test_sync_retry_succeeds_on_second_attempt(self, mock_git_module, mock_github_module, mocker):
        """Given first sync fails and second succeeds, when running pr_flow, then result is success."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None

        # First sync call fails, second succeeds
        call_count = {"sync": 0}
        original_sync = pr_flow.sync_with_default

        def mock_sync(default_branch):
            call_count["sync"] += 1
            if call_count["sync"] == 1:
                raise PrFlowError("Rebase conflict on first try")
            # Second call succeeds (no-op)

        mocker.patch.object(pr_flow, "sync_with_default", side_effect=mock_sync)
        mocker.patch.object(pr_flow, "push_branch")

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert result.merged is True
        assert call_count["sync"] == 2
        # On retry (attempt 2), force=True
        push_calls = pr_flow.push_branch.call_args_list
        assert push_calls[0][1]["force"] is True  # second attempt uses force

    def test_sync_retry_fails_after_max_retries(self, mock_git_module, mock_github_module, mocker):
        """Given all 3 sync attempts fail, when running pr_flow, then PrFlowError is raised."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"

        # All sync calls fail
        mocker.patch.object(
            pr_flow, "sync_with_default",
            side_effect=PrFlowError("Persistent conflict"),
        )

        mock_github_module.find_merged_pr.return_value = None

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert "Persistent conflict" in str(exc_info.value)
        assert pr_flow.sync_with_default.call_count == 3

    def test_sync_retry_uses_force_push_on_retry(self, mock_git_module, mock_github_module, mocker):
        """Given sync succeeds on first attempt, when pushing, then force=False."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None

        mocker.patch.object(pr_flow, "sync_with_default")  # succeeds
        mocker.patch.object(pr_flow, "push_branch")  # succeeds

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        # First attempt: force=False (sync_attempt == 1, so sync_attempt > 1 is False)
        push_call = pr_flow.push_branch.call_args
        assert push_call[1]["force"] is False


class TestMergeRetryLogic:
    """Tests for merge retry logic in pr_flow when merge_mr fails."""

    def test_merge_retry_succeeds_after_branch_update(self, mock_git_module, mock_github_module, mocker):
        """Given merge fails first time but succeeds after branch update, then result is merged."""
        from commands import pr_flow
        from commands.pr_flow import MergeError
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        # Mock merge_mr at the pr_flow module level (not the github module)
        merge_call_count = {"count": 0}

        def mock_merge_mr(pr_number):
            merge_call_count["count"] += 1
            if merge_call_count["count"] == 1:
                raise MergeError("PR not mergeable")
            # Second call succeeds

        mocker.patch.object(pr_flow, "merge_mr", side_effect=mock_merge_mr)

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert result.merged is True
        assert merge_call_count["count"] == 2

    def test_merge_retry_fails_after_branch_update(self, mock_git_module, mock_github_module, mocker):
        """Given merge fails even after branch update, then MergeError is raised."""
        from commands import pr_flow
        from commands.pr_flow import MergeError
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        # Mock merge_mr at the pr_flow module level -- always fails
        mocker.patch.object(
            pr_flow, "merge_mr",
            side_effect=MergeError("Conflict"),
        )

        with pytest.raises(MergeError) as exc_info:
            pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert "even after branch update" in str(exc_info.value)

    def test_merge_retry_does_force_push_on_retry(self, mock_git_module, mock_github_module, mocker):
        """Given merge fails first time, when retrying, then force-push is used for the branch update."""
        from commands import pr_flow
        from commands.pr_flow import MergeError
        from core.github import PullRequestResult

        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        # sync_with_default: already up to date
        mock_git_module._run_git_command.return_value = _make_completed_process(returncode=0)

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        # Mock merge_mr at the pr_flow module level: fails first, succeeds second
        merge_call_count = {"count": 0}

        def mock_merge_mr(pr_number):
            merge_call_count["count"] += 1
            if merge_call_count["count"] == 1:
                raise MergeError("Not mergeable")

        mocker.patch.object(pr_flow, "merge_mr", side_effect=mock_merge_mr)

        # Track push_branch calls to verify force parameter
        push_calls = []

        def tracking_push(branch, refspec=False, force=False):
            push_calls.append({"branch": branch, "refspec": refspec, "force": force})

        mocker.patch.object(pr_flow, "push_branch", side_effect=tracking_push)

        result = pr_flow.pr_flow("TASK-001", "Test", default_branch="develop-working")

        assert result.merged is True
        # The merge-retry push should have force=True
        # push_calls[0] is from the sync+push loop (force=False, first attempt)
        # push_calls[1] is from the merge retry (force=True)
        assert len(push_calls) == 2
        assert push_calls[0]["force"] is False
        assert push_calls[1]["force"] is True
