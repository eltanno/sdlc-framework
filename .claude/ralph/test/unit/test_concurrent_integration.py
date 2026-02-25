"""Unit tests for the concurrent loop integration (SLCA-0082).

Tests cover:
- run_concurrent_loops(): Full lifecycle integration function
- Post-loop cleanup logic

PRD Test Cases covered: TC-11 (integration)
PRD FR-7 Acceptance Criteria:
- Given loop count from config, worktrees prepared, .env synced, loops launched
- Given loop count 1, existing single-loop flow runs
- Given all loops complete, worktrees checked out to clean state, summary reported
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest


# ============================================================================
# Tests: run_concurrent_loops()
# ============================================================================


class TestRunConcurrentLoops:
    """Tests for run_concurrent_loops() integration function."""

    @patch("commands.concurrent.WorktreeManager")
    @patch("commands.concurrent.EnvSyncer")
    @patch("commands.concurrent.LoopLauncher")
    @patch("commands.concurrent.LoopMonitor")
    @patch("commands.concurrent.ConsolidatedSummary")
    def test_single_loop_bypasses_worktree_setup(
        self,
        mock_summary_cls,
        mock_monitor_cls,
        mock_launcher_cls,
        mock_env_cls,
        mock_wt_cls,
    ):
        """Given loops=1, when run_concurrent_loops runs, then worktree
        setup is bypassed and single loop runs in project root."""
        from commands.concurrent import run_concurrent_loops, SummaryReport

        project_root = Path("/fake/project")
        prd_path = Path("docs/prds/test.md")
        plan_path = Path("docs/plans/test.md")

        # Setup mocks
        mock_launcher = mock_launcher_cls.return_value
        mock_launch_result = MagicMock(
            label="ralph-0",
            process=MagicMock(poll=MagicMock(return_value=0)),
            log_file=Path("/fake/tmp/ralph-0.log"),
            start_time=datetime.now(),
        )
        mock_launcher.launch.return_value = [mock_launch_result]

        mock_monitor = mock_monitor_cls.return_value
        mock_completion = MagicMock(
            label="ralph-0", exit_code=0, runtime_seconds=100.0,
            log_file=Path("/fake/tmp/ralph-0.log"),
        )
        mock_monitor.monitor.return_value = [mock_completion]

        mock_summary = mock_summary_cls.return_value
        mock_summary.generate.return_value = SummaryReport(
            loop_summaries=[], total_completed=2, total_blocked=0,
            overall_wall_clock_seconds=100.0,
        )
        mock_summary.format_report.return_value = "Summary text"

        result = run_concurrent_loops(
            project_root=project_root,
            prd_path=prd_path,
            plan_path=plan_path,
            loop_count=1,
            default_branch="develop-working",
        )

        # Worktree manager should NOT be called for single loop
        mock_wt_cls.assert_not_called()
        mock_env_cls.assert_not_called()

        # Launcher should be called with count=1
        mock_launcher.launch.assert_called_once_with(
            count=1,
            prd_path=prd_path,
            plan_path=plan_path,
            worktree_paths=[],
        )

        assert result.total_completed == 2

    @patch("commands.concurrent.WorktreeManager")
    @patch("commands.concurrent.EnvSyncer")
    @patch("commands.concurrent.LoopLauncher")
    @patch("commands.concurrent.LoopMonitor")
    @patch("commands.concurrent.ConsolidatedSummary")
    def test_multi_loop_sets_up_worktrees_and_env(
        self,
        mock_summary_cls,
        mock_monitor_cls,
        mock_launcher_cls,
        mock_env_cls,
        mock_wt_cls,
    ):
        """Given loops=3, when run_concurrent_loops runs, then 2 worktrees
        are created and .env is synced to each."""
        from commands.concurrent import run_concurrent_loops, SummaryReport

        project_root = Path("/fake/project")
        prd_path = Path("docs/prds/test.md")
        plan_path = Path("docs/plans/test.md")

        # Setup worktree manager mock
        mock_wt = mock_wt_cls.return_value
        wt_paths = [
            Path("/fake/project/.git-worktrees/ralph-1"),
            Path("/fake/project/.git-worktrees/ralph-2"),
        ]
        mock_wt.ensure_worktrees.return_value = wt_paths

        # Setup launcher mock
        mock_launcher = mock_launcher_cls.return_value
        mock_launcher.launch.return_value = [MagicMock() for _ in range(3)]

        # Setup monitor mock
        mock_monitor = mock_monitor_cls.return_value
        mock_monitor.monitor.return_value = [
            MagicMock(label=f"ralph-{i}", exit_code=0, runtime_seconds=100.0,
                     log_file=Path(f"/fake/tmp/ralph-{i}.log"))
            for i in range(3)
        ]

        # Setup summary mock
        mock_summary = mock_summary_cls.return_value
        mock_summary.generate.return_value = SummaryReport(
            loop_summaries=[], total_completed=6, total_blocked=0,
            overall_wall_clock_seconds=100.0,
        )
        mock_summary.format_report.return_value = "Summary text"

        result = run_concurrent_loops(
            project_root=project_root,
            prd_path=prd_path,
            plan_path=plan_path,
            loop_count=3,
            default_branch="develop-working",
        )

        # Worktree manager should create 2 worktrees (3 loops - 1 main)
        mock_wt.ensure_worktrees.assert_called_once_with(
            count=2,
            default_branch="develop-working",
        )

        # EnvSyncer should sync to each worktree
        mock_env = mock_env_cls.return_value
        assert mock_env.sync_env.call_count == 2

        # Launcher should be called with count=3
        mock_launcher.launch.assert_called_once()
        call_args = mock_launcher.launch.call_args
        assert call_args[1]["count"] == 3 or call_args[0][0] == 3

        assert result.total_completed == 6

    @patch("commands.concurrent.WorktreeManager")
    @patch("commands.concurrent.EnvSyncer")
    @patch("commands.concurrent.LoopLauncher")
    @patch("commands.concurrent.LoopMonitor")
    @patch("commands.concurrent.ConsolidatedSummary")
    def test_post_loop_resets_worktrees(
        self,
        mock_summary_cls,
        mock_monitor_cls,
        mock_launcher_cls,
        mock_env_cls,
        mock_wt_cls,
    ):
        """Given loops=3 complete, when run_concurrent_loops finishes, then
        all worktrees are reset to origin/{default_branch}."""
        from commands.concurrent import run_concurrent_loops, SummaryReport

        project_root = Path("/fake/project")
        prd_path = Path("docs/prds/test.md")
        plan_path = Path("docs/plans/test.md")

        # Setup worktree manager
        mock_wt = mock_wt_cls.return_value
        wt_paths = [
            Path("/fake/project/.git-worktrees/ralph-1"),
            Path("/fake/project/.git-worktrees/ralph-2"),
        ]
        mock_wt.ensure_worktrees.return_value = wt_paths

        # Setup the rest
        mock_launcher = mock_launcher_cls.return_value
        mock_launcher.launch.return_value = [MagicMock() for _ in range(3)]
        mock_monitor = mock_monitor_cls.return_value
        mock_monitor.monitor.return_value = [
            MagicMock(label=f"ralph-{i}", exit_code=0, runtime_seconds=50.0,
                     log_file=Path(f"/fake/tmp/ralph-{i}.log"))
            for i in range(3)
        ]
        mock_summary = mock_summary_cls.return_value
        mock_summary.generate.return_value = SummaryReport(
            loop_summaries=[], total_completed=6, total_blocked=0,
            overall_wall_clock_seconds=50.0,
        )
        mock_summary.format_report.return_value = "Summary"

        run_concurrent_loops(
            project_root=project_root,
            prd_path=prd_path,
            plan_path=plan_path,
            loop_count=3,
            default_branch="develop-working",
        )

        # update_worktree called on each worktree for post-loop cleanup
        assert mock_wt.update_worktree.call_count == 2
        for i, wt_path in enumerate(wt_paths):
            mock_wt.update_worktree.assert_any_call(wt_path, "develop-working")

    @patch("commands.concurrent.WorktreeManager")
    @patch("commands.concurrent.EnvSyncer")
    @patch("commands.concurrent.LoopLauncher")
    @patch("commands.concurrent.LoopMonitor")
    @patch("commands.concurrent.ConsolidatedSummary")
    def test_post_loop_cleanup_tolerates_dirty_worktrees(
        self,
        mock_summary_cls,
        mock_monitor_cls,
        mock_launcher_cls,
        mock_env_cls,
        mock_wt_cls,
    ):
        """Given a worktree has uncommitted changes after loop completion,
        when post-loop cleanup runs, then it logs a warning but does not
        crash the overall run."""
        from commands.concurrent import (
            run_concurrent_loops,
            SummaryReport,
            DirtyWorktreeError,
        )

        project_root = Path("/fake/project")
        prd_path = Path("docs/prds/test.md")
        plan_path = Path("docs/plans/test.md")

        # Setup worktree manager that raises on cleanup
        mock_wt = mock_wt_cls.return_value
        wt_paths = [Path("/fake/project/.git-worktrees/ralph-1")]
        mock_wt.ensure_worktrees.return_value = wt_paths
        mock_wt.update_worktree.side_effect = DirtyWorktreeError(
            wt_paths[0], ["file.txt"]
        )

        # Setup the rest
        mock_launcher = mock_launcher_cls.return_value
        mock_launcher.launch.return_value = [MagicMock() for _ in range(2)]
        mock_monitor = mock_monitor_cls.return_value
        mock_monitor.monitor.return_value = [
            MagicMock(label=f"ralph-{i}", exit_code=0, runtime_seconds=50.0,
                     log_file=Path(f"/fake/tmp/ralph-{i}.log"))
            for i in range(2)
        ]
        mock_summary = mock_summary_cls.return_value
        mock_summary.generate.return_value = SummaryReport(
            loop_summaries=[], total_completed=4, total_blocked=0,
            overall_wall_clock_seconds=50.0,
        )
        mock_summary.format_report.return_value = "Summary"

        # Should NOT raise — cleanup errors are logged, not propagated
        result = run_concurrent_loops(
            project_root=project_root,
            prd_path=prd_path,
            plan_path=plan_path,
            loop_count=2,
            default_branch="develop-working",
        )

        assert result.total_completed == 4


# ============================================================================
# Tests: ConcurrentRunResult dataclass
# ============================================================================


class TestConcurrentRunResult:
    """Tests for the ConcurrentRunResult dataclass."""

    def test_result_has_required_fields(self):
        """Given a ConcurrentRunResult, when inspected, then it has
        summary_report and formatted_summary fields."""
        from commands.concurrent import ConcurrentRunResult, SummaryReport

        report = SummaryReport(
            loop_summaries=[], total_completed=3, total_blocked=1,
            overall_wall_clock_seconds=120.0,
        )
        result = ConcurrentRunResult(
            summary_report=report,
            formatted_summary="text",
            worktree_paths=[Path("/a")],
            cleanup_warnings=[],
        )

        assert result.summary_report.total_completed == 3
        assert result.formatted_summary == "text"
        assert len(result.worktree_paths) == 1
        assert result.cleanup_warnings == []

    def test_result_captures_cleanup_warnings(self):
        """Given cleanup produced warnings, when result is created, then
        warnings are captured."""
        from commands.concurrent import ConcurrentRunResult, SummaryReport

        report = SummaryReport(
            loop_summaries=[], total_completed=3, total_blocked=1,
            overall_wall_clock_seconds=120.0,
        )
        result = ConcurrentRunResult(
            summary_report=report,
            formatted_summary="text",
            worktree_paths=[],
            cleanup_warnings=["ralph-1 has dirty state"],
        )

        assert len(result.cleanup_warnings) == 1
        assert "ralph-1" in result.cleanup_warnings[0]
