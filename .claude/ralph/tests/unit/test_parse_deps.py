"""Unit tests for parse_deps module.

Tests dependency parsing from plan documents in both table and section formats.
Covers normal cases, edge cases, and circular dependency detection.
"""

from pathlib import Path

import pytest

from commands.parse_deps import (
    parse_dependencies,
    detect_circular_dependencies,
    DependencyGraph,
)


class TestParseTableFormat:
    """Tests for table format parsing."""

    def test_parse_simple_table_with_explicit_ids(self, tmp_path: Path) -> None:
        """Test parsing a table with explicit ticket IDs in the ID column."""
        plan_content = """# Test Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| TASK-001 | First task | Do this first | P1 | 2 | 1 | - |
| TASK-002 | Second task | Depends on first | P1 | 2 | 1 | TASK-001 |
| TASK-003 | Third task | Depends on both | P1 | 3 | 2 | TASK-001, TASK-002 |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == ["TASK-001"]
        assert result["TASK-003"] == ["TASK-001", "TASK-002"]

    def test_parse_table_with_row_numbers(self, tmp_path: Path) -> None:
        """Test parsing a table with row numbers that map to ticket IDs."""
        plan_content = """# Test Plan

## Tickets

| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | First task | Do this first | P1 | 2 | 1 | - |
| 2 | Second task | Depends on first | P1 | 2 | 1 | 1 |
| 3 | Third task | Depends on both | P1 | 3 | 2 | 1, 2 |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        # Need to provide ticket prefix for row number mapping
        result = parse_dependencies(plan_file, ticket_prefix="TASK", start_num=1)

        assert result["TASK-0001"] == []
        assert result["TASK-0002"] == ["TASK-0001"]
        assert result["TASK-0003"] == ["TASK-0001", "TASK-0002"]

    def test_parse_table_with_no_dependencies(self, tmp_path: Path) -> None:
        """Test parsing a table where no tickets have dependencies."""
        plan_content = """# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First task | - |
| TASK-002 | Second task | - |
| TASK-003 | Third task | None |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == []
        assert result["TASK-003"] == []



class TestParseSectionFormat:
    """Tests for section format parsing."""

    def test_parse_section_format(self, tmp_path: Path) -> None:
        """Test parsing section-based format with ### headers."""
        plan_content = """# Test Plan

### TASK-001: First Task

Description of the first task.

- **Dependencies:** None

### TASK-002: Second Task

Description of the second task.

- **Dependencies:** TASK-001

### TASK-003: Third Task

Description of the third task.

- **Dependencies:** TASK-001, TASK-002
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == ["TASK-001"]
        assert result["TASK-003"] == ["TASK-001", "TASK-002"]

    def test_parse_section_format_with_colon_after_dependencies(
        self, tmp_path: Path
    ) -> None:
        """Test parsing when Dependencies line has extra colon."""
        plan_content = """# Test Plan

### TASK-001: First Task

- **Dependencies:**: None

### TASK-002: Second Task

- **Dependencies:**: TASK-001
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == ["TASK-001"]



