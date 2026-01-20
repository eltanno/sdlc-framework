"""Main orchestrator loop for Ralph workflow.

This module implements the core Ralph loop that:
- Gets the next eligible ticket
- Invokes Claude to implement the ticket
- Handles success/failure outcomes
- Progresses through all tickets until completion

This is a port of .claude/scripts/ralph-prd.sh to Python.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

from commands.get_next import get_next_ticket, GetNextResult
from commands.mark_blocked import mark_blocked
from commands.pr_flow import pr_flow, PrFlowResult, PrFlowError
from commands.ticket_done import ticket_done
from core.config import get_pm_tool_type, ConfigError, get_use_assignee
from core.pm import PMTool, PMError, GitHubPM, LocalPM
from core.state import (
    WorkflowState,
    Ticket,
    load_workflow_state,
    save_workflow_state,
    ensure_state_dir,
    get_latest_attempt,
    write_summary,
)


# ============================================================================
# Constants
# ============================================================================

VALIDATION_PASSED = "validation_passed"
VALIDATION_FAILED = "validation_failed"

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_SONNET_THRESHOLD = 2
DEFAULT_ENGINEER_TIMEOUT = 30
DEFAULT_VALIDATOR_TIMEOUT = 10
DEFAULT_WAIT_INTERVAL = 30  # seconds
DEFAULT_MAX_WAIT_RETRIES = 60  # 60 * 30s = 30 minutes


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
        validator_model: Model to use for validation analysis
        engineer_timeout: Timeout in minutes for engineer invocation
        validator_timeout: Timeout in minutes for validator invocation
        instance_label: Label for this ralph instance (from RALPH_LABEL env)
        use_assignee: Whether to also assign issues to current user when claiming
        test_command: Command to run tests
        lint_command: Command to run linter
        typecheck_command: Command to run type checker
        build_command: Command to run build
        default_branch: Default git branch (main/master)
    """

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    sonnet_threshold: int = DEFAULT_SONNET_THRESHOLD
    state_directory: Path = field(default_factory=lambda: Path("docs/state"))
    validator_model: str = "haiku"
    engineer_timeout: int = DEFAULT_ENGINEER_TIMEOUT
    validator_timeout: int = DEFAULT_VALIDATOR_TIMEOUT
    instance_label: str = ""
    use_assignee: bool = False
    test_command: str = ""
    lint_command: str = ""
    typecheck_command: str = ""
    build_command: str = ""
    default_branch: str = "main"


