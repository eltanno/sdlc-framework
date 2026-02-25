"""Run validation checks for a ticket.

This module handles:
- Running configured test commands
- Running lint and type checks
- Running build commands
- Aggregating results

Supports both single-codebase and monorepo configurations. For monorepo
projects, validation runs against each codebase independently.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import Codebase, Config


@dataclass
class CheckResult:
    """Result of a single validation check.

    Attributes:
        name: Name of the check (e.g., "typecheck", "lint", "test", "build")
        passed: True if check passed or was skipped
        skipped: True if check was skipped (empty command or echo command)
        output: Stdout from the command
        error: Stderr from the command or error message
    """

    name: str
    passed: bool
    skipped: bool = False
    output: str = ""
    error: str = ""


@dataclass
class ValidationResult:
    """Result of all validation checks for a single codebase.

    Attributes:
        typecheck: Result of type checking
        lint: Result of linting
        test: Result of testing
        build: Result of building
        codebase_results: For monorepos, results keyed by codebase name
        error: Error message if validation couldn't run at all
    """

    typecheck: CheckResult = field(
        default_factory=lambda: CheckResult("typecheck", True, True)
    )
    lint: CheckResult = field(default_factory=lambda: CheckResult("lint", True, True))
    test: CheckResult = field(default_factory=lambda: CheckResult("test", True, True))
    build: CheckResult = field(default_factory=lambda: CheckResult("build", True, True))
    codebase_results: dict[str, "ValidationResult"] = field(default_factory=dict)
    error: str = ""

    @property
    def overall_passed(self) -> bool:
        """Check if all validation checks passed.

        Returns:
            True if all checks passed (including skipped checks)
        """
        # If there's a top-level error, fail
        if self.error:
            return False

        # For monorepo, check all codebase results
        if self.codebase_results:
            return all(r.overall_passed for r in self.codebase_results.values())

        # For single codebase, check individual results
        return all([self.typecheck.passed, self.lint.passed, self.test.passed, self.build.passed])

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary format.

        Returns:
            Dict with check results as 'pass', 'fail', or 'skip'
        """

        def check_status(result: CheckResult) -> str:
            if result.skipped:
                return "skip"
            return "pass" if result.passed else "fail"

        result: dict[str, Any] = {
            "typecheck": check_status(self.typecheck),
            "lint": check_status(self.lint),
            "test": check_status(self.test),
            "build": check_status(self.build),
            "overall": "pass" if self.overall_passed else "fail",
        }

        if self.codebase_results:
            result["codebases"] = {
                name: cb_result.to_dict()
                for name, cb_result in self.codebase_results.items()
            }

        return result


def run_command(
    command: str, working_dir: Path, timeout: int = 300, name: str = ""
) -> CheckResult:
    """Run a single validation command.

    Args:
        command: The command to run
        working_dir: Directory to run the command in
        timeout: Maximum seconds to wait for command (default 300)
        name: Name for the CheckResult (e.g., "typecheck", "lint")

    Returns:
        CheckResult with pass/fail status and output
    """
    # Empty command = skip
    if not command or command.strip() == "":
        return CheckResult(
            name=name,
            passed=True,
            skipped=True,
            output="",
            error="",
        )

    # Echo commands are effectively skips
    if command.strip().startswith("echo"):
        return CheckResult(
            name=name,
            passed=True,
            skipped=True,
            output="",
            error="",
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return CheckResult(
            name=name,
            passed=result.returncode == 0,
            skipped=False,
            output=result.stdout,
            error=result.stderr,
        )

    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            passed=False,
            skipped=False,
            output="",
            error=f"Command timed out after {timeout} seconds",
        )


def run_validation(config: Config, project_root: Path) -> ValidationResult:
    """Run all validation checks according to config.

    For single-codebase projects, runs typecheck, lint, test, build commands
    from the project root.

    For monorepo projects, runs each codebase's commands from within that
    codebase's directory.

    Args:
        config: Loaded configuration
        project_root: Root directory of the project

    Returns:
        ValidationResult with all check results
    """
    if config.is_monorepo:
        return _validate_monorepo(config, project_root)
    else:
        return _validate_single_codebase(config, project_root)


def _run_all_checks(
    commands: Config | Codebase,
    working_dir: Path,
) -> ValidationResult:
    """Run typecheck, lint, test, and build checks for a single codebase.

    Args:
        commands: Object with typecheck_command, lint_command, test_command,
                  build_command attributes (Config or Codebase)
        working_dir: Directory to run commands in

    Returns:
        ValidationResult with all check results
    """
    typecheck_result = run_command(commands.typecheck_command, working_dir, name="typecheck")
    lint_result = run_command(commands.lint_command, working_dir, name="lint")
    test_result = run_command(commands.test_command, working_dir, name="test")
    build_result = run_command(commands.build_command, working_dir, name="build")

    return ValidationResult(
        typecheck=typecheck_result,
        lint=lint_result,
        test=test_result,
        build=build_result,
    )


def _validate_single_codebase(
    config: Config, project_root: Path
) -> ValidationResult:
    """Run validation for a single-codebase project.

    Args:
        config: Configuration with dev.* commands
        project_root: Project root directory

    Returns:
        ValidationResult with all check results
    """
    return _run_all_checks(config, project_root)


def _validate_monorepo(config: Config, project_root: Path) -> ValidationResult:
    """Run validation for each codebase in a monorepo.

    Args:
        config: Configuration with dev.codebases.* entries
        project_root: Project root directory

    Returns:
        ValidationResult with codebase_results populated
    """
    codebase_results: dict[str, ValidationResult] = {}

    for codebase in config.codebases:
        codebase_path = project_root / codebase.path

        # Check if codebase directory exists
        if not codebase_path.exists():
            codebase_results[codebase.name] = ValidationResult(
                error=f"Codebase directory not found: {codebase_path}"
            )
            continue

        codebase_results[codebase.name] = _run_all_checks(codebase, codebase_path)

    return ValidationResult(codebase_results=codebase_results)
