"""Unit tests for execution report integration with scripted checks.

Tests the integration of scripted checks and post-loop review into the
/execution-report command. This implements AIUI-0064: Integrate scripted
checks into execution-report.

From the PRD:
 - FR-7: Scripted checks execute BEFORE agent review
 - FR-7: If any check fails, report failures immediately WITHOUT agent review
 - FR-7: If all checks pass, proceed to agent review
 - FR-7: Checks complete in under 30 seconds
 - FR-13: Agent review runs AFTER scripted checks pass
 - FR-14: Agent review uses review_model config (default: opus)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestRunExecutionReportChecks:
    """Tests for run_execution_report_checks() integration function."""

    def test_runs_scripted_checks_first(self, tmp_path: Path) -> None:
        """run_execution_report_checks should run scripted checks before agent review."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ExecutionReportResult,
        )

        # Track call order
        call_order: list[str] = []

        def mock_scripted_checks(*args, **kwargs):
            call_order.append("scripted_checks")
            from commands.scripted_checks import ScriptedChecksResult, ScriptedCheckResult
            return ScriptedChecksResult(
                checks=[ScriptedCheckResult(name="test", passed=True, details="PASS")],
                duration_seconds=0.1,
            )

        def mock_post_loop_review(*args, **kwargs):
            call_order.append("post_loop_review")
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(
                status="review_complete",
                findings="No issues",
                ticket_count=1,
            )

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                )

        # Scripted checks must run first
        assert call_order[0] == "scripted_checks"
        assert isinstance(result, ExecutionReportResult)

    def test_skips_agent_review_when_scripted_checks_fail(self, tmp_path: Path) -> None:
        """run_execution_report_checks should NOT invoke agent review when scripted checks fail."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        # Track whether agent review was called
        agent_review_called = False

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[
                    ScriptedCheckResult(name="merge_commits", passed=True, details="PASS"),
                    ScriptedCheckResult(name="orphaned_branches", passed=False, details="FAIL: AIUI-0001 not merged"),
                ],
                duration_seconds=0.2,
            )

        def mock_post_loop_review(*args, **kwargs):
            nonlocal agent_review_called
            agent_review_called = True
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(status="review_complete")

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                )

        # Agent review should NOT be called when scripted checks fail
        assert agent_review_called is False
        assert result.scripted_checks_passed is False

    def test_invokes_agent_review_when_scripted_checks_pass(self, tmp_path: Path) -> None:
        """run_execution_report_checks should invoke agent review when all scripted checks pass."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        # Track whether agent review was called
        agent_review_called = False

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[
                    ScriptedCheckResult(name="merge_commits", passed=True, details="PASS"),
                    ScriptedCheckResult(name="orphaned_branches", passed=True, details="PASS"),
                ],
                duration_seconds=0.2,
            )

        def mock_post_loop_review(*args, **kwargs):
            nonlocal agent_review_called
            agent_review_called = True
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(
                status="review_complete",
                findings="No issues",
                ticket_count=1,
            )

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                )

        # Agent review SHOULD be called when scripted checks pass
        assert agent_review_called is True
        assert result.scripted_checks_passed is True
        assert result.agent_review_completed is True

    def test_reports_failures_immediately_without_agent_review(self, tmp_path: Path) -> None:
        """run_execution_report_checks should report failures immediately when checks fail."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[
                    ScriptedCheckResult(name="merge_commits", passed=False, details="FAIL: AIUI-0001, AIUI-0002 not merged"),
                ],
                duration_seconds=0.1,
            )

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            result = run_execution_report_checks(
                ticket_ids=["AIUI-0001", "AIUI-0002"],
                state_dir=tmp_path,
            )

        # Result should contain failure details
        assert result.scripted_checks_passed is False
        assert "AIUI-0001" in result.scripted_checks_summary
        assert "FAIL" in result.scripted_checks_summary
        # Agent review should not have been attempted
        assert result.agent_review_completed is False

    def test_uses_all_standard_checks_by_default(self, tmp_path: Path) -> None:
        """run_execution_report_checks should use all standard checks by default."""
        from commands.scripted_checks import run_execution_report_checks

        checks_called: list[str] = []

        # Create mock check functions that track which ones were called
        def create_mock_check(name: str):
            def mock_check(ticket_ids, state_dir):
                checks_called.append(name)
                from commands.scripted_checks import ScriptedCheckResult
                return ScriptedCheckResult(name=name, passed=True, details="PASS")
            return mock_check

        # Mock the individual check functions
        with patch("commands.scripted_checks.check_merge_commits", create_mock_check("merge_commits")):
            with patch("commands.scripted_checks.check_orphaned_branches", create_mock_check("orphaned_branches")):
                with patch("commands.scripted_checks.check_bypass_language", create_mock_check("bypass_language")):
                    with patch("commands.scripted_checks.check_state_files_exist", create_mock_check("state_files")):
                        with patch("commands.scripted_checks.check_validation_files_exist", create_mock_check("validation_files")):
                            with patch("commands.scripted_checks.run_post_loop_review") as mock_review:
                                from commands.scripted_checks import PostLoopReviewResult
                                mock_review.return_value = PostLoopReviewResult(status="review_complete")

                                result = run_execution_report_checks(
                                    ticket_ids=["AIUI-0001"],
                                    state_dir=tmp_path,
                                )

        # All 5 standard checks should have been called
        assert "merge_commits" in checks_called
        assert "orphaned_branches" in checks_called
        assert "bypass_language" in checks_called
        assert "state_files" in checks_called
        assert "validation_files" in checks_called

    def test_uses_review_model_from_config(self, tmp_path: Path) -> None:
        """run_execution_report_checks should use review_model from config for agent review."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        used_model: str = ""

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[ScriptedCheckResult(name="test", passed=True, details="PASS")],
                duration_seconds=0.1,
            )

        def mock_post_loop_review(*args, model="opus", **kwargs):
            nonlocal used_model
            used_model = model
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(status="review_complete")

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                # Pass custom model
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                    review_model="sonnet",
                )

        assert used_model == "sonnet"

    def test_defaults_to_opus_for_review_model(self, tmp_path: Path) -> None:
        """run_execution_report_checks should default to opus for review_model."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        used_model: str = ""

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[ScriptedCheckResult(name="test", passed=True, details="PASS")],
                duration_seconds=0.1,
            )

        def mock_post_loop_review(*args, model="opus", **kwargs):
            nonlocal used_model
            used_model = model
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(status="review_complete")

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                # Don't pass model - should default to opus
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                )

        assert used_model == "opus"

    def test_returns_execution_report_result(self, tmp_path: Path) -> None:
        """run_execution_report_checks should return ExecutionReportResult with all fields."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ExecutionReportResult,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[ScriptedCheckResult(name="test", passed=True, details="PASS")],
                duration_seconds=0.15,
            )

        def mock_post_loop_review(*args, **kwargs):
            from commands.scripted_checks import PostLoopReviewResult
            return PostLoopReviewResult(
                status="review_complete",
                findings="All good",
                ticket_count=2,
            )

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001", "AIUI-0002"],
                    state_dir=tmp_path,
                )

        assert isinstance(result, ExecutionReportResult)
        assert result.scripted_checks_passed is True
        assert result.agent_review_completed is True
        assert result.ticket_count == 2
        assert "PASS" in result.scripted_checks_summary

    def test_handles_dry_run_mode(self, tmp_path: Path) -> None:
        """run_execution_report_checks should support dry_run mode that skips agent review invocation."""
        from commands.scripted_checks import (
            run_execution_report_checks,
            ScriptedChecksResult,
            ScriptedCheckResult,
        )

        agent_review_called = False

        def mock_scripted_checks(*args, **kwargs):
            return ScriptedChecksResult(
                checks=[ScriptedCheckResult(name="test", passed=True, details="PASS")],
                duration_seconds=0.1,
            )

        def mock_post_loop_review(*args, dry_run=False, **kwargs):
            nonlocal agent_review_called
            agent_review_called = True
            from commands.scripted_checks import PostLoopReviewResult
            if dry_run:
                return PostLoopReviewResult(status="dry_run")
            return PostLoopReviewResult(status="review_complete")

        with patch("commands.scripted_checks.run_scripted_checks", mock_scripted_checks):
            with patch("commands.scripted_checks.run_post_loop_review", mock_post_loop_review):
                result = run_execution_report_checks(
                    ticket_ids=["AIUI-0001"],
                    state_dir=tmp_path,
                    dry_run=True,
                )

        # In dry_run mode, agent review should be called with dry_run=True
        assert agent_review_called is True
        assert result.agent_review_status == "dry_run"


