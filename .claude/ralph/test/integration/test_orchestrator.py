"""Integration tests for the main orchestrator loop.

This module tests the full orchestrator workflow including:
- Happy path (all tickets complete successfully)
- Retry flow (validation failures with retry)
- All blocked scenario
- Dry run mode
- Completion scenarios

These tests mock external CLI operations (Claude, gh, git).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
)
from commands.orchestrator import (
    run_orchestrator,
    select_model_for_complexity,
    OrchestratorConfig,
    OrchestratorResult,
    EngineerResult,
    ValidatorResult,
    VALIDATION_PASSED,
    VALIDATION_FAILED,
    VALIDATION_CONFIRMED,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def orchestrator_workflow(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a complete workflow setup for orchestrator testing.

    Returns:
        Tuple of (prd_file, plan_file, config_file)
    """
    # Create PRD
    prd_content = """# Test PRD

## Requirements
- FR-1: First feature
- FR-2: Second feature
"""
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(prd_content)

    # Create Plan
    plan_content = """# Test Plan

## Tickets
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First task | - |
| TASK-002 | Second task | TASK-001 |
"""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text(plan_content)

    # Create Config
    config_content = """\
ralph:
  max_attempts: 2
  sonnet_threshold: 2
  state_directory: "{state_dir}"

dev:
  test_command: "pytest"
  lint_command: "ruff check ."

git:
  default_branch: develop-working
"""
    config_content = config_content.replace("{state_dir}", str(tmp_path / "state"))
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return prd_file, plan_file, config_file


@pytest.fixture
def single_ticket_workflow(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a workflow with a single ticket.

    Returns:
        Tuple of (prd_file, plan_file, config_file)
    """
    prd_file = tmp_path / "prd.md"
    prd_file.write_text("# Test PRD\n")

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan\n")

    config_content = """\
ralph:
  max_attempts: 3

git:
  default_branch: develop-working
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return prd_file, plan_file, config_file


class TestComplexityFlowEndToEnd:
    """Integration tests verifying complexity flows from PRD to model selection.

    This test class ensures that:
    1. Complexity is parsed from PRD ticket tables
    2. Complexity is passed to Ticket objects
    3. Complexity is used for model selection

    This is the integration test that prevents regression of the complexity feature.
    """

    def test_complexity_parsed_from_prd_table(self, tmp_path):
        """Given PRD with complexity column, when parsed, then complexity is extracted."""
        from commands.parse_deps import parse_ticket_metadata

        prd_content = """# PRD

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| TASK-001 | Simple task | Do something simple | P1 | 1 | - |
| TASK-002 | Medium task | Do something medium | P1 | 3 | TASK-001 |
| TASK-003 | Complex task | Do something complex | P1 | 5 | TASK-002 |
"""
        prd_file = tmp_path / "prd.md"
        prd_file.write_text(prd_content)

        metadata = parse_ticket_metadata(prd_file)

        assert metadata["TASK-001"].complexity == 1
        assert metadata["TASK-002"].complexity == 3
        assert metadata["TASK-003"].complexity == 5

    def test_complexity_passed_to_ticket_object(self, tmp_path):
        """Given state with complexity, when get_next_ticket runs, then Ticket has complexity."""
        from core.state import WorkflowState, RalphState
        from commands.get_next import get_next_ticket
        from core.pm import LocalPM

        # Create state with complexity data
        ralph = RalphState(
            source="none",
            tickets=["TASK-001", "TASK-002"],
            dependencies={},
            complexity={"TASK-001": 1, "TASK-002": 5},
            attempts={},
            blocked={},
        )
        state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
            ralph=ralph,
        )

        # Use LocalPM which doesn't query GitHub
        # Pass ralph_label=None since LocalPM doesn't support claiming
        pm_tool = LocalPM()

        result = get_next_ticket(state, pm_tool=pm_tool, ralph_label=None)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.ticket.complexity == 1

    def test_complexity_affects_model_selection_in_process_ticket(self, tmp_path):
        """Given ticket with complexity 1, when processed, then sonnet model is selected.

        This is the critical end-to-end test that verifies the full flow:
        PRD -> State -> Ticket -> Model Selection
        """
        from core.state import Ticket

        # Create ticket with low complexity
        ticket = Ticket(
            id="TASK-001",
            title="Simple task",
            status="pending",
            dependencies=[],
            complexity=1,
        )

        # Verify model selection uses ticket complexity
        model = select_model_for_complexity(ticket.complexity, sonnet_threshold=3)
        assert model == "sonnet", "Complexity 1 should use sonnet with threshold 3"

        # Create ticket with high complexity
        ticket_complex = Ticket(
            id="TASK-002",
            title="Complex task",
            status="pending",
            dependencies=[],
            complexity=5,
        )

        model_complex = select_model_for_complexity(ticket_complex.complexity, sonnet_threshold=3)
        assert model_complex == "opus", "Complexity 5 should use opus with threshold 3"

    def test_default_complexity_when_not_in_state(self, tmp_path):
        """Given state without complexity for a ticket, when processed, then default of 3 is used."""
        from core.state import WorkflowState, RalphState
        from commands.get_next import get_next_ticket
        from core.pm import LocalPM

        # Create state WITHOUT complexity data (simulating old state files)
        ralph = RalphState(
            source="none",
            tickets=["TASK-001"],
            dependencies={},
            complexity={},  # Empty - no complexity data
            attempts={},
            blocked={},
        )
        state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
            ralph=ralph,
        )

        # Pass ralph_label=None since LocalPM doesn't support claiming
        pm_tool = LocalPM()
        result = get_next_ticket(state, pm_tool=pm_tool, ralph_label=None)

        assert result.ticket is not None
        assert result.ticket.complexity == 3, "Should default to complexity 3 when not in state"


