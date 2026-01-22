"""Unit tests for the PM tool abstraction layer.

Tests cover:
- TicketStatus enum values
- TicketInfo dataclass
- PMTool Protocol conformance
- GitHubPM implementation with mocked subprocess calls
"""

from unittest.mock import MagicMock

import pytest


class TestTicketInfo:
    """Tests for TicketInfo dataclass."""

    def test_ticket_info_labels_default_empty_and_independent(self):
        """Given two TicketInfo instances without labels, then each gets independent list."""
        from core.pm import TicketInfo, TicketStatus

        ticket1 = TicketInfo(
            id="SDLC-001",
            title="Test ticket 1",
            status=TicketStatus.OPEN,
        )
        ticket2 = TicketInfo(
            id="SDLC-002",
            title="Test ticket 2",
            status=TicketStatus.OPEN,
        )

        # Verify defaults are empty
        assert ticket1.labels == []
        assert ticket2.labels == []

        # Verify mutability: modifying one doesn't affect the other
        ticket1.labels.append("bug")
        assert ticket1.labels == ["bug"]
        assert ticket2.labels == []  # Should remain empty


class TestGitHubPMGetTicketStatus:
    """Tests for GitHubPM.get_ticket_status method."""

    def test_get_ticket_status_returns_open_for_open_issue(self, mock_pm_subprocess: MagicMock):
        """Given open issue, when getting status, then OPEN is returned."""
        from core.pm import GitHubPM, TicketStatus

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "title": "[SDLC-0038] Test", "state": "OPEN", "labels": []}'

        pm = GitHubPM()
        status = pm.get_ticket_status("74")

        assert status == TicketStatus.OPEN

    def test_get_ticket_status_returns_closed_for_closed_issue(self, mock_pm_subprocess: MagicMock):
        """Given closed issue, when getting status, then CLOSED is returned."""
        from core.pm import GitHubPM, TicketStatus

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "title": "[SDLC-0038] Test", "state": "CLOSED", "labels": []}'

        pm = GitHubPM()
        status = pm.get_ticket_status("74")

        assert status == TicketStatus.CLOSED

    def test_get_ticket_status_returns_blocked_when_blocked_label_present(self, mock_pm_subprocess: MagicMock):
        """Given issue with blocked label, when getting status, then BLOCKED is returned."""
        from core.pm import GitHubPM, TicketStatus

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "title": "[SDLC-0038] Test", "state": "OPEN", "labels": [{"name": "blocked"}]}'

        pm = GitHubPM()
        status = pm.get_ticket_status("74")

        assert status == TicketStatus.BLOCKED


class TestGitHubPMClaimTicket:
    """Tests for GitHubPM.claim_ticket method."""

    def test_claim_ticket_returns_true_on_success(self, mock_pm_subprocess: MagicMock):
        """Given ticket id and label, when claiming succeeds, then True is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = ""

        pm = GitHubPM()
        result = pm.claim_ticket("74", "ralph-1")

        assert result is True

    def test_claim_ticket_returns_false_on_failure(self, mock_pm_subprocess: MagicMock):
        """Given gh command fails, when claiming ticket, then False is returned and status unchanged."""
        from core.pm import GitHubPM, TicketStatus

        # Setup: first call to claim_ticket fails
        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "some error"

        pm = GitHubPM()
        result = pm.claim_ticket("74", "ralph-1")

        assert result is False

        # Verify status check still works (ticket not affected by failed claim)
        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = '{"number": 74, "title": "Test", "state": "OPEN", "labels": []}'
        status = pm.get_ticket_status("74")
        assert status == TicketStatus.OPEN


class TestGitHubPMCloseTicket:
    """Tests for GitHubPM.close_ticket method."""

    def test_close_ticket_returns_true_on_success(self, mock_pm_subprocess: MagicMock):
        """Given ticket id, when closing succeeds, then True is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = ""

        pm = GitHubPM()
        result = pm.close_ticket("74")

        assert result is True

    def test_close_ticket_returns_false_on_failure(self, mock_pm_subprocess: MagicMock):
        """Given gh command fails, when closing ticket, then False is returned and status remains OPEN."""
        from core.pm import GitHubPM, TicketStatus

        # Setup: first call to close_ticket fails
        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "not found"

        pm = GitHubPM()
        result = pm.close_ticket("999")

        assert result is False

        # Verify ticket status remains OPEN (close failed)
        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = '{"number": 999, "title": "Test", "state": "OPEN", "labels": []}'
        status = pm.get_ticket_status("999")
        assert status == TicketStatus.OPEN


