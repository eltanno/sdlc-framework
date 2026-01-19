"""Unit tests for the orchestrator module.

Tests the main orchestrator loop including:
- Configuration loading
- Ticket iteration and processing
- Validation handling
- PR flow integration
- Error handling and recovery
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from commands.orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    TicketResult,
    load_config,
    run_orchestrator,
    process_ticket,
    invoke_claude,
    parse_engineer_result,
    EngineerResult,
    VALIDATION_PASSED,
    VALIDATION_FAILED,
)
from core.state import WorkflowState, Ticket


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_config_yaml(tmp_path: Path) -> Path:
    """Create a sample config.yaml file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  state_directory: "docs/state"
  validator_model: "haiku"
  engineer_timeout: 30
  validator_timeout: 10

pm:
  tool: github

dev:
  test_command: "npm test"
  lint_command: "npm run lint"
  typecheck_command: "npm run typecheck"
  build_command: "npm run build"

git:
  default_branch: main
""")
    return config_file


@pytest.fixture
def sample_env_file(tmp_path: Path) -> Path:
    """Create a sample .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("RALPH_LABEL=ralph-1\n")
    return env_file


@pytest.fixture
def sample_prd(tmp_path: Path) -> Path:
    """Create a sample PRD file."""
    prd_file = tmp_path / "docs" / "prds" / "sample.md"
    prd_file.parent.mkdir(parents=True, exist_ok=True)
    prd_file.write_text("""# Sample PRD

## Tickets

| ID | Title | Description |
|----|-------|-------------|
| TASK-001 | Setup | Initial setup |
| TASK-002 | Feature | Main feature |
""")
    return prd_file


@pytest.fixture
def sample_plan(tmp_path: Path) -> Path:
    """Create a sample plan file."""
    plan_file = tmp_path / "docs" / "plans" / "sample.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("""# Sample Plan

## Tickets

| ID | Title | Description | Priority | Complexity | Dependencies |
|----|-------|-------------|----------|------------|--------------|
| TASK-001 | Setup | Initial setup | P1 | 2 | - |
| TASK-002 | Feature | Main feature | P1 | 3 | TASK-001 |
""")
    return plan_file


@pytest.fixture
def sample_state_file(tmp_path: Path) -> Path:
    """Create a sample workflow-state.json file."""
    state_file = tmp_path / "workflow-state.json"
    state_data = {
        "version": "1.0",
        "prd_path": "docs/prds/sample.md",
        "plan_path": "docs/plans/sample.md",
        "tickets": [
            {
                "id": "TASK-001",
                "title": "Setup",
                "status": "pending",
                "dependencies": [],
                "complexity": 2,
            },
            {
                "id": "TASK-002",
                "title": "Feature",
                "status": "pending",
                "dependencies": ["TASK-001"],
                "complexity": 3,
            },
        ],
        "current_ticket": None,
        "completed_count": 0,
        "blocked_count": 0,
    }
    state_file.write_text(json.dumps(state_data, indent=2))
    return state_file


# ============================================================================
# Test OrchestratorConfig
# ============================================================================


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_valid_file(self, sample_config_yaml: Path, tmp_path: Path) -> None:
        """Test loading a valid config file."""
        config = load_config(config_file=sample_config_yaml)

        assert config.sonnet_threshold == 2
        assert config.max_attempts == 3
        assert config.state_directory == Path("docs/state")
        assert config.validator_model == "haiku"
        assert config.engineer_timeout == 30
        assert config.validator_timeout == 10

    def test_load_config_defaults(self, tmp_path: Path) -> None:
        """Test loading config with missing values uses defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("ralph:\n  max_attempts: 5\n")

        config = load_config(config_file=config_file)

        assert config.max_attempts == 5
        assert config.sonnet_threshold == 2  # Default
        assert config.engineer_timeout == 30  # Default

    def test_load_config_file_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent config file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config(config_file=tmp_path / "nonexistent.yaml")


# ============================================================================
# Test EngineerResult Parsing
# ============================================================================


class TestParseEngineerResult:
    """Tests for parse_engineer_result function."""

    def test_parse_validation_passed(self) -> None:
        """Test parsing VALIDATION_PASSED result."""
        output = """
Some log output here...

VALIDATION_PASSED

Ticket: TASK-001
Branch: feature/TASK-001-implementation
Commit: abc1234
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_PASSED
        assert result.ticket_id == "TASK-001"
        assert result.branch == "feature/TASK-001-implementation"
        assert result.commit == "abc1234"

    def test_parse_validation_failed(self) -> None:
        """Test parsing VALIDATION_FAILED result."""
        output = """
VALIDATION_FAILED

Ticket: TASK-002
Branch: feature/TASK-002-implementation
Commit: def5678
State file: docs/state/TASK-002/attempt-1/engineer-state.md
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_FAILED
        assert result.ticket_id == "TASK-002"
        assert result.state_file is not None

    def test_parse_no_marker(self) -> None:
        """Test parsing output with no validation marker."""
        output = "Some random output with no markers"
        result = parse_engineer_result(output)

        assert result.status == "unknown"
        assert result.ticket_id is None

    def test_parse_timeout(self) -> None:
        """Test parsing timeout result."""
        result = parse_engineer_result("", is_timeout=True)

        assert result.status == "timeout"


