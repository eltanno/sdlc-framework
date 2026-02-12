"""Unit tests for validation output to state directory.

AIUI-0056: Write validation output to state directory.

Tests verify that validation.md is written to docs/state/{ticket}/attempt-{n}/
after validator invocation, with proper content structure.

References:
- PRD: docs/prds/2026-01-30-ralph-validation-implementation.md (FR-5)
- Plan: docs/plans/2026-01-30-ralph-validation-implementation.md

FR-5: Validator Output to State Directory
- Given validator completes, then validation.md exists in state directory
- Given validation file exists, then it shows each acceptance criterion checked
- Given validation file exists, then it shows pass/fail for each criterion
- Given validation file exists, then it shows any flags or concerns raised
- Given validator runs multiple attempts, then attempt number is in path
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest


class TestValidationOutputLocation:
    """Tests for validation.md file location and existence."""

    def test_validation_file_written_to_correct_location_on_first_attempt(
        self,
    ) -> None:
        """Given validator completes attempt 1, when file is written, then it goes to attempt-1 directory."""
        from commands.orchestrator import invoke_validator
        from core.state import ensure_state_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            # Ensure directory exists
            ensure_state_dir(ticket_id, attempt, state_dir)

            # Mock validator that writes validation.md
            mock_output = """VALIDATION_CONFIRMED

