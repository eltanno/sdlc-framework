"""Display current workflow status.

This module handles:
- Reading workflow state via core.state.load_workflow_state()
- Showing ticket counts by status
- Highlighting active work
- Showing blocked tickets with reasons
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.state import WorkflowState, load_workflow_state

# Default block reason when none is provided on a blocked ticket.
_DEFAULT_BLOCK_REASON = "No reason provided"


@dataclass
class StatusResult:
    """Result of a status check.

    Attributes:
        initialized: Whether a workflow is active
        tickets_by_status: Count of tickets by status (pending, in_progress, completed, blocked)
        total_tickets: Total number of tickets in the workflow
        current_ticket: Details of the current in-progress ticket (if any)
        blocked_tickets: List of blocked tickets with reasons
        prd_path: Path to the PRD document
        plan_path: Path to the plan document
    """

    initialized: bool
    tickets_by_status: dict[str, int]
    total_tickets: int
    current_ticket: dict[str, Any] | None
    blocked_tickets: list[dict[str, Any]]
    prd_path: str | None
    plan_path: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "initialized": self.initialized,
            "tickets_by_status": self.tickets_by_status,
            "total_tickets": self.total_tickets,
            "current_ticket": self.current_ticket,
            "blocked_tickets": self.blocked_tickets,
            "prd_path": self.prd_path,
            "plan_path": self.plan_path,
        }


def _empty_status() -> StatusResult:
    """Return a StatusResult representing an uninitialized workflow."""
    return StatusResult(
        initialized=False,
        tickets_by_status={},
        total_tickets=0,
        current_ticket=None,
        blocked_tickets=[],
        prd_path=None,
        plan_path=None,
    )


def _status_from_workflow(state: WorkflowState) -> StatusResult:
    """Build a StatusResult from a loaded WorkflowState.

    Args:
        state: Loaded workflow state from core.state.

    Returns:
        StatusResult populated from the workflow state.
    """
    tickets = state.tickets

    # Count tickets by status
    tickets_by_status: dict[str, int] = {}
    for ticket in tickets:
        tickets_by_status[ticket.status] = tickets_by_status.get(ticket.status, 0) + 1

    # Find current ticket details
    current_ticket = None
    if state.current_ticket:
        for ticket in tickets:
            if ticket.id == state.current_ticket:
                current_ticket = {
                    "id": ticket.id,
                    "title": ticket.title,
                    "attempts": ticket.attempts,
                }
                break

    # Find blocked tickets
    blocked_tickets = []
    for ticket in tickets:
        if ticket.status == "blocked":
            blocked_tickets.append({
                "id": ticket.id,
                "title": ticket.title,
                "block_reason": ticket.block_reason or _DEFAULT_BLOCK_REASON,
            })

    return StatusResult(
        initialized=True,
        tickets_by_status=tickets_by_status,
        total_tickets=len(tickets),
        current_ticket=current_ticket,
        blocked_tickets=blocked_tickets,
        prd_path=str(state.prd_path),
        plan_path=str(state.plan_path),
    )


def get_workflow_status(state_file: Path) -> StatusResult:
    """Get the current workflow status.

    Delegates to core.state.load_workflow_state() for canonical JSON parsing,
    catching its exceptions to return safe defaults for missing or corrupt files.

    Args:
        state_file: Path to the workflow state JSON file

    Returns:
        StatusResult with workflow status information

    Note:
        If the state file doesn't exist or is invalid, returns initialized=False.
    """
    try:
        state = load_workflow_state(state_file)
    except (FileNotFoundError, ValueError, KeyError):
        return _empty_status()

    return _status_from_workflow(state)


def format_status_display(status: StatusResult) -> str:
    """Format status result for display.

    Creates a human-readable formatted string showing the workflow status,
    including ticket counts, current ticket, and any blocked tickets.

    Args:
        status: StatusResult object to format

    Returns:
        Formatted string for display
    """
    lines: list[str] = []

    if not status.initialized:
        lines.append("=" * 40)
        lines.append("         RALPH STATUS")
        lines.append("=" * 40)
        lines.append("")
        lines.append("No active workflow found.")
        lines.append("Ralph has not been initialized.")
        lines.append("")
        lines.append("To start a workflow, run:")
        lines.append("  ralph <prd-path> <plan-path>")
        lines.append("")
        lines.append("=" * 40)
        return "\n".join(lines)

    # Header
    lines.append("=" * 40)
    lines.append("         RALPH STATUS")
    lines.append("=" * 40)
    lines.append("")

    # Document paths
    if status.prd_path:
        lines.append(f"PRD:              {status.prd_path}")
    if status.plan_path:
        lines.append(f"Plan:             {status.plan_path}")
    lines.append("")

    # Progress summary
    completed = status.tickets_by_status.get("completed", 0)
    total = status.total_tickets
    lines.append(f"Progress          {completed}/{total}")
    lines.append("")

    # Current ticket
    if status.current_ticket:
        lines.append("Current Ticket")
        lines.append(f"  ID              {status.current_ticket['id']}")
        lines.append(f"  Title           {status.current_ticket['title']}")
        lines.append(f"  Attempts        {status.current_ticket['attempts']}")
        lines.append("")

    # Ticket counts by status
    lines.append("Ticket Status")
    lines.append(f"  Completed       {status.tickets_by_status.get('completed', 0)}")
    lines.append(f"  In Progress     {status.tickets_by_status.get('in_progress', 0)}")
    lines.append(f"  Pending         {status.tickets_by_status.get('pending', 0)}")
    lines.append(f"  Blocked         {status.tickets_by_status.get('blocked', 0)}")
    lines.append("")

    # Blocked tickets
    if status.blocked_tickets:
        lines.append("Blocked Tickets:")
        for ticket in status.blocked_tickets:
            lines.append(f"  {ticket['id']}: {ticket['block_reason']}")
        lines.append("")

    lines.append("=" * 40)

    return "\n".join(lines)


def display_status(state_file: Path) -> str:
    """Get and display the workflow status.

    This is the main entry point for the status command.

    Args:
        state_file: Path to the workflow state JSON file

    Returns:
        Formatted status string
    """
    status = get_workflow_status(state_file)
    return format_status_display(status)


def get_status_json(state_file: Path) -> dict[str, Any]:
    """Get the workflow status as a dictionary.

    Useful for programmatic access to status information.

    Args:
        state_file: Path to the workflow state JSON file

    Returns:
        Dictionary with status information
    """
    status = get_workflow_status(state_file)
    return status.to_dict()
