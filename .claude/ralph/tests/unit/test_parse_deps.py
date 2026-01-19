"""Unit tests for parse_deps module.

Tests cover:
- Table format parsing (markdown tables with row numbers and Dependencies column)
- Section format parsing (### PREFIX-XXX: headers with Dependencies lines)
- Circular dependency detection
- Edge cases (empty plans, missing dependencies, malformed input)
"""

from pathlib import Path

import pytest

from commands.parse_deps import (
    parse_dependencies,
    build_dependency_graph,
    detect_circular_dependencies,
    ParseError,
)


class TestParseDependenciesTableFormat:
    """Tests for parsing dependencies from table format plans."""

    def test_parse_table_format_no_dependencies(self, tmp_path: Path) -> None:
        """Given a table with all '-' dependencies, when parsed, then empty lists returned."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| SDLC-0001 | First task | Description | P1 | 2 | 1 | - |
| SDLC-0002 | Second task | Description | P1 | 2 | 1 | - |
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "SDLC")

        assert result == {
            "SDLC-0001": [],
            "SDLC-0002": [],
        }

    def test_parse_table_format_single_dependency(self, tmp_path: Path) -> None:
        """Given a table with single dependencies, when parsed, then correct lists returned."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| SDLC-0001 | First task | Description | P1 | 2 | 1 | - |
| SDLC-0002 | Second task | Description | P1 | 2 | 1 | SDLC-0001 |
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "SDLC")

        assert result == {
            "SDLC-0001": [],
            "SDLC-0002": ["SDLC-0001"],
        }

    def test_parse_table_format_multiple_dependencies(self, tmp_path: Path) -> None:
        """Given a table with multiple dependencies, when parsed, then all deps returned."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| SDLC-0001 | First task | Description | P1 | 2 | 1 | - |
| SDLC-0002 | Second task | Description | P1 | 2 | 1 | SDLC-0001 |
| SDLC-0003 | Third task | Description | P1 | 2 | 1 | SDLC-0001, SDLC-0002 |
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "SDLC")

        assert result == {
            "SDLC-0001": [],
            "SDLC-0002": ["SDLC-0001"],
            "SDLC-0003": ["SDLC-0001", "SDLC-0002"],
        }

    def test_parse_table_format_with_row_numbers(self, tmp_path: Path) -> None:
        """Given a table using row numbers for dependencies, when parsed, then converted to IDs."""
        plan_content = """\
# Test Plan

## Tickets

| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | First task | Description | P1 | 2 | 1 | - |
| 2 | Second task | Description | P1 | 2 | 1 | 1 |
| 3 | Third task | Description | P1 | 2 | 1 | 1, 2 |
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        # When using row numbers, need to provide start number
        result = parse_dependencies(plan_file, "TASK", start_number=100)

        assert result == {
            "TASK-0100": [],
            "TASK-0101": ["TASK-0100"],
            "TASK-0102": ["TASK-0100", "TASK-0101"],
        }

    def test_parse_table_format_different_prefix(self, tmp_path: Path) -> None:
        """Given a table with different ticket prefix, when parsed, then correct IDs used."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| AUCT-0161 | Task | - |
| AUCT-0162 | Task | AUCT-0161 |
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "AUCT")

        assert result == {
            "AUCT-0161": [],
            "AUCT-0162": ["AUCT-0161"],
        }


class TestParseDependenciesSectionFormat:
    """Tests for parsing dependencies from section format plans."""

    def test_parse_section_format_no_dependencies(self, tmp_path: Path) -> None:
        """Given sections with None dependencies, when parsed, then empty lists returned."""
        plan_content = """\
# Test Plan

## Tickets

### TEST-001: First Task

Description of first task.

- **Dependencies:** None

### TEST-002: Second Task

Description of second task.

- **Dependencies:** None
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result == {
            "TEST-001": [],
            "TEST-002": [],
        }

    def test_parse_section_format_single_dependency(self, tmp_path: Path) -> None:
        """Given sections with single dependencies, when parsed, then correct lists returned."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** None

### TEST-002: Second Task

- **Dependencies:** TEST-001
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result == {
            "TEST-001": [],
            "TEST-002": ["TEST-001"],
        }

    def test_parse_section_format_multiple_dependencies(self, tmp_path: Path) -> None:
        """Given sections with multiple dependencies, when parsed, then all deps returned."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** None

### TEST-002: Second Task

- **Dependencies:** TEST-001

### TEST-003: Third Task

- **Dependencies:** TEST-001, TEST-002
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result == {
            "TEST-001": [],
            "TEST-002": ["TEST-001"],
            "TEST-003": ["TEST-001", "TEST-002"],
        }

    def test_parse_section_format_dash_for_none(self, tmp_path: Path) -> None:
        """Given sections with '-' for no dependencies, when parsed, then empty lists returned."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** -

### TEST-002: Second Task

- **Dependencies:** TEST-001
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result == {
            "TEST-001": [],
            "TEST-002": ["TEST-001"],
        }

    def test_parse_section_format_colon_variation(self, tmp_path: Path) -> None:
        """Given sections with 'Dependencies:' (with colon), when parsed, then works."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** None