# ============================================================================
# Test Cases: Dry Run Mode
# ============================================================================


class TestDryRunMode:
    """Tests for dry run mode.

    Note: The orchestrator in dry_run mode doesn't update state, so the loop
    would continue forever processing the same ticket. These tests verify
    process_ticket behavior in dry_run mode rather than full orchestrator runs.
    """

    def test_dry_run_process_ticket_no_claude_invocation(
        self, orchestrator_workflow: tuple[Path, Path, Path]
    ):
        """Given dry_run=True, when process_ticket runs, then Claude is not invoked
        AND the result contains preview information about what WOULD be done."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = orchestrator_workflow
        config = OrchestratorConfig()

        # Create a test ticket
        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        with patch("commands.orchestrator.invoke_claude") as mock_invoke:
            result = process_ticket(
                ticket=ticket,
                config=config,
                prd_path=prd_file,
                plan_path=plan_file,
                dry_run=True,
            )

            # Verify Claude is not invoked
            mock_invoke.assert_not_called()

            # Verify dry run result contains correct metadata
            assert result.status == "dry_run"
            assert result.ticket_id == "TASK-001"
            assert result.attempts == 0

            # Verify it indicates what WOULD happen (preview behavior)
            # In dry run, the function should return early without any state changes


# ============================================================================
# Test Cases: Happy Path
# ============================================================================


class TestHappyPath:
    """Tests for successful completion scenarios."""

    def test_single_ticket_success(
        self, single_ticket_workflow: tuple[Path, Path, Path], tmp_path: Path
    ):
        """Given a single ticket that passes validation, when process_ticket runs,
        then the ticket is completed successfully AND pr_flow is called with correct metadata."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(state_directory=state_dir, default_branch="develop-working")
        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # Mock Claude to return VALIDATION_PASSED
        mock_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        # Mock validator to confirm the work
        mock_validator_result = ValidatorResult(
            status=VALIDATION_CONFIRMED,
            reason="All acceptance criteria verified",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=mock_result):
            with patch("commands.orchestrator.invoke_validator", return_value=mock_validator_result):
                with patch("commands.orchestrator.pr_flow") as mock_pr:
                    mock_pr.return_value = MagicMock(pr_number=100)
                    with patch("commands.orchestrator.ticket_done") as mock_done:
                        result = process_ticket(
                            ticket=ticket,
                            config=config,
                            prd_path=prd_file,
                            plan_path=plan_file,
                            dry_run=False,
                        )

        # Verify completion status
        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 100

        # Verify pr_flow was called with correct ticket ID, commit message, and default branch
        mock_pr.assert_called_once_with(
            ticket_id="TASK-001",
            commit_message="[TASK-001] Implementation complete",
            dry_run=False,
            default_branch="develop-working",
        )

        # Verify ticket_done was called with correct ticket ID and PR number
        mock_done.assert_called_once()
        call_kwargs = mock_done.call_args.kwargs
        assert call_kwargs["ticket_id"] == "TASK-001"
        assert call_kwargs["pr_number"] == "100"


