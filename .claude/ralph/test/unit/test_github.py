"""Unit tests for the GitHub CLI wrapper module.

Tests cover:
- Listing and fetching issues
- Creating and managing pull requests
- Closing issues
- Authentication error handling
"""

from unittest.mock import MagicMock

import pytest


class TestListIssues:
    """Tests for list_issues function."""

    def test_list_issues_returns_list_of_issues(self, mock_gh: MagicMock):
        """Given issues exist, when listing issues, then issues are returned."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 1, "title": "Test Issue", "state": "open"}]'

        result = github.list_issues()

        assert len(result) == 1
        assert result[0]["number"] == 1
        assert result[0]["title"] == "Test Issue"

    def test_list_issues_returns_empty_list_when_none(self, mock_gh: MagicMock):
        """Given no issues exist, when listing issues, then empty list is returned."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        result = github.list_issues()

        assert result == []

    def test_list_issues_filters_by_state(self, mock_gh: MagicMock):
        """Given state filter, when listing issues, then filter is applied."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 1, "title": "Closed Issue", "state": "closed"}]'

        result = github.list_issues(state="closed")

        # Verify correct result
        assert len(result) == 1
        assert result[0]["state"] == "closed"
        # Verify command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "issue", "list", "--json", "number,title,state,labels,body", "--state", "closed"]

    def test_list_issues_filters_by_label(self, mock_gh: MagicMock):
        """Given label filter, when listing issues, then filter is applied."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 2, "title": "Bug report"}]'

        result = github.list_issues(label="bug")

        # Verify correct result
        assert len(result) == 1
        assert result[0]["number"] == 2
        # Verify command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "issue", "list", "--json", "number,title,state,labels,body", "--label", "bug"]


class TestGetIssue:
    """Tests for get_issue function."""

    def test_get_issue_returns_issue_details(self, mock_gh: MagicMock):
        """Given issue exists, when fetching issue, then details are returned."""
        from core import github

        mock_gh.return_value.stdout = '{"number": 42, "title": "Bug Fix", "body": "Description", "state": "open", "labels": [{"name": "bug"}]}'

        result = github.get_issue(42)

        assert result["number"] == 42
        assert result["title"] == "Bug Fix"
        assert result["body"] == "Description"
        assert result["state"] == "open"

    def test_get_issue_raises_on_not_found(self, mock_gh: MagicMock):
        """Given issue doesn't exist, when fetching issue, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "Could not resolve to an Issue with the number of 999"

        with pytest.raises(github.GitHubError) as exc_info:
            github.get_issue(999)

        error = exc_info.value
        # Verify error contains issue number
        assert "999" in str(error)
        # Verify stderr is included
        assert error.stderr == "Could not resolve to an Issue with the number of 999"
        # Verify command is included
        assert error.command is not None
        assert "issue" in error.command
        assert "view" in error.command


class TestCloseIssue:
    """Tests for close_issue function."""

    def test_close_issue_closes_successfully(self, mock_gh: MagicMock):
        """Given open issue, when closing issue, then issue is closed."""
        from core import github

        mock_gh.return_value.returncode = 0
        mock_gh.return_value.stdout = ""

        github.close_issue(42)

        # Verify exact command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "issue", "close", "42"]


class TestFindIssueByTitle:
    """Tests for find_issue_by_title function."""

    def test_find_issue_by_title_returns_issue_number(self, mock_gh: MagicMock):
        """Given issue with matching title, when searching, then issue number is returned."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 110, "title": "[TASK-001] Implement feature"}]'

        result = github.find_issue_by_title("TASK-001")

        assert result == 110

    def test_find_issue_by_title_returns_none_when_not_found(self, mock_gh: MagicMock):
        """Given no matching issue, when searching, then None is returned."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        result = github.find_issue_by_title("NONEXISTENT-999")

        assert result is None


class TestCreatePullRequest:
    """Tests for create_pull_request function."""

    def test_create_pull_request_creates_pr(self, mock_gh: MagicMock):
        """Given branch with commits, when creating PR, then PR is created."""
        from core import github

        mock_gh.return_value.stdout = "https://github.com/owner/repo/pull/123"

        result = github.create_pull_request(
            title="[TASK-001] Implement feature",
            body="Implementation details",
        )

        assert result.url == "https://github.com/owner/repo/pull/123"
        assert result.number == 123

    def test_create_pull_request_with_base_branch(self, mock_gh: MagicMock):
        """Given base branch specified, when creating PR, then base is used."""
        from core import github

        mock_gh.return_value.stdout = "https://github.com/owner/repo/pull/42"

        result = github.create_pull_request(
            title="Test PR",
            body="Body",
            base="develop",
        )

        # Verify result
        assert result.number == 42
        # Verify exact command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "pr", "create", "--title", "Test PR", "--body", "Body", "--base", "develop"]

    def test_create_pull_request_extracts_pr_number_from_url(self, mock_gh: MagicMock):
        """Given PR URL returned, when parsing, then number is extracted correctly."""
        from core import github

        mock_gh.return_value.stdout = "https://github.com/org/my-repo/pull/456"

        result = github.create_pull_request("Title", "Body")

        assert result.number == 456

    def test_create_pull_request_raises_on_no_commits(self, mock_gh: MagicMock):
        """Given no commits to push, when creating PR, then error indicates nothing to push."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "pull request create failed: GraphQL: No commits between main and feature"

        with pytest.raises(github.GitHubError) as exc_info:
            github.create_pull_request("Title", "Body")

        error = exc_info.value
        # Verify error message mentions commits issue
        assert "commits" in str(error).lower()
        # Verify stderr is included
        assert error.stderr == "pull request create failed: GraphQL: No commits between main and feature"
        # Verify command is included
        assert error.command is not None
        assert "pr" in error.command
        assert "create" in error.command


