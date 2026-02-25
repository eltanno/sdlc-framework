"""Integration tests for LoopLauncher using real subprocesses.

These tests launch real subprocesses (simple shell scripts or Python
snippets) to verify process management, log file creation, and crash
handling end-to-end.

Tests cover:
- TC-11: Correct number of real processes launched with distinct cwds
- TC-12: Crash handling — remaining processes survive when one crashes
- Log file creation and content
- CompletionResult accuracy with real processes
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest


def _create_mock_ralph_script(directory: Path, exit_code: int = 0, sleep_sec: float = 0.1) -> Path:
    """Create a minimal mock Ralph script that simulates `ralph run`.

    The script:
    - Accepts `run <prd> <plan> --skip-preflight` arguments
    - Prints a status message to stdout
    - Sleeps briefly to simulate work
    - Exits with the specified exit code

    Args:
        directory: Directory to create the script in.
        exit_code: Exit code the script should return.
        sleep_sec: Seconds to sleep (simulates work).

    Returns:
        Path to the created script.
    """
    ralph_dir = directory / ".claude" / "ralph"
    ralph_dir.mkdir(parents=True, exist_ok=True)
    script = ralph_dir / "ralph"
    script.write_text(
        f"""#!/bin/bash
echo "Ralph mock started in $(pwd)"
echo "Args: $@"
echo "RALPH_LABEL=${{RALPH_LABEL:-unset}}"
sleep {sleep_sec}
echo "Ralph mock completed"
exit {exit_code}
"""
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


class TestLoopLauncherIntegrationBasic:
    """Integration tests for basic launch functionality."""

    def test_launch_creates_real_processes(self, tmp_path: Path):
        """TC-11: Given 2 loops, when launched with real scripts, then
        2 processes run and complete successfully."""
        from commands.concurrent import LoopLauncher

        # Set up project root with mock ralph script
        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project, exit_code=0)

        # Set up worktree with mock ralph script
        wt1 = project / ".git-worktrees" / "ralph-1"
        wt1.mkdir(parents=True)
        _create_mock_ralph_script(wt1, exit_code=0)

        # Create PRD and plan files
        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=2,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[wt1],
        )

        assert len(results) == 2

        # Wait for all to complete
        completions = launcher.wait_all(results)

        assert len(completions) == 2
        assert all(c.exit_code == 0 for c in completions)

    def test_launch_processes_have_distinct_cwds(self, tmp_path: Path):
        """TC-11: Given 3 loops, when launched, then each process runs in
        a distinct working directory."""
        from commands.concurrent import LoopLauncher

        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project)

        wt1 = project / ".git-worktrees" / "ralph-1"
        wt2 = project / ".git-worktrees" / "ralph-2"
        for wt in [wt1, wt2]:
            wt.mkdir(parents=True)
            _create_mock_ralph_script(wt)

        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=3,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[wt1, wt2],
        )

        cwds = [r.cwd for r in results]
        assert len(set(cwds)) == 3  # All distinct
        assert project in cwds
        assert wt1 in cwds
        assert wt2 in cwds

        # Clean up
        launcher.wait_all(results)


class TestLoopLauncherIntegrationCrash:
    """Integration tests for crash handling."""

    def test_crash_in_one_loop_does_not_kill_others(self, tmp_path: Path):
        """TC-12: Given 3 loops where one crashes, when all complete, then
        the crashed loop reports non-zero exit and others report success."""
        from commands.concurrent import LoopLauncher

        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project, exit_code=0, sleep_sec=0.1)

        wt1 = project / ".git-worktrees" / "ralph-1"
        wt2 = project / ".git-worktrees" / "ralph-2"

        wt1.mkdir(parents=True)
        # ralph-1 crashes immediately
        _create_mock_ralph_script(wt1, exit_code=1, sleep_sec=0)

        wt2.mkdir(parents=True)
        _create_mock_ralph_script(wt2, exit_code=0, sleep_sec=0.1)

        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=3,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[wt1, wt2],
        )

        completions = launcher.wait_all(results)

        crashed = [c for c in completions if c.exit_code != 0]
        succeeded = [c for c in completions if c.exit_code == 0]

        assert len(crashed) == 1
        assert crashed[0].label == "ralph-1"
        assert crashed[0].exit_code == 1
        assert len(succeeded) == 2


class TestLoopLauncherIntegrationLogFiles:
    """Integration tests for log file creation and content."""

    def test_log_files_created_in_tmp(self, tmp_path: Path):
        """Given launched processes, when they complete, then log files
        exist in tmp/ with actual output content."""
        from commands.concurrent import LoopLauncher

        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project, exit_code=0)

        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=1,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[],
        )

        completions = launcher.wait_all(results)

        # Log file should exist and contain output
        log_file = completions[0].log_file
        assert log_file.exists()
        content = log_file.read_text()
        assert "Ralph mock started" in content
        assert "Ralph mock completed" in content

    def test_log_files_contain_correct_cwd(self, tmp_path: Path):
        """Given launched processes, when log is inspected, then it shows
        the process ran in the expected working directory."""
        from commands.concurrent import LoopLauncher

        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project, exit_code=0)

        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=1,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[],
        )

        completions = launcher.wait_all(results)

        content = completions[0].log_file.read_text()
        # The mock script prints its pwd
        assert str(project) in content


class TestLoopLauncherIntegrationRuntime:
    """Integration tests for runtime tracking accuracy."""

    def test_completion_result_has_positive_runtime(self, tmp_path: Path):
        """Given a process that runs briefly, when completed, then runtime
        is a positive number."""
        from commands.concurrent import LoopLauncher

        project = tmp_path / "project"
        project.mkdir()
        _create_mock_ralph_script(project, exit_code=0, sleep_sec=0.1)

        prd = project / "docs" / "prds" / "test.md"
        plan = project / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True)
        plan.parent.mkdir(parents=True)
        prd.write_text("# Test PRD")
        plan.write_text("# Test Plan")

        launcher = LoopLauncher(project_root=project)
        results = launcher.launch(
            count=1,
            prd_path=prd,
            plan_path=plan,
            worktree_paths=[],
        )

        completions = launcher.wait_all(results)

        # Runtime should be positive (process slept for 0.1s)
        assert completions[0].runtime_seconds > 0
