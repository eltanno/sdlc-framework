"""Unit tests for core/github.py - GitHub CLI (gh) wrapper module.

Tests cover:
- Listing and fetching issues
- Creating and managing pull requests
- Closing issues and updating labels
- Error handling for auth and rate limiting

Following TDD: Write failing tests first, then implement.
"""

import json
import subprocess
from unittest.mock import MagicMock

import pytest


class TestIssueOperations:
    """Tests for GitHub issue operations."""

    def test_list_issues_returns_issues(self, mocker):
        """Given issues exist, list_issues returns them."""
        from core.github import list_issues

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"number": 1, "title": "First issue", "state": "open"},
                {"number": 2, "title": "Second issue", "state": "open"},
            ]),
            stderr="",
        )

        result = list_issues()

        assert len(result) == 2
        assert result[0]["number"] == 1
        assert result[0]["title"] == "First issue"

    def test_list_issues_with_label_filter(self, mocker):
        """Given label filter, list_issues filters by label."""
        from core.github import list_issues

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"number": 1, "title": "Bug", "labels": [{"name": "bug"}]}]),
            stderr="",
        )

        result = list_issues(labels=["bug"])

        assert len(result) == 1
        call_args = mock_run.call_args[0][0]
        assert "--label" in call_args
        assert "bug" in call_args

    def test_list_issues_with_assignee_filter(self, mocker):
        """Given assignee filter, list_issues filters by assignee."""
        from core.github import list_issues

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps([]), stderr=""
        )

        list_issues(assignee="@me")

        call_args = mock_run.call_args[0][0]
        assert "--assignee" in call_args
        assert "@me" in call_args

    def test_get_issue_returns_issue_details(self, mocker):
        """Given issue number, get_issue returns full issue data."""
        from core.github import get_issue

        issue_data = {
            "number": 123,
            "title": "Test issue",
            "body": "Issue description",
            "state": "open",
            "labels": [{"name": "enhancement"}],
            "assignees": [{"login": "user1"}],
        }
        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(issue_data), stderr=""
        )

        result = get_issue(123)

        assert result["number"] == 123
        assert result["title"] == "Test issue"
        assert result["body"] == "Issue description"

    def test_get_issue_not_found(self, mocker):
        """Given non-existent issue, get_issue returns None."""
        from core.github import get_issue

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="issue not found"
        )

        result = get_issue(99999)

        assert result is None

    def test_close_issue_success(self, mocker):
        """Given open issue, close_issue closes it."""
        from core.github import close_issue

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = close_issue(123)

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "close" in call_args
        assert "123" in call_args

    def test_close_issue_with_reason(self, mocker):
        """Given close reason, close_issue includes it."""
        from core.github import close_issue

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = close_issue(123, reason="completed")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "--reason" in call_args


class TestLabelOperations:
    """Tests for GitHub label operations."""

    def test_add_label_to_issue(self, mocker):
        """Given issue and label, add_label adds the label."""
        from core.github import add_label

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = add_label(123, "in-progress")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "edit" in call_args
        assert "--add-label" in call_args
        assert "in-progress" in call_args

    def test_remove_label_from_issue(self, mocker):
        """Given issue and label, remove_label removes the label."""
        from core.github import remove_label

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = remove_label(123, "in-progress")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "edit" in call_args
        assert "--remove-label" in call_args
        assert "in-progress" in call_args


class TestAssigneeOperations:
    """Tests for GitHub assignee operations."""

    def test_assign_issue(self, mocker):
        """Given issue and user, assign_issue assigns the user."""
        from core.github import assign_issue

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = assign_issue(123, "username")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "edit" in call_args
        assert "--add-assignee" in call_args
        assert "username" in call_args

    def test_unassign_issue(self, mocker):
        """Given issue and user, unassign_issue removes the user."""
        from core.github import unassign_issue

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = unassign_issue(123, "username")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "edit" in call_args
        assert "--remove-assignee" in call_args