class TestGetPullRequest:
    """Tests for get_pull_request function."""

    def test_get_pull_request_returns_pr_details(self, mock_gh: MagicMock):
        """Given PR exists, when fetching PR, then details are returned."""
        from core import github

        mock_gh.return_value.stdout = '{"number": 123, "title": "Test PR", "state": "open", "url": "https://github.com/owner/repo/pull/123", "mergeable": "MERGEABLE"}'

        result = github.get_pull_request(123)

        assert result["number"] == 123
        assert result["title"] == "Test PR"
        assert result["state"] == "open"


class TestListPullRequests:
    """Tests for list_pull_requests function."""

    def test_list_pull_requests_for_head_branch(self, mock_gh: MagicMock):
        """Given PRs exist for branch, when listing, then PRs are returned."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 50, "title": "Feature PR"}]'

        result = github.list_pull_requests(head="feature/test")

        assert len(result) == 1
        assert result[0]["number"] == 50

    def test_list_pull_requests_returns_empty_when_none(self, mock_gh: MagicMock):
        """Given no PRs for branch, when listing, then empty list is returned."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        result = github.list_pull_requests(head="feature/no-pr")

        assert result == []


class TestMergePullRequest:
    """Tests for merge_pull_request function."""

    def test_merge_pull_request_with_squash(self, mock_gh: MagicMock):
        """Given mergeable PR, when merging with squash, then PR is merged."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.merge_pull_request(123, strategy="squash")

        # Verify exact command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "pr", "merge", "123", "--squash"]

    def test_merge_pull_request_with_merge_commit(self, mock_gh: MagicMock):
        """Given mergeable PR, when merging with merge commit, then PR is merged."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.merge_pull_request(123, strategy="merge")

        # Verify exact command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "pr", "merge", "123", "--merge"]

    def test_merge_pull_request_with_rebase(self, mock_gh: MagicMock):
        """Given mergeable PR, when merging with rebase, then PR is merged."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.merge_pull_request(123, strategy="rebase")

        # Verify exact command structure
        args, _ = mock_gh.call_args
        assert args[0] == ["gh", "pr", "merge", "123", "--rebase"]

    def test_merge_pull_request_raises_on_conflict(self, mock_gh: MagicMock):
        """Given PR has conflicts, when merging, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "Pull request #123 is not mergeable: the merge commit cannot be cleanly created"

        with pytest.raises(github.GitHubError) as exc_info:
            github.merge_pull_request(123)

        error = exc_info.value
        # Verify error message mentions merge conflict
        assert "mergeable" in str(error).lower()
        # Verify stderr is included
        assert error.stderr == "Pull request #123 is not mergeable: the merge commit cannot be cleanly created"
        # Verify command is included
        assert error.command is not None
        assert "pr" in error.command
        assert "merge" in error.command


