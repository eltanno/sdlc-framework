"""Display current workflow status.

This module handles:
- Reading workflow state
- Showing ticket counts by status
- Highlighting active work
- Showing blocked tickets with reasons
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def get_workflow_status(state_file: Path) -> StatusResult:
    """Get the current workflow status.

    Reads the workflow state file and returns a structured status result.

    Args:
        state_file: Path to the workflow state JSON file

    Returns:
        StatusResult with workflow status information

    Note:
        If the state file doesn't exist, returns a result with initialized=False.
    """
    # Check if state file exists
    if not state_file.exists():
        return StatusResult(
            initialized=False,
            tickets_by_status={},
            total_tickets=0,
            current_ticket=None,
            blocked_tickets=[],
            prd_path=None,
            plan_path=None,
        )

    # Load state file
    try:
        data = json.loads(state_file.read_text())
    except json.JSONDecodeError:
        return StatusResult(
            initialized=False,
            tickets_by_status={},
            total_tickets=0,
            current_ticket=None,
            blocked_tickets=[],
            prd_path=None,
            plan_path=None,
        )

    tickets = data.get("tickets", [])
    current_ticket_id = data.get("current_ticket")

    # Count tickets by status
    tickets_by_status: dict[str, int] = {}
    for ticket in tickets:
        status = ticket.get("status", "unknown")
        tickets_by_status[status] = tickets_by_status.get(status, 0) + 1

    # Find current ticket details
    current_ticket = None
    if current_ticket_id:
        for ticket in tickets:
            if ticket.get("id") == current_ticket_id:
                current_ticket = {
                    "id": ticket.get("id"),
                    "title": ticket.get("title"),
                    "attempts": ticket.get("attempts", 0),
                }
                break

    # Find blocked tickets
    blocked_tickets = []
    for ticket in tickets:
        if ticket.get("status") == "blocked":
            blocked_tickets.append({
                "id": ticket.get("id"),
                "title": ticket.get("title"),
                "block_reason": ticket.get("block_reason", "No reason provided"),
            })

    return StatusResult(
        initialized=True,
        tickets_by_status=tickets_by_status,
        total_tickets=len(tickets),
        current_ticket=current_ticket,
        blocked_tickets=blocked_tickets,
        prd_path=data.get("prd_path"),
        plan_path=data.get("plan_path"),
    )


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
