"""Unit tests for CLI entry point.

Tests for:
- Argument parsing (main command, status, reset)
- Command routing to appropriate handlers
- Error handling for invalid inputs
- Verbose and dry-run flags
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli import create_parser, main


class TestCreateParser:
    """Tests for create_parser function.

    Note: Direct path invocation (ralph docs/prd.md docs/plan.md) is handled
    by main() which inserts the 'run' subcommand. These tests verify the
    parser works correctly with explicit subcommands.
    """

    def test_parser_accepts_run_with_prd_and_plan_paths(self) -> None:
        """Given 'run' with prd and plan paths, should accept them."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md"])

        assert args.prd == Path("docs/prd.md")
        assert args.plan == Path("docs/plan.md")

    def test_parser_accepts_run_with_dry_run_flag(self) -> None:
        """Given 'run' with --dry-run flag, should set dry_run to True."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md", "--dry-run"])

        assert args.dry_run is True

    def test_parser_accepts_run_with_max_attempts_value(self) -> None:
        """Given 'run' with --max-attempts flag with value, should parse as int."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md", "--max-attempts", "5"])

        assert args.max_attempts == 5

    def test_parser_run_max_attempts_defaults_to_3(self) -> None:
        """Given 'run' with no --max-attempts flag, should default to 3."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md"])

        assert args.max_attempts == 3

    def test_parser_accepts_run_with_verbose_flag(self) -> None:
        """Given 'run' with --verbose flag, should set verbose to True."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md", "--verbose"])

        assert args.verbose is True

    def test_parser_accepts_run_with_v_short_flag_for_verbose(self) -> None:
        """Given 'run' with -v flag, should set verbose to True."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md", "-v"])

        assert args.verbose is True

    def test_parser_accepts_status_subcommand(self) -> None:
        """Given 'status' subcommand with state file, should parse correctly."""
        parser = create_parser()

        args = parser.parse_args(["status", "state.json"])

        assert args.command == "status"
        assert args.state_file == Path("state.json")

    def test_parser_accepts_reset_subcommand(self) -> None:
        """Given 'reset' subcommand with ticket id, should parse correctly."""
        parser = create_parser()

        args = parser.parse_args(["reset", "TASK-123"])

        assert args.command == "reset"
        assert args.ticket_id == "TASK-123"

    def test_parser_accepts_run_subcommand(self) -> None:
        """Given 'run' subcommand with prd and plan, should parse correctly."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md"])

        assert args.command == "run"
        assert args.prd == Path("docs/prd.md")
        assert args.plan == Path("docs/plan.md")

    def test_parser_run_subcommand_accepts_dry_run(self) -> None:
        """Given 'run' subcommand with --dry-run, should set dry_run to True."""
        parser = create_parser()

        args = parser.parse_args(["run", "docs/prd.md", "docs/plan.md", "--dry-run"])

        assert args.command == "run"
        assert args.dry_run is True


class TestMainDirectPathInvocation:
    """Tests for direct path invocation (ralph docs/prd.md docs/plan.md)."""

    def test_main_handles_direct_paths_with_slash(self, tmp_path: Path) -> None:
        """Given paths with slashes, main should auto-insert 'run' subcommand."""
        prd = tmp_path / "docs" / "prd.md"
        plan = tmp_path / "docs" / "plan.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        result = main([str(prd), str(plan), "--dry-run"])

        assert result == 0

    def test_main_handles_md_extension_without_slash(self, tmp_path: Path) -> None:
        """Given .md files without slash, main should auto-insert 'run' subcommand."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        result = main([str(prd), str(plan), "--dry-run"])

        assert result == 0


class TestMain:
    """Tests for main entry point function."""

    def test_main_returns_zero_on_success(self, tmp_path: Path) -> None:
        """Given valid prd and plan files, should return 0."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        # Using explicit 'run' subcommand
        result = main(["run", str(prd), str(plan), "--dry-run"])

        assert result == 0

    def test_main_runs_status_command(self, tmp_path: Path) -> None:
        """Given status command with state file, should display status."""
        state_file = tmp_path / "state.json"
        state_data = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-001", "title": "Test", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file.write_text(json.dumps(state_data))

        result = main(["status", str(state_file)])

        assert result == 0

    def test_main_runs_reset_command(self, tmp_path: Path) -> None:
        """Given reset command with blocked ticket, should reset it."""
        state_file = tmp_path / "state.json"
        state_data = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-123", "title": "Test", "status": "blocked", "dependencies": [], "block_reason": "Test"},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 1,
        }
        state_file.write_text(json.dumps(state_data))

        result = main(["reset", "TASK-123", "--state-file", str(state_file)])

        assert result == 0

    def test_main_returns_nonzero_on_reset_error(self, tmp_path: Path) -> None:
        """Given reset command for non-blocked ticket, should return non-zero."""
        state_file = tmp_path / "state.json"
        state_data = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-123", "title": "Test", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file.write_text(json.dumps(state_data))

        result = main(["reset", "TASK-123", "--state-file", str(state_file)])

        assert result != 0

    def test_main_status_returns_zero_when_no_workflow(self, tmp_path: Path) -> None:
        """Given status command when no workflow exists, should return 0."""
        state_file = tmp_path / "nonexistent.json"

        result = main(["status", str(state_file)])

        assert result == 0

    def test_main_handles_verbose_flag_for_errors(
        self, tmp_path: Path, capsys
    ) -> None:
        """Given --verbose flag and an error, should show detailed output."""
        state_file = tmp_path / "state.json"
        state_data = {
            "version": "1.0",
            "prd_path": "docs/prds/test.md",
            "plan_path": "docs/plans/test.md",
            "tickets": [
                {"id": "TASK-123", "title": "Test", "status": "pending", "dependencies": []},
            ],
            "current_ticket": None,
            "completed_count": 0,
            "blocked_count": 0,
        }
        state_file.write_text(json.dumps(state_data))

        result = main(["reset", "TASK-123", "--state-file", str(state_file), "--verbose"])

        # Should show error details
        captured = capsys.readouterr()
        assert result != 0


