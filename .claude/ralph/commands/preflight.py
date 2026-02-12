"""Pre-flight test suite check for Ralph orchestrator.

Runs the full validation suite (typecheck, lint, test, build) once at startup
before processing any tickets. If any check fails, Ralph aborts immediately
with a clear error message instead of wasting retry attempts on every ticket.

Usage:
    from commands.preflight import run_preflight_check
    if not run_preflight_check(config_file):
        return 1  # abort
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional, Union

from commands.validate import ValidationResult, run_validation
from core.config import ConfigError, load_config

logger = logging.getLogger(__name__)


def run_preflight_check(config_file: Optional[Union[str, Path]]) -> bool:
    """Run pre-flight validation to ensure the test suite is green.

    Loads the project config and runs all validation checks (typecheck, lint,
    test, build). If any check fails, logs detailed failure information and
    returns False.

    Args:
        config_file: Path to config.yaml. If None, returns False immediately.

    Returns:
        True if all checks pass, False otherwise.
    """
    if config_file is None:
        logger.error("Pre-flight check skipped: no config file provided")
        return False

    config_path = Path(config_file)
    project_root = config_path.parent

    # Load configuration
    try:
        config = load_config(config_path)
    except ConfigError as e:
        logger.error(f"Pre-flight check failed: could not load config: {e}")
        return False

    logger.info("Running pre-flight test suite check...")
    start_time = time.monotonic()

    # Run all validation checks
    result = run_validation(config, project_root)

    elapsed = time.monotonic() - start_time

    if result.overall_passed:
        logger.info(
            f"Pre-flight check passed ({elapsed:.1f}s) -- test suite is green"
        )
        return True

    # Report failures
    logger.error(
        f"Pre-flight check FAILED ({elapsed:.1f}s) -- "
        "fix these issues before running Ralph:"
    )
    _log_failures(result)
    logger.error(
        "Aborting. Fix the failing checks and re-run, "
        "or use --skip-preflight to bypass."
    )
    return False


def _log_failures(result: ValidationResult) -> None:
    """Log details about which checks failed.

    For monorepo projects, logs failures per codebase.
    For single-codebase projects, logs each failing check.

    Args:
        result: The ValidationResult containing failure details.
    """
    if result.codebase_results:
        # Monorepo: report per-codebase failures
        for name, cb_result in result.codebase_results.items():
            if not cb_result.overall_passed:
                if cb_result.error:
                    logger.error(f"  {name}: {cb_result.error}")
                    continue
                _log_check_failures(name, cb_result)
    else:
        # Single codebase: report each failing check
        _log_check_failures(None, result)


def _log_check_failures(
    codebase_name: Optional[str], result: ValidationResult
) -> None:
    """Log individual check failures for a single codebase or project.

    Args:
        codebase_name: Name of codebase (None for single-codebase projects).
        result: ValidationResult for this codebase.
    """
    checks = [
        ("typecheck", result.typecheck),
        ("lint", result.lint),
        ("test", result.test),
        ("build", result.build),
    ]

    for check_name, check_result in checks:
        if not check_result.passed and not check_result.skipped:
            prefix = f"{codebase_name}/{check_name}" if codebase_name else check_name
            logger.error(f"  {prefix}: FAILED")
            # Log last few lines of error output for context
            error_text = check_result.error or check_result.output
            if error_text:
                lines = error_text.strip().splitlines()
                tail = lines[-5:] if len(lines) > 5 else lines
                for line in tail:
                    logger.error(f"    {line}")
