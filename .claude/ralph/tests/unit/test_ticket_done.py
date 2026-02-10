"""Unit tests for commands/ticket_done.py - Mark ticket as complete.

State Format:
- ralph.tickets: ["TASK-001", ...] (list of IDs)
- ralph.blocked: {"TASK-001": "reason"} (blocked tickets - cleared on done)
- Status comes from PM tool, not state file
- PM tools receive ticket_id directly (e.g., "SDLC-0070"), not issue numbers
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def create_state(
    tickets: list[str],
    current_ticket: str | None = None,
    blocked: dict[str, str] | None = None,
    dependencies: dict[str, list[str]] | None = None,
    attempts: dict[str, int] | None = None,
    source: str = "asana",
) -> dict:
    """Create a valid state dictionary for testing."""
    return {
        "prd_path": "docs/prds/test.md",
        "plan_path": "docs/plans/test.md",
        "tickets": [],
        "current_ticket": current_ticket,
        "completed_count": 0,
        "blocked_count": 0,
        "ralph": {
            "tickets": tickets,
            "dependencies": dependencies or {},
            "attempts": attempts or {},
            "blocked": blocked or {},
            "source": source,
        },
    }


class TestMarkTicketDone:
    """Tests for mark_ticket_done."""

    def test_mark_ticket_done_updates_state(self, tmp_path: Path):
        """Given a valid state, mark_ticket_done updates the state file."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001", "TASK-002", "TASK-003"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        assert result["ticket_id"] == "TASK-001"
        assert result["status"] == "completed"

    def test_mark_ticket_done_clears_current_ticket(self, tmp_path: Path):
        """Given current_ticket is completed ticket, mark_ticket_done clears it."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mark_ticket_done("TASK-001", state_file=state_file)

        updated = json.loads(state_file.read_text())
        assert updated["current_ticket"] is None

    def test_mark_ticket_done_records_pr_number(self, tmp_path: Path):
        """Given pr_number, mark_ticket_done includes it in result."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", pr_number="123", state_file=state_file)

        assert result["pr_number"] == "123"

    def test_mark_ticket_done_clears_blocked_if_present(self, tmp_path: Path):
        """Given ticket was blocked, mark_ticket_done removes it from blocked."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
            blocked={"TASK-001": "was blocked for testing"},
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mark_ticket_done("TASK-001", state_file=state_file)

        updated = json.loads(state_file.read_text())
        assert "TASK-001" not in updated["ralph"]["blocked"]

    def test_mark_ticket_done_returns_total_count(self, tmp_path: Path):
        """Given state, mark_ticket_done returns total ticket count."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001", "TASK-002", "TASK-003"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        assert result["total"] == 3

    def test_mark_ticket_done_remaining_is_none(self, tmp_path: Path):
        """Given state, remaining is None (can't know without PM query)."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = mark_ticket_done("TASK-001", state_file=state_file)

        assert result["remaining"] is None

    def test_mark_ticket_done_raises_on_unknown_ticket(self, tmp_path: Path):
        """Given ticket not in ralph.tickets, mark_ticket_done raises ValueError."""
        from commands.ticket_done import mark_ticket_done

        state = create_state(tickets=["TASK-001"])
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(ValueError, match="not found"):
            mark_ticket_done("TASK-INVALID", state_file=state_file)

    def test_mark_ticket_done_raises_on_missing_state_file(self, tmp_path: Path):
        """Given missing state file, mark_ticket_done raises FileNotFoundError."""
        from commands.ticket_done import mark_ticket_done

        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError, match=str(missing_file)):
            mark_ticket_done("TASK-001", state_file=missing_file)


class TestTicketDonePMTool:
    """Tests for ticket_done PM tool integration."""

    def test_ticket_done_calls_pm_tool_with_ticket_id(self, tmp_path: Path):
        """Given pm_tool, ticket_done passes ticket_id (not issue_number)."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["SDLC-0067", "SDLC-0068", "SDLC-0069", "SDLC-0070"],
            current_ticket="SDLC-0070",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True
        mock_pm.remove_label.return_value = True

        result = ticket_done(
            ticket_id="SDLC-0070",
            state_file=state_file,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        # PM tool called with ticket_id, not issue_number
        assert result["status"] == "completed"
        mock_pm.close_ticket.assert_called_once_with("SDLC-0070")
        mock_pm.remove_label.assert_called_once_with("SDLC-0070", "ralph-1")

    def test_ticket_done_removes_label_before_closing(self, tmp_path: Path):
        """Given pm_tool and ralph_label, label is removed before closing."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True
        mock_pm.remove_label.return_value = True
        call_order = []
        mock_pm.remove_label.side_effect = lambda *a: call_order.append("remove")
        mock_pm.close_ticket.side_effect = lambda *a: call_order.append("close")

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        assert call_order == ["remove", "close"]

    def test_ticket_done_skips_remove_label_without_ralph_label(self, tmp_path: Path):
        """Given no ralph_label, ticket_done skips remove_label call."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm,
            ralph_label=None,
        )

        mock_pm.remove_label.assert_not_called()
        mock_pm.close_ticket.assert_called_once()

    def test_ticket_done_handles_already_closed(self, tmp_path: Path):
        """Given ticket already closed in PM, ticket_done succeeds (idempotent)."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True  # Already closed is success

        result = ticket_done(
            ticket_id="TASK-001",
            state_file=state_file,
            pm_tool=mock_pm,
        )

        assert result["status"] == "completed"
        mock_pm.close_ticket.assert_called_once_with("TASK-001")


class TestTicketDoneGitHub:
    """Tests for GitHub CLI fallback (when no pm_tool provided)."""

    def test_ticket_done_closes_github_issue(self, tmp_path: Path):
        """Given GitHub config, ticket_done closes issue via gh CLI."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        config_file = tmp_path / "config.yaml"
        config_file.write_text("pm:\n  tool: github\n")

        with patch("commands.ticket_done.close_github_issue") as mock_close:
            with patch("commands.ticket_done.find_issue_by_ticket_id") as mock_find:
                mock_find.return_value = 42
                ticket_done(
                    ticket_id="TASK-001",
                    state_file=state_file,
                    config_file=config_file,
                )

        # Verify close_github_issue was called with issue number
        mock_close.assert_called_once_with(42)

    def test_ticket_done_removes_instance_label(self, tmp_path: Path):
        """Given instance_label in config, ticket_done removes it."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
pm:
  tool: github
ralph:
  instance_label: ralph-1
""")

        with patch("commands.ticket_done.close_github_issue"):
            with patch("commands.ticket_done.remove_label_from_issue") as mock_remove:
                with patch("commands.ticket_done.find_issue_by_ticket_id") as mock_find:
                    mock_find.return_value = 42
                    ticket_done(
                        ticket_id="TASK-001",
                        state_file=state_file,
                        config_file=config_file,
                    )

        # Verify remove_label_from_issue was called with issue number and label
        mock_remove.assert_called_once_with(42, "ralph-1")

    def test_ticket_done_skips_github_when_not_configured(self, tmp_path: Path):
        """Given pm.tool is not github, ticket_done skips GitHub ops."""
        from commands.ticket_done import ticket_done

        state = create_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        config_file = tmp_path / "config.yaml"
        config_file.write_text("pm:\n  tool: none\n")

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            ticket_done(
                ticket_id="TASK-001",
                state_file=state_file,
                config_file=config_file,
            )

        mock_run.assert_not_called()


