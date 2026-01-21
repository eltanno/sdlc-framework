"""Unit tests for commands/ticket_done.py - Ticket completion module.

Tests cover:
- Issue lookup by ticket ID
- Label removal from issues
- Issue closing
- State file updates
- Progress reporting

Following TDD: Write failing tests first, then implement.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestMarkTicketDone:
    """Tests for the mark_ticket_done function."""

    def test_mark_ticket_done_updates_state_file(self, tmp_path: Path):
        """Given a ticket in progress, marking it done updates state to completed."""
        from commands.ticket_done import mark_ticket_done

        # Setup state file with an in_progress ticket
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test ticket", "status": "in_progress", "dependencies": []},
                {"id": "TASK-002", "title": "Second ticket", "status": "pending", "dependencies": ["TASK-001"]},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        # Verify state file was updated
        updated_state = json.loads(state_file.read_text())
        assert updated_state["tickets"][0]["status"] == "completed"
        assert updated_state["completed_count"] == 1
        assert updated_state["current_ticket"] is None

        # Verify result
        assert result["ticket_id"] == "TASK-001"
        assert result["status"] == "completed"

    def test_mark_ticket_done_clears_current_ticket(self, tmp_path: Path):
        """Given a current ticket, marking it done clears the current_ticket field."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mark_ticket_done("TASK-001", state_file=state_file)

        updated_state = json.loads(state_file.read_text())
        assert updated_state["current_ticket"] is None

    def test_mark_ticket_done_records_pr_number(self, tmp_path: Path):
        """Given a PR number, marking done records it in the ticket."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", pr_number="123", state_file=state_file)

        assert result["pr_number"] == "123"

    def test_mark_ticket_done_returns_progress_info(self, tmp_path: Path):
        """Given tickets, marking done returns progress information."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test 1", "status": "completed", "dependencies": []},
                {"id": "TASK-002", "title": "Test 2", "status": "in_progress", "dependencies": []},
                {"id": "TASK-003", "title": "Test 3", "status": "pending", "dependencies": []},
            ],
            "current_ticket": "TASK-002",
            "completed_count": 1,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-002", state_file=state_file)

        assert result["progress"]["current"] == 2  # Now 2 completed
        assert result["progress"]["total"] == 3
        assert result["progress"]["remaining"] == 1

    def test_mark_ticket_done_missing_ticket_raises_error(self, tmp_path: Path):
        """Given a non-existent ticket ID, marking done raises ValueError."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(ValueError, match="Ticket.*not found"):
            mark_ticket_done("TASK-999", state_file=state_file)

    def test_mark_ticket_done_missing_state_file_raises_error(self, tmp_path: Path):
        """Given a missing state file, marking done raises FileNotFoundError."""
        from commands.ticket_done import mark_ticket_done

        missing_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            mark_ticket_done("TASK-001", state_file=missing_file)

    def test_mark_ticket_done_returns_next_ticket(self, tmp_path: Path):
        """Given remaining pending tickets, returns the next one."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test 1", "status": "in_progress", "dependencies": []},
                {"id": "TASK-002", "title": "Test 2", "status": "pending", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        # Should indicate next ticket
        assert result["next_ticket"] == "TASK-002"

    def test_mark_ticket_done_all_done_flag(self, tmp_path: Path):
        """Given last ticket completed, returns all_done=True."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        assert result["all_done"] is True


class TestGitHubIssueOperations:
    """Tests for GitHub issue operations in ticket_done."""

    def test_close_github_issue_calls_gh_cli(self, mocker):
        """Given an issue number, close_github_issue calls gh CLI correctly."""
        from commands.ticket_done import close_github_issue

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        close_github_issue(123)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "gh" in call_args[0][0]
        assert "issue" in call_args[0][0]
        assert "close" in call_args[0][0]
        assert "123" in call_args[0][0]

    def test_close_github_issue_handles_already_closed(self, mocker):
        """Given already closed issue, close_github_issue doesn't raise error."""
        from commands.ticket_done import close_github_issue

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        # Simulate already closed (gh returns success)
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        # Should not raise
        close_github_issue(123)

    def test_close_github_issue_handles_missing_gh_cli(self, mocker):
        """Given gh CLI not installed, close_github_issue raises RuntimeError."""
        from commands.ticket_done import close_github_issue

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.side_effect = FileNotFoundError("gh not found")

        with pytest.raises(RuntimeError, match="gh CLI.*not.*found"):
            close_github_issue(123)

    def test_remove_label_from_issue_calls_gh_cli(self, mocker):
        """Given an issue and label, remove_label_from_issue calls gh CLI correctly."""
        from commands.ticket_done import remove_label_from_issue

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        remove_label_from_issue(123, "ralph-1")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "gh" in call_args[0][0]
        assert "issue" in call_args[0][0]
        assert "edit" in call_args[0][0]
        assert "123" in call_args[0][0]
        assert "--remove-label" in call_args[0][0]
        assert "ralph-1" in call_args[0][0]

    def test_remove_label_handles_label_not_present(self, mocker):
        """Given label not on issue, remove_label_from_issue doesn't raise."""
        from commands.ticket_done import remove_label_from_issue

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        # gh issue edit with --remove-label is idempotent, returns success even if label not present
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        # Should not raise
        remove_label_from_issue(123, "nonexistent-label")

    def test_find_issue_by_ticket_id_returns_number(self, mocker):
        """Given a ticket ID in issue title, find_issue_by_ticket_id returns issue number."""
        from commands.ticket_done import find_issue_by_ticket_id

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 42, "title": "[TASK-001] Implement feature"},
            {"number": 43, "title": "[TASK-002] Another feature"},
        ])
        mock_run.return_value.stderr = ""

        result = find_issue_by_ticket_id("TASK-001")

        assert result == 42

    def test_find_issue_by_ticket_id_returns_none_when_not_found(self, mocker):
        """Given ticket ID not in any issue, find_issue_by_ticket_id returns None."""
        from commands.ticket_done import find_issue_by_ticket_id

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps([
            {"number": 42, "title": "[TASK-999] Other feature"},
        ])
        mock_run.return_value.stderr = ""

        result = find_issue_by_ticket_id("TASK-001")

        assert result is None

    def test_find_issue_by_ticket_id_searches_open_and_closed(self, mocker):
        """Given ticket exists as closed issue, find_issue_by_ticket_id finds it."""
        from commands.ticket_done import find_issue_by_ticket_id

        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        # First call (open issues) returns empty
        # Second call (closed issues) returns the ticket
        mock_run.return_value.returncode = 0
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=json.dumps([]), stderr=""),  # open
            MagicMock(returncode=0, stdout=json.dumps([
                {"number": 42, "title": "[TASK-001] Feature"}
            ]), stderr=""),  # closed
        ]

        result = find_issue_by_ticket_id("TASK-001")

        assert result == 42
        assert mock_run.call_count == 2


