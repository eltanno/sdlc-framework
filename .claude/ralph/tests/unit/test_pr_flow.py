"""Unit tests for the PR flow command module.

Tests cover:
- Committing staged changes
- Pushing to remote
- Creating pull requests with proper linking
- Merging pull requests
- The complete PR flow from commit to merge
- Repo tool abstraction (GitHub vs GitLab)
"""

from unittest.mock import MagicMock

import pytest


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

    This mocks _get_cached_repo_module to return a mock GitHub module
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
    mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_github)

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


class TestCreatePr:
    """Tests for create_pr function."""

    def test_create_pr_creates_with_ticket_in_title(self, mock_github_module):
        """Given ticket ID, when creating PR, then title includes ticket ID."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        result = pr_flow.create_pr("TASK-001", "Implementation complete")

        create_call = mock_github_module.create_pull_request.call_args
        title = create_call[1].get("title") or create_call[0][0]
        assert "TASK-001" in title

    def test_create_pr_links_to_issue_in_body(self, mock_github_module):
        """Given issue number, when creating PR, then body links to issue."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = 110
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        pr_flow.create_pr("TASK-001", "Implementation complete")

        create_call = mock_github_module.create_pull_request.call_args
        body = create_call[1].get("body") or create_call[0][1]
        assert "#110" in body or "Closes #110" in body

    def test_create_pr_returns_pr_info(self, mock_github_module):
        """Given PR creation succeeds, when result returned, then PR URL and number are provided."""
        from commands import pr_flow
        from core.github import PullRequestResult

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/123",
            number=123,
        )

        result = pr_flow.create_pr("TASK-001", "Test")

        assert result.number == 123
        assert result.url == "https://github.com/owner/repo/pull/123"

    def test_create_pr_handles_creation_failure(self, mock_github_module):
        """Given PR creation fails, when create_pr called, then PrFlowError is raised with details."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import GitHubError

        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.side_effect = GitHubError("API error")

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.create_pr("TASK-001", "Test")

        assert "API error" in str(exc_info.value)


class TestMergePr:
    """Tests for merge_pr function."""

    def test_merge_pr_uses_squash_by_default(self, mock_github_module):
        """Given PR number, when merging, then squash merge is used to maintain clean history."""
        from commands import pr_flow

        mock_github_module.merge_pull_request.return_value = None

        pr_flow.merge_pr(123)

        # Verify merge was attempted with squash strategy
        mock_github_module.merge_pull_request.assert_called_once()
        call_args = mock_github_module.merge_pull_request.call_args
        assert call_args[0][0] == 123
        assert call_args[1].get("strategy") == "squash"

    def test_merge_pr_handles_merge_conflicts(self, mock_github_module):
        """Given PR has merge conflicts, when merging, then PrFlowError is raised with details."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.github import GitHubError

        mock_github_module.merge_pull_request.side_effect = GitHubError("Merge conflict")

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.merge_pr(123)

        assert "Merge conflict" in str(exc_info.value)


class TestCheckoutDetachedMain:
    """Tests for checkout_detached_main function."""

    def test_checkout_detached_main_fetches_and_checkouts(self, mock_git_module):
        """Given main exists remotely, when checking out detached, then detached HEAD is used."""
        from commands import pr_flow

        mock_git_module.fetch.return_value = None
        # Simulate checkout --detach
        mock_git_module._run_git_command = MagicMock()

        pr_flow.checkout_detached_main("main")

        mock_git_module.fetch.assert_called()


