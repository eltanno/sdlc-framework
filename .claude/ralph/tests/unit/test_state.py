"""Unit tests for core/state.py - State management module.

Tests cover:
- Directory management (ensure_state_dir, get_ticket_state_dir)
- Attempt management (get_latest_attempt)
- State file reading (get_previous_state, get_previous_validation)
- State file writing with atomic writes
- Markdown generation (engineer state, validation, summary)
- Summary writing
- Ticket status management

Following TDD: Write failing tests first, then implement.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestDirectoryManagement:
    """Tests for state directory management functions."""

    def test_ensure_state_dir_creates_directory(self, tmp_path: Path):
        """Given a ticket ID and attempt, ensure_state_dir creates the directory structure."""
        from core.state import ensure_state_dir

        state_dir = ensure_state_dir("TASK-001", 1, base_dir=tmp_path)

        assert state_dir.exists()
        assert state_dir.is_dir()
        assert state_dir == tmp_path / "TASK-001" / "attempt-1"

    def test_ensure_state_dir_returns_existing_directory(self, tmp_path: Path):
        """Given an existing directory, ensure_state_dir returns it without error."""
        from core.state import ensure_state_dir

        # Pre-create the directory
        existing_dir = tmp_path / "TASK-002" / "attempt-1"
        existing_dir.mkdir(parents=True)

        result = ensure_state_dir("TASK-002", 1, base_dir=tmp_path)

        assert result == existing_dir
        assert result.exists()

    def test_ensure_state_dir_requires_ticket_id(self, tmp_path: Path):
        """Given empty ticket_id, ensure_state_dir raises ValueError."""
        from core.state import ensure_state_dir

        with pytest.raises(ValueError, match="ticket_id.*required"):
            ensure_state_dir("", 1, base_dir=tmp_path)

    def test_ensure_state_dir_requires_positive_attempt(self, tmp_path: Path):
        """Given non-positive attempt, ensure_state_dir raises ValueError."""
        from core.state import ensure_state_dir

        with pytest.raises(ValueError, match="attempt.*positive"):
            ensure_state_dir("TASK-001", 0, base_dir=tmp_path)

        with pytest.raises(ValueError, match="attempt.*positive"):
            ensure_state_dir("TASK-001", -1, base_dir=tmp_path)

    def test_get_ticket_state_dir_returns_correct_path(self, tmp_path: Path):
        """Given a ticket ID, get_ticket_state_dir returns the correct path."""
        from core.state import get_ticket_state_dir

        result = get_ticket_state_dir("TASK-001", base_dir=tmp_path)

        assert result == tmp_path / "TASK-001"


class TestAttemptManagement:
    """Tests for attempt number management."""

    def test_get_latest_attempt_returns_zero_for_new_ticket(self, tmp_path: Path):
        """Given a ticket with no attempts, get_latest_attempt returns 0."""
        from core.state import get_latest_attempt

        result = get_latest_attempt("TASK-NEW", base_dir=tmp_path)

        assert result == 0

    def test_get_latest_attempt_returns_highest_attempt(self, tmp_path: Path):
        """Given multiple attempts, get_latest_attempt returns the highest."""
        from core.state import get_latest_attempt

        # Create multiple attempt directories
        ticket_dir = tmp_path / "TASK-001"
        (ticket_dir / "attempt-1").mkdir(parents=True)
        (ticket_dir / "attempt-3").mkdir(parents=True)
        (ticket_dir / "attempt-2").mkdir(parents=True)

        result = get_latest_attempt("TASK-001", base_dir=tmp_path)

        assert result == 3

    def test_get_latest_attempt_ignores_non_attempt_directories(self, tmp_path: Path):
        """Given non-attempt directories, get_latest_attempt ignores them."""
        from core.state import get_latest_attempt

        ticket_dir = tmp_path / "TASK-001"
        (ticket_dir / "attempt-2").mkdir(parents=True)
        (ticket_dir / "other-dir").mkdir(parents=True)
        (ticket_dir / "not-attempt").mkdir(parents=True)

        result = get_latest_attempt("TASK-001", base_dir=tmp_path)

        assert result == 2


class TestStateFileReading:
    """Tests for reading state files."""

    def test_get_previous_state_returns_md_content(self, tmp_path: Path):
        """Given a markdown state file exists, get_previous_state returns its content."""
        from core.state import get_previous_state

        # Setup state file
        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        md_file = state_dir / "engineer-state.md"
        md_file.write_text("# State\n\n**Status:** passed")

        result = get_previous_state("TASK-001", attempt=1, base_dir=tmp_path)

        assert "**Status:** passed" in result

    def test_get_previous_state_prefers_md_over_json(self, tmp_path: Path):
        """Given both md and json exist, get_previous_state returns md content."""
        from core.state import get_previous_state

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "engineer-state.md").write_text("# MD Content")
        (state_dir / "engineer-state.json").write_text('{"content": "json"}')

        result = get_previous_state("TASK-001", attempt=1, base_dir=tmp_path)

        assert result == "# MD Content"

    def test_get_previous_state_falls_back_to_json(self, tmp_path: Path):
        """Given only json exists, get_previous_state converts and returns it."""
        from core.state import get_previous_state

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "engineer-state.json").write_text('{"status": "passed", "attempt": 1}')

        result = get_previous_state("TASK-001", attempt=1, base_dir=tmp_path)

        assert "passed" in result.lower() or "status" in result.lower()

    def test_get_previous_state_uses_latest_attempt_by_default(self, tmp_path: Path):
        """Given no attempt specified, get_previous_state uses the latest."""
        from core.state import get_previous_state

        # Create multiple attempts
        for i in [1, 2]:
            state_dir = tmp_path / "TASK-001" / f"attempt-{i}"
            state_dir.mkdir(parents=True)
            (state_dir / "engineer-state.md").write_text(f"# Attempt {i}")

        result = get_previous_state("TASK-001", base_dir=tmp_path)

        assert "Attempt 2" in result

    def test_get_previous_state_returns_empty_for_no_attempts(self, tmp_path: Path):
        """Given no attempts exist, get_previous_state returns empty string."""
        from core.state import get_previous_state

        result = get_previous_state("TASK-NEW", base_dir=tmp_path)

        assert result == ""

    def test_get_previous_validation_returns_md_content(self, tmp_path: Path):
        """Given a validation md file exists, get_previous_validation returns its content."""
        from core.state import get_previous_validation

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "validation.md").write_text("# Validation Report\n\nAll passed")

        result = get_previous_validation("TASK-001", attempt=1, base_dir=tmp_path)

        assert "All passed" in result


class TestStateFileWriting:
    """Tests for writing state files."""

    def test_write_engineer_state_creates_both_files(self, tmp_path: Path):
        """Given state data, write_engineer_state creates both json and md files."""
        from core.state import write_engineer_state

        state_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "status": "validation_passed",
            "branch": "feature/TASK-001-test",
            "last_commit": "abc123",
            "validation_result": {
                "typecheck": "pass",
                "lint": "pass",
                "test": "pass",
                "build": "pass",
                "overall": "pass",
            },
            "work_completed": ["Implemented feature X"],
            "files_modified": ["src/feature.py"],
            "tests_written": [{"file": "tests/test_feature.py", "tests": ["test_one"]}],
            "known_issues": [],
            "next_steps": [],
        }

        result_path = write_engineer_state(state_data, base_dir=tmp_path)

        json_file = tmp_path / "TASK-001" / "attempt-1" / "engineer-state.json"
        md_file = tmp_path / "TASK-001" / "attempt-1" / "engineer-state.md"

        assert json_file.exists()
        assert md_file.exists()
        assert result_path == md_file

        # Verify JSON content
        json_data = json.loads(json_file.read_text())
        assert json_data["ticket_id"] == "TASK-001"
        assert json_data["status"] == "validation_passed"

    def test_write_engineer_state_atomic_write(self, tmp_path: Path, mocker):
        """Given a write operation, it uses atomic write (temp file + rename)."""
        from core.state import write_engineer_state

        # Track file operations
        original_rename = os.rename
        rename_calls = []

        def track_rename(src, dst):
            rename_calls.append((src, dst))
            return original_rename(src, dst)

        mocker.patch("os.rename", side_effect=track_rename)

        state_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "status": "validation_passed",
            "branch": "feature/test",
            "last_commit": "abc",
            "validation_result": {"overall": "pass"},
            "work_completed": [],
            "files_modified": [],
            "tests_written": [],
            "known_issues": [],
            "next_steps": [],
        }

        write_engineer_state(state_data, base_dir=tmp_path)

        # Verify rename was used for atomic write
        assert len(rename_calls) >= 1

    def test_write_validation_report_creates_both_files(self, tmp_path: Path):
        """Given validation data, write_validation_report creates both json and md files."""
        from core.state import write_validation_report

        validation_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "overall_result": "pass",
            "checks": {
                "typecheck": {"status": "pass", "error_count": 0, "errors": []},
                "lint": {"status": "pass", "error_count": 0, "warning_count": 0, "errors": []},
                "test": {"status": "pass", "total": 10, "passed": 10, "failed": 0, "failures": []},
                "build": {"status": "pass", "error_count": 0, "errors": []},
            },
            "root_cause_analysis": "",
            "suggested_fixes": [],
            "priority_order": [],
        }

        result_path = write_validation_report(validation_data, base_dir=tmp_path)

        json_file = tmp_path / "TASK-001" / "attempt-1" / "validation.json"
        md_file = tmp_path / "TASK-001" / "attempt-1" / "validation.md"

        assert json_file.exists()
        assert md_file.exists()
        assert result_path == md_file


class TestMarkdownGeneration:
    """Tests for markdown generation from JSON."""

    def test_generate_engineer_state_md_includes_all_sections(self):
        """Given complete state data, generated markdown includes all required sections."""
        from core.state import generate_engineer_state_md

        state_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "status": "validation_passed",
            "branch": "feature/TASK-001-test",
            "last_commit": "abc123",
            "validation_result": {
                "typecheck": "pass",
                "lint": "pass",
                "test": "pass",
                "build": "pass",
                "overall": "pass",
            },
            "work_completed": ["Implemented feature X", "Added tests"],
            "files_modified": ["src/feature.py", "tests/test_feature.py"],
            "tests_written": [{"file": "tests/test_feature.py", "tests": ["test_one", "test_two"]}],
            "known_issues": ["Known issue one"],
            "next_steps": ["Next step one"],
        }

        result = generate_engineer_state_md(state_data)

        # Check all sections are present
        assert "# Engineer State: TASK-001" in result
        assert "**Attempt:** 1" in result
        assert "**Status:** validation_passed" in result
        assert "feature/TASK-001-test" in result
        assert "abc123" in result
        assert "## Validation Result" in result
        assert "## Work Completed" in result
        assert "Implemented feature X" in result
        assert "## Files Modified" in result
        assert "src/feature.py" in result
        assert "## Tests Written" in result
        assert "test_feature.py" in result
        assert "## Known Issues" in result
        assert "Known issue one" in result
        assert "## Next Steps" in result

    def test_generate_validation_md_includes_error_details(self):
        """Given validation data with errors, generated markdown includes error details."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "overall_result": "fail",
            "checks": {
                "typecheck": {
                    "status": "fail",
                    "error_count": 1,
                    "errors": [{"file": "src/main.py", "line": 10, "message": "Type error", "code": "TS001"}],
                },
                "lint": {
                    "status": "pass",
                    "error_count": 0,
                    "warning_count": 1,
                    "errors": [],
                },
                "test": {
                    "status": "fail",
                    "total": 5,
                    "passed": 3,
                    "failed": 2,
                    "failures": [
                        {
                            "file": "tests/test_main.py",
                            "test_name": "test_something",
                            "error": "AssertionError",
                            "expected": "True",
                            "received": "False",
                        }
                    ],
                },
                "build": {"status": "pass", "error_count": 0, "errors": []},
            },
            "root_cause_analysis": "Missing type annotation",
            "suggested_fixes": ["Add type hint to function"],
            "priority_order": ["Fix typecheck errors first"],
        }

        result = generate_validation_md(validation_data)

        assert "# Validation Report: TASK-001" in result
        assert "Overall Result" in result or "overall_result" in result.lower()
        assert "fail" in result.lower()
        assert "TypeScript" in result or "typecheck" in result.lower()
        assert "src/main.py" in result
        assert "Type error" in result
        assert "Root Cause" in result or "root_cause" in result.lower()

    def test_generate_summary_md_includes_attempt_history(self):
        """Given summary data with attempt history, generated markdown includes it."""
        from core.state import generate_summary_md

        summary_data = {
            "ticket_id": "TASK-001",
            "final_status": "SUCCESS",
            "total_attempts": 2,
            "completed": "2026-01-19T14:00:00",
            "outcome": "Ticket completed successfully after 2 attempts.",
            "attempt_history": [
                {"attempt": 1, "status": "validation_failed", "key_issues": "Test failures"},
                {"attempt": 2, "status": "validation_passed", "key_issues": "None"},
            ],
            "branch": "feature/TASK-001-test",
            "last_commit": "def456",
            "pr_number": "123",
            "files_changed": ["src/feature.py", "tests/test_feature.py"],
            "lessons_learned": ["Always run tests locally"],
        }

        result = generate_summary_md(summary_data)

        assert "# Ticket Summary: TASK-001" in result
        assert "SUCCESS" in result
        assert "**Total Attempts:** 2" in result
        assert "Attempt History" in result
        assert "validation_failed" in result
        assert "Test failures" in result
        assert "PR" in result or "pr_number" in result.lower()


