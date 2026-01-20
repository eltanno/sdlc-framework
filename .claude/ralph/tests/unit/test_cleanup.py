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
        """Given closed issues exist, when getting completed, then returns list."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 1, "title": "[TASK-001] First task"},
            {"number": 2, "title": "[TASK-002] Second task"},
        ])
        mock_run.return_value.stderr = ""

        tickets = cleanup.get_completed_tickets()

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

    def test_get_pending_tickets_success(self, mocker):
        """Given open issues without blocked label exist, when getting pending, then returns list."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 4, "title": "[TASK-004] Pending task"},
            {"number": 5, "title": "[TASK-005] Another pending"},
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
        """Given complete status, when generating summary, then includes PRD_COMPLETE."""
        counts = {"total": 3, "done": 3, "blocked": 0, "pending": 0}
        status = "complete"

        summary = cleanup.generate_summary(counts, status)

        assert "PRD_COMPLETE" in summary["completion_signal"]
        assert summary["status"] == "complete"

    def test_generate_summary_complete_with_blocked(self):
        """Given complete with blocked, when generating summary, then indicates review needed."""
        counts = {"total": 5, "done": 3, "blocked": 2, "pending": 0}
        status = "complete_with_blocked"

        summary = cleanup.generate_summary(counts, status)

        assert "NEEDS_REVIEW" in summary["completion_signal"]
        assert summary["blocked"] == 2

    def test_generate_summary_incomplete(self):
        """Given incomplete status, when generating summary, then indicates review needed."""
        counts = {"total": 5, "done": 1, "blocked": 1, "pending": 3}
        status = "incomplete"

        summary = cleanup.generate_summary(counts, status)

        assert "NEEDS_REVIEW" in summary["completion_signal"]
        assert summary["pending"] == 3


class TestCleanup:
    """Tests for the main cleanup function."""

    def test_cleanup_returns_summary_dict(self, mocker, tmp_path):
        """Given cleanup runs, when complete, then returns summary dictionary."""
        # Mock all GitHub calls
        mock_run = mocker.patch("commands.cleanup.subprocess.run")

        def side_effect(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            result.stdout = "[]"
            return result

        mock_run.side_effect = side_effect

        # Create workflow state file
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps({"phase": "implementing", "completed": []}))

        result = cleanup.cleanup(workflow_state_file=state_file)

        assert isinstance(result, dict)
        assert "status" in result
        assert "total" in result
        assert "done" in result
        assert "blocked" in result
        assert "pending" in result
        assert "completion_signal" in result

    def test_cleanup_without_workflow_state(self, mocker):
        """Given no workflow state file, when cleanup runs, then still returns summary."""
        mock_run = mocker.patch("commands.cleanup.subprocess.run")

        def side_effect(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            result.stdout = '[{"number": 1}]'
            return result

        mock_run.side_effect = side_effect

        result = cleanup.cleanup()

        assert isinstance(result, dict)
        assert "status" in result


class TestFormatOutput:
    """Tests for formatting cleanup output."""

    def test_format_output_returns_string(self):
        """Given summary data, when formatting, then returns formatted string."""
        counts = {"total": 3, "done": 2, "blocked": 1, "pending": 0}
        status = "complete_with_blocked"
        completed_tickets = [{"number": 1, "title": "[TASK-001]"}, {"number": 2, "title": "[TASK-002]"}]
        blocked_tickets = [{"number": 3, "title": "[TASK-003]"}]
        pending_tickets = []

        output = cleanup.format_output(
            counts=counts,
            status=status,
            completed_tickets=completed_tickets,
            blocked_tickets=blocked_tickets,
            pending_tickets=pending_tickets,
        )

        assert isinstance(output, str)
        assert "RALPH RUN SUMMARY" in output
        assert "Total Tickets" in output

    def test_format_output_includes_json(self):
        """Given summary data, when formatting, then includes JSON output."""
        counts = {"total": 1, "done": 1, "blocked": 0, "pending": 0}
        status = "complete"

        output = cleanup.format_output(
            counts=counts,
            status=status,
            completed_tickets=[],
            blocked_tickets=[],
            pending_tickets=[],
        )

        assert "---JSON_OUTPUT---" in output
