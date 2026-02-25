"""Unit tests for commands/mark_blocked.py - Mark ticket as blocked.

mark_blocked no longer reads or writes state files. It:
- Validates inputs (ticket_id required)
- Defaults empty reason to "Unknown reason"
- Uses PM tool for ticket updates
- Returns a result dict with blocked_ticket, reason, issue_number, timestamp
"""

from unittest.mock import MagicMock

import pytest


class TestMarkBlockedBasic:
    """Basic tests for mark_blocked."""

    def test_mark_blocked_returns_result(self):
        """Given a valid ticket, mark_blocked returns a result dict."""
        from commands.mark_blocked import mark_blocked

        result = mark_blocked(
            ticket_id="TASK-001",
            reason="Test failure",
        )

        assert isinstance(result, dict)
        assert result["blocked_ticket"] == "TASK-001"
        assert result["reason"] == "Test failure"
        assert "timestamp" in result

    def test_mark_blocked_requires_ticket_id(self):
        """Given empty ticket_id, mark_blocked raises ValueError."""
        from commands.mark_blocked import mark_blocked

        with pytest.raises(ValueError, match="ticket_id.*required"):
            mark_blocked(ticket_id="", reason="Test")

    def test_mark_blocked_uses_default_reason_if_empty(self):
        """Given empty reason, mark_blocked uses a default reason."""
        from commands.mark_blocked import mark_blocked

        result = mark_blocked(
            ticket_id="TASK-001",
            reason="",
        )

        assert result["reason"] == "Unknown reason"

    def test_mark_blocked_without_pm_tool_logs_warning(self):
        """Given no pm_tool, mark_blocked logs a warning and still returns result."""
        from commands.mark_blocked import mark_blocked

        result = mark_blocked(
            ticket_id="TASK-001",
            reason="Test",
        )

        assert result["blocked_ticket"] == "TASK-001"
        assert result["issue_number"] is None


class TestMarkBlockedPMTool:
    """Tests for PM tool integration."""

    def test_mark_blocked_calls_pm_tool_add_blocked_label(self):
        """Given pm_tool, mark_blocked calls add_blocked_label with reason."""
        from commands.mark_blocked import mark_blocked

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True
        mock_pm.remove_label.return_value = True

        mark_blocked(
            ticket_id="SDLC-0070",
            reason="Validation failed",
            issue_number=42,
            pm_tool=mock_pm,
        )

        mock_pm.add_blocked_label.assert_called_once_with("SDLC-0070", "Validation failed")

    def test_mark_blocked_calls_pm_tool_remove_label(self):
        """Given pm_tool and ralph_label, mark_blocked removes the label."""
        from commands.mark_blocked import mark_blocked

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True
        mock_pm.remove_label.return_value = True

        mark_blocked(
            ticket_id="SDLC-0070",
            reason="Test failure",
            issue_number=42,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        mock_pm.remove_label.assert_called_once_with("SDLC-0070", "ralph-1")

    def test_mark_blocked_skips_remove_label_without_ralph_label(self):
        """Given pm_tool but no ralph_label, mark_blocked skips remove_label."""
        from commands.mark_blocked import mark_blocked

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = True

        mark_blocked(
            ticket_id="TASK-001",
            reason="Test",
            issue_number=42,
            pm_tool=mock_pm,
            ralph_label=None,
        )

        mock_pm.remove_label.assert_not_called()

    def test_mark_blocked_continues_on_pm_tool_failure(self):
        """Given pm_tool.add_blocked_label fails, result is still returned."""
        from commands.mark_blocked import mark_blocked

        mock_pm = MagicMock()
        mock_pm.add_blocked_label.return_value = False  # Simulate failure

        result = mark_blocked(
            ticket_id="TASK-001",
            reason="Test failure",
            issue_number=42,
            pm_tool=mock_pm,
        )

        # Result should still be returned
        assert result["blocked_ticket"] == "TASK-001"
        assert result["reason"] == "Test failure"
