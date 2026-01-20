"""State management for Ralph workflow.

This module handles reading and writing state files that track workflow
progress, ticket statuses, and execution history. All writes are atomic
to prevent corruption from interruptions.

Key components:
- Directory management: ensure_state_dir, get_ticket_state_dir
- Attempt tracking: get_latest_attempt
- State file I/O: get_previous_state, get_previous_validation
- State file writing: write_engineer_state, write_validation_report
- Markdown generation: generate_engineer_state_md, generate_validation_md, generate_summary_md
- Workflow state: load_workflow_state, save_workflow_state, WorkflowState, Ticket
- Prompt building: build_prompt
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================================
# Constants
# ============================================================================

DEFAULT_STATE_DIRECTORY = Path("docs/state")


# ============================================================================
# Dataclasses
# ============================================================================


@dataclass
class Ticket:
    """Represents a ticket in the workflow (v1 schema).

    Attributes:
        id: Unique ticket identifier (e.g., "TASK-001")
        title: Human-readable ticket title
        status: Current status (pending, in_progress, completed, blocked)
        dependencies: List of ticket IDs that must complete first
        attempts: Number of implementation attempts made
        block_reason: Reason for blocking (if status is blocked)
    """

    id: str
    title: str
    status: str
    dependencies: list[str]
    attempts: int = 0
    block_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None or k == "block_reason"}


@dataclass
class RalphState:
    """Represents Ralph's supplemental state data (v2 schema).

    V2 schema stores only supplemental data - ticket status comes from the PM tool.
    This dataclass tracks:
    - Which tickets exist (IDs only, not full objects)
    - Dependencies between tickets
    - Attempt counts per ticket
    - Blocked status and reasons
    - Source PM tool type

    Attributes:
        tickets: List of ticket IDs (strings only, not full ticket objects)
        dependencies: Map of ticket ID to list of dependency ticket IDs
        attempts: Map of ticket ID to attempt count
        blocked: Map of ticket ID to block reason
        source: PM tool type (e.g., "github", "trello", "asana")
    """

    source: str
    tickets: list[str] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    blocked: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tickets": self.tickets,
            "dependencies": self.dependencies,
            "attempts": self.attempts,
            "blocked": self.blocked,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RalphState":
        """Create RalphState from a dictionary.

        Args:
            data: Dictionary containing ralph state data

        Returns:
            RalphState instance
        """
        return cls(
            tickets=data.get("tickets", []),
            dependencies=data.get("dependencies", {}),
            attempts=data.get("attempts", {}),
            blocked=data.get("blocked", {}),
            source=data.get("source", "unknown"),
        )


@dataclass
class WorkflowState:
    """Represents the overall workflow state.

    Supports both v1 and v2 schemas:
    - v1: Uses tickets list with full Ticket objects (including status)
    - v2: Uses ralph field with RalphState (status from PM tool)

    Attributes:
        version: State file format version ("1.0" or "2.0")
        prd_path: Path to the PRD document
        plan_path: Path to the plan document
        tickets: List of tickets in the workflow (v1 schema, kept for backward compat)
        current_ticket: ID of the currently active ticket (or None)
        completed_count: Number of completed tickets
        blocked_count: Number of blocked tickets
        ralph: Ralph's supplemental state data (v2 schema, None for v1)
    """

    version: str
    prd_path: Path
    plan_path: Path
    tickets: list[Ticket]
    current_ticket: str | None = None
    completed_count: int = 0
    blocked_count: int = 0
    ralph: RalphState | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "version": self.version,
            "prd_path": str(self.prd_path),
            "plan_path": str(self.plan_path),
            "tickets": [t.to_dict() for t in self.tickets],
            "current_ticket": self.current_ticket,
            "completed_count": self.completed_count,
            "blocked_count": self.blocked_count,
        }
        # Include ralph field only if present (v2 schema)
        if self.ralph is not None:
            result["ralph"] = self.ralph.to_dict()
        return result


# ============================================================================
# Directory Management
# ============================================================================


def ensure_state_dir(
    ticket_id: str, attempt: int, base_dir: Path | None = None
) -> Path:
    """Ensure state directory exists for a ticket/attempt.

    Args:
        ticket_id: The ticket identifier (e.g., "TASK-001")
        attempt: The attempt number (must be positive)
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Path to the attempt directory

    Raises:
        ValueError: If ticket_id is empty or attempt is not positive
    """
    if not ticket_id:
        raise ValueError("ticket_id is required")
    if attempt < 1:
        raise ValueError("attempt must be a positive integer")

    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY

    state_dir = base_dir / ticket_id / f"attempt-{attempt}"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_ticket_state_dir(ticket_id: str, base_dir: Path | None = None) -> Path:
    """Get path to ticket state directory.

    Args:
        ticket_id: The ticket identifier
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Path to the ticket's state directory
    """
    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY
    return base_dir / ticket_id


# ============================================================================
# Attempt Management
# ============================================================================


def get_latest_attempt(ticket_id: str, base_dir: Path | None = None) -> int:
    """Get the latest attempt number for a ticket.

    Args:
        ticket_id: The ticket identifier
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Highest attempt number, or 0 if none exist
    """
    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY

    ticket_dir = base_dir / ticket_id

    if not ticket_dir.exists():
        return 0

    max_attempt = 0
    for item in ticket_dir.iterdir():
        if item.is_dir() and item.name.startswith("attempt-"):
            try:
                attempt_num = int(item.name.replace("attempt-", ""))
                max_attempt = max(max_attempt, attempt_num)
            except ValueError:
                continue

    return max_attempt


# ============================================================================
# State File Reading
# ============================================================================


def get_previous_state(
    ticket_id: str, attempt: int | None = None, base_dir: Path | None = None
) -> str:
    """Get previous engineer state file contents.

    Prefers markdown over JSON. If attempt is not specified, uses the latest attempt.

    Args:
        ticket_id: The ticket identifier
        attempt: Specific attempt number (optional, defaults to latest)
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Contents of engineer-state.md (preferred) or .json, or empty string if not found
    """
    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY

    if attempt is None:
        attempt = get_latest_attempt(ticket_id, base_dir)

    if attempt == 0:
        return ""

    state_dir = base_dir / ticket_id / f"attempt-{attempt}"
    md_file = state_dir / "engineer-state.md"
    json_file = state_dir / "engineer-state.json"

    if md_file.exists():
        return md_file.read_text()
    elif json_file.exists():
        # Fallback: convert JSON to readable format
        try:
            data = json.loads(json_file.read_text())
            lines = []
            for key, value in data.items():
                lines.append(f"**{key}:** {value}")
            return "\n".join(lines)
        except json.JSONDecodeError:
            return json_file.read_text()
    else:
        return ""


def get_previous_validation(
    ticket_id: str, attempt: int | None = None, base_dir: Path | None = None
) -> str:
    """Get previous validation report contents.

    Prefers markdown over JSON. If attempt is not specified, uses the latest attempt.

    Args:
        ticket_id: The ticket identifier
        attempt: Specific attempt number (optional, defaults to latest)
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Contents of validation.md (preferred) or .json, or empty string if not found
    """
    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY

    if attempt is None:
        attempt = get_latest_attempt(ticket_id, base_dir)

    if attempt == 0:
        return ""

    state_dir = base_dir / ticket_id / f"attempt-{attempt}"
    md_file = state_dir / "validation.md"
    json_file = state_dir / "validation.json"

    if md_file.exists():
        return md_file.read_text()
    elif json_file.exists():
        try:
            data = json.loads(json_file.read_text())
            lines = []
            for key, value in data.items():
                lines.append(f"**{key}:** {value}")
            return "\n".join(lines)
        except json.JSONDecodeError:
            return json_file.read_text()
    else:
        return ""


# ============================================================================
# State File Writing
# ============================================================================


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically.

    Uses a temporary file and rename to ensure atomic writes.

    Args:
        path: Target file path
        content: Content to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory, then rename
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent, prefix=".tmp_", suffix=path.suffix
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.rename(temp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def write_engineer_state(
    state_data: dict[str, Any], base_dir: Path | None = None
) -> Path:
    """Write engineer state to both JSON and markdown files.

    Args:
        state_data: Dictionary containing state information
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Path to the markdown file
    """
    ticket_id = state_data["ticket_id"]
    attempt = state_data["attempt"]

    state_dir = ensure_state_dir(ticket_id, attempt, base_dir)

    # Write JSON file
    json_file = state_dir / "engineer-state.json"
    json_content = json.dumps(state_data, indent=2)
    _atomic_write(json_file, json_content)

    # Generate and write markdown file
    md_file = state_dir / "engineer-state.md"
    md_content = generate_engineer_state_md(state_data)
    _atomic_write(md_file, md_content)

    return md_file


def write_validation_report(
    validation_data: dict[str, Any], base_dir: Path | None = None
) -> Path:
    """Write validation report to both JSON and markdown files.

    Args:
        validation_data: Dictionary containing validation information
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Path to the markdown file
    """
    ticket_id = validation_data["ticket_id"]
    attempt = validation_data["attempt"]

    state_dir = ensure_state_dir(ticket_id, attempt, base_dir)

    # Write JSON file
    json_file = state_dir / "validation.json"
    json_content = json.dumps(validation_data, indent=2)
    _atomic_write(json_file, json_content)

    # Generate and write markdown file
    md_file = state_dir / "validation.md"
    md_content = generate_validation_md(validation_data)
    _atomic_write(md_file, md_content)

    return md_file


def write_summary(
    ticket_id: str,
    status: str,
    total_attempts: int,
    pr_number: str | None = None,
    usage: dict[str, Any] | None = None,
    base_dir: Path | None = None,
) -> Path:
    """Write ticket summary after completion or blocking.

    Args:
        ticket_id: The ticket identifier
        status: Final status ("SUCCESS" or "BLOCKED")
        total_attempts: Total number of attempts made
        pr_number: PR number if merged (optional)
        usage: Usage metrics dictionary (optional)
        base_dir: Base directory for state files (default: docs/state)

    Returns:
        Path to the summary markdown file
    """
    if base_dir is None:
        base_dir = DEFAULT_STATE_DIRECTORY

    ticket_dir = base_dir / ticket_id
    ticket_dir.mkdir(parents=True, exist_ok=True)

    # Build attempt history from existing state files
    attempt_history = []
    for i in range(1, total_attempts + 1):
        state_file = ticket_dir / f"attempt-{i}" / "engineer-state.json"
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text())
                attempt_status = state_data.get("status", "unknown")
                known_issues = state_data.get("known_issues", [])
                key_issues = ", ".join(known_issues) if known_issues else "None"
            except json.JSONDecodeError:
                attempt_status = "unknown"
                key_issues = "Failed to parse state file"
        else:
            attempt_status = "unknown"
            key_issues = "No state file"

        attempt_history.append({
            "attempt": i,
            "status": attempt_status,
            "key_issues": key_issues,
        })

    # Build outcome description
    if status == "SUCCESS":
        outcome = f"Ticket completed successfully after {total_attempts} attempt(s). PR #{pr_number} merged."
    else:
        outcome = f"Ticket blocked after {total_attempts} attempt(s). Manual intervention required."

    # Get lessons learned from last state file if blocked
    lessons = []
    if status == "BLOCKED":
        last_state_file = ticket_dir / f"attempt-{total_attempts}" / "engineer-state.json"
        if last_state_file.exists():
            try:
                last_state = json.loads(last_state_file.read_text())
                lessons = last_state.get("known_issues", []) + last_state.get("next_steps", [])
            except json.JSONDecodeError:
                pass

    # Build summary data
    summary_data = {
        "ticket_id": ticket_id,
        "final_status": status,
        "total_attempts": total_attempts,
        "completed": datetime.now().isoformat(),
        "outcome": outcome,
        "attempt_history": attempt_history,
        "branch": f"feature/{ticket_id}-implementation",
        "last_commit": "N/A",  # Would need git to get this
        "pr_number": pr_number or "None (blocked)",
        "files_changed": [],  # Would need git to get this
        "lessons_learned": lessons,
    }

    if usage:
        summary_data["usage"] = usage

    # Write JSON file
    json_file = ticket_dir / "summary.json"
    json_content = json.dumps(summary_data, indent=2)
    _atomic_write(json_file, json_content)

    # Generate and write markdown file
    md_file = ticket_dir / "summary.md"
    md_content = generate_summary_md(summary_data)
    _atomic_write(md_file, md_content)

    return md_file


# ============================================================================
# Markdown Generation
# ============================================================================


def _status_display(status: str) -> str:
    """Convert status to display text."""
    mapping = {
        "pass": "PASS",
        "fail": "FAIL",
        "skip": "SKIP",
    }
    return mapping.get(status, status)


def generate_engineer_state_md(state_data: dict[str, Any]) -> str:
    """Generate engineer state markdown from data.

    Args:
        state_data: Dictionary containing state information

    Returns:
        Formatted markdown string
    """
    ticket_id = state_data.get("ticket_id", "UNKNOWN")
    attempt = state_data.get("attempt", 1)
    timestamp = state_data.get("timestamp", "N/A")
    status = state_data.get("status", "unknown")
    branch = state_data.get("branch", "N/A")
    last_commit = state_data.get("last_commit", "N/A")

    # Validation results
    validation = state_data.get("validation_result", {})
    typecheck = validation.get("typecheck", "skip")
    lint = validation.get("lint", "skip")
    test_result = validation.get("test", "skip")
    build = validation.get("build", "skip")
    overall = validation.get("overall", "unknown")

    # List sections
    work_completed = state_data.get("work_completed", [])
    files_modified = state_data.get("files_modified", [])
    known_issues = state_data.get("known_issues", [])
    next_steps = state_data.get("next_steps", [])
    tests_written = state_data.get("tests_written", [])

    # Format lists
    work_list = "\n".join(f"- {item}" for item in work_completed) or "- No work items recorded"
    files_list = "\n".join(f"- `{item}`" for item in files_modified) or "- No files recorded"
    issues_list = "\n".join(f"- {item}" for item in known_issues) or "- No known issues"
    steps_list = "\n".join(f"{i+1}. {item}" for i, item in enumerate(next_steps)) or "- No next steps specified"

    # Format tests
    if tests_written:
        tests_sections = []
        for test_file in tests_written:
            file_name = test_file.get("file", "Unknown file")
            tests = test_file.get("tests", [])
            tests_list = "\n".join(f"- {t}" for t in tests)
            tests_sections.append(f"### {file_name}\n\n{tests_list}")
        tests_md = "\n\n".join(tests_sections)
    else:
        tests_md = "No tests recorded"

    return f"""# Engineer State: {ticket_id}

