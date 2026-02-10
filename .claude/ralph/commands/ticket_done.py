"""Mark a ticket as complete.

This module handles:
- Removing in-progress labels
- Closing associated issues
- Updating workflow state with completion timestamp

Functions:
    mark_ticket_done: Update state to mark ticket complete
    close_github_issue: Close a GitHub issue via gh CLI
    remove_label_from_issue: Remove a label from a GitHub issue
    find_issue_by_ticket_id: Look up issue number from ticket ID
    ticket_done: Main entry point combining all operations
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from core.pm import PMTool


def mark_ticket_done(
    ticket_id: str,
    pr_number: str | None = None,
    issue_number: int | None = None,
    state_file: Path | None = None,
) -> dict[str, Any]:
    """Mark a ticket as complete in the workflow state file.

    Args:
        ticket_id: The ticket identifier to mark complete
        pr_number: Optional PR number associated with the completion
        issue_number: Optional GitHub issue number
        state_file: Path to the workflow state file

    Returns:
        Dictionary with completion details including progress info

    Raises:
        FileNotFoundError: If state_file doesn't exist
        ValueError: If ticket_id is not found in state
    """
    if state_file is None:
        state_file = Path("workflow-state.json")

    if not state_file.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")

    # Load current state
    state = json.loads(state_file.read_text())

    ralph = state.get("ralph")
    if not ralph:
        raise ValueError("State file missing ralph section")

    tickets = ralph.get("tickets", [])
    if ticket_id not in tickets:
        raise ValueError(f"Ticket '{ticket_id}' not found in state file")

    # Remove from blocked if it was blocked
    if ticket_id in ralph.get("blocked", {}):
        del ralph["blocked"][ticket_id]

    # Clear current ticket
    state["current_ticket"] = None

    # Save updated state
    state_file.write_text(json.dumps(state, indent=2))

    # Calculate progress
    total = len(tickets)

    return {
        "ticket_id": ticket_id,
        "status": "completed",
        "pr_number": pr_number,
        "total": total,
        "remaining": None,  # Can't know without PM tool query
        "next_ticket": None,
    }


def close_github_issue(issue_number: int) -> None:
    """Close a GitHub issue via gh CLI.

    Args:
        issue_number: The issue number to close

    Raises:
        RuntimeError: If gh CLI is not available
    """
    try:
        result = subprocess.run(
            ["gh", "issue", "close", str(issue_number)],
            capture_output=True,
            text=True,
        )
        # gh issue close is idempotent - doesn't error on already closed
        if result.returncode != 0:
            # Check if it's just an already-closed issue
            if "already closed" not in result.stderr.lower():
                # Log warning but don't fail
                pass
    except FileNotFoundError as e:
        raise RuntimeError("gh CLI is not found. Please install GitHub CLI.") from e


def remove_label_from_issue(issue_number: int, label: str) -> None:
    """Remove a label from a GitHub issue.

    This operation is idempotent - it won't error if the label isn't present.

    Args:
        issue_number: The issue number
        label: The label name to remove

    Raises:
        RuntimeError: If gh CLI is not available
    """
    try:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--remove-label", label],
            capture_output=True,
            text=True,
        )
        # gh issue edit --remove-label is idempotent
    except FileNotFoundError as e:
        raise RuntimeError("gh CLI is not found. Please install GitHub CLI.") from e


def find_issue_by_ticket_id(ticket_id: str) -> int | None:
    """Look up GitHub issue number by ticket ID in title.

    Searches both open and closed issues for a ticket ID in the title.

    Args:
        ticket_id: The ticket identifier to search for

    Returns:
        Issue number if found, None otherwise
    """
    try:
        # Search open issues first
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--json", "number,title", "--limit", "100"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            issues = json.loads(result.stdout) if result.stdout else []
            for issue in issues:
                if ticket_id in issue.get("title", ""):
                    return issue["number"]

        # Search closed issues if not found in open
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "closed", "--json", "number,title", "--limit", "100"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            issues = json.loads(result.stdout) if result.stdout else []
            for issue in issues:
                if ticket_id in issue.get("title", ""):
                    return issue["number"]

        return None

    except FileNotFoundError:
        # gh CLI not available
        return None
    except json.JSONDecodeError:
        return None


def _load_config(config_file: Path | None) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_file: Path to config.yaml

    Returns:
        Configuration dictionary, or empty dict if file doesn't exist
    """
    if config_file is None:
        config_file = Path("config.yaml")

    if not config_file.exists():
        return {}

    try:
        return yaml.safe_load(config_file.read_text()) or {}
    except yaml.YAMLError:
        return {}


def ticket_done(
    ticket_id: str,
    pr_number: str | None = None,
    issue_number: int | None = None,
    state_file: Path | None = None,
    config_file: Path | None = None,
    pm_tool: PMTool | None = None,
    ralph_label: str | None = None,
) -> dict[str, Any]:
    """Complete a ticket, handling both state update and PM tool operations.

    This is the main entry point that:
    1. Uses pm_tool if provided, otherwise falls back to config-based GitHub operations
    2. Looks up issue number if not provided (from state)
    3. Removes instance label via PM tool if configured
    4. Closes the issue via PM tool
    5. Updates workflow state (preserving attempt_count for metrics)

    Args:
        ticket_id: The ticket identifier to complete
        pr_number: Optional PR number
        issue_number: Optional GitHub issue number (will be looked up if not provided)
        state_file: Path to workflow state file
        config_file: Path to config.yaml
        pm_tool: Optional PM tool instance (takes precedence over config-based GitHub)
        ralph_label: Optional label to remove from the ticket (e.g., "ralph-1")

    Returns:
        Dictionary with completion details
    """
    # Resolve issue number from state if not provided
    actual_issue_number = issue_number
    if actual_issue_number is None and state_file and state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            for t in state.get("tickets", []):
                if t["id"] == ticket_id and "issue_number" in t:
                    actual_issue_number = t["issue_number"]
                    break
        except (json.JSONDecodeError, KeyError):
            pass

    # Use PM tool if provided (takes precedence over config-based operations)
    if pm_tool is not None:
        # PM tools like Asana use ticket_id directly (e.g., "SDLC-0070")
        # They resolve to internal IDs (GIDs) internally
        # Remove instance label first (if provided)
        if ralph_label:
            pm_tool.remove_label(ticket_id, ralph_label)

        # Close the ticket (idempotent - handles already closed)
        pm_tool.close_ticket(ticket_id)
    else:
        # Fall back to config-based GitHub operations (legacy behavior)
        config = _load_config(config_file)
        pm_config = config.get("pm", {})
        ralph_config = config.get("ralph", {})

        pm_tool_name = pm_config.get("tool", "none")
        instance_label = ralph_config.get("instance_label", "")

        if pm_tool_name == "github":
            # If still no issue number, look it up via gh CLI
            if actual_issue_number is None:
                actual_issue_number = find_issue_by_ticket_id(ticket_id)

            # Perform GitHub operations if we have an issue number
            if actual_issue_number is not None:
                # Remove instance label if configured
                if instance_label:
                    remove_label_from_issue(actual_issue_number, instance_label)

                # Close the issue
                close_github_issue(actual_issue_number)

    # Update the state file (preserves all existing ticket fields including attempt_count)
    result = mark_ticket_done(
        ticket_id=ticket_id,
        pr_number=pr_number,
        issue_number=actual_issue_number,
        state_file=state_file,
    )

    return result
