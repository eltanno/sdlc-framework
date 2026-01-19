"""Unit tests for the GitHub CLI wrapper module.

Tests cover:
- Issue listing, fetching, closing, and editing
- Pull request listing, creating, and merging
- Authentication checking and error handling
- Rate limiting detection
"""

import json
import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest


# Test fixtures
@pytest.fixture
def sample_issue() -> dict[str, Any]:
    """Sample issue data as returned by gh CLI."""
    return {
        "number": 42,
        "title": "[TASK-001] Implement feature X",
        "body": "Description of the task",
        "state": "OPEN",
        "labels": [{"name": "task"}, {"name": "ralph-1"}],
        "assignees": [{"login": "testuser"}],
        "url": "https://github.com/owner/repo/issues/42",
    }


@pytest.fixture
def sample_pr() -> dict[str, Any]:
    """Sample PR data as returned by gh CLI."""
    return {
        "number": 123,
        "title": "[TASK-001] Implement feature X",
        "body": "PR description",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/pull/123",
        "headRefName": "feature/TASK-001-implementation",
        "baseRefName": "main",
    }


class TestListIssues:
    """Tests for list_issues function."""

    def test_list_issues_returns_empty_list_when_none_found(self, mock_gh: MagicMock):
        """Given no issues match, when listing issues, then empty list is returned."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        result = github.list_issues()

        assert result == []
        mock_gh.assert_called_once()

    def test_list_issues_returns_issues_with_correct_metadata(
        self, mock_gh: MagicMock, sample_issue: dict[str, Any]
    ):
        """Given issues exist, when listing issues, then all metadata is returned."""
        from core import github

        mock_gh.return_value.stdout = json.dumps([sample_issue])

        result = github.list_issues()

        assert len(result) == 1
        assert result[0]["number"] == 42
        assert result[0]["title"] == "[TASK-001] Implement feature X"
        assert result[0]["state"] == "OPEN"

    def test_list_issues_filters_by_state(self, mock_gh: MagicMock):
        """Given state filter, when listing issues, then --state flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_issues(state="open")

        call_args = mock_gh.call_args[0][0]
        assert "--state" in call_args
        assert "open" in call_args

    def test_list_issues_filters_by_labels(self, mock_gh: MagicMock):
        """Given labels filter, when listing issues, then --label flags are used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_issues(labels=["task", "blocked"])

        call_args = mock_gh.call_args[0][0]
        assert "--label" in call_args
        assert "task" in call_args
        assert "blocked" in call_args

    def test_list_issues_filters_by_assignee(self, mock_gh: MagicMock):
        """Given assignee filter, when listing issues, then --assignee flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_issues(assignee="testuser")

        call_args = mock_gh.call_args[0][0]
        assert "--assignee" in call_args
        assert "testuser" in call_args

    def test_list_issues_uses_search_term(self, mock_gh: MagicMock):
        """Given search term, when listing issues, then --search flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_issues(search="TASK-001 in:title")

        call_args = mock_gh.call_args[0][0]
        assert "--search" in call_args
        assert "TASK-001 in:title" in call_args

    def test_list_issues_respects_limit(self, mock_gh: MagicMock):
        """Given limit, when listing issues, then --limit flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_issues(limit=50)

        call_args = mock_gh.call_args[0][0]
        assert "--limit" in call_args
        assert "50" in call_args


class TestGetIssue:
    """Tests for get_issue function."""

    def test_get_issue_returns_full_details(
        self, mock_gh: MagicMock, sample_issue: dict[str, Any]
    ):
        """Given issue exists, when fetching, then all details are returned."""
        from core import github

        mock_gh.return_value.stdout = json.dumps(sample_issue)

        result = github.get_issue(42)

        assert result["number"] == 42
        assert result["title"] == "[TASK-001] Implement feature X"
        assert result["body"] == "Description of the task"
        assert result["state"] == "OPEN"
        assert len(result["labels"]) == 2

    def test_get_issue_raises_on_not_found(self, mock_gh: MagicMock):
        """Given issue doesn't exist, when fetching, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "Could not resolve to an Issue with the number of 999"

        with pytest.raises(github.GitHubError) as exc_info:
            github.get_issue(999)

        assert "999" in str(exc_info.value)


class TestCloseIssue:
    """Tests for close_issue function."""

    def test_close_issue_succeeds(self, mock_gh: MagicMock):
        """Given valid issue, when closing, then issue is closed."""
        from core import github

        mock_gh.return_value.returncode = 0
        mock_gh.return_value.stdout = ""

        github.close_issue(42)

        call_args = mock_gh.call_args[0][0]
        assert "issue" in call_args
        assert "close" in call_args
        assert "42" in call_args

    def test_close_issue_raises_on_failure(self, mock_gh: MagicMock):
        """Given close fails, when closing issue, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "Issue already closed"

        with pytest.raises(github.GitHubError):
            github.close_issue(42)


