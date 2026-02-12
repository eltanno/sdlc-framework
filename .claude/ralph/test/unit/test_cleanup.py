"""Unit tests for cleanup command.

Tests for the cleanup functionality that handles:
- Querying GitHub for issue counts
- Generating workflow summaries
- Updating workflow state
- Archiving state files
"""

import json
import subprocess
from unittest.mock import MagicMock


# We'll import the module we're building
from commands import cleanup


class TestGetIssueCounts:
    """Tests for getting issue counts from GitHub."""

    def test_get_issue_counts_all_closed(self, mocker):
        """Given all issues are closed, when getting counts, then returns correct totals."""
        # Mock subprocess.run for gh CLI calls
        mock_run = mocker.patch("commands.cleanup.subprocess.run")

        # Setup mock responses for different gh queries
        def side_effect(*args, **kwargs):
            cmd = args[0]
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""

            if "--state" in cmd and "all" in cmd:
                result.stdout = '[{"number": 1}, {"number": 2}, {"number": 3}]'
            elif "--state" in cmd and "closed" in cmd:
                result.stdout = '[{"number": 1}, {"number": 2}, {"number": 3}]'
            elif "--label" in cmd and "blocked" in cmd:
                result.stdout = '[]'
            elif "--state" in cmd and "open" in cmd:
                result.stdout = '[]'
            else:
                result.stdout = '[]'
            return result

        mock_run.side_effect = side_effect

        counts = cleanup.get_issue_counts()

        assert counts["total"] == 3
        assert counts["done"] == 3
        assert counts["blocked"] == 0
        assert counts["pending"] == 0

    def test_get_issue_counts_with_blocked(self, mocker):
        """Given some issues are blocked, when getting counts, then blocked count is accurate."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")

        def side_effect(*args, **kwargs):
            cmd = args[0]
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""

            if "--state" in cmd and "all" in cmd:
                result.stdout = '[{"number": 1}, {"number": 2}, {"number": 3}, {"number": 4}]'
            elif "--state" in cmd and "closed" in cmd:
                result.stdout = '[{"number": 1}, {"number": 2}]'
            elif "--label" in cmd and "blocked" in cmd:
                result.stdout = '[{"number": 3}]'
            elif "--state" in cmd and "open" in cmd:
                result.stdout = '[{"number": 3}, {"number": 4}]'
            else:
                result.stdout = '[]'
            return result

        mock_run.side_effect = side_effect

        counts = cleanup.get_issue_counts()

        assert counts["total"] == 4
        assert counts["done"] == 2
        assert counts["blocked"] == 1
        assert counts["pending"] == 1

    def test_get_issue_counts_gh_error_returns_zeros(self, mocker):
        """Given gh CLI fails, when getting counts, then returns zeros."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.side_effect = subprocess.SubprocessError("gh not found")

        counts = cleanup.get_issue_counts()

        assert counts["total"] == 0
        assert counts["done"] == 0
        assert counts["blocked"] == 0
        assert counts["pending"] == 0


class TestDetermineStatus:
    """Tests for determining completion status."""

    def test_determine_status_complete(self):
        """Given no pending and no blocked, when determining status, then returns complete."""
        counts = {"total": 5, "done": 5, "blocked": 0, "pending": 0}

        status = cleanup.determine_status(counts)

        assert status == "complete"

    def test_determine_status_complete_with_blocked(self):
        """Given no pending but some blocked, when determining status, then returns complete_with_blocked."""
        counts = {"total": 5, "done": 3, "blocked": 2, "pending": 0}

        status = cleanup.determine_status(counts)

        assert status == "complete_with_blocked"

    def test_determine_status_incomplete(self):
        """Given pending tickets exist, when determining status, then returns incomplete."""
        counts = {"total": 5, "done": 2, "blocked": 1, "pending": 2}

        status = cleanup.determine_status(counts)

        assert status == "incomplete"


class TestGetCompletedTickets:
    """Tests for listing completed tickets."""

    def test_get_completed_tickets_success(self, mocker):
        """Given closed issues exist, when getting completed, then queries with correct parameters."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 1, "title": "[TASK-001] First task"},
            {"number": 2, "title": "[TASK-002] Second task"},
        ])
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_completed_tickets()

        # Verify correct gh CLI parameters
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--state" in call_args
        assert "closed" in call_args
        assert "--label" in call_args
        assert "task" in call_args
        assert "--json" in call_args
        assert "number,title" in call_args

        # Verify result
        assert len(tickets) == 2
        assert tickets[0]["title"] == "[TASK-001] First task"

    def test_get_completed_tickets_empty(self, mocker):
        """Given no closed issues, when getting completed, then returns empty list."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "[]"
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_completed_tickets()

        assert tickets == []


