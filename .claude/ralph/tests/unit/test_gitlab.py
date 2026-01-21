"""Unit tests for the GitLab CLI wrapper module.

Tests cover:
- Listing and fetching merge requests
- Creating and managing merge requests
- Merge request merge operations
- Authentication error handling
- CLI not installed handling
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_glab(mocker):
    """Mock glab CLI commands.

    This fixture mocks the subprocess.run calls specifically for glab commands.
    By default, it returns empty results with success status.

    Returns:
        MagicMock that can be configured with side_effect or return_value
    """
    mock = mocker.patch("core.gitlab.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = "[]"
    mock.return_value.stderr = ""
    return mock


class TestGitLabError:
    """Tests for GitLabError exception class."""

    def test_gitlab_error_contains_message(self):
        """Given error, when raised, then message is included."""
        from core import gitlab

        error = gitlab.GitLabError("Authentication failed")

        assert "Authentication failed" in str(error)

    def test_gitlab_error_contains_stderr(self):
        """Given error with stderr, when raised, then stderr is accessible."""
        from core import gitlab

        error = gitlab.GitLabError("Failed", stderr="glab: not logged in")

        assert error.stderr == "glab: not logged in"

    def test_gitlab_error_contains_command(self):
        """Given error with command, when raised, then command is accessible."""
        from core import gitlab

        error = gitlab.GitLabError("Failed", command=["glab", "mr", "list"])

        assert error.command == ["glab", "mr", "list"]


class TestGitLabNotInstalledError:
    """Tests for GitLabNotInstalledError exception class."""

    def test_gitlab_not_installed_error_is_gitlab_error(self):
        """GitLabNotInstalledError should be a subclass of GitLabError."""
        from core import gitlab

        error = gitlab.GitLabNotInstalledError("glab not found")

        assert isinstance(error, gitlab.GitLabError)


class TestGitLabAuthError:
    """Tests for GitLabAuthError exception class."""

    def test_gitlab_auth_error_is_gitlab_error(self):
        """GitLabAuthError should be a subclass of GitLabError."""
        from core import gitlab

        error = gitlab.GitLabAuthError("Not authenticated")

        assert isinstance(error, gitlab.GitLabError)


class TestGitLabCLINotInstalled:
    """Tests for glab CLI not installed scenario."""

    def test_raises_error_when_glab_not_installed(self, mock_glab: MagicMock):
        """Given glab not installed, when any operation attempted, then clear error is raised."""
        from core import gitlab

        mock_glab.side_effect = FileNotFoundError("glab not found")

        with pytest.raises(gitlab.GitLabNotInstalledError) as exc_info:
            gitlab.list_merge_requests()

        assert "glab" in str(exc_info.value).lower()
        assert "install" in str(exc_info.value).lower()


class TestGitLabNotAuthenticated:
    """Tests for authentication error handling."""

    def test_raises_auth_error_when_not_logged_in(self, mock_glab: MagicMock):
        """Given not authenticated, when any operation attempted, then clear error is raised."""
        from core import gitlab

        mock_glab.return_value.returncode = 1
        mock_glab.return_value.stderr = "glab: To use GitLab CLI, you must authenticate"

        with pytest.raises(gitlab.GitLabAuthError) as exc_info:
            gitlab.list_merge_requests()

        assert "auth" in str(exc_info.value).lower()


class TestMergeRequestResult:
    """Tests for MergeRequestResult dataclass."""

    def test_merge_request_result_has_url_and_number(self):
        """MergeRequestResult should have url and number attributes."""
        from core.gitlab import MergeRequestResult

        result = MergeRequestResult(
            url="https://gitlab.example.com/group/project/-/merge_requests/123",
            number=123
        )

        assert result.url == "https://gitlab.example.com/group/project/-/merge_requests/123"
        assert result.number == 123


class TestCreateMergeRequest:
    """Tests for create_merge_request function."""

    def test_create_merge_request_creates_mr(self, mock_glab: MagicMock):
        """Given branch with commits, when creating MR, then MR is created."""
        from core import gitlab

        mock_glab.return_value.stdout = "https://gitlab.example.com/group/repo/-/merge_requests/123"

        result = gitlab.create_merge_request(
            title="[TASK-001] Implement feature",
            body="Implementation details",
        )

        assert result.url == "https://gitlab.example.com/group/repo/-/merge_requests/123"
        assert result.number == 123

    def test_create_merge_request_with_base_branch(self, mock_glab: MagicMock):
        """Given base branch specified, when creating MR, then base is used."""
        from core import gitlab

        mock_glab.return_value.stdout = "https://gitlab.example.com/group/repo/-/merge_requests/42"

        gitlab.create_merge_request(
            title="Test MR",
            body="Body",
            base="develop",
        )

        call_args = mock_glab.call_args[0][0]
        assert "--target-branch" in call_args or "-b" in call_args
        assert "develop" in call_args

    def test_create_merge_request_extracts_mr_number_from_url(self, mock_glab: MagicMock):
        """Given MR URL returned, when parsing, then number is extracted correctly."""
        from core import gitlab

        mock_glab.return_value.stdout = "https://gitlab.example.com/org/my-repo/-/merge_requests/456"

        result = gitlab.create_merge_request("Title", "Body")

        assert result.number == 456

    def test_create_merge_request_with_draft_flag(self, mock_glab: MagicMock):
        """Given draft flag set, when creating MR, then draft MR is created."""
        from core import gitlab

        mock_glab.return_value.stdout = "https://gitlab.example.com/group/repo/-/merge_requests/99"

        gitlab.create_merge_request(
            title="Draft MR",
            body="Work in progress",
            draft=True,
        )

        call_args = mock_glab.call_args[0][0]
        assert "--draft" in call_args

    def test_create_merge_request_raises_on_no_commits(self, mock_glab: MagicMock):
        """Given no commits to push, when creating MR, then error indicates nothing to push."""
        from core import gitlab

        mock_glab.return_value.returncode = 1
        mock_glab.return_value.stderr = "error creating merge request: there are no changes"

        with pytest.raises(gitlab.GitLabError) as exc_info:
            gitlab.create_merge_request("Title", "Body")

        assert "changes" in str(exc_info.value).lower() or "no" in str(exc_info.value).lower()


class TestGetMergeRequest:
    """Tests for get_merge_request function."""

    def test_get_merge_request_returns_mr_details(self, mock_glab: MagicMock):
        """Given MR exists, when fetching MR, then details are returned."""
        from core import gitlab

        mock_glab.return_value.stdout = '{"iid": 123, "title": "Test MR", "state": "opened", "web_url": "https://gitlab.example.com/group/repo/-/merge_requests/123"}'

        result = gitlab.get_merge_request(123)

        assert result["iid"] == 123
        assert result["title"] == "Test MR"
        assert result["state"] == "opened"

    def test_get_merge_request_raises_on_not_found(self, mock_glab: MagicMock):
        """Given MR doesn't exist, when fetching MR, then error is raised."""
        from core import gitlab

        mock_glab.return_value.returncode = 1
        mock_glab.return_value.stderr = "merge request !999 not found"

        with pytest.raises(gitlab.GitLabError) as exc_info:
            gitlab.get_merge_request(999)

        assert "999" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