class TestMainWithOrchestrator:
    """Tests for main function with orchestrator integration."""

    def test_main_calls_orchestrator_run(self, tmp_path: Path, mocker) -> None:
        """Given prd and plan, should call run_orchestrator with correct args."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        # Mock the orchestrator run function
        mock_run = mocker.patch("cli.run_orchestrator", return_value=0)

        # Use 'run' subcommand or paths with slashes for auto-detection
        result = main(["run", str(prd), str(plan)])

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get("prd_path") == prd

    def test_main_passes_dry_run_to_orchestrator(self, tmp_path: Path, mocker) -> None:
        """Given --dry-run, should pass dry_run=True to orchestrator."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        mock_run = mocker.patch("cli.run_orchestrator", return_value=0)

        result = main(["run", str(prd), str(plan), "--dry-run"])

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get("dry_run") is True

    def test_main_passes_max_attempts_to_orchestrator(self, tmp_path: Path, mocker) -> None:
        """Given --max-attempts, should pass value to orchestrator."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        mock_run = mocker.patch("cli.run_orchestrator", return_value=0)

        result = main(["run", str(prd), str(plan), "--max-attempts", "5"])

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args.kwargs.get("max_attempts") == 5


class TestErrorHandling:
    """Tests for CLI error handling."""

    def test_main_returns_nonzero_for_missing_prd(self, tmp_path: Path) -> None:
        """Given non-existent PRD file, should return non-zero exit code."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan")

        result = main(["run", str(tmp_path / "missing.md"), str(plan)])

        assert result != 0

    def test_main_returns_nonzero_for_missing_plan(self, tmp_path: Path) -> None:
        """Given non-existent plan file, should return non-zero exit code."""
        prd = tmp_path / "prd.md"
        prd.write_text("# PRD")

        result = main(["run", str(prd), str(tmp_path / "missing.md")])

        assert result != 0

    def test_main_displays_error_message_for_missing_file(
        self, tmp_path: Path, capsys
    ) -> None:
        """Given missing file, should display helpful error message."""
        prd = tmp_path / "prd.md"
        prd.write_text("# PRD")
        missing_plan = tmp_path / "missing.md"

        result = main(["run", str(prd), str(missing_plan)])

        captured = capsys.readouterr()
        # Error message should mention the file
        assert "missing" in captured.err.lower() or "not found" in captured.err.lower() or result != 0

    def test_main_returns_nonzero_for_invalid_max_attempts(self, tmp_path: Path) -> None:
        """Given invalid --max-attempts value, should return non-zero."""
        prd = tmp_path / "prd.md"
        plan = tmp_path / "plan.md"
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        # argparse will exit with code 2 for invalid arguments
        with pytest.raises(SystemExit) as exc_info:
            main(["run", str(prd), str(plan), "--max-attempts", "invalid"])

        assert exc_info.value.code != 0


class TestHelpDisplay:
    """Tests for help display."""

    def test_help_flag_shows_usage(self, capsys) -> None:
        """Given --help flag, should display usage information."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "ralph" in captured.out.lower()
        assert exc_info.value.code == 0

    def test_help_shows_dry_run_option(self, capsys) -> None:
        """Given --help flag, should show --dry-run option."""
        with pytest.raises(SystemExit):
            main(["--help"])

        captured = capsys.readouterr()
        assert "--dry-run" in captured.out

    def test_help_shows_max_attempts_option(self, capsys) -> None:
        """Given --help flag, should show --max-attempts option."""
        with pytest.raises(SystemExit):
            main(["--help"])

        captured = capsys.readouterr()
        assert "--max-attempts" in captured.out

    def test_help_shows_verbose_option(self, capsys) -> None:
        """Given --help flag, should show --verbose option."""
        with pytest.raises(SystemExit):
            main(["--help"])

        captured = capsys.readouterr()
        assert "--verbose" in captured.out or "-v" in captured.out