### TEST-002: Second Task

- **Dependencies:** TEST-001
"""
        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert "TEST-001" in result
        assert "TEST-002" in result


class TestBuildDependencyGraph:
    """Tests for building dependency graphs from parsed dependencies."""

    def test_build_graph_empty(self) -> None:
        """Given empty dependencies, when graph built, then empty dict returned."""
        deps: dict[str, list[str]] = {}
        graph = build_dependency_graph(deps)
        assert graph == {}

    def test_build_graph_no_deps(self) -> None:
        """Given tickets with no dependencies, when graph built, then all have empty lists."""
        deps = {
            "TASK-001": [],
            "TASK-002": [],
        }
        graph = build_dependency_graph(deps)
        assert graph == {
            "TASK-001": [],
            "TASK-002": [],
        }

    def test_build_graph_linear_deps(self) -> None:
        """Given linear dependencies, when graph built, then correct structure."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-002"],
        }
        graph = build_dependency_graph(deps)

        # Graph should show what each ticket depends on
        assert graph["TASK-001"] == []
        assert graph["TASK-002"] == ["TASK-001"]
        assert graph["TASK-003"] == ["TASK-002"]

    def test_build_graph_complex_deps(self) -> None:
        """Given complex dependencies, when graph built, then all dependencies captured."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-001"],
            "TASK-004": ["TASK-002", "TASK-003"],
        }
        graph = build_dependency_graph(deps)

        assert set(graph["TASK-004"]) == {"TASK-002", "TASK-003"}


class TestDetectCircularDependencies:
    """Tests for circular dependency detection."""

    def test_detect_no_circular_deps(self) -> None:
        """Given valid DAG, when checked, then no cycles detected."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-002"],
        }
        cycles = detect_circular_dependencies(deps)
        assert cycles == []

    def test_detect_simple_circular_dep(self) -> None:
        """Given simple circular dependency (A->B->A), when checked, then cycle detected."""
        deps = {
            "TASK-001": ["TASK-002"],
            "TASK-002": ["TASK-001"],
        }
        cycles = detect_circular_dependencies(deps)
        assert len(cycles) > 0
        # Both tickets should be in the cycle
        cycle_tickets = set()
        for cycle in cycles:
            cycle_tickets.update(cycle)
        assert "TASK-001" in cycle_tickets
        assert "TASK-002" in cycle_tickets

    def test_detect_self_reference(self) -> None:
        """Given self-referencing dependency, when checked, then cycle detected."""
        deps = {
            "TASK-001": ["TASK-001"],
        }
        cycles = detect_circular_dependencies(deps)
        assert len(cycles) > 0
        assert "TASK-001" in cycles[0]

    def test_detect_complex_circular_dep(self) -> None:
        """Given complex circular dependency (A->B->C->A), when checked, then cycle detected."""
        deps = {
            "TASK-001": ["TASK-003"],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-002"],
        }
        cycles = detect_circular_dependencies(deps)
        assert len(cycles) > 0

    def test_detect_multiple_cycles(self) -> None:
        """Given multiple independent cycles, when checked, then all cycles detected."""
        deps = {
            "TASK-001": ["TASK-002"],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-004"],
            "TASK-004": ["TASK-003"],
        }
        cycles = detect_circular_dependencies(deps)
        # Should detect both cycles
        assert len(cycles) >= 2