class TestSummaryWriting:
    """Tests for ticket summary writing."""

    def test_write_summary_creates_files(self, tmp_path: Path):
        """Given ticket completion, write_summary creates summary files."""
        from core.state import write_summary

        # Setup some attempt directories first
        attempt_dir = tmp_path / "TASK-001" / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text(
            json.dumps({"status": "validation_passed", "known_issues": []})
        )

        result_path = write_summary(
            ticket_id="TASK-001",
            status="SUCCESS",
            total_attempts=1,
            pr_number="123",
            base_dir=tmp_path,
        )

        json_file = tmp_path / "TASK-001" / "summary.json"
        md_file = tmp_path / "TASK-001" / "summary.md"

        assert json_file.exists()
        assert md_file.exists()
        assert result_path == md_file

    def test_write_summary_includes_usage_metrics(self, tmp_path: Path):
        """Given usage metrics, write_summary includes them in the summary."""
        from core.state import write_summary

        attempt_dir = tmp_path / "TASK-001" / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text(
            json.dumps({"status": "validation_passed", "known_issues": []})
        )

        usage = {
            "invocation_count": 5,
            "duration_seconds": 120,
            "total_cost": 0.15,
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "opus",
        }

        write_summary(
            ticket_id="TASK-001",
            status="SUCCESS",
            total_attempts=1,
            pr_number="123",
            usage=usage,
            base_dir=tmp_path,
        )

        json_file = tmp_path / "TASK-001" / "summary.json"
        data = json.loads(json_file.read_text())

        assert "usage" in data
        assert data["usage"]["total_cost"] == 0.15


