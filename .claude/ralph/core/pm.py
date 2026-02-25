"""PM (Project Management) tool abstraction layer.

This module provides a Protocol-based abstraction for PM tool operations,
allowing Ralph to work with different ticket tracking systems (GitHub Issues,
Trello, etc.) through a common interface.

The default implementation (GitHubPM) uses the gh CLI to interact with
GitHub Issues. All external dependencies (subprocess calls) are isolated
for easy mocking in tests.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from core.errors import CLIError

logger = logging.getLogger(__name__)


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


class PMError(CLIError):
    """Base exception for PM tool operations.

    Attributes:
        message: Error message
        command: The command that failed (if available)
        stderr: Standard error output from the command
    """

    pass


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

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a label from a ticket.

        Used for releasing claims during race condition recovery.

        Args:
            ticket_id: Unique identifier for the ticket
            label: Label to remove

        Returns:
            True if removal succeeded, False otherwise
        """
        ...

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign a ticket to the current user.

        Used when ralph.use_assignee is enabled to assign issues
        in addition to labeling.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            True if assignment succeeded, False otherwise
        """
        ...


def _run_gh_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command and return the result.

    Delegates to core.github._run_gh_command and translates exceptions
    to PM-specific error types.

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
    from core.github import (
        _run_gh_command as _github_run_gh_command,
        GitHubNotInstalledError,
        GitHubAuthError,
        GitHubError,
    )

    try:
        return _github_run_gh_command(
            args, check=check, capture_output=capture_output
        )
    except GitHubNotInstalledError as e:
        raise PMNotInstalledError(str(e), command=e.command, stderr=e.stderr) from e
    except GitHubAuthError as e:
        raise PMAuthError(str(e), command=e.command, stderr=e.stderr) from e
    except GitHubError as e:
        raise PMError(str(e), command=e.command, stderr=e.stderr) from e


class GitHubPM:
    """PM tool implementation using GitHub Issues via gh CLI.

    This implementation queries GitHub Issues for ticket status and uses
    labels for concurrency control (ralph-* labels for claiming tickets).

    Ticket IDs (like "SDLC-0052") are stored in the state file and matched
    to GitHub issues by title pattern. The title should contain [TICKET_ID]
    (e.g., "[SDLC-0052] Description").
    """

    def __init__(self, blocked_label: str = "blocked", ticket_prefix: str | None = None):
        """Initialize GitHubPM.

        Args:
            blocked_label: Label name used to mark blocked tickets
            ticket_prefix: Project ticket prefix (e.g., "SLCA") for matching
                issue titles like "[SLCA-0052] Description"
        """
        self._blocked_label = blocked_label
        self._ticket_prefix = ticket_prefix
        # Cache mapping ticket_id (e.g., "SDLC-0052") to issue_number (e.g., "102")
        self._ticket_to_issue: dict[str, str] = {}

    def _extract_ticket_id(self, title: str) -> str | None:
        """Extract ticket ID from issue title.

        When ticket_prefix is set, matches exactly [{prefix}-XXXX].
        Otherwise falls back to matching any [LETTERS-DIGITS] pattern.

        Args:
            title: Issue title

        Returns:
            Ticket ID if found, None otherwise
        """
        import re
        if self._ticket_prefix:
            pattern = rf"\[({re.escape(self._ticket_prefix)}-\d+)\]"
        else:
            pattern = r"\[([A-Z]+-\d+)\]"
        matches = re.findall(pattern, title)
        return matches[0] if matches else None

    def _find_issue_number(self, ticket_id: str) -> str | None:
        """Find GitHub issue number for a ticket ID.

        First checks the cache, then queries GitHub if not found.
        If the ticket_id is already numeric, returns it directly (backwards compat).

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number

        Returns:
            Issue number as string if found, None otherwise
        """
        # If ticket_id is already numeric, it's an issue number - return as-is
        if ticket_id.isdigit():
            return ticket_id

        # Check cache first
        if ticket_id in self._ticket_to_issue:
            return self._ticket_to_issue[ticket_id]

        # Query GitHub for issues and search by title
        args = [
            "issue",
            "list",
            "--state",
            "all",
            "--search",
            f"[{ticket_id}] in:title",
            "--json",
            "number,title",
            "--limit",
            "10",
        ]

        result = _run_gh_command(args, check=False)
        if result.returncode != 0:
            return None

        issues = json.loads(result.stdout)
        for issue in issues:
            title = issue.get("title", "")
            extracted = self._extract_ticket_id(title)
            if extracted == ticket_id:
                issue_num = str(issue.get("number", ""))
                self._ticket_to_issue[ticket_id] = issue_num
                return issue_num

        return None

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of a GitHub issue.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number

        Returns:
            TicketStatus indicating current state

        Raises:
            PMError: If operation fails or ticket not found
            PMAuthError: If not authenticated
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            # Try using ticket_id directly as issue number (backwards compat)
            issue_num = ticket_id

        args = [
            "issue",
            "view",
            issue_num,
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
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number
            label: Label to add (e.g., "ralph-1")

        Returns:
            True if claim succeeded, False otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        args = [
            "issue",
            "edit",
            issue_num,
            "--add-label",
            label,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0

    def close_ticket(self, ticket_id: str) -> bool:
        """Close a GitHub issue.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number

        Returns:
            True if close succeeded, False otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        args = [
            "issue",
            "close",
            issue_num,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark an issue as blocked with a comment.

        Adds the blocked label and posts a comment with the reason.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number
            reason: Reason why the ticket is blocked

        Returns:
            True if operation succeeded, False otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        # First add the blocked label
        label_args = [
            "issue",
            "edit",
            issue_num,
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
            issue_num,
            "--body",
            f"Blocked: {reason}",
        ]

        result = _run_gh_command(comment_args, check=False)
        return result.returncode == 0

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if an issue is claimed by any Ralph instance.

        Checks for any label starting with 'ralph-'.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number

        Returns:
            Tuple of (is_claimed, claiming_label) where claiming_label
            is the ralph-* label if claimed, None otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        args = [
            "issue",
            "view",
            issue_num,
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

        Supports two modes:
        - If ticket_ids are numeric (e.g., ["74", "75"]), matches by issue number
        - If ticket_ids are non-numeric (e.g., ["SDLC-0052"]), matches by title pattern

        Args:
            ticket_ids: List of ticket IDs or issue numbers

        Returns:
            List of TicketInfo for issues that are open
        """
        if not ticket_ids:
            return []

        # Detect if we're using ticket IDs or issue numbers
        # If all are numeric, use issue number matching (backwards compat)
        use_issue_numbers = all(tid.isdigit() for tid in ticket_ids)

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

        ticket_id_set = set(ticket_ids)
        tickets = []

        for issue in issues:
            title = issue.get("title", "")
            issue_num = str(issue.get("number", ""))

            if use_issue_numbers:
                # Old behavior: match by issue number
                if issue_num in ticket_id_set:
                    labels = [label["name"] for label in issue.get("labels", [])]

                    if self._blocked_label in labels:
                        status = TicketStatus.BLOCKED
                    else:
                        status = TicketStatus.OPEN

                    tickets.append(
                        TicketInfo(
                            id=issue_num,
                            title=title,
                            status=status,
                            labels=labels,
                        )
                    )
            else:
                # New behavior: match by ticket ID in title
                extracted_id = self._extract_ticket_id(title)

                if extracted_id and extracted_id in ticket_id_set:
                    # Cache the mapping for later use
                    self._ticket_to_issue[extracted_id] = issue_num

                    labels = [label["name"] for label in issue.get("labels", [])]

                    if self._blocked_label in labels:
                        status = TicketStatus.BLOCKED
                    else:
                        status = TicketStatus.OPEN

                    tickets.append(
                        TicketInfo(
                            id=extracted_id,  # Use ticket ID
                            title=title,
                            status=status,
                            labels=labels,
                        )
                    )

        return tickets

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a label from an issue.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number
            label: Label to remove

        Returns:
            True if removal succeeded, False otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        args = [
            "issue",
            "edit",
            issue_num,
            "--remove-label",
            label,
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign an issue to the current authenticated user.

        Uses @me to assign to the current user.

        Args:
            ticket_id: Ticket ID (e.g., "SDLC-0052") or issue number

        Returns:
            True if assignment succeeded, False otherwise
        """
        # Convert ticket_id to issue number if needed
        issue_num = self._find_issue_number(ticket_id)
        if issue_num is None:
            issue_num = ticket_id

        args = [
            "issue",
            "edit",
            issue_num,
            "--add-assignee",
            "@me",
        ]

        result = _run_gh_command(args, check=False)
        return result.returncode == 0


class LocalPM:
    """Fallback PM tool for local-only operation without external PM system.

    This implementation stores ticket state in memory only (degraded mode).
    It does not provide concurrency control or persistent state tracking.

    Use this when:
    - No PM tool is configured (pm.tool: none in config)
    - Operating in standalone mode without GitHub/Trello

    Limitations:
    - No concurrency control (claim_ticket always succeeds)
    - State is lost when the process exits
    - No real label/claim tracking
    """

    def __init__(self) -> None:
        """Initialize LocalPM with warning about degraded functionality."""
        logger.warning(
            "LocalPM initialized: Running in degraded mode without PM tool. "
            "No concurrency control or persistent state tracking available."
        )
        # Track closed and blocked tickets in memory
        self._closed_tickets: set[str] = set()
        self._blocked_tickets: set[str] = set()

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of a ticket based on local tracking.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            TicketStatus based on local state (OPEN by default)
        """
        if ticket_id in self._closed_tickets:
            return TicketStatus.CLOSED
        if ticket_id in self._blocked_tickets:
            return TicketStatus.BLOCKED
        return TicketStatus.OPEN

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a ticket (always succeeds in local mode - no concurrency control).

        Args:
            ticket_id: Unique identifier for the ticket
            label: Label to add (ignored in local mode)

        Returns:
            Always True (no real claiming mechanism)
        """
        logger.debug(
            f"LocalPM.claim_ticket: No concurrency control in local mode. "
            f"Ticket {ticket_id} with label {label} not actually claimed."
        )
        return True

    def close_ticket(self, ticket_id: str) -> bool:
        """Close a ticket by tracking it locally.

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            True (always succeeds)
        """
        self._closed_tickets.add(ticket_id)
        # Remove from blocked if it was blocked
        self._blocked_tickets.discard(ticket_id)
        return True

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark a ticket as blocked by tracking it locally.

        Args:
            ticket_id: Unique identifier for the ticket
            reason: Reason why the ticket is blocked (logged)

        Returns:
            True (always succeeds)
        """
        logger.info(f"Ticket {ticket_id} blocked: {reason}")
        self._blocked_tickets.add(ticket_id)
        return True

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if a ticket is claimed (always returns False in local mode).

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            Always (False, None) - no claiming mechanism in local mode
        """
        return (False, None)

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open tickets from the provided list.

        Args:
            ticket_ids: List of ticket IDs to check

        Returns:
            List of TicketInfo for tickets that are not closed/blocked
        """
        if not ticket_ids:
            return []

        tickets = []
        for ticket_id in ticket_ids:
            status = self.get_ticket_status(ticket_id)
            if status == TicketStatus.OPEN:
                tickets.append(
                    TicketInfo(
                        id=ticket_id,
                        title=f"Local ticket {ticket_id}",
                        status=TicketStatus.OPEN,
                        labels=[],
                    )
                )
        return tickets

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a label from a ticket (no-op in local mode).

        Args:
            ticket_id: Unique identifier for the ticket
            label: Label to remove (ignored)

        Returns:
            Always True (no real label mechanism)
        """
        return True

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign a ticket to self (no-op in local mode).

        Args:
            ticket_id: Unique identifier for the ticket

        Returns:
            Always True (no real assignment mechanism)
        """
        logger.debug(
            f"LocalPM.assign_to_self: No assignment mechanism in local mode. "
            f"Ticket {ticket_id} not actually assigned."
        )
        return True
