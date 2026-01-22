"""Unit tests for ticket_start command module.

Tests the ticket_start module which handles:
- Creating feature branches for tickets
- Checking out existing branches
- Updating workflow state to in_progress
- Preventing branch creation with uncommitted changes
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from commands.ticket_start import (
    start_ticket,
    TicketStartError,
    DirtyWorkingDirectoryError,
    TicketNotFoundError,
    generate_branch_name,
)


class TestGenerateBranchName:
    """Tests for branch name generation."""

    def test_generate_branch_name_simple_id(self):
        """Test branch name generation with simple ticket ID."""
        result = generate_branch_name("TASK-001")
        assert result == "feature/TASK-001-implementation"

    def test_generate_branch_name_sdlc_format(self):
        """Test branch name generation with SDLC format ID."""
        result = generate_branch_name("SDLC-0022")
        assert result == "feature/SDLC-0022-implementation"

    def test_generate_branch_name_with_custom_suffix(self):
        """Test branch name generation with custom suffix."""
        result = generate_branch_name("TASK-001", suffix="auth-feature")
        assert result == "feature/TASK-001-auth-feature"


class TestStartTicket:
    """Tests for the start_ticket function."""

    def test_start_ticket_creates_branch_when_not_exists(
        self, tmp_path: Path, mocker
    ):
        """Test that start_ticket creates a new branch when it doesn't exist."""
        # Setup: create a workflow state file
        state_file = self._create_state_file(tmp_path, "TASK-001", "pending")

        # Mock git operations
        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False
        mock_git.branch_exists.return_value = False
        mock_git.get_current_branch.return_value = "main"

        # Call the function
        result = start_ticket("TASK-001", state_file)

        # Verify branch was created with correct arguments
        mock_git.create_branch.assert_called_once_with(
            "feature/TASK-001-implementation", "origin/main"
        )

        # Verify result object has correct values
        assert result.ticket_id == "TASK-001"
        assert result.branch == "feature/TASK-001-implementation"
        assert result.status == "in_progress"
        assert result.created_new_branch is True

        # Verify state file was updated correctly
        with open(state_file) as f:
            state = json.load(f)
        ticket = next(t for t in state["tickets"] if t["id"] == "TASK-001")
        assert ticket["status"] == "in_progress"
        assert state["current_ticket"] == "TASK-001"

    def test_start_ticket_checks_out_existing_branch(
        self, tmp_path: Path, mocker
    ):
        """Test that start_ticket checks out an existing branch."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "pending")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False
        mock_git.branch_exists.return_value = True
        mock_git.get_current_branch.return_value = "main"

        result = start_ticket("TASK-001", state_file)

        # Verify existing branch was checked out
        mock_git.checkout_branch.assert_called_once_with(
            "feature/TASK-001-implementation"
        )
        # Verify no new branch was created
        mock_git.create_branch.assert_not_called()

        # Verify result reflects checkout of existing branch
        assert result.branch == "feature/TASK-001-implementation"
        assert result.created_new_branch is False
        assert result.status == "in_progress"

        # Verify state was updated
        with open(state_file) as f:
            state = json.load(f)
        assert state["current_ticket"] == "TASK-001"

    def test_start_ticket_raises_error_with_dirty_working_directory(
        self, tmp_path: Path, mocker
    ):
        """Test that start_ticket raises error when working directory is dirty."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "pending")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = True
        mock_git.get_status.return_value = MagicMock(
            modified=["file.py"],
            staged=[],
            untracked=["new_file.py"],
        )

        with pytest.raises(DirtyWorkingDirectoryError) as exc_info:
            start_ticket("TASK-001", state_file)

        assert "uncommitted changes" in str(exc_info.value).lower()

    def test_start_ticket_updates_state_file(self, tmp_path: Path, mocker):
        """Test that start_ticket updates the workflow state file."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "pending")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False
        mock_git.branch_exists.return_value = False
        mock_git.get_current_branch.return_value = "main"

        start_ticket("TASK-001", state_file)

        # Verify state file was updated
        with open(state_file) as f:
            state = json.load(f)

        ticket = next(t for t in state["tickets"] if t["id"] == "TASK-001")
        assert ticket["status"] == "in_progress"
        assert state["current_ticket"] == "TASK-001"

    def test_start_ticket_raises_error_for_nonexistent_ticket(
        self, tmp_path: Path, mocker
    ):
        """Test that start_ticket raises error for non-existent ticket."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "pending")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False

        with pytest.raises(TicketNotFoundError) as exc_info:
            start_ticket("TASK-999", state_file)

        assert "TASK-999" in str(exc_info.value)

    def test_start_ticket_already_in_progress_on_same_branch(
        self, tmp_path: Path, mocker
    ):
        """Test starting a ticket that's already in progress on correct branch."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "in_progress")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False
        mock_git.branch_exists.return_value = True
        mock_git.get_current_branch.return_value = "feature/TASK-001-implementation"

        # Read state before operation to verify idempotency
        with open(state_file) as f:
            state_before = json.load(f)

        # Should succeed without error - idempotent operation
        result = start_ticket("TASK-001", state_file)

        # No branch operations needed since we're already on the correct branch
        mock_git.create_branch.assert_not_called()
        mock_git.checkout_branch.assert_not_called()

        # Verify result is consistent
        assert result.branch == "feature/TASK-001-implementation"
        assert result.status == "in_progress"
        assert result.ticket_id == "TASK-001"

        # Verify state file critical fields remain unchanged (idempotent)
        with open(state_file) as f:
            state_after = json.load(f)
        assert state_after["current_ticket"] == state_before["current_ticket"]
        ticket_before = next(t for t in state_before["tickets"] if t["id"] == "TASK-001")
        ticket_after = next(t for t in state_after["tickets"] if t["id"] == "TASK-001")
        assert ticket_after["status"] == ticket_before["status"]
        assert ticket_after["id"] == ticket_before["id"]

    def test_start_ticket_with_completed_ticket_raises_error(
        self, tmp_path: Path, mocker
    ):
        """Test that starting a completed ticket raises an error."""
        state_file = self._create_state_file(tmp_path, "TASK-001", "completed")

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False

        with pytest.raises(TicketStartError) as exc_info:
            start_ticket("TASK-001", state_file)

        assert "already completed" in str(exc_info.value).lower()

    def test_start_ticket_with_blocked_ticket_raises_error(
        self, tmp_path: Path, mocker
    ):
        """Test that starting a blocked ticket raises an error."""
        state_file = self._create_state_file(
            tmp_path, "TASK-001", "blocked", block_reason="Dependencies failed"
        )

        mock_git = mocker.patch("commands.ticket_start.git")
        mock_git.is_dirty.return_value = False

        with pytest.raises(TicketStartError) as exc_info:
            start_ticket("TASK-001", state_file)

        assert "blocked" in str(exc_info.value).lower()

    def _create_state_file(
        self,
        tmp_path: Path,
        ticket_id: str,
        status: str,
        block_reason: str | None = None,
    ) -> Path:
        """Helper to create a state file for testing."""
        ticket_data = {
            "id": ticket_id,
            "title": f"Test ticket {ticket_id}",
            "status": status,
            "dependencies": [],
            "attempts": 0,
        }
        if block_reason:
            ticket_data["block_reason"] = block_reason

        state_content = {
            "version": "2.0",
            "prd_path": "docs/prds/test-prd.md",
            "plan_path": "docs/plans/test-plan.md",
            "tickets": [ticket_data],
            "current_ticket": ticket_id if status == "in_progress" else None,
            "completed_count": 1 if status == "completed" else 0,
            "blocked_count": 1 if status == "blocked" else 0,
        }

        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_content, indent=2))
        return state_file
