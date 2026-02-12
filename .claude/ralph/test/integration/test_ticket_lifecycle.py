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
from commands.ticket_done import mark_ticket_done
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
        """Given a pending ticket, when completed, then current_ticket is cleared
        and completion info is returned."""
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

        # Verify completion result
        assert done_result["status"] == "completed"
        assert done_result["pr_number"] == "123"
        assert done_result["total"] == 3  # Total tickets in workflow

        # Step 3: Verify current_ticket is cleared (clears current)
        reloaded_state = load_workflow_state(state_file)
        assert reloaded_state.current_ticket is None

    def test_complete_all_tickets_in_order(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given tickets with dependencies, when mark_ticket_done is called,
        then completion info is returned for each."""
        state_file, state = lifecycle_workflow

        # Complete TASK-001
        result1 = mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)
        assert result1["status"] == "completed"
        assert result1["total"] == 3

        # Complete TASK-002
        result2 = mark_ticket_done("TASK-002", pr_number="101", state_file=state_file)
        assert result2["status"] == "completed"
        assert result2["total"] == 3

        # Complete TASK-003
        result3 = mark_ticket_done("TASK-003", pr_number="102", state_file=state_file)
        assert result3["status"] == "completed"
        assert result3["total"] == 3

        # Verify current_ticket is still cleared (clears current)
        final_state = load_workflow_state(state_file)
        assert final_state.current_ticket is None

    def test_done_clears_current_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given a ticket being completed, when marked done,
        then current_ticket is cleared in state."""
        state_file, state = lifecycle_workflow

        # First set a current ticket
        raw_state = json.loads(state_file.read_text())
        raw_state["current_ticket"] = "TASK-001"
        state_file.write_text(json.dumps(raw_state, indent=2))

        done_result = mark_ticket_done(
            ticket_id="TASK-001",
            pr_number="100",
            state_file=state_file,
        )

        assert done_result["status"] == "completed"
        assert done_result["ticket_id"] == "TASK-001"

        # Verify current_ticket is cleared
        raw_state = json.loads(state_file.read_text())
        assert raw_state["current_ticket"] is None


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
        assert state.tickets[0].status != "pending"  # Negative assertion
        assert state.blocked_count == 1

        # Reset the blocked ticket
        result = reset_ticket(
            ticket_id="TASK-001",
            state_file=state_file,
        )

        assert result.success is True
        assert result.success is not False  # Negative assertion
        assert result.previous_status == "blocked"
        assert result.new_status == "pending"
        assert result.new_status != "blocked"  # Negative assertion

        # Verify state is updated
        reloaded_state = load_workflow_state(state_file)
        ticket = next(t for t in reloaded_state.tickets if t.id == "TASK-001")
        assert ticket.status == "pending"
        assert ticket.status != "blocked"  # Verify transition happened
        assert ticket.block_reason is None
        assert ticket.attempts == 0
        assert ticket.attempts != 3  # Verify reset, not just presence
        assert reloaded_state.blocked_count == 0
        assert reloaded_state.blocked_count != 1  # Verify decrement

    def test_reset_then_complete_ticket(
        self, blocked_workflow: tuple[Path, WorkflowState], mock_gh_cli, tmp_path: Path
    ):
        """Given a reset ticket, when work completes successfully,
        then current_ticket is cleared and ticket is removed from blocked."""
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
        assert done_result["pr_number"] == "200"
        assert done_result["total"] == 2

        # Verify current_ticket is cleared (clears current)
        final_state = load_workflow_state(state_file)
        assert final_state.current_ticket is None

    def test_reset_with_state_cleanup(
        self, blocked_workflow: tuple[Path, WorkflowState], tmp_path: Path
    ):
        """Given a blocked ticket with state files, when reset with cleanup,
        then state directory and all files are removed."""
        state_file, state = blocked_workflow
        state_base_dir = tmp_path / "state"

        # Create state directory with multiple files
        state_dir = ensure_state_dir("TASK-001", 1, state_base_dir)
        file1 = state_dir / "engineer-state.json"
        file2 = state_dir / "attempt-1.log"
        file1.write_text('{"test": true}')
        file2.write_text('log data')

        # Verify state dir and files exist
        assert state_dir.exists()
        assert file1.exists()
        assert file2.exists()

        # Reset with cleanup
        result = reset_ticket(
            ticket_id="TASK-001",
            state_file=state_file,
            clean_state=True,
            state_base_dir=state_base_dir,
        )

        assert result.success is True
        assert result.state_cleaned is True
        assert result.state_cleaned is not False  # Negative assertion

        # Verify directory AND files are gone
        assert not (state_base_dir / "TASK-001").exists()
        assert not file1.exists()  # Files removed
        assert not file2.exists()  # All files removed

    def test_cannot_reset_non_blocked_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given a pending ticket, when reset attempted,
        then TicketResetError is raised with clear error message."""
        state_file, state = lifecycle_workflow

        # Verify ticket is actually pending, not blocked
        ticket = next(t for t in state.tickets if t.id == "TASK-001")
        assert ticket.status == "pending"
        assert ticket.status != "blocked"

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-001", state_file=state_file)

        error_msg = str(exc_info.value)
        assert "only blocked tickets can be reset" in error_msg
        assert "TASK-001" in error_msg  # Error includes ticket ID

    def test_cannot_reset_nonexistent_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given a non-existent ticket ID, when reset attempted,
        then TicketResetError is raised with helpful message."""
        state_file, state = lifecycle_workflow

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-999", state_file=state_file)

        error_msg = str(exc_info.value)
        assert "not found" in error_msg
        assert "TASK-999" in error_msg  # Error includes the invalid ID


# ============================================================================
# Test Cases: Resume Interrupted Work
# ============================================================================


class TestResumeInterruptedWork:
    """Tests for resuming work after interruption."""

    def test_resume_in_progress_ticket(
        self, in_progress_workflow: tuple[Path, WorkflowState]
    ):
        """Given an in-progress ticket exists alongside pending tickets,
        when getting next ticket, then in-progress ticket takes priority."""
        state_file, state = in_progress_workflow

        result = get_next_ticket(state)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.ticket.id != "TASK-002"  # Pending ticket NOT selected (in-progress has priority)
        assert result.ticket.status == "in_progress"
        assert result.ticket.status != "pending"  # Verify it's actually in_progress
        assert result.ticket.status != "blocked"  # Not other states
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

        # Reload state multiple times and verify current_ticket is cleared (clears current)
        for _ in range(3):
            reloaded = load_workflow_state(state_file)
            # current_ticket is cleared when ticket is completed
            assert reloaded.current_ticket is None

    def test_concurrent_state_updates(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given multiple state updates occur, when state is checked,
        then all updates are reflected."""
        state_file, state = lifecycle_workflow

        # First update: mark ticket done (clears current_ticket)
        mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)

        # Verify current_ticket was cleared
        state2 = load_workflow_state(state_file)
        assert state2.current_ticket is None

        # Second update: manually set another ticket in progress
        state2.tickets[1].status = "in_progress"
        state2.current_ticket = "TASK-002"
        save_workflow_state(state2, state_file)

        # Verify the manual update persisted
        final_state = load_workflow_state(state_file)
        assert final_state.tickets[1].status == "in_progress"
        assert final_state.current_ticket == "TASK-002"


# ============================================================================
# Test Cases: Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in lifecycle operations."""

    def test_done_fails_for_nonexistent_ticket(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given a non-existent ticket ID, when marking done,
        then error is raised with helpful message."""
        state_file, state = lifecycle_workflow

        with pytest.raises(Exception) as exc_info:
            mark_ticket_done(ticket_id="TASK-999", state_file=state_file)

        error_msg = str(exc_info.value)
        assert "not found" in error_msg
        assert "TASK-999" in error_msg  # Error message includes the invalid ID

    def test_done_fails_for_missing_state_file(self, tmp_path: Path):
        """Given state file doesn't exist, when marking done,
        then FileNotFoundError is raised with helpful message."""
        fake_state_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            mark_ticket_done(ticket_id="TASK-001", state_file=fake_state_file)

        # Verify error message is helpful
        error_msg = str(exc_info.value)
        assert "nonexistent.json" in error_msg or "State file" in error_msg

    def test_reset_fails_for_missing_state_file(self, tmp_path: Path):
        """Given state file doesn't exist, when resetting,
        then TicketResetError is raised with clear message."""
        fake_state_file = tmp_path / "nonexistent.json"

        with pytest.raises(TicketResetError) as exc_info:
            reset_ticket(ticket_id="TASK-001", state_file=fake_state_file)

        error_msg = str(exc_info.value)
        assert "State file not found" in error_msg
        assert str(fake_state_file) in error_msg  # Error includes file path


# ============================================================================
# Test Cases: Progress Tracking
# ============================================================================


class TestProgressTracking:
    """Tests for progress tracking through the lifecycle."""

    def test_total_tickets_returned_during_completion(
        self, lifecycle_workflow: tuple[Path, WorkflowState], mock_gh_cli
    ):
        """Given tickets are completed sequentially, when completion checked,
        then total ticket count is returned."""
        state_file, state = lifecycle_workflow

        # Complete first ticket - returns total only
        result1 = mark_ticket_done("TASK-001", pr_number="100", state_file=state_file)
        assert result1["status"] == "completed"
        assert result1["total"] == 3
        assert result1["remaining"] is None  # can't know without PM query
        assert result1["next_ticket"] is None  # can't know without PM query

        # Complete second ticket
        result2 = mark_ticket_done("TASK-002", pr_number="101", state_file=state_file)
        assert result2["status"] == "completed"
        assert result2["total"] == 3

        # Complete third ticket
        result3 = mark_ticket_done("TASK-003", pr_number="102", state_file=state_file)
        assert result3["status"] == "completed"
        assert result3["total"] == 3

    def test_blocked_count_updates_correctly(
        self, blocked_workflow: tuple[Path, WorkflowState]
    ):
        """Given blocked tickets are reset, when state checked,
        then blocked count decrements to reflect actual blocked tickets."""
        state_file, state = blocked_workflow

        # Initial state has 1 blocked
        assert state.blocked_count == 1
        assert state.blocked_count != 0  # Negative assertion

        # Verify the ticket is actually blocked
        blocked_ticket = next(t for t in state.tickets if t.id == "TASK-001")
        assert blocked_ticket.status == "blocked"

        # Reset the blocked ticket
        reset_ticket(ticket_id="TASK-001", state_file=state_file)

        # Verify blocked count is decremented AND ticket is no longer blocked
        reloaded = load_workflow_state(state_file)
        assert reloaded.blocked_count == 0
        assert reloaded.blocked_count != 1  # Verify actual decrement

        # Verify the ticket is actually unblocked
        reset_ticket_obj = next(t for t in reloaded.tickets if t.id == "TASK-001")
        assert reset_ticket_obj.status == "pending"
        assert reset_ticket_obj.status != "blocked"  # Verify unblocked


# ============================================================================
# Test Cases: Business Logic Validation
# ============================================================================


class TestBusinessLogic:
    """Tests for business rules and invariants."""

    def test_get_next_excludes_blocked_tickets(
        self, blocked_workflow: tuple[Path, WorkflowState]
    ):
        """Given a blocked ticket exists, when getting next ticket,
        then blocked tickets are never returned."""
        state_file, state = blocked_workflow

        # TASK-001 is blocked, TASK-002 is pending
        result = get_next_ticket(state)

        # Should return TASK-002, NOT TASK-001
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert result.ticket.id != "TASK-001"  # Blocked ticket NOT returned
        assert result.ticket.status == "pending"
        assert result.ticket.status != "blocked"  # Verify it's not blocked

        # Verify blocked ticket still exists in state (just not returned)
        blocked_ticket = next(t for t in state.tickets if t.id == "TASK-001")
        assert blocked_ticket.status == "blocked"

    def test_dependencies_must_be_satisfied(
        self, lifecycle_workflow: tuple[Path, WorkflowState]
    ):
        """Given tickets with dependencies, when getting next ticket,
        then only tickets with satisfied dependencies are returned."""
        state_file, state = lifecycle_workflow

        # TASK-001 has no dependencies
        # TASK-002 depends on TASK-001
        # TASK-003 depends on TASK-002

        # Initially, only TASK-001 should be available
        result = get_next_ticket(state)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.ticket.id != "TASK-002"  # Dependencies not satisfied
        assert result.ticket.id != "TASK-003"  # Dependencies not satisfied

        # Verify dependency structure
        task_001 = next(t for t in state.tickets if t.id == "TASK-001")
        task_002 = next(t for t in state.tickets if t.id == "TASK-002")
        task_003 = next(t for t in state.tickets if t.id == "TASK-003")

        assert task_001.dependencies == []  # No dependencies
        assert task_002.dependencies == ["TASK-001"]  # Depends on 001
        assert task_003.dependencies == ["TASK-002"]  # Depends on 002
