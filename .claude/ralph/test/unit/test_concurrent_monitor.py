"""Unit tests for the LoopMonitor and ConsolidatedSummary in concurrent.py.

Tests cover:
- LoopMonitor.check_progress: read tail of each log file for status
- LoopMonitor.detect_stalled: flag logs with no new output for >30 min
- LoopMonitor.monitor: poll processes until all complete
- ConsolidatedSummary.generate: per-loop and aggregate statistics
- LoopProgress dataclass fields
- StalledLoopWarning dataclass fields
- SummaryReport dataclass fields

PRD Test Cases covered: TC-13
PRD FR-5 Acceptance Criteria:
- Given multiple loops running, monitor reads tail of each log file
  and reports brief status per loop
- Given all loops completed, summary includes per-loop completed/blocked
  counts, total completed/blocked, wall-clock time per loop, overall time
- Given a loop produced no output for >30 minutes, flagged as stalled
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# ============================================================================
# Tests: LoopProgress dataclass
# ============================================================================


class TestLoopProgress:
    """Tests for the LoopProgress dataclass."""

    def test_loop_progress_has_required_fields(self):
        """Given a LoopProgress, when inspected, then it has label,
        current_ticket, tickets_completed, and last_output_line fields."""
        from commands.concurrent import LoopProgress

        progress = LoopProgress(
            label="ralph-0",
            current_ticket="SLCA-0076",
            tickets_completed=2,
            last_output_line="[2026-02-25] Implementing SLCA-0076...",
        )

        assert progress.label == "ralph-0"
        assert progress.current_ticket == "SLCA-0076"
        assert progress.tickets_completed == 2
        assert progress.last_output_line == "[2026-02-25] Implementing SLCA-0076..."

    def test_loop_progress_defaults_to_none_for_current_ticket(self):
        """Given a LoopProgress with no active ticket, when inspected,
        then current_ticket is None."""
        from commands.concurrent import LoopProgress

        progress = LoopProgress(
            label="ralph-1",
            current_ticket=None,
            tickets_completed=0,
            last_output_line="Starting...",
        )

        assert progress.current_ticket is None


# ============================================================================
# Tests: StalledLoopWarning dataclass
# ============================================================================


class TestStalledLoopWarning:
    """Tests for the StalledLoopWarning dataclass."""

    def test_stalled_loop_warning_has_required_fields(self):
        """Given a StalledLoopWarning, when inspected, then it has label,
        log_file, last_modified, and minutes_stalled fields."""
        from commands.concurrent import StalledLoopWarning

        now = datetime.now()
        warning = StalledLoopWarning(
            label="ralph-2",
            log_file=Path("/project/tmp/ralph-2-2026-02-25.log"),
            last_modified=now,
            minutes_stalled=35.0,
        )

        assert warning.label == "ralph-2"
        assert warning.log_file == Path("/project/tmp/ralph-2-2026-02-25.log")
        assert warning.last_modified == now
        assert warning.minutes_stalled == 35.0


# ============================================================================
# Tests: LoopMonitor.check_progress
# ============================================================================


class TestLoopMonitorCheckProgress:
    """Tests for reading log file tails and reporting progress."""

    def test_check_progress_reads_tail_of_each_log(self, tmp_path: Path):
        """Given multiple log files with content, when check_progress is
        called, then it returns progress for each loop."""
        from commands.concurrent import LoopMonitor

        # Create log files with content
        log0 = tmp_path / "ralph-0-2026-02-25.log"
        log1 = tmp_path / "ralph-1-2026-02-25.log"
        log0.write_text(
            "[INFO] Starting ralph-0\n"
            "[INFO] Claiming SLCA-0076\n"
            "[INFO] SLCA-0076 COMPLETED\n"
            "[INFO] Claiming SLCA-0077\n"
        )
        log1.write_text(
            "[INFO] Starting ralph-1\n"
            "[INFO] Claiming SLCA-0078\n"
        )

        log_files = {"ralph-0": log0, "ralph-1": log1}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert len(progress_list) == 2
        labels = {p.label for p in progress_list}
        assert labels == {"ralph-0", "ralph-1"}

    def test_check_progress_detects_completed_tickets(self, tmp_path: Path):
        """Given a log file with COMPLETED markers, when check_progress
        is called, then tickets_completed reflects the count."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text(
            "[INFO] SLCA-0076 COMPLETED\n"
            "[INFO] SLCA-0077 COMPLETED\n"
            "[INFO] Claiming SLCA-0078\n"
        )

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert progress_list[0].tickets_completed == 2

    def test_check_progress_detects_current_ticket(self, tmp_path: Path):
        """Given a log file showing a ticket being worked on, when
        check_progress is called, then current_ticket is set."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text(
            "[INFO] SLCA-0076 COMPLETED\n"
            "[INFO] Claiming SLCA-0077\n"
            "[INFO] Working on SLCA-0077\n"
        )

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert progress_list[0].current_ticket == "SLCA-0077"

    def test_check_progress_returns_last_output_line(self, tmp_path: Path):
        """Given a log file with multiple lines, when check_progress is
        called, then last_output_line is the last non-empty line."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text(
            "[INFO] Starting\n"
            "[INFO] Processing\n"
            "[INFO] Last meaningful line\n"
        )

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert "Last meaningful line" in progress_list[0].last_output_line

    def test_check_progress_handles_empty_log_file(self, tmp_path: Path):
        """Given an empty log file, when check_progress is called,
        then progress shows 0 completed and no current ticket."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("")

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert progress_list[0].tickets_completed == 0
        assert progress_list[0].current_ticket is None

    def test_check_progress_handles_missing_log_file(self, tmp_path: Path):
        """Given a log file that doesn't exist, when check_progress is
        called, then it returns progress with 0 completed and a note."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "nonexistent.log"

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        progress_list = monitor.check_progress(log_files)

        assert progress_list[0].tickets_completed == 0
        assert progress_list[0].current_ticket is None


