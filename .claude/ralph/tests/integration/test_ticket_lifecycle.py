"""Integration tests for ticket lifecycle flows.

This module tests the complete ticket lifecycle including:
- Start -> Work -> Done flow
- Start -> Block -> Reset -> Done flow
- Resuming interrupted work
- State persistence across operations

These tests use temporary state files and mock external operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
    load_workflow_state,
    save_workflow_state,
    write_engineer_state,
    get_latest_attempt,
    ensure_state_dir,
)
from commands.get_next import get_next_ticket
from commands.ticket_done import mark_ticket_done, ticket_done
from commands.ticket_reset import reset_ticket, TicketResetError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def lifecycle_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a workflow for lifecycle testing.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(id="TASK-001", title="First task", status="pending", dependencies=[]),
        Ticket(id="TASK-002", title="Second task", status="pending", dependencies=["TASK-001"]),
        Ticket(id="TASK-003", title="Third task", status="pending", dependencies=["TASK-002"]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002", "TASK-003"],
        dependencies={"TASK-002": ["TASK-001"], "TASK-003": ["TASK-002"]},
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
def in_progress_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a workflow with an in-progress ticket.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(id="TASK-001", title="In progress task", status="in_progress", dependencies=[], attempts=1),
        Ticket(id="TASK-002", title="Pending task", status="pending", dependencies=["TASK-001"]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002"],
        dependencies={"TASK-002": ["TASK-001"]},
        attempts={"TASK-001": 1},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,
        current_ticket="TASK-001",
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


@pytest.fixture
def blocked_workflow(tmp_path: Path) -> tuple[Path, WorkflowState]:
    """Create a workflow with a blocked ticket.

    Returns:
        Tuple of (state_file_path, workflow_state)
    """
    tickets = [
        Ticket(
            id="TASK-001",
            title="Blocked task",
            status="blocked",
            dependencies=[],
            attempts=3,
            block_reason="Exceeded max attempts",
        ),
        Ticket(id="TASK-002", title="Pending task", status="pending", dependencies=[]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002"],
        dependencies={},
        attempts={"TASK-001": 3},
        blocked={"TASK-001": "Exceeded max attempts"},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,
        blocked_count=1,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)
    return state_file, state


@pytest.fixture
def mock_gh_cli(mocker):
    """Mock gh CLI for GitHub operations."""
    mock = mocker.patch("commands.ticket_done.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = "[]"
    mock.return_value.stderr = ""
    return mock


# ============================================================================
# Test Cases: Start -> Done Flow
# ============================================================================


class TestStartToDoneFlow:
    """Tests for the basic start -> work -> done lifecycle."""

    def test_complete_single_ticket_lifecycle(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given a pending ticket, when completed, then status becomes completed
        and next ticket becomes available."""
        state_file, state = lifecycle_workflow

        # Step 1: Get next ticket
        result = get_next_ticket(state)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

        # Step 2: Simulate work completion - mark done
        done_result = mark_ticket_done(
            ticket_id="TASK-001",
            pr_number="123",
            state_file=state_file,
        )

        # Verify completion
        assert done_result["status"] == "completed"
        assert done_result["pr_number"] == "123"
        assert done_result["progress"]["current"] == 1
        assert done_result["progress"]["remaining"] == 2

        # Step 3: Get next ticket - should be TASK-002 now
        reloaded_state = load_workflow_state(state_file)
        result = get_next_ticket(reloaded_state)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"

    def test_complete_all_tickets_in_order(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given tickets with dependencies, when completed in order,
        then all tickets become completed."""
        state_file, state = lifecycle_workflow

        # Complete TASK-001
        mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)

        # Complete TASK-002
        mark_ticket_done("TASK-002", pr_number="101", state_file=state_file)

        # Complete TASK-003
        done_result = mark_ticket_done("TASK-003", pr_number="102", state_file=state_file)

        assert done_result["all_done"]
        assert done_result["progress"]["remaining"] == 0

        # Verify final state
        final_state = load_workflow_state(state_file)
        result = get_next_ticket(final_state)
        assert result.status == "complete"
        assert result.completed == 3

    def test_done_with_issue_number(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given a ticket with associated issue, when completed,
        then issue number is recorded in state."""
        state_file, state = lifecycle_workflow

        done_result = mark_ticket_done(
            ticket_id="TASK-001",
            pr_number="100",
            issue_number=42,
            state_file=state_file,
        )

        # Reload and check issue number recorded
        final_state = load_workflow_state(state_file)
        ticket = next(t for t in final_state.tickets if t.id == "TASK-001")
        # Note: issue_number is not a Ticket attribute, check raw state
        raw_state = json.loads(state_file.read_text())
        ticket_data = next(t for t in raw_state["tickets"] if t["id"] == "TASK-001")
        assert ticket_data["issue_number"] == 42


# ============================================================================
# Test Cases: Start -> Block -> Reset -> Done Flow
# ============================================================================


class TestBlockResetFlow:
    """Tests for the block -> reset -> done lifecycle."""

    def test_reset_blocked_ticket_to_pending(
        self, blocked_workflow: tuple[Path, WorkflowState], tmp_path: Path
    ):
        """Given a blocked ticket, when reset, then status becomes pending
        and ticket becomes available again."""
        state_file, state = blocked_workflow

        # Verify ticket is blocked initially
        assert state.tickets[0].status == "blocked"
        assert state.blocked_count == 1

        # Reset the blocked ticket
        result = reset_ticket(
            ticket_id="TASK-001",
            state_file=state_file,
        )

        assert result.success
        assert result.previous_status == "blocked"
        assert result.new_status == "pending"

        # Verify state is updated
        reloaded_state = load_workflow_state(state_file)
        ticket = next(t for t in reloaded_state.tickets if t.id == "TASK-001")
        assert ticket.status == "pending"
        assert ticket.block_reason is None
        assert ticket.attempts == 0
        assert reloaded_state.blocked_count == 0

    def test_reset_then_complete_ticket(
        self, blocked_workflow: tuple[Path, WorkflowState], mock_gh_cli, tmp_path: Path
    ):
        """Given a reset ticket, when work completes successfully,
        then ticket becomes completed."""
        state_file, state = blocked_workflow

        # Reset the blocked ticket
        reset_ticket(ticket_id="TASK-001", state_file=state_file)

        # Get next - should return the reset ticket
        reloaded_state = load_workflow_state(state_file)
        result = get_next_ticket(reloaded_state)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

        # Complete the ticket
        done_result = mark_ticket_done(
            ticket_id="TASK-001",
            pr_number="200",
            state_file=state_file,
        )

        assert done_result["status"] == "completed"

        # Verify final state
        final_state = load_workflow_state(state_file)
        ticket = next(t for t in final_state.tickets if t.id == "TASK-001")
        assert ticket.status == "completed"

    def test_reset_with_state_cleanup(
        self, blocked_workflow: tuple[Path, WorkflowState], tmp_path: Path
    ):
        """Given a blocked ticket with state files, when reset with cleanup,
        then state directory is removed."""
        state_file, state = blocked_workflow
        state_base_dir = tmp_path / "state"

        # Create state directory with some files
        state_dir = ensure_state_dir("TASK-001", 1, state_base_dir)
        (state_dir / "engineer-state.json").write_text('{"test": true}')

        # Verify state dir exists
        assert state_dir.exists()

        # Reset with cleanup
        result = reset_ticket(
            ticket_id="TASK-001",
            state_file=state_file,
            clean_state=True,
            state_base_dir=state_base_dir,
        )

        assert result.success
        assert result.state_cleaned
        assert not (state_base_dir / "TASK-001").exists()

    def test_cannot_reset_non_blocked_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given a pending ticket, when reset attempted,
        then TicketResetError is raised."""
        state_file, state = lifecycle_workflow

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-001", state_file=state_file)

        assert "only blocked tickets can be reset" in str(exc_info.value)

    def test_cannot_reset_nonexistent_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given a non-existent ticket ID, when reset attempted,
        then TicketResetError is raised."""
        state_file, state = lifecycle_workflow

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-999", state_file=state_file)

        assert "not found" in str(exc_info.value)


# ============================================================================
# Test Cases: Resume Interrupted Work
# ============================================================================


class TestResumeInterruptedWork:
    """Tests for resuming work after interruption."""

    def test_resume_in_progress_ticket(
        self, in_progress_workflow: tuple[Path, WorkflowState]
    ):
        """Given an in-progress ticket exists, when getting next ticket,
        then the in-progress ticket is returned for resumption."""
        state_file, state = in_progress_workflow

        result = get_next_ticket(state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.ticket.status == "in_progress"
        assert "resuming" in result.message.lower()

    def test_state_files_preserved_on_resume(
        self, in_progress_workflow: tuple[Path, WorkflowState], tmp_path: Path
    ):
        """Given previous attempt state files exist, when resuming,
        then state files are accessible."""
        state_file, state = in_progress_workflow
        state_base_dir = tmp_path / "state"

        # Create state from previous attempt
        state_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "status": "validation_failed",
            "branch": "feature/TASK-001-implementation",
            "last_commit": "abc123",
            "validation_result": {
                "typecheck": "pass",
                "lint": "fail",
                "test": "pass",
                "build": "pass",
                "overall": "fail",
            },
            "work_completed": ["Initial implementation"],
            "files_modified": ["src/main.py"],
            "tests_written": [],
            "known_issues": ["Lint errors in main.py"],
            "next_steps": ["Fix lint errors"],
        }
        write_engineer_state(state_data, state_base_dir)

        # Verify state file exists
        latest_attempt = get_latest_attempt("TASK-001", state_base_dir)
        assert latest_attempt == 1

        # Get next ticket - should be the in-progress one
        result = get_next_ticket(state)
        assert result.ticket.id == "TASK-001"

    def test_resume_increments_attempt_counter(
        self, in_progress_workflow: tuple[Path, WorkflowState], tmp_path: Path
    ):
        """Given a resumed ticket that fails again, when state is written,
        then attempt counter is incremented."""
        state_file, state = in_progress_workflow
        state_base_dir = tmp_path / "state"

        # First attempt state
        state_data_1 = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "status": "validation_failed",
            "branch": "feature/TASK-001-implementation",
            "last_commit": "abc123",
            "validation_result": {"overall": "fail"},
            "work_completed": [],
            "files_modified": [],
            "tests_written": [],
            "known_issues": [],
            "next_steps": [],
        }
        write_engineer_state(state_data_1, state_base_dir)

        assert get_latest_attempt("TASK-001", state_base_dir) == 1

        # Second attempt state
        state_data_2 = {
            "ticket_id": "TASK-001",
            "attempt": 2,
            "status": "validation_failed",
            "branch": "feature/TASK-001-implementation",
            "last_commit": "def456",
            "validation_result": {"overall": "fail"},
            "work_completed": [],
            "files_modified": [],
            "tests_written": [],
            "known_issues": [],
            "next_steps": [],
        }
        write_engineer_state(state_data_2, state_base_dir)

        assert get_latest_attempt("TASK-001", state_base_dir) == 2


