"""Get the next eligible ticket to work on.

This module finds the next ticket based on:
- Ticket status (pending, not blocked)
- Dependency satisfaction
- Priority ordering (first by order in the list)

The get_next_ticket function returns a GetNextResult dataclass that contains:
- The next ticket to work on (or None if no eligible tickets)
- Status information (ready, complete, waiting_on_dependencies, all_blocked)
- Counts of tickets by status
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.state import WorkflowState, Ticket


@dataclass
class GetNextResult:
    """Result of getting the next ticket.

    Attributes:
        ticket: The next eligible ticket, or None if no eligible tickets
        status: Status of the search ("ready", "complete", "waiting_on_dependencies", "all_blocked")
        message: Human-readable message describing the result
        has_more: Whether there are more tickets to process
        total: Total number of tickets
        pending: Number of pending tickets
        completed: Number of completed tickets
        blocked: Number of blocked tickets
        in_progress: Number of in-progress tickets
        skipped_for_deps: Number of tickets skipped due to unmet dependencies
    """

    ticket: Ticket | None
    status: str
    message: str
    has_more: bool
    total: int = 0
    pending: int = 0
    completed: int = 0
    blocked: int = 0
    in_progress: int = 0
    skipped_for_deps: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "next_ticket": self.ticket.id if self.ticket else None,
            "ticket_title": self.ticket.title if self.ticket else None,
            "status": self.status,
            "message": self.message,
            "has_more": self.has_more,
            "total": self.total,
            "pending": self.pending,
            "completed": self.completed,
            "blocked": self.blocked,
            "in_progress": self.in_progress,
            "skipped_for_deps": self.skipped_for_deps,
        }


def is_ticket_eligible(ticket: Ticket, completed_ids: set[str]) -> bool:
    """Check if a ticket is eligible to be worked on.

    A ticket is eligible if:
    1. Its status is "pending" or "in_progress" (to resume)
    2. All its dependencies have been completed

    Args:
        ticket: The ticket to check
        completed_ids: Set of ticket IDs that have been completed

    Returns:
        True if the ticket is eligible, False otherwise
    """
    # Not eligible if completed or blocked
    if ticket.status in ("completed", "blocked"):
        return False

    # Pending or in_progress tickets are potentially eligible
    if ticket.status not in ("pending", "in_progress"):
        return False

    # Check if all dependencies are satisfied
    if ticket.dependencies:
        for dep_id in ticket.dependencies:
            if dep_id not in completed_ids:
                return False

    return True


def get_ticket_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Get counts of tickets by status.

    Args:
        tickets: List of tickets to count

    Returns:
        Dictionary with counts: total, pending, completed, blocked, in_progress
    """
    counts = {
        "total": len(tickets),
        "pending": 0,
        "completed": 0,
        "blocked": 0,
        "in_progress": 0,
    }

    for ticket in tickets:
        if ticket.status == "pending":
            counts["pending"] += 1
        elif ticket.status == "completed":
            counts["completed"] += 1
        elif ticket.status == "blocked":
            counts["blocked"] += 1
        elif ticket.status == "in_progress":
            counts["in_progress"] += 1

    return counts


def get_next_ticket(state: WorkflowState) -> GetNextResult:
    """Find the next eligible ticket to work on.

    The selection algorithm:
    1. First, check for in-progress tickets (to resume work)
    2. Then, find pending tickets with all dependencies satisfied
    3. Skip blocked tickets
    4. Return first eligible ticket by order in the list

    Args:
        state: The current workflow state

    Returns:
        GetNextResult containing the next ticket and status information
    """
    # Get ticket counts
    counts = get_ticket_counts(state.tickets)

    # Handle empty workflow
    if not state.tickets:
        return GetNextResult(
            ticket=None,
            status="complete",
            message="No tickets in workflow",
            has_more=False,
            **counts,
            skipped_for_deps=0,
        )

    # Build set of completed ticket IDs for dependency checking
    completed_ids: set[str] = set()
    for ticket in state.tickets:
        if ticket.status == "completed":
            completed_ids.add(ticket.id)

    # Track tickets skipped due to dependencies
    skipped_for_deps = 0

    # First priority: check for in-progress tickets (to resume)
    for ticket in state.tickets:
        if ticket.status == "in_progress":
            return GetNextResult(
                ticket=ticket,
                status="ready",
                message=f"Resuming in-progress ticket: {ticket.id}",
                has_more=True,
                **counts,
                skipped_for_deps=0,
            )

    # Second priority: find pending tickets with satisfied dependencies
    for ticket in state.tickets:
        if ticket.status == "blocked":
            continue

        if ticket.status != "pending":
            continue

        # Check if dependencies are satisfied
        if is_ticket_eligible(ticket, completed_ids):
            # Calculate skipped_for_deps for remaining tickets
            for remaining in state.tickets:
                if remaining.id != ticket.id and remaining.status == "pending":
                    if not is_ticket_eligible(remaining, completed_ids):
                        skipped_for_deps += 1

            return GetNextResult(
                ticket=ticket,
                status="ready",
                message=f"Next ticket: {ticket.id}",
                has_more=True,
                **counts,
                skipped_for_deps=skipped_for_deps,
            )
        else:
            # This ticket has unmet dependencies
            skipped_for_deps += 1

    # No eligible tickets found - determine why
    if counts["blocked"] == counts["total"]:
        return GetNextResult(
            ticket=None,
            status="all_blocked",
            message="All tickets are blocked",
            has_more=False,
            **counts,
            skipped_for_deps=skipped_for_deps,
        )

    if counts["completed"] == counts["total"]:
        return GetNextResult(
            ticket=None,
            status="complete",
            message="All tickets are complete",
            has_more=False,
            **counts,
            skipped_for_deps=skipped_for_deps,
        )

    if skipped_for_deps > 0:
        return GetNextResult(
            ticket=None,
            status="waiting_on_dependencies",
            message=f"All {skipped_for_deps} pending ticket(s) are waiting on dependencies",
            has_more=True,
            **counts,
            skipped_for_deps=skipped_for_deps,
        )

    # Fallback: no pending tickets and not all complete
    return GetNextResult(
        ticket=None,
        status="complete",
        message="No pending tickets",
        has_more=False,
        **counts,
        skipped_for_deps=skipped_for_deps,
    )