class TestFindIssueByTicketId:
    """Tests for find_issue_by_ticket_id helper function."""

    def test_find_issue_returns_number_when_found(self):
        """Given matching issue exists, find_issue_by_ticket_id returns number."""
        from commands.ticket_done import find_issue_by_ticket_id
        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([
                    {"number": 42, "title": "[TASK-001] Test ticket"}
                ]),
                stderr=""
            )

            result = find_issue_by_ticket_id("TASK-001")

        assert result == 42

    def test_find_issue_returns_none_when_not_found(self):
        """Given no matching issue, find_issue_by_ticket_id returns None."""
        from commands.ticket_done import find_issue_by_ticket_id

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([
                    {"number": 1, "title": "Unrelated Issue"}
                ]),
                stderr=""
            )
        result = find_issue_by_ticket_id("TASK-001")

        assert result is None

    def test_find_issue_searches_open_then_closed(self):
        """Given ticket in closed issues, find_issue_by_ticket_id finds it."""
        from commands.ticket_done import find_issue_by_ticket_id

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            # First call (open) returns empty, second call (closed) returns match
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="[]", stderr=""),
                MagicMock(
                    returncode=0,
                    stdout=json.dumps([{"number": 99, "title": "[TASK-001] Old"}]),
                    stderr=""
                ),
            ]
            result = find_issue_by_ticket_id("TASK-001")

        assert result == 99
        assert mock_run.call_count == 2


class TestCloseGitHubIssue:
    """Tests for close_github_issue helper function."""

    def test_close_issue_calls_gh_cli(self):
        """Given issue number, close_github_issue calls gh issue close."""
        from commands.ticket_done import close_github_issue

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            close_github_issue(42)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["gh", "issue", "close", "42"]

    def test_close_issue_handles_already_closed(self):
        """Given already closed issue, close_github_issue succeeds."""
        from commands.ticket_done import close_github_issue

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="issue already closed"
            )
            # Should not raise
            close_github_issue(42)

    def test_close_issue_raises_on_missing_gh(self):
        """Given gh CLI not found, close_github_issue raises RuntimeError."""
        from commands.ticket_done import close_github_issue

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")
            with pytest.raises(RuntimeError, match="gh CLI"):
                close_github_issue(42)


class TestRemoveLabelFromIssue:
    """Tests for remove_label_from_issue helper function."""

    def test_remove_label_calls_gh_cli(self):
        """Given issue and label, remove_label_from_issue calls gh CLI."""
        from commands.ticket_done import remove_label_from_issue

        with patch("commands.ticket_done.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            remove_label_from_issue(42, "ralph-1")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["gh", "issue", "edit", "42", "--remove-label", "ralph-1"]

