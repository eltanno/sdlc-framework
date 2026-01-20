"""Unit tests for commands/validate.py - Validation command.

Tests running validation checks (typecheck, lint, test, build) for both
single-codebase and monorepo project structures.
"""

import subprocess
from pathlib import Path


from commands import validate
from core.config import Config, Codebase


class TestRunCommand:
    """Tests for the run_command helper function."""

    def test_run_command_success(self, mocker) -> None:
        """Given a successful command, when run, then returns CheckResult with pass."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success output"
        mock_run.return_value.stderr = ""

        result = validate.run_command("npm test", Path("/project"))

        assert result.passed is True
        assert result.output == "Success output"
        assert result.error == ""

    def test_run_command_failure(self, mocker) -> None:
        """Given a failing command, when run, then returns CheckResult with fail."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error: test failed"

        result = validate.run_command("npm test", Path("/project"))

        assert result.passed is False
        assert result.error == "Error: test failed"

    def test_run_command_empty_returns_skip(self, mocker) -> None:
        """Given empty command string, when run, then returns skipped result."""
        result = validate.run_command("", Path("/project"))

        assert result.passed is True
        assert result.skipped is True

    def test_run_command_echo_returns_skip(self, mocker) -> None:
        """Given echo command, when run, then returns skipped result."""
        result = validate.run_command("echo 'No tests'", Path("/project"))

        assert result.passed is True
        assert result.skipped is True

    def test_run_command_uses_correct_working_dir(self, mocker) -> None:
        """Given a working directory, when run, then subprocess uses that cwd."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        validate.run_command("npm test", Path("/my/project"))

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == Path("/my/project")

    def test_run_command_timeout_handling(self, mocker) -> None:
        """Given a command that times out, when run, then returns failure."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired("npm test", 60)

        result = validate.run_command("npm test", Path("/project"), timeout=60)

        assert result.passed is False
        assert "timed out" in result.error.lower()


class TestCheckResultDataclass:
    """Tests for the CheckResult dataclass."""

    def test_check_result_creation(self) -> None:
        """Given valid inputs, when CheckResult created, then all fields set."""
        result = validate.CheckResult(
            name="test",
            passed=True,
            skipped=False,
            output="output",
            error="",
        )

        assert result.name == "test"
        assert result.passed is True
        assert result.skipped is False
        assert result.output == "output"
        assert result.error == ""


class TestValidationResultDataclass:
    """Tests for the ValidationResult dataclass."""

    def test_validation_result_overall_pass(self) -> None:
        """Given all checks pass, when overall checked, then returns pass."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", True, False, "", ""),
            lint=validate.CheckResult("lint", True, False, "", ""),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, False, "", ""),
        )

        assert result.overall_passed is True

    def test_validation_result_overall_fail_on_any_failure(self) -> None:
        """Given any check fails, when overall checked, then returns fail."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", True, False, "", ""),
            lint=validate.CheckResult("lint", False, False, "", "lint error"),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, False, "", ""),
        )

        assert result.overall_passed is False

    def test_validation_result_skipped_counts_as_pass(self) -> None:
        """Given skipped checks, when overall checked, then counts as pass."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", True, True, "", ""),
            lint=validate.CheckResult("lint", True, True, "", ""),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, True, "", ""),
        )

        assert result.overall_passed is True


class TestValidateSingleCodebase:
    """Tests for validating a single-codebase project."""

    def test_validate_runs_all_checks(self, mocker, tmp_path: Path) -> None:
        """Given single-codebase config, when validate, then runs all 4 checks."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        config = Config(
            typecheck_command="mypy .",
            lint_command="ruff check .",
            test_command="pytest",
            build_command="python -m build",
        )

        result = validate.run_validation(config, tmp_path)

        assert result.typecheck.passed is True
        assert result.lint.passed is True
        assert result.test.passed is True
        assert result.build.passed is True
        assert mock_run.call_count == 4

    def test_validate_continues_after_failure(self, mocker, tmp_path: Path) -> None:
        """Given a failing check, when validate, then continues running other checks."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        # First call (typecheck) fails, rest succeed
        mock_run.side_effect = [
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "type error"})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
            type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
        ]

        config = Config(
            typecheck_command="mypy .",
            lint_command="ruff check .",
            test_command="pytest",
            build_command="python -m build",
        )

        result = validate.run_validation(config, tmp_path)

        assert result.typecheck.passed is False
        assert result.lint.passed is True
        assert result.test.passed is True
        assert result.build.passed is True
        assert result.overall_passed is False

    def test_validate_skips_empty_commands(self, mocker, tmp_path: Path) -> None:
        """Given empty commands, when validate, then skips those checks."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        config = Config(
            typecheck_command="",
            lint_command="",
            test_command="pytest",
            build_command="",
        )

        result = validate.run_validation(config, tmp_path)

        assert result.typecheck.skipped is True
        assert result.lint.skipped is True
        assert result.test.passed is True
        assert result.test.skipped is False
        assert result.build.skipped is True
        assert mock_run.call_count == 1  # Only test runs