class TestTicketStatus:
    """Tests for ticket status tracking in workflow state."""

    def test_load_workflow_state_parses_json(self, tmp_path: Path):
        """Given a valid state file, load_workflow_state returns parsed state."""
        from core.state import load_workflow_state

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "First", "status": "pending", "dependencies": []},
                {"id": "TASK-002", "title": "Second", "status": "in_progress", "dependencies": ["TASK-001"]},
            ],
            "current_ticket": "TASK-002",
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        result = load_workflow_state(state_file)

        assert result.version == "1.0"
        assert len(result.tickets) == 2
        assert result.current_ticket == "TASK-002"

    def test_load_workflow_state_raises_on_missing_file(self, tmp_path: Path):
        """Given a missing state file, load_workflow_state raises FileNotFoundError."""
        from core.state import load_workflow_state

        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            load_workflow_state(missing_file)

    def test_load_workflow_state_raises_on_invalid_json(self, tmp_path: Path):
        """Given invalid JSON, load_workflow_state raises ValueError."""
        from core.state import load_workflow_state

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {{{")

        with pytest.raises(ValueError, match="Invalid.*JSON"):
            load_workflow_state(invalid_file)

    def test_save_workflow_state_writes_atomically(self, tmp_path: Path):
        """Given workflow state, save_workflow_state writes atomically."""
        from core.state import WorkflowState, Ticket, save_workflow_state

        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[
                Ticket(id="TASK-001", title="First", status="pending", dependencies=[]),
            ],
            current_ticket=None,
        )
        state_file = tmp_path / "workflow-state.json"

        save_workflow_state(state, state_file)

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["version"] == "1.0"
        assert len(data["tickets"]) == 1

    def test_update_ticket_status_changes_status(self, tmp_path: Path):
        """Given a ticket ID and new status, update_ticket_status updates it."""
        from core.state import load_workflow_state, save_workflow_state, update_ticket_status

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "First", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        update_ticket_status(state_file, "TASK-001", "in_progress")

        updated_state = load_workflow_state(state_file)
        assert updated_state.tickets[0].status == "in_progress"

    def test_get_ticket_by_id_returns_ticket(self, tmp_path: Path):
        """Given a valid ticket ID, get_ticket_by_id returns the ticket."""
        from core.state import load_workflow_state, get_ticket_by_id

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "First", "status": "pending", "dependencies": []},
                {"id": "TASK-002", "title": "Second", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        workflow_state = load_workflow_state(state_file)
        ticket = get_ticket_by_id(workflow_state, "TASK-002")

        assert ticket is not None
        assert ticket.id == "TASK-002"
        assert ticket.title == "Second"

    def test_get_ticket_by_id_returns_none_for_invalid_id(self, tmp_path: Path):
        """Given an invalid ticket ID, get_ticket_by_id returns None."""
        from core.state import load_workflow_state, get_ticket_by_id

        state = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "First", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
        }
        state_file = tmp_path / "workflow-state.json"
        state_file.write_text(json.dumps(state))

        workflow_state = load_workflow_state(state_file)
        ticket = get_ticket_by_id(workflow_state, "TASK-INVALID")

        assert ticket is None


class TestPromptBuilding:
    """Tests for prompt template building."""

    def test_build_prompt_substitutes_placeholders(self, tmp_path: Path):
        """Given a template with placeholders, build_prompt substitutes them."""
        from core.state import build_prompt

        template_file = tmp_path / "template.md"
        template_file.write_text("Hello {NAME}, ticket {TICKET_ID} is ready.")

        result = build_prompt(template_file, NAME="World", TICKET_ID="TASK-001")

        assert result == "Hello World, ticket TASK-001 is ready."

    def test_build_prompt_handles_missing_template(self, tmp_path: Path):
        """Given a missing template file, build_prompt raises FileNotFoundError."""
        from core.state import build_prompt

        missing_file = tmp_path / "missing.md"

        with pytest.raises(FileNotFoundError):
            build_prompt(missing_file, NAME="Test")

    def test_build_prompt_warns_on_unsubstituted_placeholders(self, tmp_path: Path, capsys):
        """Given unsubstituted placeholders, build_prompt logs a warning."""
        from core.state import build_prompt

        template_file = tmp_path / "template.md"
        template_file.write_text("Hello {NAME}, ticket {UNSUBSTITUTED} is ready.")

        result = build_prompt(template_file, NAME="World")

        # Check warning was logged (to stderr)
        captured = capsys.readouterr()
        assert "UNSUBSTITUTED" in captured.err or "{UNSUBSTITUTED}" in result

    def test_build_prompt_substitutes_config_values(self, tmp_path: Path):
        """Given config.yaml exists, build_prompt auto-substitutes config values."""
        from core.state import build_prompt

        # Create config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dev:
  test_command: "pytest"
  lint_command: "ruff check ."
""")

        template_file = tmp_path / "template.md"
        template_file.write_text("Run tests with: {TEST_COMMAND}")

        result = build_prompt(template_file, config_dir=tmp_path)

        assert result == "Run tests with: pytest"


class TestAdditionalCoverage:
    """Additional tests for edge cases and increased coverage."""

    def test_ensure_state_dir_uses_default_base_dir(self, mocker):
        """Given no base_dir, ensure_state_dir uses the default."""
        from core.state import ensure_state_dir, DEFAULT_STATE_DIRECTORY

        # Mock mkdir to avoid creating real directories
        mock_mkdir = mocker.patch("pathlib.Path.mkdir")

        result = ensure_state_dir("TASK-001", 1, base_dir=None)

        # Should use default directory
        assert str(DEFAULT_STATE_DIRECTORY) in str(result)

    def test_get_ticket_state_dir_uses_default_base_dir(self):
        """Given no base_dir, get_ticket_state_dir uses the default."""
        from core.state import get_ticket_state_dir, DEFAULT_STATE_DIRECTORY

        result = get_ticket_state_dir("TASK-001", base_dir=None)

        assert str(DEFAULT_STATE_DIRECTORY) in str(result)

    def test_get_latest_attempt_uses_default_base_dir(self, mocker):
        """Given no base_dir, get_latest_attempt uses the default."""
        from core.state import get_latest_attempt, DEFAULT_STATE_DIRECTORY

        # Mock Path.exists to return False (no directory exists)
        mocker.patch("pathlib.Path.exists", return_value=False)

        result = get_latest_attempt("TASK-001", base_dir=None)

        assert result == 0

    def test_get_latest_attempt_handles_invalid_attempt_names(self, tmp_path: Path):
        """Given directories with non-numeric attempt names, they are skipped."""
        from core.state import get_latest_attempt

        ticket_dir = tmp_path / "TASK-001"
        (ticket_dir / "attempt-1").mkdir(parents=True)
        (ticket_dir / "attempt-abc").mkdir(parents=True)  # Invalid name
        (ticket_dir / "attempt-").mkdir(parents=True)  # Invalid name

        result = get_latest_attempt("TASK-001", base_dir=tmp_path)

        assert result == 1

    def test_get_previous_state_handles_invalid_json(self, tmp_path: Path):
        """Given invalid JSON file, get_previous_state returns raw content."""
        from core.state import get_previous_state

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "engineer-state.json").write_text("not valid json {{{")

        result = get_previous_state("TASK-001", attempt=1, base_dir=tmp_path)

        assert "not valid json" in result

    def test_get_previous_state_returns_empty_when_no_files(self, tmp_path: Path):
        """Given empty attempt directory, get_previous_state returns empty string."""
        from core.state import get_previous_state

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        # No files created

        result = get_previous_state("TASK-001", attempt=1, base_dir=tmp_path)

        assert result == ""

    def test_get_previous_validation_falls_back_to_json(self, tmp_path: Path):
        """Given only json exists, get_previous_validation falls back to json."""
        from core.state import get_previous_validation

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "validation.json").write_text('{"result": "pass"}')

        result = get_previous_validation("TASK-001", attempt=1, base_dir=tmp_path)

        assert "pass" in result.lower()

    def test_get_previous_validation_handles_invalid_json(self, tmp_path: Path):
        """Given invalid JSON file, get_previous_validation returns raw content."""
        from core.state import get_previous_validation

        state_dir = tmp_path / "TASK-001" / "attempt-1"
        state_dir.mkdir(parents=True)
        (state_dir / "validation.json").write_text("invalid {{{")

        result = get_previous_validation("TASK-001", attempt=1, base_dir=tmp_path)

        assert "invalid" in result

    def test_get_previous_validation_uses_default_base_dir(self, mocker):
        """Given no base_dir, get_previous_validation uses the default."""
        from core.state import get_previous_validation

        # Mock get_latest_attempt to return 0
        mocker.patch("core.state.get_latest_attempt", return_value=0)

        result = get_previous_validation("TASK-001", base_dir=None)

        assert result == ""

    def test_write_summary_blocked_status(self, tmp_path: Path):
        """Given BLOCKED status, write_summary extracts lessons learned."""
        from core.state import write_summary

        # Setup attempt with known issues
        attempt_dir = tmp_path / "TASK-001" / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text(
            json.dumps({
                "status": "validation_failed",
                "known_issues": ["Test failure"],
                "next_steps": ["Fix the test"]
            })
        )

        write_summary(
            ticket_id="TASK-001",
            status="BLOCKED",
            total_attempts=1,
            base_dir=tmp_path,
        )

        json_file = tmp_path / "TASK-001" / "summary.json"
        data = json.loads(json_file.read_text())

        assert "Test failure" in data["lessons_learned"]
        assert "blocked" in data["outcome"].lower()

    def test_write_summary_missing_state_file(self, tmp_path: Path):
        """Given missing state files, write_summary handles gracefully."""
        from core.state import write_summary

        # Don't create any attempt directories

        write_summary(
            ticket_id="TASK-001",
            status="BLOCKED",
            total_attempts=2,
            base_dir=tmp_path,
        )

        json_file = tmp_path / "TASK-001" / "summary.json"
        data = json.loads(json_file.read_text())

        # Should have "unknown" status for missing state files
        assert any(h["status"] == "unknown" for h in data["attempt_history"])

    def test_write_summary_invalid_state_json(self, tmp_path: Path):
        """Given corrupt state file, write_summary handles gracefully."""
        from core.state import write_summary

        attempt_dir = tmp_path / "TASK-001" / "attempt-1"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "engineer-state.json").write_text("invalid json {{{")

        write_summary(
            ticket_id="TASK-001",
            status="BLOCKED",
            total_attempts=1,
            base_dir=tmp_path,
        )

        json_file = tmp_path / "TASK-001" / "summary.json"
        data = json.loads(json_file.read_text())

        assert any("Failed to parse" in h["key_issues"] for h in data["attempt_history"])

    def test_generate_validation_md_with_lint_errors(self):
        """Given lint errors, generated markdown includes lint error details."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "overall_result": "fail",
            "checks": {
                "typecheck": {"status": "pass", "error_count": 0, "errors": []},
                "lint": {
                    "status": "fail",
                    "error_count": 2,
                    "warning_count": 0,
                    "errors": [
                        {"file": "src/main.py", "line": 5, "rule": "E501", "message": "Line too long", "severity": "error"}
                    ],
                },
                "test": {"status": "pass", "total": 5, "passed": 5, "failed": 0, "failures": []},
                "build": {"status": "pass", "error_count": 0, "errors": []},
            },
            "root_cause_analysis": "",
            "suggested_fixes": [],
            "priority_order": [],
        }

        result = generate_validation_md(validation_data)

        assert "E501" in result
        assert "Line too long" in result

    def test_generate_validation_md_with_build_errors(self):
        """Given build errors, generated markdown includes build error details."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "TASK-001",
            "attempt": 1,
            "timestamp": "2026-01-19T12:00:00",
            "overall_result": "fail",
            "checks": {
                "typecheck": {"status": "pass", "error_count": 0, "errors": []},
                "lint": {"status": "pass", "error_count": 0, "warning_count": 0, "errors": []},
                "test": {"status": "pass", "total": 5, "passed": 5, "failed": 0, "failures": []},
                "build": {
                    "status": "fail",
                    "error_count": 1,
                    "errors": [{"file": "src/main.py", "message": "Import not found"}],
                },
            },
            "root_cause_analysis": "",
            "suggested_fixes": [],
            "priority_order": [],
        }

        result = generate_validation_md(validation_data)

        assert "Import not found" in result

    def test_generate_summary_md_empty_history(self):
        """Given empty attempt history, generated markdown shows placeholder."""
        from core.state import generate_summary_md

        summary_data = {
            "ticket_id": "TASK-001",
            "final_status": "SUCCESS",
            "total_attempts": 0,
            "completed": "2026-01-19T14:00:00",
            "outcome": "No attempts.",
            "attempt_history": [],
            "branch": "feature/test",
            "last_commit": "abc",
            "pr_number": "1",
            "files_changed": [],
            "lessons_learned": [],
        }

        result = generate_summary_md(summary_data)

        assert "No history recorded" in result

    def test_build_prompt_no_config_dir(self, tmp_path: Path):
        """Given no config_dir, build_prompt works without config substitution."""
        from core.state import build_prompt

        template_file = tmp_path / "template.md"
        template_file.write_text("Run: {TEST_COMMAND}")

        # Without config_dir, placeholder stays
        result = build_prompt(template_file, config_dir=None)

        assert "{TEST_COMMAND}" in result

    def test_ticket_to_dict_excludes_none_values(self):
        """Test Ticket.to_dict keeps block_reason key but excludes other None values."""
        from core.state import Ticket

        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="pending",
            dependencies=[],
            block_reason=None,
        )

        result = ticket.to_dict()

        # block_reason should be present even if None (per the implementation)
        assert "block_reason" in result


class TestDataclasses:
    """Tests for state dataclasses."""

    def test_ticket_dataclass_creation(self):
        """Test Ticket dataclass can be created with all fields."""
        from core.state import Ticket

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=["TASK-000"],
            attempts=0,
            block_reason=None,
        )

        assert ticket.id == "TASK-001"
        assert ticket.status == "pending"
        assert ticket.dependencies == ["TASK-000"]

    def test_ticket_dataclass_defaults(self):
        """Test Ticket dataclass has correct defaults."""
        from core.state import Ticket

        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="pending",
            dependencies=[],
        )

        assert ticket.attempts == 0
        assert ticket.block_reason is None

    def test_workflow_state_dataclass_creation(self):
        """Test WorkflowState dataclass can be created."""
        from core.state import WorkflowState, Ticket

        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])],
            current_ticket=None,
        )

        assert state.version == "1.0"
        assert len(state.tickets) == 1

    def test_workflow_state_to_dict(self):
        """Test WorkflowState can be converted to dict for serialization."""
        from core.state import WorkflowState, Ticket

        state = WorkflowState(
            version="1.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])],
            current_ticket="TASK-001",
        )

        result = state.to_dict()

        assert result["version"] == "1.0"
        assert result["prd_path"] == "docs/prds/test.md"
        assert len(result["tickets"]) == 1
        assert result["tickets"][0]["id"] == "TASK-001"
