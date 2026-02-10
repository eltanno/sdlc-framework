"""Get the next eligible ticket to work on.

This module finds the next ticket based on:
- Ticket status (pending, not blocked)
- Dependency satisfaction
- Priority ordering (first by order in the list)

The get_next_ticket function returns a GetNextResult dataclass that contains:
- The next ticket to work on (or None if no eligible tickets)
- Status information (ready, complete, waiting_on_dependencies, all_blocked, error)
- Counts of tickets by status

When a PM tool is provided, ticket status is queried from the PM tool
(e.g., GitHub Issues) rather than local state. This allows for:
- Correct status when PM tool state differs from local state
- Label-based concurrency control for parallel Ralph instances
- Dependency checking against PM tool (closed = completed)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from core.pm import PMTool, PMError, TicketInfo, TicketStatus
from core.state import WorkflowState, Ticket

logger = logging.getLogger(__name__)

# Race detection window in seconds
# After adding our label, we wait this long before re-querying
# to give other instances time to also add their labels
RACE_DETECTION_SLEEP_SECONDS = 0.5


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


def claim_ticket_with_race_detection(
    pm_tool: PMTool,
    ticket_id: str,
    ralph_label: str | None = None,
    use_assignee: bool = False,
) -> bool:
    """Claim a ticket using label-based concurrency control with race detection.

    This function implements the claim flow:
    1. If no ralph_label provided, skip claiming (return True)
    2. Add our label to the ticket via PM tool
    3. Sleep briefly to allow other instances to also claim
    4. Re-query to verify we won the race
    5. If another ralph-* label won, release our claim and return False

    Args:
        pm_tool: PM tool for claiming operations
        ticket_id: ID of the ticket to claim
        ralph_label: This Ralph instance's label (e.g., "ralph-1")
        use_assignee: If True, also assign to current user after successful claim

    Returns:
        True if claim succeeded (or no claiming needed), False if claim failed
    """
    # If no ralph_label, skip claiming entirely
    if not ralph_label:
        logger.debug(f"No ralph_label provided, skipping claim for {ticket_id}")
        return True

    # Step 1: Add our label
    logger.debug(f"Claiming ticket {ticket_id} with label {ralph_label}")
    if not pm_tool.claim_ticket(ticket_id, ralph_label):
        logger.warning(f"Failed to add label {ralph_label} to {ticket_id}")
        return False

    # Step 2: Sleep for race detection window
    logger.debug(f"Sleeping {RACE_DETECTION_SLEEP_SECONDS}s for race detection")
    time.sleep(RACE_DETECTION_SLEEP_SECONDS)

    # Step 3: Re-query to verify we won the race
    is_claimed, claiming_label = pm_tool.is_ticket_claimed(ticket_id)

    # Step 4: Check if we won
    if claiming_label != ralph_label:
        # Another instance's label won - release our claim
        logger.info(
            f"Race condition detected on {ticket_id}: "
            f"our label={ralph_label}, winner={claiming_label}"
        )
        pm_tool.remove_label(ticket_id, ralph_label)
        return False

    # Step 5: If use_assignee is enabled, also assign to self
    if use_assignee:
        logger.debug(f"Assigning ticket {ticket_id} to self")
        if hasattr(pm_tool, 'assign_to_self'):
            pm_tool.assign_to_self(ticket_id)

    logger.info(f"Successfully claimed ticket {ticket_id} with label {ralph_label}")
    return True


def _check_dependencies_via_pm_tool(
    ticket_id: str,
    ticket_deps: list[str],
    ticket_ids: list[str],
    open_ticket_ids: set[str],
    pm_tool: PMTool,
) -> bool:
    """Check if all dependencies are satisfied by querying PM tool status.

    A dependency is satisfied only if:
    1. It exists in the workflow ticket list (ticket_ids)
    2. It is CLOSED in the PM tool (not in open_ticket_ids, or status is CLOSED)

    If a dependency doesn't exist in the workflow (not in ticket_ids), it is
    logged as a warning and treated as unmet.

    Args:
        ticket_id: ID of the ticket being checked (for logging)
        ticket_deps: List of dependency ticket IDs for this ticket
        ticket_ids: List of all known ticket IDs in the workflow
        open_ticket_ids: Set of ticket IDs that are currently open
        pm_tool: PM tool for querying ticket status

    Returns:
        True if all dependencies are satisfied, False otherwise
    """
    if not ticket_deps:
        return True

    ticket_id_set = set(ticket_ids)

    for dep_id in ticket_deps:
        # Check if dependency exists in the workflow
        if dep_id not in ticket_id_set:
            # Dependency doesn't exist in the workflow - treat as unmet
            logger.warning(
                f"Dependency {dep_id} for ticket {ticket_id} not found in workflow. "
                "Treating as unmet dependency."
            )
            return False

        # Check if dependency is closed (completed)
        if dep_id in open_ticket_ids:
            # Dependency is in the open tickets list - check its actual status
            try:
                dep_status = pm_tool.get_ticket_status(dep_id)
                if dep_status != TicketStatus.CLOSED:
                    # Dependency is still open
                    return False
            except PMError as e:
                # Failed to query dependency status - log warning and treat as unmet
                logger.warning(
                    f"Failed to check status of dependency {dep_id} for ticket {ticket_id}: {e}. "
                    "Treating as unmet dependency."
                )
                return False
        # If not in open_ticket_ids but in ticket_ids, it's closed (completed)

    return True


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

    When pm_tool is provided, ticket status is queried from the PM tool:
    - Open tickets in PM tool are considered pending
    - Closed tickets in PM tool are considered completed
    - Tickets with blocked label are skipped
    - Tickets claimed by other Ralph instances (ralph-* labels) are skipped

    Args:
        state: The current workflow state
        pm_tool: Optional PM tool for querying ticket status
        ralph_label: This Ralph instance's label (e.g., "ralph-1") for concurrency control

    Returns:
        GetNextResult containing the next ticket and status information
    """
    # If pm_tool is provided and we have ralph state, use PM tool
    if pm_tool is not None and state.ralph is not None:
        return _get_next_ticket_with_pm_tool(state, pm_tool, ralph_label)

    # Otherwise, fall back to local state
    return _get_next_ticket_from_local_state(state)


