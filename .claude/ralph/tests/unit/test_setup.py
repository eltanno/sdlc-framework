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

from commands import setup
from core.state import WorkflowState


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
# PRD: Feature

## Tickets

| ID | Title |
|----|-------|
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
# PRD: Feature

## Tickets

| ID | Title |
|----|-------|
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
## Tickets

| ID | Title |
|----|-------|
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
## Tickets

| ID | Title |
|----|-------|
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
        # v2 format uses ralph.tickets
        ticket_ids = data["ralph"]["tickets"]
        assert "TASK-001" in ticket_ids
        assert "TASK-002" in ticket_ids

    def test_initialize_state_creates_v2_format(self, tmp_path: Path) -> None:
        """Given tickets, when initializing, then state is v2 format."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("## Tickets\n\n| ID | Title |\n|----|-------|\n| [TASK-001](url) | First |")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
""")

        setup.initialize_workflow_state(prd_path, plan_path, state_file)

        data = json.loads(state_file.read_text())
        # v2 format has ralph section, version 2.0, and empty tickets array
        assert data["version"] == "2.0"
        assert "ralph" in data
        assert data["tickets"] == []

    def test_initialize_state_includes_dependencies(self, tmp_path: Path) -> None:
        """Given plan with dependencies, when initializing, then deps are in state."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("""
## Tickets

| ID | Title |
|----|-------|
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
        # v2 format uses ralph.dependencies
        deps = data["ralph"]["dependencies"]
        assert deps.get("TASK-001", []) == []
        assert deps.get("TASK-002", []) == ["TASK-001"]

    def test_initialize_state_stores_paths(self, tmp_path: Path) -> None:
        """Given PRD and plan paths, when initializing, then paths are stored."""
        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        prd_path.write_text("## Tickets\n\n| ID | Title |\n|----|-------|\n| [TASK-001](url) | First |")
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
## Tickets

| ID | Title |
|----|-------|
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


