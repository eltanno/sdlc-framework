"""Reset a blocked ticket for retry.

This module handles:
- Cleaning up state files (attempt directories) for a fresh start
- Providing reset result information

The actual blocked/unblocked status is managed via PM tool labels,
not local state files. This module focuses on filesystem cleanup.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.state import (
    get_ticket_state_dir,
    DEFAULT_STATE_DIRECTORY,
)


class TicketResetError(Exception):
    """Raised when a ticket reset operation fails.

    This exception is raised in the following scenarios:
    - The ticket ID is empty
    """

    pass


@dataclass
class ResetResult:
    """Result of a ticket reset operation.

    Attributes:
        success: Whether the reset was successful
        ticket_id: The ID of the ticket that was reset
        state_cleaned: Whether state files were removed
    """

    success: bool
    ticket_id: str
    state_cleaned: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a dictionary for JSON output."""
        return {
            "ticket": self.ticket_id,
            "state_cleaned": self.state_cleaned,
        }


def reset_ticket(
    ticket_id: str,
    clean_state: bool = True,
    state_base_dir: Path | None = None,
) -> ResetResult:
    """Reset a ticket by cleaning up its state files.

    This function removes the ticket's attempt directories so that
    Ralph treats it as a fresh ticket on the next run. The actual
    blocked/unblocked status is managed via PM tool labels.

    Args:
        ticket_id: The ID of the ticket to reset
        clean_state: If True, remove the ticket's state directory
        state_base_dir: Base directory for state files (default: docs/state)

    Returns:
        ResetResult with details about the operation

    Raises:
        TicketResetError: If the ticket_id is empty
    """
    if not ticket_id:
        raise TicketResetError("ticket_id is required")

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
        state_cleaned=state_cleaned,
    )
