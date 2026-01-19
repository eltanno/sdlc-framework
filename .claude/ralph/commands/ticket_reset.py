"""Reset a blocked ticket to pending status.

This module handles:
- Clearing blocked status and reason
- Resetting attempt counter
- Updating workflow state
- Optional cleanup of state files

The reset operation only works on tickets with status "blocked".
Attempting to reset a ticket with any other status will raise an error.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.state import (
    load_workflow_state,
    save_workflow_state,
    get_ticket_by_id,
    get_ticket_state_dir,
    DEFAULT_STATE_DIRECTORY,
)


class TicketResetError(Exception):
    """Raised when a ticket reset operation fails.

    This exception is raised in the following scenarios:
    - The ticket does not exist
    - The ticket is not in "blocked" status
    - The state file cannot be found or read
    """

    pass


@dataclass
class ResetResult:
    """Result of a ticket reset operation.

    Attributes:
        success: Whether the reset was successful
        ticket_id: The ID of the ticket that was reset
        previous_status: The ticket's status before reset
        new_status: The ticket's status after reset (should be "pending")
        state_cleaned: Whether state files were removed
    """

    success: bool
    ticket_id: str
    previous_status: str
    new_status: str
    state_cleaned: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a dictionary for JSON output.

        Returns:
            Dictionary with reset result information, matching the shell
            script's JSON output format for backward compatibility.
        """
        return {
            "ticket": self.ticket_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "state_cleaned": self.state_cleaned,
        }


def reset_ticket(
    ticket_id: str,
    state_file: Path,
    clean_state: bool = False,
    state_base_dir: Path | None = None,
) -> ResetResult:
    """Reset a blocked ticket to pending status.

    This function:
    1. Validates the ticket exists and is blocked
    2. Updates the ticket status to "pending"
    3. Clears the block reason
    4. Resets the attempt counter to 0
    5. Optionally removes state files for a fresh start
    6. Updates the blocked count in workflow state

    Args:
        ticket_id: The ID of the ticket to reset
        state_file: Path to the workflow state JSON file
        clean_state: If True, remove the ticket's state directory
        state_base_dir: Base directory for state files (default: docs/state)

    Returns:
        ResetResult with details about the operation

    Raises:
        TicketResetError: If the ticket doesn't exist, is not blocked,
            or the state file cannot be read
    """
    # Load workflow state
    if not state_file.exists():
        raise TicketResetError(f"State file not found: {state_file}")

    try:
        workflow_state = load_workflow_state(state_file)
    except (FileNotFoundError, ValueError) as e:
        raise TicketResetError(f"Failed to load state file: {e}") from e

    # Find the ticket
    ticket = get_ticket_by_id(workflow_state, ticket_id)
    if ticket is None:
        raise TicketResetError(f"Ticket {ticket_id} not found in workflow state")

    # Check that ticket is blocked
    if ticket.status != "blocked":
        raise TicketResetError(
            f"Ticket {ticket_id} has status '{ticket.status}', "
            f"only blocked tickets can be reset"
        )

    # Store previous status for result
    previous_status = ticket.status

    # Reset the ticket
    ticket.status = "pending"
    ticket.block_reason = None
    ticket.attempts = 0

    # Update blocked count
    if workflow_state.blocked_count > 0:
        workflow_state.blocked_count -= 1

    # Save updated state
    save_workflow_state(workflow_state, state_file)

    # Optionally clean state files
    state_cleaned = False
    if clean_state:
        if state_base_dir is None:
            state_base_dir = DEFAULT_STATE_DIRECTORY

        ticket_state_dir = get_ticket_state_dir(ticket_id, state_base_dir)
        if ticket_state_dir.exists():
            shutil.rmtree(ticket_state_dir)
            state_cleaned = True

    return ResetResult(
        success=True,
        ticket_id=ticket_id,
        previous_status=previous_status,
        new_status="pending",
        state_cleaned=state_cleaned,
    )