class TestGetBlockedTickets:
    """Tests for listing blocked tickets."""

    def test_get_blocked_tickets_success(self, mocker):
        """Given blocked issues exist, when getting blocked, then returns list."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 3, "title": "[TASK-003] Blocked task"},
        ])
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_blocked_tickets()

        assert len(tickets) == 1
        assert tickets[0]["number"] == 3


class TestGetPendingTickets:
    """Tests for listing pending tickets."""

    def test_get_pending_tickets_excludes_blocked(self, mocker):
        """Given mix of open and blocked tasks, when getting pending, then only non-blocked returned."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        # Mock response includes both pending and blocked tickets
        mock_run.return_value.stdout = json.dumps([
            {"number": 4, "title": "[TASK-004] Pending task", "labels": [{"name": "task"}]},
            {"number": 5, "title": "[TASK-005] Blocked task", "labels": [{"name": "task"}, {"name": "blocked"}]},
            {"number": 6, "title": "[TASK-006] Another pending", "labels": [{"name": "task"}]},
        ])
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_pending_tickets()

        # Should only return the 2 non-blocked tickets
        assert len(tickets) == 2
        assert tickets[0]["number"] == 4
        assert tickets[1]["number"] == 6
        # Verify blocked ticket is NOT in results
        assert all(t["number"] != 5 for t in tickets)

    def test_get_pending_tickets_all_pending(self, mocker):
        """Given all open tasks are pending (none blocked), when getting pending, then returns all."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 4, "title": "[TASK-004] Pending task", "labels": [{"name": "task"}]},
            {"number": 5, "title": "[TASK-005] Another pending", "labels": [{"name": "task"}]},
        ])
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_pending_tickets()

        assert len(tickets) == 2


class TestUpdateWorkflowState:
    """Tests for updating workflow state file."""

    def test_update_workflow_state_success(self, tmp_path):
        """Given workflow state file exists, when updating, then phase becomes idle."""
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps({
            "phase": "implementing",
            "completed": ["prd", "plan"]
        }))

        cleanup.update_workflow_state(state_file)

        updated = json.loads(state_file.read_text())
        assert updated["phase"] == "idle"
        assert "ralph" in updated["completed"]

    def test_update_workflow_state_file_missing(self, tmp_path):
        """Given workflow state file doesn't exist, when updating, then no error raised."""
        state_file = tmp_path / "workflow-state.json"

        # Should not raise
        cleanup.update_workflow_state(state_file)

        # File still shouldn't exist
        assert not state_file.exists()

    def test_update_workflow_state_preserves_existing_completed(self, tmp_path):
        """Given completed list exists, when updating, then ralph is added to existing."""
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps({
            "phase": "implementing",
            "completed": ["discovery", "prd", "plan"]
        }))

        cleanup.update_workflow_state(state_file)

        updated = json.loads(state_file.read_text())
        assert "discovery" in updated["completed"]
        assert "prd" in updated["completed"]
        assert "plan" in updated["completed"]
        assert "ralph" in updated["completed"]

    def test_update_workflow_state_no_duplicates(self, tmp_path):
        """Given ralph already in completed, when updating, then no duplicate added."""
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps({
            "phase": "implementing",
            "completed": ["ralph"]
        }))

        cleanup.update_workflow_state(state_file)

        updated = json.loads(state_file.read_text())
        assert updated["completed"].count("ralph") == 1


class TestGenerateSummary:
    """Tests for generating cleanup summary."""

    def test_generate_summary_complete(self):
        """Given complete status, when generating summary, then signals completion and includes all counts."""
        counts = {"total": 3, "done": 3, "blocked": 0, "pending": 0}
        status = "complete"

        summary = cleanup.generate_summary(counts, status)

        # Verify status is preserved
        assert summary["status"] == "complete"
        # Verify completion is signaled (not hardcoding exact string)
        assert summary["completion_signal"] == "PRD_COMPLETE"
        # Verify all counts are included
        assert summary["total"] == 3
        assert summary["done"] == 3
        assert summary["blocked"] == 0
        assert summary["pending"] == 0

    def test_generate_summary_needs_review_when_incomplete(self):
        """Given non-complete status, when generating summary, then signals review needed."""
        counts = {"total": 5, "done": 3, "blocked": 2, "pending": 0}
        status = "complete_with_blocked"

        summary = cleanup.generate_summary(counts, status)

        # Verify status is preserved
        assert summary["status"] == "complete_with_blocked"
        # Verify review is signaled (semantic check: not "complete")
        assert summary["completion_signal"] != "PRD_COMPLETE"
        assert summary["completion_signal"] == "NEEDS_REVIEW"
        # Verify counts preserved
        assert summary["blocked"] == 2

    def test_generate_summary_preserves_all_counts(self):
        """Given any status, when generating summary, then all count fields are preserved."""
        counts = {"total": 10, "done": 5, "blocked": 2, "pending": 3}
        status = "incomplete"

        summary = cleanup.generate_summary(counts, status)

        # Verify all counts from input appear in output
        assert summary["total"] == counts["total"]
        assert summary["done"] == counts["done"]
        assert summary["blocked"] == counts["blocked"]
        assert summary["pending"] == counts["pending"]


