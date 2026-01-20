"""Integration tests for get_next ticket selection flow.

This module tests the ticket selection logic across multiple scenarios:
- Empty queue handling
- Dependency satisfaction logic
- Blocked ticket handling
- All tickets complete scenarios

These tests use temporary state files to simulate real workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
    load_workflow_state,
    save_workflow_state,
)
from commands.get_next import get_next_ticket, GetNextResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create an empty workflow with no tickets.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    ralph = RalphState(
        tickets=[],
        dependencies={},
        attempts={},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=[],
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


@pytest.fixture
def simple_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a simple workflow with 3 independent tickets.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(id="TASK-001", title="First task", status="pending", dependencies=[]),
        Ticket(id="TASK-002", title="Second task", status="pending", dependencies=[]),
        Ticket(id="TASK-003", title="Third task", status="pending", dependencies=[]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002", "TASK-003"],
        dependencies={},
        attempts={},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


@pytest.fixture
def dependency_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a workflow with dependencies.

    Dependency graph:
    - TASK-001: no dependencies
    - TASK-002: depends on TASK-001
    - TASK-003: depends on TASK-001, TASK-002

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(id="TASK-001", title="First task", status="pending", dependencies=[]),
        Ticket(id="TASK-002", title="Second task", status="pending", dependencies=["TASK-001"]),
        Ticket(id="TASK-003", title="Third task", status="pending", dependencies=["TASK-001", "TASK-002"]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002", "TASK-003"],
        dependencies={"TASK-002": ["TASK-001"], "TASK-003": ["TASK-001", "TASK-002"]},
        attempts={},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


@pytest.fixture
def mixed_status_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a workflow with mixed ticket statuses.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(id="TASK-001", title="Completed task", status="completed", dependencies=[]),
        Ticket(id="TASK-002", title="Blocked task", status="blocked", dependencies=[], block_reason="Test block"),
        Ticket(id="TASK-003", title="Pending task", status="pending", dependencies=[]),
        Ticket(id="TASK-004", title="In progress task", status="in_progress", dependencies=[]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002", "TASK-003", "TASK-004"],
        dependencies={},
        attempts={},
        blocked={"TASK-002": "Test block"},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,
        completed_count=1,
        blocked_count=1,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


# ============================================================================
# Test Cases: Empty Queue
# ============================================================================


class TestEmptyQueue:
    """Tests for empty workflow handling."""

    def test_empty_workflow_returns_complete_status(self, empty_workflow: tuple[Path, WorkflowState]):
        """Given no tickets exist, when getting next ticket, then status is complete."""
        state_file, state = empty_workflow

        result = get_next_ticket(state)

        assert result.ticket is None
        assert result.status == "complete"
        assert result.message == "No tickets in workflow"
        assert not result.has_more
        assert result.total == 0

    def test_empty_workflow_has_zero_counts(self, empty_workflow: tuple[Path, WorkflowState]):
        """Given no tickets exist, when getting next ticket, then all counts are zero."""
        state_file, state = empty_workflow

        result = get_next_ticket(state)

        assert result.pending == 0
        assert result.completed == 0
        assert result.blocked == 0
        assert result.in_progress == 0
        assert result.skipped_for_deps == 0


# ============================================================================
# Test Cases: Dependencies Satisfied
# ============================================================================


class TestDependenciesSatisfied:
    """Tests for ticket selection with satisfied dependencies."""

    def test_first_ticket_selected_from_independent_tickets(
        self, simple_workflow: tuple[Path, WorkflowState]
    ):
        """Given multiple independent pending tickets, when getting next ticket,
        then the first by order is returned."""
        state_file, state = simple_workflow

        result = get_next_ticket(state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.status == "ready"
        assert result.has_more

    def test_dependent_ticket_available_after_dependency_completed(
        self, dependency_workflow: tuple[Path, WorkflowState]
    ):
        """Given a ticket depends on completed tickets, when getting next ticket,
        then the dependent ticket becomes available."""
        state_file, state = dependency_workflow

        # Complete TASK-001
        state.tickets[0].status = "completed"
        state.completed_count = 1

        result = get_next_ticket(state)

        # TASK-002 should now be available (its only dependency is complete)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert result.status == "ready"

    def test_third_level_ticket_available_after_all_deps_completed(
        self, dependency_workflow: tuple[Path, WorkflowState]
    ):
        """Given a ticket depends on multiple completed tickets, when getting next,
        then the ticket becomes available after all dependencies are complete."""
        state_file, state = dependency_workflow

        # Complete TASK-001 and TASK-002
        state.tickets[0].status = "completed"
        state.tickets[1].status = "completed"
        state.completed_count = 2

        result = get_next_ticket(state)

        # TASK-003 should now be available (both dependencies complete)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-003"
        assert result.status == "ready"


# ============================================================================
# Test Cases: Dependencies Blocked
# ============================================================================


class TestDependenciesBlocked:
    """Tests for ticket selection with blocked dependencies."""

    def test_ticket_skipped_when_dependency_not_complete(
        self, dependency_workflow: tuple[Path, WorkflowState]
    ):
        """Given a ticket depends on incomplete tickets, when getting next ticket,
        then that ticket is skipped and first eligible ticket is returned."""
        state_file, state = dependency_workflow

        result = get_next_ticket(state)

        # Only TASK-001 is eligible (others have unmet dependencies)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        # TASK-002 and TASK-003 are skipped due to dependencies
        assert result.skipped_for_deps == 2

    def test_no_ticket_when_all_waiting_on_dependencies(
        self, dependency_workflow: tuple[Path, WorkflowState]
    ):
        """Given all pending tickets have unmet dependencies, when getting next ticket,
        then status is waiting_on_dependencies."""
        state_file, state = dependency_workflow

        # Block TASK-001 instead of completing it
        state.tickets[0].status = "blocked"
        state.blocked_count = 1

        result = get_next_ticket(state)

        # TASK-002 and TASK-003 are waiting on TASK-001 which is blocked
        assert result.ticket is None
        assert result.status == "waiting_on_dependencies"
        assert "waiting on dependencies" in result.message.lower()
        assert result.skipped_for_deps == 2


# ============================================================================
# Test Cases: All Tickets Complete
# ============================================================================


class TestAllComplete:
    """Tests for all tickets complete scenario."""

    def test_complete_status_when_all_tickets_done(
        self, simple_workflow: tuple[Path, WorkflowState]
    ):
        """Given all tickets are complete, when getting next ticket,
        then status is complete with no more tickets."""
        state_file, state = simple_workflow

        # Mark all tickets as completed
        for ticket in state.tickets:
            ticket.status = "completed"
        state.completed_count = 3

        result = get_next_ticket(state)

        assert result.ticket is None
        assert result.status == "complete"
        assert result.message == "All tickets are complete"
        assert not result.has_more
        assert result.completed == 3
        assert result.pending == 0


# ============================================================================
# Test Cases: Blocked Tickets
# ============================================================================


class TestBlockedTickets:
    """Tests for blocked ticket handling."""

    def test_blocked_tickets_excluded_from_selection(
        self, mixed_status_workflow: tuple[Path, WorkflowState]
    ):
        """Given blocked tickets exist, when getting next ticket,
        then blocked tickets are excluded from selection."""
        state_file, state = mixed_status_workflow

        result = get_next_ticket(state)

        # In-progress ticket should be resumed first
        assert result.ticket is not None
        assert result.ticket.id == "TASK-004"
        # TASK-002 is blocked, so it's not selected
        assert result.blocked == 1

    def test_all_blocked_status_when_no_pending(self, tmp_path: Path):
        """Given all non-completed tickets are blocked, when getting next ticket,
        then status is all_blocked."""
        tickets = [
            Ticket(id="TASK-001", title="Blocked 1", status="blocked", dependencies=[]),
            Ticket(id="TASK-002", title="Blocked 2", status="blocked", dependencies=[]),
        ]
        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            blocked_count=2,
        )

        result = get_next_ticket(state)

        assert result.ticket is None
        assert result.status == "all_blocked"
        assert result.message == "All tickets are blocked"
        assert not result.has_more


# ============================================================================
# Test Cases: In-Progress Resumption
# ============================================================================


class TestInProgressResumption:
    """Tests for resuming in-progress tickets."""

    def test_in_progress_ticket_resumed_before_pending(
        self, mixed_status_workflow: tuple[Path, WorkflowState]
    ):
        """Given an in-progress ticket exists, when getting next ticket,
        then the in-progress ticket is returned (to resume work)."""
        state_file, state = mixed_status_workflow

        result = get_next_ticket(state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-004"
        assert result.ticket.status == "in_progress"
        assert "resuming" in result.message.lower()

    def test_in_progress_with_dependencies_checked(self, tmp_path: Path):
        """Given an in-progress ticket has dependencies, when getting next ticket,
        then the in-progress ticket is returned regardless."""
        # In-progress tickets are resumed even if dependencies aren't strictly checked
        # (they were already started, so deps were satisfied at that time)
        tickets = [
            Ticket(id="TASK-001", title="Dependency", status="pending", dependencies=[]),
            Ticket(id="TASK-002", title="In progress", status="in_progress", dependencies=["TASK-001"]),
        ]
        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        # In-progress is returned even though dependency not complete
        # (it was started, so we should resume it)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"


# ============================================================================
# Test Cases: Count Accuracy
# ============================================================================


class TestCountAccuracy:
    """Tests for accurate ticket count reporting."""

    def test_counts_reflect_actual_ticket_statuses(
        self, mixed_status_workflow: tuple[Path, WorkflowState]
    ):
        """Given a mixed workflow, when getting next ticket,
        then counts accurately reflect each status."""
        state_file, state = mixed_status_workflow

        result = get_next_ticket(state)

        assert result.total == 4
        assert result.completed == 1  # TASK-001
        assert result.blocked == 1  # TASK-002
        assert result.pending == 1  # TASK-003
        assert result.in_progress == 1  # TASK-004

    def test_counts_include_all_tickets_regardless_of_selection(
        self, dependency_workflow: tuple[Path, WorkflowState]
    ):
        """Given tickets with dependencies, when getting next ticket,
        then counts include all tickets not just eligible ones."""
        state_file, state = dependency_workflow

        result = get_next_ticket(state)

        # All tickets are pending, even if only one is eligible
        assert result.total == 3
        assert result.pending == 3
        assert result.completed == 0
        assert result.blocked == 0


# ============================================================================
# Test Cases: State File Integration
# ============================================================================


class TestStateFileIntegration:
    """Tests for integration with state file operations."""

    def test_get_next_after_state_file_reload(self, simple_workflow: tuple[Path, WorkflowState]):
        """Given a state file is saved and reloaded, when getting next ticket,
        then the correct ticket is returned."""
        state_file, original_state = simple_workflow

        # Reload from file
        reloaded_state = load_workflow_state(state_file)

        result = get_next_ticket(reloaded_state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

    def test_state_changes_reflected_in_next_call(self, simple_workflow: tuple[Path, WorkflowState]):
        """Given the state is modified and saved, when getting next ticket after reload,
        then changes are reflected."""
        state_file, state = simple_workflow

        # Complete first ticket
        state.tickets[0].status = "completed"
        state.completed_count = 1
        save_workflow_state(state, state_file)

        # Reload and get next
        reloaded_state = load_workflow_state(state_file)
        result = get_next_ticket(reloaded_state)

        # Now TASK-002 should be next (TASK-001 is complete)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert result.completed == 1


# ============================================================================
# Test Cases: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_ticket_workflow(self, tmp_path: Path):
        """Given only one ticket exists, when getting next ticket,
        then that ticket is returned."""
        tickets = [
            Ticket(id="TASK-001", title="Only task", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.total == 1

    def test_circular_dependency_handling(self, tmp_path: Path):
        """Given tickets with circular dependencies, when getting next ticket,
        then no ticket is available (waiting on dependencies)."""
        # This tests that circular dependencies don't cause infinite loops
        tickets = [
            Ticket(id="TASK-001", title="Task 1", status="pending", dependencies=["TASK-002"]),
            Ticket(id="TASK-002", title="Task 2", status="pending", dependencies=["TASK-001"]),
        ]
        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        # Both are waiting on each other
        assert result.ticket is None
        assert result.status == "waiting_on_dependencies"
        assert result.skipped_for_deps == 2

    def test_self_referencing_dependency(self, tmp_path: Path):
        """Given a ticket depends on itself, when getting next ticket,
        then it is skipped (waiting on dependencies)."""
        tickets = [
            Ticket(id="TASK-001", title="Self ref", status="pending", dependencies=["TASK-001"]),
            Ticket(id="TASK-002", title="Normal", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        # TASK-002 should be selected (TASK-001 depends on itself which is not complete)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        # Both TASK-001 (self-ref) and TASK-002's skipped_for_deps count includes
        # remaining pending tickets with unmet deps after selection
        assert result.skipped_for_deps >= 1
