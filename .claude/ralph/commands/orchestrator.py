"""Main orchestrator loop for Ralph workflow.

This module implements the core Ralph loop that:
- Gets the next eligible ticket
- Invokes Claude to implement the ticket
- Handles success/failure outcomes
- Progresses through all tickets until completion

This is a port of .claude/scripts/ralph-prd.sh to Python.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

from commands.get_next import get_next_ticket
from commands.mark_blocked import mark_blocked
from commands.pr_flow import pr_flow, PrFlowError, MergeError
from commands.ticket_done import ticket_done
from core.claude_cli import parse_stream_json_result
from core.config import get_pm_tool_type, get_ticket_prefix, ConfigError
from core.pm import PMTool, GitHubPM, LocalPM
from core.asana_pm import AsanaPM
from core.git import stage_files
from core.state import (
    Ticket,
    WorkflowState,
    build_workflow_state,
    ensure_state_dir,
    get_latest_attempt,
    write_summary,
)


# ============================================================================
# Constants
# ============================================================================

VALIDATION_PASSED = "validation_passed"
VALIDATION_FAILED = "validation_failed"
ALREADY_IMPLEMENTED = "already_implemented"

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_SONNET_THRESHOLD = 2
DEFAULT_ENGINEER_TIMEOUT = 30
DEFAULT_VALIDATOR_TIMEOUT = 10
DEFAULT_VALIDATOR_MAX_RETRIES = 2
DEFAULT_WAIT_INTERVAL = 30  # seconds
DEFAULT_MAX_WAIT_RETRIES = 60  # 60 * 30s = 30 minutes


# ============================================================================
# Helper Functions
# ============================================================================


def stage_summary_files(ticket_id: str, state_directory: str | Path) -> None:
    """Stage summary files so they get included in the next commit.

    This is called before pr_flow so the summary files are included
    in the PR's commit rather than being left uncommitted.

    Args:
        ticket_id: The ticket ID (e.g., "AIUI-0024")
        state_directory: Directory containing state files (e.g., "docs/state")
    """
    try:
        summary_dir = Path(state_directory) / ticket_id
        summary_json = summary_dir / "summary.json"
        summary_md = summary_dir / "summary.md"

        files_to_stage = []
        if summary_json.exists():
            files_to_stage.append(str(summary_json))
        if summary_md.exists():
            files_to_stage.append(str(summary_md))

        if not files_to_stage:
            logger.debug(f"No summary files to stage for {ticket_id}")
            return

        stage_files(files_to_stage)
        logger.debug(f"Staged summary files for {ticket_id}: {files_to_stage}")
    except Exception as e:
        # Don't fail the ticket over staging issues
        logger.warning(f"Failed to stage summary files for {ticket_id}: {e}")


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator.

    Attributes:
        max_attempts: Maximum retry attempts per ticket before marking blocked
        sonnet_threshold: Complexity threshold for model selection (1-threshold use sonnet)
        state_directory: Directory for engineer state files
        validator_model: Model to use for validation analysis (default: "sonnet")
        engineer_timeout: Timeout in minutes for engineer invocation
        validator_timeout: Timeout in minutes for validator invocation
        validator_max_retries: Max validator-only retries before falling back to engineer re-run
        instance_label: Label for this ralph instance (from RALPH_LABEL env)
        use_assignee: Whether to also assign issues to current user when claiming
        test_command: Command to run tests
        lint_command: Command to run linter
        typecheck_command: Command to run type checker
        build_command: Command to run build
        default_branch: Default git branch (from config.yaml git.default_branch)
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    sonnet_threshold: int = DEFAULT_SONNET_THRESHOLD
    state_directory: Path = field(default_factory=lambda: Path("docs/state"))
    validator_model: str = "sonnet"
    engineer_timeout: int = DEFAULT_ENGINEER_TIMEOUT
    validator_timeout: int = DEFAULT_VALIDATOR_TIMEOUT
    validator_max_retries: int = DEFAULT_VALIDATOR_MAX_RETRIES
    instance_label: str = ""
    use_assignee: bool = False
    test_command: str = ""
    lint_command: str = ""
    typecheck_command: str = ""
    build_command: str = ""
    default_branch: str = ""


@dataclass
class EngineerResult:
    """Result from parsing Claude engineer output.

    Attributes:
        status: Result status (validation_passed, validation_failed, timeout, unknown)
        ticket_id: Ticket ID from output
        branch: Branch name from output
        commit: Commit SHA from output
        raw_output: Raw output from Claude
    """

    status: str
    ticket_id: str | None = None
    branch: str | None = None
    commit: str | None = None
    raw_output: str = ""


@dataclass
class TicketResult:
    """Result of processing a single ticket.

    Attributes:
        ticket_id: The ticket identifier
        status: Final status (completed, blocked, dry_run)
        attempts: Number of attempts made
        pr_number: PR number if created
        block_reason: Reason if blocked
        duration_seconds: Time taken to process this ticket
    """

    ticket_id: str
    status: str
    attempts: int = 0
    pr_number: int | None = None
    block_reason: str | None = None
    duration_seconds: float = 0.0


@dataclass
class OrchestratorResult:
    """Result of running the orchestrator.

    Attributes:
        status: Final status (complete, incomplete, error)
        completed_count: Number of tickets completed
        blocked_count: Number of tickets blocked
        ticket_results: Results for each processed ticket
        start_time: When orchestration started
        end_time: When orchestration ended
    """

    status: str
    completed_count: int = 0
    blocked_count: int = 0
    ticket_results: list[TicketResult] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class ValidatorResult:
    """Result from parsing validator agent output.

    AIUI-0052: Implements result structure for the validation agent.

    Attributes:
        status: Result status (validation_confirmed, validation_rejected, timeout, dry_run, unknown)
        ticket_id: Ticket ID from output
        reason: Rejection reason if validation_rejected
        raw_output: Raw output from Claude validator
    """

    status: str
    ticket_id: str | None = None
    reason: str | None = None
    raw_output: str = ""


# ============================================================================
# Configuration Loading
# ============================================================================


def load_config(
    config_file: Path | None = None,
    env_file: Path | None = None,
) -> OrchestratorConfig:
    """Load orchestrator configuration from YAML and environment.

    Args:
        config_file: Path to config.yaml (default: config.yaml in cwd)
        env_file: Path to .env file (default: .env in cwd)

    Returns:
        OrchestratorConfig with loaded values

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if config_file is None:
        config_file = Path("config.yaml")

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    # Load YAML config
    with open(config_file) as f:
        config_data = yaml.safe_load(f) or {}

    ralph_config = config_data.get("ralph", {})
    dev_config = config_data.get("dev", {})
    git_config = config_data.get("git", {})

    # Load environment variables
    instance_label = os.environ.get("RALPH_LABEL", "")

    # Load from .env if exists
    if env_file is None:
        env_file = Path(".env")

    if env_file.exists() and not instance_label:
        for line in env_file.read_text().splitlines():
            if line.startswith("RALPH_LABEL="):
                instance_label = line.split("=", 1)[1].strip().strip("'\"")
                break

    default_branch = git_config.get("default_branch", "")
    if not default_branch:
        raise ConfigError(
            "git.default_branch is not set in config.yaml. "
            "This is required — add e.g.: git:\n  default_branch: develop-working",
            file_path=config_file,
        )

    return OrchestratorConfig(
        max_attempts=ralph_config.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
        sonnet_threshold=ralph_config.get("sonnet_threshold", DEFAULT_SONNET_THRESHOLD),
        state_directory=Path(ralph_config.get("state_directory", "docs/state")),
        validator_model=ralph_config.get("validator_model", "sonnet"),
        engineer_timeout=ralph_config.get("engineer_timeout", DEFAULT_ENGINEER_TIMEOUT),
        validator_timeout=ralph_config.get("validator_timeout", DEFAULT_VALIDATOR_TIMEOUT),
        validator_max_retries=ralph_config.get("validator_max_retries", DEFAULT_VALIDATOR_MAX_RETRIES),
        instance_label=instance_label,
        use_assignee=ralph_config.get("use_assignee", False),
        test_command=dev_config.get("test_command", ""),
        lint_command=dev_config.get("lint_command", ""),
        typecheck_command=dev_config.get("typecheck_command", ""),
        build_command=dev_config.get("build_command", ""),
        default_branch=default_branch,
    )