def _get_next_ticket_with_pm_tool(
    state: WorkflowState,
    pm_tool: PMTool,
    ralph_label: str | None = None,
) -> GetNextResult:
    """Find the next eligible ticket using PM tool for status.

    Args:
        state: The current workflow state with ralph field
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
                # Get complexity from state (defaults to 3)
                complexity_map = state.ralph.complexity if state.ralph else {}
                ticket_complexity = complexity_map.get(ticket_id, 3)

                # Create a Ticket object for the result
                ticket = Ticket(
                    id=ticket_info.id,
                    title=ticket_info.title,
                    status="in_progress",
                    dependencies=dependencies.get(ticket_id, []),
                    complexity=ticket_complexity,
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
    # Track tickets where claim failed due to race conditions
    skipped_for_claims = 0

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
        deps_satisfied = _check_dependencies_via_pm_tool(
            ticket_id=ticket_id,
            ticket_deps=ticket_deps,
            ticket_ids=ticket_ids,
            open_ticket_ids=open_ticket_ids,
            pm_tool=pm_tool,
        )

        if deps_satisfied:
            # Try to claim this ticket with race detection
            claim_succeeded = claim_ticket_with_race_detection(
                pm_tool=pm_tool,
                ticket_id=ticket_id,
                ralph_label=ralph_label,
                use_assignee=False,  # TODO: wire up use_assignee from config
            )

            if not claim_succeeded:
                # Race condition detected - try next ticket
                logger.info(f"Claim failed for {ticket_id}, trying next ticket")
                skipped_for_claims += 1
                continue

            # Calculate skipped_for_deps for remaining tickets
            for remaining_id in ticket_ids:
                if remaining_id != ticket_id and remaining_id in open_ticket_ids:
                    remaining_info = open_ticket_map[remaining_id]
                    if remaining_info.status != TicketStatus.BLOCKED:
                        remaining_deps = dependencies.get(remaining_id, [])
                        if remaining_deps:
                            deps_met = _check_dependencies_via_pm_tool(
                                ticket_id=remaining_id,
                                ticket_deps=remaining_deps,
                                ticket_ids=ticket_ids,
                                open_ticket_ids=open_ticket_ids,
                                pm_tool=pm_tool,
                            )
                            if not deps_met:
                                skipped_for_deps += 1

            # Get complexity from state (defaults to 3)
            complexity_map = state.ralph.complexity if state.ralph else {}
            ticket_complexity = complexity_map.get(ticket_id, 3)

            # Create a Ticket object for the result
            ticket = Ticket(
                id=ticket_info.id,
                title=ticket_info.title,
                status="pending",
                dependencies=ticket_deps,
                complexity=ticket_complexity,
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
    # Check if all claims failed (skipped_for_claims > 0 and no other reason)
    if skipped_for_claims > 0 and skipped_for_deps == 0 and blocked_count < len(open_tickets):
        return GetNextResult(
            ticket=None,
            status="waiting_on_claims",
            message=f"All {skipped_for_claims} eligible ticket(s) claimed by other instances",
            has_more=True,
            total=len(ticket_ids),
            pending=pending_count,
            completed=completed_count,
            blocked=blocked_count,
            in_progress=0,
            skipped_for_deps=0,
        )

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
    """Find the next eligible ticket using local state.

    This is the fallback behavior when no PM tool is provided.

    Args:
        state: The current workflow state with tickets list

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
