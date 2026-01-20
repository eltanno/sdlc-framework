"""Parse ticket dependencies from plan documents.

This module handles:
- Parsing dependency tables from markdown (table format)
- Parsing dependency sections from markdown (section format)
- Building dependency graphs
- Detecting circular dependencies

Supports TWO formats:

FORMAT 1 - Table format:
| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| TASK-001 | Title | Desc | P1 | 2 | 1 | - |
| TASK-002 | Title | Desc | P1 | 2 | 1 | TASK-001 |

Or with row numbers:
| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | Title | Desc | P1 | 2 | 1 | - |
| 2 | Title | Desc | P1 | 2 | 1 | 1 |

FORMAT 2 - Section format:
### TEST-001: Title here
- **Dependencies:** None (or TEST-001, TEST-002)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class ParseError(Exception):
    """Raised when parsing fails due to invalid format."""

    pass


@dataclass
class DependencyGraph:
    """Represents a dependency graph of tickets.

    Attributes:
        dependencies: Dictionary mapping ticket ID to list of dependency IDs
        ticket_prefix: The prefix used for ticket IDs (e.g., "TASK", "SDLC")
    """

    dependencies: dict[str, list[str]]
    ticket_prefix: str = ""

    def get_dependencies(self, ticket_id: str) -> list[str]:
        """Get the list of dependencies for a ticket.

        Args:
            ticket_id: The ticket ID to look up

        Returns:
            List of ticket IDs that this ticket depends on,
            or empty list if ticket not found
        """
        return self.dependencies.get(ticket_id, [])

    def get_dependents(self, ticket_id: str) -> list[str]:
        """Get the list of tickets that depend on a given ticket.

        Args:
            ticket_id: The ticket ID to look up

        Returns:
            List of ticket IDs that depend on this ticket
        """
        dependents = []
        for tid, deps in self.dependencies.items():
            if ticket_id in deps:
                dependents.append(tid)
        return dependents

    def to_dict(self) -> dict[str, list[str]]:
        """Convert the graph to a dictionary.

        Returns:
            Dictionary mapping ticket IDs to their dependencies
        """
        return self.dependencies


def parse_dependencies(
    plan_path: Path,
    ticket_prefix: str | None = None,
    start_num: int | None = None,
) -> dict[str, list[str]]:
    """Parse ticket dependencies from a plan document.

    Supports both table format and section format. Automatically detects
    which format is used based on content.

    Args:
        plan_path: Path to the plan markdown file
        ticket_prefix: Optional prefix for ticket IDs (e.g., "TASK").
                      Required if using row number format.
        start_num: Starting number for ticket ID mapping when using row numbers.
                  Required if using row number format.

    Returns:
        Dictionary mapping ticket IDs to lists of dependency ticket IDs.
        Empty list means no dependencies.

    Raises:
        FileNotFoundError: If the plan file doesn't exist
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    content = plan_path.read_text()

    if not content.strip():
        return {}

    # Try table format first
    result = _parse_table_format(content, ticket_prefix, start_num)

    # If no results from table format, try section format
    if not result:
        result = _parse_section_format(content)

    return result


def _parse_table_format(
    content: str,
    ticket_prefix: str | None = None,
    start_num: int | None = None,
) -> dict[str, list[str]]:
    """Parse dependencies from table format.

    Args:
        content: The plan content
        ticket_prefix: Optional prefix for row number mapping
        start_num: Starting number for row number mapping

    Returns:
        Dictionary of dependencies
    """
    result: dict[str, list[str]] = {}

    # Find table header row
    lines = content.split("\n")
    in_table = False
    header_cols: list[str] = []
    id_col_idx = -1
    deps_col_idx = -1

    for line in lines:
        line = line.strip()

        # Detect table header (looking for ID or # column and Dependencies column)
        if not in_table and "|" in line:
            # Check if this looks like a header row
            # Split by | but keep structure (first and last elements will be empty)
            raw_cols = line.split("|")
            # Strip whitespace but keep all elements to preserve column indices
            cols = [c.strip() for c in raw_cols]
            # Find non-empty columns for header detection
            non_empty_cols = [(i, c) for i, c in enumerate(cols) if c]

            # Look for ID/# column and Dependencies column
            for i, col in non_empty_cols:
                col_lower = col.lower()
                if col_lower in ("id", "#"):
                    id_col_idx = i
                elif "dependencies" in col_lower or "dependency" in col_lower:
                    deps_col_idx = i

            if id_col_idx >= 0 and deps_col_idx >= 0:
                header_cols = cols
                in_table = True
                continue

        # Skip separator rows
        if in_table and re.match(r"^\|[-|\s]+\|$", line):
            continue

        # If we're in the table and hit a non-table line, we're done
        if in_table and not line.startswith("|"):
            break

        # Parse table data rows
        if in_table and line.startswith("|"):
            # Split by | and preserve structure for proper column indexing
            raw_cols = line.split("|")
            cols = [c.strip() for c in raw_cols]

            if len(cols) <= max(id_col_idx, deps_col_idx):
                continue  # Skip malformed rows

            id_value = cols[id_col_idx] if id_col_idx < len(cols) else ""
            deps_value = cols[deps_col_idx] if deps_col_idx < len(cols) else ""

            # Determine ticket ID
            ticket_id = _extract_ticket_id(id_value, ticket_prefix, start_num)
            if not ticket_id:
                continue

            # Parse dependencies
            deps = _parse_deps_value(deps_value, ticket_prefix, start_num)

            result[ticket_id] = deps

    return result