# ============================================================================
# PM Tool Factory
# ============================================================================


def create_pm_tool(config_file: Path | None = None) -> PMTool:
    """Create a PM tool instance based on configuration.

    Reads the pm.tool setting from config.yaml and creates the appropriate
    PM tool implementation.

    Args:
        config_file: Path to config.yaml (default: config.yaml in cwd)

    Returns:
        PMTool instance (GitHubPM, LocalPM, etc.)

    Raises:
        ConfigError: If pm.tool is not configured or has an invalid value
    """
    if config_file is None:
        config_file = Path("config.yaml")

    # Get PM tool type from config
    pm_tool_type = get_pm_tool_type(config_file)
    logger.info(f"Creating PM tool: {pm_tool_type}")

    # Create appropriate PM tool instance
    if pm_tool_type == "github":
        ticket_prefix = get_ticket_prefix(config_file)
        logger.debug(f"Initializing GitHubPM (ticket_prefix={ticket_prefix})")
        return GitHubPM(ticket_prefix=ticket_prefix)
    elif pm_tool_type == "asana":
        logger.debug("Initializing AsanaPM")
        return AsanaPM()
    elif pm_tool_type == "none":
        logger.debug("Initializing LocalPM (degraded mode)")
        return LocalPM()
    else:
        # For future PM tools (trello), raise ConfigError
        # until they're implemented
        raise ConfigError(
            f"PM tool '{pm_tool_type}' is not yet implemented. "
            f"Supported tools: github, asana, none",
            file_path=config_file
        )


# ============================================================================
# Model Selection
# ============================================================================


def select_model_for_complexity(complexity: int, sonnet_threshold: int) -> str:
    """Select model based on ticket complexity.

    Args:
        complexity: Ticket complexity (1-5)
        sonnet_threshold: Threshold for using sonnet (complexity <= threshold uses sonnet)

    Returns:
        Model name ("sonnet" or "opus")
    """
    if complexity <= sonnet_threshold:
        return "sonnet"
    return "opus"


# ============================================================================
# Engineer Result Parsing
# ============================================================================


def parse_engineer_result(output: str, is_timeout: bool = False) -> EngineerResult:
    """Parse Claude engineer output to extract result.

    Args:
        output: Raw output from Claude engineer
        is_timeout: Whether the invocation timed out

    Returns:
        EngineerResult with parsed fields
    """
    if is_timeout:
        return EngineerResult(status="timeout", raw_output=output)

    # Check for validation markers
    # Note: Check ALREADY_IMPLEMENTED first since it may also contain VALIDATION_PASSED
    if "ALREADY_IMPLEMENTED" in output:
        status = ALREADY_IMPLEMENTED
    elif "VALIDATION_PASSED" in output:
        status = VALIDATION_PASSED
    elif "VALIDATION_FAILED" in output:
        status = VALIDATION_FAILED
    else:
        return EngineerResult(status="unknown", raw_output=output)

    # Parse ticket ID
    ticket_match = re.search(r"Ticket:\s*(\S+)", output)
    ticket_id = ticket_match.group(1) if ticket_match else None

    # Parse branch
    branch_match = re.search(r"Branch:\s*(\S+)", output)
    branch = branch_match.group(1) if branch_match else None

    # Parse commit
    commit_match = re.search(r"Commit:\s*(\S+)", output)
    commit = commit_match.group(1) if commit_match else None

    return EngineerResult(
        status=status,
        ticket_id=ticket_id,
        branch=branch,
        commit=commit,
        raw_output=output,
    )