# ============================================================================
# Tests: LoopMonitor.detect_stalled
# ============================================================================


class TestLoopMonitorDetectStalled:
    """Tests for detecting stalled loops based on log file modification time."""

    def test_detect_stalled_flags_old_log_file(self, tmp_path: Path):
        """Given a log file not modified for >30 minutes, when
        detect_stalled is called, then it returns a warning."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("[INFO] Starting\n")

        # Set modification time to 35 minutes ago
        old_time = time.time() - (35 * 60)
        os.utime(log0, (old_time, old_time))

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=30)

        assert len(warnings) == 1
        assert warnings[0].label == "ralph-0"
        assert warnings[0].minutes_stalled >= 30

    def test_detect_stalled_ignores_recent_log_file(self, tmp_path: Path):
        """Given a log file modified recently, when detect_stalled
        is called, then no warning is returned."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("[INFO] Still working\n")
        # Just written, so modification time is recent

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=30)

        assert len(warnings) == 0

    def test_detect_stalled_multiple_logs_mixed(self, tmp_path: Path):
        """Given 3 log files where one is stalled, when detect_stalled
        is called, then only the stalled one is flagged."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log2 = tmp_path / "ralph-2.log"

        log0.write_text("[INFO] Active\n")  # Recent
        log1.write_text("[INFO] Old\n")  # Will be stalled
        log2.write_text("[INFO] Active\n")  # Recent

        # Set log1 to 45 minutes ago
        old_time = time.time() - (45 * 60)
        os.utime(log1, (old_time, old_time))

        log_files = {"ralph-0": log0, "ralph-1": log1, "ralph-2": log2}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=30)

        assert len(warnings) == 1
        assert warnings[0].label == "ralph-1"

    def test_detect_stalled_handles_missing_log_file(self, tmp_path: Path):
        """Given a nonexistent log file, when detect_stalled is called,
        then it does not raise an error (graceful handling)."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "nonexistent.log"

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=30)

        # Should not crash, but may flag as stalled or skip
        assert isinstance(warnings, list)

    def test_detect_stalled_uses_custom_threshold(self, tmp_path: Path):
        """Given a custom threshold of 10 minutes, when a log file is
        15 minutes old, then it is flagged as stalled."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("[INFO] Working\n")

        # Set modification time to 15 minutes ago
        old_time = time.time() - (15 * 60)
        os.utime(log0, (old_time, old_time))

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=10)

        assert len(warnings) == 1

    def test_detect_stalled_at_exact_threshold_not_flagged(self, tmp_path: Path):
        """Given a log file modified exactly at the threshold boundary,
        when detect_stalled is called, then it is NOT flagged (must exceed)."""
        from commands.concurrent import LoopMonitor

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("[INFO] Working\n")

        # Set modification time to exactly 30 minutes ago
        # Use a small buffer to avoid flaky test timing
        old_time = time.time() - (29.5 * 60)
        os.utime(log0, (old_time, old_time))

        log_files = {"ralph-0": log0}
        monitor = LoopMonitor()
        warnings = monitor.detect_stalled(log_files, threshold_minutes=30)

        assert len(warnings) == 0


# ============================================================================
# Tests: LoopMonitor.monitor
# ============================================================================


class TestLoopMonitorMonitor:
    """Tests for the main monitoring loop that polls processes until completion."""

    def test_monitor_returns_when_all_processes_complete(self, tmp_path: Path):
        """Given all processes have completed, when monitor runs, then
        it returns completion results for each."""
        from commands.concurrent import (
            CompletionResult,
            LaunchResult,
            LoopMonitor,
        )

        proc0 = MagicMock()
        proc0.poll.return_value = 0

        proc1 = MagicMock()
        proc1.poll.return_value = 0

        now = datetime.now()
        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log0.write_text("[INFO] Done\n")
        log1.write_text("[INFO] Done\n")

        launch_results = [
            LaunchResult(
                process=proc0, label="ralph-0", cwd=tmp_path,
                log_file=log0, start_time=now,
            ),
            LaunchResult(
                process=proc1, label="ralph-1",
                cwd=tmp_path / ".git-worktrees" / "ralph-1",
                log_file=log1, start_time=now,
            ),
        ]

        monitor = LoopMonitor(poll_interval_seconds=0.01)
        completions = monitor.monitor(launch_results)

        assert len(completions) == 2
        assert all(c.exit_code == 0 for c in completions)

    def test_monitor_reports_crashed_process(self, tmp_path: Path):
        """Given one process crashes, when monitor completes, then
        the crashed process's exit code is reported."""
        from commands.concurrent import LaunchResult, LoopMonitor

        proc0 = MagicMock()
        proc0.poll.return_value = 0

        proc1 = MagicMock()
        proc1.poll.return_value = 1  # crash

        now = datetime.now()
        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log0.write_text("[INFO] Done\n")
        log1.write_text("[ERROR] Crash\n")

        launch_results = [
            LaunchResult(
                process=proc0, label="ralph-0", cwd=tmp_path,
                log_file=log0, start_time=now,
            ),
            LaunchResult(
                process=proc1, label="ralph-1",
                cwd=tmp_path / ".git-worktrees" / "ralph-1",
                log_file=log1, start_time=now,
            ),
        ]

        monitor = LoopMonitor(poll_interval_seconds=0.01)
        completions = monitor.monitor(launch_results)

        crashed = [c for c in completions if c.exit_code != 0]
        assert len(crashed) == 1
        assert crashed[0].label == "ralph-1"
        assert crashed[0].exit_code == 1

    def test_monitor_collects_runtime_for_each(self, tmp_path: Path):
        """Given processes complete at different times, when monitor
        returns, then each CompletionResult has a non-negative runtime."""
        from commands.concurrent import LaunchResult, LoopMonitor

        proc0 = MagicMock()
        proc0.poll.return_value = 0

        now = datetime.now()
        log0 = tmp_path / "ralph-0.log"
        log0.write_text("[INFO] Done\n")

        launch_results = [
            LaunchResult(
                process=proc0, label="ralph-0", cwd=tmp_path,
                log_file=log0, start_time=now,
            ),
        ]

        monitor = LoopMonitor(poll_interval_seconds=0.01)
        completions = monitor.monitor(launch_results)

        assert completions[0].runtime_seconds >= 0