class TestFindMergedPr:
    """Tests for find_merged_pr function."""

    def test_find_merged_pr_returns_pr_number(self, mock_gh: MagicMock):
        """Given merged PR exists, when searching, then PR number is returned."""
        from core import github

        mock_gh.return_value.stdout = '[{"number": 99, "title": "[TASK-001] Feature"}]'

        result = github.find_merged_pr("TASK-001")

        assert result == 99

    def test_find_merged_pr_returns_none_when_not_found(self, mock_gh: MagicMock):
        """Given no merged PR, when searching, then None is returned."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        result = github.find_merged_pr("NONEXISTENT-999")

        assert result is None


class TestDeleteRemoteBranch:
    """Tests for delete_remote_branch function."""

    def test_delete_remote_branch_deletes_successfully(self, mock_gh: MagicMock):
        """Given remote branch exists, when deleting, then branch is deleted."""
        from core import github

        mock_gh.return_value.returncode = 0
        mock_gh.return_value.stdout = ""
        mock_gh.return_value.stderr = ""

        github.delete_remote_branch("feature/old-branch")

        # Verify command was called
        mock_gh.assert_called_once()
        # Verify command structure (should be git push --delete or gh api)
        args, _ = mock_gh.call_args
        cmd = args[0]
        # Function uses git push origin --delete
        assert cmd == ["git", "push", "origin", "--delete", "feature/old-branch"]


class TestGitHubError:
    """Tests for GitHubError exception class."""

    def test_github_error_contains_message(self):
        """Given error, when raised, then message is included."""
        from core import github

        error = github.GitHubError("Authentication failed")

        assert "Authentication failed" in str(error)

    def test_github_error_contains_stderr(self):
        """Given error with stderr, when raised, then stderr is accessible."""
        from core import github

        error = github.GitHubError("Failed", stderr="gh: not logged in")

        assert error.stderr == "gh: not logged in"


class TestGitHubNotAuthenticated:
    """Tests for authentication error handling."""

    def test_raises_auth_error_when_not_logged_in(self, mock_gh: MagicMock):
        """Given not authenticated, when any operation attempted, then clear error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "gh: To use GitHub CLI in a GitHub Actions workflow, set the GH_TOKEN environment variable"

        with pytest.raises(github.GitHubAuthError) as exc_info:
            github.list_issues()

        error = exc_info.value
        # Verify error message mentions authentication
        error_str = str(error).lower()
        assert "auth" in error_str or "token" in error_str
        # Verify stderr is included
        assert error.stderr == "gh: To use GitHub CLI in a GitHub Actions workflow, set the GH_TOKEN environment variable"


class TestGitHubCLINotInstalled:
    """Tests for gh CLI not installed scenario."""

    def test_raises_error_when_gh_not_installed(self, mock_gh: MagicMock):
        """Given gh not installed, when any operation attempted, then clear error is raised."""
        from core import github

        mock_gh.side_effect = FileNotFoundError("gh not found")

        with pytest.raises(github.GitHubNotInstalledError) as exc_info:
            github.list_issues()

        assert "gh" in str(exc_info.value).lower()