# ============================================================================
# Validator Result Constants
# ============================================================================

VALIDATION_CONFIRMED = "validation_confirmed"
VALIDATION_REJECTED = "validation_rejected"


# ============================================================================
# Validator Result Parsing
# ============================================================================


def parse_validator_result(output: str, is_timeout: bool = False) -> ValidatorResult:
    """Parse validator agent output to extract result.

    AIUI-0052: Implements parsing for validation agent responses.

    Args:
        output: Raw output from Claude validator agent
        is_timeout: Whether the invocation timed out

    Returns:
        ValidatorResult with parsed fields
    """
    if is_timeout:
        return ValidatorResult(status="timeout", raw_output=output)

    # Check for validation markers
    if "VALIDATION_CONFIRMED" in output:
        status = VALIDATION_CONFIRMED
    elif "VALIDATION_REJECTED" in output:
        status = VALIDATION_REJECTED
    else:
        return ValidatorResult(status="unknown", raw_output=output)

    # Parse ticket ID
    ticket_match = re.search(r"Ticket:\s*(\S+)", output)
    ticket_id = ticket_match.group(1) if ticket_match else None

    # Parse reason (for rejected results)
    reason = None
    if status == VALIDATION_REJECTED:
        reason_match = re.search(r"Reason:\s*(.+?)(?:\n|$)", output, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()

    return ValidatorResult(
        status=status,
        ticket_id=ticket_id,
        reason=reason,
        raw_output=output,
    )


# ============================================================================
# Validator Invocation
# ============================================================================


def invoke_validator(
    prompt: str,
    timeout_minutes: int = 10,
    model: str = "sonnet",
    dry_run: bool = False,
) -> ValidatorResult:
    """Invoke Claude CLI for validation work.

    AIUI-0052: Implements the validation agent invocation.

    Calls the Claude CLI with the validator_model from config and handles
    timeout appropriately. The validator agent verifies engineer work
    against original PRD/plan acceptance criteria.

    Args:
        prompt: The validation prompt to send to Claude
        timeout_minutes: Timeout in minutes (default: 10)
        model: Model to use for validation (default: sonnet)
        dry_run: If True, don't actually invoke Claude

    Returns:
        ValidatorResult with parsed output containing:
        - status: validation_confirmed, validation_rejected, timeout, dry_run, or unknown
        - ticket_id: The ticket being validated
        - reason: Rejection reason if validation_rejected
        - raw_output: Full output from Claude

    Raises:
        RuntimeError: If Claude CLI is not found in PATH
    """
    if dry_run:
        return ValidatorResult(
            status="dry_run",
            raw_output="[DRY RUN] Would invoke Claude validator",
        )

    # Build command - uses same structure as invoke_claude but without
    # the engineer agent (validators use default agent with tools for reading)
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--allowedTools",
        "Bash,Read,Glob,Grep,Write",
        "--output-format",
        "stream-json",
        "--verbose",
    ]

    # Build clean environment (remove CLAUDECODE to allow nested invocation)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
            env=env,
        )

        output = result.stdout + result.stderr
        result_text = parse_stream_json_result(output)
        return parse_validator_result(result_text)

    except subprocess.TimeoutExpired:
        return ValidatorResult(
            status="timeout",
            raw_output="Validator invocation timed out",
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Claude CLI not found. Please ensure it is installed and in PATH."
        )


# ============================================================================
# System Manifest Update
# ============================================================================


def update_system_manifest(
    prd_path: Path,
    plan_path: Path,
    result: OrchestratorResult,
    config: OrchestratorConfig,
) -> None:
    """Update docs/SYSTEM.md after tickets have been completed.

    Creates a branch from origin/{default_branch}, invokes Claude (haiku)
    to review and edit the system manifest, then uses pr_flow to push,
    create a PR, and merge. Finally returns to detached HEAD.

    This is a best-effort operation -- failures are logged but do not
    affect the orchestrator result.

    Args:
        prd_path: Path to PRD document that was implemented
        plan_path: Path to plan document for the implementation
        result: Orchestrator result containing completed ticket info
        config: Orchestrator configuration (provides default_branch)
    """
    from commands.pr_flow import pr_flow as run_pr_flow, checkout_detached_default, PrFlowError
    from core import git

    # Extract completed ticket IDs from results
    completed_ids = [
        tr.ticket_id
        for tr in result.ticket_results
        if tr.status == "completed"
    ]

    if not completed_ids:
        logger.debug("No completed tickets to update SYSTEM.md for")
        return

    completed_ticket_ids = ", ".join(completed_ids)
    completed_ids_str = ", ".join(completed_ids[:3])  # Brief summary

    # Create a branch for the SYSTEM.md update
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"docs/system-manifest-update-{timestamp}"

    prompt = f"""You are updating the project's living system manifest after a batch of tickets were implemented.

## Task
1. Read `docs/SYSTEM.md` -- this is the current system manifest
2. Read the PRD at `{prd_path}` -- this describes what was planned
3. Read the plan at `{plan_path}` -- this describes the technical approach
4. Review the completed tickets: {completed_ticket_ids}
5. Determine if any of these sections in SYSTEM.md need updating:
   - Architecture Overview (new services, components)
   - Data Model (new tables, columns, relationships)
   - Frontend Architecture (new stores, pipeline changes)
   - Backend Architecture (new REST routes, new WS message types)
   - Key Architectural Decisions (new decisions made)
   - Conventions & Patterns (new patterns established)
   - Active Constraints & Known Issues (new fragile areas)
   - What NOT to Do (new anti-patterns discovered)
   - Document Index (new documents created)
6. If changes are needed, edit SYSTEM.md using the Edit tool
7. If changes were made, update the "Last updated" date comment at the top
8. Do NOT commit -- the orchestrator will handle committing and merging

## Rules
- ONLY update if there are meaningful system-level changes (new message types, new tables, new stores, etc.)
- Do NOT update for bug fixes, CSS changes, or minor tweaks
- Keep the document concise -- same style as existing content
- Do NOT add content that duplicates existing entries
- If nothing needs updating, do nothing and exit
"""

    try:
        # Create branch from origin/{default_branch}
        git.fetch(remote="origin")
        git._run_git_command(
            ["checkout", "-b", branch_name, f"origin/{config.default_branch}"]
        )

        logger.info(f"Invoking Claude to update SYSTEM.md for tickets: {completed_ticket_ids}")
        invoke_claude(
            prompt=prompt,
            model="haiku",
            timeout_minutes=5,
            dry_run=False,
        )

        # Use pr_flow to push, create PR, and merge
        run_pr_flow(
            ticket_id="docs",
            commit_message=f"docs: update SYSTEM.md after {completed_ids_str}",
            default_branch=config.default_branch,
        )

        logger.info("SYSTEM.md update step completed")
    except Exception as e:
        logger.warning(f"SYSTEM.md update failed (non-fatal): {e}")
    finally:
        # Always return to detached HEAD at default branch
        checkout_detached_default(default_branch=config.default_branch)


