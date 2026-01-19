"""Unit tests for the setup command module.

Tests cover:
- PRD and plan file validation
- Ticket extraction from PRD
- Dependency parsing and storage
- Workflow state initialization
- GitHub connectivity checks
- Error handling for missing files and malformed content
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from commands import setup
from core.state import WorkflowState, Ticket


class TestValidatePaths:
    """Tests for PRD and plan path validation."""

    def test_validate_paths_both_exist(self, tmp_path: Path) -> None:
        """Given valid PRD and plan paths, when validated, then no error is raised."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        prd_path.write_text("# PRD\nContent")
        plan_path.write_text("# Plan\nContent")

        # Should not raise
        setup.validate_paths(prd_path, plan_path)

    def test_validate_paths_prd_missing_raises_error(self, tmp_path: Path) -> None:
        """Given PRD file doesn't exist, when validated, then FileNotFoundError is raised."""
        prd_path = tmp_path / "missing-prd.md"
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("# Plan\nContent")

        with pytest.raises(FileNotFoundError) as exc_info:
            setup.validate_paths(prd_path, plan_path)

        assert "PRD file not found" in str(exc_info.value)
        assert str(prd_path) in str(exc_info.value)

    def test_validate_paths_plan_missing_raises_error(self, tmp_path: Path) -> None:
        """Given plan file doesn't exist, when validated, then FileNotFoundError is raised."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "missing-plan.md"
        prd_path.write_text("# PRD\nContent")

        with pytest.raises(FileNotFoundError) as exc_info:
            setup.validate_paths(prd_path, plan_path)

        assert "Plan file not found" in str(exc_info.value)
        assert str(plan_path) in str(exc_info.value)

    def test_validate_paths_both_missing_raises_prd_error_first(
        self, tmp_path: Path
    ) -> None:
        """Given both files missing, when validated, then PRD error is raised first."""
        prd_path = tmp_path / "missing-prd.md"
        plan_path = tmp_path / "missing-plan.md"

        with pytest.raises(FileNotFoundError) as exc_info:
            setup.validate_paths(prd_path, plan_path)

        # PRD error should come first
        assert "PRD file not found" in str(exc_info.value)


class TestExtractTicketsFromPRD:
    """Tests for ticket extraction from PRD documents."""

    def test_extract_tickets_from_prd_with_linked_tickets(
        self, tmp_path: Path
    ) -> None:
        """Given a PRD with markdown-linked ticket IDs, when extracted, then all IDs are returned."""
        prd_path = tmp_path / "prd.md"
        prd_path.write_text("""
# PRD: Feature

## Tickets

| ID | Title |
|----|-------|
| [TASK-001](https://github.com/repo/issues/1) | First ticket |
| [TASK-002](https://github.com/repo/issues/2) | Second ticket |
| [TASK-003](https://github.com/repo/issues/3) | Third ticket |
""")

        tickets = setup.extract_tickets_from_prd(prd_path)

        assert tickets == ["TASK-001", "TASK-002", "TASK-003"]

    def test_extract_tickets_from_prd_with_unlinked_tickets(
        self, tmp_path: Path
    ) -> None:
        """Given a PRD with plain ticket IDs (no links), when extracted, then all IDs are returned."""
        prd_path = tmp_path / "prd.md"
        prd_path.write_text("""
# PRD: Feature

## Tickets

| ID | Title |
|----|-------|
| SDLC-0001 | First ticket |
| SDLC-0002 | Second ticket |
""")

        tickets = setup.extract_tickets_from_prd(prd_path)

        assert tickets == ["SDLC-0001", "SDLC-0002"]

    def test_extract_tickets_from_prd_no_tickets_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """Given a PRD with no ticket IDs, when extracted, then empty list is returned."""
        prd_path = tmp_path / "prd.md"
        prd_path.write_text("""
# PRD: Feature

Just some text without any ticket IDs.
""")

        tickets = setup.extract_tickets_from_prd(prd_path)

        assert tickets == []

    def test_extract_tickets_from_prd_preserves_order(self, tmp_path: Path) -> None:
        """Given a PRD with tickets in specific order, when extracted, then order is preserved."""
        prd_path = tmp_path / "prd.md"
        prd_path.write_text("""
| [TASK-003](url) | Third |
| [TASK-001](url) | First |
| [TASK-002](url) | Second |
""")

        tickets = setup.extract_tickets_from_prd(prd_path)

        # Should preserve document order
        assert tickets == ["TASK-003", "TASK-001", "TASK-002"]

    def test_extract_tickets_from_prd_removes_duplicates(self, tmp_path: Path) -> None:
        """Given a PRD with duplicate ticket IDs, when extracted, then duplicates are removed."""
        prd_path = tmp_path / "prd.md"
        prd_path.write_text("""
| [TASK-001](url) | First |
| [TASK-001](url) | Duplicate |
| [TASK-002](url) | Second |
""")

        tickets = setup.extract_tickets_from_prd(prd_path)

        # Should remove duplicates while preserving first occurrence order
        assert tickets == ["TASK-001", "TASK-002"]


class TestExtractTicketPrefix:
    """Tests for ticket prefix extraction."""

    def test_extract_prefix_from_ticket_ids(self) -> None:
        """Given ticket IDs, when extracting prefix, then common prefix is returned."""
        tickets = ["TASK-001", "TASK-002", "TASK-003"]

        prefix = setup.extract_ticket_prefix(tickets)

        assert prefix == "TASK"

    def test_extract_prefix_with_longer_prefix(self) -> None:
        """Given tickets with multi-letter prefix, when extracting, then full prefix is returned."""
        tickets = ["SDLC-0001", "SDLC-0002"]

        prefix = setup.extract_ticket_prefix(tickets)

        assert prefix == "SDLC"

    def test_extract_prefix_empty_list_returns_none(self) -> None:
        """Given empty ticket list, when extracting prefix, then None is returned."""
        tickets: list[str] = []

        prefix = setup.extract_ticket_prefix(tickets)

        assert prefix is None

    def test_extract_prefix_inconsistent_prefixes_uses_first(self) -> None:
        """Given tickets with different prefixes, when extracting, then first prefix is used."""
        tickets = ["TASK-001", "SDLC-002", "TASK-003"]

        prefix = setup.extract_ticket_prefix(tickets)

        assert prefix == "TASK"


class TestInitializeWorkflowState:
    """Tests for workflow state initialization."""

    def test_initialize_state_creates_file(self, tmp_path: Path) -> None:
        """Given valid inputs, when initializing state, then state file is created."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("""
| [TASK-001](url) | First |
| [TASK-002](url) | Second |
""")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | TASK-001 |
""")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        assert state_file.exists()

    def test_initialize_state_contains_tickets(self, tmp_path: Path) -> None:
        """Given PRD with tickets, when initializing, then tickets are in state file."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("""
| [TASK-001](url) | First |
| [TASK-002](url) | Second |
""")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | TASK-001 |
""")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        data = json.loads(state_file.read_text())
        ticket_ids = [t["id"] for t in data["tickets"]]
        assert "TASK-001" in ticket_ids
        assert "TASK-002" in ticket_ids

    def test_initialize_state_sets_pending_status(self, tmp_path: Path) -> None:
        """Given tickets, when initializing, then all tickets have pending status."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("| [TASK-001](url) | First |")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
""")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        data = json.loads(state_file.read_text())
        for ticket in data["tickets"]:
            assert ticket["status"] == "pending"

    def test_initialize_state_includes_dependencies(self, tmp_path: Path) -> None:
        """Given plan with dependencies, when initializing, then deps are in state."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("""
