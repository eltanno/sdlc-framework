"""Unit tests for the LoopLauncher in concurrent.py.

Tests cover:
- Launching the correct number of processes (TC-11)
- Each process runs in its own working directory
- Each process writes to a dedicated log file in tmp/
- Crash handling: remaining processes continue when one crashes (TC-12)
- All processes completing reports exit codes and runtimes
- Startup failure handling
- LaunchResult dataclass fields
- Log file path computation

PRD Test Cases covered: TC-11, TC-12
"""

from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest


# ============================================================================
# Tests: LaunchResult dataclass
# ============================================================================


class TestLaunchResult:
    """Tests for the LaunchResult dataclass."""

    def test_launch_result_has_required_fields(self):
        """Given a LaunchResult, when inspected, then it has process, label,
        cwd, log_file, and start_time fields."""
        from commands.concurrent import LaunchResult

        result = LaunchResult(
            process=MagicMock(),
            label="ralph-0",
            cwd=Path("/project"),
            log_file=Path("/project/tmp/ralph-0-2026-02-25.log"),
            start_time=datetime.now(),
        )

        assert result.label == "ralph-0"
        assert result.cwd == Path("/project")
        assert result.log_file == Path("/project/tmp/ralph-0-2026-02-25.log")
        assert result.process is not None
        assert result.start_time is not None

    def test_launch_result_stores_process_reference(self):
        """Given a LaunchResult with a process, when inspected, then process
        is accessible for polling and termination."""
        from commands.concurrent import LaunchResult

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None

        result = LaunchResult(
            process=mock_proc,
            label="ralph-1",
            cwd=Path("/project/.git-worktrees/ralph-1"),
            log_file=Path("/project/tmp/ralph-1-2026-02-25.log"),
            start_time=datetime.now(),
        )

        assert result.process.pid == 12345
        assert result.process.poll() is None


# ============================================================================
# Tests: LoopLauncher log file path computation
# ============================================================================


class TestLoopLauncherLogPaths:
    """Tests for log file path computation."""

    def test_log_file_path_in_tmp_directory(self, tmp_path: Path):
        """Given a project root, when computing log path, then it is in tmp/ directory."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        log_path = launcher.log_file_path("ralph-0")

        assert log_path.parent == tmp_path / "tmp"

    def test_log_file_path_includes_label(self, tmp_path: Path):
        """Given a label, when computing log path, then filename includes the label."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        log_path = launcher.log_file_path("ralph-1")

        assert "ralph-1" in log_path.name

    def test_log_file_path_includes_date(self, tmp_path: Path):
        """Given today's date, when computing log path, then filename includes date stamp."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        log_path = launcher.log_file_path("ralph-0")

        today = datetime.now().strftime("%Y-%m-%d")
        assert today in log_path.name

    def test_log_file_paths_are_unique_per_label(self, tmp_path: Path):
        """Given different labels, when computing log paths, then each path is unique."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)

        paths = [launcher.log_file_path(f"ralph-{i}") for i in range(4)]

        assert len(set(paths)) == 4


# ============================================================================
# Tests: LoopLauncher.launch
# ============================================================================