@dataclass
class EngineerResult:
    """Result from parsing Claude engineer output.

    Attributes:
        status: Result status (validation_passed, validation_failed, timeout, unknown)
        ticket_id: Ticket ID from output
        branch: Branch name from output
        commit: Commit SHA from output
        state_file: Path to state file (if provided)
        raw_output: Raw output from Claude
    """

    status: str
    ticket_id: str | None = None
    branch: str | None = None
    commit: str | None = None
    state_file: str | None = None
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
    """

    ticket_id: str
    status: str
    attempts: int = 0
    pr_number: int | None = None
    block_reason: str | None = None


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

    return OrchestratorConfig(
        max_attempts=ralph_config.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
        sonnet_threshold=ralph_config.get("sonnet_threshold", DEFAULT_SONNET_THRESHOLD),
        state_directory=Path(ralph_config.get("state_directory", "docs/state")),
        validator_model=ralph_config.get("validator_model", "haiku"),
        engineer_timeout=ralph_config.get("engineer_timeout", DEFAULT_ENGINEER_TIMEOUT),
        validator_timeout=ralph_config.get("validator_timeout", DEFAULT_VALIDATOR_TIMEOUT),
        instance_label=instance_label,
        use_assignee=ralph_config.get("use_assignee", False),
        test_command=dev_config.get("test_command", ""),
        lint_command=dev_config.get("lint_command", ""),
        typecheck_command=dev_config.get("typecheck_command", ""),
        build_command=dev_config.get("build_command", ""),
        default_branch=git_config.get("default_branch", "main"),
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
        logger.debug("Initializing GitHubPM")
        return GitHubPM()
    elif pm_tool_type == "none":
        logger.debug("Initializing LocalPM (degraded mode)")
        return LocalPM()
    else:
        # For future PM tools (trello, asana, linear), raise ConfigError
        # until they're implemented
        raise ConfigError(
            f"PM tool '{pm_tool_type}' is not yet implemented. "
            f"Supported tools: github, none",
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
    if "VALIDATION_PASSED" in output:
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

    # Parse state file
    state_match = re.search(r"State file:\s*(.+)", output)
    state_file = state_match.group(1).strip() if state_match else None

    return EngineerResult(
        status=status,
        ticket_id=ticket_id,
        branch=branch,
        commit=commit,
        state_file=state_file,
        raw_output=output,
    )


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

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
        )

        output = result.stdout + result.stderr

        # Parse result from stream-json output
        # Look for {"type":"result"} JSON line
        result_text = ""
        for line in output.splitlines():
            if '"type":"result"' in line:
                try:
                    data = json.loads(line)
                    result_text = data.get("result", "")
                    break
                except json.JSONDecodeError:
                    continue

        # If no result JSON found, use full output
        if not result_text:
            result_text = output

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
    state_file: Path,
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
        state_file: Path to workflow state file
        dry_run: If True, don't invoke Claude
        pm_tool: Optional PM tool for ticket operations
        ralph_label: Optional ralph instance label for concurrency control

    Returns:
        TicketResult with processing outcome
    """
    ticket_id = ticket.id
    branch_name = f"feature/{ticket_id}-implementation"

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
        result = invoke_claude(
            prompt=prompt,
            timeout_minutes=config.engineer_timeout,
            model=model,
            dry_run=dry_run,
        )

        # Handle result
        if result.status == VALIDATION_PASSED:
            # Success! Run PR flow
            try:
                pr_result = pr_flow(
                    ticket_id=ticket_id,
                    commit_message=f"[{ticket_id}] Implementation complete",
                    dry_run=dry_run,
                )

                # Mark ticket done
                ticket_done(
                    ticket_id=ticket_id,
                    pr_number=str(pr_result.pr_number) if pr_result.pr_number else None,
                    state_file=state_file,
                    pm_tool=pm_tool,
                    ralph_label=ralph_label,
                )

                # Write success summary
                write_summary(
                    ticket_id=ticket_id,
                    status="SUCCESS",
                    total_attempts=current_attempt,
                    pr_number=str(pr_result.pr_number) if pr_result.pr_number else None,
                    base_dir=config.state_directory,
                )

                return TicketResult(
                    ticket_id=ticket_id,
                    status="completed",
                    attempts=current_attempt,
                    pr_number=pr_result.pr_number,
                )

            except PrFlowError as e:
                # PR flow failed, but validation passed - treat as completed but note issue
                return TicketResult(
                    ticket_id=ticket_id,
                    status="completed",
                    attempts=current_attempt,
                    block_reason=f"PR flow error: {e}",
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
    block_reason = f"Exceeded {config.max_attempts} attempts"
    logger.warning(f"Ticket {ticket_id} blocked: {block_reason}")

    # Mark blocked in PM tool and state
    if pm_tool is not None:
        try:
            mark_blocked(
                ticket_id=ticket_id,
                reason=block_reason,
                state_file=state_file,
                pm_tool=pm_tool,
                ralph_label=ralph_label,
            )
            logger.debug(f"Marked ticket {ticket_id} as blocked in PM tool")
        except Exception as e:
            # Log but don't fail - we still want to return blocked status
            # The state file update in mark_blocked might have succeeded
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
    )


# ============================================================================
# Prompt Building
# ============================================================================


