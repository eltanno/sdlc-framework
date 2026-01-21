"""Unit tests for commands/mark_blocked.py - Mark ticket as blocked.

Tests cover v2 format ONLY (real production format):
- tickets: [] (empty array)
- ralph.tickets: ["TASK-001", ...] (list of IDs)
- ralph.blocked: {"TASK-001": "reason"} (blocked tickets)

Status comes from PM tool, not state file.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def create_v2_state(
    tickets: list[str],
    current_ticket: str | None = None,
    blocked: dict[str, str] | None = None,
    dependencies: dict[str, list[str]] | None = None,
    attempts: dict[str, int] | None = None,
    source: str = "asana",
) -> dict:
    """Create a valid v2 format state dictionary.

    This is the ONLY format used in production. v1 format is gone.
    """
    return {
        "version": "2.0",
        "prd_path": "docs/prds/test.md",
        "plan_path": "docs/plans/test.md",
        "tickets": [],  # Always empty in v2 - IDs are in ralph.tickets
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


class TestMarkBlockedV2Basic:
    """Basic tests for mark_blocked with v2 format."""

    def test_mark_blocked_returns_result(self, tmp_path: Path):
        """Given a valid ticket, mark_blocked returns a result dict."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test failure",
                state_file=state_file,
            )

        assert isinstance(result, dict)
        assert result["blocked_ticket"] == "TASK-001"
        assert result["reason"] == "Test failure"
        assert "timestamp" in result

    def test_mark_blocked_requires_ticket_id(self, tmp_path: Path):
        """Given empty ticket_id, mark_blocked raises ValueError."""
        from commands.mark_blocked import mark_blocked

        state_file = tmp_path / "workflow-state.json"
        state_file.write_text("{}")

        with pytest.raises(ValueError, match="ticket_id.*required"):
            mark_blocked(ticket_id="", reason="Test", state_file=state_file)

    def test_mark_blocked_uses_default_reason_if_empty(self, tmp_path: Path):
        """Given empty reason, mark_blocked uses a default reason."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(tickets=["TASK-001"], current_ticket="TASK-001")
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="",
                state_file=state_file,
            )

        assert result["reason"] != ""

    def test_mark_blocked_raises_on_missing_state_file(self, tmp_path: Path):
        """Given missing state file, mark_blocked raises FileNotFoundError."""
        from commands.mark_blocked import mark_blocked

        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=missing_file,
            )

    def test_mark_blocked_raises_on_unknown_ticket(self, tmp_path: Path):
        """Given ticket not in ralph.tickets, mark_blocked raises ValueError."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(tickets=["TASK-001"])
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with pytest.raises(ValueError, match="not found"):
            with patch("commands.mark_blocked.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
                mark_blocked(
                    ticket_id="TASK-INVALID",
                    reason="Test",
                    state_file=state_file,
                )


class TestMarkBlockedV2StateUpdate:
    """Tests for v2 state updates when marking blocked."""

    def test_mark_blocked_adds_to_ralph_blocked(self, tmp_path: Path):
        """Given a ticket, mark_blocked adds it to ralph.blocked with reason."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Validation failed",
                state_file=state_file,
            )

        updated = json.loads(state_file.read_text())
        assert "TASK-001" in updated["ralph"]["blocked"]
        assert updated["ralph"]["blocked"]["TASK-001"] == "Validation failed"

    def test_mark_blocked_clears_current_ticket(self, tmp_path: Path):
        """Given current_ticket is blocked ticket, mark_blocked clears it."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001", "TASK-002"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Blocked",
                state_file=state_file,
            )

        updated = json.loads(state_file.read_text())
        assert updated["current_ticket"] is None

    def test_mark_blocked_does_not_increment_blocked_count(self, tmp_path: Path):
        """Given v2 format, blocked_count stays 0 (we use ralph.blocked instead)."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(tickets=["TASK-001"], current_ticket="TASK-001")
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
            )

        updated = json.loads(state_file.read_text())
        assert updated["blocked_count"] == 0
        assert "TASK-001" in updated["ralph"]["blocked"]


class TestMarkBlockedV2PMTool:
    """Tests for PM tool integration with v2 format."""

    def test_mark_blocked_calls_pm_tool_add_blocked_label(self, tmp_path: Path):
        """Given pm_tool, mark_blocked calls add_blocked_label with reason."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["SDLC-0070"],
            current_ticket="SDLC-0070",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True
        mock_pm.remove_label.return_value = True

        mark_blocked(
            ticket_id="SDLC-0070",
            reason="Validation failed",
            state_file=state_file,
            issue_number=42,
            pm_tool=mock_pm,
        )

        mock_pm.add_blocked_label.assert_called_once_with("42", "Validation failed")

    def test_mark_blocked_calls_pm_tool_remove_label(self, tmp_path: Path):
        """Given pm_tool and ralph_label, mark_blocked removes the label."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["SDLC-0070"],
            current_ticket="SDLC-0070",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True
        mock_pm.remove_label.return_value = True

        mark_blocked(
            ticket_id="SDLC-0070",
            reason="Test failure",
            state_file=state_file,
            issue_number=42,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        mock_pm.remove_label.assert_called_once_with("42", "ralph-1")

    def test_mark_blocked_skips_remove_label_without_ralph_label(self, tmp_path: Path):
        """Given pm_tool but no ralph_label, mark_blocked skips remove_label."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True

        mark_blocked(
            ticket_id="TASK-001",
            reason="Test",
            state_file=state_file,
            issue_number=42,
            pm_tool=mock_pm,
            ralph_label=None,
        )

        mock_pm.remove_label.assert_not_called()

    def test_mark_blocked_with_pm_tool_skips_subprocess(self, tmp_path: Path):
        """Given pm_tool, mark_blocked does not use subprocess for GitHub ops."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True
        mock_pm.remove_label.return_value = True

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
                issue_number=42,
                pm_tool=mock_pm,
            )

        # When pm_tool is provided with issue_number, subprocess should NOT be called
        mock_run.assert_not_called()

    def test_mark_blocked_continues_on_pm_tool_failure(self, tmp_path: Path):
        """Given pm_tool.add_blocked_label fails, state is still updated."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = False  # Simulate failure

        mark_blocked(
            ticket_id="TASK-001",
            reason="Test failure",
            state_file=state_file,
            issue_number=42,
            pm_tool=mock_pm,
        )

        # State should still be updated
        updated = json.loads(state_file.read_text())
        assert "TASK-001" in updated["ralph"]["blocked"]