**Attempt:** {attempt}
**Timestamp:** {timestamp}
**Status:** {status}
**Branch:** `{branch}`
**Last Commit:** `{last_commit}`

---

## Validation Result

| Check | Result |
|-------|--------|
| TypeScript | {_status_display(typecheck)} |
| Lint | {_status_display(lint)} |
| Tests | {_status_display(test_result)} |
| Build | {_status_display(build)} |
| **Overall** | **{_status_display(overall)}** |

---

## Work Completed

{work_list}

---

## Files Modified

{files_list}

---

## Tests Written

{tests_md}

---

## Known Issues

{issues_list}

---

## Next Steps (If Resuming)

{steps_list}
"""


def generate_validation_md(validation_data: dict[str, Any]) -> str:
    """Generate validation report markdown from data.

    Args:
        validation_data: Dictionary containing validation information

    Returns:
        Formatted markdown string
    """
    ticket_id = validation_data.get("ticket_id", "UNKNOWN")
    attempt = validation_data.get("attempt", 1)
    timestamp = validation_data.get("timestamp", "N/A")
    overall_result = validation_data.get("overall_result", "unknown")

    checks = validation_data.get("checks", {})

    # Typecheck
    ts = checks.get("typecheck", {})
    ts_status = ts.get("status", "skip")
    ts_errors = ts.get("error_count", 0)
    ts_error_list = ts.get("errors", [])

    # Lint
    lint = checks.get("lint", {})
    lint_status = lint.get("status", "skip")
    lint_errors = lint.get("error_count", 0)
    lint_warnings = lint.get("warning_count", 0)
    lint_error_list = lint.get("errors", [])

    # Test
    test = checks.get("test", {})
    test_status = test.get("status", "skip")
    test_total = test.get("total", 0)
    test_passed = test.get("passed", 0)
    test_failed = test.get("failed", 0)
    test_failures = test.get("failures", [])

    # Build
    build = checks.get("build", {})
    build_status = build.get("status", "skip")
    build_errors_count = build.get("error_count", 0)
    build_error_list = build.get("errors", [])

    root_cause = validation_data.get("root_cause_analysis", "No analysis provided")
    suggested_fixes = validation_data.get("suggested_fixes", [])
    priority_order = validation_data.get("priority_order", [])

    # Format error lists
    ts_errors_md = "No TypeScript errors"
    if ts_error_list:
        lines = []
        for err in ts_error_list:
            lines.append(f"- **{err.get('file', 'unknown')}:{err.get('line', '?')}**: {err.get('message', '')} ({err.get('code', '')})")
        ts_errors_md = "\n".join(lines)

    lint_errors_md = "No lint errors"
    if lint_error_list:
        lines = []
        for err in lint_error_list:
            lines.append(f"- **{err.get('file', 'unknown')}:{err.get('line', '?')}**: [{err.get('rule', '')}] {err.get('message', '')} ({err.get('severity', '')})")
        lint_errors_md = "\n".join(lines)

    test_failures_md = "No test failures"
    if test_failures:
        lines = []
        for fail in test_failures:
            lines.append(f"""### {fail.get('file', 'Unknown')}

