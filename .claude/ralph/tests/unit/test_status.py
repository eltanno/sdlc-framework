"""Unit tests for status command.

Tests for:
- Status display with active workflow
- Status display with no workflow
- Ticket counts by status
- Active ticket highlighting
"""

import json
import re
from pathlib import Path


from commands.status import (
    StatusResult,
    get_workflow_status,
    format_status_display,
)


class TestGetWorkflowStatus:
    """Tests for get_workflow_status function."""

    def test_returns_not_initialized_when_no_state_file(self, tmp_path: Path) -> None:
        """Given no state file exists, should return not initialized status."""
        state_file = tmp_path / "nonexistent.json"

        result = get_workflow_status(state_file)

        assert result.initialized is False
        assert result.tickets_by_status == {}
        assert result.current_ticket is None

    def test_returns_ticket_counts_by_status(self, tmp_path: Path) -> None:
        """Given an active workflow, should return ticket counts by status."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "completed", "dependencies": []},
                {"id": "TASK-002", "title": "Task 2", "status": "completed", "dependencies": []},
                {"id": "TASK-003", "title": "Task 3", "status": "in_progress", "dependencies": []},
                {"id": "TASK-004", "title": "Task 4", "status": "pending", "dependencies": []},
                {"id": "TASK-005", "title": "Task 5", "status": "pending", "dependencies": []},
                {"id": "TASK-006", "title": "Task 6", "status": "pending", "dependencies": []},
                {"id": "TASK-007", "title": "Task 7", "status": "blocked", "dependencies": [], "block_reason": "Depends on external API"},
            ],
            "current_ticket": "TASK-003",
            "completed_count": 2,
            "blocked_count": 1,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.initialized is True
        assert result.tickets_by_status["completed"] == 2
        assert result.tickets_by_status["in_progress"] == 1
        assert result.tickets_by_status["pending"] == 3
        assert result.tickets_by_status["blocked"] == 1

    def test_returns_current_ticket_when_in_progress(self, tmp_path: Path) -> None:
        """Given a ticket is in progress, should return current ticket info."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Implement feature X", "status": "in_progress", "dependencies": [], "attempts": 2},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.current_ticket is not None
        assert result.current_ticket["id"] == "TASK-001"
        assert result.current_ticket["title"] == "Implement feature X"
        assert result.current_ticket["attempts"] == 2

    def test_returns_total_ticket_count(self, tmp_path: Path) -> None:
        """Given an active workflow, should return total ticket count."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "completed", "dependencies": []},
                {"id": "TASK-002", "title": "Task 2", "status": "pending", "dependencies": []},
                {"id": "TASK-003", "title": "Task 3", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 1,
            "blocked_count": 0,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.total_tickets == 3

    def test_returns_blocked_tickets_with_reasons(self, tmp_path: Path) -> None:
        """Given blocked tickets exist, should return them with reasons."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "blocked", "dependencies": [], "block_reason": "Missing API key"},
                {"id": "TASK-002", "title": "Task 2", "status": "blocked", "dependencies": [], "block_reason": "Needs database migration"},
                {"id": "TASK-003", "title": "Task 3", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 2,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert len(result.blocked_tickets) == 2
        assert result.blocked_tickets[0]["id"] == "TASK-001"
        assert result.blocked_tickets[0]["block_reason"] == "Missing API key"
        assert result.blocked_tickets[1]["id"] == "TASK-002"
        assert result.blocked_tickets[1]["block_reason"] == "Needs database migration"

    def test_returns_prd_and_plan_paths(self, tmp_path: Path) -> None:
        """Given an active workflow, should return PRD and plan paths."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/feature-x.md",
            "plan_path": "docs/plans/feature-x.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.prd_path == "docs/prds/feature-x.md"
        assert result.plan_path == "docs/plans/feature-x.md"


class TestFormatStatusDisplay:
    """Tests for format_status_display function."""

    def test_displays_no_workflow_message_when_not_initialized(self) -> None:
        """Given no workflow exists, should display not initialized message."""
        result = StatusResult(
            initialized=False,
            tickets_by_status={},
            total_tickets=0,
            current_ticket=None,
            blocked_tickets=[],
            prd_path=None,
            plan_path=None,
        )

        output = format_status_display(result)

        # Should show a clear "no workflow" message as the primary content
        # Verify it's not just buried in output but is the main message
        assert re.search(r"(no\s+(active\s+)?workflow|not\s+initialized)", output, re.IGNORECASE)
        # Should NOT show ticket counts or other workflow details
        assert not re.search(r"(completed|in.progress|pending|blocked):\s*\d+", output, re.IGNORECASE)

    def test_displays_ticket_counts_when_active(self) -> None:
        """Given an active workflow, should display ticket counts."""
        result = StatusResult(
            initialized=True,
            tickets_by_status={
                "completed": 5,
                "in_progress": 1,
                "pending": 10,
                "blocked": 2,
            },
            total_tickets=18,
            current_ticket=None,
            blocked_tickets=[],
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
        )

        output = format_status_display(result)

        # Verify each status label is associated with correct count
        # Use regex to ensure counts appear with their labels, not just anywhere
        assert re.search(r"completed[:\s]+5", output, re.IGNORECASE)
        assert re.search(r"in.progress[:\s]+1", output, re.IGNORECASE)
        assert re.search(r"pending[:\s]+10", output, re.IGNORECASE)
        assert re.search(r"blocked[:\s]+2", output, re.IGNORECASE)
        # Verify total is displayed (as "Progress: X/18" or similar)
        assert re.search(r"(total|progress|all)[:\s]+\d+/18", output, re.IGNORECASE)

    def test_highlights_current_ticket_when_in_progress(self) -> None:
        """Given a ticket is in progress, should highlight it."""
        result = StatusResult(
            initialized=True,
            tickets_by_status={"in_progress": 1, "pending": 5},
            total_tickets=6,
            current_ticket={
                "id": "TASK-042",
                "title": "Implement authentication",
                "attempts": 1,
            },
            blocked_tickets=[],
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
        )

        output = format_status_display(result)

        # Verify current ticket section exists
        # Format is "Current Ticket:" header followed by ID/Title/Attempts
        assert re.search(r"current\s+ticket", output, re.IGNORECASE)
        # Verify title and ID are in current ticket section (extract section between headers)
        current_section = re.search(r"current\s+ticket:.*?(ticket\s+status:|={5,}|$)", output, re.IGNORECASE | re.DOTALL)
        assert current_section is not None
        section_text = current_section.group(0)
        assert "TASK-042" in section_text
        assert "Implement authentication" in section_text
        # Verify attempts is displayed in the same section
        assert re.search(r"attempts?[:\s]+1", section_text, re.IGNORECASE)

    def test_displays_blocked_tickets_with_reasons(self) -> None:
        """Given blocked tickets exist, should display them with reasons."""
        result = StatusResult(
            initialized=True,
            tickets_by_status={"blocked": 2, "pending": 3},
            total_tickets=5,
            current_ticket=None,
            blocked_tickets=[
                {"id": "TASK-001", "block_reason": "Waiting for API access"},
                {"id": "TASK-002", "block_reason": "Dependency not resolved"},
            ],
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
        )

        output = format_status_display(result)

        # Verify each blocked ticket is associated with its reason
        # TASK-001 should be near its reason (same line or adjacent lines)
        assert re.search(r"TASK-001[^\n]{0,100}Waiting for API access", output, re.IGNORECASE) or \
               re.search(r"Waiting for API access[^\n]{0,100}TASK-001", output, re.IGNORECASE)
        # TASK-002 should be near its reason
        assert re.search(r"TASK-002[^\n]{0,100}Dependency not resolved", output, re.IGNORECASE) or \
               re.search(r"Dependency not resolved[^\n]{0,100}TASK-002", output, re.IGNORECASE)
        # Verify there's a blocked tickets section
        assert re.search(r"blocked", output, re.IGNORECASE)


class TestStatusResultDataclass:
    """Tests for StatusResult dataclass."""

    def test_to_dict_returns_serializable_dict(self) -> None:
        """StatusResult.to_dict should return a JSON-serializable dictionary."""
        result = StatusResult(
            initialized=True,
            tickets_by_status={"completed": 2, "pending": 3},
            total_tickets=5,
            current_ticket={"id": "TASK-001", "title": "Test", "attempts": 1},
            blocked_tickets=[{"id": "TASK-002", "block_reason": "Blocked"}],
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
        )

        data = result.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(data)
        assert json_str is not None

        # Verify ALL fields are present and correctly serialized
        assert data["initialized"] is True
        assert data["tickets_by_status"]["completed"] == 2
        assert data["tickets_by_status"]["pending"] == 3
        assert data["total_tickets"] == 5
        assert data["current_ticket"]["id"] == "TASK-001"
        assert data["current_ticket"]["title"] == "Test"
        assert data["current_ticket"]["attempts"] == 1
        assert len(data["blocked_tickets"]) == 1
        assert data["blocked_tickets"][0]["id"] == "TASK-002"
        assert data["blocked_tickets"][0]["block_reason"] == "Blocked"
        assert data["prd_path"] == "docs/prds/test.md"
        assert data["plan_path"] == "docs/plans/test.md"


class TestEdgeCases:
    """Edge case tests for status command."""

    def test_handles_invalid_json_state_file(self, tmp_path: Path) -> None:
        """Given corrupted state file, should return not initialized."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{ invalid json }")

        result = get_workflow_status(state_file)

        # Verify ALL fields are safe defaults, not just initialized
        assert result.initialized is False
        assert result.tickets_by_status == {}
        assert result.total_tickets == 0
        assert result.current_ticket is None
        assert result.blocked_tickets == []
        assert result.prd_path is None
        assert result.plan_path is None

    def test_handles_empty_tickets_list(self, tmp_path: Path) -> None:
        """Given workflow with no tickets, should return empty counts."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.initialized is True
        assert result.total_tickets == 0
        assert result.tickets_by_status == {}

    def test_handles_missing_optional_fields(self, tmp_path: Path) -> None:
        """Given state file with minimal fields, should handle gracefully."""
        state_data = {
            "tickets": [
                {"id": "TASK-001", "title": "Task", "status": "pending"},
            ],
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.initialized is True
        assert result.total_tickets == 1
        assert result.prd_path is None
        assert result.plan_path is None

    def test_handles_blocked_ticket_without_reason(self, tmp_path: Path) -> None:
        """Given blocked ticket without reason, should provide a default."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "blocked", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert len(result.blocked_tickets) == 1
        # Verify a default reason is provided (don't hardcode exact string)
        assert result.blocked_tickets[0]["block_reason"]  # truthy check
        assert len(result.blocked_tickets[0]["block_reason"]) > 0

    def test_handles_current_ticket_not_in_tickets_list(self, tmp_path: Path) -> None:
        """Given current_ticket ID that doesn't match any ticket, should return None."""
        state_data = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Task 1", "status": "pending", "dependencies": []},
            ],
            "current_ticket": "TASK-999",  # Doesn't exist in tickets list
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(state_data))

        result = get_workflow_status(state_file)

        assert result.current_ticket is None
