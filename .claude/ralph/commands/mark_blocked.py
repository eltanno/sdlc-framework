"""Mark a ticket as blocked.

This module handles:
- Setting blocked status with reason
- Adding blocked labels to GitHub issues (via PM tool or subprocess)
- Removing instance labels
- Unassigning issues
- Updating workflow state
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.pm import PMTool


def mark_blocked(
    ticket_id: str,
    reason: str,
    state_file: Path,
    issue_number: int | None = None,
    pm_tool: "PMTool | None" = None,
    ralph_label: str | None = None,
) -> dict[str, Any]:
    """Mark a ticket as blocked with a reason.

    Updates the workflow state to mark the ticket as blocked and optionally
    updates the corresponding GitHub issue with a blocked label and comment.

    When pm_tool is provided, uses the PM tool abstraction layer instead of
    direct subprocess calls. This allows for consistent behavior across
    different PM systems (GitHub, Trello, etc.).

    Args:
        ticket_id: The ticket identifier (e.g., "TASK-001")
        reason: The reason for blocking the ticket
        state_file: Path to the workflow state file
        issue_number: Optional GitHub issue number (will be looked up if not provided)
        pm_tool: Optional PM tool instance for GitHub operations
        ralph_label: Optional ralph instance label to remove when blocking

    Returns:
        Dictionary containing:
        - blocked_ticket: The ticket ID that was blocked
        - reason: The blocking reason
        - issue_number: The GitHub issue number (or None if not found)
        - timestamp: When the ticket was blocked

    Raises:
        ValueError: If ticket_id is empty or ticket not found in state
        FileNotFoundError: If state_file doesn't exist
    """
    # Validate inputs
    if not ticket_id:
        raise ValueError("ticket_id is required")

    if not reason:
        reason = "Unknown reason"

    # Import state module (avoid circular imports)
    from core.state import (
        load_workflow_state,
        save_workflow_state,
        get_ticket_by_id,
    )

    # Load workflow state
    state = load_workflow_state(state_file)

    # Find the ticket
    ticket = get_ticket_by_id(state, ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found in state file")

    # Look up GitHub issue if not provided (only when not using pm_tool)
    found_issue = issue_number
    if found_issue is None and pm_tool is None:
        found_issue = _lookup_issue_by_ticket_id(ticket_id)

    # Update GitHub issue if found
    if found_issue is not None:
        if pm_tool is not None:
            # Use PM tool for GitHub operations
            _update_issue_via_pm_tool(
                pm_tool, str(found_issue), reason, ralph_label
            )
        else:
            # Fall back to direct subprocess calls
            _update_github_issue(found_issue, reason)

    # Update ticket status
    ticket.status = "blocked"
    ticket.block_reason = reason

    # Update workflow counts
    state.blocked_count += 1

    # Clear current ticket if it's the one being blocked
    if state.current_ticket == ticket_id:
        state.current_ticket = None

    # Save updated state
    save_workflow_state(state, state_file)

    # Build result
    result = {
        "blocked_ticket": ticket_id,
        "reason": reason,
        "issue_number": found_issue,
        "timestamp": datetime.now().isoformat(),
    }

    return result


def _lookup_issue_by_ticket_id(ticket_id: str) -> int | None:
    """Look up a GitHub issue number by ticket ID.

    Searches open issues for one whose title contains the ticket ID.

    Args:
        ticket_id: The ticket identifier to search for

    Returns:
        The issue number if found, None otherwise
    """
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--json", "number,title",
                "--limit", "100",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        issues = json.loads(result.stdout)
        for issue in issues:
            if ticket_id in issue.get("title", ""):
                return issue["number"]

        return None
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None


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


def _update_github_issue(issue_number: int, reason: str) -> None:
    """Update a GitHub issue to mark it as blocked.

    Performs the following operations:
    1. Remove instance label (if RALPH_LABEL is set)
    2. Add 'blocked' label
    3. Unassign the issue
    4. Add a comment with the blocking reason

    All operations continue even if individual steps fail.

    Args:
        issue_number: The GitHub issue number
        reason: The blocking reason to include in the comment
    """
    # Remove instance label if configured
    instance_label = os.environ.get("RALPH_LABEL")
    if instance_label:
        subprocess.run(
            [
                "gh", "issue", "edit", str(issue_number),
                "--remove-label", instance_label,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    # Add blocked label
    subprocess.run(
        [
            "gh", "issue", "edit", str(issue_number),
            "--add-label", "blocked",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Unassign the issue
    subprocess.run(
        [
            "gh", "issue", "edit", str(issue_number),
            "--remove-assignee", "@me",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Add comment with blocking reason
    comment_body = f"""**Blocked by Ralph automation**

Reason: {reason}

This issue has been marked as blocked and unassigned."""

    subprocess.run(
        [
            "gh", "issue", "comment", str(issue_number),
            "--body", comment_body,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