**Test:** {fail.get('test_name', 'Unknown')}

**Error:**
```
{fail.get('error', 'N/A')}
```

**Expected:** {fail.get('expected', 'N/A')}
**Received:** {fail.get('received', 'N/A')}
""")
        test_failures_md = "\n".join(lines)

    build_errors_md = "No build errors"
    if build_error_list:
        lines = []
        for err in build_error_list:
            lines.append(f"- **{err.get('file', 'unknown')}**: {err.get('message', '')}")
        build_errors_md = "\n".join(lines)

    fixes_md = "\n".join(f"{i+1}. {fix}" for i, fix in enumerate(suggested_fixes)) or "No suggestions provided"
    priority_md = "\n".join(f"{i+1}. {p}" for i, p in enumerate(priority_order)) or "No priority order specified"

    return f"""# Validation Report: {ticket_id}

**Attempt:** {attempt}
**Timestamp:** {timestamp}
**Overall Result:** {overall_result}

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| TypeScript | {ts_status} | {ts_errors} errors |
| Lint | {lint_status} | {lint_errors} errors, {lint_warnings} warnings |
| Tests | {test_status} | {test_passed}/{test_total} passed, {test_failed} failed |
| Build | {build_status} | {build_errors_count} errors |

---

## TypeScript Errors