class TestTicketDoneIntegration:
    """Integration tests for ticket_done with GitHub operations."""

    def test_ticket_done_closes_github_issue(self, tmp_path: Path, mocker):
        """Given GitHub config and issue, ticket_done closes the issue."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Setup config file with GitHub PM tool
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: github
ralph:
  instance_label: ralph-1
""")

        # Mock subprocess for gh commands
        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            config_file=config_file,
        )

        assert result["status"] == "completed"
        # Verify gh was called to close issue
        assert any("close" in str(c) for c in mock_run.call_args_list)

    def test_ticket_done_removes_instance_label(self, tmp_path: Path, mocker):
        """Given instance_label config, ticket_done removes the label first."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Setup config file with instance label
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: github
ralph:
  instance_label: ralph-1
""")

        # Mock subprocess for gh commands
        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            config_file=config_file,
        )

        # Verify label removal was called
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("--remove-label" in c and "ralph-1" in c for c in calls)

    def test_ticket_done_skips_github_when_not_configured(self, tmp_path: Path, mocker):
        """Given no GitHub config, ticket_done doesn't call gh CLI."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Setup config file without GitHub PM tool
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: trello
""")

        # Mock subprocess - should NOT be called
        mock_run = mocker.patch("commands.ticket_done.subprocess.run")

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            config_file=config_file,
        )

        assert result["status"] == "completed"
        # Verify gh was NOT called
        mock_run.assert_not_called()

    def test_ticket_done_looks_up_issue_when_not_in_state(self, tmp_path: Path, mocker):
        """Given issue_number not in state, ticket_done looks it up via gh CLI."""
        from commands.ticket_done import ticket_done

        # Setup state file without issue_number
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Setup config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: github
""")

        # Mock subprocess
        mock_run = mocker.patch("commands.ticket_done.subprocess.run")
        mock_run.side_effect = [
            # Issue list (open)
            MagicMock(returncode=0, stdout=json.dumps([
                {"number": 99, "title": "[TASK-001] Implement feature"}
            ]), stderr=""),
            # Label removal (may or may not be called)
            MagicMock(returncode=0, stdout="", stderr=""),
            # Issue close
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            config_file=config_file,
        )

        assert result["status"] == "completed"
        assert result.get("issue_number") == 99


class TestTicketDoneOutput:
    """Tests for ticket_done output format."""

    def test_ticket_done_returns_complete_result(self, tmp_path: Path, mocker):
        """Given successful completion, returns all expected fields."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
                {"id": "TASK-002", "title": "Next", "status": "pending", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # No config file - skip GitHub operations
        mocker.patch("commands.ticket_done.subprocess.run")

        result = ticket_done(
            ticket_id="TASK-001",
            pr_number="42",
            state_file=state_file,
            config_file=None,
        )

        # Check all expected fields
        assert "ticket_id" in result
        assert result["ticket_id"] == "TASK-001"
        assert "status" in result
        assert result["status"] == "completed"
        assert "pr_number" in result
        assert result["pr_number"] == "42"
        assert "progress" in result
        assert "current" in result["progress"]
        assert "total" in result["progress"]
        assert "remaining" in result["progress"]
        assert "next_ticket" in result
        assert "all_done" in result


class TestTicketDoneWithV2Format:
    """Tests for ticket_done with REAL v2 format (ralph.tickets as ID list).

    IMPORTANT: v2 format has:
    - tickets: [] (empty array)
    - ralph.tickets: ["TASK-001", "TASK-002"] (list of IDs only)
    - Status comes from PM tool, NOT from state file

    Earlier tests use v1 format (tickets array with full objects).
    These tests verify the real v2 format used in production.
    """

    def test_mark_ticket_done_v2_format_basic(self, tmp_path: Path):
        """Given REAL v2 format state file, mark_ticket_done updates correctly."""
        from commands.ticket_done import mark_ticket_done

        # REAL v2 format - tickets is empty, ralph.tickets has IDs only
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],  # Empty in v2!
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
            "ralph": {
                "tickets": ["TASK-001", "TASK-002", "TASK-003"],
                "dependencies": {},
                "attempts": {},
                "blocked": {},
                "source": "asana",
            },
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        assert result["ticket_id"] == "TASK-001"
        assert result["status"] == "completed"
        # v2 clears current_ticket
        updated = json.loads(state_file.read_text())
        assert updated["current_ticket"] is None

    def test_mark_ticket_done_v2_clears_blocked_if_present(self, tmp_path: Path):
        """Given v2 ticket was blocked, mark_ticket_done removes it from blocked dict."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
            "ralph": {
                "tickets": ["TASK-001", "TASK-002"],
                "dependencies": {},
                "attempts": {},
                "blocked": {"TASK-001": "was blocked for testing"},
                "source": "asana",
            },
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mark_ticket_done("TASK-001", state_file=state_file)

        updated = json.loads(state_file.read_text())
        assert "TASK-001" not in updated["ralph"]["blocked"]

    def test_mark_ticket_done_v2_raises_on_unknown_ticket(self, tmp_path: Path):
        """Given v2 format, mark_ticket_done raises if ticket not in ralph.tickets."""
        from commands.ticket_done import mark_ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
            "ralph": {
                "tickets": ["TASK-001"],
                "dependencies": {},
                "attempts": {},
                "blocked": {},
                "source": "asana",
            },
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(ValueError, match="not found"):
            mark_ticket_done("TASK-999", state_file=state_file)

    def test_ticket_done_v2_calls_pm_tool_with_ticket_id(self, tmp_path: Path):
        """Given REAL v2 format, ticket_done passes ticket_id (not issue_number) to PM tool."""
        from commands.ticket_done import ticket_done

        # REAL v2 format - no issue_number anywhere
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],
            "current_ticket": "SDLC-0070",
            "completed_count": 0,
            "blocked_count": 0,
            "ralph": {
                "tickets": ["SDLC-0067", "SDLC-0068", "SDLC-0069", "SDLC-0070"],
                "dependencies": {},
                "attempts": {},
                "blocked": {},
                "source": "asana",
            },
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Mock PM tool
        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True
        mock_pm.remove_label.return_value = True

        result = ticket_done(
            ticket_id="SDLC-0070",
            state_file=state_file,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        # PM tool should be called with ticket_id directly
        assert result["status"] == "completed"
        mock_pm.close_ticket.assert_called_once_with("SDLC-0070")
        mock_pm.remove_label.assert_called_once_with("SDLC-0070", "ralph-1")

    def test_ticket_done_v2_returns_limited_progress_info(self, tmp_path: Path):
        """Given v2 format, ticket_done returns limited progress (no remaining count)."""
        from commands.ticket_done import ticket_done

        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
            "ralph": {
                "tickets": ["TASK-001", "TASK-002", "TASK-003"],
                "dependencies": {},
                "attempts": {},
                "blocked": {},
                "source": "asana",
            },
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm,
        )

        # v2 returns total but remaining is None (can't know without PM query)
        assert result["total"] == 3
        assert result["remaining"] is None


class TestTicketDoneWithPMTool:
    """Tests for ticket_done integration with PMTool protocol."""

    def test_ticket_done_accepts_pm_tool_parameter(self, tmp_path: Path, mocker):
        """Given a pm_tool parameter, ticket_done accepts it without error."""
        from commands.ticket_done import ticket_done
        from core.pm import LocalPM

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create PM tool mock
        pm_tool = LocalPM()

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=pm_tool,
        )

        assert result["status"] == "completed"

    def test_ticket_done_calls_pm_tool_close_ticket(self, tmp_path: Path, mocker):
        """Given pm_tool, ticket_done calls close_ticket with issue number."""
        from commands.ticket_done import ticket_done

        # Setup state file with issue_number
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True
        mock_pm_tool.remove_label.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # PM tool is called with ticket_id, not issue_number
        mock_pm_tool.close_ticket.assert_called_once_with("TASK-001")

    def test_ticket_done_calls_pm_tool_remove_label(self, tmp_path: Path, mocker):
        """Given pm_tool and ralph_label, ticket_done removes the label first."""
        from commands.ticket_done import ticket_done

        # Setup state file with issue_number
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True
        mock_pm_tool.remove_label.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # PM tool is called with ticket_id, not issue_number
        mock_pm_tool.remove_label.assert_called_once_with("TASK-001", "ralph-1")

    def test_ticket_done_removes_label_before_closing(self, tmp_path: Path, mocker):
        """Given pm_tool and ralph_label, remove_label is called before close_ticket."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Track call order
        call_order = []
        mock_pm_tool = MagicMock()
        mock_pm_tool.remove_label.side_effect = lambda *args: call_order.append("remove_label") or True
        mock_pm_tool.close_ticket.side_effect = lambda *args: call_order.append("close_ticket") or True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        assert call_order == ["remove_label", "close_ticket"]

    def test_ticket_done_handles_already_closed_issue(self, tmp_path: Path, mocker):
        """Given pm_tool returns False for close, ticket_done still succeeds."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Mock PM tool that returns False for close (issue already closed)
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = False  # Already closed
        mock_pm_tool.remove_label.return_value = True

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # Should still complete successfully
        assert result["status"] == "completed"

    def test_ticket_done_calls_pm_tool_with_ticket_id_not_issue_number(self, tmp_path: Path, mocker):
        """Given pm_tool, ticket_done calls it with ticket_id directly (not issue_number)."""
        from commands.ticket_done import ticket_done

        # Setup state file WITHOUT issue_number (like v2 format)
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": []},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True
        mock_pm_tool.remove_label.return_value = True

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # Should call PM tool with ticket_id (not issue_number)
        assert result["status"] == "completed"
        mock_pm_tool.close_ticket.assert_called_once_with("TASK-001")
        mock_pm_tool.remove_label.assert_called_once_with("TASK-001", "ralph-1")

    def test_ticket_done_skips_remove_label_without_ralph_label(self, tmp_path: Path, mocker):
        """Given pm_tool but no ralph_label, ticket_done skips remove_label."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label=None,  # No label
        )

        # close_ticket should be called, but not remove_label
        mock_pm_tool.close_ticket.assert_called_once()
        mock_pm_tool.remove_label.assert_not_called()

    def test_ticket_done_preserves_attempt_count_in_state(self, tmp_path: Path, mocker):
        """Given ticket with attempt_count, ticket_done preserves it in state."""
        from commands.ticket_done import ticket_done

        # Setup state file with attempt_count
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {
                    "id": "TASK-001",
                    "title": "Test",
                    "status": "in_progress",
                    "dependencies": [],
                    "issue_number": 42,
                    "attempt_count": 3,
                },
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True
        mock_pm_tool.remove_label.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # Verify attempt_count is preserved in state
        updated_state = json.loads(state_file.read_text())
        assert updated_state["tickets"][0]["attempt_count"] == 3

    def test_ticket_done_uses_pm_tool_over_config_github(self, tmp_path: Path, mocker):
        """Given both pm_tool and github config, pm_tool takes precedence."""
        from commands.ticket_done import ticket_done

        # Setup state file
        state = {
            "version": "2.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "in_progress", "dependencies": [], "issue_number": 42},
            ],
            "current_ticket": "TASK-001",
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        # Setup config file with GitHub
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: github
ralph:
  instance_label: ralph-1
""")

        # Mock subprocess - should NOT be called when pm_tool is provided
        mock_run = mocker.patch("commands.ticket_done.subprocess.run")

        # Create mock PM tool
        mock_pm_tool = MagicMock()
        mock_pm_tool.close_ticket.return_value = True
        mock_pm_tool.remove_label.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            config_file=config_file,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-1",
        )

        # pm_tool should be called, not subprocess (gh CLI)
        mock_pm_tool.close_ticket.assert_called_once()
        mock_run.assert_not_called()