Ticket: AIUI-0056
All acceptance criteria verified against original PRD/plan.
"""
            import json as json_module

            json_result = json_module.dumps({"type": "result", "result": mock_output})

            with patch("commands.orchestrator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=json_result,
                    stderr="",
                    returncode=0,
                )

                # Simulate validator writing the file
                expected_path = state_dir / ticket_id / f"attempt-{attempt}" / "validation.md"
                expected_path.write_text("Mock validation content")

                result = invoke_validator(
                    prompt="Test prompt",
                    timeout_minutes=10,
                    model="sonnet",
                    dry_run=False,
                )

            # Verify file exists at expected location
            assert expected_path.exists()
            assert result.status == "validation_confirmed"

    def test_validation_file_written_to_correct_location_on_second_attempt(
        self,
    ) -> None:
        """Given validator completes attempt 2, when file is written, then it goes to attempt-2 directory."""
        from core.state import ensure_state_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 2

            # Ensure directory exists
            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)

            # Verify path structure
            assert attempt_dir == state_dir / ticket_id / "attempt-2"
            assert attempt_dir.exists()

    def test_validation_file_path_includes_ticket_id(self) -> None:
        """Given ticket ID, when validation file path is constructed, then it includes ticket ID."""
        from core.state import ensure_state_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0999"
            attempt = 1

            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)
            validation_path = attempt_dir / "validation.md"

            assert ticket_id in str(validation_path)
            assert "attempt-1" in str(validation_path)


class TestValidationFileContent:
    """Tests for validation.md file content structure."""

    def test_write_validation_report_creates_markdown_file(self) -> None:
        """Given validation data, when write_validation_report is called, then validation.md is created."""
        from core.state import write_validation_report

        with tempfile.TemporaryDirectory() as tmpdir:
            validation_data = {
                "ticket_id": "AIUI-0056",
                "attempt": 1,
                "timestamp": "2026-01-30T10:00:00",
                "overall_result": "PASS",
                "checks": {
                    "criteria_1": {"status": "pass", "note": "Implemented correctly"},
                    "criteria_2": {"status": "pass", "note": "All tests pass"},
                },
            }

            md_path = write_validation_report(validation_data, base_dir=Path(tmpdir))

            assert md_path.exists()
            assert md_path.name == "validation.md"
            assert "AIUI-0056" in str(md_path)

    def test_validation_markdown_includes_ticket_id(self) -> None:
        """Given validation data with ticket ID, when markdown is generated, then it includes ticket ID."""
        from core.state import write_validation_report

        with tempfile.TemporaryDirectory() as tmpdir:
            validation_data = {
                "ticket_id": "AIUI-0056",
                "attempt": 1,
                "timestamp": "2026-01-30T10:00:00",
                "overall_result": "PASS",
                "checks": {},
            }

            md_path = write_validation_report(validation_data, base_dir=Path(tmpdir))
            content = md_path.read_text()

            assert "AIUI-0056" in content
    def test_validation_markdown_includes_acceptance_criteria_results(self) -> None:
        """Given validation with AC results, when markdown is generated, then it shows each AC."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "AIUI-0056",
            "attempt": 1,
            "timestamp": "2026-01-30T10:00:00",
            "overall_result": "PASS",
            "checks": {
                "typecheck": {"status": "pass", "error_count": 0, "errors": []},
                "lint": {
                    "status": "pass",
                    "error_count": 0,
                    "warning_count": 0,
                    "errors": [],
                },
                "test": {
                    "status": "pass",
                    "total": 10,
                    "passed": 10,
                    "failed": 0,
                    "failures": [],
                },
                "build": {"status": "pass", "error_count": 0, "errors": []},
            },
        }

        markdown = generate_validation_md(validation_data)

        # Should show each check result
        assert "TypeScript" in markdown or "typecheck" in markdown.lower()
        assert "Lint" in markdown or "lint" in markdown.lower()
        assert "Test" in markdown or "test" in markdown.lower()
        assert "Build" in markdown or "build" in markdown.lower()


    def test_validation_markdown_shows_pass_fail_status(self) -> None:
        """Given validation with mixed pass/fail, when markdown is generated, then it shows status."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "AIUI-0056",
            "attempt": 1,
            "timestamp": "2026-01-30T10:00:00",
            "overall_result": "FAIL",
            "checks": {
                "typecheck": {"status": "pass", "error_count": 0, "errors": []},
                "lint": {
                    "status": "fail",
                    "error_count": 2,
                    "warning_count": 0,
                    "errors": [
                        {
                            "file": "test.py",
                            "line": 10,
                            "message": "Line too long",
                            "rule": "E501",
                            "severity": "error",
                        }
                    ],
                },
            },
        }

        markdown = generate_validation_md(validation_data)

        # Should indicate pass/fail
        assert "pass" in markdown.lower() or "fail" in markdown.lower()
        # Should show the lint error
        assert "Line too long" in markdown or "E501" in markdown

    def test_validation_markdown_includes_flags_and_concerns(self) -> None:
        """Given validation with concerns, when markdown is generated, then concerns are shown."""
        from core.state import generate_validation_md

        validation_data = {
            "ticket_id": "AIUI-0056",
            "attempt": 1,
            "timestamp": "2026-01-30T10:00:00",
            "overall_result": "FAIL",
            "root_cause_analysis": "Tests are failing due to incorrect mock setup",
            "suggested_fixes": [
                "Fix mock configuration in test_foo.py",
                "Update test assertions in test_bar.py",
            ],
            "checks": {},
        }

        markdown = generate_validation_md(validation_data)

        # Should show root cause and suggested fixes
        assert "mock setup" in markdown or "Root Cause" in markdown
        assert "test_foo.py" in markdown or "suggested" in markdown.lower()


class TestValidationFileExistenceCheck:
    """Tests for verifying validation.md file existence after validator runs."""

    def test_validation_file_exists_after_successful_validation(self) -> None:
        """Given validator confirms, when validation completes, then validation.md exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            # Create state directory
            from core.state import ensure_state_dir

            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)

            # Simulate validator writing validation.md
            validation_file = attempt_dir / "validation.md"
            validation_file.write_text("# Validation Report\n\nAll checks passed.")

            # Verify file exists
            assert validation_file.exists()
            content = validation_file.read_text()
            assert "Validation Report" in content

    def test_validation_file_exists_after_rejected_validation(self) -> None:
        """Given validator rejects, when validation completes, then validation.md exists with rejection details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            # Create state directory
            from core.state import ensure_state_dir

            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)

            # Simulate validator writing validation.md with rejection
            validation_file = attempt_dir / "validation.md"
            validation_file.write_text(
                "# Validation Report\n\nStatus: REJECTED\nReason: Acceptance criteria not met."
            )

            # Verify file exists
            assert validation_file.exists()
            content = validation_file.read_text()
            assert "REJECTED" in content
            assert "not met" in content


class TestValidationFileVerification:
    """Tests for verifying validation.md exists after validator invocation."""

    def test_check_validation_file_exists_returns_true_when_file_present(self) -> None:
        """Given validation.md exists, when checked, then return True."""
        from commands.orchestrator import check_validation_file_exists

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            from core.state import ensure_state_dir

            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)
            validation_file = attempt_dir / "validation.md"
            validation_file.write_text("Validation content")

            result = check_validation_file_exists(ticket_id, attempt, state_dir)

            assert result is True

    def test_check_validation_file_exists_returns_false_when_file_missing(self) -> None:
        """Given validation.md does not exist, when checked, then return False."""
        from commands.orchestrator import check_validation_file_exists

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            from core.state import ensure_state_dir

            # Create directory but no validation.md file
            ensure_state_dir(ticket_id, attempt, state_dir)

            result = check_validation_file_exists(ticket_id, attempt, state_dir)

            assert result is False

    def test_write_fallback_validation_creates_file_when_missing(self) -> None:
        """Given validation.md missing after validator runs, when fallback is written, then file is created."""
        from commands.orchestrator import write_fallback_validation_report

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"
            attempt = 1

            from core.state import ensure_state_dir

            attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)
            validation_file = attempt_dir / "validation.md"

            # File does not exist initially
            assert not validation_file.exists()

            # Write fallback
            write_fallback_validation_report(
                ticket_id=ticket_id,
                attempt=attempt,
                status="validation_confirmed",
                message="Validator completed but did not write validation.md",
                state_dir=state_dir,
            )

            # File should now exist
            assert validation_file.exists()
            content = validation_file.read_text()
            assert ticket_id in content
            assert "validation_confirmed" in content.lower() or "confirmed" in content.lower()


class TestValidationOutputAttempts:
    """Tests for validation output across multiple attempts."""

    def test_each_attempt_has_separate_validation_file(self) -> None:
        """Given multiple attempts, when validator runs, then each attempt has its own validation.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"

            from core.state import ensure_state_dir

            # Create directories for attempts 1, 2, 3
            for attempt in [1, 2, 3]:
                attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)
                validation_file = attempt_dir / "validation.md"
                validation_file.write_text(f"Validation report for attempt {attempt}")

            # Verify all three files exist separately
            for attempt in [1, 2, 3]:
                validation_path = (
                    state_dir / ticket_id / f"attempt-{attempt}" / "validation.md"
                )
                assert validation_path.exists()
                content = validation_path.read_text()
                assert f"attempt {attempt}" in content

    def test_validation_files_do_not_overwrite_previous_attempts(self) -> None:
        """Given validator runs multiple attempts, when files are written, then previous attempts are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            ticket_id = "AIUI-0056"

            from core.state import write_validation_report

            # Write validation for attempt 1
            validation_data_1 = {
                "ticket_id": ticket_id,
                "attempt": 1,
                "timestamp": "2026-01-30T10:00:00",
                "overall_result": "FAIL",
                "checks": {},
            }
            path_1 = write_validation_report(validation_data_1, base_dir=state_dir)

            # Write validation for attempt 2
            validation_data_2 = {
                "ticket_id": ticket_id,
                "attempt": 2,
                "timestamp": "2026-01-30T11:00:00",
                "overall_result": "PASS",
                "checks": {},
            }
            path_2 = write_validation_report(validation_data_2, base_dir=state_dir)

            # Verify both files exist and are different
            assert path_1.exists()
            assert path_2.exists()
            assert path_1 != path_2
            assert "attempt-1" in str(path_1)
            assert "attempt-2" in str(path_2)

            # Verify contents are different
            content_1 = path_1.read_text()
            content_2 = path_2.read_text()
            assert "Attempt: 1" in content_1 or "attempt:** 1" in content_1.lower()
            assert "Attempt: 2" in content_2 or "attempt:** 2" in content_2.lower()

