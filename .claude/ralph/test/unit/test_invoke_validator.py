"""Unit tests for invoke_validator function.

AIUI-0052: Implement invoke_validator function.

Tests for the invoke_validator function that calls Claude CLI with the
validator_model from config and handles timeout appropriately.

References:
- PRD: docs/prds/2026-01-30-ralph-validation-implementation.md
- Plan: docs/plans/2026-01-30-ralph-validation-implementation.md

FR-1: Invoke Validation Agent After Engineer Completes
- Given the validator returns VALIDATION_CONFIRMED, function returns confirmed result
- Given the validator returns VALIDATION_REJECTED, function returns rejected result
- Given the validation times out, function returns timeout result

FR-6: Use Configurable Validator Model
- Given validator_model in config, function uses the configured model
- Given dry_run=True, function does not invoke Claude CLI
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestInvokeValidator:
    """Tests for the invoke_validator function."""

    def test_invoke_validator_returns_confirmed_when_validation_passes(self) -> None:
        """Given VALIDATION_CONFIRMED in output, when invoke_validator is called, then it returns confirmed status."""
        from commands.orchestrator import invoke_validator, ValidatorResult

        mock_output = "Some log output here...\n\nVALIDATION_CONFIRMED\n\nTicket: AIUI-0051\nAll acceptance criteria verified against original PRD/plan."
        # Use json.dumps to properly escape the output for JSON
        import json as json_module
        json_result = json_module.dumps({"type": "result", "result": mock_output})

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json_result,
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "validation_confirmed"
            assert result.ticket_id == "AIUI-0051"

    def test_invoke_validator_returns_rejected_when_validation_fails(self) -> None:
        """Given VALIDATION_REJECTED in output, when invoke_validator is called, then it returns rejected status."""
        from commands.orchestrator import invoke_validator, ValidatorResult

        mock_output = "VALIDATION_REJECTED\n\nTicket: AIUI-0051\nReason: Acceptance criteria AC-3 not met."
        # Use json.dumps to properly escape the output for JSON
        import json as json_module
        json_result = json_module.dumps({"type": "result", "result": mock_output})

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json_result,
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "validation_rejected"
            assert result.ticket_id == "AIUI-0051"

    def test_invoke_validator_returns_timeout_when_process_times_out(self) -> None:
        """Given subprocess times out, when invoke_validator is called, then it returns timeout status."""
        from commands.orchestrator import invoke_validator
        import subprocess

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=600)

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "timeout"

    def test_invoke_validator_uses_configured_model(self) -> None:
        """Given model parameter, when invoke_validator is called, then it passes model to Claude CLI."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"type":"result","result":"VALIDATION_CONFIRMED\n\nTicket: TASK-001"}',
                stderr="",
                returncode=0,
            )

            invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="haiku",  # Specific model
                dry_run=False,
            )

            # Verify the model was passed to subprocess.run
            call_args = mock_run.call_args[0][0]
            assert "--model" in call_args
            model_index = call_args.index("--model")
            assert call_args[model_index + 1] == "haiku"

    def test_invoke_validator_dry_run_does_not_call_subprocess(self) -> None:
        """Given dry_run=True, when invoke_validator is called, then subprocess is not called."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=True,
            )

            mock_run.assert_not_called()
            assert result.status == "dry_run"

    def test_invoke_validator_uses_correct_timeout(self) -> None:
        """Given timeout_minutes parameter, when invoke_validator is called, then it sets correct timeout."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"type":"result","result":"VALIDATION_CONFIRMED\n\nTicket: TASK-001"}',
                stderr="",
                returncode=0,
            )

            invoke_validator(
                prompt="Test prompt",
                timeout_minutes=5,  # 5 minutes = 300 seconds
                model="sonnet",
                dry_run=False,
            )

            # Verify timeout was passed correctly (5 minutes = 300 seconds)
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["timeout"] == 300

    def test_invoke_validator_parses_reason_from_rejected_output(self) -> None:
        """Given VALIDATION_REJECTED with reason, when invoke_validator is called, then reason is parsed."""
        from commands.orchestrator import invoke_validator

        mock_output = "VALIDATION_REJECTED\n\nTicket: AIUI-0052\nReason: Dependencies AIUI-0051 not merged to develop."
        # Use json.dumps to properly escape the output for JSON
        import json as json_module
        json_result = json_module.dumps({"type": "result", "result": mock_output})

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json_result,
                stderr="",
                returncode=0,
            )

            result = invoke_validator(
                prompt="Test prompt",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            assert result.status == "validation_rejected"
            assert result.reason is not None
            assert "Dependencies" in result.reason or "not merged" in result.reason


class TestParseValidatorResult:
    """Tests for parse_validator_result function."""

    def test_parse_validation_confirmed(self) -> None:
        """Given VALIDATION_CONFIRMED in output, when parsed, then status is validation_confirmed."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_CONFIRMED

Ticket: TASK-001
All acceptance criteria verified.
"""

        result = parse_validator_result(output)

        assert result.status == "validation_confirmed"
        assert result.ticket_id == "TASK-001"

    def test_parse_validation_rejected(self) -> None:
        """Given VALIDATION_REJECTED in output, when parsed, then status is validation_rejected."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_REJECTED

Ticket: TASK-002
Reason: Bypass language detected in engineer state file.
"""

        result = parse_validator_result(output)

        assert result.status == "validation_rejected"
        assert result.ticket_id == "TASK-002"
        assert result.reason is not None
        assert "Bypass" in result.reason or "detected" in result.reason

    def test_parse_unknown_result(self) -> None:
        """Given no validation marker, when parsed, then status is unknown."""
        from commands.orchestrator import parse_validator_result

        output = "Some random output without validation markers"
        result = parse_validator_result(output)

        assert result.status == "unknown"

    def test_parse_timeout_result(self) -> None:
        """Given is_timeout=True, when parsed, then status is timeout."""
        from commands.orchestrator import parse_validator_result

        result = parse_validator_result("", is_timeout=True)

        assert result.status == "timeout"

    def test_parse_extracts_ticket_id(self) -> None:
        """Given ticket ID in output, when parsed, then ticket_id is extracted."""
        from commands.orchestrator import parse_validator_result

        output = """\
VALIDATION_CONFIRMED

Ticket: AIUI-0052-SPECIAL
All good.
"""

        result = parse_validator_result(output)

        assert result.ticket_id == "AIUI-0052-SPECIAL"


class TestValidatorResultDataclass:
    """Tests for the ValidatorResult dataclass."""

    def test_validator_result_has_required_fields(self) -> None:
        """ValidatorResult should have status, ticket_id, reason, and raw_output fields."""
        from commands.orchestrator import ValidatorResult

        result = ValidatorResult(
            status="validation_confirmed",
            ticket_id="TASK-001",
            reason=None,
            raw_output="test output",
        )

        assert result.status == "validation_confirmed"
        assert result.ticket_id == "TASK-001"
        assert result.reason is None
        assert result.raw_output == "test output"

    def test_validator_result_defaults(self) -> None:
        """ValidatorResult should have sensible defaults for optional fields."""
        from commands.orchestrator import ValidatorResult

        result = ValidatorResult(status="timeout")

        assert result.status == "timeout"
        assert result.ticket_id is None
        assert result.reason is None
        assert result.raw_output == ""


class TestInvokeValidatorIntegration:
    """Integration-style tests for invoke_validator."""

    def test_invoke_validator_builds_correct_cli_command(self) -> None:
        """Verify invoke_validator builds the correct Claude CLI command."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"type":"result","result":"VALIDATION_CONFIRMED\n\nTicket: TASK-001"}',
                stderr="",
                returncode=0,
            )

            invoke_validator(
                prompt="Validate ticket TASK-001",
                timeout_minutes=10,
                model="sonnet",
                dry_run=False,
            )

            # Verify command structure
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "claude"
            assert "-p" in call_args
            assert "--model" in call_args
            assert "--output-format" in call_args
            assert "stream-json" in call_args

    def test_invoke_validator_raises_on_missing_claude_cli(self) -> None:
        """Given Claude CLI not found, when invoke_validator is called, then RuntimeError is raised."""
        from commands.orchestrator import invoke_validator

        with patch("commands.orchestrator.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("claude not found")

            with pytest.raises(RuntimeError) as exc_info:
                invoke_validator(
                    prompt="Test prompt",
                    timeout_minutes=10,
                    model="sonnet",
                    dry_run=False,
                )

            assert "Claude CLI not found" in str(exc_info.value)
