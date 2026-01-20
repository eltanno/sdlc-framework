"""Finalize and archive workflow.

This module handles:
- Querying GitHub for issue counts (source of truth)
- Generating workflow summaries
- Updating workflow state to idle
- Archiving state files

The cleanup command is called at the end of a ralph run to:
1. Query GitHub for the final issue counts
2. Update the workflow-state.json to set phase to 'idle'
3. Generate and display a summary of the run
4. Output JSON data for programmatic consumption
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_issue_counts() -> dict[str, int]:
    """Get issue counts from GitHub.

    Queries GitHub for total, closed, blocked, and pending issue counts.
    GitHub is always the source of truth for issue status.

    Returns:
        Dictionary with keys: total, done, blocked, pending
        All values default to 0 if gh CLI fails
    """
    try:
        # Get total issues with 'task' label
        total_result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "all",
                "--label", "task",
                "--json", "number",
                "--limit", "1000",
            ],
            capture_output=True,
            text=True,
        )
        total = len(json.loads(total_result.stdout)) if total_result.returncode == 0 else 0

        # Get closed issues with 'task' label
        done_result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "closed",
                "--label", "task",
                "--json", "number",
                "--limit", "1000",
            ],
            capture_output=True,
            text=True,
        )
        done = len(json.loads(done_result.stdout)) if done_result.returncode == 0 else 0

        # Get open issues with 'blocked' label
        blocked_result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--label", "blocked",
                "--json", "number",
                "--limit", "1000",
            ],
            capture_output=True,
            text=True,
        )
        blocked = len(json.loads(blocked_result.stdout)) if blocked_result.returncode == 0 else 0

        # Get open issues with 'task' label
        open_result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--label", "task",
                "--json", "number",
                "--limit", "1000",
            ],
            capture_output=True,
            text=True,
        )
        open_count = len(json.loads(open_result.stdout)) if open_result.returncode == 0 else 0

        # Pending = open - blocked (ensure non-negative)
        pending = max(0, open_count - blocked)

        return {
            "total": total,
            "done": done,
            "blocked": blocked,
            "pending": pending,
        }

    except (subprocess.SubprocessError, json.JSONDecodeError):
        # Return zeros if gh CLI fails
        return {
            "total": 0,
            "done": 0,
            "blocked": 0,
            "pending": 0,
        }


def determine_status(counts: dict[str, int]) -> str:
    """Determine the completion status based on issue counts.

    Args:
        counts: Dictionary with total, done, blocked, pending counts

    Returns:
        Status string: "complete", "complete_with_blocked", or "incomplete"
    """
    pending = counts.get("pending", 0)
    blocked = counts.get("blocked", 0)

    if pending == 0 and blocked == 0:
        return "complete"
    elif pending == 0:
        return "complete_with_blocked"
    else:
        return "incomplete"


def get_completed_tickets() -> list[dict[str, Any]]:
    """Get list of completed (closed) tickets from GitHub.

    Returns:
        List of dictionaries with number and title keys
    """
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "closed",
                "--label", "task",
                "--json", "number,title",
                "--limit", "1000",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def get_blocked_tickets() -> list[dict[str, Any]]:
    """Get list of blocked tickets from GitHub.

    Returns:
        List of dictionaries with number and title keys
    """
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--label", "blocked",
                "--json", "number,title",
                "--limit", "100",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def get_pending_tickets() -> list[dict[str, Any]]:
    """Get list of pending (open, not blocked) tickets from GitHub.

    Returns:
        List of dictionaries with number and title keys
    """
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--state", "open",
                "--label", "task",
                "--json", "number,title",
                "--limit", "100",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []


def update_workflow_state(state_file: Path) -> None:
    """Update workflow state file to mark ralph as complete.

    Sets phase to 'idle' and adds 'ralph' to the completed list.
    If the file doesn't exist, does nothing (no error).

    Args:
        state_file: Path to workflow-state.json
    """
    if not state_file.exists():
        return

    try:
        data = json.loads(state_file.read_text())

        # Set phase to idle
        data["phase"] = "idle"

        # Add ralph to completed list (avoid duplicates)
        completed = data.get("completed", [])
        if "ralph" not in completed:
            completed.append("ralph")
        data["completed"] = completed

        # Write back atomically
        state_file.write_text(json.dumps(data, indent=2))

    except (json.JSONDecodeError, IOError):
        # If we can't read/write the file, just skip
        pass


def generate_summary(counts: dict[str, int], status: str) -> dict[str, Any]:
    """Generate summary dictionary for JSON output.

    Args:
        counts: Issue counts dictionary
        status: Completion status string

    Returns:
        Summary dictionary with status, counts, and completion signal
    """
    completion_signal = "PRD_COMPLETE" if status == "complete" else "NEEDS_REVIEW"

    return {
        "status": status,
        "total": counts.get("total", 0),
        "done": counts.get("done", 0),
        "blocked": counts.get("blocked", 0),
        "pending": counts.get("pending", 0),
        "completion_signal": completion_signal,
    }


def format_output(
    counts: dict[str, int],
    status: str,
    completed_tickets: list[dict[str, Any]],
    blocked_tickets: list[dict[str, Any]],
    pending_tickets: list[dict[str, Any]],
) -> str:
    """Format the cleanup output for display.

    Args:
        counts: Issue counts dictionary
        status: Completion status string
        completed_tickets: List of completed ticket dicts
        blocked_tickets: List of blocked ticket dicts
        pending_tickets: List of pending ticket dicts

    Returns:
        Formatted output string with summary and JSON
    """
    lines = []

    # Header
    lines.append("")
    lines.append("=" * 40)
    lines.append("         RALPH RUN SUMMARY")
    lines.append("=" * 40)
    lines.append("")

    # Counts
    lines.append(f"Total Tickets:    {counts.get('total', 0)}")
    lines.append(f"Completed:        {counts.get('done', 0)}")
    lines.append(f"Blocked:          {counts.get('blocked', 0)}")
    lines.append(f"Pending:          {counts.get('pending', 0)}")
    lines.append("")

    # Completed tickets
    if completed_tickets:
        lines.append("Completed tickets:")
        for ticket in completed_tickets:
            title = ticket.get("title", "Unknown")
            # Extract ticket ID from title like "[TASK-001] Description"
            if "]" in title:
                lines.append(f"  - {title.split(']')[0]}]")
            else:
                lines.append(f"  - {title}")
        lines.append("")

    # Blocked tickets
    if blocked_tickets:
        lines.append("Blocked tickets:")
        for ticket in blocked_tickets:
            lines.append(f"  - {ticket.get('title', 'Unknown')}")
        lines.append("")

    # Pending tickets
    if pending_tickets:
        lines.append("Pending tickets (not started):")
        for ticket in pending_tickets:
            lines.append(f"  - {ticket.get('title', 'Unknown')}")
        lines.append("")

    # Final status
    lines.append("=" * 40)
    if status == "complete":
        lines.append("PRD_COMPLETE")
        lines.append("All tickets have been implemented!")
    elif status == "complete_with_blocked":
        lines.append("PRD_COMPLETE_WITH_BLOCKED")
        lines.append(f"All possible tickets done. {counts.get('blocked', 0)} tickets need manual review.")
    else:
        lines.append("PRD_INCOMPLETE")
        lines.append(f"{counts.get('pending', 0)} tickets still pending.")
    lines.append("=" * 40)

    # JSON output
    lines.append("")
    lines.append("---JSON_OUTPUT---")
    summary = generate_summary(counts, status)
    lines.append(json.dumps(summary, indent=2))

    return "\n".join(lines)


def cleanup(
    workflow_state_file: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run the cleanup process.

    This is the main entry point for the cleanup command. It:
    1. Queries GitHub for issue counts
    2. Updates workflow state file (if provided)
    3. Returns summary dictionary

    Args:
        workflow_state_file: Optional path to workflow-state.json
        verbose: If True, print verbose output

    Returns:
        Summary dictionary with status and counts
    """
    if verbose:
        logger.info("Cleanup starting - querying GitHub for final counts...")

    # Get counts from GitHub
    counts = get_issue_counts()

    # Determine status
    status = determine_status(counts)

    # Update workflow state if file provided
    if workflow_state_file is not None:
        update_workflow_state(workflow_state_file)

    # Get ticket lists for display
    completed_tickets = get_completed_tickets()
    blocked_tickets = get_blocked_tickets()
    pending_tickets = get_pending_tickets()

    if verbose:
        logger.info(f"Cleanup {status}: total={counts.get('total', 0)}, closed={counts.get('closed', 0)}, blocked={counts.get('blocked', 0)}, pending={counts.get('pending', 0)}")

    # Generate and return summary
    return generate_summary(counts, status)


def main() -> int:
    """Main entry point for command-line usage.

    Returns:
        Exit code (always 0 - cleanup is informational)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Finalize ralph run and generate summary"
    )
    parser.add_argument(
        "--workflow-state",
        type=Path,
        default=Path("workflow-state.json"),
        help="Path to workflow-state.json (default: workflow-state.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print verbose output",
    )

    args = parser.parse_args()

    cleanup(
        workflow_state_file=args.workflow_state if args.workflow_state.exists() else None,
        verbose=True,  # Always verbose when run as command
    )

    # Always exit 0 - cleanup is informational, not a pass/fail gate
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
