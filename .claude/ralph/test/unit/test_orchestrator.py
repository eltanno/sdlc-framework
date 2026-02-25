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
from unittest.mock import MagicMock, patch

import pytest

from commands.orchestrator import (
    OrchestratorConfig,
    TicketResult,
    load_config,
    run_orchestrator,
    process_ticket,
    parse_engineer_result,
    EngineerResult,
    ValidatorResult,
    VALIDATION_PASSED,
    VALIDATION_FAILED,
    VALIDATION_CONFIRMED,
    VALIDATION_REJECTED,
    DEFAULT_VALIDATOR_MAX_RETRIES,
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
  validator_max_retries: 2

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
        assert config.validator_max_retries == 2

    def test_load_config_defaults(self, tmp_path: Path) -> None:
        """Test loading config with missing values uses defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("ralph:\n  max_attempts: 5\ngit:\n  default_branch: develop-working\n")

        config = load_config(config_file=config_file)

        assert config.max_attempts == 5
        assert config.sonnet_threshold == 2  # Default
        assert config.engineer_timeout == 30  # Default
        assert config.validator_max_retries == DEFAULT_VALIDATOR_MAX_RETRIES  # Default
        assert config.default_branch == "develop-working"

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

    def test_parse_validation_passed_malformed_ticket_id(self) -> None:
        """Test parsing handles missing ticket ID gracefully."""
        output = """
VALIDATION_PASSED

Branch: feature/TASK-001-implementation
Commit: abc1234
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_PASSED
        assert result.ticket_id is None  # Missing ticket ID
        assert result.branch == "feature/TASK-001-implementation"

    def test_parse_validation_passed_missing_all_fields(self) -> None:
        """Test parsing handles output with marker but no metadata."""
        output = "VALIDATION_PASSED"
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_PASSED
        assert result.ticket_id is None
        assert result.branch is None
        assert result.commit is None

    def test_parse_validation_failed(self) -> None:
        """Test parsing VALIDATION_FAILED result extracts ticket and branch."""
        output = """
VALIDATION_FAILED

Ticket: TASK-002
Branch: feature/TASK-002-implementation
Commit: def5678
"""
        result = parse_engineer_result(output)

        assert result.status == VALIDATION_FAILED
        assert result.ticket_id == "TASK-002"
        assert result.branch == "feature/TASK-002-implementation"
        assert result.commit == "def5678"

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

    @patch("commands.orchestrator.stage_summary_files")
    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    @patch("commands.orchestrator.pr_flow")
    @patch("commands.orchestrator.ticket_done")
    def test_process_ticket_success_first_attempt(
        self,
        mock_ticket_done: MagicMock,
        mock_pr_flow: MagicMock,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        mock_stage_summary_files: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test processing a ticket that succeeds on first attempt verifies data flow."""
        from commands.orchestrator import ValidatorResult, VALIDATION_CONFIRMED

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

        mock_get_latest_attempt.return_value = 0  # First attempt

        # Mock Claude returning VALIDATION_PASSED
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        # Mock validator prompt and result (AIUI-0055)
        mock_build_prompt.return_value = "Validator prompt"
        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_CONFIRMED,
            ticket_id="TASK-001",
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

            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Verify result contains correct data
        assert result.ticket_id == "TASK-001"
        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 42

        # Verify Claude was invoked with correct parameters
        mock_invoke.assert_called_once()
        invoke_call = mock_invoke.call_args
        assert invoke_call[1]["timeout_minutes"] == 30
        assert invoke_call[1]["dry_run"] is False

        # Verify validator was invoked (AIUI-0055)
        mock_invoke_validator.assert_called_once()

        # Verify pr_flow was called with correct ticket_id
        mock_pr_flow.assert_called_once()
        pr_call = mock_pr_flow.call_args
        assert pr_call[1]["ticket_id"] == "TASK-001"
        assert pr_call[1]["dry_run"] is False

        # Verify ticket_done was called with correct data
        mock_ticket_done.assert_called_once()
        ticket_done_call = mock_ticket_done.call_args
        assert ticket_done_call[1]["ticket_id"] == "TASK-001"
        assert ticket_done_call[1]["pr_number"] == "42"
        assert ticket_done_call[1]["pm_tool"] is None
        assert ticket_done_call[1]["ralph_label"] == "ralph-test"

        # Verify summary was written BEFORE pr_flow (so pr_number is None)
        mock_write_summary.assert_called_once()
        summary_call = mock_write_summary.call_args
        assert summary_call[1]["ticket_id"] == "TASK-001"
        assert summary_call[1]["status"] == "SUCCESS"
        assert summary_call[1]["total_attempts"] == 1
        assert summary_call[1]["pr_number"] is None  # Written before PR created

        # Verify summary files were staged before pr_flow
        mock_stage_summary_files.assert_called_once_with(
            "TASK-001", tmp_path / "docs/state"
        )

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.mark_blocked")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    def test_process_ticket_blocked_after_max_attempts(
        self,
        mock_invoke: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_mark_blocked: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test processing a ticket that fails all attempts calls mark_blocked with correct data."""
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

        mock_get_latest_attempt.return_value = 0  # First attempt

        # Mock Claude returning VALIDATION_FAILED both times
        mock_invoke.return_value = EngineerResult(
            status=VALIDATION_FAILED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        # Create a mock PM tool to trigger mark_blocked call
        mock_pm_tool = MagicMock()

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",

            dry_run=False,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-test",
        )

        assert result.status == "blocked"
        assert result.attempts == 2
        assert mock_invoke.call_count == 2

        # Verify mark_blocked was called with correct data
        mock_mark_blocked.assert_called_once()
        mark_blocked_call = mock_mark_blocked.call_args
        assert mark_blocked_call[1]["ticket_id"] == "TASK-001"
        assert mark_blocked_call[1]["pm_tool"] == mock_pm_tool
        assert mark_blocked_call[1]["ralph_label"] == "ralph-test"
        reason_lower = mark_blocked_call[1]["reason"].lower()
        assert "exceeded" in reason_lower and "attempts" in reason_lower

        # Verify summary was written with BLOCKED status
        mock_write_summary.assert_called_once()
        summary_call = mock_write_summary.call_args
        assert summary_call[1]["ticket_id"] == "TASK-001"
        assert summary_call[1]["status"] == "BLOCKED"
        assert summary_call[1]["total_attempts"] == 2

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

            dry_run=True,
        )

        assert result.status == "dry_run"
        mock_invoke.assert_not_called()


# ============================================================================
# Test run_orchestrator
# ============================================================================


class TestRunOrchestrator:
    """Tests for run_orchestrator function."""

    @pytest.fixture(autouse=True)
    def set_ralph_label(self):
        """Set RALPH_LABEL for all tests in this class."""
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-test"}):
            yield

    @patch("commands.orchestrator.create_pm_tool")
    @patch("commands.orchestrator.process_ticket")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    def test_run_orchestrator_all_complete(
        self,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        mock_process: MagicMock,
        mock_create_pm: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test running orchestrator when all tickets complete verifies completion logic."""
        # Setup mock state
        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[
                Ticket(id="TASK-001", title="Task 1", status="pending", dependencies=[]),
            ],
        )
        mock_build_state.return_value = mock_state

        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        # First call returns ticket, second call returns no more tickets
        mock_get_next.side_effect = [
            MagicMock(ticket=mock_state.tickets[0], has_more=True, status="ready"),
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
            workflow_state=mock_state,
            config_file=sample_config_yaml,
            dry_run=False,
        )

        # Verify completion logic
        assert result.completed_count == 1
        assert result.blocked_count == 0
        assert result.status == "complete"

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    def test_run_orchestrator_no_tickets(
        self,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test running orchestrator with no pending tickets."""
        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
        )

        mock_build_state.return_value = mock_state

        mock_get_next.return_value = MagicMock(
            ticket=None,
            has_more=False,
            status="complete",
        )

        result = run_orchestrator(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            workflow_state=mock_state,
            config_file=sample_config_yaml,
            dry_run=False,
        )

        assert result.status == "complete"
        assert result.completed_count == 0

    @patch("commands.orchestrator.create_pm_tool")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    def test_run_orchestrator_waiting_on_dependencies(
        self,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        mock_create_pm: MagicMock,
        tmp_path: Path,
        sample_config_yaml: Path,
    ) -> None:
        """Test orchestrator retries when waiting on dependencies then completes."""
        mock_state = WorkflowState(
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
        mock_build_state.return_value = mock_state

        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        # Return waiting_on_dependencies status multiple times then complete
        mock_get_next.side_effect = [
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=True, status="waiting_on_dependencies"),
            MagicMock(ticket=None, has_more=False, status="complete"),
        ]

        result = run_orchestrator(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            workflow_state=mock_state,
            config_file=sample_config_yaml,
            dry_run=False,
            max_wait_retries=3,
        )

        # Verify orchestrator completes without processing tickets
        assert result.status == "complete"
        assert result.completed_count == 0
        assert result.blocked_count == 0

        # Verify get_next_ticket was called 3 times (retries)
        assert mock_get_next.call_count == 3


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
        """Test that GitHub PM tool is created and has correct interface."""
        from commands.orchestrator import create_pm_tool
        from core.pm import GitHubPM

        pm_tool = create_pm_tool(github_config_yaml)

        # Verify tool exists and has required interface (PMTool protocol)
        assert pm_tool is not None
        assert hasattr(pm_tool, 'get_ticket_status')
        assert hasattr(pm_tool, 'claim_ticket')
        assert hasattr(pm_tool, 'close_ticket')
        assert hasattr(pm_tool, 'add_blocked_label')
        assert hasattr(pm_tool, 'remove_label')

        # Verify it's a GitHub PM implementation
        assert isinstance(pm_tool, GitHubPM)

    def test_create_pm_tool_local(self, local_config_yaml: Path) -> None:
        """Test that local PM tool is created and has correct interface."""
        from commands.orchestrator import create_pm_tool
        from core.pm import LocalPM

        pm_tool = create_pm_tool(local_config_yaml)

        # Verify tool exists and has required interface (PMTool protocol)
        assert pm_tool is not None
        assert hasattr(pm_tool, 'get_ticket_status')
        assert hasattr(pm_tool, 'claim_ticket')
        assert hasattr(pm_tool, 'close_ticket')
        assert hasattr(pm_tool, 'add_blocked_label')
        assert hasattr(pm_tool, 'remove_label')

        # Verify it's a LocalPM implementation
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

    @pytest.fixture
    def asana_config_yaml(self, tmp_path: Path) -> Path:
        """Create a config.yaml with pm.tool: asana."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  sonnet_threshold: 2
  max_attempts: 3
  state_directory: "docs/state"

pm:
  tool: asana

dev:
  test_command: "npm test"

git:
  default_branch: main
""")
        return config_file

    @patch.dict(os.environ, {
        "ASANA_ACCESS_TOKEN": "test-token",
        "ASANA_WORKSPACE_ID": "workspace-123",
        "ASANA_PROJECT_ID": "project-456",
    })
    def test_create_pm_tool_asana(self, asana_config_yaml: Path) -> None:
        """Test that Asana PM tool is created and has correct interface.

        SDLC-0059: Orchestrator factory integration.
        FR-10 Acceptance Criteria:
        - Given pm.tool: asana in config.yaml, when create_pm_tool() is called,
          then a PM tool with asana interface is returned.
        """
        from commands.orchestrator import create_pm_tool
        from core.asana_pm import AsanaPM

        pm_tool = create_pm_tool(asana_config_yaml)

        # Verify tool exists and has required interface (PMTool protocol)
        assert pm_tool is not None
        assert hasattr(pm_tool, 'get_ticket_status')
        assert hasattr(pm_tool, 'claim_ticket')
        assert hasattr(pm_tool, 'close_ticket')
        assert hasattr(pm_tool, 'add_blocked_label')
        assert hasattr(pm_tool, 'remove_label')

        # Verify it's an AsanaPM implementation
        assert isinstance(pm_tool, AsanaPM)

    @patch.dict(os.environ, {}, clear=True)
    def test_create_pm_tool_asana_missing_credentials_raises_auth_error(
        self, asana_config_yaml: Path
    ) -> None:
        """Test that AsanaPM raises PMAuthError when credentials are missing.

        SDLC-0059: Orchestrator factory integration.
        FR-10 Acceptance Criteria:
        - Given Asana credentials are missing, when AsanaPM is instantiated,
          then PMAuthError is raised with helpful message listing required env vars.
        """
        from commands.orchestrator import create_pm_tool
        from core.pm import PMAuthError

        # Ensure Asana environment variables are NOT set
        os.environ.pop("ASANA_ACCESS_TOKEN", None)
        os.environ.pop("ASANA_WORKSPACE_ID", None)
        os.environ.pop("ASANA_PROJECT_ID", None)

        with pytest.raises(PMAuthError) as exc_info:
            create_pm_tool(asana_config_yaml)

        error_message = str(exc_info.value)
        assert "ASANA_ACCESS_TOKEN" in error_message
        assert "ASANA_WORKSPACE_ID" in error_message
        assert "ASANA_PROJECT_ID" in error_message

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_passes_pm_tool_to_get_next(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that run_orchestrator passes correct PM tool and ralph_label to get_next_ticket."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
        )
        mock_build_state.return_value = mock_state

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
                workflow_state=mock_state,
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify get_next_ticket was called with correct pm_tool and ralph_label
        mock_get_next.assert_called()
        call_kwargs = mock_get_next.call_args[1]
        assert call_kwargs["pm_tool"] == mock_pm_tool
        assert call_kwargs["ralph_label"] == "ralph-1"

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.mark_blocked")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_passes_pm_tool_to_mark_blocked(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        mock_invoke: MagicMock,
        mock_mark_blocked: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that mark_blocked receives correct ticket_id, PM tool, and reason."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_pm_tool.get_pm_type.return_value = "github"
        mock_create_pm.return_value = mock_pm_tool
        mock_get_latest_attempt.return_value = 0  # First attempt

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[ticket],
        )
        mock_build_state.return_value = mock_state

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
        )

        # Override max attempts to 1 for faster test
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
                workflow_state=mock_state,
                config_file=config_file,
                dry_run=False,
            )

        # Verify mark_blocked was called with complete data
        mock_mark_blocked.assert_called_once()
        call_kwargs = mock_mark_blocked.call_args[1]
        assert call_kwargs["ticket_id"] == "TASK-001"
        assert call_kwargs["pm_tool"] == mock_pm_tool
        assert call_kwargs["ralph_label"] == "ralph-1"
        # Verify reason explains the failure
        reason_lower = call_kwargs["reason"].lower()
        assert "exceeded" in reason_lower and "attempts" in reason_lower

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_handles_pm_error_gracefully(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that PM error stops orchestrator gracefully with error status."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])],
        )
        mock_build_state.return_value = mock_state

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
                workflow_state=mock_state,
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify orchestrator stops gracefully with specific error status
        assert result is not None
        # When PM tool errors, orchestrator should stop (status is "complete" because loop exits)
        # But no tickets should be processed
        assert result.status == "complete"
        assert result.completed_count == 0
        assert result.blocked_count == 0

    @patch("commands.orchestrator.get_next_ticket")
    @patch("commands.orchestrator.build_workflow_state")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_reads_ralph_label_from_env(
        self,
        mock_create_pm: MagicMock,
        mock_build_state: MagicMock,
        mock_get_next: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that RALPH_LABEL environment variable is correctly passed to get_next_ticket."""
        # Setup
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        mock_state = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
        )
        mock_build_state.return_value = mock_state

        mock_get_next.return_value = MagicMock(
            ticket=None,
            has_more=False,
            status="complete",
        )

        # Test with specific RALPH_LABEL value
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-42"}):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                workflow_state=mock_state,
                config_file=github_config_yaml,
                dry_run=False,
            )

        # Verify exact ralph_label value was passed
        call_kwargs = mock_get_next.call_args[1]
        assert call_kwargs["ralph_label"] == "ralph-42"

        # Test with different label to verify it's not hardcoded
        mock_get_next.reset_mock()
        with patch.dict(os.environ, {"RALPH_LABEL": "ralph-99"}):
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                workflow_state=mock_state,
                config_file=github_config_yaml,
                dry_run=False,
            )

        call_kwargs = mock_get_next.call_args[1]
        assert call_kwargs["ralph_label"] == "ralph-99"

    @patch("commands.orchestrator.load_config")
    @patch("commands.orchestrator.create_pm_tool")
    def test_run_orchestrator_raises_error_when_ralph_label_not_set(
        self,
        mock_create_pm: MagicMock,
        mock_load_config: MagicMock,
        tmp_path: Path,
        github_config_yaml: Path,
    ) -> None:
        """Test that RuntimeError is raised when RALPH_LABEL not set."""
        mock_pm_tool = MagicMock()
        mock_create_pm.return_value = mock_pm_tool

        # Return a config with empty instance_label to simulate RALPH_LABEL not set
        mock_load_config.return_value = OrchestratorConfig(
            sonnet_threshold=2,
            max_attempts=3,
            state_directory="docs/state",
            instance_label="",  # Empty - simulates RALPH_LABEL not set
            use_assignee=False,
        )

        mock_ws = WorkflowState(
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            tickets=[],
        )

        with pytest.raises(RuntimeError) as exc_info:
            run_orchestrator(
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                workflow_state=mock_ws,
                config_file=github_config_yaml,
                dry_run=False,
            )

        assert "RALPH_LABEL is required" in str(exc_info.value)

    def test_load_config_reads_use_assignee(self, tmp_path: Path) -> None:
        """Test that use_assignee setting is correctly loaded from config."""
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

        # Verify use_assignee is loaded correctly
        assert hasattr(config, 'use_assignee')
        assert config.use_assignee is True

        # Test with use_assignee: false
        config_file.write_text("""
ralph:
  max_attempts: 3
  use_assignee: false
pm:
  tool: github
dev:
  test_command: "npm test"
git:
  default_branch: main
""")

        config = load_config(config_file)
        assert config.use_assignee is False


# ============================================================================
# Test Validator Integration in process_ticket (AIUI-0055)
# ============================================================================


class TestValidatorIntegration:
    """Tests for validator integration into process_ticket.

    AIUI-0055: Integrate validator into orchestrator.

    These tests verify that:
    1. When engineer returns VALIDATION_PASSED, validator is invoked
    2. When validator returns VALIDATION_CONFIRMED, pr_flow is called
    3. When validator returns VALIDATION_REJECTED, pr_flow is NOT called
    4. When validator returns VALIDATION_REJECTED, ticket is marked as failed
    5. Validator uses the configured validator_model

    FR-1: Invoke Validation Agent After Engineer Completes
    """

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    @patch("commands.orchestrator.pr_flow")
    def test_pr_flow_not_called_when_validator_rejects(
        self,
        mock_pr_flow: MagicMock,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator returns VALIDATION_REJECTED, when processing ticket, then pr_flow is NOT called.

        FR-1: Given the validator returns VALIDATION_REJECTED, when the orchestrator
        processes this, then it does NOT proceed to pr_flow().
        """
        from commands.orchestrator import (
            ValidatorResult,
            VALIDATION_REJECTED,
        )

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        config = OrchestratorConfig(
            max_attempts=1,  # Only one attempt to verify rejection behavior
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer returns VALIDATION_PASSED
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator returns VALIDATION_REJECTED
        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_REJECTED,
            ticket_id="TASK-001",
            reason="Acceptance criteria AC-3 not met",
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",

            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Verify pr_flow was NOT called
        mock_pr_flow.assert_not_called()

        # Ticket should be blocked after max attempts
        assert result.status == "blocked"

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.mark_blocked")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_ticket_marked_failed_when_validator_rejects(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_mark_blocked: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator returns VALIDATION_REJECTED, when max attempts exceeded, then ticket is marked failed.

        FR-1: Given the validator returns VALIDATION_REJECTED, when the orchestrator
        processes this, then the ticket is marked as failed with validator findings.
        """
        from commands.orchestrator import (
            ValidatorResult,
            VALIDATION_REJECTED,
        )

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        config = OrchestratorConfig(
            max_attempts=1,  # Only one attempt
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer returns VALIDATION_PASSED
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator returns VALIDATION_REJECTED
        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_REJECTED,
            ticket_id="TASK-001",
            reason="Bypass language detected",
        )

        # Create mock PM tool to trigger mark_blocked call
        mock_pm_tool = MagicMock()

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",

            dry_run=False,
            pm_tool=mock_pm_tool,
            ralph_label="ralph-test",
        )

        # Verify ticket is blocked
        assert result.status == "blocked"

        # Verify mark_blocked was called
        mock_mark_blocked.assert_called_once()

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_validator_rejection_triggers_retry(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator rejects on first attempt, when max_attempts > 1, then retry is triggered.

        This tests the retry loop behavior when validator rejects.
        """
        from commands.orchestrator import (
            ValidatorResult,
            VALIDATION_REJECTED,
        )

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        config = OrchestratorConfig(
            max_attempts=2,  # Allow retry
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer always returns VALIDATION_PASSED
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator rejects both times
        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_REJECTED,
            ticket_id="TASK-001",
            reason="Criteria not met",
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",

            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # With validator_max_retries=2 (default), validator is retried 2 extra times
        # before falling back to a full engineer re-run.
        # Attempt 1: engineer(1) -> validator rejects -> validator retry 1 -> validator retry 2
        # All validator retries exhausted -> engineer attempt 2
        # Attempt 2: engineer(2) -> validator rejects -> validator retry 1 -> validator retry 2
        # All validator retries exhausted -> max_attempts exceeded -> blocked
        assert mock_invoke_claude.call_count == 2
        # Each engineer attempt triggers 1 initial + 2 retries = 3 validator calls, x2 attempts = 6
        assert mock_invoke_validator.call_count == 6

        # Ticket should be blocked after exhausting attempts
        assert result.status == "blocked"
        assert result.attempts == 2


class TestValidatorRetry:
    """Tests for validator-only retry logic (SLCA-0083).

    When the validator fails (timeout, rejection, unknown), the orchestrator
    should retry JUST the validator before falling back to a full engineer re-run.
    This saves tokens when the engineer's work was correct but the validator had issues.
    """

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_validator_timeout_retries_validator_not_engineer(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator times out, when retrying, then only the validator is retried (not engineer).

        SLCA-0083: Validator timeout should trigger validator-only retry, not a full engineer re-run.
        With max_attempts=1 and validator_max_retries=2, the engineer should run exactly once,
        while the validator should run 3 times (1 initial + 2 retries).
        """
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        config = OrchestratorConfig(
            max_attempts=1,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
            validator_max_retries=2,
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer returns VALIDATION_PASSED (once)
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator always times out
        mock_invoke_validator.return_value = ValidatorResult(
            status="timeout",
            raw_output="Validator invocation timed out",
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Engineer should only be called ONCE - validator retries don't re-run engineer
        assert mock_invoke_claude.call_count == 1

        # Validator should be called 3 times: 1 initial + 2 retries
        assert mock_invoke_validator.call_count == 3

        # With max_attempts=1, after exhausting validator retries, ticket is blocked
        assert result.status == "blocked"

    @patch("commands.orchestrator.stage_summary_files")
    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    @patch("commands.orchestrator.pr_flow")
    @patch("commands.orchestrator.ticket_done")
    def test_validator_passes_on_retry_completes_with_one_attempt(
        self,
        mock_ticket_done: MagicMock,
        mock_pr_flow: MagicMock,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        mock_stage_summary_files: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator fails then passes on retry, when processing, then ticket completes with attempts=1.

        SLCA-0083: If the validator initially rejects but succeeds on retry,
        the ticket should complete with attempts=1 since the engineer only ran once.
        """
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
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
            validator_max_retries=2,
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer returns VALIDATION_PASSED
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator: first call rejects, second call confirms
        mock_invoke_validator.side_effect = [
            ValidatorResult(
                status=VALIDATION_REJECTED,
                ticket_id="TASK-001",
                reason="Flaky check",
            ),
            ValidatorResult(
                status=VALIDATION_CONFIRMED,
                ticket_id="TASK-001",
            ),
        ]

        mock_pr_flow.return_value = MagicMock(pr_number=42, merged=True)

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Engineer only called once
        assert mock_invoke_claude.call_count == 1

        # Validator called twice (initial rejection + retry that confirms)
        assert mock_invoke_validator.call_count == 2

        # Ticket completes with attempts=1 (engineer only ran once)
        assert result.status == "completed"
        assert result.attempts == 1
        assert result.pr_number == 42

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_validator_exhausts_retries_falls_back_to_engineer(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator exhausts all retries, when processing, then falls back to full engineer re-run.

        SLCA-0083: When all validator retries are exhausted, the orchestrator should
        increment the engineer attempt counter and do a full engineer re-run.
        With max_attempts=2 and validator_max_retries=1:
        - Attempt 1: engineer -> validator rejects -> 1 validator retry (rejects) -> exhausted
        - Attempt 2: engineer -> validator rejects -> 1 validator retry (rejects) -> exhausted
        - max_attempts exceeded -> blocked
        """
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
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
            validator_max_retries=1,  # Only 1 validator retry
        )

        mock_get_latest_attempt.return_value = 0

        # Engineer always returns VALIDATION_PASSED
        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator always rejects
        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_REJECTED,
            ticket_id="TASK-001",
            reason="Criteria not met",
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Engineer called twice (once per attempt)
        assert mock_invoke_claude.call_count == 2

        # Validator called 4 times: 2 attempts x (1 initial + 1 retry) = 4
        assert mock_invoke_validator.call_count == 4

        # Ticket blocked after exhausting all attempts
        assert result.status == "blocked"
        assert result.attempts == 2

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_validator_unknown_status_triggers_validator_retry(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Given validator returns unknown status, when retrying, then only validator is retried.

        SLCA-0083: Unknown validator status should trigger validator-only retry,
        same as timeout and rejection.
        """
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        config = OrchestratorConfig(
            max_attempts=1,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
            validator_max_retries=2,
        )

        mock_get_latest_attempt.return_value = 0

        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        # Validator returns unknown status every time
        mock_invoke_validator.return_value = ValidatorResult(
            status="unknown",
            raw_output="Garbled output",
        )

        result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=tmp_path / "prd.md",
            plan_path=tmp_path / "plan.md",
            dry_run=False,
            pm_tool=None,
            ralph_label="ralph-test",
        )

        # Engineer only called once
        assert mock_invoke_claude.call_count == 1

        # Validator called 3 times: 1 initial + 2 retries
        assert mock_invoke_validator.call_count == 3

        assert result.status == "blocked"

    @patch("commands.orchestrator.write_summary")
    @patch("commands.orchestrator.ensure_state_dir")
    @patch("commands.orchestrator.get_latest_attempt")
    @patch("commands.orchestrator.invoke_claude")
    @patch("commands.orchestrator.invoke_validator")
    @patch("commands.orchestrator.build_validator_prompt")
    def test_validator_retry_logs_correctly(
        self,
        mock_build_prompt: MagicMock,
        mock_invoke_validator: MagicMock,
        mock_invoke_claude: MagicMock,
        mock_get_latest_attempt: MagicMock,
        mock_ensure_state_dir: MagicMock,
        mock_write_summary: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Given validator retry occurs, when logging, then log includes retry count.

        SLCA-0083: Log messages should clearly indicate validator retry number.
        """
        import logging

        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )

        config = OrchestratorConfig(
            max_attempts=1,
            sonnet_threshold=2,
            state_directory=tmp_path / "docs/state",
            validator_model="sonnet",
            engineer_timeout=30,
            validator_timeout=10,
            validator_max_retries=2,
        )

        mock_get_latest_attempt.return_value = 0

        mock_invoke_claude.return_value = EngineerResult(
            status=VALIDATION_PASSED,
            ticket_id="TASK-001",
            branch="feature/TASK-001-implementation",
            commit="abc1234",
        )

        mock_build_prompt.return_value = "Validator prompt"

        mock_invoke_validator.return_value = ValidatorResult(
            status=VALIDATION_REJECTED,
            ticket_id="TASK-001",
            reason="Criteria not met",
        )

        with caplog.at_level(logging.INFO, logger="commands.orchestrator"):
            process_ticket(
                ticket=ticket,
                config=config,
                prd_path=tmp_path / "prd.md",
                plan_path=tmp_path / "plan.md",
                    dry_run=False,
                pm_tool=None,
                ralph_label="ralph-test",
            )

        # Check that validator retry log messages appear
        retry_logs = [r for r in caplog.records if "Validator retry" in r.message]
        assert len(retry_logs) == 2  # 2 retries
        assert "1/2" in retry_logs[0].message
        assert "2/2" in retry_logs[1].message
        assert "TASK-001" in retry_logs[0].message