class TestEditIssue:
    """Tests for edit_issue function."""

    def test_edit_issue_adds_labels(self, mock_gh: MagicMock):
        """Given labels to add, when editing issue, then --add-label flags used."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.edit_issue(42, add_labels=["ralph-1", "task"])

        call_args = mock_gh.call_args[0][0]
        assert "--add-label" in call_args
        assert "ralph-1" in call_args
        assert "task" in call_args

    def test_edit_issue_removes_labels(self, mock_gh: MagicMock):
        """Given labels to remove, when editing issue, then --remove-label flags used."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.edit_issue(42, remove_labels=["in-progress"])

        call_args = mock_gh.call_args[0][0]
        assert "--remove-label" in call_args
        assert "in-progress" in call_args

    def test_edit_issue_adds_assignees(self, mock_gh: MagicMock):
        """Given assignees to add, when editing issue, then --add-assignee flags used."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.edit_issue(42, add_assignees=["@me"])

        call_args = mock_gh.call_args[0][0]
        assert "--add-assignee" in call_args
        assert "@me" in call_args

    def test_edit_issue_removes_assignees(self, mock_gh: MagicMock):
        """Given assignees to remove, when editing issue, then --remove-assignee flags used."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.edit_issue(42, remove_assignees=["@me"])

        call_args = mock_gh.call_args[0][0]
        assert "--remove-assignee" in call_args
        assert "@me" in call_args


class TestCommentIssue:
    """Tests for comment_issue function."""

    def test_comment_issue_adds_comment(self, mock_gh: MagicMock):
        """Given issue and body, when commenting, then comment is added."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.comment_issue(42, "This is a comment")

        call_args = mock_gh.call_args[0][0]
        assert "issue" in call_args
        assert "comment" in call_args
        assert "42" in call_args
        assert "--body" in call_args


class TestListPRs:
    """Tests for list_prs function."""

    def test_list_prs_returns_prs(
        self, mock_gh: MagicMock, sample_pr: dict[str, Any]
    ):
        """Given PRs exist, when listing, then PRs are returned."""
        from core import github

        mock_gh.return_value.stdout = json.dumps([sample_pr])

        result = github.list_prs()

        assert len(result) == 1
        assert result[0]["number"] == 123

    def test_list_prs_filters_by_head_branch(self, mock_gh: MagicMock):
        """Given head filter, when listing PRs, then --head flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_prs(head="feature/TASK-001")

        call_args = mock_gh.call_args[0][0]
        assert "--head" in call_args
        assert "feature/TASK-001" in call_args

    def test_list_prs_filters_by_state(self, mock_gh: MagicMock):
        """Given state filter, when listing PRs, then --state flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_prs(state="merged")

        call_args = mock_gh.call_args[0][0]
        assert "--state" in call_args
        assert "merged" in call_args

    def test_list_prs_uses_search(self, mock_gh: MagicMock):
        """Given search term, when listing PRs, then --search flag is used."""
        from core import github

        mock_gh.return_value.stdout = "[]"

        github.list_prs(search="TASK-001 in:title")

        call_args = mock_gh.call_args[0][0]
        assert "--search" in call_args


class TestGetPR:
    """Tests for get_pr function."""

    def test_get_pr_returns_details(
        self, mock_gh: MagicMock, sample_pr: dict[str, Any]
    ):
        """Given PR exists, when fetching, then details are returned."""
        from core import github

        mock_gh.return_value.stdout = json.dumps(sample_pr)

        result = github.get_pr(123)

        assert result["number"] == 123
        assert result["url"] == "https://github.com/owner/repo/pull/123"


class TestCreatePR:
    """Tests for create_pr function."""

    def test_create_pr_returns_pr_url(self, mock_gh: MagicMock):
        """Given PR created successfully, when creating, then URL is returned."""
        from core import github

        mock_gh.return_value.returncode = 0
        mock_gh.return_value.stdout = json.dumps({
            "number": 123,
            "url": "https://github.com/owner/repo/pull/123",
        })

        result = github.create_pr(
            title="[TASK-001] Feature",
            body="Description",
            base="main",
        )

        assert result["url"] == "https://github.com/owner/repo/pull/123"
        assert result["number"] == 123

    def test_create_pr_uses_correct_flags(self, mock_gh: MagicMock):
        """Given PR details, when creating, then correct flags are used."""
        from core import github

        mock_gh.return_value.stdout = json.dumps({"number": 1, "url": "url"})

        github.create_pr(
            title="[TASK-001] Feature",
            body="Description",
            base="main",
        )

        call_args = mock_gh.call_args[0][0]
        assert "pr" in call_args
        assert "create" in call_args
        assert "--title" in call_args
        assert "--body" in call_args
        assert "--base" in call_args

    def test_create_pr_raises_on_nothing_to_push(self, mock_gh: MagicMock):
        """Given no changes to push, when creating PR, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "nothing to commit"

        with pytest.raises(github.GitHubError) as exc_info:
            github.create_pr(title="Title", body="Body", base="main")

        assert "nothing to commit" in str(exc_info.value).lower() or "push" in str(exc_info.value).lower()