class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""

    def test_detect_simple_circular_dependency(self) -> None:
        """Test detecting A -> B -> A cycle."""
        deps = {
            "TASK-001": ["TASK-002"],
            "TASK-002": ["TASK-001"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 1
        cycle = cycles[0]
        assert cycle[0] == cycle[-1]  # Cycle starts and ends at same node
        assert set(cycle[:-1]) == {"TASK-001", "TASK-002"}

    def test_detect_longer_circular_dependency(self) -> None:
        """Test detecting A -> B -> C -> A cycle."""
        deps = {
            "TASK-001": ["TASK-002"],
            "TASK-002": ["TASK-003"],
            "TASK-003": ["TASK-001"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 1
        cycle = cycles[0]
        assert cycle[0] == cycle[-1]  # Cycle starts and ends at same node
        assert set(cycle[:-1]) == {"TASK-001", "TASK-002", "TASK-003"}

    def test_no_circular_dependencies(self) -> None:
        """Test that linear dependencies return no cycles."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-002"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 0

    def test_self_referential_dependency(self) -> None:
        """Test detecting a ticket that depends on itself."""
        deps = {
            "TASK-001": ["TASK-001"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 1
        cycle = cycles[0]
        assert cycle[0] == cycle[-1]  # Cycle starts and ends at same node
        assert cycle == ["TASK-001", "TASK-001"]


class TestDependencyGraph:
    """Tests for the DependencyGraph dataclass."""

    def test_get_dependents(self) -> None:
        """Test finding which tickets depend on a given ticket."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-001"],
            "TASK-004": ["TASK-002"],
        }
        graph = DependencyGraph(dependencies=deps, ticket_prefix="TASK")

        dependents = graph.get_dependents("TASK-001")

        assert "TASK-002" in dependents
        assert "TASK-003" in dependents
        assert "TASK-004" not in dependents

    def test_get_dependencies(self) -> None:
        """Test getting dependencies for a ticket."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-001", "TASK-002"],
        }
        graph = DependencyGraph(dependencies=deps, ticket_prefix="TASK")

        assert graph.get_dependencies("TASK-001") == []
        assert graph.get_dependencies("TASK-002") == ["TASK-001"]
        assert "TASK-001" in graph.get_dependencies("TASK-003")
        assert "TASK-002" in graph.get_dependencies("TASK-003")

    def test_get_dependencies_unknown_ticket(self) -> None:
        """Test getting dependencies for a non-existent ticket."""
        deps = {"TASK-001": []}
        graph = DependencyGraph(dependencies=deps, ticket_prefix="TASK")

        assert graph.get_dependencies("TASK-999") == []


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test error when plan file doesn't exist."""
        non_existent = tmp_path / "non_existent.md"

        with pytest.raises(FileNotFoundError):
            parse_dependencies(non_existent)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty plan file."""
        plan_file = tmp_path / "empty.md"
        plan_file.write_text("")

        result = parse_dependencies(plan_file)

        assert result == {}

    def test_no_tickets_section(self, tmp_path: Path) -> None:
        """Test parsing a plan with no tickets section."""
        plan_content = """# Test Plan

## Summary
This plan has no tickets table.

## Goals
- Some goal
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result == {}

    def test_malformed_table_row(self, tmp_path: Path) -> None:
        """Test parsing with malformed table rows (should skip them)."""
        plan_content = """# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | Valid task | - |
| This is not a valid row
| TASK-002 | Another valid task | TASK-001 |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        # Should parse valid rows and skip invalid
        assert "TASK-001" in result
        assert "TASK-002" in result


class TestRealWorldPlanFormat:
    """Tests with realistic plan formats matching the shell script behavior."""

    def test_parse_plan_matching_shell_script_format(self, tmp_path: Path) -> None:
        """Test parsing a plan that matches the actual shell script test format."""
        # This matches the format in the real PRD/plan documents
        plan_content = """# Implementation Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| SDLC-0013 | Package structure setup | Create directory structure | P1 | 2 | 1 | - |
| SDLC-0014 | Core: config.py | Port config-helpers.sh | P1 | 3 | 1 | SDLC-0013 |
| SDLC-0015 | Core: state.py | Port state-utils.sh | P1 | 4 | 1 | SDLC-0014 |
| SDLC-0016 | Core: github.py | Create gh CLI wrapper | P1 | 3 | 1 | SDLC-0014 |
| SDLC-0017 | Core: git.py | Create git CLI wrapper | P1 | 3 | 1 | SDLC-0014 |
| SDLC-0018 | Core unit tests | Unit tests for all core | P1 | 3 | 1 | SDLC-0014, SDLC-0015, SDLC-0016, SDLC-0017 |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file)

        assert result["SDLC-0013"] == []
        assert result["SDLC-0014"] == ["SDLC-0013"]
        assert result["SDLC-0015"] == ["SDLC-0014"]
        assert result["SDLC-0016"] == ["SDLC-0014"]
        assert result["SDLC-0017"] == ["SDLC-0014"]
        assert "SDLC-0014" in result["SDLC-0018"]
        assert "SDLC-0015" in result["SDLC-0018"]
        assert "SDLC-0016" in result["SDLC-0018"]
        assert "SDLC-0017" in result["SDLC-0018"]