class TestListMergeRequests:
    """Tests for list_merge_requests function."""

    def test_list_merge_requests_returns_list_of_mrs(self, mock_glab: MagicMock):
        """Given MRs exist, when listing MRs, then MRs are returned."""
        from core import gitlab

        mock_glab.return_value.stdout = '[{"iid": 1, "title": "Test MR", "state": "opened"}]'

        result = gitlab.list_merge_requests()

        assert len(result) == 1
        assert result[0]["iid"] == 1
        assert result[0]["title"] == "Test MR"

    def test_list_merge_requests_returns_empty_list_when_none(self, mock_glab: MagicMock):
        """Given no MRs exist, when listing MRs, then empty list is returned."""
        from core import gitlab

        mock_glab.return_value.stdout = "[]"

        result = gitlab.list_merge_requests()

        assert result == []

    def test_list_merge_requests_for_head_branch(self, mock_glab: MagicMock):
        """Given MRs exist for branch, when listing, then MRs are returned."""
        from core import gitlab

        mock_glab.return_value.stdout = '[{"iid": 50, "title": "Feature MR"}]'

        result = gitlab.list_merge_requests(head="feature/test")

        assert len(result) == 1
        assert result[0]["iid"] == 50

        call_args = mock_glab.call_args[0][0]
        assert "--source-branch" in call_args
        assert "feature/test" in call_args

    def test_list_merge_requests_filters_by_state(self, mock_glab: MagicMock):
        """Given state filter, when listing MRs, then filter is applied."""
        from core import gitlab

        mock_glab.return_value.stdout = "[]"

        gitlab.list_merge_requests(state="merged")

        call_args = mock_glab.call_args[0][0]
        assert "--state" in call_args
        assert "merged" in call_args


