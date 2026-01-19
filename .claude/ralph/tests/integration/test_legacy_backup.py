"""Tests for legacy shell script backup structure.

This module verifies that the shell scripts have been properly moved to
the ralph-legacy directory for rollback purposes.
"""

from pathlib import Path

import pytest


class TestLegacyBackupStructure:
    """Tests verifying the legacy backup structure is correct."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory.

        Returns:
            Path to the project root (3 levels up from this test file)
        """
        # This test file is at .claude/ralph/tests/integration/
        # Project root is 4 levels up
        return Path(__file__).parent.parent.parent.parent.parent

    @pytest.fixture
    def legacy_dir(self, project_root: Path) -> Path:
        """Get the legacy scripts directory.

        Args:
            project_root: Path to project root

        Returns:
            Path to the ralph-legacy directory
        """
        return project_root / ".claude" / "scripts" / "ralph-legacy"

    @pytest.fixture
    def python_dir(self, project_root: Path) -> Path:
        """Get the Python ralph directory.

        Args:
            project_root: Path to project root

        Returns:
            Path to the Python ralph directory
        """
        return project_root / ".claude" / "ralph"

    def test_legacy_directory_exists(self, legacy_dir: Path) -> None:
        """Verify the ralph-legacy directory exists."""
        assert legacy_dir.exists(), f"Legacy directory not found: {legacy_dir}"
        assert legacy_dir.is_dir(), f"Legacy path is not a directory: {legacy_dir}"

    def test_legacy_readme_exists(self, legacy_dir: Path) -> None:
        """Verify the legacy README exists and is marked deprecated."""
        readme = legacy_dir / "README.md"
        assert readme.exists(), f"Legacy README not found: {readme}"

        content = readme.read_text()
        assert "DEPRECATED" in content, "README should be marked DEPRECATED"
        assert ".claude/ralph/" in content, "README should reference Python version"

    def test_main_orchestrator_moved(self, legacy_dir: Path) -> None:
        """Verify ralph-prd.sh was moved to legacy."""
        orchestrator = legacy_dir / "ralph-prd.sh"
        assert orchestrator.exists(), f"Orchestrator not moved: {orchestrator}"

    def test_all_helper_scripts_moved(self, legacy_dir: Path) -> None:
        """Verify all helper scripts were moved to legacy."""
        expected_scripts = [
            "setup.sh",
            "get-next-ticket.sh",
            "ticket-start.sh",
            "ticket-done.sh",
            "mark-blocked.sh",
            "ticket-reset.sh",
            "validate.sh",
            "pr-flow.sh",
            "status.sh",
            "cleanup.sh",
            "parse-plan-deps.sh",
            "config-helpers.sh",
            "state-utils.sh",
        ]

        for script in expected_scripts:
            script_path = legacy_dir / script
            assert script_path.exists(), f"Script not moved: {script}"

    def test_test_scripts_moved(self, legacy_dir: Path) -> None:
        """Verify test scripts were moved to legacy."""
        test_scripts = [
            "test-get-next-ticket.sh",
            "test-mark-blocked.sh",
            "test-ticket-done.sh",
        ]

        for script in test_scripts:
            script_path = legacy_dir / script
            assert script_path.exists(), f"Test script not moved: {script}"

    def test_old_directory_removed(self, project_root: Path) -> None:
        """Verify the old ralph directory no longer exists."""
        old_dir = project_root / ".claude" / "scripts" / "ralph"
        assert not old_dir.exists(), f"Old directory should be removed: {old_dir}"

    def test_python_version_exists(self, python_dir: Path) -> None:
        """Verify the Python version exists and is ready to use."""
        assert python_dir.exists(), f"Python ralph directory not found: {python_dir}"

        # Check for key Python files
        assert (python_dir / "cli.py").exists(), "cli.py should exist"
        assert (python_dir / "ralph").exists(), "Shell wrapper should exist"
        assert (python_dir / "core").exists(), "core module should exist"
        assert (python_dir / "commands").exists(), "commands module should exist"

    def test_shell_wrapper_points_to_python(self, python_dir: Path) -> None:
        """Verify the shell wrapper invokes Python."""
        wrapper = python_dir / "ralph"
        assert wrapper.exists(), f"Shell wrapper not found: {wrapper}"

        content = wrapper.read_text()
        assert "python" in content.lower(), "Wrapper should invoke Python"
        assert "cli.py" in content, "Wrapper should call cli.py"

    def test_legacy_scripts_are_executable(self, legacy_dir: Path) -> None:
        """Verify legacy scripts maintain executable permissions."""
        # Key scripts that should be executable
        executable_scripts = [
            "ralph-prd.sh",
            "setup.sh",
            "get-next-ticket.sh",
            "validate.sh",
        ]

        for script in executable_scripts:
            script_path = legacy_dir / script
            if script_path.exists():
                # Check if file has execute permission (any of user/group/other)
                import stat
                mode = script_path.stat().st_mode
                is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
                assert is_executable, f"Script should be executable: {script}"