class TestDetectTicketMismatch:
    """Tests for detecting PRD/state ticket mismatch."""

    def test_detect_mismatch_returns_false_when_tickets_match(
        self, tmp_path: Path
    ) -> None:
        """Given PRD and state have same tickets, when detecting mismatch, then returns False."""
        prd_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]
        state_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is False
        assert result.added == []
        assert result.removed == []

    def test_detect_mismatch_returns_true_when_tickets_differ(
        self, tmp_path: Path
    ) -> None:
        """Given PRD has tickets [A,B,C] and state has [A,B,D], when detecting, then mismatch found."""
        prd_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]
        state_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0004"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert "SDLC-0003" in result.added
        assert "SDLC-0004" in result.removed

    def test_detect_mismatch_identifies_added_tickets(self) -> None:
        """Given PRD has more tickets than state, when detecting, then added tickets identified."""
        prd_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]
        state_tickets = ["SDLC-0001", "SDLC-0002"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert result.added == ["SDLC-0003"]
        assert result.removed == []

    def test_detect_mismatch_identifies_removed_tickets(self) -> None:
        """Given PRD has fewer tickets than state, when detecting, then removed tickets identified."""
        prd_tickets = ["SDLC-0001", "SDLC-0002"]
        state_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert result.added == []
        assert result.removed == ["SDLC-0003"]

    def test_detect_mismatch_ignores_order_differences(self) -> None:
        """Given same tickets in different order, when detecting, then no mismatch."""
        prd_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]
        state_tickets = ["SDLC-0003", "SDLC-0001", "SDLC-0002"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is False

    def test_detect_mismatch_handles_empty_prd(self) -> None:
        """Given empty PRD tickets, when detecting, then all state tickets are removed."""
        prd_tickets: list[str] = []
        state_tickets = ["SDLC-0001", "SDLC-0002"]

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert result.added == []
        assert set(result.removed) == {"SDLC-0001", "SDLC-0002"}

    def test_detect_mismatch_handles_empty_state(self) -> None:
        """Given empty state tickets, when detecting, then all PRD tickets are added."""
        prd_tickets = ["SDLC-0001", "SDLC-0002"]
        state_tickets: list[str] = []

        result = setup.detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert set(result.added) == {"SDLC-0001", "SDLC-0002"}
        assert result.removed == []


class TestResetStateFromPRD:
    """Tests for resetting state from PRD while preserving attempt counts."""

    def test_reset_state_from_prd_creates_new_state(self, tmp_path: Path) -> None:
        """Given PRD with tickets, when resetting state, then new state is created."""
        prd_tickets = ["SDLC-0001", "SDLC-0002"]
        dependencies = {"SDLC-0002": ["SDLC-0001"]}
        complexity = {"SDLC-0001": 2, "SDLC-0002": 3}
        old_attempts: dict[str, int] = {}

        new_ralph = setup.reset_state_from_prd(
            prd_tickets=prd_tickets,
            dependencies=dependencies,
            complexity=complexity,
            old_attempts=old_attempts,
            old_blocked={},
            source="github",
        )

        assert new_ralph.tickets == ["SDLC-0001", "SDLC-0002"]
        assert new_ralph.dependencies == {"SDLC-0002": ["SDLC-0001"]}
        assert new_ralph.complexity == {"SDLC-0001": 2, "SDLC-0002": 3}
        assert new_ralph.source == "github"
        # New tickets should have no attempts recorded
        assert new_ralph.attempts == {}

    def test_reset_state_preserves_attempt_counts_for_matching_tickets(
        self, tmp_path: Path
    ) -> None:
        """Given old state has attempts, when resetting, then matching ticket attempts preserved."""
        prd_tickets = ["SDLC-0001", "SDLC-0002", "SDLC-0003"]
        dependencies: dict[str, list[str]] = {}
        complexity: dict[str, int] = {}
        old_attempts = {"SDLC-0001": 2, "SDLC-0002": 1, "SDLC-0004": 3}  # SDLC-0004 not in PRD

        new_ralph = setup.reset_state_from_prd(
            prd_tickets=prd_tickets,
            dependencies=dependencies,
            complexity=complexity,
            old_attempts=old_attempts,
            old_blocked={},
            source="github",
        )

        # Should preserve attempts for tickets that exist in PRD
        assert new_ralph.attempts == {"SDLC-0001": 2, "SDLC-0002": 1}
        # SDLC-0003 has no previous attempts, so not in dict
        # SDLC-0004 not in PRD, so discarded

    def test_reset_state_clears_blocked_for_removed_tickets(
        self, tmp_path: Path
    ) -> None:
        """Given old state has blocked tickets, when resetting, then removed tickets' blocked cleared."""
        prd_tickets = ["SDLC-0001", "SDLC-0002"]
        dependencies: dict[str, list[str]] = {}
        complexity: dict[str, int] = {}
        old_attempts: dict[str, int] = {}
        old_blocked = {
            "SDLC-0001": "Test failures",
            "SDLC-0003": "Lint errors",  # Not in PRD
        }

        new_ralph = setup.reset_state_from_prd(
            prd_tickets=prd_tickets,
            dependencies=dependencies,
            complexity=complexity,
            old_attempts=old_attempts,
            old_blocked=old_blocked,
            source="github",
        )

        # Should preserve blocked only for tickets that exist in PRD
        assert new_ralph.blocked == {"SDLC-0001": "Test failures"}
        # SDLC-0003 blocked should be cleared (not in PRD)

    def test_reset_state_uses_new_dependencies(self, tmp_path: Path) -> None:
        """Given new dependencies from plan, when resetting, then new dependencies used."""
        prd_tickets = ["SDLC-0001", "SDLC-0002"]
        new_dependencies = {"SDLC-0002": ["SDLC-0001"]}
        complexity: dict[str, int] = {}
        old_attempts: dict[str, int] = {}

        new_ralph = setup.reset_state_from_prd(
            prd_tickets=prd_tickets,
            dependencies=new_dependencies,
            complexity=complexity,
            old_attempts=old_attempts,
            old_blocked={},
            source="github",
        )

        assert new_ralph.dependencies == {"SDLC-0002": ["SDLC-0001"]}


class TestSetupWithExistingState:
    """Tests for setup behavior when state file already exists."""

    def test_setup_detects_mismatch_with_existing_state(self, tmp_path: Path) -> None:
        """Given existing state with different tickets, when setup runs, then mismatch detected."""
        from core.state import RalphState, save_workflow_state

        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        # Create PRD with tickets A, B, C
        prd_path.write_text("""
## Tickets

| ID | Title |
|----|-------|
| [SDLC-0001](url) | First |
| [SDLC-0002](url) | Second |
| [SDLC-0003](url) | Third |
""")
        plan_path.write_text("""
| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-0001 | First | - |
| SDLC-0002 | Second | SDLC-0001 |
| SDLC-0003 | Third | - |
""")

        # Create existing state with tickets A, B, D
        existing_ralph = RalphState(
            tickets=["SDLC-0001", "SDLC-0002", "SDLC-0004"],
            dependencies={"SDLC-0002": ["SDLC-0001"]},
            attempts={"SDLC-0002": 2},
            blocked={},
            source="github",
        )
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_path,
            plan_path=plan_path,
            tickets=[],
            ralph=existing_ralph,
        )
        save_workflow_state(existing_state, state_file)

        # Run setup - should detect mismatch
        result = setup.run_setup(prd_path, plan_path, state_file, interactive=False)

        assert result.success is True
        assert result.mismatch_detected is True
        assert "SDLC-0003" in (result.tickets_added or [])
        assert "SDLC-0004" in (result.tickets_removed or [])

    def test_setup_noninteractive_warns_and_continues(
        self, tmp_path: Path, capsys
    ) -> None:
        """Given mismatch in non-interactive mode, when setup runs, then warns and uses PRD."""
        from core.state import RalphState, save_workflow_state, load_workflow_state

        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        # Create PRD with new tickets
        prd_path.write_text("""
## Tickets

| ID | Title |
|----|-------|
| [SDLC-0001](url) | First |
| [SDLC-0002](url) | Second |
""")
        plan_path.write_text("| ID | Title | Dependencies |\n|----|-------|--------------|")

        # Create existing state with different tickets
        existing_ralph = RalphState(
            tickets=["SDLC-0001", "SDLC-0003"],  # 0003 not in PRD
            dependencies={},
            attempts={"SDLC-0001": 1},
            blocked={},
            source="github",
        )
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_path,
            plan_path=plan_path,
            tickets=[],
            ralph=existing_ralph,
        )
        save_workflow_state(existing_state, state_file)

        # Run setup non-interactively
        result = setup.run_setup(prd_path, plan_path, state_file, interactive=False)

        # Should succeed with warning
        assert result.success is True
        assert result.warning is not None
        assert "mismatch" in result.warning.lower()

        # State should now match PRD
        new_state = load_workflow_state(state_file)
        assert new_state.ralph is not None
        assert set(new_state.ralph.tickets) == {"SDLC-0001", "SDLC-0002"}

        # Attempt count for SDLC-0001 should be preserved
        assert new_state.ralph.attempts.get("SDLC-0001") == 1

    def test_setup_interactive_prompts_user(
        self, tmp_path: Path, mocker
    ) -> None:
        """Given mismatch in interactive mode, when setup runs, then prompts user."""
        from core.state import RalphState, save_workflow_state

        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        # Create PRD
        prd_path.write_text("## Tickets\n\n| ID | Title |\n|----|-------|\n| [SDLC-0001](url) | First |")
        plan_path.write_text("| ID | Title | Dependencies |\n|----|-------|--------------|")

        # Create existing state with different tickets
        existing_ralph = RalphState(
            tickets=["SDLC-0002"],
            dependencies={},
            attempts={},
            blocked={},
            source="github",
        )
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_path,
            plan_path=plan_path,
            tickets=[],
            ralph=existing_ralph,
        )
        save_workflow_state(existing_state, state_file)

        # Mock user input to confirm reset
        mock_input = mocker.patch("builtins.input", return_value="y")

        result = setup.run_setup(prd_path, plan_path, state_file, interactive=True)

        # Should have prompted user with reset confirmation
        assert mock_input.called
        call_args = mock_input.call_args[0][0]
        assert "Reset" in call_args and "PRD" in call_args
        assert result.success is True
        assert result.mismatch_detected is True

    def test_setup_interactive_user_rejects_reset(
        self, tmp_path: Path, mocker
    ) -> None:
        """Given mismatch and user rejects reset, when setup runs, then aborts."""
        from core.state import RalphState, save_workflow_state

        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        # Create PRD
        prd_path.write_text("## Tickets\n\n| ID | Title |\n|----|-------|\n| [SDLC-0001](url) | First |")
        plan_path.write_text("| ID | Title | Dependencies |\n|----|-------|--------------|")

        # Create existing state with different tickets
        existing_ralph = RalphState(
            tickets=["SDLC-0002"],
            dependencies={},
            attempts={},
            blocked={},
            source="github",
        )
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_path,
            plan_path=plan_path,
            tickets=[],
            ralph=existing_ralph,
        )
        save_workflow_state(existing_state, state_file)

        # Mock user input to reject reset
        mock_input = mocker.patch("builtins.input", return_value="n")

        result = setup.run_setup(prd_path, plan_path, state_file, interactive=True)

        # Should fail/abort due to user rejection
        assert result.success is False
        assert "abort" in (result.error or "").lower()

    def test_setup_no_mismatch_proceeds_normally(self, tmp_path: Path) -> None:
        """Given existing state matches PRD, when setup runs, then proceeds without reset."""
        from core.state import RalphState, save_workflow_state, load_workflow_state

        prd_path = tmp_path / "prd.md"
        plan_path = tmp_path / "plan.md"
        state_file = tmp_path / "workflow-state.json"

        # Create PRD
        prd_path.write_text("## Tickets\n\n| ID | Title |\n|----|-------|\n| [SDLC-0001](url) | First |")
        plan_path.write_text("| ID | Title | Dependencies |\n|----|-------|--------------|")

        # Create existing state with SAME tickets
        existing_ralph = RalphState(
            tickets=["SDLC-0001"],
            dependencies={},
            attempts={"SDLC-0001": 2},  # Existing attempt count
            blocked={},
            source="github",
        )
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_path,
            plan_path=plan_path,
            tickets=[],
            ralph=existing_ralph,
        )
        save_workflow_state(existing_state, state_file)

        result = setup.run_setup(prd_path, plan_path, state_file, interactive=False)

        assert result.success is True
        assert result.mismatch_detected is False

        # Attempt count should be preserved
        new_state = load_workflow_state(state_file)
        assert new_state.ralph is not None
        assert new_state.ralph.attempts.get("SDLC-0001") == 2