class TestParseErrorHandling:
    """Tests for error handling in parsing."""

    def test_parse_file_not_found(self, tmp_path: Path) -> None:
        """Given non-existent file, when parsed, then ParseError raised."""
        non_existent = tmp_path / "does-not-exist.md"

        with pytest.raises(ParseError) as exc_info:
            parse_dependencies(non_existent, "TEST")

        assert "not found" in str(exc_info.value).lower()

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Given empty file, when parsed, then empty dict returned."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        result = parse_dependencies(empty_file, "TEST")

        assert result == {}

    def test_parse_no_tickets_section(self, tmp_path: Path) -> None:
        """Given plan without tickets section, when parsed, then empty dict returned."""
        plan_content = """\
# Test Plan

## Summary

This is just a summary with no tickets.
"""
        plan_file = tmp_path / "no-tickets.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result == {}

    def test_parse_malformed_table(self, tmp_path: Path) -> None:
        """Given malformed table, when parsed, then handles gracefully."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Dependencies
|----|-------|
| SDLC-0001 | First | -
"""
        plan_file = tmp_path / "malformed.md"
        plan_file.write_text(plan_content)

        # Should not crash, may return empty or partial results
        result = parse_dependencies(plan_file, "SDLC")
        # At minimum, should not raise unhandled exception
        assert isinstance(result, dict)


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_whitespace_in_dependencies(self, tmp_path: Path) -> None:
        """Given dependencies with extra whitespace, when parsed, then handled correctly."""
        plan_content = """\
# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-0001 | First | - |
| SDLC-0002 | Second |   SDLC-0001   |
| SDLC-0003 | Third | SDLC-0001 ,  SDLC-0002 |
"""
        plan_file = tmp_path / "whitespace.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "SDLC")

        assert result["SDLC-0002"] == ["SDLC-0001"]
        assert set(result["SDLC-0003"]) == {"SDLC-0001", "SDLC-0002"}

    def test_mixed_case_none(self, tmp_path: Path) -> None:
        """Given 'NONE' or 'none' for dependencies, when parsed, then treated as empty."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** NONE

### TEST-002: Second Task

- **Dependencies:** none
"""
        plan_file = tmp_path / "mixed-case.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TEST")

        assert result["TEST-001"] == []
        assert result["TEST-002"] == []

    def test_duplicate_ticket_ids(self, tmp_path: Path) -> None:
        """Given duplicate ticket IDs, when parsed, then last one wins or error raised."""
        plan_content = """\
# Test Plan

### TEST-001: First Task

- **Dependencies:** None

### TEST-001: Duplicate Task

- **Dependencies:** TEST-002
"""
        plan_file = tmp_path / "duplicate.md"
        plan_file.write_text(plan_content)

        # Should either take last definition or raise error
        result = parse_dependencies(plan_file, "TEST")
        assert "TEST-001" in result

    def test_dependency_on_unknown_ticket(self, tmp_path: Path) -> None:
        """Given dependency on non-existent ticket, when parsed, then included anyway."""
        plan_content = """\
# Test Plan

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-0001 | First | SDLC-9999 |
"""
        plan_file = tmp_path / "unknown-dep.md"
        plan_file.write_text(plan_content)

        # Unknown dependencies are still recorded (validation happens elsewhere)
        result = parse_dependencies(plan_file, "SDLC")
        assert result["SDLC-0001"] == ["SDLC-9999"]

    def test_large_ticket_numbers(self, tmp_path: Path) -> None:
        """Given large ticket numbers, when parsed, then handled correctly."""
        plan_content = """\
# Test Plan

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-9999 | First | - |
| SDLC-10000 | Second | SDLC-9999 |
"""
        plan_file = tmp_path / "large-numbers.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "SDLC")

        assert "SDLC-9999" in result
        assert "SDLC-10000" in result
        assert result["SDLC-10000"] == ["SDLC-9999"]

    def test_row_numbers_without_start_number(self, tmp_path: Path) -> None:
        """Given row numbers and ticket IDs in content, when parsed, then start number inferred."""
        plan_content = """\
# Test Plan

This plan references TASK-0050 as the first ticket.

| # | Title | Dependencies |
|---|-------|--------------|
| 1 | First task | - |
| 2 | Second task | 1 |
"""
        plan_file = tmp_path / "infer-start.md"
        plan_file.write_text(plan_content)

        # Should infer start_number=50 from "TASK-0050" in content
        result = parse_dependencies(plan_file, "TASK")

        assert "TASK-0050" in result
        assert "TASK-0051" in result
        assert result["TASK-0051"] == ["TASK-0050"]

    def test_row_numbers_with_non_numeric_rows(self, tmp_path: Path) -> None:
        """Given table with non-numeric row values, when parsed, then skips invalid rows."""
        plan_content = """\
# Test Plan

| # | Title | Dependencies |
|---|-------|--------------|
| 1 | First task | - |
| abc | Invalid row | - |
| 2 | Second task | 1 |
"""
        plan_file = tmp_path / "invalid-row.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TASK", start_number=100)

        # Should have 2 valid tickets (1 and 2), skipping "abc"
        assert len(result) == 2
        assert "TASK-0100" in result
        assert "TASK-0101" in result

    def test_table_with_missing_id_column(self, tmp_path: Path) -> None:
        """Given table without recognizable ID column, when parsed, then empty result."""
        plan_content = """\
# Test Plan

| Title | Description | Dependencies |
|-------|-------------|--------------|
| First | Desc | - |
"""
        plan_file = tmp_path / "no-id.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TASK")

        # No ID column, so nothing can be parsed
        assert result == {}

    def test_table_with_insufficient_columns(self, tmp_path: Path) -> None:
        """Given row with fewer columns than expected, when parsed, then row skipped."""
        plan_content = """\
# Test Plan

| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 |
"""
        plan_file = tmp_path / "short-row.md"
        plan_file.write_text(plan_content)

        result = parse_dependencies(plan_file, "TASK")

        # Second row should be skipped due to insufficient columns
        assert len(result) == 1
        assert "TASK-001" in result
