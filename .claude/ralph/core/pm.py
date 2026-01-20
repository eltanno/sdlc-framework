"""PM (Project Management) tool abstraction layer.

This module provides a Protocol-based abstraction for PM tool operations,
allowing Ralph to work with different ticket tracking systems (GitHub Issues,
Trello, etc.) through a common interface.

The default implementation (GitHubPM) uses the gh CLI to interact with
GitHub Issues. All external dependencies (subprocess calls) are isolated
for easy mocking in tests.
"""

import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class TicketStatus(Enum):
    """Status of a ticket in the PM tool.

    Values:
        OPEN: Ticket is open and available for work
        CLOSED: Ticket is closed/completed
        BLOCKED: Ticket is blocked (has blocked label)
    """

    OPEN = "open"
    CLOSED = "closed"
    BLOCKED = "blocked"


@dataclass
class TicketInfo:
    """Information about a ticket from the PM tool.

    Attributes:
        id: Unique identifier for the ticket (e.g., issue number as string)
        title: Ticket title/summary
        status: Current status of the ticket
        labels: List of label names attached to the ticket
    """

    id: str
    title: str
    status: TicketStatus
    labels: list[str] = field(default_factory=list)


class PMError(Exception):
    """Base exception for PM tool operations.

    Attributes:
        message: Error message
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


class PMNotInstalledError(PMError):
    """Raised when the PM tool CLI is not installed or not found."""

    pass


class PMAuthError(PMError):
    """Raised when the PM tool CLI is not authenticated."""

    pass


class PMTool(Protocol):
    """Protocol defining the interface for PM tool implementations.

    All PM tools must implement these methods to be compatible with Ralph.
    This uses structural typing (duck typing) - no inheritance required.
    """

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of a ticket.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            TicketStatus indicating current state

        Raises:
            PMError: If operation fails
        """
        ...

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a ticket by adding a label.

        Args:
            ticket_id: Unique identifier for the ticket
            label: Label to add (e.g., "ralph-1")

        Returns:
            True if claim succeeded, False otherwise
        """
        ...

    def close_ticket(self, ticket_id: str) -> bool:
        """Close/complete a ticket.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            True if close succeeded, False otherwise
        """
        ...

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark a ticket as blocked with a reason.

        Args:
            ticket_id: Unique identifier for the ticket
            reason: Reason why the ticket is blocked

        Returns:
            True if operation succeeded, False otherwise
        """
        ...

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if a ticket is claimed by any Ralph instance.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            Tuple of (is_claimed, claiming_label) where claiming_label
            is the ralph-* label if claimed, None otherwise
        """
        ...

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open tickets from the provided list.

        Args:
            ticket_ids: List of ticket IDs to check

        Returns:
            List of TicketInfo for tickets that are open
        """
        ...


