"""Parse ticket dependencies from plan documents.

This module handles:
- Parsing dependency tables from markdown
- Parsing dependency sections from markdown
- Building dependency graphs
- Detecting circular dependencies
"""

import re
from pathlib import Path
from typing import Optional


class ParseError(Exception):
    """Raised when plan parsing fails."""

    pass


def parse_dependencies(
    plan_path: Path,
    ticket_prefix: str,
    start_number: Optional[int] = None,
) -> dict[str, list[str]]:
    """Parse ticket dependencies from a plan document.

    Supports two formats:

    **Table format:**
    ```
    | ID | Title | Dependencies |
    |----|-------|--------------|
    | SDLC-0001 | Task | - |
    | SDLC-0002 | Task | SDLC-0001 |
    ```

    **Row number format:**
    ```
    | # | Title | Dependencies |
    |---|-------|--------------|
    | 1 | Task | - |
    | 2 | Task | 1 |
    ```

    **Section format:**
    ```
    ### TEST-001: Title
    - **Dependencies:** None

    ### TEST-002: Title
    - **Dependencies:** TEST-001
    ```

    Args:
        plan_path: Path to the plan markdown file.
        ticket_prefix: Ticket ID prefix (e.g., "SDLC", "AUCT", "TEST").
        start_number: Starting ticket number for row-number format tables.
            Required when table uses row numbers instead of ticket IDs.

    Returns:
        Dict mapping ticket IDs to list of dependency ticket IDs.
        Example: {"SDLC-0001": [], "SDLC-0002": ["SDLC-0001"]}

    Raises:
        ParseError: If the plan file is not found.
    """
    if not plan_path.exists():
        raise ParseError(f"Plan file not found: {plan_path}")

    content = plan_path.read_text()

    if not content.strip():
        return {}

    # Try table format first
    result = _parse_table_format(content, ticket_prefix, start_number)

    # If no tickets found, try section format
    if not result:
        result = _parse_section_format(content, ticket_prefix)

    return result


def _parse_table_format(
    content: str,
    ticket_prefix: str,
    start_number: Optional[int] = None,
) -> dict[str, list[str]]:
    """Parse dependencies from markdown table format.

    Args:
        content: Plan file content.
        ticket_prefix: Ticket ID prefix.
        start_number: Starting ticket number for row-number tables.

    Returns:
        Dict mapping ticket IDs to dependency lists.
    """
    result: dict[str, list[str]] = {}

    # Find table rows
    lines = content.split("\n")
    in_table = False
    header_found = False
    dep_column_index = -1
    id_column_index = -1
    uses_row_numbers = False

    for line in lines:
        line = line.strip()

        # Detect table header
        if not header_found and "|" in line:
            # Check if this looks like a header row
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]  # Remove empty cells

            # Look for Dependencies column
            for i, cell in enumerate(cells):
                if cell.lower() in ("dependencies", "dependency"):
                    dep_column_index = i
                    header_found = True

            # Look for ID column or # column
            for i, cell in enumerate(cells):
                cell_lower = cell.lower()
                if cell_lower in ("id", "#"):
                    id_column_index = i
                    if cell_lower == "#":
                        uses_row_numbers = True

            if header_found:
                in_table = True
                continue

        # Skip separator rows (|---|---|)
        if in_table and re.match(r"^\|[-|\s]+\|$", line):
            continue

        # If we're in table and hit a non-table line, we're done
        if in_table and not line.startswith("|"):
            break

        # Parse data rows
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]  # Remove empty cells

            if len(cells) <= max(id_column_index, dep_column_index):
                continue

            # Get ticket ID
            id_cell = cells[id_column_index] if id_column_index >= 0 else ""
            deps_cell = cells[dep_column_index] if dep_column_index >= 0 else ""

            if uses_row_numbers:
                # Convert row number to ticket ID
                try:
                    row_num = int(id_cell)
                    if start_number is None:
                        # Try to extract start number from content
                        start_number = _find_start_number(content, ticket_prefix)
                    ticket_num = (start_number or 1) + row_num - 1
                    ticket_id = f"{ticket_prefix}-{ticket_num:04d}"
                except ValueError:
                    continue
            else:
                # Extract ticket ID from cell
                match = re.search(rf"{ticket_prefix}-\d+", id_cell)
                if match:
                    ticket_id = match.group(0)
                else:
                    continue

            # Parse dependencies
            deps = _parse_deps_cell(deps_cell, ticket_prefix, start_number, uses_row_numbers)
            result[ticket_id] = deps

    return result