class TestPullRequestOperations:
    """Tests for GitHub pull request operations."""

    def test_create_pr_success(self, mocker):
        """Given changes pushed, create_pr creates pull request."""
        from core.github import create_pr

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"number": 42, "url": "https://github.com/owner/repo/pull/42"}),
            stderr="",
        )

        result = create_pr(
            title="Add feature",
            body="Description of the feature",
            base="main",
        )

        assert result is not None
        assert result["number"] == 42
        call_args = mock_run.call_args[0][0]
        assert "create" in call_args
        assert "--title" in call_args
        assert "--body" in call_args

    def test_create_pr_with_issue_link(self, mocker):
        """Given issue number, create_pr links PR to issue."""
        from core.github import create_pr

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"number": 42, "url": "https://github.com/owner/repo/pull/42"}),
            stderr="",
        )

        create_pr(
            title="Add feature",
            body="Closes #123",
            base="main",
        )

        call_args = mock_run.call_args[0][0]
        # Body should include issue reference
        body_idx = call_args.index("--body") + 1
        assert "123" in call_args[body_idx]

    def test_get_pr_returns_pr_details(self, mocker):
        """Given PR number, get_pr returns PR data."""
        from core.github import get_pr

        pr_data = {
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "mergeable": True,
            "headRefName": "feature/test",
        }
        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(pr_data), stderr=""
        )

        result = get_pr(42)

        assert result["number"] == 42
        assert result["title"] == "Test PR"

    def test_list_prs_returns_prs(self, mocker):
        """Given PRs exist, list_prs returns them."""
        from core.github import list_prs

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"number": 1, "title": "First PR"},
                {"number": 2, "title": "Second PR"},
            ]),
            stderr="",
        )

        result = list_prs()

        assert len(result) == 2

    def test_merge_pr_success(self, mocker):
        """Given mergeable PR, merge_pr merges it."""
        from core.github import merge_pr

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = merge_pr(42)

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "merge" in call_args
        assert "42" in call_args

    def test_merge_pr_with_squash(self, mocker):
        """Given squash option, merge_pr uses squash merge."""
        from core.github import merge_pr

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = merge_pr(42, merge_method="squash")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "--squash" in call_args


class TestErrorHandling:
    """Tests for GitHub CLI error handling."""

    def test_auth_error_raises_exception(self, mocker):
        """Given not authenticated, operations raise GitHubAuthError."""
        from core.github import list_issues, GitHubAuthError

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="gh auth login"
        )

        with pytest.raises(GitHubAuthError):
            list_issues()

    def test_rate_limit_raises_exception(self, mocker):
        """Given rate limit hit, operations raise GitHubRateLimitError."""
        from core.github import list_issues, GitHubRateLimitError

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="API rate limit exceeded"
        )

        with pytest.raises(GitHubRateLimitError):
            list_issues()

    def test_gh_not_installed_raises_exception(self, mocker):
        """Given gh not installed, operations raise GitHubNotFoundError."""
        from core.github import list_issues, GitHubNotFoundError

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.side_effect = FileNotFoundError("gh not found")

        with pytest.raises(GitHubNotFoundError):
            list_issues()


class TestUserOperations:
    """Tests for GitHub user operations."""

    def test_get_current_user(self, mocker):
        """Given authenticated, get_current_user returns username."""
        from core.github import get_current_user

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="testuser\n", stderr=""
        )

        result = get_current_user()

        assert result == "testuser"

    def test_get_current_user_not_authenticated(self, mocker):
        """Given not authenticated, get_current_user returns None."""
        from core.github import get_current_user

        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="not logged in"
        )

        result = get_current_user()

        assert result is None


class TestRepoOperations:
    """Tests for GitHub repository operations."""

    def test_get_repo_info(self, mocker):
        """Given in a repo, get_repo_info returns repo details."""
        from core.github import get_repo_info

        repo_data = {
            "owner": {"login": "owner"},
            "name": "repo",
            "defaultBranchRef": {"name": "main"},
        }
        mock_run = mocker.patch("core.github.subprocess.run")
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps(repo_data), stderr=""
        )

        result = get_repo_info()

        assert result["owner"]["login"] == "owner"
        assert result["name"] == "repo"