class TestValidateMonorepo:
    """Tests for validating a monorepo project."""

    def test_validate_monorepo_runs_all_codebases(self, mocker, tmp_path: Path) -> None:
        """Given monorepo config, when validate, then validates all codebases."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        # Create codebase directories
        (tmp_path / "mobile").mkdir()
        (tmp_path / "backend").mkdir()

        config = Config(
            is_monorepo=True,
            codebases=[
                Codebase(
                    name="mobile",
                    path="mobile",
                    test_command="npm test",
                ),
                Codebase(
                    name="backend",
                    path="backend",
                    test_command="pytest",
                ),
            ],
        )

        result = validate.run_validation(config, tmp_path)

        # Should have results for both codebases
        assert "mobile" in result.codebase_results
        assert "backend" in result.codebase_results
        assert result.overall_passed is True

    def test_validate_monorepo_uses_codebase_paths(self, mocker, tmp_path: Path) -> None:
        """Given monorepo, when validate, then uses correct cwd for each codebase."""
        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        # Create codebase directory
        (tmp_path / "api").mkdir()

        config = Config(
            is_monorepo=True,
            codebases=[
                Codebase(
                    name="api",
                    path="api",
                    test_command="pytest",
                ),
            ],
        )

        validate.run_validation(config, tmp_path)

        # Check subprocess was called with codebase path
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == tmp_path / "api"

    def test_validate_monorepo_fails_if_any_codebase_fails(
        self, mocker, tmp_path: Path
    ) -> None:
        """Given one failing codebase, when validate, then overall fails."""
        call_count = [0]

        def mock_subprocess(*args, **kwargs):
            call_count[0] += 1
            result = type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            # Fail the second codebase's test
            if "backend" in str(kwargs.get("cwd", "")):
                result.returncode = 1
                result.stderr = "test failed"
            return result

        mock_run = mocker.patch("commands.validate.subprocess.run")
        mock_run.side_effect = mock_subprocess

        # Create codebase directories
        (tmp_path / "mobile").mkdir()
        (tmp_path / "backend").mkdir()

        config = Config(
            is_monorepo=True,
            codebases=[
                Codebase(name="mobile", path="mobile", test_command="npm test"),
                Codebase(name="backend", path="backend", test_command="pytest"),
            ],
        )

        result = validate.run_validation(config, tmp_path)

        assert result.codebase_results["mobile"].overall_passed is True
        assert result.codebase_results["backend"].overall_passed is False
        assert result.overall_passed is False

    def test_validate_monorepo_missing_directory_fails(
        self, mocker, tmp_path: Path
    ) -> None:
        """Given missing codebase directory, when validate, then that codebase fails."""
        config = Config(
            is_monorepo=True,
            codebases=[
                Codebase(name="missing", path="missing", test_command="npm test"),
            ],
        )

        result = validate.run_validation(config, tmp_path)

        assert result.codebase_results["missing"].overall_passed is False
        assert "not found" in result.codebase_results["missing"].error.lower()


class TestValidationOutput:
    """Tests for validation result formatting."""

    def test_to_dict_single_codebase(self, tmp_path: Path) -> None:
        """Given single-codebase result, when to_dict, then returns expected format."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", True, False, "", ""),
            lint=validate.CheckResult("lint", True, False, "", ""),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, False, "", ""),
        )

        as_dict = result.to_dict()

        assert as_dict["typecheck"] == "pass"
        assert as_dict["lint"] == "pass"
        assert as_dict["test"] == "pass"
        assert as_dict["build"] == "pass"
        assert as_dict["overall"] == "pass"

    def test_to_dict_with_skipped(self, tmp_path: Path) -> None:
        """Given skipped checks, when to_dict, then shows 'skip'."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", True, True, "", ""),
            lint=validate.CheckResult("lint", True, False, "", ""),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, True, "", ""),
        )

        as_dict = result.to_dict()

        assert as_dict["typecheck"] == "skip"
        assert as_dict["lint"] == "pass"
        assert as_dict["build"] == "skip"

    def test_to_dict_with_failure(self, tmp_path: Path) -> None:
        """Given failed checks, when to_dict, then shows 'fail'."""
        result = validate.ValidationResult(
            typecheck=validate.CheckResult("typecheck", False, False, "", "error"),
            lint=validate.CheckResult("lint", True, False, "", ""),
            test=validate.CheckResult("test", True, False, "", ""),
            build=validate.CheckResult("build", True, False, "", ""),
        )

        as_dict = result.to_dict()

        assert as_dict["typecheck"] == "fail"
        assert as_dict["overall"] == "fail"