def _extract_ticket_id(
    value: str,
    ticket_prefix: str | None = None,
    start_num: int | None = None,
) -> str | None:
    """Extract or construct a ticket ID from a value.

    Args:
        value: The raw value from the ID column
        ticket_prefix: Optional prefix for row number mapping
        start_num: Starting number for row number mapping

    Returns:
        The ticket ID, or None if invalid
    """
    value = value.strip()

    # Check if it's already a full ticket ID (PREFIX-NNNN format)
    ticket_pattern = re.compile(r"^[A-Z]+-\d+$")
    if ticket_pattern.match(value):
        return value

    # Check if it's a row number
    if value.isdigit() and ticket_prefix is not None and start_num is not None:
        row_num = int(value)
        ticket_num = start_num + row_num - 1
        return f"{ticket_prefix}-{ticket_num:04d}"

    return None


def _parse_deps_value(
    value: str,
    ticket_prefix: str | None = None,
    start_num: int | None = None,
) -> list[str]:
    """Parse a dependencies cell value into a list of ticket IDs.

    Args:
        value: The raw dependencies value
        ticket_prefix: Optional prefix for row number mapping
        start_num: Starting number for row number mapping

    Returns:
        List of dependency ticket IDs
    """
    value = value.strip()

    # No dependencies
    if not value or value == "-" or value.lower() == "none":
        return []

    deps = []

    # First try to extract full ticket IDs (PREFIX-NNNN format)
    ticket_ids = re.findall(r"[A-Z]+-\d+", value)
    if ticket_ids:
        return ticket_ids

    # Otherwise, treat as comma-separated row numbers
    if ticket_prefix is not None and start_num is not None:
        for part in value.split(","):
            part = part.strip()
            if part.isdigit():
                row_num = int(part)
                ticket_num = start_num + row_num - 1
                dep_id = f"{ticket_prefix}-{ticket_num:04d}"
                deps.append(dep_id)

    return deps


def _parse_section_format(content: str) -> dict[str, list[str]]:
    """Parse dependencies from section format.

    Section format:
    ### PREFIX-NNN: Title
    - **Dependencies:** PREFIX-XXX, PREFIX-YYY (or "None" or "-")

    Args:
        content: The plan content

    Returns:
        Dictionary of dependencies
    """
    result: dict[str, list[str]] = {}
    current_ticket: str | None = None

    # Pattern for section headers like "### TASK-001:" or "### SDLC-0019:"
    header_pattern = re.compile(r"^###\s+([A-Z]+-\d+):", re.MULTILINE)

    # Pattern for dependencies line
    deps_pattern = re.compile(
        r"^\s*-\s*\*\*[Dd]ependencies:?\*\*:?\s*(.*)$", re.MULTILINE
    )

    for line in content.split("\n"):
        # Check for section header
        header_match = header_pattern.match(line)
        if header_match:
            current_ticket = header_match.group(1)
            result[current_ticket] = []  # Initialize with empty deps
            continue

        # Check for dependencies line
        if current_ticket:
            deps_match = deps_pattern.match(line)
            if deps_match:
                deps_value = deps_match.group(1).strip()

                # Check for "None", "-", or empty
                if not deps_value or deps_value.lower() == "none" or deps_value == "-":
                    result[current_ticket] = []
                else:
                    # Extract ticket IDs
                    ticket_ids = re.findall(r"[A-Z]+-\d+", deps_value)
                    result[current_ticket] = ticket_ids

    return result


def detect_circular_dependencies(
    dependencies: dict[str, list[str]],
) -> list[list[str]]:
    """Detect circular dependencies in the dependency graph.

    Uses depth-first search to find all cycles in the graph.

    Args:
        dependencies: Dictionary mapping ticket IDs to dependency lists

    Returns:
        List of cycles found. Each cycle is a list of ticket IDs
        forming the cycle. Empty list if no cycles.
    """
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        """Depth-first search for cycle detection."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for dep in dependencies.get(node, []):
            if dep not in visited:
                dfs(dep)
            elif dep in rec_stack:
                # Found a cycle - extract it
                cycle_start_idx = path.index(dep)
                cycle = path[cycle_start_idx:] + [dep]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    # Run DFS from each unvisited node
    for ticket_id in dependencies:
        if ticket_id not in visited:
            dfs(ticket_id)

    return cycles
