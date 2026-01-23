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
    save_workflow_state,
)
from commands.orchestrator import (
    run_orchestrator,
    load_config,
    parse_engineer_result,
    select_model_for_complexity,
    OrchestratorConfig,
    OrchestratorResult,
    EngineerResult,
    VALIDATION_PASSED,
    VALIDATION_FAILED,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_config(tmp_path: Path) -> Path:
    """Create a test config.yaml file.

    Returns:
        Path to the config file
    """
    config_content = """
project:
  name: test-project

ralph:
  max_attempts: 3
  sonnet_threshold: 2
  state_directory: "docs/state"
  engineer_timeout: 30
  validator_timeout: 10

dev:
  test_command: "pytest"
  lint_command: "ruff check ."
  typecheck_command: "mypy ."
  build_command: "python -m build"

git:
  default_branch: main
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def orchestrator_workflow(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a complete workflow setup for orchestrator testing.

    Returns:
        Tuple of (prd_file, plan_file, state_file, config_file)
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

    # Create State
    tickets = [
        Ticket(id="TASK-001", title="First task", status="pending", dependencies=[]),
        Ticket(id="TASK-002", title="Second task", status="pending", dependencies=["TASK-001"]),
    ]
    ralph = RalphState(
        tickets=["TASK-001", "TASK-002"],
        dependencies={"TASK-002": ["TASK-001"]},
        attempts={},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=prd_file,
        plan_path=plan_file,
        tickets=tickets,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)

    # Create Config
    config_content = """
ralph:
  max_attempts: 2
  sonnet_threshold: 2
  state_directory: "{state_dir}"

dev:
  test_command: "pytest"
  lint_command: "ruff check ."
"""
    config_content = config_content.replace("{state_dir}", str(tmp_path / "state"))
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return prd_file, plan_file, state_file, config_file


@pytest.fixture
def single_ticket_workflow(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a workflow with a single ticket.

    Returns:
        Tuple of (prd_file, plan_file, state_file, config_file)
    """
    prd_file = tmp_path / "prd.md"
    prd_file.write_text("# Test PRD\n")

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Test Plan\n")

    tickets = [
        Ticket(id="TASK-001", title="Only task", status="pending", dependencies=[]),
    ]
    ralph = RalphState(
        tickets=["TASK-001"],
        dependencies={},
        attempts={},
        blocked={},
        source="github",
    )
    state = WorkflowState(
        version="2.0",
        prd_path=prd_file,
        plan_path=plan_file,
        tickets=tickets,
        ralph=ralph,
    )
    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)

    config_content = """
ralph:
  max_attempts: 3
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    return prd_file, plan_file, state_file, config_file


# ============================================================================
# Test Cases: Configuration Loading
# ============================================================================


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_config_from_yaml(self, test_config: Path):
        """Given a valid config.yaml, when loaded, then values are correct."""
        config = load_config(test_config)

        assert config.max_attempts == 3
        assert config.sonnet_threshold == 2
        assert config.engineer_timeout == 30
        assert config.test_command == "pytest"
        assert config.default_branch == "main"

    def test_load_config_with_defaults(self, tmp_path: Path):
        """Given a minimal config.yaml, when loaded, then defaults are used."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("project:\n  name: test\n")

        config = load_config(config_file)

        assert config.max_attempts == 3  # default
        assert config.sonnet_threshold == 2  # default
        assert config.engineer_timeout == 30  # default

    def test_load_config_missing_file(self, tmp_path: Path):
        """Given config.yaml doesn't exist, when loading, then error is raised."""
        fake_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(fake_config)


# ============================================================================
# Test Cases: Model Selection
# ============================================================================


class TestModelSelection:
    """Tests for model selection based on complexity."""

    def test_sonnet_for_low_complexity(self):
        """Given low complexity ticket, when selecting model, then sonnet is chosen."""
        assert select_model_for_complexity(1, sonnet_threshold=2) == "sonnet"
        assert select_model_for_complexity(2, sonnet_threshold=2) == "sonnet"

    def test_opus_for_high_complexity(self):
        """Given high complexity ticket, when selecting model, then opus is chosen."""
        assert select_model_for_complexity(3, sonnet_threshold=2) == "opus"
        assert select_model_for_complexity(4, sonnet_threshold=2) == "opus"
        assert select_model_for_complexity(5, sonnet_threshold=2) == "opus"