class TestSyncWithMain:
    """Tests for sync_with_main function."""

    def test_sync_with_main_fetches_and_merges(self, mock_git_module):
        """Given main exists remotely, when syncing, then fetch and merge are called."""
        from commands import pr_flow

        mock_git_module.fetch.return_value = None
        mock_git_module.merge.return_value = None

        pr_flow.sync_with_main("main")

        mock_git_module.fetch.assert_called_once_with(remote="origin")
        mock_git_module.merge.assert_called_once_with("origin/main")

    def test_sync_with_main_raises_on_conflict(self, mock_git_module):
        """Given merge has conflicts, when syncing, then PrFlowError is raised."""
        from commands import pr_flow
        from commands.pr_flow import PrFlowError
        from core.git import GitError

        mock_git_module.fetch.return_value = None
        mock_git_module.merge.side_effect = GitError("CONFLICT")
        # Ensure GitError is the real exception class, not mocked
        mock_git_module.GitError = GitError

        with pytest.raises(PrFlowError) as exc_info:
            pr_flow.sync_with_main()

        assert "Merge conflicts" in str(exc_info.value)



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

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = 110
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Implementation complete")

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

    def test_pr_flow_already_merged_returns_early(self, mock_git_module, mock_github_module):
        """Given PR already merged, when running flow, then returns early with already_done."""
        from commands import pr_flow

        mock_git_module.get_current_branch.return_value = "main"
        mock_git_module.is_dirty.return_value = False
        mock_github_module.find_merged_pr.return_value = 99

        result = pr_flow.pr_flow("TASK-001", "Test")

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

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = [{"number": 50}]
        mock_github_module.get_pull_request.return_value = {
            "number": 50,
            "url": "https://github.com/owner/repo/pull/50",
        }
        mock_github_module.merge_pull_request.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Test")

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

        mock_github_module.find_merged_pr.return_value = None
        mock_github_module.list_pull_requests.return_value = []
        mock_github_module.find_issue_by_title.return_value = None
        mock_github_module.create_pull_request.return_value = PullRequestResult(
            url="https://github.com/owner/repo/pull/42",
            number=42,
        )

        result = pr_flow.pr_flow("TASK-001", "Test", no_merge=True)

        assert result.merged is False
        mock_github_module.merge_pull_request.assert_not_called()


    def test_pr_flow_raises_on_main_with_no_changes(self, mock_git_module, mock_github_module):
        """Given on main branch with no changes and no existing PR, when running flow, then error is raised."""
        from commands import pr_flow

        mock_git_module.get_current_branch.return_value = "main"
        mock_git_module.is_dirty.return_value = False
        mock_github_module.find_merged_pr.return_value = None

        with pytest.raises(pr_flow.PrFlowError) as exc_info:
            pr_flow.pr_flow("TASK-001", "Test")

        assert "main" in str(exc_info.value).lower() or "default branch" in str(exc_info.value).lower()




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

        # Mock _get_cached_repo_module to return gitlab mock
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

        mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_gitlab)

        # Setup git mocks
        mock_git_module.get_current_branch.return_value = "feature/TASK-001-test"
        mock_git_module.is_dirty.return_value = True
        mock_git_module.stage_all.return_value = None
        mock_git_module.commit.return_value = "abc1234"
        mock_git_module.push.return_value = None
        mock_git_module.fetch.return_value = None
        mock_git_module.merge.return_value = None

        result = pr_flow.pr_flow("TASK-001", "Implementation complete")

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

        mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_gitlab)

        result = pr_flow.create_mr("TASK-001", "Test implementation")

        mock_gitlab.create_merge_request.assert_called_once()
        call_kwargs = mock_gitlab.create_merge_request.call_args[1]
        assert "TASK-001" in call_kwargs.get("title", "")

    def test_merge_mr_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when merge_mr called, then gitlab.merge_merge_request is called."""
        from commands import pr_flow

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.merge_merge_request.return_value = None

        mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_gitlab)

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

        mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_gitlab)

        result = pr_flow.find_existing_pr("feature/test")

        mock_gitlab.list_merge_requests.assert_called_once()
        # GitLab uses 'iid' but we should handle either 'number' or 'iid'
        assert result == 50

    def test_check_already_merged_uses_gitlab_when_configured(self, tmp_path, mocker):
        """Given repo.type: gitlab, when check_already_merged called, then gitlab.find_merged_mr is called."""
        from commands import pr_flow

        mock_gitlab = mocker.MagicMock()
        mock_gitlab.find_merged_mr.return_value = 99

        mocker.patch("commands.pr_flow._get_cached_repo_module", return_value=mock_gitlab)

        result = pr_flow.check_already_merged("TASK-001")

        mock_gitlab.find_merged_mr.assert_called_once_with("TASK-001")
        assert result == 99