class TestMergePR:
    """Tests for merge_pr function."""

    def test_merge_pr_squash_by_default(self, mock_gh: MagicMock):
        """Given PR number, when merging, then squash merge is used."""
        from core import github

        mock_gh.return_value.returncode = 0

        github.merge_pr(123)

        call_args = mock_gh.call_args[0][0]
        assert "pr" in call_args
        assert "merge" in call_args
        assert "--squash" in call_args
        assert "123" in call_args

    def test_merge_pr_raises_on_conflict(self, mock_gh: MagicMock):
        """Given merge conflict, when merging PR, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "Pull request has conflicts"

        with pytest.raises(github.GitHubError):
            github.merge_pr(123)


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    def test_get_current_user_returns_login(self, mock_gh: MagicMock):
        """Given authenticated, when getting user, then login is returned."""
        from core import github

        # --jq ".login" returns the plain string, not JSON
        mock_gh.return_value.stdout = "testuser\n"

        result = github.get_current_user()

        assert result == "testuser"

    def test_get_current_user_raises_when_not_authenticated(self, mock_gh: MagicMock):
        """Given not authenticated, when getting user, then error is raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "authentication required"

        with pytest.raises(github.AuthenticationError):
            github.get_current_user()


class TestCheckAuth:
    """Tests for check_auth function."""

    def test_check_auth_returns_true_when_authenticated(self, mock_gh: MagicMock):
        """Given valid auth, when checking, then True is returned."""
        from core import github

        mock_gh.return_value.returncode = 0
        mock_gh.return_value.stdout = json.dumps({"login": "user"})

        result = github.check_auth()

        assert result is True

    def test_check_auth_returns_false_when_not_authenticated(self, mock_gh: MagicMock):
        """Given no auth, when checking, then False is returned."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "authentication required"

        result = github.check_auth()

        assert result is False


class TestAuthenticationErrors:
    """Tests for authentication error handling."""

    def test_list_issues_raises_auth_error_when_not_authenticated(
        self, mock_gh: MagicMock
    ):
        """Given gh not authenticated, when listing issues, then AuthenticationError raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "gh auth login"

        with pytest.raises(github.AuthenticationError) as exc_info:
            github.list_issues()

        assert "auth" in str(exc_info.value).lower()


class TestRateLimitErrors:
    """Tests for rate limit error handling."""

    def test_list_issues_raises_rate_limit_error(self, mock_gh: MagicMock):
        """Given rate limited, when listing issues, then RateLimitError raised."""
        from core import github

        mock_gh.return_value.returncode = 1
        mock_gh.return_value.stderr = "API rate limit exceeded"

        with pytest.raises(github.RateLimitError) as exc_info:
            github.list_issues()

        assert "rate limit" in str(exc_info.value).lower()


class TestAPICall:
    """Tests for api_call function (for low-level API access)."""

    def test_api_call_returns_json(self, mock_gh: MagicMock):
        """Given API endpoint, when calling, then JSON is returned."""
        from core import github

        mock_gh.return_value.stdout = json.dumps([{"name": "label1"}])

        result = github.api_call("repos/owner/repo/labels")

        assert len(result) == 1
        assert result[0]["name"] == "label1"

    def test_api_call_with_method(self, mock_gh: MagicMock):
        """Given method specified, when calling API, then method flag is used."""
        from core import github

        mock_gh.return_value.stdout = "{}"

        github.api_call("repos/owner/repo/labels", method="POST", fields={"name": "test"})

        call_args = mock_gh.call_args[0][0]
        assert "-X" in call_args or "--method" in call_args


class TestGitHubError:
    """Tests for GitHubError exception class."""

    def test_github_error_contains_command(self):
        """Given error, when raised, then command is included."""
        from core import github

        error = github.GitHubError("Operation failed", command=["gh", "issue", "list"])

        assert "gh" in str(error)
        assert "issue" in str(error)

    def test_github_error_contains_stderr(self):
        """Given error with stderr, when raised, then stderr is accessible."""
        from core import github

        error = github.GitHubError("Failed", stderr="detailed error message")

        assert error.stderr == "detailed error message"