{ts_errors_md}

---

## Lint Errors

{lint_errors_md}

---

## Test Failures

{test_failures_md}

---

## Build Errors

{build_errors_md}

---

## Root Cause Analysis

{root_cause}

---

## Suggested Fixes

{fixes_md}

---

## Priority Order

{priority_md}
"""


def generate_summary_md(summary_data: dict[str, Any]) -> str:
    """Generate summary markdown from data.

    Args:
        summary_data: Dictionary containing summary information

    Returns:
        Formatted markdown string
    """
    ticket_id = summary_data.get("ticket_id", "UNKNOWN")
    final_status = summary_data.get("final_status", "UNKNOWN")
    total_attempts = summary_data.get("total_attempts", 0)
    completed = summary_data.get("completed", "N/A")
    outcome = summary_data.get("outcome", "No outcome recorded")
    attempt_history = summary_data.get("attempt_history", [])
    branch = summary_data.get("branch", "N/A")
    last_commit = summary_data.get("last_commit", "N/A")
    pr_number = summary_data.get("pr_number", "None (blocked)")
    files_changed = summary_data.get("files_changed", [])
    lessons_learned = summary_data.get("lessons_learned", [])
    usage = summary_data.get("usage")

    # Format attempt history
    if attempt_history:
        history_lines = []
        for h in attempt_history:
            history_lines.append(f"| {h.get('attempt', '-')} | {h.get('status', '-')} | {h.get('key_issues', '-')} |")
        history_md = "\n".join(history_lines)
    else:
        history_md = "| - | - | No history recorded |"

    # Format files
    files_md = "\n".join(f"- `{f}`" for f in files_changed) or "- No files recorded"

    # Format lessons
    lessons_md = "\n".join(f"- {l}" for l in lessons_learned) or "- No lessons recorded"

    # Format usage if present
    usage_section = ""
    if usage:
        invocations = usage.get("invocation_count", 0)
        duration = usage.get("duration_seconds", 0)
        cost = usage.get("total_cost", 0)
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_tokens", 0)
        model = usage.get("model", "unknown")
        complexity = usage.get("complexity", "unknown")

        mins = duration // 60
        secs = duration % 60

        usage_section = f"""---