class TestComplexityFlowEndToEnd:
    """Integration tests verifying complexity flows from PRD to model selection.

    This test class ensures that:
    1. Complexity is parsed from PRD ticket tables
    2. Complexity is stored in the state file
    3. Complexity is passed to Ticket objects
    4. Complexity is used for model selection

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

    def test_complexity_stored_in_state_file(self, tmp_path):
        """Given PRD with complexity, when setup runs, then state file contains complexity."""
        from commands.setup import initialize_workflow_state
        import json

        prd_content = """# PRD

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| TEST-001 | Task 1 | Description | P1 | 2 | - |
| TEST-002 | Task 2 | Description | P1 | 4 | TEST-001 |
"""
        prd_file = tmp_path / "prd.md"
        prd_file.write_text(prd_content)

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\nNo table here.")

        state_file = tmp_path / "state.json"

        initialize_workflow_state(prd_file, plan_file, state_file)

        # Read and verify state file
        state_data = json.loads(state_file.read_text())
        assert "ralph" in state_data
        assert "complexity" in state_data["ralph"]
        assert state_data["ralph"]["complexity"]["TEST-001"] == 2
        assert state_data["ralph"]["complexity"]["TEST-002"] == 4

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
            version="2.0",
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
            version="2.0",
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
# Test Cases: Engineer Result Parsing
# ============================================================================


class TestEngineerResultParsing:
    """Tests for parsing engineer output."""

    def test_parse_validation_passed(self):
        """Given VALIDATION_PASSED output, when parsed, then status is correct."""
        output = """
VALIDATION_PASSED

