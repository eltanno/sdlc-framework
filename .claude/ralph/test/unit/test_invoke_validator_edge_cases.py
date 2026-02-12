"""Additional edge case tests for invoke_validator function.

AIUI-0065: Additional comprehensive unit tests for validator functions.

This module adds edge case tests that weren't covered in the initial
test_invoke_validator.py file to ensure complete coverage of error paths.

References:
- PRD: docs/prds/2026-01-30-ralph-validation-implementation.md
- Plan: docs/plans/2026-01-30-ralph-validation-implementation.md
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestInvokeValidatorEdgeCases:
    """Edge case tests for invoke_validator function."""

    def test_invoke_validator_handles_malformed_json_gracefully(self) -> None:
        """Given malformed JSON in output, when invoke_validator is called, then it falls back to full output."""
        from commands.orchestrator import invoke_validator

        # Malformed JSON - missing closing brace
        mock_output = '{"type":"result", "result":"VALIDATION_CONFIRMED\n\nTicket: TASK-001"'

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=mock_output,
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            # JSON parsing will fail, so it falls back to full output
            # The full output still contains the malformed JSON, which includes the text
            # "VALIDATION_CONFIRMED", so parse_validator_result can still parse it
            assert result.status == "validation_confirmed"
            # The ticket ID will include the trailing quote from malformed JSON
            assert "TASK-001" in result.ticket_id

    def test_invoke_validator_handles_empty_output(self) -> None:
        """Given empty output, when invoke_validator is called, then it returns unknown status."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "unknown"
            assert result.raw_output == ""

    def test_invoke_validator_handles_no_result_json_line(self) -> None:
        """Given output without result JSON line, when invoke_validator is called, then it uses full output."""
        from commands.orchestrator import invoke_validator

        # Output with JSON but not result type
        mock_output = '{"type":"log","message":"Starting validation"}\nVALIDATION_CONFIRMED\n\nTicket: TASK-001'

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=mock_output,
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            # Should use full output as fallback
            assert result.status == "validation_confirmed"
            assert result.ticket_id == "TASK-001"

    def test_invoke_validator_combines_stdout_and_stderr(self) -> None:
        """Given output in stderr, when invoke_validator is called, then it combines stdout and stderr."""
        from commands.orchestrator import invoke_validator
        import json as json_module

        json_result = json_module.dumps({"type": "result", "result": "VALIDATION_CONFIRMED\n\nTicket: TASK-001"})

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="",
                stderr=json_result,  # Result in stderr instead of stdout
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "validation_confirmed"
            assert result.ticket_id == "TASK-001"

    def test_invoke_validator_handles_subprocess_nonzero_exit(self) -> None:
        """Given subprocess returns non-zero, when invoke_validator is called, then it still parses output."""
        from commands.orchestrator import invoke_validator
        import json as json_module

        # Need proper newlines for JSON encoding
        result_text = "VALIDATION_REJECTED\n\nTicket: TASK-001\nReason: Test failed"
        json_result = json_module.dumps({"type": "result", "result": result_text})

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json_result,
                stderr="",
                returncode=1,  # Non-zero exit
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            # Should still parse the output even with non-zero exit
            assert result.status == "validation_rejected"
            assert result.ticket_id == "TASK-001"
            assert "Test failed" in result.reason


class TestParseValidatorResultEdgeCases:
    """Edge case tests for parse_validator_result function."""

    def test_parse_validator_result_without_ticket_id(self) -> None:
        """Given output without ticket ID, when parsed, then ticket_id is None."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_CONFIRMED

All acceptance criteria verified.
"""

        result = parse_validator_result(output)

        assert result.status == "validation_confirmed"
        assert result.ticket_id is None

    def test_parse_validator_result_rejected_without_reason(self) -> None:
        """Given VALIDATION_REJECTED without reason, when parsed, then reason is None."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_REJECTED

Ticket: TASK-001
"""

        result = parse_validator_result(output)

        assert result.status == "validation_rejected"
        assert result.ticket_id == "TASK-001"
        assert result.reason is None

    def test_parse_validator_result_preserves_raw_output(self) -> None:
        """Given any output, when parsed, then raw_output is preserved."""
        from commands.orchestrator import parse_validator_result

        output = "Some random output with VALIDATION_CONFIRMED\nTicket: TASK-001\nExtra details here"
        result = parse_validator_result(output)

        assert result.raw_output == output

    def test_parse_validator_result_handles_multiline_reason(self) -> None:
        """Given reason spanning multiple lines, when parsed, then only first line is captured."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_REJECTED

Ticket: TASK-001
Reason: First line of reason
Second line should not be included
"""

        result = parse_validator_result(output)

        assert result.status == "validation_rejected"
        assert result.reason == "First line of reason"

    def test_parse_validator_result_case_insensitive_reason(self) -> None:
        """Given 'REASON:' or 'reason:' or 'Reason:', when parsed, then reason is extracted."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_REJECTED

Ticket: TASK-001
REASON: Test failed
"""

        result = parse_validator_result(output)

        assert result.status == "validation_rejected"
        assert result.reason == "Test failed"

    def test_parse_validator_result_handles_ticket_id_with_special_chars(self) -> None:
        """Given ticket ID with underscores/hyphens, when parsed, then ticket_id is extracted correctly."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_CONFIRMED

Ticket: AIUI_0051-SPECIAL-123
All good.
"""

        result = parse_validator_result(output)

        assert result.ticket_id == "AIUI_0051-SPECIAL-123"

    def test_parse_validator_result_empty_string(self) -> None:
        """Given empty string, when parsed, then status is unknown."""
        from commands.orchestrator import parse_validator_result

        result = parse_validator_result("")

        assert result.status == "unknown"
        assert result.ticket_id is None
        assert result.reason is None
        assert result.raw_output == ""
