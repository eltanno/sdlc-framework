"""Unit tests for commands/ticket_reset.py - Ticket reset functionality.

reset_ticket no longer reads or writes state files. It:
- Validates ticket_id is not empty
- Optionally cleans up the ticket's state directory (attempt dirs)
- Returns a ResetResult with success, ticket_id, state_cleaned

The actual blocked/unblocked status is managed via PM tool labels,
not local state files. This module focuses on filesystem cleanup.
"""

from pathlib import Path

import pytest


class TestResetTicket:
    """Tests for the reset_ticket function."""

    def test_reset_ticket_returns_success(self):
        """Given a valid ticket_id, reset_ticket returns a successful result."""
        from commands.ticket_reset import reset_ticket

        result = reset_ticket("TASK-001", clean_state=False)

        assert result.success is True
        assert result.ticket_id == "TASK-001"
        assert result.state_cleaned is False

    def test_reset_ticket_raises_on_empty_ticket_id(self):
        """Given an empty ticket_id, reset_ticket raises TicketResetError."""
        from commands.ticket_reset import reset_ticket, TicketResetError

        with pytest.raises(TicketResetError, match="ticket_id is required"):
            reset_ticket("")

    def test_reset_ticket_default_clean_state_is_true(self, tmp_path: Path):
        """Given no clean_state argument, default is True (cleans up)."""
        from commands.ticket_reset import reset_ticket

        # Create state directory with files
        state_dir = tmp_path / "TASK-001"
        attempt_dir = state_dir / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')

        result = reset_ticket(
            "TASK-001",
            state_base_dir=tmp_path,
        )

        # Default clean_state=True should remove the directory
        assert not state_dir.exists()
        assert result.state_cleaned is True


class TestResetTicketWithCleanup:
    """Tests for the reset_ticket function with state cleanup option."""

    def test_reset_with_clean_state_removes_state_directory(self, tmp_path: Path):
        """Given clean_state=True, when resetting, then state files are removed."""
        from commands.ticket_reset import reset_ticket

        # Create state directory with files
        state_dir = tmp_path / "TASK-001"
        attempt_dir = state_dir / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')
        (attempt_dir / "engineer-state.md").write_text("# State")
        (state_dir / "attempt-2").mkdir()
        (state_dir / "attempt-2" / "validation.json").write_text('{"result": "fail"}')

        result = reset_ticket(
            "TASK-001",
            clean_state=True,
            state_base_dir=tmp_path,
        )

        # Verify state directory was removed
        assert not state_dir.exists()
        assert result.state_cleaned is True

    def test_reset_without_clean_state_preserves_state_directory(self, tmp_path: Path):
        """Given clean_state=False, when resetting, then state files are preserved."""
        from commands.ticket_reset import reset_ticket

        # Create state directory
        state_dir = tmp_path / "TASK-001"
        attempt_dir = state_dir / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')

        result = reset_ticket(
            "TASK-001",
            clean_state=False,
            state_base_dir=tmp_path,
        )

        # Verify state directory was preserved
        assert state_dir.exists()
        assert (attempt_dir / "engineer-state.json").exists()
        assert result.state_cleaned is False

    def test_reset_with_clean_state_handles_missing_state_dir(self, tmp_path: Path):
        """Given clean_state=True but no state directory exists, then no error."""
        from commands.ticket_reset import reset_ticket

        # No state directory created
        state_dir = tmp_path / "TASK-001"
        assert not state_dir.exists()

        # Should not raise error
        result = reset_ticket(
            "TASK-001",
            clean_state=True,
            state_base_dir=tmp_path,
        )

        assert result.success is True
        # state_cleaned is False because there was nothing to clean
        assert result.state_cleaned is False


class TestResetTicketResult:
    """Tests for the ResetResult dataclass returned by reset_ticket."""

    def test_result_contains_all_required_fields(self):
        """Given a successful reset, result contains all expected fields."""
        from commands.ticket_reset import reset_ticket

        result = reset_ticket("TASK-001", clean_state=False)

        assert result.success is True
        assert result.ticket_id == "TASK-001"
        assert result.state_cleaned is False

    def test_result_to_dict_for_json_output(self):
        """Given a result, to_dict returns JSON-serializable dictionary."""
        import json
        from commands.ticket_reset import reset_ticket

        result = reset_ticket("TASK-001", clean_state=False)
        result_dict = result.to_dict()

        # Should be JSON serializable (verify by actually serializing)
        json_str = json.dumps(result_dict)
        parsed = json.loads(json_str)

        # Should contain expected keys with correct values
        assert result_dict["ticket"] == "TASK-001"
        assert result_dict["state_cleaned"] is False

        # Verify round-trip preserves data
        assert parsed == result_dict

    def test_result_to_dict_with_cleaned_state(self, tmp_path: Path):
        """Given state was cleaned, to_dict reflects that."""
        from commands.ticket_reset import reset_ticket

        # Create a state directory to clean
        state_dir = tmp_path / "TASK-001"
        (state_dir / "attempt-1").mkdir(parents=True)

        result = reset_ticket("TASK-001", clean_state=True, state_base_dir=tmp_path)
        result_dict = result.to_dict()

        assert result_dict["ticket"] == "TASK-001"
        assert result_dict["state_cleaned"] is True