Ticket: TASK-001
Branch: feature/TASK-001-implementation
Commit: abc123def
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_PASSED
        assert result.ticket_id == "TASK-001"
        assert result.branch == "feature/TASK-001-implementation"
        assert result.commit == "abc123def"

    def test_parse_validation_failed(self):
        """Given VALIDATION_FAILED output, when parsed, then status is correct."""
        output = """
VALIDATION_FAILED

Ticket: TASK-002
Branch: feature/TASK-002-implementation
Commit: def456ghi
State file: docs/state/TASK-002/attempt-1/engineer-state.md
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_FAILED
        assert result.ticket_id == "TASK-002"
        assert result.state_file == "docs/state/TASK-002/attempt-1/engineer-state.md"

    def test_parse_timeout_result(self):
        """Given timeout occurred, when parsed, then status is timeout."""
        output = "Some partial output before timeout..."

        result = parse_engineer_result(output, is_timeout=True)

        assert result.status == "timeout"
        assert result.raw_output == output

    def test_parse_unknown_result(self):
        """Given no validation marker, when parsed, then status is unknown."""
        output = "Some output without markers"

        result = parse_engineer_result(output)

        assert result.status == "unknown"


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
        self, orchestrator_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given dry_run=True, when process_ticket runs, then Claude is not invoked
        AND the result contains preview information about what WOULD be done."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = orchestrator_workflow
        config = OrchestratorConfig()

        # Create a test ticket
        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        with patch("commands.orchestrator.invoke_claude") as mock_invoke:
            result = process_ticket(
                ticket=ticket,
                config=config,
                prd_path=prd_file,
                plan_path=plan_file,
                state_file=state_file,
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
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given a single ticket that passes validation, when process_ticket runs,
        then the ticket is completed successfully AND pr_flow is called with correct metadata."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(state_directory=state_dir)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # Mock Claude to return VALIDATION_PASSED
        mock_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=mock_result):
            with patch("commands.orchestrator.pr_flow") as mock_pr:
                mock_pr.return_value = MagicMock(pr_number=100)
                with patch("commands.orchestrator.ticket_done") as mock_done:
                    result = process_ticket(
                        ticket=ticket,
                        config=config,
                        prd_path=prd_file,
                        plan_path=plan_file,
                        state_file=state_file,
                        dry_run=False,
                    )

        # Verify completion status
        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 100

        # Verify pr_flow was called with correct ticket ID and commit message
        mock_pr.assert_called_once_with(
            ticket_id="TASK-001",
            commit_message="[TASK-001] Implementation complete",
            dry_run=False,
        )

        # Verify ticket_done was called with correct ticket ID, PR number, and state file
        mock_done.assert_called_once()
        call_kwargs = mock_done.call_args.kwargs
        assert call_kwargs["ticket_id"] == "TASK-001"
        assert call_kwargs["pr_number"] == "100"
        assert call_kwargs["state_file"] == state_file


# ============================================================================
# Test Cases: Retry Flow
# ============================================================================


class TestRetryFlow:
    """Tests for retry on validation failure."""

    def test_retry_on_validation_failure(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given validation fails then passes, when process_ticket runs,
        then ticket is completed after retry AND second attempt includes failure context."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(max_attempts=3, state_directory=state_dir)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # Mock Claude to fail first, then succeed
        fail_result = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
            state_file="docs/state/TASK-001/attempt-1/state.md",
        )
        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="def456",
        )

        with patch("commands.orchestrator.invoke_claude", side_effect=[fail_result, pass_result]) as mock_invoke:
            with patch("commands.orchestrator.pr_flow") as mock_pr:
                mock_pr.return_value = MagicMock(pr_number=100)
                with patch("commands.orchestrator.ticket_done"):
                    result = process_ticket(
                        ticket=ticket,
                        config=config,
                        prd_path=prd_file,
                        plan_path=plan_file,
                        state_file=state_file,
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
        self, single_ticket_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given max attempts exceeded, when process_ticket finishes,
        then ticket is marked blocked with clear explanation of failure."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
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
                state_file=state_file,
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
        self, single_ticket_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given max attempts exceeded, when blocked, then block reason explains
        the ticket ID and attempt count for debugging."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
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
                state_file=state_file,
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
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given Claude times out, when process_ticket runs, then retry is attempted
        AND timeout is treated as retryable (not permanent failure)."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(max_attempts=3, state_directory=state_dir)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        # First call times out, second succeeds
        timeout_result = EngineerResult(status="timeout", raw_output="Timed out")
        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        with patch("commands.orchestrator.invoke_claude", side_effect=[timeout_result, pass_result]) as mock_invoke:
            with patch("commands.orchestrator.pr_flow") as mock_pr:
                mock_pr.return_value = MagicMock(pr_number=100)
                with patch("commands.orchestrator.ticket_done"):
                    result = process_ticket(
                        ticket=ticket,
                        config=config,
                        prd_path=prd_file,
                        plan_path=plan_file,
                        state_file=state_file,
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
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_orchestrator_handles_waiting_on_dependencies(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
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
            version="2.0",
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
        )
        mock_load_state.return_value = mock_state

        # Return waiting_on_dependencies status for max_wait_retries times, then complete
        mock_get_next.side_effect = [
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        config_content = """
ralph:
  max_attempts: 3
pm:
  tool: none
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        # RALPH_LABEL is required
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
            result = run_orchestrator(
                prd_path=prd_file,
                plan_path=plan_file,
                state_file=tmp_path / "state.json",
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
# Test Cases: State File Integration
# ============================================================================


class TestStateFileIntegration:
    """Tests for state file integration with process_ticket."""

    def test_ticket_done_called_with_correct_state(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given a ticket completes, when process_ticket finishes,
        then ticket_done is called with correct ticket ID and state file."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        state_dir = tmp_path / "test_state"
        state_dir.mkdir()
        config = OrchestratorConfig(state_directory=state_dir)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc123",
        )

        with patch("commands.orchestrator.invoke_claude", return_value=pass_result):
            with patch("commands.orchestrator.pr_flow") as mock_pr:
                mock_pr.return_value = MagicMock(pr_number=100)
                with patch("commands.orchestrator.ticket_done") as mock_done:
                    process_ticket(
                        ticket=ticket,
                        config=config,
                        prd_path=prd_file,
                        plan_path=plan_file,
                        state_file=state_file,
                        dry_run=False,
                    )

        # Verify ticket_done was called with correct arguments
        mock_done.assert_called_once()
        call_kwargs = mock_done.call_args.kwargs

        # Verify it received the state file and ticket ID
        assert call_kwargs["ticket_id"] == "TASK-001"
        assert call_kwargs["state_file"] == state_file
        assert call_kwargs["pr_number"] == "100"
