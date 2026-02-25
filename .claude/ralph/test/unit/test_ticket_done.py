"""Unit tests for commands/ticket_done.py - Mark ticket as complete.

State Format:
- Status comes from PM tool, not state file
- PM tools receive ticket_id directly (e.g., "SDLC-0070"), not issue numbers
"""

from unittest.mock import MagicMock


class TestTicketDonePMTool:
    """Tests for ticket_done PM tool integration."""

    def test_ticket_done_calls_pm_tool_with_ticket_id(self):
        """Given pm_tool, ticket_done passes ticket_id (not issue_number)."""
        from commands.ticket_done import ticket_done

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True
        mock_pm.remove_label.return_value = True

        result = ticket_done(
            ticket_id="SDLC-0070",
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        # PM tool called with ticket_id, not issue_number
        assert result["status"] == "completed"
        mock_pm.close_ticket.assert_called_once_with("SDLC-0070")
        mock_pm.remove_label.assert_called_once_with("SDLC-0070", "ralph-1")

    def test_ticket_done_removes_label_before_closing(self):
        """Given pm_tool and ralph_label, label is removed before closing."""
        from commands.ticket_done import ticket_done

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True
        mock_pm.remove_label.return_value = True
        call_order = []
        mock_pm.remove_label.side_effect = lambda *a: call_order.append("remove")
        mock_pm.close_ticket.side_effect = lambda *a: call_order.append("close")

        ticket_done(
            ticket_id="TASK-001",
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        assert call_order == ["remove", "close"]

    def test_ticket_done_skips_remove_label_without_ralph_label(self):
        """Given no ralph_label, ticket_done skips remove_label call."""
        from commands.ticket_done import ticket_done

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True

        ticket_done(
            ticket_id="TASK-001",
            pm_tool=mock_pm,
            ralph_label=None,
        )

        mock_pm.remove_label.assert_not_called()
        mock_pm.close_ticket.assert_called_once()

    def test_ticket_done_handles_already_closed(self):
        """Given ticket already closed in PM, ticket_done succeeds (idempotent)."""
        from commands.ticket_done import ticket_done

        mock_pm = MagicMock()
        mock_pm.close_ticket.return_value = True  # Already closed is success

        result = ticket_done(
            ticket_id="TASK-001",
            pm_tool=mock_pm,
        )

        assert result["status"] == "completed"
        mock_pm.close_ticket.assert_called_once_with("TASK-001")

    def test_ticket_done_without_pm_tool_logs_warning(self):
        """Given no pm_tool, ticket_done logs a warning and returns result."""
        from commands.ticket_done import ticket_done

        result = ticket_done(
            ticket_id="TASK-001",
        )

        assert result["status"] == "completed"
        assert result["ticket_id"] == "TASK-001"