# ============================================================================
# Claude Invocation
# ============================================================================


def invoke_claude(
    prompt: str,
    timeout_minutes: int = 30,
    model: str = "opus",
    dry_run: bool = False,
) -> EngineerResult:
    """Invoke Claude CLI for engineer work.

    Args:
        prompt: The prompt to send to Claude
        timeout_minutes: Timeout in minutes
        model: Model to use (opus/sonnet)
        dry_run: If True, don't actually invoke Claude

    Returns:
        EngineerResult with parsed output

    Raises:
        RuntimeError: If Claude CLI fails unexpectedly
    """
    if dry_run:
        return EngineerResult(
            status="dry_run",
            raw_output="[DRY RUN] Would invoke Claude",
        )

    # Build command
    cmd = [
        "claude",
        "-p",
        prompt,
        "--agent",
        "engineer",
        "--model",
        model,
        "--allowedTools",
        "Bash,Read,Write,Edit,Glob,Grep,TodoWrite",
        "--output-format",
        "stream-json",
        "--verbose",
    ]

    # Build clean environment (remove CLAUDECODE to allow nested invocation)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
            env=env,
        )

        output = result.stdout + result.stderr
        result_text = parse_stream_json_result(output)
        return parse_engineer_result(result_text)

    except subprocess.TimeoutExpired:
        return EngineerResult(status="timeout", raw_output="Claude invocation timed out")
    except FileNotFoundError:
        raise RuntimeError("Claude CLI not found. Please ensure it is installed and in PATH.")


# ============================================================================
# Ticket Processing
# ============================================================================