class TestGitHubPMAddBlockedLabel:
    """Tests for GitHubPM.add_blocked_label method."""

    def test_add_blocked_label_makes_two_calls(self, mock_pm_subprocess: MagicMock):
        """Given ticket id and reason, when blocking, then both label and comment operations called."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = ""

        pm = GitHubPM()
        result = pm.add_blocked_label("74", "Test failures")

        assert result is True
        # Should make exactly two calls: one for label, one for comment
        assert mock_pm_subprocess.call_count == 2

    def test_add_blocked_label_returns_false_on_failure(self, mock_pm_subprocess: MagicMock):
        """Given gh command fails, when blocking, then False is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "error"

        pm = GitHubPM()
        result = pm.add_blocked_label("74", "Test failures")

        assert result is False


class TestGitHubPMIsTicketClaimed:
    """Tests for GitHubPM.is_ticket_claimed method."""

    def test_is_ticket_claimed_returns_true_when_ralph_label_exists(self, mock_pm_subprocess: MagicMock):
        """Given issue has ralph-* label, when checking, then (True, label) is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "labels": [{"name": "ralph-2"}]}'

        pm = GitHubPM()
        claimed, label = pm.is_ticket_claimed("74")

        assert claimed is True
        assert label == "ralph-2"

    def test_is_ticket_claimed_returns_false_when_no_ralph_label(self, mock_pm_subprocess: MagicMock):
        """Given issue has no ralph-* label, when checking, then (False, None) is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "labels": [{"name": "bug"}]}'

        pm = GitHubPM()
        claimed, label = pm.is_ticket_claimed("74")

        assert claimed is False
        assert label is None

    def test_is_ticket_claimed_returns_false_when_no_labels(self, mock_pm_subprocess: MagicMock):
        """Given issue has no labels, when checking, then (False, None) is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.stdout = '{"number": 74, "labels": []}'

        pm = GitHubPM()
        claimed, label = pm.is_ticket_claimed("74")

        assert claimed is False
        assert label is None


class TestGitHubPMGetOpenTickets:
    """Tests for GitHubPM.get_open_tickets method."""

    def test_get_open_tickets_returns_list_of_ticket_info(self, mock_pm_subprocess: MagicMock):
        """Given ticket ids, when getting open tickets, then list of TicketInfo returned."""
        from core.pm import GitHubPM, TicketInfo, TicketStatus

        # Mock response for gh issue list
        mock_pm_subprocess.return_value.stdout = '''[
            {"number": 74, "title": "[SDLC-0038] PM abstraction", "state": "OPEN", "labels": []},
            {"number": 75, "title": "[SDLC-0039] Config loading", "state": "OPEN", "labels": []}
        ]'''

        pm = GitHubPM()
        tickets = pm.get_open_tickets(["74", "75", "76"])

        assert len(tickets) == 2
        assert isinstance(tickets[0], TicketInfo)
        assert tickets[0].id == "74"
        assert tickets[0].status == TicketStatus.OPEN

    def test_get_open_tickets_filters_by_provided_ids(self, mock_pm_subprocess: MagicMock):
        """Given ticket ids, when getting open tickets, then only matching tickets returned."""
        from core.pm import GitHubPM

        # Response has tickets not in our list
        mock_pm_subprocess.return_value.stdout = '''[
            {"number": 74, "title": "[SDLC-0038] Test", "state": "OPEN", "labels": []},
            {"number": 99, "title": "[OTHER] Not in scope", "state": "OPEN", "labels": []}
        ]'''

        pm = GitHubPM()
        tickets = pm.get_open_tickets(["74", "75"])

        assert len(tickets) == 1
        assert tickets[0].id == "74"

    def test_get_open_tickets_returns_empty_list_when_none_open(self, mock_pm_subprocess: MagicMock):
        """Given all tickets closed, when getting open tickets, then empty list returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.stdout = "[]"

        pm = GitHubPM()
        tickets = pm.get_open_tickets(["74", "75"])

        assert tickets == []

    def test_get_open_tickets_includes_labels_in_ticket_info(self, mock_pm_subprocess: MagicMock):
        """Given tickets with labels, when getting open tickets, then labels included."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.stdout = '''[
            {"number": 74, "title": "Test", "state": "OPEN", "labels": [{"name": "bug"}, {"name": "priority-high"}]}
        ]'''

        pm = GitHubPM()
        tickets = pm.get_open_tickets(["74"])

        assert tickets[0].labels == ["bug", "priority-high"]


class TestGitHubPMRemoveLabel:
    """Tests for GitHubPM.remove_label method."""

    def test_remove_label_returns_true_on_success(self, mock_pm_subprocess: MagicMock):
        """Given ticket id and label, when removal succeeds, then True is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = ""

        pm = GitHubPM()
        result = pm.remove_label("74", "ralph-1")

        assert result is True

    def test_remove_label_returns_false_on_failure(self, mock_pm_subprocess: MagicMock):
        """Given gh command fails, when removing label, then False is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "label not found"

        pm = GitHubPM()
        result = pm.remove_label("74", "ralph-1")

        assert result is False


class TestGitHubPMAssignToSelf:
    """Tests for GitHubPM.assign_to_self method."""

    def test_assign_to_self_returns_true_on_success(self, mock_pm_subprocess: MagicMock):
        """Given ticket id, when assignment succeeds, then True is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 0
        mock_pm_subprocess.return_value.stdout = ""

        pm = GitHubPM()
        result = pm.assign_to_self("74")

        assert result is True

    def test_assign_to_self_returns_false_on_failure(self, mock_pm_subprocess: MagicMock):
        """Given gh command fails, when assigning to self, then False is returned."""
        from core.pm import GitHubPM

        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "assignment failed"

        pm = GitHubPM()
        result = pm.assign_to_self("74")

        assert result is False


