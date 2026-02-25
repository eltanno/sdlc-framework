"""Tests for core.errors module.

Tests the CLIError base class used by PMError, GitHubError, GitError, GitLabError.
"""

from core.errors import CLIError


class TestCLIError:
    """Tests for CLIError base class."""

    def test_message_only(self):
        """Given just a message, str() returns just the message."""
        err = CLIError("something failed")
        assert str(err) == "something failed"
        assert err.command is None
        assert err.stderr is None

    def test_message_with_command(self):
        """Given message and command, str() includes command string."""
        err = CLIError("failed", command=["gh", "issue", "list"])
        assert "failed" in str(err)
        assert "gh issue list" in str(err)

    def test_message_with_stderr(self):
        """Given message and stderr, str() includes stderr."""
        err = CLIError("failed", stderr="permission denied")
        assert "failed" in str(err)
        assert "permission denied" in str(err)

    def test_message_with_command_and_stderr(self):
        """Given message, command, and stderr, str() includes all three."""
        err = CLIError("failed", command=["git", "push"], stderr="rejected")
        result = str(err)
        assert "failed" in result
        assert "git push" in result
        assert "rejected" in result

    def test_stores_command_attribute(self):
        """Given a command, stores it as attribute."""
        cmd = ["gh", "pr", "create"]
        err = CLIError("failed", command=cmd)
        assert err.command == cmd

    def test_stores_stderr_attribute(self):
        """Given stderr, stores it as attribute."""
        err = CLIError("failed", stderr="error output")
        assert err.stderr == "error output"

    def test_is_exception(self):
        """CLIError is an Exception."""
        err = CLIError("test")
        assert isinstance(err, Exception)


class TestCLIErrorSubclasses:
    """Tests that all error subclasses properly inherit from CLIError."""

    def test_pm_error_is_cli_error(self):
        from core.pm import PMError
        err = PMError("test")
        assert isinstance(err, CLIError)
        assert isinstance(err, Exception)

    def test_github_error_is_cli_error(self):
        from core.github import GitHubError
        err = GitHubError("test")
        assert isinstance(err, CLIError)

    def test_git_error_is_cli_error(self):
        from core.git import GitError
        err = GitError("test")
        assert isinstance(err, CLIError)

    def test_gitlab_error_is_cli_error(self):
        from core.gitlab import GitLabError
        err = GitLabError("test")
        assert isinstance(err, CLIError)

    def test_pm_error_with_command_and_stderr(self):
        from core.pm import PMError
        err = PMError("failed", command=["gh", "issue"], stderr="err")
        assert err.command == ["gh", "issue"]
        assert err.stderr == "err"
        assert "failed" in str(err)
        assert "gh issue" in str(err)
        assert "err" in str(err)

    def test_github_not_installed_error_inheritance(self):
        from core.github import GitHubNotInstalledError, GitHubError
        err = GitHubNotInstalledError("gh not found")
        assert isinstance(err, GitHubError)
        assert isinstance(err, CLIError)

    def test_pm_not_installed_error_inheritance(self):
        from core.pm import PMNotInstalledError, PMError
        err = PMNotInstalledError("gh not found")
        assert isinstance(err, PMError)
        assert isinstance(err, CLIError)

    def test_git_not_installed_error_inheritance(self):
        from core.git import GitNotInstalledError, GitError
        err = GitNotInstalledError("git not found")
        assert isinstance(err, GitError)
        assert isinstance(err, CLIError)

    def test_gitlab_not_installed_error_inheritance(self):
        from core.gitlab import GitLabNotInstalledError, GitLabError
        err = GitLabNotInstalledError("glab not found")
        assert isinstance(err, GitLabError)
        assert isinstance(err, CLIError)
