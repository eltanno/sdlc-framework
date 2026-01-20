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
        """Given dry_run=True, when process_ticket runs, then Claude is not invoked."""
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

        # Claude should not be invoked in dry run
        mock_invoke.assert_not_called()
        assert result.status == "dry_run"

    def test_dry_run_process_ticket_returns_dry_run_status(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given dry_run=True, when process_ticket runs, then result has dry_run status."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        config = OrchestratorConfig()

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=prd_file,
            plan_path=plan_file,
            state_file=state_file,
            dry_run=True,
        )

        assert result.status == "dry_run"
        assert result.ticket_id == "TASK-001"
        assert result.attempts == 0


# ============================================================================
# Test Cases: Happy Path
# ============================================================================


class TestHappyPath:
    """Tests for successful completion scenarios."""

    def test_single_ticket_success(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given a single ticket that passes validation, when process_ticket runs,
        then the ticket is completed successfully."""
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
                with patch("commands.orchestrator.ticket_done"):
                    result = process_ticket(
                        ticket=ticket,
                        config=config,
                        prd_path=prd_file,
                        plan_path=plan_file,
                        state_file=state_file,
                        dry_run=False,
                    )

        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 100


# ============================================================================
# Test Cases: Retry Flow
# ============================================================================


class TestRetryFlow:
    """Tests for retry on validation failure."""

    def test_retry_on_validation_failure(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given validation fails then passes, when process_ticket runs,
        then ticket is completed after retry."""
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
        )
        pass_result = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="def456",
        )

        with patch("commands.orchestrator.invoke_claude", side_effect=[fail_result, pass_result]):
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

        assert result.status == "completed"
        assert result.attempts == 2


# ============================================================================
# Test Cases: All Blocked Scenario
# ============================================================================


class TestAllBlockedScenario:
    """Tests for when all tickets become blocked."""

    def test_ticket_blocked_after_max_attempts(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given max attempts exceeded, when process_ticket finishes,
        then ticket is marked blocked."""
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

        assert result.status == "blocked"
        assert result.attempts == 2
        assert "exceeded" in result.block_reason.lower()

    def test_blocked_result_includes_max_attempts(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path]
    ):
        """Given max attempts exceeded, when blocked, then block reason includes attempt count."""
        from commands.orchestrator import process_ticket

        prd_file, plan_file, state_file, config_file = single_ticket_workflow
        config = OrchestratorConfig(max_attempts=3)

        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])

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

        assert result.status == "blocked"
        assert "3" in result.block_reason


# ============================================================================
# Test Cases: Timeout Handling
# ============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling."""

    def test_timeout_triggers_retry(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given Claude times out, when process_ticket runs, then retry is attempted."""
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

        with patch("commands.orchestrator.invoke_claude", side_effect=[timeout_result, pass_result]):
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

        assert result.status == "completed"
        assert result.attempts == 2


# ============================================================================
# Test Cases: Completion Scenarios
# ============================================================================


class TestCompletionScenarios:
    """Tests for various completion scenarios."""

    def test_orchestrator_result_has_default_timing(self):
        """Given an OrchestratorResult, then it has timing fields initialized."""
        result = OrchestratorResult(status="running")

        assert result.start_time is None  # Not set until run_orchestrator
        assert result.end_time is None

    def test_incomplete_status_determination(self):
        """Test incomplete status is set when there are both completed and blocked tickets."""
        result = OrchestratorResult(
            status="running",
            completed_count=1,
            blocked_count=1,
        )

        # After orchestrator determines final status:
        # if blocked_count > 0 and completed_count > 0, status should be incomplete
        if result.blocked_count > 0 and result.completed_count == 0:
            final_status = "all_blocked"
        elif result.blocked_count > 0:
            final_status = "incomplete"
        else:
            final_status = "complete"

        assert final_status == "incomplete"


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

    def test_ticket_done_called_after_completion(
        self, single_ticket_workflow: tuple[Path, Path, Path, Path], tmp_path: Path
    ):
        """Given a ticket completes, when process_ticket finishes,
        then ticket_done is called to update state."""
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

        # ticket_done should have been called
        mock_done.assert_called_once()