class TestMarkBlockedV2GitHub:
    """Tests for GitHub CLI fallback (when no pm_tool provided)."""

    def test_mark_blocked_looks_up_issue_without_pm_tool(self, tmp_path: Path):
        """Given no pm_tool, mark_blocked looks up issue via gh CLI."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"number": 42, "title": "[TASK-001] Test"}]),
                stderr=""
            )
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
            )

        assert result["issue_number"] == 42

    def test_mark_blocked_uses_provided_issue_number(self, tmp_path: Path):
        """Given issue_number provided, mark_blocked uses it directly."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
                issue_number=99,
            )

        assert result["issue_number"] == 99

    def test_mark_blocked_adds_blocked_label_via_gh(self, tmp_path: Path):
        """Given GitHub config, mark_blocked adds blocked label via gh CLI."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
                issue_number=42,
            )

        # Check that gh issue edit --add-label blocked was called
        calls = [str(call) for call in mock_run.call_args_list]
        assert any("--add-label" in c and "blocked" in c for c in calls)

    def test_mark_blocked_handles_no_issue_found(self, tmp_path: Path):
        """Given no matching GitHub issue, mark_blocked still updates state."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            result = mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
            )

        assert result["issue_number"] is None
        updated = json.loads(state_file.read_text())
        assert "TASK-001" in updated["ralph"]["blocked"]

    def test_mark_blocked_handles_gh_cli_error(self, tmp_path: Path):
        """Given gh CLI fails, mark_blocked still updates state."""
        from commands.mark_blocked import mark_blocked

        state = create_v2_state(
            tickets=["TASK-001"],
            current_ticket="TASK-001",
        )
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        with patch("commands.mark_blocked.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="not authenticated"
            )
            mark_blocked(
                ticket_id="TASK-001",
                reason="Test",
                state_file=state_file,
            )

        updated = json.loads(state_file.read_text())
        assert "TASK-001" in updated["ralph"]["blocked"]