## Usage Metrics

| Metric | Value |
|--------|-------|
| Model | {model} |
| Complexity | {complexity} |
| Invocations | {invocations} |
| Duration | {mins}m {secs}s |
| Input Tokens | {input_tokens} |
| Output Tokens | {output_tokens} |
| Cache Read | {cache_read} |
| **Cost** | ${cost:.4f} |
"""

    return f"""# Ticket Summary: {ticket_id}

**Final Status:** {final_status}
**Total Attempts:** {total_attempts}
**Completed:** {completed}

---

## Outcome

{outcome}

---

## Attempt History

| Attempt | Status | Key Issues |
|---------|--------|------------|
{history_md}

---

## Final State

**Branch:** `{branch}`
**Last Commit:** `{last_commit}`
**PR:** {pr_number}

---

## Files Changed

{files_md}
{usage_section}
---

## Lessons Learned

{lessons_md}
"""


# ============================================================================
# V1 to V2 Migration
# ============================================================================


def migrate_v1_to_v2(v1_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate v1 state format to v2.

    V1 stores full ticket objects with status in a "tickets" list.
    V2 stores supplemental data in a "ralph" object (status comes from PM tool).

    Args:
        v1_data: Dictionary in v1 format

    Returns:
        Dictionary in v2 format
    """
    tickets = v1_data.get("tickets", [])

    # Extract ticket IDs
    ticket_ids = [t["id"] for t in tickets]

    # Extract dependencies (only for tickets that have non-empty dependencies)
    dependencies: dict[str, list[str]] = {}
    for t in tickets:
        deps = t.get("dependencies", [])
        if deps:
            dependencies[t["id"]] = deps

    # Extract attempt counts (only for non-zero attempts)
    attempts: dict[str, int] = {}
    for t in tickets:
        attempt_count = t.get("attempts", 0)
        if attempt_count > 0:
            attempts[t["id"]] = attempt_count

    # Extract blocked reasons
    blocked: dict[str, str] = {}
    for t in tickets:
        if t.get("status") == "blocked":
            reason = t.get("block_reason") or "Blocked (migrated from v1)"
            blocked[t["id"]] = reason

    return {
        "version": "2.0",
        "prd_path": v1_data.get("prd_path", ""),
        "plan_path": v1_data.get("plan_path", ""),
        "tickets": [],  # v2 doesn't use tickets list
        "ralph": {
            "tickets": ticket_ids,
            "dependencies": dependencies,
            "attempts": attempts,
            "blocked": blocked,
            "source": "unknown",  # Can't determine source from v1
        },
    }


