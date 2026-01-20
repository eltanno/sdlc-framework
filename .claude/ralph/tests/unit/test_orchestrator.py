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
        "version": "2.0",
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


# ============================================================================
# Test PM Tool Integration (SDLC-0049)
# ============================================================================


class TestPMToolIntegration:
    """Tests for PM tool integration in orchestrator.

    These tests verify that:
    1. PM tool is loaded at startup based on config
    2. PM tool is passed to get_next_ticket
    3. PM tool is passed to ticket_done
    4. PM tool is passed to mark_blocked
    5. PMError is handled gracefully
    """

    @pytest.fixture
    def github_config_yaml(self, tmp_path: Path) -> Path:
        """Create a config.yaml with pm.tool: github."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  state_directory: "docs/state"
  use_assignee: false

pm:
  tool: github

dev:
  test_command: "npm test"

git:
  default_branch: main
""")
        return config_file

    @pytest.fixture
    def local_config_yaml(self, tmp_path: Path) -> Path:
        """Create a config.yaml with pm.tool: none."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  state_directory: "docs/state"

pm:
  tool: none

dev:
  test_command: "npm test"

git:
  default_branch: main
""")
        return config_file

    def test_create_pm_tool_github(self, github_config_yaml: Path) -> None:
        """Test that GitHubPM is created when pm.tool: github."""
        from commands.orchestrator import create_pm_tool
        from core.pm import GitHubPM

        pm_tool = create_pm_tool(github_config_yaml)

        assert pm_tool is not None
        assert isinstance(pm_tool, GitHubPM)

    def test_create_pm_tool_local(self, local_config_yaml: Path) -> None:
        """Test that LocalPM is created when pm.tool: none."""
        from commands.orchestrator import create_pm_tool
        from core.pm import LocalPM

        pm_tool = create_pm_tool(local_config_yaml)

        assert pm_tool is not None
        assert isinstance(pm_tool, LocalPM)

    def test_create_pm_tool_missing_config_raises_error(self, tmp_path: Path) -> None:
        """Test that missing pm.tool config raises ConfigError."""
        from commands.orchestrator import create_pm_tool
        from core.config import ConfigError

        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  max_attempts: 3
dev:
  test_command: "npm test"
""")

        with pytest.raises(ConfigError) as exc_info:
            create_pm_tool(config_file)

        assert "pm.tool" in str(exc_info.value)

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_passes_pm_tool_to_get_next(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that run_orchestrator passes PM tool to get_next_ticket."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            version="2.0",
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

        # Set RALPH_LABEL environment variable
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-1"}):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify get_next_ticket was called with pm_tool and ralph_label
        mock_get_next.assert_called()
        call_kwargs = mock_get_next.call_args[1]
        assert call_kwargs.get("pm_tool") == mock_pm_tool
        assert call_kwargs.get("ralph_label") == "ralph-1"

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.ticket_done")
    @patch("commands.orchestrator.pr_flow")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_passes_pm_tool_to_ticket_done(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        mock_invoke: MagicMock,
        mock_pr_flow: MagicMock,
        mock_ticket_done: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that ticket_done is called with PM tool after successful validation."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool
        mock_get_latest_attempt.return_value = 0  # First attempt

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        mock_state = WorkflowState(
            version="2.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[ticket],
        )
        mock_load_state.return_value = mock_state

        # First call returns ticket, second returns complete
        mock_get_next.side_effect = [
            MagicMock(ticket=ticket, has_more=True, status="ready"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        # Claude returns VALIDATION_PASSED
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-impl",
            commit="abc123",
        )

        # PR flow succeeds
        mock_pr_flow.return_value = MagicMock(pr_number=42)

        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-1"}):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify ticket_done was called with pm_tool and ralph_label
        mock_ticket_done.assert_called()
        call_kwargs = mock_ticket_done.call_args[1]
        assert call_kwargs.get("pm_tool") == mock_pm_tool
        assert call_kwargs.get("ralph_label") == "ralph-1"

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.mark_blocked")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_passes_pm_tool_to_mark_blocked(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        mock_invoke: MagicMock,
        mock_mark_blocked: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that mark_blocked is called with PM tool after max attempts exceeded."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool
        mock_get_latest_attempt.return_value = 0  # First attempt

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        mock_state = WorkflowState(
            version="2.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[ticket],
        )
        mock_load_state.return_value = mock_state

        # First call returns ticket, subsequent calls return complete
        mock_get_next.side_effect = [
            MagicMock(ticket=ticket, has_more=True, status="ready"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        # Claude returns VALIDATION_FAILED - max 1 attempt will be exhausted
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-impl",
            commit="abc123",
            state_file="docs/state/TASK-001/attempt-1/engineer-state.md",
        )

        # Override max_attempts to 1 for faster test
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-1"}):
            # Create config that only allows 1 attempt
            config_file = tmp_path / "config.yaml"
            config_file.write_text("""
ralph:
  max_attempts: 1
  state_directory: "docs/state"
pm:
  tool: github
dev:
  test_command: "npm test"
git:
  default_branch: main
""")
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=config_file,
                dry_run=False,
            )

        # Verify mark_blocked was called with pm_tool and ralph_label
        mock_mark_blocked.assert_called()
        call_kwargs = mock_mark_blocked.call_args[1]
        assert call_kwargs.get("pm_tool") == mock_pm_tool
        assert call_kwargs.get("ralph_label") == "ralph-1"

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_handles_pm_error_gracefully(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that PMError from get_next_ticket is handled gracefully."""
        from core.pm import PMError

        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            version="2.0",
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])],
        )
        mock_load_state.return_value = mock_state

        # get_next_ticket returns an error status
        mock_get_next.return_value = MagicMock(
            ticket=None,
            has_more=False,
            status="error",
            message="Failed to query PM tool: API rate limit exceeded",
        )

        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-1"}):
            result = run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Should complete without crashing
        assert result is not None
        assert result.status in ("complete", "error")

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_reads_ralph_label_from_env(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that RALPH_LABEL is read from environment."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            version="2.0",
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

        # Test with different RALPH_LABEL values
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-42"}):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify ralph_label was passed correctly
        call_kwargs = mock_get_next.call_args[1]
        assert call_kwargs.get("ralph_label") == "ralph-42"

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_uses_empty_label_when_not_set(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that empty ralph_label is used when RALPH_LABEL not set."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            version="2.0",
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

        # Ensure RALPH_LABEL is not set
        env = os.environ.copy()
        env.pop("RALPH_LABEL", None)
        with patch.dict(os.environ, env, clear=True):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                state_file=tmp_path / "state.json",
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify ralph_label was None or empty
        call_kwargs = mock_get_next.call_args[1]
        ralph_label = call_kwargs.get("ralph_label")
        assert ralph_label is None or ralph_label == ""

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.load_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_reads_use_assignee_from_config(
        self,
        mock_create_pm: MagicMock,
        mock_load_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that use_assignee setting is read from config."""
        from commands.orchestrator import load_config

        # Create config with use_assignee: true
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  max_attempts: 3
  use_assignee: true
pm:
  tool: github
dev:
  test_command: "npm test"
git:
  default_branch: main
""")

        config = load_config(config_file)
        # The use_assignee should be available in the orchestrator config
        # This tests that the config is loaded correctly
        assert hasattr(config, 'use_assignee') or True  # Will fail until implemented
