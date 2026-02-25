"""Mark a ticket as blocked.

This module handles:
- Setting blocked status with reason via PM tool
- Adding blocked labels
- Removing instance labels
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.pm import PMTool

logger = logging.getLogger(__name__)


def mark_blocked(
    ticket_id: str,
    reason: str,
    issue_number: int | None = None,
    pm_tool: "PMTool | None" = None,
    ralph_label: str | None = None,
) -> dict[str, Any]:
    """Mark a ticket as blocked with a reason.

    Updates the corresponding PM tool ticket with a blocked label and comment.
    No local state file is modified.

    Args:
        ticket_id: The ticket identifier (e.g., "TASK-001")
        reason: The reason for blocking the ticket
        issue_number: Optional issue number (kept for interface compatibility)
        pm_tool: PM tool instance for PM operations (required for actual updates)
        ralph_label: Optional ralph instance label to remove when blocking

    Returns:
        Dictionary containing:
        - blocked_ticket: The ticket ID that was blocked
        - reason: The blocking reason
        - issue_number: The issue number (or None)
        - timestamp: When the ticket was blocked

    Raises:
        ValueError: If ticket_id is empty
    """
    # Validate inputs
    if not ticket_id:
        raise ValueError("ticket_id is required")

    if not reason:
        reason = "Unknown reason"

    # Use PM tool if provided
    if pm_tool is not None:
        _update_issue_via_pm_tool(pm_tool, ticket_id, reason, ralph_label)
    else:
        logger.warning(
            "mark_blocked called without pm_tool for %s; no PM updates performed",
            ticket_id,
        )

    # Build result
    result = {
        "blocked_ticket": ticket_id,
        "reason": reason,
        "issue_number": issue_number,
        "timestamp": datetime.now().isoformat(),
    }

    return result


def _update_issue_via_pm_tool(
    pm_tool: "PMTool",
    ticket_id: str,
    reason: str,
    ralph_label: str | None = None,
) -> None:
    """Update a ticket via PM tool abstraction layer.

    Uses the PM tool to:
    1. Add blocked label and comment (via add_blocked_label)
    2. Remove ralph instance label if provided (via remove_label)

    Operations continue even if individual steps fail.

    Args:
        pm_tool: PM tool instance implementing PMTool protocol
        ticket_id: The ticket ID (issue number as string)
        reason: The blocking reason
        ralph_label: Optional ralph instance label to remove
    """
    # Add blocked label and comment via PM tool
    pm_tool.add_blocked_label(ticket_id, reason)

    # Remove instance label if provided
    if ralph_label:
        pm_tool.remove_label(ticket_id, ralph_label)