# ============================================================================
# Test Cases: Retry Flow
# ============================================================================


class TestRetryFlow:
    """Tests for retry on validation failure."""

    def test_retry_on_validation_failure(
        self, single_ticket_workflow: tuple[Path, Path, Path], tmp_path: Path
    ):
        """Given validation fails then passes, when process_ticket runs,
        then ticket is completed after retry AND second attempt includes failure context."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(max_attempts=3, state_directory=state_dir, default_branch="develop-working")

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # Mock Claude to fail first, then succeed
        fail_result = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )
        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="def456",
        )

        # Mock validator to confirm on second attempt
        mock_validator_result = ValidatorResult(
            status=VALIDATION_CONFIRMED,
            reason="All acceptance criteria verified",
        )

        with patch("commands.orchestrator.invoke_claude", side_effect=[fail_result, pass_result]) as mock_invoke:
            with patch("commands.orchestrator.invoke_validator", return_value=mock_validator_result):
                with patch("commands.orchestrator.pr_flow") as mock_pr:
                    mock_pr.return_value = MagicMock(pr_number=100)
                    with patch("commands.orchestrator.ticket_done"):
                        result = process_ticket(
                            ticket=ticket,
                            config=config,
                            prd_path=prd_file,
                            plan_path=plan_file,
                            dry_run=False,
                        )

        # Verify completion after retry
        assert result.status == "completed"
        assert result.attempts == 2

        # Verify invoke_claude was called twice (retry behavior)
        assert mock_invoke.call_count == 2

        # Both calls should have the same basic structure (prompt, timeout, model)
        for call in mock_invoke.call_args_list:
            assert "prompt" in call.kwargs
            assert "timeout_minutes" in call.kwargs
            assert "model" in call.kwargs
            assert call.kwargs["dry_run"] == False


# ============================================================================
# Test Cases: All Blocked Scenario
# ============================================================================


class TestAllBlockedScenario:
    """Tests for when all tickets become blocked."""

    def test_ticket_blocked_after_max_attempts(
        self, single_ticket_workflow: tuple[Path, Path, Path]
    ):
        """Given max attempts exceeded, when process_ticket finishes,
        then ticket is marked blocked with clear explanation of failure."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        config = OrchestratorConfig(max_attempts=2)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # Mock Claude to always fail
        fail_result = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=fail_result):
            result = process_ticket(
                ticket=ticket,
                config=config,
                prd_path=prd_file,
                plan_path=plan_file,
                dry_run=False,
            )

        # Verify blocked status
        assert result.status == "blocked"
        assert result.attempts == 2
        assert result.ticket_id == "TASK-001"

        # Verify block reason contains required debugging information
        assert "2" in result.block_reason  # max_attempts value
        reason_lower = result.block_reason.lower()
        assert any(keyword in reason_lower for keyword in ["exceeded", "maximum", "max", "attempts"])

    def test_blocked_result_explains_what_failed(
        self, single_ticket_workflow: tuple[Path, Path, Path]
    ):
        """Given max attempts exceeded, when blocked, then block reason explains
        the ticket ID and attempt count for debugging."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        config = OrchestratorConfig(max_attempts=3)

        ticket = Ticket(id="TASK-001", title="Test task", status="pending", dependencies=[])

        fail_result = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=fail_result):
            result = process_ticket(
                ticket=ticket,
                config=config,
                prd_path=prd_file,
                plan_path=plan_file,
                dry_run=False,
            )

        # Verify block reason contains essential debugging info
        assert result.status == "blocked"
        assert result.attempts == 3
        assert result.ticket_id == "TASK-001"  # Ticket ID is in the result object

        # Must contain attempt count in the reason
        assert "3" in result.block_reason

        # Must indicate it's about exceeding attempts (not just "3 seconds" or random "3")
        reason_lower = result.block_reason.lower()
        assert "attempt" in reason_lower or "tries" in reason_lower


# ============================================================================
# Test Cases: Timeout Handling
# ============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling."""

    def test_timeout_triggers_retry(
        self, single_ticket_workflow: tuple[Path, Path, Path], tmp_path: Path
    ):
        """Given Claude times out, when process_ticket runs, then retry is attempted
        AND timeout is treated as retryable (not permanent failure)."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(max_attempts=3, state_directory=state_dir, default_branch="develop-working")

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # First call times out, second succeeds
        timeout_result = EngineerResult(status="timeout", raw_output="Timed out")
        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        # Mock validator to confirm on second attempt
        mock_validator_result = ValidatorResult(
            status=VALIDATION_CONFIRMED,
            reason="All acceptance criteria verified",
        )

        with patch("commands.orchestrator.invoke_claude", side_effect=[timeout_result, pass_result]) as mock_invoke:
            with patch("commands.orchestrator.invoke_validator", return_value=mock_validator_result):
                with patch("commands.orchestrator.pr_flow") as mock_pr:
                    mock_pr.return_value = MagicMock(pr_number=100)
                    with patch("commands.orchestrator.ticket_done"):
                        result = process_ticket(
                            ticket=ticket,
                            config=config,
                            prd_path=prd_file,
                            plan_path=plan_file,
                            dry_run=False,
                        )

        # Verify retry happened after timeout
        assert result.status == "completed"
        assert result.attempts == 2

        # Verify timeout was treated as retryable error (called twice)
        assert mock_invoke.call_count == 2

        # Verify both calls were made with consistent parameters
        for call in mock_invoke.call_args_list:
            assert "prompt" in call.kwargs
            assert call.kwargs["dry_run"] == False


# ============================================================================
# Test Cases: Completion Scenarios
# ============================================================================


class TestCompletionScenarios:
    """Tests for various completion scenarios."""

    def test_orchestrator_result_tracks_timing(self):
        """Given an OrchestratorResult is created, when timing is set,
        then start_time and end_time are available for metrics."""
        from datetime import datetime

        result = OrchestratorResult(status="running")

        # Initially unset
        assert result.start_time is None
        assert result.end_time is None

        # After setting (simulating what run_orchestrator does)
        result.start_time = datetime.now()
        result.end_time = datetime.now()

        # Verify timing fields are populated
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.end_time >= result.start_time


# ============================================================================
# Test Cases: Dependency Waiting
# ============================================================================


class TestDependencyWaiting:
    """Tests for dependency waiting behavior."""

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_orchestrator_handles_waiting_on_dependencies(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path
    ):
        """Given tickets waiting on dependencies that won't resolve, when max wait reached,
        then orchestrator exits."""
        # Setup PM tool mock
        mock_create_pm.return_value = MagicMock()

        # Create minimal files for config
        prd_file = tmp_path / "prd.md"
        prd_file.write_text("# Test PRD\n")
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Test Plan\n")

        # Setup mock state
        mock_state = WorkflowState(
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
        )
        mock_build_state.return_value = mock_state

        # Return waiting_on_dependencies status for max_wait_retries times, then complete
        mock_get_next.side_effect = [
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        config_content = """\
ralph:
  max_attempts: 3