# ============================================================================
# Test process_ticket
# ============================================================================


class TestProcessTicket:
    """Tests for process_ticket function."""

    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.pr_flow")
    @patch("commands.orchestrator.ticket_done")
    def test_process_ticket_success_first_attempt(
        self,
        mock_ticket_done: MagicMock,
        mock_pr_flow: MagicMock,
        mock_invoke: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test processing a ticket that succeeds on first attempt."""
        # Setup
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        config = OrchestratorConfig(
            max_attempts=3,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="haiku",
            engineer_timeout=30,
            validator_timeout=10,
        )

        # Mock Claude returning VALIDATION_PASSED
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
            state_file=None,
        )

        # Mock PR flow
        mock_pr_flow.return_value = MagicMock(
            pr_number=42,
            merged=True,
        )

        # Run
        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            dry_run=False,
        )

        # Assert
        assert result.ticket_id == "TASK-001"
        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 42
        mock_invoke.assert_called_once()
        mock_pr_flow.assert_called_once()

    @patch("commands.orchestrator.invoke_claude")
    def test_process_ticket_blocked_after_max_attempts(
        self,
        mock_invoke: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test processing a ticket that fails all attempts."""
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        config = OrchestratorConfig(
            max_attempts=2,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="haiku",
            engineer_timeout=30,
            validator_timeout=10,
        )

        # Mock Claude returning VALIDATION_FAILED
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
            state_file=str(tmp_path / "docs/state/TASK-001/attempt-1/engineer-state.md"),
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            dry_run=False,
        )

        assert result.status == "blocked"
        assert result.attempts == 2
        assert mock_invoke.call_count == 2

    @patch("commands.orchestrator.invoke_claude")
    def test_process_ticket_dry_run(
        self,
        mock_invoke: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test dry run mode doesn't invoke Claude."""
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        config = OrchestratorConfig(
            max_attempts=3,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="haiku",
            engineer_timeout=30,
            validator_timeout=10,
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            dry_run=True,
        )

        assert result.status == "dry_run"
        mock_invoke.assert_not_called()


# ============================================================================
# Test run_orchestrator
# ============================================================================


class TestRunOrchestrator:
    """Tests for run_orchestrator function."""

    @patch("commands.orchestrator.process_ticket")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    def test_run_orchestrator_all_complete(
        self,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        mock_process: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test running orchestrator when all tickets complete."""
        # Setup mock state
        mock_state = WorkflowState(
            version="1.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[
                Ticket(id="TASK-001", title="Task 1", status="pending", dependencies=[]),
            ],
        )
        mock_load_state.return_value = mock_state

        # First call returns ticket, second call returns no more tickets
        mock_get_next.side_effect = [
            MagicMock(ticket=mock_state.tickets[0], has_more=True),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        mock_process.return_value = TicketResult(
            ticket_id="TASK-001",
            status="completed",
            attempts=1,
            pr_number=1,
        )

        # Run
        result = run_orchestrator(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            config_file=sample_config_yaml,
            dry_run=False,
        )

        assert result.completed_count == 1
        assert result.blocked_count == 0
        assert result.status == "complete"

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    def test_run_orchestrator_no_tickets(
        self,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test running orchestrator with no pending tickets."""
        mock_state = WorkflowState(
            version="1.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
        )
        mock_load_state.return_value = mock_state

        mock_get_next.return_value = MagicMock(
            ticket=None,
            has_more=False,
            status="complete",
        )

        result = run_orchestrator(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            config_file=sample_config_yaml,
            dry_run=False,
        )

        assert result.status == "complete"
        assert result.completed_count == 0

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    def test_run_orchestrator_waiting_on_dependencies(
        self,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test orchestrator handling dependency waiting."""
        mock_state = WorkflowState(
            version="1.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[
                Ticket(
                    id="TASK-002",
                    title="Task 2",
                    status="pending",
                    dependencies=["TASK-001"],
                ),
            ],
        )
        mock_load_state.return_value = mock_state

        # Return waiting_on_dependencies status multiple times then complete
        mock_get_next.side_effect = [
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        result = run_orchestrator(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            state_file=tmp_path / "state.json",
            config_file=sample_config_yaml,
            dry_run=False,
            max_wait_retries=3,
        )

        assert result.status == "complete"


# ============================================================================
# Test Model Selection
# ============================================================================


class TestModelSelection:
    """Tests for model selection based on complexity."""

    def test_select_model_below_threshold(self) -> None:
        """Test that tickets below threshold use sonnet."""
        from commands.orchestrator import select_model_for_complexity

        model = select_model_for_complexity(complexity=2, sonnet_threshold=2)
        assert model == "sonnet"

    def test_select_model_above_threshold(self) -> None:
        """Test that tickets above threshold use opus."""
        from commands.orchestrator import select_model_for_complexity

        model = select_model_for_complexity(complexity=3, sonnet_threshold=2)
        assert model == "opus"

    def test_select_model_at_threshold(self) -> None:
        """Test that tickets at threshold use sonnet."""
        from commands.orchestrator import select_model_for_complexity

        model = select_model_for_complexity(complexity=2, sonnet_threshold=2)
        assert model == "sonnet"