def process_ticket(
    ticket: Ticket,
    config: OrchestratorConfig,
    prd_path: Path,
    plan_path: Path,
    dry_run: bool = False,
    pm_tool: PMTool | None = None,
    ralph_label: str | None = None,
) -> TicketResult:
    """Process a single ticket through implementation and validation.

    Args:
        ticket: The ticket to process
        config: Orchestrator configuration
        prd_path: Path to PRD document
        plan_path: Path to plan document
        dry_run: If True, don't invoke Claude
        pm_tool: Optional PM tool for ticket operations
        ralph_label: Optional ralph instance label for concurrency control

    Returns:
        TicketResult with processing outcome
    """
    ticket_id = ticket.id
    branch_name = f"feature/{ticket_id}-implementation"
    start_time = time.time()

    # Get complexity for model selection
    complexity = getattr(ticket, "complexity", 3) or 3
    model = select_model_for_complexity(complexity, config.sonnet_threshold)

    # Dry run mode
    if dry_run:
        return TicketResult(
            ticket_id=ticket_id,
            status="dry_run",
            attempts=0,
        )

    def _format_duration(seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    # Get starting attempt number
    current_attempt = get_latest_attempt(ticket_id, config.state_directory) + 1

    # Attempt loop
    while current_attempt <= config.max_attempts:
        # Ensure state directory exists
        ensure_state_dir(ticket_id, current_attempt, config.state_directory)

        # Build prompt based on attempt number
        if current_attempt == 1:
            prompt = _build_initial_prompt(
                ticket_id=ticket_id,
                prd_path=prd_path,
                plan_path=plan_path,
                max_attempts=config.max_attempts,
                default_branch=config.default_branch,
            )
        else:
            prompt = _build_resume_prompt(
                ticket_id=ticket_id,
                attempt=current_attempt,
                max_attempts=config.max_attempts,
                branch=branch_name,
                state_directory=config.state_directory,
            )

        # Invoke Claude
        logger.info(f"Invoking Claude for {ticket_id} (attempt {current_attempt}/{config.max_attempts}, model={model}, complexity={complexity})")
        result = invoke_claude(
            prompt=prompt,
            timeout_minutes=config.engineer_timeout,
            model=model,
            dry_run=dry_run,
        )

        # Handle result
        logger.info(f"Claude returned: {result.status} for {ticket_id}")

        if result.status == VALIDATION_PASSED:
            # AIUI-0055: Invoke validation agent after engineer reports VALIDATION_PASSED
            # The validator verifies work against original PRD/plan acceptance criteria
            logger.info(f"Engineer passed for {ticket_id}, invoking validator...")

            # Build validator prompt with paths to PRD, plan, and state
            validator_prompt = build_validator_prompt(
                ticket_id=ticket_id,
                prd_path=prd_path,
                plan_path=plan_path,
                state_dir=config.state_directory,
                attempt=current_attempt,
                default_branch=config.default_branch,
            )

            # SLCA-0083: Validator retry loop
            # Retry the validator up to validator_max_retries times before
            # falling back to a full engineer re-run.
            validator_confirmed = False
            max_validator_calls = 1 + config.validator_max_retries

            for validator_attempt in range(max_validator_calls):
                # Invoke validator with configured model and timeout
                validator_result = invoke_validator(
                    prompt=validator_prompt,
                    timeout_minutes=config.validator_timeout,
                    model=config.validator_model,
                    dry_run=dry_run,
                )

                logger.info(f"Validator returned: {validator_result.status} for {ticket_id}")

                if validator_result.status == VALIDATION_CONFIRMED:
                    validator_confirmed = True
                    break

                # Validator did not confirm - log and potentially retry
                logger.warning(
                    f"Validator rejected {ticket_id}: {validator_result.reason or 'No reason given'}"
                )

                # If this was the initial call or an earlier retry, log the retry
                if validator_attempt < config.validator_max_retries:
                    retry_num = validator_attempt + 1
                    logger.info(
                        f"Validator retry {retry_num}/{config.validator_max_retries} for {ticket_id}"
                    )

            if not validator_confirmed:
                # All validator retries exhausted - fall back to full engineer re-run
                logger.warning(
                    f"All validator retries exhausted for {ticket_id}, "
                    f"falling back to engineer re-run"
                )
                current_attempt += 1
                continue

            # Validator confirmed - proceed with PR flow
            logger.info(f"Validator confirmed {ticket_id}, proceeding to PR flow")

            # Write summary BEFORE pr_flow so it gets included in the PR
            write_summary(
                ticket_id=ticket_id,
                status="SUCCESS",
                total_attempts=current_attempt,
                pr_number=None,  # PR not created yet
                base_dir=config.state_directory,
            )

            # Stage summary files so pr_flow includes them in its commit
            stage_summary_files(ticket_id, config.state_directory)

            # Run PR flow (will include staged summary files)
            try:
                pr_result = pr_flow(
                    ticket_id=ticket_id,
                    commit_message=f"[{ticket_id}] Implementation complete",
                    dry_run=dry_run,
                    default_branch=config.default_branch,
                )

                # Mark ticket done
                ticket_done(
                    ticket_id=ticket_id,
                    pr_number=str(pr_result.pr_number) if pr_result.pr_number else None,
                    pm_tool=pm_tool,
                    ralph_label=ralph_label,
                )

                duration = time.time() - start_time
                logger.info(f"Ticket {ticket_id} completed in {_format_duration(duration)} ({current_attempt} attempt(s))")
                return TicketResult(
                    ticket_id=ticket_id,
                    status="completed",
                    attempts=current_attempt,
                    pr_number=pr_result.pr_number,
                    duration_seconds=duration,
                )

            except MergeError as e:
                # Merge failed - this is a real failure, don't close the ticket
                # The PR was created but couldn't be merged (conflicts, API issues, etc.)
                duration = time.time() - start_time
                logger.error(f"Ticket {ticket_id} merge failed after {_format_duration(duration)}: {e}")

                # Mark as blocked so it can be retried or manually fixed
                mark_blocked(
                    ticket_id=ticket_id,
                    reason=f"Merge failed: {e}",
                    pm_tool=pm_tool,
                    ralph_label=ralph_label,
                )

                write_summary(
                    ticket_id=ticket_id,
                    status="BLOCKED",
                    total_attempts=current_attempt,
                    pr_number=None,
                    base_dir=config.state_directory,
                )

                return TicketResult(
                    ticket_id=ticket_id,
                    status="blocked",
                    attempts=current_attempt,
                    block_reason=f"Merge failed: {e}",
                    duration_seconds=duration,
                )

            except PrFlowError as e:
                # PR flow failed - push failed, PR couldn't be created, sync conflict, etc.
                # Code never made it to the target branch, don't close the ticket
                duration = time.time() - start_time
                logger.error(f"Ticket {ticket_id} PR flow failed after {_format_duration(duration)}: {e}")

                # Mark as blocked so it can be retried or manually fixed
                mark_blocked(
                    ticket_id=ticket_id,
                    reason=f"PR flow failed: {e}",
                    pm_tool=pm_tool,
                    ralph_label=ralph_label,
                )

                write_summary(
                    ticket_id=ticket_id,
                    status="BLOCKED",
                    total_attempts=current_attempt,
                    pr_number=None,
                    base_dir=config.state_directory,
                )

                return TicketResult(
                    ticket_id=ticket_id,
                    status="blocked",
                    attempts=current_attempt,
                    block_reason=f"PR flow failed: {e}",
                    duration_seconds=duration,
                )

        elif result.status == ALREADY_IMPLEMENTED:
            # Work was already done (e.g., bundled with another ticket)
            # Skip PR flow, just close the ticket
            duration = time.time() - start_time
            logger.info(f"Ticket {ticket_id} already implemented, closing in {_format_duration(duration)}")

            ticket_done(
                ticket_id=ticket_id,
                pr_number=None,
                pm_tool=pm_tool,
                ralph_label=ralph_label,
            )

            write_summary(
                ticket_id=ticket_id,
                status="SUCCESS",
                total_attempts=current_attempt,
                pr_number=None,
                base_dir=config.state_directory,
            )

            # Note: Summary files left uncommitted in this edge case
            # (detached HEAD prevents pushing, no PR to include them)

            return TicketResult(
                ticket_id=ticket_id,
                status="completed",
                attempts=current_attempt,
                duration_seconds=duration,
            )

        elif result.status == VALIDATION_FAILED:
            # Try again if we have attempts left
            current_attempt += 1
            continue

        elif result.status == "timeout":
            # Timeout - try again
            current_attempt += 1
            continue

        else:
            # Unknown result - try again
            current_attempt += 1
            continue

    # Exceeded max attempts - mark as blocked
    duration = time.time() - start_time
    block_reason = f"Exceeded {config.max_attempts} attempts"
    logger.warning(f"Ticket {ticket_id} blocked after {_format_duration(duration)}: {block_reason}")

    # Mark blocked in PM tool
    if pm_tool is not None:
        try:
            mark_blocked(
                ticket_id=ticket_id,
                reason=block_reason,
                pm_tool=pm_tool,
                ralph_label=ralph_label,
            )
            logger.debug(f"Marked ticket {ticket_id} as blocked in PM tool")
        except Exception as e:
            logger.error(f"Failed to mark ticket {ticket_id} as blocked in PM tool: {e}")

    write_summary(
        ticket_id=ticket_id,
        status="BLOCKED",
        total_attempts=config.max_attempts,
        base_dir=config.state_directory,
    )

    return TicketResult(
        ticket_id=ticket_id,
        status="blocked",
        attempts=config.max_attempts,
        block_reason=block_reason,
        duration_seconds=duration,
    )


# ============================================================================
# Prompt Building
# ============================================================================


def _build_initial_prompt(
    ticket_id: str,
    prd_path: Path,
    plan_path: Path,
    max_attempts: int,
    default_branch: str,
) -> str:
    """Build initial implementation prompt for first attempt.

    Args:
        ticket_id: The ticket identifier
        prd_path: Path to PRD document
        plan_path: Path to plan document
        max_attempts: Maximum attempts allowed
        default_branch: Default git branch from config (required)

    Returns:
        Formatted prompt string
    """
    return f"""# Engineer Task: Implement {ticket_id}

## Context

**Ticket:** {ticket_id}
**Attempt:** 1 of {max_attempts}
**Branch:** Create "feature/{ticket_id}-implementation"

## Required Reading

1. **System Manifest:** `docs/SYSTEM.md` - Understand current architecture, decisions, and conventions FIRST
2. **PRD:** `{prd_path}` - Find acceptance criteria for {ticket_id}
3. **Plan:** `{plan_path}` - Find technical approach for {ticket_id}
4. **Coding Standards:** `docs/coding-standards.md` - Follow all standards

## Your Task

Implement this ticket using Test-Driven Development:

### Step 1: Create Feature Branch

```bash
git fetch origin {default_branch}
git checkout -b feature/{ticket_id}-implementation origin/{default_branch}
```

### Step 2: TDD Implementation

For each piece of functionality:
1. **RED:** Write a failing test
2. **GREEN:** Write minimum code to pass
3. **REFACTOR:** Clean up while tests stay green

### Step 3: Run Validation

After implementation, run ALL checks from config.yaml and fix any errors.

### Step 4: Write State File

Create state file with implementation details.

### Step 5: Commit and Report

If validation passed:
```
VALIDATION_PASSED

Ticket: {ticket_id}
Branch: feature/{ticket_id}-implementation
Commit: <sha>
```

If validation failed:
```
VALIDATION_FAILED

Ticket: {ticket_id}
Branch: feature/{ticket_id}-implementation
Commit: <sha>
State file: docs/state/{ticket_id}/attempt-1/engineer-state.md
```
"""


def _build_resume_prompt(
    ticket_id: str,
    attempt: int,
    max_attempts: int,
    branch: str,
    state_directory: Path,
) -> str:
    """Build resume prompt for subsequent attempts.

    Args:
        ticket_id: The ticket identifier
        attempt: Current attempt number
        max_attempts: Maximum attempts allowed
        branch: Branch name
        state_directory: Directory for state files

    Returns:
        Formatted prompt string
    """
    prev_attempt = attempt - 1
    prev_state_file = state_directory / ticket_id / f"attempt-{prev_attempt}" / "engineer-state.md"

    return f"""# Engineer Task: Resume {ticket_id}

## Context

**Ticket:** {ticket_id}
**Attempt:** {attempt} of {max_attempts}
**Branch:** {branch} (already exists - checkout and continue)

## Previous Attempt

Review the previous state file for context on what was done and what failed:
- Previous state: `{prev_state_file}`

## Your Task

1. **Checkout the existing branch:** `git checkout {branch}`
2. **Review previous work** - Read the state file
3. **Fix the issues** - Address validation failures
4. **Run validation** - All checks must pass
5. **Report result** - VALIDATION_PASSED or VALIDATION_FAILED

Report your result at the end:

If validation passed:
```
VALIDATION_PASSED

Ticket: {ticket_id}
Branch: {branch}
Commit: <sha>
```

If validation failed:
```
VALIDATION_FAILED

Ticket: {ticket_id}
Branch: {branch}
Commit: <sha>
State file: docs/state/{ticket_id}/attempt-{attempt}/engineer-state.md
```
"""


def check_validation_file_exists(
    ticket_id: str,
    attempt: int,
    state_dir: Path,
) -> bool:
    """Check if validation.md file exists for a ticket attempt.

    AIUI-0056: Implements validation file existence check.

    Args:
        ticket_id: The ticket identifier (e.g., "AIUI-0056")
        attempt: Current attempt number
        state_dir: Base directory for state files

    Returns:
        True if validation.md exists, False otherwise
    """
    validation_file = state_dir / ticket_id / f"attempt-{attempt}" / "validation.md"
    return validation_file.exists()


def write_fallback_validation_report(
    ticket_id: str,
    attempt: int,
    status: str,
    message: str,
    state_dir: Path,
) -> Path:
    """Write fallback validation report when validator doesn't write one.

    AIUI-0056: Implements fallback validation report writing.

    If the validator agent completes but doesn't write validation.md,
    this function creates a minimal validation report as fallback.

    Args:
        ticket_id: The ticket identifier
        attempt: Current attempt number
        status: Validation status (validation_confirmed, validation_rejected, etc.)
        message: Message to include in the report
        state_dir: Base directory for state files

    Returns:
        Path to the created validation.md file
    """
    from datetime import datetime
    from core.state import ensure_state_dir

    # Ensure directory exists
    attempt_dir = ensure_state_dir(ticket_id, attempt, state_dir)
    validation_file = attempt_dir / "validation.md"

    # Create fallback validation report
    content = f"""# Validation Report: {ticket_id}

**Attempt:** {attempt}
**Timestamp:** {datetime.now().isoformat()}
**Status:** {status}

---

## Note

{message}

This is a fallback validation report created because the validator agent
did not write a validation.md file.

---

## Validator Result

**Status:** {status.replace('_', ' ').upper()}

The validator completed execution but did not produce a detailed validation report.
Check the validator agent output for more details.
"""

    validation_file.write_text(content)
    return validation_file


def build_validator_prompt(
    ticket_id: str,
    prd_path: Path,
    plan_path: Path,
    state_dir: Path,
    attempt: int,
    default_branch: str = "",
) -> str:
    """Build validation prompt for the validator agent.

    Constructs a prompt that instructs the validator to verify engineer work
    against ORIGINAL acceptance criteria from PRD/plan (not the engineer's
    interpretation). Includes bypass language detection and dependency
    verification instructions.

    This function implements:
    - FR-2: Validator Reads Original Acceptance Criteria
    - FR-3: Validator Verifies Dependencies Merged
    - FR-4: Validator Flags Bypass Language
    - FR-5: Validator Output to State Directory

    Args:
        ticket_id: The ticket identifier (e.g., "AIUI-0051")
        prd_path: Path to PRD document containing acceptance criteria
        plan_path: Path to plan document containing technical approach
        state_dir: Base directory for state files (e.g., "docs/state")
        attempt: Current attempt number
        default_branch: Default git branch name (required, e.g., "develop-working")

    Returns:
        Formatted prompt string for the validation agent
    """
    if not default_branch:
        from core.config import get_default_branch
        default_branch = get_default_branch()

    state_path = state_dir / ticket_id / f"attempt-{attempt}"
    engineer_state_file = state_path / "engineer-state.md"
    validation_output = state_path / "validation.md"

    return f"""# Validation Agent Task: Verify {ticket_id}

## Your Role

You are a validation agent. Your job is to verify the engineer's work against
ORIGINAL acceptance criteria from the PRD and plan - NOT the engineer's
interpretation of what they think they did.

**IMPORTANT:** The PRD and plan contain the REAL acceptance criteria. The engineer
state file shows what the engineer CLAIMS they did. If there is a mismatch between
what was required and what was delivered, you must flag it.

Do NOT trust the engineer's state file for criteria definition. Compare actual
implementation against original PRD/plan requirements.

## Required Reading

1. **PRD:** `{prd_path}` - Find the ORIGINAL acceptance criteria for {ticket_id}
2. **Plan:** `{plan_path}` - Find the technical approach and dependencies for {ticket_id}
3. **Engineer state:** `{engineer_state_file}` - See what the engineer claims they did

## Verification Steps

### Step 1: Verify Acceptance Criteria

For each acceptance criterion in the PRD/plan for {ticket_id}:
1. Read the original criterion from PRD/plan
2. Check if it is actually met in the implementation
3. Note any discrepancies or partial implementations

### Step 2: Verify Upstream Dependencies Are Merged

If the ticket has upstream dependencies listed in the plan (other tickets it depends ON):
1. Run `git log origin/{default_branch} --oneline | grep {{dependency-id}}` for each upstream dependency
2. Verify each upstream dependency has a merge commit on `{default_branch}`
3. If any upstream dependency is NOT merged, this is a validation failure

**IMPORTANT:** The default branch is `{default_branch}` (NOT necessarily "main").
Do NOT check whether the CURRENT ticket is merged. The current ticket is still on its
feature branch — merging to `{default_branch}` happens AFTER validation confirms.
You are only checking that tickets this one DEPENDS ON are already merged to `{default_branch}`.

### Step 3: Scan for Bypass Language

Scan the engineer's state file for bypass language patterns that may indicate
the engineer redefined success criteria:

- "not merged but acceptable" or similar
- "doesn't block" or "doesn't apply"
- "out of scope" justifications that contradict PRD requirements
- Any language that reframes or downgrades acceptance criteria

If bypass language is detected, flag it and require explicit justification.

### Step 4: Flag Criteria Mismatches

If the engineer redefined what "success" means in their state file (different
from the original PRD/plan criteria), this must be flagged as a concern.

## Output Requirements

Write your validation findings to: `{validation_output}`

Your validation file should include:
- Each acceptance criterion checked
- Pass/fail status for each criterion
- Any bypass language detected
- Any concerns or flags raised
- Dependency merge verification results

## Final Decision

After completing verification, return ONE of:

**If all criteria met and no concerns:**
```
VALIDATION_CONFIRMED

Ticket: {ticket_id}
All acceptance criteria verified against original PRD/plan.
```

**If criteria not met or concerns require review:**
```
VALIDATION_REJECTED

Ticket: {ticket_id}
Reason: [specific reason - criteria not met, bypass detected, dependencies not merged, etc.]
```

Do NOT return VALIDATION_CONFIRMED if:
- Any original acceptance criterion is not met
- Upstream dependencies are not merged to {default_branch}
- Bypass language is detected without valid justification
- The engineer's interpretation differs significantly from PRD requirements
"""


# ============================================================================
# Main Orchestrator
# ============================================================================


def run_orchestrator(
    prd_path: Path,
    plan_path: Path,
    workflow_state: WorkflowState,
    config_file: Path | None = None,
    dry_run: bool = False,
    max_wait_retries: int = DEFAULT_MAX_WAIT_RETRIES,
    wait_interval: int = DEFAULT_WAIT_INTERVAL,
) -> OrchestratorResult:
    """Run the main orchestrator loop.

    Processes tickets in dependency order until all are complete or blocked.

    Args:
        prd_path: Path to PRD document
        plan_path: Path to plan document
        workflow_state: In-memory workflow state built from PRD/plan
        config_file: Path to config.yaml
        dry_run: If True, don't invoke Claude
        max_wait_retries: Maximum retries when waiting for dependencies or claims
        wait_interval: Seconds to wait between dependency/claims checks

    Returns:
        OrchestratorResult with final status
    """
    result = OrchestratorResult(
        status="running",
        start_time=datetime.now(),
    )

    # Load configuration
    config = load_config(config_file)
    logger.debug(f"Loaded config: max_attempts={config.max_attempts}, use_assignee={config.use_assignee}")

    # Create PM tool based on config
    pm_tool = create_pm_tool(config_file)

    # Get RALPH_LABEL from config (which reads from env or .env file)
    ralph_label = config.instance_label or None
    if ralph_label:
        logger.info(f"Running as instance: {ralph_label}")
    else:
        raise RuntimeError(
            "RALPH_LABEL is required.\n"
            "Set it in environment or .env file to identify this Ralph instance.\n"
            "Example: RALPH_LABEL=ralph-0 .claude/ralph/ralph run ...\n"
            "Or add to .env: RALPH_LABEL=ralph-0"
        )

    # Use provided workflow state
    state = workflow_state

    # Ticket processing loop
    wait_retry_count = 0

    while True:
        # Get next ticket using PM tool for status queries
        next_result = get_next_ticket(
            state,
            pm_tool=pm_tool,
            ralph_label=ralph_label,
        )

        # Handle waiting on dependencies
        if next_result.status == "waiting_on_dependencies":
            wait_retry_count += 1

            if wait_retry_count >= max_wait_retries:
                # Max wait time reached
                break

            # Wait and retry
            if not dry_run:
                time.sleep(wait_interval)

            # Rebuild state from PRD (gets fresh data)
            state = build_workflow_state(prd_path, plan_path)
            continue

        # Handle waiting on claims (all eligible tickets claimed by other instances)
        if next_result.status == "waiting_on_claims":
            wait_retry_count += 1

            if wait_retry_count >= max_wait_retries:
                # Max wait time reached waiting for other instances to complete
                logger.info(
                    "Max wait time exceeded: all eligible tickets are claimed by other "
                    "instances. Exiting loop after %d retries.",
                    wait_retry_count,
                )
                break

            logger.info(
                "All eligible tickets claimed by other instances (retry %d/%d). "
                "Waiting %ds before retry...",
                wait_retry_count,
                max_wait_retries,
                wait_interval,
            )

            # Wait and retry
            if not dry_run:
                time.sleep(wait_interval)

            # Rebuild state from PRD (gets fresh data)
            state = build_workflow_state(prd_path, plan_path)
            continue

        # Reset wait counter when we get a ticket
        wait_retry_count = 0

        # No more tickets
        if not next_result.has_more or next_result.ticket is None:
            break

        # Process this ticket
        ticket = next_result.ticket
        ticket_result = process_ticket(
            ticket=ticket,
            config=config,
            prd_path=prd_path,
            plan_path=plan_path,
            dry_run=dry_run,
            pm_tool=pm_tool,
            ralph_label=ralph_label,
        )

        result.ticket_results.append(ticket_result)

        if ticket_result.status == "completed":
            result.completed_count += 1
        elif ticket_result.status == "blocked":
            result.blocked_count += 1

        # Rebuild state for next iteration
        state = build_workflow_state(prd_path, plan_path)

    # Note: SYSTEM.md update has been moved to /ralph-loop (post-loop step).
    # This ensures it runs exactly once after ALL concurrent loops finish,
    # rather than each orchestrator instance trying to update independently.

    # Determine final status
    result.end_time = datetime.now()

    if result.blocked_count > 0 and result.completed_count == 0:
        result.status = "all_blocked"
    elif result.blocked_count > 0:
        result.status = "incomplete"
    else:
        result.status = "complete"

    return result


# ============================================================================
# CLI Entry Point
# ============================================================================


def main(
    prd_path: str,
    plan_path: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Main entry point for orchestrator.

    Args:
        prd_path: Path to PRD document
        plan_path: Path to plan document
        dry_run: If True, don't invoke Claude
        verbose: Show verbose output

    Returns:
        Exit code (0 for success, 1 for incomplete, 2 for error)
    """
    try:
        prd = Path(prd_path)
        plan = Path(plan_path)

        if not prd.exists():
            logger.error(f"PRD not found: {prd}")
            return 2

        if not plan.exists():
            logger.error(f"Plan not found: {plan}")
            return 2

        # Build workflow state from PRD and plan
        ws = build_workflow_state(prd, plan)

        result = run_orchestrator(
            prd_path=prd,
            plan_path=plan,
            workflow_state=ws,
            dry_run=dry_run,
        )

        # Log summary
        logger.info(f"Orchestration {result.status}: completed={result.completed_count}, blocked={result.blocked_count}")

        if result.status == "complete":
            return 0
        else:
            return 1

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        if verbose:
            logger.exception("Full traceback:")
        return 2


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Orchestrator")
    parser.add_argument("prd", help="Path to PRD document")
    parser.add_argument("plan", help="Path to plan document")
    parser.add_argument("--dry-run", action="store_true", help="Preview without invoking Claude")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    sys.exit(main(
        prd_path=args.prd,
        plan_path=args.plan,
        dry_run=args.dry_run,
        verbose=args.verbose,
    ))
