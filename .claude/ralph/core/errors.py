"""Base error classes for Ralph CLI wrappers.

Provides CLIError as a shared base for all CLI-related exceptions
(PMError, GitHubError, GitError, GitLabError). Each stores the
failed command and stderr output alongside the human-readable message.
"""

from __future__ import annotations


class CLIError(Exception):
    """Base exception for CLI tool operations.

    All CLI wrapper modules (git, github, gitlab, pm) use subclasses
    of this class so callers can catch broad or narrow error types.

    Attributes:
        command: The command that failed (if available)
        stderr: Standard error output from the command
    """

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        stderr: str | None = None,
    ):
        self.command = command
        self.stderr = stderr
        if command:
            full_message = f"{message}: {' '.join(command)}"
        else:
            full_message = message
        if stderr:
            full_message = f"{full_message}\n{stderr}"
        super().__init__(full_message)
