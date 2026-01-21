"""Initialize Ralph run from PRD and plan.

This module handles:
- Validating PRD and plan files exist
- Parsing tickets from PRD
- Parsing dependencies from plan
- Creating initial workflow state
- Detecting and handling PRD/state ticket mismatches
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from commands.parse_deps import parse_dependencies
from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
    save_workflow_state,
    load_workflow_state,
)


# Set up logger for this module
logger = logging.getLogger(__name__)


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class MismatchResult:
    """Result from detecting ticket mismatch between PRD and state.

    Attributes:
        has_mismatch: Whether tickets differ between PRD and state
        added: Tickets in PRD but not in state (new tickets)
        removed: Tickets in state but not in PRD (removed tickets)
    """

    has_mismatch: bool
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


@dataclass
class SetupResult:
    """Result from running setup.

    Attributes:
        success: Whether setup completed successfully
        ticket_count: Number of tickets found
        ticket_prefix: The ticket prefix extracted (e.g., "TASK", "SDLC")
        error: Error message if setup failed
        warning: Warning message if applicable
        mismatch_detected: Whether a PRD/state ticket mismatch was detected
        tickets_added: New tickets from PRD (if mismatch detected)
        tickets_removed: Old tickets no longer in PRD (if mismatch detected)
    """

    success: bool
    ticket_count: int = 0
    ticket_prefix: str | None = None
    error: str | None = None
    warning: str | None = None
    mismatch_detected: bool = False
    tickets_added: list[str] | None = None
    tickets_removed: list[str] | None = None


# ============================================================================
# Path Validation
# ============================================================================


def validate_paths(prd_path: Path, plan_path: Path) -> None:
    """Validate that PRD and plan files exist.

    Args:
        prd_path: Path to the PRD document
        plan_path: Path to the plan document

    Raises:
        FileNotFoundError: If either file doesn't exist
    """
    if not prd_path.exists():
        raise FileNotFoundError(f"PRD file not found: {prd_path}")
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")


# ============================================================================
# Ticket Extraction
# ============================================================================


def extract_tickets_from_prd(prd_path: Path) -> list[str]:
    """Extract ticket IDs from a PRD document.

    Supports two formats:
    1. Markdown-linked tickets: [TASK-001](https://github.com/...)
    2. Plain ticket IDs: TASK-001 (in a table context)

    Args:
        prd_path: Path to the PRD document

    Returns:
        List of unique ticket IDs in document order
    """
    content = prd_path.read_text()
    tickets: list[str] = []
    seen: set[str] = set()

    # First try to match markdown-linked tickets: [PREFIX-NNNN](url)
    # Require 3+ digits to exclude test case IDs like TC-1
    linked_pattern = re.compile(r"\[([A-Z]+-\d{3,})\]\(")
    linked_matches = linked_pattern.findall(content)

    if linked_matches:
        for ticket_id in linked_matches:
            if ticket_id not in seen:
                tickets.append(ticket_id)
                seen.add(ticket_id)
        return tickets

    # Fall back to plain ticket IDs in table format
    # Look for ticket IDs at the start of a table cell
    # Require 3+ digits to exclude test case IDs like TC-1
    plain_pattern = re.compile(r"\|\s*([A-Z]+-\d{3,})\s*\|")
    plain_matches = plain_pattern.findall(content)

    for ticket_id in plain_matches:
        if ticket_id not in seen:
            tickets.append(ticket_id)
            seen.add(ticket_id)

    return tickets


def extract_ticket_prefix(tickets: list[str]) -> str | None:
    """Extract the common prefix from ticket IDs.

    Args:
        tickets: List of ticket IDs (e.g., ["TASK-001", "TASK-002"])

    Returns:
        The ticket prefix (e.g., "TASK"), or None if list is empty
    """
    if not tickets:
        return None

    # Get prefix from first ticket
    first = tickets[0]
    match = re.match(r"^([A-Z]+)-", first)
    if match:
        return match.group(1)

    return None


# ============================================================================
# Mismatch Detection and State Reset
# ============================================================================


def detect_ticket_mismatch(
    prd_tickets: list[str], state_tickets: list[str]
) -> MismatchResult:
    """Detect if tickets in PRD differ from tickets in state.

    Args:
        prd_tickets: List of ticket IDs from PRD
        state_tickets: List of ticket IDs from existing state

    Returns:
        MismatchResult with has_mismatch flag and lists of added/removed tickets
    """
    prd_set = set(prd_tickets)
    state_set = set(state_tickets)

    # Tickets in PRD but not in state (new tickets added to PRD)
    added = [t for t in prd_tickets if t not in state_set]

    # Tickets in state but not in PRD (tickets removed from PRD)
    removed = [t for t in state_tickets if t not in prd_set]

    has_mismatch = len(added) > 0 or len(removed) > 0

    return MismatchResult(
        has_mismatch=has_mismatch,
        added=added,
        removed=removed,
    )


def reset_state_from_prd(
    prd_tickets: list[str],
    dependencies: dict[str, list[str]],
    old_attempts: dict[str, int],
    old_blocked: dict[str, str],
    source: str,
) -> RalphState:
    """Create new RalphState from PRD while preserving attempt counts for matching tickets.

    Args:
        prd_tickets: List of ticket IDs from PRD (source of truth)
        dependencies: Dependencies parsed from plan
        old_attempts: Previous attempt counts (preserved for matching tickets)
        old_blocked: Previous blocked reasons (preserved for matching tickets)
        source: PM tool source (e.g., "github", "trello")

    Returns:
        New RalphState with tickets from PRD, preserving data for matching tickets
    """
    prd_set = set(prd_tickets)

    # Preserve attempts only for tickets that exist in PRD
    preserved_attempts = {
        ticket_id: count
        for ticket_id, count in old_attempts.items()
        if ticket_id in prd_set and count > 0
    }

    # Preserve blocked reasons only for tickets that exist in PRD
    preserved_blocked = {
        ticket_id: reason
        for ticket_id, reason in old_blocked.items()
        if ticket_id in prd_set
    }

    return RalphState(
        tickets=prd_tickets,
        dependencies=dependencies,
        attempts=preserved_attempts,
        blocked=preserved_blocked,
        source=source,
    )


# ============================================================================
# Workflow State Initialization
# ============================================================================


def initialize_workflow_state(
    prd_path: Path,
    plan_path: Path,
    state_file: Path,
) -> WorkflowState:
    """Initialize workflow state from PRD and plan.

    Extracts tickets from PRD, parses dependencies from plan,
    and creates the initial workflow state file.

    Args:
        prd_path: Path to the PRD document
        plan_path: Path to the plan document
        state_file: Path where the state file should be created

    Returns:
        The created WorkflowState object
    """
    # Extract tickets from PRD
    ticket_ids = extract_tickets_from_prd(prd_path)

    # Parse dependencies from plan
    dependencies = parse_dependencies(plan_path)

    # Extract titles from plan if available (stub for now - just use ID as title)
    # In a full implementation, we'd parse titles from the plan table

    # Create Ticket objects
    tickets: list[Ticket] = []
    for ticket_id in ticket_ids:
        deps = dependencies.get(ticket_id, [])
        ticket = Ticket(
            id=ticket_id,
            title=ticket_id,  # Use ID as title for now
            status="pending",
            dependencies=deps,
            attempts=0,
            block_reason=None,
        )
        tickets.append(ticket)

    # Create WorkflowState
    state = WorkflowState(
        version="1.0",
        prd_path=prd_path,
        plan_path=plan_path,
        tickets=tickets,
        current_ticket=None,
        completed_count=0,
        blocked_count=0,
    )

    # Save state file
    save_workflow_state(state, state_file)

    return state


# ============================================================================
# Main Setup Function
# ============================================================================


def run_setup(
    prd_path: Path,
    plan_path: Path,
    state_file: Path,
    interactive: bool = False,
) -> SetupResult:
    """Run the setup process to initialize a Ralph workflow.

    This is the main entry point for the setup command. If a state file already
    exists, it will detect mismatches between the PRD and existing state and
    handle reconciliation.

    Args:
        prd_path: Path to the PRD document
        plan_path: Path to the plan document
        state_file: Path where the state file should be created
        interactive: If True, prompt user to confirm state reset on mismatch.
                    If False, warn and continue with PRD as source of truth.

    Returns:
        SetupResult with success status and metadata
    """
    # Validate paths
    try:
        validate_paths(prd_path, plan_path)
    except FileNotFoundError as e:
        return SetupResult(success=False, error=str(e))

    # Extract tickets from PRD
    prd_tickets = extract_tickets_from_prd(prd_path)

    # Parse dependencies from plan
    dependencies = parse_dependencies(plan_path)

    # Check if state file already exists
    mismatch_detected = False
    tickets_added: list[str] | None = None
    tickets_removed: list[str] | None = None
    warning: str | None = None

    if state_file.exists():
        try:
            existing_state = load_workflow_state(state_file)

            # Get tickets from existing state (v2 format uses ralph.tickets)
            if existing_state.ralph is not None:
                state_tickets = existing_state.ralph.tickets
                old_attempts = existing_state.ralph.attempts
                old_blocked = existing_state.ralph.blocked
                source = existing_state.ralph.source
            else:
                # v1 format fallback
                state_tickets = [t.id for t in existing_state.tickets]
                old_attempts = {t.id: t.attempts for t in existing_state.tickets if t.attempts > 0}
                old_blocked = {t.id: t.block_reason for t in existing_state.tickets if t.block_reason}
                source = "unknown"

            # Detect mismatch
            mismatch_result = detect_ticket_mismatch(prd_tickets, state_tickets)

            if mismatch_result.has_mismatch:
                mismatch_detected = True
                tickets_added = mismatch_result.added
                tickets_removed = mismatch_result.removed

                # Log the mismatch
                logger.warning(
                    f"Ticket mismatch detected: +{len(tickets_added)} added, "
                    f"-{len(tickets_removed)} removed"
                )

                if interactive:
                    # Prompt user to confirm reset
                    logger.info(f"PRD tickets: {prd_tickets}, State tickets: {state_tickets}")
                    logger.info(f"Added: {tickets_added}, Removed: {tickets_removed}")

                    user_input = input("Reset state to match PRD? (y/n): ").strip().lower()
                    if user_input != "y":
                        return SetupResult(
                            success=False,
                            error="User aborted: state reset rejected",
                            mismatch_detected=True,
                            tickets_added=tickets_added,
                            tickets_removed=tickets_removed,
                        )

                # Reset state from PRD (non-interactive mode or user confirmed)
                warning = (
                    f"State mismatch detected and reconciled. "
                    f"Added {len(tickets_added)} ticket(s), removed {len(tickets_removed)} ticket(s)."
                )

                # Create new RalphState from PRD with preserved data
                new_ralph = reset_state_from_prd(
                    prd_tickets=prd_tickets,
                    dependencies=dependencies,
                    old_attempts=old_attempts,
                    old_blocked=old_blocked,
                    source=source,
                )

                # Create new workflow state with v2 format
                state = WorkflowState(
                    version="2.0",
                    prd_path=prd_path,
                    plan_path=plan_path,
                    tickets=[],  # v2 uses ralph.tickets
                    ralph=new_ralph,
                    current_ticket=None,
                    completed_count=0,
                    blocked_count=0,
                )

                # Save updated state
                save_workflow_state(state, state_file)

                ticket_prefix = extract_ticket_prefix(prd_tickets)
                return SetupResult(
                    success=True,
                    ticket_count=len(prd_tickets),
                    ticket_prefix=ticket_prefix,
                    warning=warning,
                    mismatch_detected=True,
                    tickets_added=tickets_added,
                    tickets_removed=tickets_removed,
                )
            else:
                # No mismatch - state matches PRD, just return success
                ticket_prefix = extract_ticket_prefix(prd_tickets)
                return SetupResult(
                    success=True,
                    ticket_count=len(prd_tickets),
                    ticket_prefix=ticket_prefix,
                    warning=None,
                    mismatch_detected=False,
                )

        except (FileNotFoundError, ValueError) as e:
            # State file exists but is invalid, create fresh state
            logger.warning(f"Invalid existing state file, creating fresh: {e}")

    # No existing state or invalid state - initialize fresh state
    try:
        state = initialize_workflow_state(prd_path, plan_path, state_file)
    except Exception as e:
        return SetupResult(success=False, error=f"Failed to initialize state: {e}")

    # Extract ticket metadata
    ticket_ids = [t.id for t in state.tickets]
    ticket_prefix = extract_ticket_prefix(ticket_ids)
    ticket_count = len(ticket_ids)

    # Check for warnings
    if ticket_count == 0:
        warning = "No tickets found in PRD"

    return SetupResult(
        success=True,
        ticket_count=ticket_count,
        ticket_prefix=ticket_prefix,
        warning=warning,
        mismatch_detected=mismatch_detected,
        tickets_added=tickets_added,
        tickets_removed=tickets_removed,
    )