def _parse_section_format(content: str, ticket_prefix: str) -> dict[str, list[str]]:
    """Parse dependencies from section format.

    Args:
        content: Plan file content.
        ticket_prefix: Ticket ID prefix.

    Returns:
        Dict mapping ticket IDs to dependency lists.
    """
    result: dict[str, list[str]] = {}
    current_ticket: Optional[str] = None

    # Pattern for section header: ### PREFIX-XXX: Title
    header_pattern = re.compile(rf"^###\s+({ticket_prefix}-\d+):", re.IGNORECASE)
    # Pattern for dependencies line: - **Dependencies:** value
    deps_pattern = re.compile(r"^\-\s+\*\*[Dd]ependencies:?\*\*:?\s*(.*)", re.IGNORECASE)

    for line in content.split("\n"):
        line = line.strip()

        # Check for section header
        header_match = header_pattern.match(line)
        if header_match:
            current_ticket = header_match.group(1)
            result[current_ticket] = []
            continue

        # Check for dependencies line
        if current_ticket:
            deps_match = deps_pattern.match(line)
            if deps_match:
                deps_value = deps_match.group(1).strip()
                result[current_ticket] = _parse_deps_value(deps_value, ticket_prefix)

    return result


def _parse_deps_cell(
    cell: str,
    ticket_prefix: str,
    start_number: Optional[int] = None,
    uses_row_numbers: bool = False,
) -> list[str]:
    """Parse a dependencies table cell.

    Args:
        cell: Cell content.
        ticket_prefix: Ticket ID prefix.
        start_number: Starting ticket number for row-number format.
        uses_row_numbers: Whether dependencies use row numbers.

    Returns:
        List of dependency ticket IDs.
    """
    cell = cell.strip()

    # Handle empty/none values
    if not cell or cell == "-" or cell.lower() in ("none", "n/a"):
        return []

    # Check if cell contains actual ticket IDs
    ticket_ids = re.findall(rf"{ticket_prefix}-\d+", cell)
    if ticket_ids:
        return ticket_ids

    # Otherwise, try to parse as row numbers
    if uses_row_numbers and start_number is not None:
        deps = []
        for part in re.split(r"[,\s]+", cell):
            part = part.strip()
            if part and part.isdigit():
                dep_num = (start_number or 1) + int(part) - 1
                deps.append(f"{ticket_prefix}-{dep_num:04d}")
        return deps

    return []


def _parse_deps_value(value: str, ticket_prefix: str) -> list[str]:
    """Parse a dependencies value from section format.

    Args:
        value: Dependencies value (e.g., "None", "TEST-001, TEST-002").
        ticket_prefix: Ticket ID prefix.

    Returns:
        List of dependency ticket IDs.
    """
    value = value.strip()

    # Handle empty/none values
    if not value or value == "-" or value.lower() in ("none", "n/a"):
        return []

    # Extract all ticket IDs
    return re.findall(rf"{ticket_prefix}-\d+", value)


def _find_start_number(content: str, ticket_prefix: str) -> int:
    """Find the starting ticket number from content.

    Args:
        content: Plan file content.
        ticket_prefix: Ticket ID prefix.

    Returns:
        Starting ticket number, or 1 if not found.
    """
    # Find first ticket ID in content
    match = re.search(rf"{ticket_prefix}-(\d+)", content)
    if match:
        return int(match.group(1))
    return 1


def build_dependency_graph(dependencies: dict[str, list[str]]) -> dict[str, list[str]]:
    """Build a dependency graph from parsed dependencies.

    This function takes the raw dependency mapping and returns the same
    structure (for now). Future versions may add additional graph analysis.

    Args:
        dependencies: Dict mapping ticket IDs to their dependency lists.

    Returns:
        Dict mapping ticket IDs to their dependency lists.
    """
    return dict(dependencies)


def detect_circular_dependencies(dependencies: dict[str, list[str]]) -> list[list[str]]:
    """Detect circular dependencies in the dependency graph.

    Uses depth-first search to find cycles in the dependency graph.

    Args:
        dependencies: Dict mapping ticket IDs to their dependency lists.

    Returns:
        List of cycles found. Each cycle is a list of ticket IDs forming
        the cycle. Empty list if no cycles found.
    """
    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(ticket: str) -> bool:
        """Depth-first search to find cycles."""
        visited.add(ticket)
        rec_stack.add(ticket)
        path.append(ticket)

        for dep in dependencies.get(ticket, []):
            if dep not in visited:
                if dfs(dep):
                    return True
            elif dep in rec_stack:
                # Found a cycle - extract it from path
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                cycles.append(cycle)
                return True

        path.pop()
        rec_stack.remove(ticket)
        return False

    for ticket in dependencies:
        if ticket not in visited:
            dfs(ticket)

    return cycles