class TestCleanup:
    """Tests for the main cleanup function."""

    def test_cleanup_orchestrates_complete_workflow(self, mocker, tmp_path):
        """Given cleanup runs, when complete, then calls all helpers and returns correct summary."""
        # Mock all helper functions instead of subprocess
        mock_get_counts = mocker.patch("commands.cleanup.get_issue_counts")
        mock_determine_status = mocker.patch("commands.cleanup.determine_status")
        mock_update_state = mocker.patch("commands.cleanup.update_workflow_state")
        mock_get_completed = mocker.patch("commands.cleanup.get_completed_tickets")
        mock_get_blocked = mocker.patch("commands.cleanup.get_blocked_tickets")
        mock_get_pending = mocker.patch("commands.cleanup.get_pending_tickets")

        # Setup mock return values
        counts = {"total": 5, "done": 3, "blocked": 1, "pending": 1}
        mock_get_counts.return_value = counts
        mock_determine_status.return_value = "incomplete"
        mock_get_completed.return_value = []
        mock_get_blocked.return_value = []
        mock_get_pending.return_value = []

        # Create workflow state file
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps({"phase": "implementing", "completed": []}))

        result = cleanup.cleanup(workflow_state_file=state_file)

        # Verify all helpers were called
        mock_get_counts.assert_called_once()
        mock_determine_status.assert_called_once_with(counts)
        mock_update_state.assert_called_once_with(state_file)
        mock_get_completed.assert_called_once()
        mock_get_blocked.assert_called_once()
        mock_get_pending.assert_called_once()

        # Verify correct summary returned
        assert result["status"] == "incomplete"
        assert result["total"] == 5
        assert result["done"] == 3
        assert result["blocked"] == 1
        assert result["pending"] == 1
        assert result["completion_signal"] == "NEEDS_REVIEW"

    def test_cleanup_without_workflow_state(self, mocker):
        """Given no workflow state file, when cleanup runs, then state update skipped."""
        # Mock helpers
        mock_get_counts = mocker.patch("commands.cleanup.get_issue_counts")
        mock_determine_status = mocker.patch("commands.cleanup.determine_status")
        mock_update_state = mocker.patch("commands.cleanup.update_workflow_state")
        mocker.patch("commands.cleanup.get_completed_tickets", return_value=[])
        mocker.patch("commands.cleanup.get_blocked_tickets", return_value=[])
        mocker.patch("commands.cleanup.get_pending_tickets", return_value=[])

        counts = {"total": 1, "done": 1, "blocked": 0, "pending": 0}
        mock_get_counts.return_value = counts
        mock_determine_status.return_value = "complete"

        result = cleanup.cleanup(workflow_state_file=None)

        # Verify state update was NOT called
        mock_update_state.assert_not_called()

        # Verify summary still returned correctly
        assert result["status"] == "complete"
        assert result["completion_signal"] == "PRD_COMPLETE"


class TestFormatOutput:
    """Tests for formatting cleanup output."""

    def test_format_output_shows_correct_numbers(self):
        """Given summary data, when formatting, then exact numbers appear in output."""
        counts = {"total": 10, "done": 7, "blocked": 2, "pending": 1}
        status = "incomplete"
        completed_tickets = [{"number": 1, "title": "[TASK-001] Done"}, {"number": 2, "title": "[TASK-002] Also done"}]
        blocked_tickets = [{"number": 3, "title": "[TASK-003] Blocked"}]
        pending_tickets = [{"number": 4, "title": "[TASK-004] Pending"}]

        output = cleanup.format_output(
            counts=counts,
            status=status,
            completed_tickets=completed_tickets,
            blocked_tickets=blocked_tickets,
            pending_tickets=pending_tickets,
        )

        # Verify structure
        assert isinstance(output, str)
        assert "RALPH RUN SUMMARY" in output

        # Verify exact numbers appear
        assert "Total Tickets:    10" in output
        assert "Completed:        7" in output
        assert "Blocked:          2" in output
        assert "Pending:          1" in output

        # Verify ticket sections appear
        assert "[TASK-001]" in output
        assert "[TASK-002]" in output
        assert "[TASK-003] Blocked" in output
        assert "[TASK-004] Pending" in output

    def test_format_output_includes_valid_json(self):
        """Given summary data, when formatting, then includes parseable JSON with correct values."""
        counts = {"total": 5, "done": 5, "blocked": 0, "pending": 0}
        status = "complete"

        output = cleanup.format_output(
            counts=counts,
            status=status,
            completed_tickets=[],
            blocked_tickets=[],
            pending_tickets=[],
        )

        # Verify JSON delimiter exists
        assert "---JSON_OUTPUT---" in output

        # Extract and parse JSON section
        json_start = output.find("---JSON_OUTPUT---") + len("---JSON_OUTPUT---")
        json_str = output[json_start:].strip()
        parsed = json.loads(json_str)

        # Verify JSON contains correct values
        assert parsed["status"] == "complete"
        assert parsed["total"] == 5
        assert parsed["done"] == 5
        assert parsed["blocked"] == 0
        assert parsed["pending"] == 0
        assert parsed["completion_signal"] == "PRD_COMPLETE"