class TestLoopLauncherLaunch:
    """Tests for launching parallel Ralph subprocesses."""

    def test_launch_returns_correct_number_of_results(self, tmp_path: Path):
        """TC-11: Given a request for 3 loops, when launched, then 3 LaunchResult
        objects are returned."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        worktree_paths = [
            tmp_path / ".git-worktrees" / "ralph-1",
            tmp_path / ".git-worktrees" / "ralph-2",
        ]
        for wt in worktree_paths:
            wt.mkdir(parents=True, exist_ok=True)

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            results = launcher.launch(
                count=3,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=worktree_paths,
            )

        assert len(results) == 3

    def test_launch_ralph_0_runs_in_project_root(self, tmp_path: Path):
        """Given a launch of 3 loops, when inspecting ralph-0, then its cwd is
        the project root directory."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        worktree_paths = [tmp_path / ".git-worktrees" / "ralph-1"]
        for wt in worktree_paths:
            wt.mkdir(parents=True, exist_ok=True)

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            results = launcher.launch(
                count=2,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=worktree_paths,
            )

        # ralph-0 should have cwd = project root
        ralph_0 = [r for r in results if r.label == "ralph-0"][0]
        assert ralph_0.cwd == tmp_path

    def test_launch_worktrees_run_in_worktree_dirs(self, tmp_path: Path):
        """Given a launch of 3 loops, when inspecting ralph-1 and ralph-2, then
        their cwds are the worktree directories."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        wt1 = tmp_path / ".git-worktrees" / "ralph-1"
        wt2 = tmp_path / ".git-worktrees" / "ralph-2"
        wt1.mkdir(parents=True, exist_ok=True)
        wt2.mkdir(parents=True, exist_ok=True)

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            results = launcher.launch(
                count=3,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[wt1, wt2],
            )

        ralph_1 = [r for r in results if r.label == "ralph-1"][0]
        ralph_2 = [r for r in results if r.label == "ralph-2"][0]
        assert ralph_1.cwd == wt1
        assert ralph_2.cwd == wt2

    def test_launch_creates_tmp_directory(self, tmp_path: Path):
        """Given tmp/ doesn't exist, when launching, then tmp/ is created."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        assert not (tmp_path / "tmp").exists()

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            launcher.launch(
                count=1,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[],
            )

        assert (tmp_path / "tmp").exists()

    def test_launch_each_process_gets_dedicated_log_file(self, tmp_path: Path):
        """Given 3 launched loops, when inspecting results, then each has a unique log file."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        wt1 = tmp_path / ".git-worktrees" / "ralph-1"
        wt2 = tmp_path / ".git-worktrees" / "ralph-2"
        wt1.mkdir(parents=True, exist_ok=True)
        wt2.mkdir(parents=True, exist_ok=True)

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            results = launcher.launch(
                count=3,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[wt1, wt2],
            )

        log_files = [r.log_file for r in results]
        assert len(set(log_files)) == 3  # All unique

    def test_launch_popen_called_with_correct_command(self, tmp_path: Path):
        """Given a launch, when Popen is called, then the command includes
        ralph run with prd and plan paths."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            launcher.launch(
                count=1,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[],
            )

        # At least one Popen call should contain 'ralph' and 'run'
        assert mock_popen.called
        call_args = mock_popen.call_args_list[0]
        cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args", [])
        cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
        assert "ralph" in cmd_str
        assert "run" in cmd_str

    def test_launch_popen_called_with_correct_cwd(self, tmp_path: Path):
        """Given a launch with worktrees, when Popen is called for each, then
        cwd is set to the correct directory."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        wt1 = tmp_path / ".git-worktrees" / "ralph-1"
        wt1.mkdir(parents=True, exist_ok=True)

        popen_calls = []

        def track_popen(*args, **kwargs):
            popen_calls.append(kwargs)
            proc = MagicMock()
            proc.pid = 1000 + len(popen_calls)
            proc.poll.return_value = None
            return proc

        with patch("commands.concurrent.subprocess.Popen", side_effect=track_popen):
            launcher.launch(
                count=2,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[wt1],
            )

        cwds = [c.get("cwd") for c in popen_calls]
        # ralph-0 -> project root, ralph-1 -> worktree
        assert tmp_path in cwds
        assert wt1 in cwds

    def test_launch_popen_stdout_redirected_to_log_file(self, tmp_path: Path):
        """Given a launch, when Popen is called, then stdout and stderr are
        redirected to the log file."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        popen_kwargs = []

        def track_popen(*args, **kwargs):
            popen_kwargs.append(kwargs)
            proc = MagicMock()
            proc.pid = 1000
            proc.poll.return_value = None
            return proc

        with patch("commands.concurrent.subprocess.Popen", side_effect=track_popen):
            launcher.launch(
                count=1,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[],
            )

        # stdout should be a file handle (not None or PIPE)
        assert "stdout" in popen_kwargs[0]
        assert popen_kwargs[0]["stdout"] is not None

    def test_launch_labels_are_correct(self, tmp_path: Path):
        """Given a launch of 3 loops, when inspecting results, then labels are
        ralph-0, ralph-1, ralph-2."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        wt1 = tmp_path / ".git-worktrees" / "ralph-1"
        wt2 = tmp_path / ".git-worktrees" / "ralph-2"
        wt1.mkdir(parents=True, exist_ok=True)
        wt2.mkdir(parents=True, exist_ok=True)

        with patch("commands.concurrent.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1000
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            results = launcher.launch(
                count=3,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[wt1, wt2],
            )

        labels = sorted([r.label for r in results])
        assert labels == ["ralph-0", "ralph-1", "ralph-2"]


# ============================================================================
# Tests: LoopLauncher.wait_all
# ============================================================================


class TestLoopLauncherWaitAll:
    """Tests for waiting on all processes and collecting results."""

    def test_wait_all_returns_completion_results(self, tmp_path: Path):
        """Given all processes complete, when wait_all is called, then it returns
        exit codes and runtimes for each."""
        from commands.concurrent import LoopLauncher, LaunchResult, CompletionResult

        launcher = LoopLauncher(project_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0

        launch_results = [
            LaunchResult(
                process=mock_proc,
                label="ralph-0",
                cwd=tmp_path,
                log_file=tmp_path / "tmp" / "ralph-0.log",
                start_time=datetime.now(),
            ),
        ]

        completions = launcher.wait_all(launch_results)

        assert len(completions) == 1
        assert completions[0].label == "ralph-0"
        assert completions[0].exit_code == 0
        assert completions[0].runtime_seconds >= 0

    def test_wait_all_reports_crashed_process(self, tmp_path: Path):
        """TC-12: Given a process that crashes (non-zero exit), when wait_all
        completes, then the crash is reported with the exit code."""
        from commands.concurrent import LoopLauncher, LaunchResult, CompletionResult

        launcher = LoopLauncher(project_root=tmp_path)

        # Process 1: succeeds
        proc_ok = MagicMock()
        proc_ok.wait.return_value = 0
        proc_ok.returncode = 0

        # Process 2: crashes
        proc_crash = MagicMock()
        proc_crash.wait.return_value = 1
        proc_crash.returncode = 1

        # Process 3: succeeds
        proc_ok2 = MagicMock()
        proc_ok2.wait.return_value = 0
        proc_ok2.returncode = 0

        now = datetime.now()
        launch_results = [
            LaunchResult(
                process=proc_ok, label="ralph-0",
                cwd=tmp_path, log_file=tmp_path / "tmp" / "r0.log",
                start_time=now,
            ),
            LaunchResult(
                process=proc_crash, label="ralph-1",
                cwd=tmp_path / ".git-worktrees" / "ralph-1",
                log_file=tmp_path / "tmp" / "r1.log",
                start_time=now,
            ),
            LaunchResult(
                process=proc_ok2, label="ralph-2",
                cwd=tmp_path / ".git-worktrees" / "ralph-2",
                log_file=tmp_path / "tmp" / "r2.log",
                start_time=now,
            ),
        ]

        completions = launcher.wait_all(launch_results)

        assert len(completions) == 3
        crashed = [c for c in completions if c.exit_code != 0]
        succeeded = [c for c in completions if c.exit_code == 0]
        assert len(crashed) == 1
        assert crashed[0].label == "ralph-1"
        assert crashed[0].exit_code == 1
        assert len(succeeded) == 2

    def test_wait_all_does_not_kill_remaining_on_crash(self, tmp_path: Path):
        """TC-12: Given a process crashes, when wait_all continues, then
        remaining processes are NOT terminated."""
        from commands.concurrent import LoopLauncher, LaunchResult

        launcher = LoopLauncher(project_root=tmp_path)

        proc_ok = MagicMock()
        proc_ok.wait.return_value = 0
        proc_ok.returncode = 0

        proc_crash = MagicMock()
        proc_crash.wait.return_value = 1
        proc_crash.returncode = 1

        now = datetime.now()
        launch_results = [
            LaunchResult(
                process=proc_ok, label="ralph-0",
                cwd=tmp_path, log_file=tmp_path / "tmp" / "r0.log",
                start_time=now,
            ),
            LaunchResult(
                process=proc_crash, label="ralph-1",
                cwd=tmp_path / ".git-worktrees" / "ralph-1",
                log_file=tmp_path / "tmp" / "r1.log",
                start_time=now,
            ),
        ]

        launcher.wait_all(launch_results)

        # Neither process should have terminate() called
        proc_ok.terminate.assert_not_called()
        proc_crash.terminate.assert_not_called()

    def test_wait_all_collects_runtime_for_each(self, tmp_path: Path):
        """Given processes complete at different times, when wait_all returns,
        then each CompletionResult has accurate runtime."""
        from commands.concurrent import LoopLauncher, LaunchResult

        launcher = LoopLauncher(project_root=tmp_path)

        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0

        start = datetime.now()
        launch_results = [
            LaunchResult(
                process=mock_proc, label="ralph-0",
                cwd=tmp_path, log_file=tmp_path / "tmp" / "r0.log",
                start_time=start,
            ),
        ]

        completions = launcher.wait_all(launch_results)

        assert completions[0].runtime_seconds >= 0


# ============================================================================
# Tests: CompletionResult dataclass
# ============================================================================


class TestCompletionResult:
    """Tests for the CompletionResult dataclass."""

    def test_completion_result_has_required_fields(self):
        """Given a CompletionResult, when inspected, then it has label,
        exit_code, runtime_seconds, and log_file."""
        from commands.concurrent import CompletionResult

        result = CompletionResult(
            label="ralph-0",
            exit_code=0,
            runtime_seconds=120.5,
            log_file=Path("/project/tmp/ralph-0.log"),
        )

        assert result.label == "ralph-0"
        assert result.exit_code == 0
        assert result.runtime_seconds == 120.5
        assert result.log_file == Path("/project/tmp/ralph-0.log")

    def test_completion_result_exit_code_non_zero_for_crash(self):
        """Given a crashed process, when CompletionResult is created, then
        exit_code is non-zero."""
        from commands.concurrent import CompletionResult

        result = CompletionResult(
            label="ralph-1",
            exit_code=1,
            runtime_seconds=45.0,
            log_file=Path("/project/tmp/ralph-1.log"),
        )

        assert result.exit_code != 0


# ============================================================================
# Tests: LoopLauncher startup failure handling
# ============================================================================


class TestLoopLauncherStartupFailure:
    """Tests for handling startup failures during launch."""

    def test_launch_raises_on_startup_failure(self, tmp_path: Path):
        """Given Popen raises an exception, when launching, then a
        LaunchError is raised with the failed label."""
        from commands.concurrent import LoopLauncher, LaunchError

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        with patch(
            "commands.concurrent.subprocess.Popen",
            side_effect=OSError("Permission denied"),
        ):
            with pytest.raises(LaunchError) as exc_info:
                launcher.launch(
                    count=1,
                    prd_path=prd,
                    plan_path=plan,
                    worktree_paths=[],
                )

        assert "ralph-0" in str(exc_info.value)

    def test_launch_cleans_up_started_processes_on_failure(self, tmp_path: Path):
        """Given a multi-process launch where process N fails to start, when
        the error is raised, then already-started processes are terminated."""
        from commands.concurrent import LoopLauncher, LaunchError

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        wt1 = tmp_path / ".git-worktrees" / "ralph-1"
        wt1.mkdir(parents=True, exist_ok=True)

        started_proc = MagicMock()
        started_proc.pid = 1000
        started_proc.poll.return_value = None

        call_count = 0

        def popen_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return started_proc
            raise OSError("Failed to start process 2")

        with patch(
            "commands.concurrent.subprocess.Popen",
            side_effect=popen_side_effect,
        ):
            with pytest.raises(LaunchError):
                launcher.launch(
                    count=2,
                    prd_path=prd,
                    plan_path=plan,
                    worktree_paths=[wt1],
                )

        # The already-started process should be terminated
        started_proc.terminate.assert_called_once()


# ============================================================================
# Tests: LoopLauncher with skip_preflight flag
# ============================================================================


class TestLoopLauncherSkipPreflight:
    """Tests for skip-preflight flag passed to subprocesses."""

    def test_launch_passes_skip_preflight(self, tmp_path: Path):
        """Given a launch, when Popen is called, then --skip-preflight flag
        is included in the command (preflight ran by caller already)."""
        from commands.concurrent import LoopLauncher

        launcher = LoopLauncher(project_root=tmp_path)
        prd = tmp_path / "docs" / "prds" / "test.md"
        plan = tmp_path / "docs" / "plans" / "test.md"
        prd.parent.mkdir(parents=True, exist_ok=True)
        plan.parent.mkdir(parents=True, exist_ok=True)
        prd.write_text("# PRD")
        plan.write_text("# Plan")

        popen_calls = []

        def track_popen(*args, **kwargs):
            popen_calls.append((args, kwargs))
            proc = MagicMock()
            proc.pid = 1000
            proc.poll.return_value = None
            return proc

        with patch("commands.concurrent.subprocess.Popen", side_effect=track_popen):
            launcher.launch(
                count=1,
                prd_path=prd,
                plan_path=plan,
                worktree_paths=[],
            )

        cmd = popen_calls[0][0][0] if popen_calls[0][0] else popen_calls[0][1].get("args", [])
        cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
        assert "--skip-preflight" in cmd_str
