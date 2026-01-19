"""Initialize Ralph run from PRD and plan.

This module handles:
- Validating PRD and plan files exist
- Parsing tickets from PRD
- Parsing dependencies from plan
- Creating initial workflow state
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from commands.parse_deps import parse_dependencies
from core.state import WorkflowState, Ticket, save_workflow_state, _atomic_write


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class SetupResult:
    """Result from running setup.

    Attributes:
        success: Whether setup completed successfully
        ticket_count: Number of tickets found
        ticket_prefix: The ticket prefix extracted (e.g., "TASK", "SDLC")
        error: Error message if setup failed
        warning: Warning message if applicable
    """

    success: bool
    ticket_count: int = 0
    ticket_prefix: str | None = None
    error: str | None = None
    warning: str | None = None


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
    linked_pattern = re.compile(r"\[([A-Z]+-\d+)\]\(")
    linked_matches = linked_pattern.findall(content)

    if linked_matches:
        for ticket_id in linked_matches:
            if ticket_id not in seen:
                tickets.append(ticket_id)
                seen.add(ticket_id)
        return tickets

    # Fall back to plain ticket IDs in table format
    # Look for ticket IDs at the start of a table cell
    plain_pattern = re.compile(r"\|\s*([A-Z]+-\d+)\s*\|")
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
) -> SetupResult:
    """Run the setup process to initialize a Ralph workflow.

    This is the main entry point for the setup command.

    Args:
        prd_path: Path to the PRD document
        plan_path: Path to the plan document
        state_file: Path where the state file should be created

    Returns:
        SetupResult with success status and metadata
    """
    # Validate paths
    try:
        validate_paths(prd_path, plan_path)
    except FileNotFoundError as e:
        return SetupResult(success=False, error=str(e))

    # Initialize state
    try:
        state = initialize_workflow_state(prd_path, plan_path, state_file)
    except Exception as e:
        return SetupResult(success=False, error=f"Failed to initialize state: {e}")

    # Extract ticket metadata
    ticket_ids = [t.id for t in state.tickets]
    ticket_prefix = extract_ticket_prefix(ticket_ids)
    ticket_count = len(ticket_ids)

    # Check for warnings
    warning = None
    if ticket_count == 0:
        warning = "No tickets found in PRD"

    return SetupResult(
        success=True,
        ticket_count=ticket_count,
        ticket_prefix=ticket_prefix,
        warning=warning,
    )