class TestExecutionReportResult:
    """Tests for ExecutionReportResult dataclass."""

    def test_has_required_fields(self) -> None:
        """ExecutionReportResult should have all required fields."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=True,
            scripted_checks_summary="All passed",
            agent_review_completed=True,
            agent_review_status="review_complete",
            agent_review_findings="No issues",
            ticket_count=3,
        )

        assert result.scripted_checks_passed is True
        assert result.scripted_checks_summary == "All passed"
        assert result.agent_review_completed is True
        assert result.agent_review_status == "review_complete"
        assert result.agent_review_findings == "No issues"
        assert result.ticket_count == 3

    def test_default_values(self) -> None:
        """ExecutionReportResult should have sensible defaults."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=False,
            scripted_checks_summary="FAIL",
        )

        # Defaults for when agent review not run
        assert result.agent_review_completed is False
        assert result.agent_review_status == ""
        assert result.agent_review_findings == ""
        assert result.ticket_count == 0

    def test_has_concerns_when_agent_review_has_concerns(self) -> None:
        """ExecutionReportResult.has_concerns should be True when agent review found concerns."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=True,
            scripted_checks_summary="All passed",
            agent_review_completed=True,
            agent_review_status="review_concerns",
            agent_review_findings="Found issues",
        )

        assert result.has_concerns is True

    def test_has_concerns_when_scripted_checks_failed(self) -> None:
        """ExecutionReportResult.has_concerns should be True when scripted checks failed."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=False,
            scripted_checks_summary="FAIL: Missing merges",
            agent_review_completed=False,
        )

        assert result.has_concerns is True

    def test_no_concerns_when_all_passed(self) -> None:
        """ExecutionReportResult.has_concerns should be False when everything passed."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=True,
            scripted_checks_summary="All passed",
            agent_review_completed=True,
            agent_review_status="review_complete",
            agent_review_findings="No issues",
        )

        assert result.has_concerns is False

    def test_get_full_report_summary(self) -> None:
        """ExecutionReportResult should generate a formatted report summary."""
        from commands.scripted_checks import ExecutionReportResult

        result = ExecutionReportResult(
            scripted_checks_passed=True,
            scripted_checks_summary="Scripted Checks: PASS\n  [PASS] merge_commits",
            agent_review_completed=True,
            agent_review_status="review_complete",
            agent_review_findings="## Summary\nAll tickets implemented correctly.",
            ticket_count=3,
        )

        report = result.get_report_summary()

        # Should include both scripted checks and agent review sections
        assert "Scripted Checks" in report
        assert "PASS" in report
        assert "Agent Review" in report or "review" in report.lower()
        assert "3" in report  # ticket count


class TestGetDefaultChecks:
    """Tests for get_default_checks() function."""

    def test_returns_all_five_standard_checks(self) -> None:
        """get_default_checks should return all 5 standard check functions."""
        from commands.scripted_checks import get_default_checks

        checks = get_default_checks()

        assert len(checks) == 5
        # Verify check names
        check_names = [getattr(c, "__name__", str(c)) for c in checks]
        assert "check_merge_commits" in check_names
        assert "check_orphaned_branches" in check_names
        assert "check_bypass_language" in check_names
        assert "check_state_files_exist" in check_names
        assert "check_validation_files_exist" in check_names

    def test_checks_are_callable(self) -> None:
        """get_default_checks should return callable check functions."""
        from commands.scripted_checks import get_default_checks

        checks = get_default_checks()

        for check in checks:
            assert callable(check)
