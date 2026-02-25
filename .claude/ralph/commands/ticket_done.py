"""Mark a ticket as complete.

This module handles:
- Closing tickets via PM tool
- Removing in-progress/instance labels via PM tool
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from core.pm import PMTool

logger = logging.getLogger(__name__)


def ticket_done(
    ticket_id: str,
    pr_number: str | None = None,
    issue_number: int | None = None,
    config_file: "Path | None" = None,
    pm_tool: "PMTool | None" = None,
    ralph_label: str | None = None,
) -> dict[str, Any]:
    """Complete a ticket via PM tool operations.

    Args:
        ticket_id: The ticket identifier to complete
        pr_number: Optional PR number
        issue_number: Optional issue number (kept for interface compatibility)
        config_file: Unused, kept for interface compatibility
        pm_tool: PM tool instance (required for actual updates)
        ralph_label: Optional label to remove from the ticket (e.g., "ralph-1")

    Returns:
        Dictionary with completion details
    """
    actual_issue_number = issue_number

    if pm_tool is not None:
        # Remove instance label first (if provided)
        if ralph_label:
            pm_tool.remove_label(ticket_id, ralph_label)

        # Close the ticket (idempotent - handles already closed)
        pm_tool.close_ticket(ticket_id)
    else:
        logger.warning(
            "ticket_done called without pm_tool for %s; no PM updates performed",
            ticket_id,
        )

    return {
        "ticket_id": ticket_id,
        "status": "completed",
        "pr_number": pr_number,
        "issue_number": actual_issue_number,
    }
