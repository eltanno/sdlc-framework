"""Unit tests for post-loop review agent functionality.

Tests the post-loop review agent invoked after scripted checks pass.
This implements AIUI-0063: Create post-loop review agent.

The post-loop review agent (FR-13 and FR-14 from PRD):
- Only runs after all scripted checks pass
- Uses review_model from config (default: opus)
- Looks for cross-ticket patterns
- Assesses overall coherence of changes
- Identifies anything scripts couldn't catch
- Writes findings to execution report document
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestBuildReviewPrompt:
    """Tests for build_review_prompt() function."""

    def test_includes_ticket_ids_in_prompt(self) -> None:
        """build_review_prompt should include all ticket IDs in the prompt."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=Path("docs/state"),
            scripted_checks_summary="All checks passed",
        )

        assert "AIUI-0001" in prompt
        assert "AIUI-0002" in prompt
        assert "AIUI-0003" in prompt

    def test_includes_state_directory_path(self) -> None:
        """build_review_prompt should include the state directory path."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("/custom/state/path"),
            scripted_checks_summary="All checks passed",
        )

        assert "/custom/state/path" in prompt

    def test_includes_scripted_checks_summary(self) -> None:
        """build_review_prompt should include the scripted checks summary."""
        from commands.scripted_checks import build_review_prompt

        checks_summary = """Scripted Checks: PASS

[PASS] merge_commits
    PASS: All tickets merged

[PASS] orphaned_branches
    PASS: No orphaned branches

Duration: 0.15s"""

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            scripted_checks_summary=checks_summary,
        )

        assert "All tickets merged" in prompt or "Scripted Checks: PASS" in prompt

    def test_instructs_cross_ticket_pattern_analysis(self) -> None:
        """build_review_prompt should instruct the agent to look for cross-ticket patterns."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001", "AIUI-0002"],
            state_dir=Path("docs/state"),
            scripted_checks_summary="All checks passed",
        )

        # Should mention looking for patterns across tickets
        assert "cross-ticket" in prompt.lower() or "pattern" in prompt.lower()

    def test_instructs_overall_coherence_assessment(self) -> None:
        """build_review_prompt should instruct the agent to assess overall coherence."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001", "AIUI-0002"],
            state_dir=Path("docs/state"),
            scripted_checks_summary="All checks passed",
        )

        # Should mention coherence or consistency
        assert "coherence" in prompt.lower() or "consistent" in prompt.lower()

    def test_includes_validation_file_references(self) -> None:
        """build_review_prompt should reference validation.md files in state directory."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            scripted_checks_summary="All checks passed",
        )

        # Should mention validation files to review
        assert "validation.md" in prompt or "validation" in prompt.lower()

    def test_includes_expected_output_format(self) -> None:
        """build_review_prompt should specify expected output format for the review."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            scripted_checks_summary="All checks passed",
        )

        # Should mention expected output or findings format
        assert "finding" in prompt.lower() or "report" in prompt.lower() or "output" in prompt.lower()

    def test_handles_empty_ticket_list(self) -> None:
        """build_review_prompt should handle empty ticket list gracefully."""
        from commands.scripted_checks import build_review_prompt

        prompt = build_review_prompt(
            ticket_ids=[],
            state_dir=Path("docs/state"),
            scripted_checks_summary="No checks run",
        )

        # Should still produce a valid prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestRunPostLoopReview:
    """Tests for run_post_loop_review() function."""

    def test_returns_review_result_dataclass(self) -> None:
        """run_post_loop_review should return a PostLoopReviewResult."""
        from commands.scripted_checks import run_post_loop_review, PostLoopReviewResult

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type":"result","result":"REVIEW_COMPLETE\\n\\nNo issues found."}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
                model="opus",
            )

            assert isinstance(result, PostLoopReviewResult)

    def test_uses_specified_model(self) -> None:
        """run_post_loop_review should invoke Claude with the specified model."""
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type":"result","result":"REVIEW_COMPLETE\\n\\nNo issues found."}',
                stderr="",
            )

            run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
                model="sonnet",
            )

            # Check that the model was passed to the command
            call_args = mock_run.call_args
            cmd = call_args[0][0]  # First positional arg is the command list
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "sonnet"

    def test_uses_opus_by_default(self) -> None:
        """run_post_loop_review should default to opus model when not specified."""
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type":"result","result":"REVIEW_COMPLETE\\n\\nNo issues found."}',
                stderr="",
            )

            run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
                # model not specified - should default to opus
            )

            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "opus"

    def test_dry_run_mode_returns_without_invocation(self) -> None:
        """run_post_loop_review should return without invoking Claude in dry_run mode."""
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            result = run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
                dry_run=True,
            )

            # Should not call subprocess.run in dry_run mode
            mock_run.assert_not_called()

            # Should return a valid result with dry_run status
            assert result.status == "dry_run"

    def test_handles_timeout(self) -> None:
        """run_post_loop_review should handle timeout gracefully."""
        import subprocess
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
                timeout_minutes=5,
            )

            assert result.status == "timeout"

    def test_parses_review_complete_response(self) -> None:
        """run_post_loop_review should parse REVIEW_COMPLETE from output."""
        from commands.scripted_checks import run_post_loop_review

        review_output = """REVIEW_COMPLETE