class TestGitHubPMErrorHandling:
    """Tests for GitHubPM error handling."""

    def test_raises_pm_error_when_gh_not_installed(self, mock_pm_subprocess: MagicMock):
        """Given gh not installed, when any operation attempted, then PMError is raised."""
        from core.pm import GitHubPM, PMError

        mock_pm_subprocess.side_effect = FileNotFoundError("gh not found")

        pm = GitHubPM()
        with pytest.raises(PMError) as exc_info:
            pm.get_ticket_status("74")

        assert "gh" in str(exc_info.value).lower() or "not installed" in str(exc_info.value).lower()

    def test_raises_pm_error_when_not_authenticated(self, mock_pm_subprocess: MagicMock):
        """Given gh not authenticated, when any operation attempted, then PMAuthError is raised."""
        from core.pm import GitHubPM, PMAuthError

        mock_pm_subprocess.return_value.returncode = 1
        mock_pm_subprocess.return_value.stderr = "GH_TOKEN environment variable not set"

        pm = GitHubPM()
        with pytest.raises(PMAuthError) as exc_info:
            pm.get_ticket_status("74")

        assert "auth" in str(exc_info.value).lower() or "token" in str(exc_info.value).lower()


# Fixture for mocking subprocess in pm module
@pytest.fixture
def mock_pm_subprocess(mocker):
    """Mock subprocess.run for pm module.

    Returns:
        MagicMock that can be configured with side_effect or return_value
    """
    mock = mocker.patch("core.pm.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = "[]"
    mock.return_value.stderr = ""
    return mock


# =============================================================================
# LocalPM Tests
# =============================================================================


class TestLocalPMInit:
    """Tests for LocalPM initialization."""

    def test_local_pm_logs_warning_on_init(self, caplog):
        """Given LocalPM, when initialized, then warning is logged about degraded mode."""
        import logging

        from core.pm import LocalPM

        with caplog.at_level(logging.WARNING):
            pm = LocalPM()

        assert any("degraded" in record.message.lower() for record in caplog.records)


class TestLocalPMGetTicketStatus:
    """Tests for LocalPM.get_ticket_status method."""

    def test_get_ticket_status_returns_open_by_default(self):
        """Given untracked ticket, when getting status, then OPEN is returned."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        status = pm.get_ticket_status("SDLC-0040")

        assert status == TicketStatus.OPEN

    def test_get_ticket_status_returns_closed_when_tracked_closed(self):
        """Given ticket tracked as closed, when getting status, then CLOSED is returned."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        pm.close_ticket("SDLC-0040")
        status = pm.get_ticket_status("SDLC-0040")

        assert status == TicketStatus.CLOSED

    def test_get_ticket_status_returns_blocked_when_tracked_blocked(self):
        """Given ticket tracked as blocked, when getting status, then BLOCKED is returned."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        pm.add_blocked_label("SDLC-0040", "Test failure")
        status = pm.get_ticket_status("SDLC-0040")

        assert status == TicketStatus.BLOCKED


class TestLocalPMClaimTicket:
    """Tests for LocalPM.claim_ticket method."""

    def test_claim_ticket_always_returns_true(self):
        """Given any ticket, when claiming, then True is returned (no concurrency control)."""
        from core.pm import LocalPM

        pm = LocalPM()
        result = pm.claim_ticket("SDLC-0040", "ralph-1")

        assert result is True

    def test_claim_ticket_logs_debug_about_no_concurrency(self, caplog):
        """Given claim_ticket called, then debug message logged about no concurrency control."""
        import logging

        from core.pm import LocalPM

        pm = LocalPM()
        caplog.clear()  # Clear init warnings
        with caplog.at_level(logging.DEBUG):
            pm.claim_ticket("SDLC-0040", "ralph-1")

        # Check for specific concurrency debug message
        assert any("no concurrency control" in record.message.lower()
                   for record in caplog.records)


class TestLocalPMCloseTicket:
    """Tests for LocalPM.close_ticket method."""

    def test_close_ticket_returns_true(self):
        """Given ticket id, when closing, then True is returned."""
        from core.pm import LocalPM

        pm = LocalPM()
        result = pm.close_ticket("SDLC-0040")

        assert result is True

    def test_close_ticket_tracks_ticket_as_closed(self):
        """Given ticket id, when closing, then ticket is tracked as closed."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        pm.close_ticket("SDLC-0040")

        assert pm.get_ticket_status("SDLC-0040") == TicketStatus.CLOSED


class TestLocalPMAddBlockedLabel:
    """Tests for LocalPM.add_blocked_label method."""

    def test_add_blocked_label_returns_true(self):
        """Given ticket id and reason, when blocking, then True is returned."""
        from core.pm import LocalPM

        pm = LocalPM()
        result = pm.add_blocked_label("SDLC-0040", "Test failures")

        assert result is True

    def test_add_blocked_label_tracks_ticket_as_blocked(self):
        """Given ticket id, when blocking, then ticket is tracked as blocked."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        pm.add_blocked_label("SDLC-0040", "Test failures")

        assert pm.get_ticket_status("SDLC-0040") == TicketStatus.BLOCKED


class TestLocalPMIsTicketClaimed:
    """Tests for LocalPM.is_ticket_claimed method."""

    def test_is_ticket_claimed_always_returns_false_none(self):
        """Given any ticket, when checking claimed, then (False, None) returned."""
        from core.pm import LocalPM

        pm = LocalPM()
        claimed, label = pm.is_ticket_claimed("SDLC-0040")

        assert claimed is False
        assert label is None


class TestLocalPMGetOpenTickets:
    """Tests for LocalPM.get_open_tickets method."""

    def test_get_open_tickets_returns_all_untracked_as_open(self):
        """Given ticket ids, when getting open tickets, then untracked ones returned."""
        from core.pm import LocalPM, TicketStatus

        pm = LocalPM()
        tickets = pm.get_open_tickets(["SDLC-0040", "SDLC-0041", "SDLC-0042"])

        assert len(tickets) == 3
        for ticket in tickets:
            assert ticket.status == TicketStatus.OPEN

    def test_get_open_tickets_excludes_closed_tickets(self):
        """Given some closed tickets, when getting open, then closed excluded."""
        from core.pm import LocalPM

        pm = LocalPM()
        pm.close_ticket("SDLC-0041")
        tickets = pm.get_open_tickets(["SDLC-0040", "SDLC-0041", "SDLC-0042"])

        ticket_ids = [t.id for t in tickets]
        assert "SDLC-0041" not in ticket_ids
        assert len(tickets) == 2

    def test_get_open_tickets_excludes_blocked_tickets(self):
        """Given some blocked tickets, when getting open, then blocked excluded."""
        from core.pm import LocalPM

        pm = LocalPM()
        pm.add_blocked_label("SDLC-0041", "Test failure")
        tickets = pm.get_open_tickets(["SDLC-0040", "SDLC-0041", "SDLC-0042"])

        ticket_ids = [t.id for t in tickets]
        assert "SDLC-0041" not in ticket_ids
        assert len(tickets) == 2

    def test_get_open_tickets_returns_ticket_info_objects(self):
        """Given ticket ids, when getting open tickets, then TicketInfo objects returned."""
        from core.pm import LocalPM, TicketInfo

        pm = LocalPM()
        tickets = pm.get_open_tickets(["SDLC-0040"])

        assert len(tickets) == 1
        assert isinstance(tickets[0], TicketInfo)
        assert tickets[0].id == "SDLC-0040"

    def test_get_open_tickets_returns_empty_for_empty_input(self):
        """Given empty ticket list, when getting open tickets, then empty list returned."""
        from core.pm import LocalPM

        pm = LocalPM()
        tickets = pm.get_open_tickets([])

        assert tickets == []


class TestLocalPMRemoveLabel:
    """Tests for LocalPM.remove_label method."""

    def test_remove_label_always_returns_true(self):
        """Given any ticket and label, when removing, then True is returned (no-op)."""
        from core.pm import LocalPM

        pm = LocalPM()
        result = pm.remove_label("SDLC-0040", "ralph-1")

        assert result is True


class TestLocalPMAssignToSelf:
    """Tests for LocalPM.assign_to_self method."""

    def test_assign_to_self_always_returns_true(self):
        """Given any ticket, when assigning to self, then True is returned (no-op)."""
        from core.pm import LocalPM

        pm = LocalPM()
        result = pm.assign_to_self("SDLC-0040")

        assert result is True