def _build_initial_prompt(
    ticket_id: str,
    prd_path: Path,
    plan_path: Path,
    max_attempts: int,
) -> str:
    """Build initial implementation prompt for first attempt.

    Args:
        ticket_id: The ticket identifier
        prd_path: Path to PRD document
        plan_path: Path to plan document
        max_attempts: Maximum attempts allowed

    Returns:
        Formatted prompt string
    """
    return f"""# Engineer Task: Implement {ticket_id}

## Context

**Ticket:** {ticket_id}
**Attempt:** 1 of {max_attempts}
**Branch:** Create `feature/{ticket_id}-implementation`

## Required Reading

1. **PRD:** `{prd_path}` - Find acceptance criteria for {ticket_id}
2. **Plan:** `{plan_path}` - Find technical approach for {ticket_id}
3. **Coding Standards:** `docs/coding-standards.md` - Follow all standards

## Your Task

Implement this ticket using Test-Driven Development:

### Step 1: Create Feature Branch

```bash
git fetch origin main
git checkout -b feature/{ticket_id}-implementation origin/main
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
**Branch:** `{branch}` (already exists - checkout and continue)

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


# ============================================================================
# Main Orchestrator
# ============================================================================


def run_orchestrator(
    prd_path: Path,
    plan_path: Path,
    state_file: Path,
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
        state_file: Path to workflow state file
        config_file: Path to config.yaml
        dry_run: If True, don't invoke Claude
        max_wait_retries: Maximum retries when waiting for dependencies
        wait_interval: Seconds to wait between dependency checks

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

    # Load workflow state
    state = load_workflow_state(state_file)
    logger.debug(f"Loaded workflow state from {state_file}")

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

            # Reload state (might have been updated by another instance)
            state = load_workflow_state(state_file)
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
            state_file=state_file,
            dry_run=dry_run,
            pm_tool=pm_tool,
            ralph_label=ralph_label,
        )

        result.ticket_results.append(ticket_result)

        if ticket_result.status == "completed":
            result.completed_count += 1
        elif ticket_result.status == "blocked":
            result.blocked_count += 1

        # Reload state for next iteration
        state = load_workflow_state(state_file)

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
    max_attempts: int | None = None,
    verbose: bool = False,
) -> int:
    """Main entry point for orchestrator.

    Args:
        prd_path: Path to PRD document
        plan_path: Path to plan document
        dry_run: If True, don't invoke Claude
        max_attempts: Override max attempts from config
        verbose: Show verbose output

    Returns:
        Exit code (0 for success, 1 for incomplete, 2 for error)
    """
    try:
        prd = Path(prd_path)
        plan = Path(plan_path)

        if not prd.exists():
            print(f"ERROR: PRD not found: {prd}")
            return 2

        if not plan.exists():
            print(f"ERROR: Plan not found: {plan}")
            return 2

        # Determine state file path
        state_file = Path("workflow-state.json")
        if not state_file.exists():
            print(f"ERROR: State file not found: {state_file}")
            print("Run setup first to initialize the workflow.")
            return 2

        result = run_orchestrator(
            prd_path=prd,
            plan_path=plan,
            state_file=state_file,
            dry_run=dry_run,
        )

        # Print summary
        print(f"\nOrchestration {result.status}")
        print(f"Completed: {result.completed_count}")
        print(f"Blocked: {result.blocked_count}")

        if result.status == "complete":
            return 0
        else:
            return 1

    except Exception as e:
        print(f"ERROR: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 2


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Orchestrator")
    parser.add_argument("prd", help="Path to PRD document")
    parser.add_argument("plan", help="Path to plan document")
    parser.add_argument("--dry-run", action="store_true", help="Preview without invoking Claude")
    parser.add_argument("--max-attempts", type=int, help="Max attempts per ticket")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    sys.exit(main(
        prd_path=args.prd,
        plan_path=args.plan,
        dry_run=args.dry_run,
        max_attempts=args.max_attempts,
        verbose=args.verbose,
    ))