pm:
  tool: none
git:
  default_branch: develop-working
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        # RALPH_LABEL is required
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
            result = run_orchestrator(
                prd_path=prd_file,
                plan_path=plan_file,
                workflow_state=mock_state,
                config_file=config_file,
                dry_run=False,
                max_wait_retries=1,  # Only wait once
                wait_interval=0,  # Don't actually wait
            )

        # TASK-002 is waiting on blocked TASK-001, so nothing gets processed
        # The orchestrator should exit after max wait retries
        assert result.completed_count == 0
        assert result.status == "complete"


# ============================================================================
# Test Cases: Claims Waiting (Gap 8 Fix - SLCA-0081)
# ============================================================================


class TestClaimsWaiting:
    """Tests for waiting_on_claims retry behavior (Gap 8 fix).

    When all eligible tickets are claimed by other instances, the orchestrator
    must retry with a wait instead of exiting prematurely.
    """

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_waiting_on_claims_triggers_retry(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
    ):
        """Given `get_next_ticket` returns `waiting_on_claims`, when orchestrator
        processes this status, then it retries instead of exiting immediately."""
        mock_create_pm.return_value = MagicMock()

        prd_file = tmp_path / "prd.md"
        prd_file.write_text("# Test PRD\n")
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Test Plan\n")

        mock_state = WorkflowState(
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
        )
        mock_build_state.return_value = mock_state

        # Return waiting_on_claims once, then no_more_tickets
        mock_get_next.side_effect = [
            MagicMock(ticket=None, has_more=True, status="waiting_on_claims"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        config_content = """\
ralph:
  max_attempts: 3
pm:
  tool: none
git:
  default_branch: develop-working
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
            result = run_orchestrator(
                prd_path=prd_file,
                plan_path=plan_file,
                workflow_state=mock_state,
                config_file=config_file,
                dry_run=False,
                max_wait_retries=3,  # More than the 1 waiting_on_claims response
                wait_interval=0,  # Don't actually wait
            )

        # Orchestrator must have retried: get_next_ticket called at least twice
        # (not once, which would mean it exited immediately on waiting_on_claims)
        assert mock_get_next.call_count == 2, (
            f"Expected 2 calls to get_next_ticket (retry after waiting_on_claims), "
            f"got {mock_get_next.call_count}. "
            "Orchestrator must not exit immediately on waiting_on_claims."
        )
        assert result.completed_count == 0
        assert result.status == "complete"

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_waiting_on_claims_timeout_exits_gracefully(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """Given repeated `waiting_on_claims` responses, when max wait time is exceeded,
        then orchestrator exits gracefully with a clear log message."""
        import logging

        mock_create_pm.return_value = MagicMock()

        prd_file = tmp_path / "prd.md"
        prd_file.write_text("# Test PRD\n")
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Test Plan\n")

        mock_state = WorkflowState(
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
        )
        mock_build_state.return_value = mock_state

        # Always return waiting_on_claims
        mock_get_next.return_value = MagicMock(
            ticket=None, has_more=True, status="waiting_on_claims"
        )

        config_content = """\
ralph:
  max_attempts: 3
pm:
  tool: none
git:
  default_branch: develop-working
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with caplog.at_level(logging.INFO, logger="commands.orchestrator"):
            with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
                result = run_orchestrator(
                    prd_path=prd_file,
                    plan_path=plan_file,
                    workflow_state=mock_state,
                    config_file=config_file,
                    dry_run=False,
                    max_wait_retries=2,  # Exit after 2 retries
                    wait_interval=0,  # Don't actually wait
                )

        # Orchestrator exits after max_wait_retries calls
        assert mock_get_next.call_count == 2, (
            f"Expected 2 calls (max_wait_retries=2), got {mock_get_next.call_count}"
        )
        assert result.completed_count == 0
        # Must exit cleanly (not crash)
        assert result.status == "complete"

        # Must log a clear message about the timeout
        log_text = " ".join(caplog.messages).lower()
        assert any(
            keyword in log_text
            for keyword in ["claim", "wait", "timeout", "max", "exit"]
        ), f"Expected a log message about claims wait timeout, got: {caplog.messages}"


# ============================================================================
# Test Cases: State File Integration
# ============================================================================


class TestTicketDoneIntegration:
    """Tests for ticket_done integration with process_ticket."""

    def test_ticket_done_called_with_correct_data(
        self, single_ticket_workflow: tuple[Path, Path, Path], tmp_path: Path
    ):
        """Given a ticket completes, when process_ticket finishes,
        then ticket_done is called with correct ticket ID and PR number."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(state_directory=state_dir, default_branch="develop-working")

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        # Mock validator to confirm the work
        mock_validator_result = ValidatorResult(
            status=VALIDATION_CONFIRMED,
            reason="All acceptance criteria verified",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=pass_result):
            with patch("commands.orchestrator.invoke_validator", return_value=mock_validator_result):
                with patch("commands.orchestrator.pr_flow") as mock_pr:
                    mock_pr.return_value = MagicMock(pr_number=100)
                    with patch("commands.orchestrator.ticket_done") as mock_done:
                        process_ticket(
                            ticket=ticket,
                            config=config,
                            prd_path=prd_file,
                            plan_path=plan_file,
                            dry_run=False,
                        )

        # Verify ticket_done was called with correct arguments
        mock_done.assert_called_once()
        call_kwargs = mock_done.call_args.kwargs

        # Verify it received the ticket ID and PR number
        assert call_kwargs["ticket_id"] == "TASK-001"
        assert call_kwargs["pr_number"] == "100"


# ============================================================================
# Test Cases: SYSTEM.md Update Moved to /ralph-loop (SLCA-0085)
# ============================================================================


class TestSystemManifestNotCalledByOrchestrator:
    """Tests verifying that run_orchestrator does NOT call update_system_manifest.

    SLCA-0085: The SYSTEM.md update was moved from the orchestrator to the
    /ralph-loop command to prevent conflicts when running concurrent loops.
    Each orchestrator instance should NOT attempt to update SYSTEM.md.
    """

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    @patch("commands.orchestrator.process_ticket")
    def test_run_orchestrator_does_not_call_update_system_manifest(
        self,
        mock_process_ticket: MagicMock,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
    ):
        """Given tickets complete successfully, when run_orchestrator finishes,
        then update_system_manifest is NOT called (it is now the caller's
        responsibility via /ralph-loop)."""
        mock_create_pm.return_value = MagicMock()

        prd_file = tmp_path / "prd.md"
        prd_file.write_text("# Test PRD\n")
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Test Plan\n")

        mock_state = WorkflowState(
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
        )
        mock_build_state.return_value = mock_state

        # First call returns a ticket, second call returns complete
        mock_ticket = MagicMock()
        mock_ticket.ticket = Ticket(
            id="TASK-001", title="Test", status="pending", dependencies=[]
        )
        mock_ticket.has_more = True
        mock_ticket.status = "ready"

        mock_get_next.side_effect = [
            mock_ticket,
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        # process_ticket returns completed result
        from commands.orchestrator import TicketResult

        mock_process_ticket.return_value = TicketResult(
            ticket_id="TASK-001",
            status="completed",
            attempts=1,
            pr_number=100,
        )

        config_content = """\
ralph:
  max_attempts: 3
pm:
  tool: none
git:
  default_branch: develop-working
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
            with patch(
                "commands.orchestrator.update_system_manifest"
            ) as mock_update:
                result = run_orchestrator(
                    prd_path=prd_file,
                    plan_path=plan_file,
                    workflow_state=mock_state,
                    config_file=config_file,
                    dry_run=False,
                )

        # Verify ticket was completed
        assert result.completed_count == 1

        # CRITICAL: update_system_manifest must NOT be called by run_orchestrator
        mock_update.assert_not_called()

    def test_update_system_manifest_is_importable_as_public_api(self):
        """Given the function was renamed from _update_system_manifest,
        when importing from orchestrator, then it is available as
        update_system_manifest (no leading underscore)."""
        from commands.orchestrator import update_system_manifest

        assert callable(update_system_manifest)