## Summary
All 3 tickets in the batch were implemented correctly.

## Cross-Ticket Analysis
- No conflicting changes between tickets
- Consistent coding patterns used

## Concerns
None identified.
"""
        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f'{{"type":"result","result":"{review_output.replace(chr(10), "\\n")}"}}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
            )

            assert result.status == "review_complete"

    def test_parses_review_concerns_response(self) -> None:
        """run_post_loop_review should parse REVIEW_CONCERNS from output."""
        from commands.scripted_checks import run_post_loop_review

        review_output = """REVIEW_CONCERNS

## Summary
Potential issues identified in the batch.

## Concerns
1. AIUI-0002 may conflict with AIUI-0001 changes
2. Inconsistent error handling patterns detected
"""
        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f'{{"type":"result","result":"{review_output.replace(chr(10), "\\n")}"}}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001", "AIUI-0002"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
            )

            assert result.status == "review_concerns"
            assert "AIUI-0002" in result.findings or "conflict" in result.findings.lower()

    def test_extracts_findings_from_response(self) -> None:
        """run_post_loop_review should extract findings text from response."""
        from commands.scripted_checks import run_post_loop_review

        review_output = """REVIEW_COMPLETE

## Findings
All tickets implemented correctly with consistent patterns.
"""
        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=f'{{"type":"result","result":"{review_output.replace(chr(10), "\\n")}"}}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
            )

            assert "implemented correctly" in result.findings or "consistent" in result.findings.lower()

    def test_includes_ticket_count_in_findings(self) -> None:
        """run_post_loop_review result should include ticket count."""
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type":"result","result":"REVIEW_COMPLETE\\n\\nAll good."}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
            )

            assert result.ticket_count == 3

    def test_handles_unknown_response(self) -> None:
        """run_post_loop_review should handle unrecognized response format."""
        from commands.scripted_checks import run_post_loop_review

        with patch("commands.scripted_checks.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"type":"result","result":"Some unexpected output format"}',
                stderr="",
            )

            result = run_post_loop_review(
                ticket_ids=["AIUI-0001"],
                state_dir=Path("docs/state"),
                scripted_checks_summary="All passed",
            )

            assert result.status == "unknown"
            assert result.raw_output is not None


class TestPostLoopReviewResult:
    """Tests for PostLoopReviewResult dataclass."""

    def test_has_required_fields(self) -> None:
        """PostLoopReviewResult should have all required fields."""
        from commands.scripted_checks import PostLoopReviewResult

        result = PostLoopReviewResult(
            status="review_complete",
            findings="No issues found",
            ticket_count=3,
            raw_output="REVIEW_COMPLETE\n\nNo issues found",
        )

        assert result.status == "review_complete"
        assert result.findings == "No issues found"
        assert result.ticket_count == 3
        assert "REVIEW_COMPLETE" in result.raw_output

    def test_has_concerns_property(self) -> None:
        """PostLoopReviewResult should have has_concerns property."""
        from commands.scripted_checks import PostLoopReviewResult

        # No concerns
        result_ok = PostLoopReviewResult(
            status="review_complete",
            findings="No issues",
            ticket_count=1,
        )
        assert result_ok.has_concerns is False

        # Has concerns
        result_concerns = PostLoopReviewResult(
            status="review_concerns",
            findings="Some issues found",
            ticket_count=1,
        )
        assert result_concerns.has_concerns is True

    def test_default_values(self) -> None:
        """PostLoopReviewResult should have sensible defaults."""
        from commands.scripted_checks import PostLoopReviewResult

        result = PostLoopReviewResult(status="unknown")

        assert result.findings == ""
        assert result.ticket_count == 0
        assert result.raw_output == ""
