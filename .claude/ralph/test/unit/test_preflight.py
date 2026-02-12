"""Unit tests for commands/preflight.py - Pre-flight test suite check.

Tests that Ralph runs a pre-flight validation check at startup to catch
pre-existing test failures before wasting retry attempts on tickets.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

from commands.validate import CheckResult, ValidationResult
from core.config import Config, Codebase


class TestRunPreflightCheck:
    """Tests for the run_preflight_check function."""

    def test_preflight_passes_when_all_checks_pass(self, mocker, tmp_path: Path) -> None:
        """Given all validation checks pass, when preflight runs, then returns True."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(
            typecheck_command="tsc --noEmit",
            lint_command="eslint .",
            test_command="vitest run",
            build_command="tsc -b",
        )

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, False, "", ""),
            lint=CheckResult("lint", True, False, "", ""),
            test=CheckResult("test", True, False, "", ""),
            build=CheckResult("build", True, False, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        result = run_preflight_check(config_file)

        assert result is True

    def test_preflight_fails_when_tests_fail(self, mocker, tmp_path: Path) -> None:
        """Given test check fails, when preflight runs, then returns False."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(test_command="vitest run")

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", True, True, "", ""),
            test=CheckResult("test", False, False, "", "FAIL src/auth.test.ts"),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        result = run_preflight_check(config_file)

        assert result is False

    def test_preflight_fails_when_lint_fails(self, mocker, tmp_path: Path) -> None:
        """Given lint check fails, when preflight runs, then returns False."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(lint_command="eslint .")

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", False, False, "", "lint errors"),
            test=CheckResult("test", True, True, "", ""),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  lint: eslint .\n")

        result = run_preflight_check(config_file)

        assert result is False

    def test_preflight_reports_which_checks_failed_single_codebase(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given failures in single codebase, when preflight runs, then logs which checks failed."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(
            test_command="vitest run",
            lint_command="eslint .",
        )

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", False, False, "", "3 errors found"),
            test=CheckResult("test", False, False, "", "FAIL auth.test.ts"),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        with caplog.at_level(logging.ERROR):
            result = run_preflight_check(config_file)

        assert result is False
        # Check that specific failed check names appear in log output
        log_text = caplog.text
        assert "lint" in log_text.lower()
        assert "test" in log_text.lower()

    def test_preflight_reports_which_checks_failed_monorepo(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given failures in monorepo, when preflight runs, then logs codebase and check names."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(
            is_monorepo=True,
            codebases=[
                Codebase(name="frontend", path="frontend", test_command="vitest run"),
                Codebase(name="backend", path="backend", test_command="vitest run"),
            ],
        )

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            codebase_results={
                "frontend": ValidationResult(
                    typecheck=CheckResult("typecheck", True, True, "", ""),
                    lint=CheckResult("lint", True, True, "", ""),
                    test=CheckResult("test", False, False, "", "FAIL component.test.tsx"),
                    build=CheckResult("build", True, True, "", ""),
                ),
                "backend": ValidationResult(
                    typecheck=CheckResult("typecheck", True, True, "", ""),
                    lint=CheckResult("lint", True, True, "", ""),
                    test=CheckResult("test", True, False, "", ""),
                    build=CheckResult("build", True, True, "", ""),
                ),
            }
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  codebases:\n    - name: frontend\n")

        with caplog.at_level(logging.ERROR):
            result = run_preflight_check(config_file)

        assert result is False
        log_text = caplog.text
        assert "frontend" in log_text.lower()

    def test_preflight_logs_timing_on_success(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given successful preflight, when complete, then logs elapsed time."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(test_command="vitest run")

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", True, True, "", ""),
            test=CheckResult("test", True, False, "", ""),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        with caplog.at_level(logging.INFO):
            result = run_preflight_check(config_file)

        assert result is True
        log_text = caplog.text
        assert "pre-flight" in log_text.lower()
        assert "passed" in log_text.lower()

    def test_preflight_logs_timing_on_failure(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given failed preflight, when complete, then logs elapsed time."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(test_command="vitest run")

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", True, True, "", ""),
            test=CheckResult("test", False, False, "", "FAIL"),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        with caplog.at_level(logging.ERROR):
            result = run_preflight_check(config_file)

        assert result is False
        log_text = caplog.text
        assert "failed" in log_text.lower()

    def test_preflight_uses_project_root_from_config_path(
        self, mocker, tmp_path: Path
    ) -> None:
        """Given config in a subdirectory, when preflight runs, then uses parent as project root."""
        from commands.preflight import run_preflight_check

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.return_value = Config(test_command="vitest run")

        mock_validate = mocker.patch("commands.preflight.run_validation")
        mock_validate.return_value = ValidationResult(
            typecheck=CheckResult("typecheck", True, True, "", ""),
            lint=CheckResult("lint", True, True, "", ""),
            test=CheckResult("test", True, False, "", ""),
            build=CheckResult("build", True, True, "", ""),
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text("dev:\n  test: vitest run\n")

        run_preflight_check(config_file)

        # Verify run_validation was called with the config's parent directory
        mock_validate.assert_called_once()
        call_args = mock_validate.call_args
        # run_validation(config, project_root) -- positional args
        assert call_args[0][1] == tmp_path

    def test_preflight_handles_config_load_error(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given config load fails, when preflight runs, then returns False with error log."""
        from commands.preflight import run_preflight_check
        from core.config import ConfigError

        mock_load = mocker.patch("commands.preflight.load_config")
        mock_load.side_effect = ConfigError("Bad YAML")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content")

        with caplog.at_level(logging.ERROR):
            result = run_preflight_check(config_file)

        assert result is False
        assert "config" in caplog.text.lower() or "error" in caplog.text.lower()

    def test_preflight_returns_false_when_no_config_file(
        self, mocker, tmp_path: Path, caplog
    ) -> None:
        """Given None config_file, when preflight runs, then returns False."""
        from commands.preflight import run_preflight_check

        with caplog.at_level(logging.ERROR):
            result = run_preflight_check(None)

        assert result is False


class TestSkipPreflightFlag:
    """Tests that --skip-preflight flag is recognized by the arg parser."""

    def test_skip_preflight_flag_recognized(self) -> None:
        """Given --skip-preflight flag, when parsing args, then flag is set to True."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "prd.md", "plan.md", "--skip-preflight"])

        assert args.skip_preflight is True

    def test_skip_preflight_defaults_to_false(self) -> None:
        """Given no --skip-preflight flag, when parsing args, then flag defaults to False."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "prd.md", "plan.md"])

        assert args.skip_preflight is False