# ============================================================================
# Test Cases: State Persistence
# ============================================================================


class TestStatePersistence:
    """Tests for state persistence across operations."""

    def test_state_survives_reload(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given state changes are made, when state file is reloaded,
        then changes persist correctly."""
        state_file, state = lifecycle_workflow

        # Complete first ticket
        mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)

        # Reload state multiple times and verify
        for _ in range(3):
            reloaded = load_workflow_state(state_file)
            ticket = next(t for t in reloaded.tickets if t.id == "TASK-001")
            assert ticket.status == "completed"
            assert reloaded.completed_count == 1

    def test_concurrent_state_updates(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given multiple state updates occur, when state is checked,
        then all updates are reflected."""
        state_file, state = lifecycle_workflow

        # Simulate multiple updates
        mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)

        # Reload and update again
        state2 = load_workflow_state(state_file)
        state2.tickets[1].status = "in_progress"
        state2.current_ticket = "TASK-002"
        save_workflow_state(state2, state_file)

        # Verify both changes persisted
        final_state = load_workflow_state(state_file)
        assert final_state.tickets[0].status == "completed"
        assert final_state.tickets[1].status == "in_progress"
        assert final_state.current_ticket == "TASK-002"

    def test_pr_and_issue_tracked_in_state(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given PR and issue info provided, when ticket completed,
        then both are tracked in state."""
        state_file, state = lifecycle_workflow

        mark_ticket_done(
            ticket_id="TASK-001",
            pr_number="150",
            issue_number=50,
            state_file=state_file,
        )

        # Read raw state to check pr and issue
        raw_state = json.loads(state_file.read_text())
        ticket_data = next(t for t in raw_state["tickets"] if t["id"] == "TASK-001")

        assert ticket_data["status"] == "completed"
        assert ticket_data["pr"] == "150"
        assert ticket_data["issue_number"] == 50


# ============================================================================
# Test Cases: Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in lifecycle operations."""

    def test_done_fails_for_nonexistent_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given a non-existent ticket ID, when marking done,
        then ValueError is raised."""
        state_file, state = lifecycle_workflow

        with pytest.raises(ValueError) as exc_info:
            mark_ticket_done(ticket_id="TASK-999", state_file=state_file)

        assert "not found" in str(exc_info.value)

    def test_done_fails_for_missing_state_file(self, tmp_path: Path):
        """Given state file doesn't exist, when marking done,
        then FileNotFoundError is raised."""
        fake_state_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            mark_ticket_done(ticket_id="TASK-001", state_file=fake_state_file)

    def test_reset_fails_for_missing_state_file(self, tmp_path: Path):
        """Given state file doesn't exist, when resetting,
        then TicketResetError is raised."""
        fake_state_file = tmp_path / "nonexistent.json"

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-001", state_file=fake_state_file)

        assert "State file not found" in str(exc_info.value)


# ============================================================================
# Test Cases: Progress Tracking
# ============================================================================


class TestProgressTracking:
    """Tests for progress tracking through the lifecycle."""

    def test_progress_updates_correctly_during_completion(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given tickets are completed sequentially, when progress checked,
        then counts update correctly."""
        state_file, state = lifecycle_workflow

        # Complete first ticket
        result1 = mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)
        assert result1["progress"]["current"] == 1
        assert result1["progress"]["total"] == 3
        assert result1["progress"]["remaining"] == 2
        assert result1["next_ticket"] == "TASK-002"

        # Complete second ticket
        result2 = mark_ticket_done("TASK-002", pr_number="101", state_file=state_file)
        assert result2["progress"]["current"] == 2
        assert result2["progress"]["remaining"] == 1
        assert result2["next_ticket"] == "TASK-003"

        # Complete third ticket
        result3 = mark_ticket_done("TASK-003", pr_number="102", state_file=state_file)
        assert result3["progress"]["current"] == 3
        assert result3["progress"]["remaining"] == 0
        assert result3["all_done"]
        assert result3["next_ticket"] is None

    def test_blocked_count_updates_correctly(
        self, blocked_workflow: tuple[Path, WorkflowState]
    ):
        """Given blocked tickets are reset, when state checked,
        then blocked count updates correctly."""
        state_file, state = blocked_workflow

        # Initial state has 1 blocked
        assert state.blocked_count == 1

        # Reset the blocked ticket
        reset_ticket(ticket_id="TASK-001", state_file=state_file)

        # Verify blocked count is decremented
        reloaded = load_workflow_state(state_file)
        assert reloaded.blocked_count == 0
