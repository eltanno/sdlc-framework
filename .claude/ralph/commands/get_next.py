"""Get the next eligible ticket to work on.

This module finds the next ticket based on:
- Ticket status (pending, not blocked)
- Dependency satisfaction
- Priority ordering (first by order in the list)

The get_next_ticket function returns a GetNextResult dataclass that contains:
- The next ticket to work on (or None if no eligible tickets)
- Status information (ready, complete, waiting_on_dependencies, all_blocked, error)
- Counts of tickets by status

When a PM tool is provided (v2 schema), ticket status is queried from the PM tool
(e.g., GitHub Issues) rather than local state. This allows for:
- Correct status when PM tool state differs from local state
- Label-based concurrency control for parallel Ralph instances
- Dependency checking against PM tool (closed = completed)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.pm import PMTool, PMError, TicketInfo, TicketStatus
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


def get_next_ticket(
    state: WorkflowState,
    pm_tool: PMTool | None = None,
    ralph_label: str | None = None,
) -> GetNextResult:
    """Find the next eligible ticket to work on.

    The selection algorithm:
    1. First, check for in-progress tickets (to resume work)
    2. Then, find pending tickets with all dependencies satisfied
    3. Skip blocked tickets
    4. Return first eligible ticket by order in the list

    When pm_tool is provided (v2 schema), ticket status is queried from the PM tool:
    - Open tickets in PM tool are considered pending
    - Closed tickets in PM tool are considered completed
    - Tickets with blocked label are skipped
    - Tickets claimed by other Ralph instances (ralph-* labels) are skipped

    Args:
        state: The current workflow state
        pm_tool: Optional PM tool for querying ticket status (v2 schema)
        ralph_label: This Ralph instance's label (e.g., "ralph-1") for concurrency control

    Returns:
        GetNextResult containing the next ticket and status information
    """
    # If pm_tool is provided and we have ralph state (v2 schema), use PM tool
    if pm_tool is not None and state.ralph is not None:
        return _get_next_ticket_with_pm_tool(state, pm_tool, ralph_label)

    # Otherwise, fall back to v1 behavior using local state
    return _get_next_ticket_from_local_state(state)


def _get_next_ticket_with_pm_tool(
    state: WorkflowState,
    pm_tool: PMTool,
    ralph_label: str | None = None,
) -> GetNextResult:
    """Find the next eligible ticket using PM tool for status.

    Args:
        state: The current workflow state (v2 schema with ralph field)
        pm_tool: PM tool for querying ticket status
        ralph_label: This Ralph instance's label for concurrency control

    Returns:
        GetNextResult containing the next ticket and status information
    """
    # Get ticket IDs from ralph state
    ticket_ids = state.ralph.tickets if state.ralph else []

    # Handle empty workflow
    if not ticket_ids:
        return GetNextResult(
            ticket=None,
            status="complete",
            message="No tickets in workflow",
            has_more=False,
            total=0,
            pending=0,
            completed=0,
            blocked=0,
            in_progress=0,
            skipped_for_deps=0,
        )

    # Query PM tool for open tickets
    try:
        open_tickets = pm_tool.get_open_tickets(ticket_ids)
    except PMError as e:
        return GetNextResult(
            ticket=None,
            status="error",
            message=f"Failed to query PM tool: {e}",
            has_more=False,
            total=len(ticket_ids),
            pending=0,
            completed=0,
            blocked=0,
            in_progress=0,
            skipped_for_deps=0,
        )

    # Build lookup of open tickets
    open_ticket_map: dict[str, TicketInfo] = {t.id: t for t in open_tickets}
    open_ticket_ids = set(open_ticket_map.keys())

    # Count tickets by status
    blocked_count = sum(
        1 for t in open_tickets if t.status == TicketStatus.BLOCKED
    )
    completed_count = len(ticket_ids) - len(open_tickets)
    pending_count = len(open_tickets) - blocked_count

    # Get dependencies from ralph state
    dependencies = state.ralph.dependencies if state.ralph else {}

    # Track tickets skipped due to dependencies
    skipped_for_deps = 0

    # First priority: check for in-progress tickets claimed by THIS instance
    if ralph_label:
        for ticket_id in ticket_ids:
            if ticket_id not in open_ticket_ids:
                continue
            ticket_info = open_ticket_map[ticket_id]
            if ticket_info.status == TicketStatus.BLOCKED:
                continue

            # Check if this ticket is claimed by us
            if ralph_label in ticket_info.labels:
                # Create a Ticket object for the result
                ticket = Ticket(
                    id=ticket_info.id,
                    title=ticket_info.title,
                    status="in_progress",
                    dependencies=dependencies.get(ticket_id, []),
                )
                return GetNextResult(
                    ticket=ticket,
                    status="ready",
                    message=f"Resuming in-progress ticket: {ticket_id}",
                    has_more=True,
                    total=len(ticket_ids),
                    pending=pending_count,
                    completed=completed_count,
                    blocked=blocked_count,
                    in_progress=1,
                    skipped_for_deps=0,
                )

    # Second priority: find pending tickets with satisfied dependencies
    for ticket_id in ticket_ids:
        # Skip if not in open tickets (closed = completed)
        if ticket_id not in open_ticket_ids:
            continue

        ticket_info = open_ticket_map[ticket_id]

        # Skip blocked tickets
        if ticket_info.status == TicketStatus.BLOCKED:
            continue

        # Skip tickets claimed by OTHER instances
        if ralph_label:
            is_claimed, claiming_label = pm_tool.is_ticket_claimed(ticket_id)
            if is_claimed and claiming_label != ralph_label:
                continue

        # Check if dependencies are satisfied
        ticket_deps = dependencies.get(ticket_id, [])
        deps_satisfied = True

        for dep_id in ticket_deps:
            # Check if dependency is closed (completed)
            if dep_id in open_ticket_ids:
                # Dependency is still open - need to check its status
                dep_status = pm_tool.get_ticket_status(dep_id)
                if dep_status != TicketStatus.CLOSED:
                    deps_satisfied = False
                    break
            # If not in open_ticket_ids, it's closed = completed

        if deps_satisfied:
            # Calculate skipped_for_deps for remaining tickets
            for remaining_id in ticket_ids:
                if remaining_id != ticket_id and remaining_id in open_ticket_ids:
                    remaining_info = open_ticket_map[remaining_id]
                    if remaining_info.status != TicketStatus.BLOCKED:
                        remaining_deps = dependencies.get(remaining_id, [])
                        for dep_id in remaining_deps:
                            if dep_id in open_ticket_ids:
                                dep_status = pm_tool.get_ticket_status(dep_id)
                                if dep_status != TicketStatus.CLOSED:
                                    skipped_for_deps += 1
                                    break

            # Create a Ticket object for the result
            ticket = Ticket(
                id=ticket_info.id,
                title=ticket_info.title,
                status="pending",
                dependencies=ticket_deps,
            )
            return GetNextResult(
                ticket=ticket,
                status="ready",
                message=f"Next ticket: {ticket_id}",
                has_more=True,
                total=len(ticket_ids),
                pending=pending_count,
                completed=completed_count,
                blocked=blocked_count,
                in_progress=0,
                skipped_for_deps=skipped_for_deps,
            )
        else:
            skipped_for_deps += 1

    # No eligible tickets found - determine why
    if blocked_count == len(open_tickets) and blocked_count > 0:
        return GetNextResult(
            ticket=None,
            status="all_blocked",
            message="All open tickets are blocked",
            has_more=False,
            total=len(ticket_ids),
            pending=pending_count,
            completed=completed_count,
            blocked=blocked_count,
            in_progress=0,
            skipped_for_deps=skipped_for_deps,
        )

    if not open_tickets:
        return GetNextResult(
            ticket=None,
            status="complete",
            message="All tickets are complete",
            has_more=False,
            total=len(ticket_ids),
            pending=0,
            completed=len(ticket_ids),
            blocked=0,
            in_progress=0,
            skipped_for_deps=skipped_for_deps,
        )

    if skipped_for_deps > 0:
        return GetNextResult(
            ticket=None,
            status="waiting_on_dependencies",
            message=f"All {skipped_for_deps} pending ticket(s) are waiting on dependencies",
            has_more=True,
            total=len(ticket_ids),
            pending=pending_count,
            completed=completed_count,
            blocked=blocked_count,
            in_progress=0,
            skipped_for_deps=skipped_for_deps,
        )

    # Fallback: no pending tickets and not all complete
    return GetNextResult(
        ticket=None,
        status="complete",
        message="No pending tickets",
        has_more=False,
        total=len(ticket_ids),
        pending=pending_count,
        completed=completed_count,
        blocked=blocked_count,
        in_progress=0,
        skipped_for_deps=skipped_for_deps,
    )


def _get_next_ticket_from_local_state(state: WorkflowState) -> GetNextResult:
    """Find the next eligible ticket using local state (v1 schema).

    This is the fallback behavior when no PM tool is provided.

    Args:
        state: The current workflow state (v1 schema with tickets list)

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
