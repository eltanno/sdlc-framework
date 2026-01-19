"""Start work on a ticket.

This module handles:
- Creating feature branches for tickets
- Checking out existing branches if they already exist
- Updating workflow state to mark ticket as in_progress

The branch naming convention is: feature/{ticket_id}-{description}
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core import git
from core.state import (
    load_workflow_state,
    save_workflow_state,
    get_ticket_by_id,
)


class TicketStartError(Exception):
    """Base exception for ticket start operations.

    Attributes:
        message: Error message
        ticket_id: The ticket that failed to start (if applicable)
    """

    def __init__(self, message: str, ticket_id: str | None = None):
        self.ticket_id = ticket_id
        super().__init__(message)


class DirtyWorkingDirectoryError(TicketStartError):
    """Raised when there are uncommitted changes in the working directory.

    This prevents branch creation to avoid potential data loss.
    """

    pass


class TicketNotFoundError(TicketStartError):
    """Raised when the specified ticket doesn't exist in the state file."""

    pass


@dataclass
class TicketStartResult:
    """Result of starting a ticket.

    Attributes:
        ticket_id: The ticket that was started
        branch: The branch name for the ticket
        status: The new status (always "in_progress")
        created_new_branch: True if a new branch was created, False if existing
    """

    ticket_id: str
    branch: str
    status: str
    created_new_branch: bool


def generate_branch_name(ticket_id: str, suffix: str = "implementation") -> str:
    """Generate a feature branch name for a ticket.

    Args:
        ticket_id: The ticket identifier (e.g., "TASK-001", "SDLC-0022")
        suffix: Branch name suffix (default: "implementation")

    Returns:
        Branch name in format: feature/{ticket_id}-{suffix}

    Examples:
        >>> generate_branch_name("TASK-001")
        'feature/TASK-001-implementation'
        >>> generate_branch_name("SDLC-0022", "auth-feature")
        'feature/SDLC-0022-auth-feature'
    """
    return f"feature/{ticket_id}-{suffix}"


def start_ticket(
    ticket_id: str,
    state_file: Path,
    start_point: str = "origin/main",
) -> TicketStartResult:
    """Start work on a ticket by creating or checking out its feature branch.

    This function performs the following steps:
    1. Checks for uncommitted changes (fails if dirty)
    2. Loads the workflow state and validates the ticket
    3. Creates a new branch or checks out an existing one
    4. Updates the workflow state to mark the ticket as in_progress

    Args:
        ticket_id: The ticket identifier to start (e.g., "TASK-001")
        state_file: Path to the workflow state JSON file
        start_point: Git ref to branch from for new branches (default: origin/main)

    Returns:
        TicketStartResult with branch name, status, and whether branch was created

    Raises:
        DirtyWorkingDirectoryError: If there are uncommitted changes
        TicketNotFoundError: If the ticket doesn't exist in state
        TicketStartError: If the ticket is already completed or blocked
    """
    # Step 1: Check for uncommitted changes
    if git.is_dirty():
        status = git.get_status()
        modified = status.modified
        untracked = status.untracked
        raise DirtyWorkingDirectoryError(
            f"Cannot start ticket {ticket_id}: uncommitted changes detected. "
            f"Modified: {modified}, Untracked: {untracked}",
            ticket_id=ticket_id,
        )

    # Step 2: Load and validate state
    state = load_workflow_state(state_file)
    ticket = get_ticket_by_id(state, ticket_id)

    if ticket is None:
        raise TicketNotFoundError(
            f"Ticket {ticket_id} not found in workflow state",
            ticket_id=ticket_id,
        )

    # Validate ticket status
    if ticket.status == "completed":
        raise TicketStartError(
            f"Ticket {ticket_id} is already completed. Cannot restart a completed ticket.",
            ticket_id=ticket_id,
        )

    if ticket.status == "blocked":
        raise TicketStartError(
            f"Ticket {ticket_id} is blocked: {ticket.block_reason}. "
            "Use ticket_reset to unblock before starting.",
            ticket_id=ticket_id,
        )

    # Step 3: Create or checkout branch
    branch_name = generate_branch_name(ticket_id)
    current_branch = git.get_current_branch()
    created_new_branch = False

    # Check if we're already on the correct branch
    if current_branch == branch_name:
        # Already on the correct branch - no action needed
        pass
    elif git.branch_exists(branch_name):
        # Branch exists - check it out
        git.checkout_branch(branch_name)
    else:
        # Create new branch from start_point
        git.create_branch(branch_name, start_point)
        created_new_branch = True

    # Step 4: Update workflow state
    ticket.status = "in_progress"
    state.current_ticket = ticket_id
    save_workflow_state(state, state_file)

    return TicketStartResult(
        ticket_id=ticket_id,
        branch=branch_name,
        status="in_progress",
        created_new_branch=created_new_branch,
    )
