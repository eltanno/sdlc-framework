"""Unit tests for commands/ticket_reset.py - Ticket reset functionality.

Tests cover:
- Resetting blocked tickets to pending
- Clearing block reason
- Resetting attempt counter
- Handling non-blocked tickets (error case)
- Handling non-existent tickets (error case)
- Optional state cleanup

Following TDD: Write failing tests first, then implement.
"""

import json
import shutil
from pathlib import Path

import pytest


class TestResetTicket:
    """Tests for the reset_ticket function."""

    def test_reset_blocked_ticket_sets_status_to_pending(self, tmp_path: Path):
        """Given a blocked ticket, when resetting, then ticket status becomes pending."""
        from commands.ticket_reset import reset_ticket
        from core.state import load_workflow_state

        # Setup workflow state with blocked ticket
        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 3,
                    "block_reason": "Test failure",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = reset_ticket("TASK-001", state_file)

        # Verify state was updated
        updated_state = load_workflow_state(state_file)
        ticket = updated_state.tickets[0]

        assert ticket.status == "pending"
        assert result.success is True
        assert result.previous_status == "blocked"
        assert result.new_status == "pending"

    def test_reset_blocked_ticket_clears_block_reason(self, tmp_path: Path):
        """Given a blocked ticket with a reason, when resetting, then block reason is cleared."""
        from commands.ticket_reset import reset_ticket
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 2,
                    "block_reason": "Validation failed after 3 attempts",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        reset_ticket("TASK-001", state_file)

        updated_state = load_workflow_state(state_file)
        ticket = updated_state.tickets[0]

        assert ticket.block_reason is None

    def test_reset_blocked_ticket_resets_attempt_counter(self, tmp_path: Path):
        """Given a blocked ticket with attempts, when resetting, then attempt counter resets to 0."""
        from commands.ticket_reset import reset_ticket
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 5,
                    "block_reason": "Max attempts exceeded",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        reset_ticket("TASK-001", state_file)

        updated_state = load_workflow_state(state_file)
        ticket = updated_state.tickets[0]

        assert ticket.attempts == 0

    def test_reset_non_blocked_ticket_raises_error(self, tmp_path: Path):
        """Given a non-blocked ticket, when resetting, then an error is raised."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Pending ticket",
                    "status": "pending",
                    "dependencies": [],
                    "attempts": 0,
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(TicketResetError, match="only blocked tickets can be reset"):
            reset_ticket("TASK-001", state_file)

    def test_reset_in_progress_ticket_raises_error(self, tmp_path: Path):
        """Given an in-progress ticket, when resetting, then an error is raised."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "In-progress ticket",
                    "status": "in_progress",
                    "dependencies": [],
                    "attempts": 1,
                }
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(TicketResetError, match="only blocked tickets can be reset"):
            reset_ticket("TASK-001", state_file)

    def test_reset_completed_ticket_raises_error(self, tmp_path: Path):
        """Given a completed ticket, when resetting, then an error is raised."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Completed ticket",
                    "status": "completed",
                    "dependencies": [],
                    "attempts": 1,
                }
            ],
            "current_ticket": None,
            "completed_count": 1,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(TicketResetError, match="only blocked tickets can be reset"):
            reset_ticket("TASK-001", state_file)

    def test_reset_nonexistent_ticket_raises_error(self, tmp_path: Path):
        """Given a non-existent ticket ID, when resetting, then an error is raised."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Some ticket",
                    "status": "pending",
                    "dependencies": [],
                    "attempts": 0,
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(TicketResetError, match="not found"):
            reset_ticket("TASK-INVALID", state_file)

    def test_reset_with_missing_state_file_raises_error(self, tmp_path: Path):
        """Given a missing state file, when resetting, then an error is raised."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        missing_file = tmp_path / "missing-state.json"

        with pytest.raises(TicketResetError, match="State file not found"):
            reset_ticket("TASK-001", missing_file)


class TestResetTicketWithCleanup:
    """Tests for the reset_ticket function with state cleanup option."""

    def test_reset_with_clean_state_removes_state_directory(self, tmp_path: Path):
        """Given clean_state=True, when resetting, then state files are removed."""
        from commands.ticket_reset import reset_ticket

        # Setup workflow state
        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 2,
                    "block_reason": "Test failure",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create state directory with files
        state_dir = tmp_path / "docs" / "state" / "TASK-001"
        attempt_dir = state_dir / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')
        (attempt_dir / "engineer-state.md").write_text("# State")
        (state_dir / "attempt-2").mkdir()
        (state_dir / "attempt-2" / "validation.json").write_text('{"result": "fail"}')

        result = reset_ticket(
            "TASK-001",
            state_file,
            clean_state=True,
            state_base_dir=tmp_path / "docs" / "state"
        )

        # Verify state directory was removed
        assert not state_dir.exists()
        assert result.state_cleaned is True

    def test_reset_without_clean_state_preserves_state_directory(self, tmp_path: Path):
        """Given clean_state=False (default), when resetting, then state files are preserved."""
        from commands.ticket_reset import reset_ticket

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 1,
                    "block_reason": "Error",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create state directory
        state_dir = tmp_path / "docs" / "state" / "TASK-001"
        attempt_dir = state_dir / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')

        result = reset_ticket(
            "TASK-001",
            state_file,
            clean_state=False,
            state_base_dir=tmp_path / "docs" / "state"
        )

        # Verify state directory was preserved
        assert state_dir.exists()
        assert (attempt_dir / "engineer-state.json").exists()
        assert result.state_cleaned is False

    def test_reset_with_clean_state_handles_missing_state_dir(self, tmp_path: Path):
        """Given clean_state=True but no state directory exists, when resetting, then no error."""
        from commands.ticket_reset import reset_ticket

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 0,
                    "block_reason": "Never started",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # No state directory created
        state_dir = tmp_path / "docs" / "state" / "TASK-001"
        assert not state_dir.exists()

        # Should not raise error
        result = reset_ticket(
            "TASK-001",
            state_file,
            clean_state=True,
            state_base_dir=tmp_path / "docs" / "state"
        )

        assert result.success is True
        # state_cleaned is False because there was nothing to clean
        assert result.state_cleaned is False


class TestResetTicketResult:
    """Tests for the ResetResult dataclass returned by reset_ticket."""

    def test_result_contains_all_required_fields(self, tmp_path: Path):
        """Given a successful reset, result contains all expected fields."""
        from commands.ticket_reset import reset_ticket

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 3,
                    "block_reason": "Validation failed",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = reset_ticket("TASK-001", state_file)

        assert result.success is True
        assert result.ticket_id == "TASK-001"
        assert result.previous_status == "blocked"
        assert result.new_status == "pending"
        assert result.state_cleaned is False

    def test_result_to_dict_for_json_output(self, tmp_path: Path):
        """Given a result, to_dict returns JSON-serializable dictionary."""
        from commands.ticket_reset import reset_ticket

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 1,
                    "block_reason": "Error",
                }
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = reset_ticket("TASK-001", state_file)
        result_dict = result.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)

        # Should contain expected keys
        assert result_dict["ticket"] == "TASK-001"
        assert result_dict["previous_status"] == "blocked"
        assert result_dict["new_status"] == "pending"
        assert result_dict["state_cleaned"] is False


class TestResetTicketUpdatesBlockedCount:
    """Tests for blocked count updates in workflow state."""

    def test_reset_decrements_blocked_count(self, tmp_path: Path):
        """Given a blocked ticket, when resetting, then blocked_count is decremented."""
        from commands.ticket_reset import reset_ticket
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 2,
                    "block_reason": "Error",
                },
                {
                    "id": "TASK-002",
                    "title": "Another blocked ticket",
                    "status": "blocked",
                    "dependencies": [],
                    "attempts": 1,
                    "block_reason": "Another error",
                },
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 2,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        reset_ticket("TASK-001", state_file)

        updated_state = load_workflow_state(state_file)
        assert updated_state.blocked_count == 1