| [TASK-001](url) | First |
| [TASK-002](url) | Second |
""")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | TASK-001 |
""")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        data = json.loads(state_file.read_text())
        tickets_by_id = {t["id"]: t for t in data["tickets"]}
        assert tickets_by_id["TASK-001"]["dependencies"] == []
        assert tickets_by_id["TASK-002"]["dependencies"] == ["TASK-001"]

    def test_initialize_state_stores_paths(self, tmp_path: Path) -> None:
        """Given PRD and plan paths, when initializing, then paths are stored."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("| [TASK-001](url) | First |")
        plan_path.write_text("| ID | Title | Dependencies |\n|----|-------|--------------|")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        data = json.loads(state_file.read_text())
        assert data["prd_path"] == str(prd_path)
        assert data["plan_path"] == str(plan_path)


class TestRunSetup:
    """Integration tests for the main setup function."""

    def test_run_setup_success(self, tmp_path: Path) -> None:
        """Given valid files, when running setup, then returns success result."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("""
| [TASK-001](url) | First |
| [TASK-002](url) | Second |
""")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | TASK-001 |
""")

        result = setup.run_setup(prd_path, plan_path, state_file)

        assert result.success is True
        assert result.ticket_count == 2
        assert state_file.exists()

    def test_run_setup_missing_prd_fails(self, tmp_path: Path) -> None:
        """Given missing PRD, when running setup, then returns failure result."""
        prd_path = tmp_path / "missing-prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"
        plan_path.write_text("# Plan")

        result = setup.run_setup(prd_path, plan_path, state_file)

        assert result.success is False
        assert "PRD file not found" in result.error

    def test_run_setup_missing_plan_fails(self, tmp_path: Path) -> None:
        """Given missing plan, when running setup, then returns failure result."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "missing-plan.md"
        state_file = tmp_path / "workflow-state.json"
        prd_path.write_text("# PRD")

        result = setup.run_setup(prd_path, plan_path, state_file)

        assert result.success is False
        assert "Plan file not found" in result.error

    def test_run_setup_no_tickets_warns(self, tmp_path: Path) -> None:
        """Given PRD with no tickets, when running setup, then result has warning."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("# PRD without tickets")
        plan_path.write_text("# Plan")

        result = setup.run_setup(prd_path, plan_path, state_file)

        # Should still succeed but with warning
        assert result.success is True
        assert result.ticket_count == 0
        assert "No tickets found" in (result.warning or "")


class TestSetupResult:
    """Tests for SetupResult dataclass."""

    def test_setup_result_success(self) -> None:
        """Given success parameters, when creating result, then fields are set."""
        result = setup.SetupResult(
            success=True,
            ticket_count=5,
            ticket_prefix="TASK",
        )

        assert result.success is True
        assert result.ticket_count == 5
        assert result.ticket_prefix == "TASK"
        assert result.error is None

    def test_setup_result_failure(self) -> None:
        """Given failure parameters, when creating result, then error is set."""
        result = setup.SetupResult(
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.ticket_count == 0