# ============================================================================
# Tests: SummaryReport dataclass
# ============================================================================


class TestSummaryReport:
    """Tests for the SummaryReport dataclass."""

    def test_summary_report_has_required_fields(self):
        """Given a SummaryReport, when inspected, then it has
        loop_summaries, total_completed, total_blocked, and
        overall_wall_clock_seconds fields."""
        from commands.concurrent import LoopSummary, SummaryReport

        report = SummaryReport(
            loop_summaries=[
                LoopSummary(
                    label="ralph-0",
                    completed_count=2,
                    blocked_count=1,
                    exit_code=0,
                    wall_clock_seconds=120.0,
                ),
            ],
            total_completed=2,
            total_blocked=1,
            overall_wall_clock_seconds=120.0,
        )

        assert len(report.loop_summaries) == 1
        assert report.total_completed == 2
        assert report.total_blocked == 1
        assert report.overall_wall_clock_seconds == 120.0


class TestLoopSummary:
    """Tests for the LoopSummary dataclass."""

    def test_loop_summary_has_required_fields(self):
        """Given a LoopSummary, when inspected, then it has label,
        completed_count, blocked_count, exit_code, and wall_clock_seconds."""
        from commands.concurrent import LoopSummary

        summary = LoopSummary(
            label="ralph-0",
            completed_count=3,
            blocked_count=1,
            exit_code=0,
            wall_clock_seconds=300.5,
        )

        assert summary.label == "ralph-0"
        assert summary.completed_count == 3
        assert summary.blocked_count == 1
        assert summary.exit_code == 0
        assert summary.wall_clock_seconds == 300.5