def _is_v1_state(data: dict[str, Any]) -> bool:
    """Check if state data is in v1 format.

    V1 is detected when:
    - version is "1.0" or missing
    - AND ralph section is missing

    Args:
        data: State data dictionary

    Returns:
        True if v1 format, False otherwise
    """
    version = data.get("version", "1.0")
    has_ralph = "ralph" in data

    # v1 format: version 1.0 (or missing) and no ralph section
    return version == "1.0" and not has_ralph


# ============================================================================
# Workflow State Management
# ============================================================================


def load_workflow_state(state_file: Path) -> WorkflowState:
    """Load workflow state from a JSON file.

    Supports both v1 and v2 schemas. V1 files are auto-migrated to v2:
    - v1: Full ticket objects with status stored locally
    - v2: ralph section with ticket IDs only, status from PM tool

    Args:
        state_file: Path to the state file

    Returns:
        WorkflowState object (always in v2 format)

    Raises:
        FileNotFoundError: If the state file doesn't exist
        ValueError: If the state file contains invalid JSON
    """
    if not state_file.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")

    try:
        data = json.loads(state_file.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in state file: {e}")

    # Auto-migrate v1 to v2
    if _is_v1_state(data):
        print(
            f"Migrating state file from v1.0 to v2.0: {state_file}",
            file=sys.stderr,
        )
        data = migrate_v1_to_v2(data)

    # Parse tickets (v1 schema - may be empty for v2)
    tickets = [
        Ticket(
            id=t["id"],
            title=t["title"],
            status=t["status"],
            dependencies=t.get("dependencies", []),
            attempts=t.get("attempts", 0),
            block_reason=t.get("block_reason"),
        )
        for t in data.get("tickets", [])
    ]

    # Parse ralph section (v2 schema - should always exist after migration)
    ralph_data = data.get("ralph")
    ralph = RalphState.from_dict(ralph_data) if ralph_data is not None else None

    return WorkflowState(
        version=data.get("version", "2.0"),
        prd_path=Path(data["prd_path"]),
        plan_path=Path(data["plan_path"]),
        tickets=tickets,
        current_ticket=data.get("current_ticket"),
        completed_count=data.get("completed_count", 0),
        blocked_count=data.get("blocked_count", 0),
        ralph=ralph,
    )


def save_workflow_state(state: WorkflowState, state_file: Path) -> None:
    """Save workflow state to a JSON file atomically.

    Args:
        state: WorkflowState object to save
        state_file: Path to the state file
    """
    content = json.dumps(state.to_dict(), indent=2)
    _atomic_write(state_file, content)


def update_ticket_status(state_file: Path, ticket_id: str, new_status: str) -> None:
    """Update a ticket's status in the workflow state file.

    Args:
        state_file: Path to the state file
        ticket_id: ID of the ticket to update
        new_status: New status value
    """
    state = load_workflow_state(state_file)

    for ticket in state.tickets:
        if ticket.id == ticket_id:
            ticket.status = new_status
            break

    save_workflow_state(state, state_file)


def get_ticket_by_id(state: WorkflowState, ticket_id: str) -> Ticket | None:
    """Get a ticket by its ID.

    Args:
        state: WorkflowState object
        ticket_id: ID of the ticket to find

    Returns:
        Ticket object if found, None otherwise
    """
    for ticket in state.tickets:
        if ticket.id == ticket_id:
            return ticket
    return None


# ============================================================================
# Prompt Building
# ============================================================================


def build_prompt(
    template_file: Path,
    config_dir: Path | None = None,
    **substitutions: str,
) -> str:
    """Build a prompt from a template file with placeholder substitution.

    Substitutes all {KEY} patterns with provided values.
    Also automatically reads commands from config.yaml.

    Args:
        template_file: Path to the template file
        config_dir: Directory containing config.yaml (optional)
        **substitutions: Key-value pairs for placeholder substitution

    Returns:
        Processed template content

    Raises:
        FileNotFoundError: If the template file doesn't exist
    """
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_file}")

    content = template_file.read_text()

    # Process all substitutions
    for key, value in substitutions.items():
        placeholder = f"{{{key}}}"
        content = content.replace(placeholder, value)

    # Try to read config.yaml for auto-substitution
    if config_dir is not None:
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            try:
                import yaml
                config = yaml.safe_load(config_file.read_text())
                dev = config.get("dev", {})

                config_subs = {
                    "TEST_COMMAND": dev.get("test_command", ""),
                    "LINT_COMMAND": dev.get("lint_command", ""),
                    "TYPECHECK_COMMAND": dev.get("typecheck_command", ""),
                    "BUILD_COMMAND": dev.get("build_command", ""),
                    "DEFAULT_BRANCH": dev.get("default_branch", "main"),
                }

                for key, value in config_subs.items():
                    if value:
                        placeholder = f"{{{key}}}"
                        content = content.replace(placeholder, value)
            except Exception:
                pass  # Ignore config loading errors

    # Warn about unsubstituted placeholders
    remaining = re.findall(r"\{[A-Z_]+\}", content)
    if remaining:
        print(f"WARNING: Unsubstituted placeholders remain:", file=sys.stderr)
        for placeholder in set(remaining):
            print(f"  - {placeholder}", file=sys.stderr)

    return content
