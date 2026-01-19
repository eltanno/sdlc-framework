"""Unit tests for commands/mark_blocked.py - Mark ticket as blocked.

Tests cover:
- Marking ticket as blocked with reason
- Adding blocked label to GitHub issue
- Removing instance label
- Unassigning issue
- Adding blocking comment
- Updating workflow state

Following TDD: Write failing tests first, then implement.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMarkBlockedBasic:
    """Tests for basic mark_blocked functionality."""

    def test_mark_blocked_returns_result(self, tmp_path: Path):
        """Given a ticket ID and reason, mark_blocked returns a result dict."""
        from commands.mark_blocked import mark_blocked

        # Setup state file
        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            # Mock gh CLI returning empty list (no GitHub issue found)
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[]",
                stderr=""
            )
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        assert isinstance(result, dict)
        assert "blocked_ticket" in result
        assert result["blocked_ticket"] == "TASK-001"
        assert result["reason"] == "Test failure"

    def test_mark_blocked_requires_ticket_id(self, tmp_path: Path):
        """Given empty ticket_id, mark_blocked raises ValueError."""
        from commands.mark_blocked import mark_blocked

        state_file = tmp_path / "workflow-state.json"
        state_file.write_text("{}")

        with pytest.raises(ValueError, match="ticket_id.*required"):
            mark_blocked(ticket_id="", reason="Test", state_file=state_file)

    def test_mark_blocked_requires_reason(self, tmp_path: Path):
        """Given empty reason, mark_blocked uses default reason."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="",  # Empty reason
                state_file=state_file,
            )

        # Should use a default reason
        assert result["reason"] != ""
        assert "reason" in result["reason"].lower() or result["reason"] == "Unknown reason"


class TestMarkBlockedStateUpdate:
    """Tests for state file updates when marking blocked."""

    def test_mark_blocked_updates_ticket_status(self, tmp_path: Path):
        """Given a ticket, mark_blocked updates its status to blocked in state file."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        updated_state = load_workflow_state(state_file)
        assert updated_state.tickets[0].status == "blocked"

    def test_mark_blocked_records_block_reason(self, tmp_path: Path):
        """Given a reason, mark_blocked stores it in the ticket's block_reason."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Validation failed",
                state_file=state_file,
            )

        updated_state = load_workflow_state(state_file)
        assert updated_state.tickets[0].block_reason == "Validation failed"

    def test_mark_blocked_increments_blocked_count(self, tmp_path: Path):
        """Given a ticket is blocked, mark_blocked increments blocked_count."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        updated_state = load_workflow_state(state_file)
        assert updated_state.blocked_count == 1

    def test_mark_blocked_clears_current_ticket(self, tmp_path: Path):
        """Given current_ticket is the blocked ticket, mark_blocked clears it."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        updated_state = load_workflow_state(state_file)
        assert updated_state.current_ticket is None


class TestMarkBlockedGitHub:
    """Tests for GitHub operations when marking blocked."""

    def test_mark_blocked_looks_up_issue_by_ticket_id(self, tmp_path: Path):
        """Given no issue number, mark_blocked looks up the issue by ticket ID."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            # Return an issue that matches the ticket ID
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([
                    {"number": 42, "title": "[TASK-001] Test ticket"},
                ]),
                stderr=""
            )
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        assert result["issue_number"] == 42

    def test_mark_blocked_uses_provided_issue_number(self, tmp_path: Path):
        """Given issue_number is provided, mark_blocked uses it directly."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
                issue_number=99,
            )

        assert result["issue_number"] == 99

    def test_mark_blocked_adds_blocked_label(self, tmp_path: Path):
        """Given an issue exists, mark_blocked adds the 'blocked' label."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
                issue_number=42,
            )

        # Check that gh issue edit --add-label blocked was called
        calls = [str(call) for call in mock_run.call_args_list]
        add_label_called = any("--add-label" in str(call) and "blocked" in str(call) for call in calls)
        assert add_label_called, f"Expected --add-label blocked call, got: {calls}"

    def test_mark_blocked_adds_comment(self, tmp_path: Path):
        """Given an issue exists, mark_blocked adds a comment with the reason."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Validation failed",
                state_file=state_file,
                issue_number=42,
            )

        # Check that gh issue comment was called
        calls = [str(call) for call in mock_run.call_args_list]
        comment_called = any("issue" in str(call) and "comment" in str(call) for call in calls)
        assert comment_called, f"Expected gh issue comment call, got: {calls}"

    def test_mark_blocked_unassigns_issue(self, tmp_path: Path):
        """Given an issue exists, mark_blocked unassigns it."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
                issue_number=42,
            )

        # Check that gh issue edit --remove-assignee was called
        calls = [str(call) for call in mock_run.call_args_list]
        unassign_called = any("--remove-assignee" in str(call) for call in calls)
        assert unassign_called, f"Expected --remove-assignee call, got: {calls}"

    def test_mark_blocked_removes_instance_label(self, tmp_path: Path):
        """Given an instance label is configured, mark_blocked removes it."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch.dict("os.environ", {"RALPH_LABEL": "ralph-1"}):
                mark_blocked(
                    ticket_id="TASK-001",
                    reason="Test failure",
                    state_file=state_file,
                    issue_number=42,
                )

        # Check that gh issue edit --remove-label ralph-1 was called
        calls = [str(call) for call in mock_run.call_args_list]
        remove_label_called = any("--remove-label" in str(call) for call in calls)
        assert remove_label_called, f"Expected --remove-label call, got: {calls}"


class TestMarkBlockedWithoutGitHub:
    """Tests for mark_blocked when GitHub issue is not found."""

    def test_mark_blocked_handles_no_issue_found(self, tmp_path: Path):
        """Given no matching GitHub issue, mark_blocked still updates state."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            # gh issue list returns empty array
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        # State should still be updated
        updated_state = load_workflow_state(state_file)
        assert updated_state.tickets[0].status == "blocked"
        assert result["issue_number"] is None

    def test_mark_blocked_handles_gh_cli_error(self, tmp_path: Path):
        """Given gh CLI fails, mark_blocked still updates state and continues."""
        from commands.mark_blocked import mark_blocked
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            # gh CLI fails
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not authenticated")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        # State should still be updated
        updated_state = load_workflow_state(state_file)
        assert updated_state.tickets[0].status == "blocked"


class TestMarkBlockedErrorCases:
    """Tests for error handling in mark_blocked."""

    def test_mark_blocked_raises_on_missing_state_file(self, tmp_path: Path):
        """Given missing state file, mark_blocked raises FileNotFoundError."""
        from commands.mark_blocked import mark_blocked

        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=missing_file,
            )

    def test_mark_blocked_raises_on_ticket_not_found(self, tmp_path: Path):
        """Given ticket not in state, mark_blocked raises ValueError."""
        from commands.mark_blocked import mark_blocked

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(ValueError, match="Ticket.*not found"):
            with patch("commands.mark_blocked.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                mark_blocked(
                    ticket_id="TASK-INVALID",
                    reason="Test failure",
                    state_file=state_file,
                )