def _run_gh_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command and return the result.

    Args:
        args: Command arguments (without 'gh' prefix)
        check: If True, raise PMError on non-zero exit code
        capture_output: If True, capture stdout and stderr

    Returns:
        CompletedProcess with stdout, stderr, and returncode

    Raises:
        PMNotInstalledError: If gh is not installed
        PMAuthError: If gh is not authenticated
        PMError: For other gh command failures
    """
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
        )
    except FileNotFoundError:
        raise PMNotInstalledError(
            "GitHub CLI (gh) is not installed. Please install it from https://cli.github.com/",
            command=cmd,
        )

    if check and result.returncode != 0:
        stderr = result.stderr if result.stderr else ""

        # Check for authentication errors
        if (
            "GH_TOKEN" in stderr
            or "not logged in" in stderr
            or "authentication" in stderr.lower()
        ):
            raise PMAuthError(
                "GitHub CLI is not authenticated. Run 'gh auth login' to authenticate.",
                command=cmd,
                stderr=stderr,
            )

        raise PMError(
            f"GitHub CLI command failed with exit code {result.returncode}",
            command=cmd,
            stderr=stderr,
        )

    return result


class GitHubPM:
    """PM tool implementation using GitHub Issues via gh CLI.

    This implementation queries GitHub Issues for ticket status and uses
    labels for concurrency control (ralph-* labels for claiming tickets).
    """

    def __init__(self, blocked_label: str = "blocked"):
        """Initialize GitHubPM.

        Args:
            blocked_label: Label name used to mark blocked tickets
        """
        self._blocked_label = blocked_label

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of a GitHub issue.

        Args:
            ticket_id: Issue number as string

        Returns:
            TicketStatus indicating current state

        Raises:
            PMError: If operation fails
            PMAuthError: If not authenticated
        """
        args = [
            "issue",
            "view",
            ticket_id,
            "--json",
            "number,title,state,labels",
        ]

        result = _run_gh_command(args)
        issue = json.loads(result.stdout)

        # Check for blocked label first
        labels = [label["name"] for label in issue.get("labels", [])]
        if self._blocked_label in labels:
            return TicketStatus.BLOCKED

        # Check state
        state = issue.get("state", "").upper()
        if state == "CLOSED":
            return TicketStatus.CLOSED

        return TicketStatus.OPEN

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a ticket by adding a label.

        Args:
            ticket_id: Issue number as string
            label: Label to add (e.g., "ralph-1")

        Returns:
            True if claim succeeded, False otherwise
        """
        args = [
            "issue",
            "edit",
            ticket_id,
            "--add-label",
            label,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0

    def close_ticket(self, ticket_id: str) -> bool:
        """Close a GitHub issue.

        Args:
            ticket_id: Issue number as string

        Returns:
            True if close succeeded, False otherwise
        """
        args = [
            "issue",
            "close",
            ticket_id,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark an issue as blocked with a comment.

        Adds the blocked label and posts a comment with the reason.

        Args:
            ticket_id: Issue number as string
            reason: Reason why the ticket is blocked

        Returns:
            True if operation succeeded, False otherwise
        """
        # First add the blocked label
        label_args = [
            "issue",
            "edit",
            ticket_id,
            "--add-label",
            self._blocked_label,
        ]

        result = _run_gh_command(label_args, check=False)
        if result.returncode != 0:
            return False

        # Then add a comment with the reason
        comment_args = [
            "issue",
            "comment",
            ticket_id,
            "--body",
            f"Blocked: {reason}",
        ]

        result = _run_gh_command(comment_args, check=False)
        return result.returncode == 0

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if an issue is claimed by any Ralph instance.

        Checks for any label starting with 'ralph-'.

        Args:
            ticket_id: Issue number as string

        Returns:
            Tuple of (is_claimed, claiming_label) where claiming_label
            is the ralph-* label if claimed, None otherwise
        """
        args = [
            "issue",
            "view",
            ticket_id,
            "--json",
            "number,labels",
        ]

        result = _run_gh_command(args, check=False)
        if result.returncode != 0:
            return (False, None)

        issue = json.loads(result.stdout)
        labels = issue.get("labels", [])

        for label in labels:
            label_name = label.get("name", "")
            if label_name.startswith("ralph-"):
                return (True, label_name)

        return (False, None)

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open issues from the provided list.

        Args:
            ticket_ids: List of issue numbers as strings

        Returns:
            List of TicketInfo for issues that are open
        """
        if not ticket_ids:
            return []

        # List all open issues
        args = [
            "issue",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,state,labels",
        ]

        result = _run_gh_command(args, check=False)
        if result.returncode != 0:
            return []

        issues = json.loads(result.stdout)

        # Filter to only issues in our ticket_ids list
        ticket_id_set = set(ticket_ids)
        tickets = []

        for issue in issues:
            issue_id = str(issue.get("number", ""))
            if issue_id in ticket_id_set:
                labels = [label["name"] for label in issue.get("labels", [])]

                # Determine status
                if self._blocked_label in labels:
                    status = TicketStatus.BLOCKED
                else:
                    status = TicketStatus.OPEN

                tickets.append(
                    TicketInfo(
                        id=issue_id,
                        title=issue.get("title", ""),
                        status=status,
                        labels=labels,
                    )
                )

        return tickets

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a label from an issue.

        Args:
            ticket_id: Issue number as string
            label: Label to remove

        Returns:
            True if removal succeeded, False otherwise
        """
        args = [
            "issue",
            "edit",
            ticket_id,
            "--remove-label",
            label,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0
