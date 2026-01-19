"""Test that the Ralph package structure is correct."""

import os
import subprocess
from pathlib import Path

import pytest


# Get the ralph package directory
RALPH_DIR = Path(__file__).parent.parent.parent


class TestPackageStructure:
    """Tests for verifying the package structure."""

    def test_core_module_importable(self):
        """Core module should be importable."""
        from core import config, state, github, git

    def test_commands_module_importable(self):
        """Commands module should be importable."""
        from commands import (
            orchestrator,
            get_next,
            ticket_start,
            ticket_done,
            mark_blocked,
            ticket_reset,
            validate,
            pr_flow,
            setup,
            status,
            cleanup,
            parse_deps,
        )

    def test_core_module_has_docstring(self):
        """Core module should have a docstring."""
        import core
        assert core.__doc__ is not None

    def test_commands_module_has_docstring(self):
        """Commands module should have a docstring."""
        import commands
        assert commands.__doc__ is not None


class TestRequirements:
    """Tests for requirements files."""

    def test_requirements_txt_exists(self):
        """requirements.txt should exist."""
        req_file = RALPH_DIR / "requirements.txt"
        assert req_file.exists(), f"requirements.txt not found at {req_file}"

    def test_requirements_txt_has_pyyaml(self):
        """requirements.txt should include PyYAML."""
        req_file = RALPH_DIR / "requirements.txt"
        content = req_file.read_text()
        # Check for pyyaml (case-insensitive as pip normalizes names)
        assert "pyyaml" in content.lower(), "PyYAML not found in requirements.txt"

    def test_requirements_dev_txt_exists(self):
        """requirements-dev.txt should exist."""
        req_file = RALPH_DIR / "requirements-dev.txt"
        assert req_file.exists(), f"requirements-dev.txt not found at {req_file}"

    def test_requirements_dev_has_pytest(self):
        """requirements-dev.txt should include pytest."""
        req_file = RALPH_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest" in content.lower(), "pytest not found in requirements-dev.txt"

    def test_requirements_dev_has_pytest_cov(self):
        """requirements-dev.txt should include pytest-cov."""
        req_file = RALPH_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest-cov" in content.lower(), "pytest-cov not found in requirements-dev.txt"

    def test_requirements_dev_has_pytest_mock(self):
        """requirements-dev.txt should include pytest-mock."""
        req_file = RALPH_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest-mock" in content.lower(), "pytest-mock not found in requirements-dev.txt"


class TestShellWrapper:
    """Tests for the shell wrapper entry point."""

    def test_shell_wrapper_exists(self):
        """ralph shell wrapper should exist."""
        wrapper = RALPH_DIR / "ralph"
        assert wrapper.exists(), f"Shell wrapper not found at {wrapper}"

    def test_shell_wrapper_is_executable(self):
        """ralph shell wrapper should be executable."""
        wrapper = RALPH_DIR / "ralph"
        assert os.access(wrapper, os.X_OK), "Shell wrapper is not executable"

    def test_shell_wrapper_invokes_python(self):
        """ralph shell wrapper should invoke Python cli.py."""
        wrapper = RALPH_DIR / "ralph"
        content = wrapper.read_text()
        # Should reference cli.py
        assert "cli.py" in content, "Shell wrapper does not reference cli.py"


class TestCliModule:
    """Tests for the CLI entry point module."""

    def test_cli_module_exists(self):
        """cli.py should exist."""
        cli_file = RALPH_DIR / "cli.py"
        assert cli_file.exists(), f"cli.py not found at {cli_file}"

    def test_cli_module_has_main(self):
        """cli.py should have a main function or entry point."""
        cli_file = RALPH_DIR / "cli.py"
        content = cli_file.read_text()
        # Should have either a main() function or if __name__ == '__main__'
        has_main = "def main" in content or '__name__' in content
        assert has_main, "cli.py should have main function or __main__ block"