class TestMergeMergeRequest:
    """Tests for merge_merge_request function."""

    def test_merge_merge_request_with_squash(self, mock_glab: MagicMock):
        """Given mergeable MR, when merging with squash, then MR is merged."""
        from core import gitlab

        mock_glab.return_value.returncode = 0

        gitlab.merge_merge_request(123, strategy="squash")

        call_args = mock_glab.call_args[0][0]
        assert "glab" in call_args
        assert "mr" in call_args
        assert "merge" in call_args
        assert "--squash" in call_args or "-s" in call_args

    def test_merge_merge_request_with_merge_commit(self, mock_glab: MagicMock):
        """Given mergeable MR, when merging with merge commit, then MR is merged."""
        from core import gitlab

        mock_glab.return_value.returncode = 0

        gitlab.merge_merge_request(123, strategy="merge")

        call_args = mock_glab.call_args[0][0]
        # merge commit is the default, so no squash flag
        assert "--squash" not in call_args and "-s" not in call_args

    def test_merge_merge_request_with_rebase(self, mock_glab: MagicMock):
        """Given mergeable MR, when merging with rebase, then MR is merged."""
        from core import gitlab

        mock_glab.return_value.returncode = 0

        gitlab.merge_merge_request(123, strategy="rebase")

        call_args = mock_glab.call_args[0][0]
        assert "--rebase" in call_args or "-r" in call_args

    def test_merge_merge_request_raises_on_conflict(self, mock_glab: MagicMock):
        """Given MR has conflicts, when merging, then error is raised."""
        from core import gitlab

        mock_glab.return_value.returncode = 1
        mock_glab.return_value.stderr = "Merge request !123 cannot be merged: the merge commit cannot be cleanly created"

        with pytest.raises(gitlab.GitLabError) as exc_info:
            gitlab.merge_merge_request(123)

        assert "merge" in str(exc_info.value).lower() or "conflict" in str(exc_info.value).lower()


class TestFindMergedMr:
    """Tests for find_merged_mr function."""

    def test_find_merged_mr_returns_mr_number(self, mock_glab: MagicMock):
        """Given merged MR exists, when searching, then MR number is returned."""
        from core import gitlab

        mock_glab.return_value.stdout = '[{"iid": 99, "title": "[TASK-001] Feature"}]'

        result = gitlab.find_merged_mr("TASK-001")

        assert result == 99

    def test_find_merged_mr_returns_none_when_not_found(self, mock_glab: MagicMock):
        """Given no merged MR, when searching, then None is returned."""
        from core import gitlab

        mock_glab.return_value.stdout = "[]"

        result = gitlab.find_merged_mr("NONEXISTENT-999")

        assert result is None


class TestDeleteRemoteBranch:
    """Tests for delete_remote_branch function."""

    def test_delete_remote_branch_deletes_successfully(self, mock_glab: MagicMock):
        """Given remote branch exists, when deleting, then branch is deleted."""
        from core import gitlab

        mock_glab.return_value.returncode = 0

        # This may use git push or glab api - either way test the function works
        gitlab.delete_remote_branch("feature/old-branch")

        # Just verify no exception is raised

    def test_delete_remote_branch_ignores_nonexistent_branch(self, mock_glab: MagicMock):
        """Given remote branch doesn't exist, when deleting, then no error is raised."""
        from core import gitlab

        mock_glab.return_value.returncode = 1
        mock_glab.return_value.stderr = "error: remote ref does not exist"

        # Should not raise
        gitlab.delete_remote_branch("nonexistent-branch")