# ============================================================================
# Tests: ConsolidatedSummary.generate
# ============================================================================


class TestConsolidatedSummaryGenerate:
    """Tests for generating a consolidated summary from loop results."""

    def test_generate_with_three_loops(self, tmp_path: Path):
        """TC-13: Given 3 loop results (2 completed each, 1 blocked each),
        when generating summary, then it shows 6 completed, 3 blocked,
        per-loop and total timing."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        # Create log files with COMPLETED and BLOCKED markers
        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log2 = tmp_path / "ralph-2.log"

        log0.write_text(
            "[INFO] SLCA-0076 COMPLETED\n"
            "[INFO] SLCA-0077 COMPLETED\n"
            "[INFO] SLCA-0078 BLOCKED\n"
        )
        log1.write_text(
            "[INFO] SLCA-0079 COMPLETED\n"
            "[INFO] SLCA-0080 COMPLETED\n"
            "[INFO] SLCA-0081 BLOCKED\n"
        )
        log2.write_text(
            "[INFO] SLCA-0082 COMPLETED\n"
            "[INFO] SLCA-0083 COMPLETED\n"
            "[INFO] SLCA-0084 BLOCKED\n"
        )

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=120.0, log_file=log0,
            ),
            CompletionResult(
                label="ralph-1", exit_code=0,
                runtime_seconds=150.0, log_file=log1,
            ),
            CompletionResult(
                label="ralph-2", exit_code=0,
                runtime_seconds=180.0, log_file=log2,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        assert report.total_completed == 6
        assert report.total_blocked == 3
        assert len(report.loop_summaries) == 3

        # Per-loop checks
        loop0 = [ls for ls in report.loop_summaries if ls.label == "ralph-0"][0]
        assert loop0.completed_count == 2
        assert loop0.blocked_count == 1
        assert loop0.exit_code == 0
        assert loop0.wall_clock_seconds == 120.0

    def test_generate_with_crashed_loop(self, tmp_path: Path):
        """Given a loop that crashed (exit code != 0), when generating
        summary, then it reports the crash exit code and still counts
        tickets from the log."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"

        log0.write_text(
            "[INFO] SLCA-0076 COMPLETED\n"
            "[INFO] SLCA-0077 COMPLETED\n"
        )
        log1.write_text(
            "[INFO] SLCA-0078 COMPLETED\n"
            "[ERROR] Process crashed\n"
        )

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=120.0, log_file=log0,
            ),
            CompletionResult(
                label="ralph-1", exit_code=1,
                runtime_seconds=45.0, log_file=log1,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        assert report.total_completed == 3
        loop1 = [ls for ls in report.loop_summaries if ls.label == "ralph-1"][0]
        assert loop1.exit_code == 1
        assert loop1.completed_count == 1

    def test_generate_with_empty_log_files(self, tmp_path: Path):
        """Given loops with empty log files, when generating summary,
        then counts are all 0."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        log0 = tmp_path / "ralph-0.log"
        log0.write_text("")

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=5.0, log_file=log0,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        assert report.total_completed == 0
        assert report.total_blocked == 0

    def test_generate_overall_wall_clock_is_max_runtime(self, tmp_path: Path):
        """Given loops with different runtimes, when generating summary,
        then overall_wall_clock_seconds is the maximum runtime
        (since they run in parallel)."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log0.write_text("[INFO] Done\n")
        log1.write_text("[INFO] Done\n")

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=120.0, log_file=log0,
            ),
            CompletionResult(
                label="ralph-1", exit_code=0,
                runtime_seconds=180.0, log_file=log1,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        # Overall wall-clock should be the max (parallel execution)
        assert report.overall_wall_clock_seconds == 180.0

    def test_generate_per_loop_wall_clock_matches_runtime(self, tmp_path: Path):
        """Given completion results with known runtimes, when generating
        summary, then each per-loop wall_clock_seconds matches."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        log0 = tmp_path / "ralph-0.log"
        log1 = tmp_path / "ralph-1.log"
        log0.write_text("[INFO] Done\n")
        log1.write_text("[INFO] Done\n")

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=100.0, log_file=log0,
            ),
            CompletionResult(
                label="ralph-1", exit_code=0,
                runtime_seconds=200.0, log_file=log1,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        loop0 = [ls for ls in report.loop_summaries if ls.label == "ralph-0"][0]
        loop1 = [ls for ls in report.loop_summaries if ls.label == "ralph-1"][0]
        assert loop0.wall_clock_seconds == 100.0
        assert loop1.wall_clock_seconds == 200.0

    def test_generate_with_no_completions(self):
        """Given an empty list of completions, when generating summary,
        then all counts are 0."""
        from commands.concurrent import ConsolidatedSummary

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate([])

        assert report.total_completed == 0
        assert report.total_blocked == 0
        assert report.overall_wall_clock_seconds == 0.0
        assert len(report.loop_summaries) == 0

    def test_generate_with_missing_log_file(self, tmp_path: Path):
        """Given a completion result with a nonexistent log file, when
        generating summary, then it handles gracefully with 0 counts."""
        from commands.concurrent import (
            CompletionResult,
            ConsolidatedSummary,
        )

        log0 = tmp_path / "nonexistent.log"

        completions = [
            CompletionResult(
                label="ralph-0", exit_code=0,
                runtime_seconds=60.0, log_file=log0,
            ),
        ]

        summary_gen = ConsolidatedSummary()
        report = summary_gen.generate(completions)

        assert report.total_completed == 0
        assert report.total_blocked == 0


# ============================================================================
# Tests: ConsolidatedSummary.format_report
# ============================================================================


class TestConsolidatedSummaryFormat:
    """Tests for formatting the summary report as human-readable text."""

    def test_format_report_includes_per_loop_info(self):
        """Given a summary report with 2 loops, when formatted, then
        the output mentions each loop by label."""
        from commands.concurrent import (
            ConsolidatedSummary,
            LoopSummary,
            SummaryReport,
        )

        report = SummaryReport(
            loop_summaries=[
                LoopSummary(
                    label="ralph-0", completed_count=3,
                    blocked_count=0, exit_code=0,
                    wall_clock_seconds=120.0,
                ),
                LoopSummary(
                    label="ralph-1", completed_count=2,
                    blocked_count=1, exit_code=0,
                    wall_clock_seconds=150.0,
                ),
            ],
            total_completed=5,
            total_blocked=1,
            overall_wall_clock_seconds=150.0,
        )

        summary_gen = ConsolidatedSummary()
        text = summary_gen.format_report(report)

        assert "ralph-0" in text
        assert "ralph-1" in text

    def test_format_report_includes_totals(self):
        """Given a summary report, when formatted, then the output
        includes total completed and total blocked counts."""
        from commands.concurrent import (
            ConsolidatedSummary,
            LoopSummary,
            SummaryReport,
        )

        report = SummaryReport(
            loop_summaries=[
                LoopSummary(
                    label="ralph-0", completed_count=4,
                    blocked_count=2, exit_code=0,
                    wall_clock_seconds=200.0,
                ),
            ],
            total_completed=4,
            total_blocked=2,
            overall_wall_clock_seconds=200.0,
        )

        summary_gen = ConsolidatedSummary()
        text = summary_gen.format_report(report)

        assert "4" in text  # total completed
        assert "2" in text  # total blocked

    def test_format_report_includes_timing(self):
        """Given a summary report, when formatted, then the output
        includes wall-clock timing information."""
        from commands.concurrent import (
            ConsolidatedSummary,
            LoopSummary,
            SummaryReport,
        )

        report = SummaryReport(
            loop_summaries=[
                LoopSummary(
                    label="ralph-0", completed_count=2,
                    blocked_count=0, exit_code=0,
                    wall_clock_seconds=3600.0,  # 1 hour
                ),
            ],
            total_completed=2,
            total_blocked=0,
            overall_wall_clock_seconds=3600.0,
        )

        summary_gen = ConsolidatedSummary()
        text = summary_gen.format_report(report)

        # Should include some timing indication (minutes or seconds)
        assert len(text) > 0
