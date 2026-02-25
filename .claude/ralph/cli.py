#!/usr/bin/env python3
"""Ralph CLI entry point.

This module provides the command-line interface for Ralph, the automated
workflow orchestrator. It parses arguments and delegates to the appropriate
command modules.

Usage:
    ralph run <prd-path> <plan-path> [options]
    ralph status <state-file>
    ralph reset <ticket-id>

Options:
    --dry-run           Preview without invoking Claude
    --verbose           Show debug output and stack traces
    --help              Show help message
"""

import argparse
import logging
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Ralph - Automated workflow orchestrator for PRD/plan execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ralph run docs/prd.md docs/plan.md              # Run full workflow
    ralph run docs/prd.md docs/plan.md --dry-run    # Preview without execution
    ralph status state.json                          # Check workflow status
    ralph reset TASK-123                             # Reset blocked ticket
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Main orchestrator
    run_parser = subparsers.add_parser("run", help="Run the orchestrator loop")
    run_parser.add_argument("prd", type=Path, help="Path to PRD document")
    run_parser.add_argument("plan", type=Path, help="Path to plan document")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without invoking Claude",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show debug output and stack traces",
    )
    run_parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip pre-flight test suite check",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show workflow status")
    status_parser.add_argument("state_file", type=Path, help="Path to state file")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset a blocked ticket")
    reset_parser.add_argument("ticket_id", help="Ticket ID to reset (e.g., TASK-123)")

    return parser


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    """Main entry point for Ralph CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle no command
    if args.command is None:
        parser.print_help()
        return 1

    # Setup logging
    verbose = getattr(args, "verbose", False)
    setup_logging(verbose)

    # Route to appropriate command
    if args.command == "run":
        return run_command(args)
    elif args.command == "status":
        return status_command(args)
    elif args.command == "reset":
        return reset_command(args)
    else:
        parser.print_help()
        return 1


def run_command(args: argparse.Namespace) -> int:
    """Execute the run command - main orchestrator loop."""
    from commands.orchestrator import run_orchestrator
    from core.state import build_workflow_state

    logger = logging.getLogger(__name__)

    # Validate paths
    if not args.prd.exists():
        logger.error(f"PRD file not found: {args.prd}")
        return 1
    if not args.plan.exists():
        logger.error(f"Plan file not found: {args.plan}")
        return 1

    # Find config.yaml
    config_file = Path("config.yaml")
    if not config_file.exists():
        config_file = None

    # Build workflow state in memory from PRD and plan
    logger.info(f"Starting Ralph: prd={args.prd}, plan={args.plan}, config={config_file or 'defaults'}")

    from core.config import get_default_branch
    try:
        default_branch = get_default_branch(config_file or Path("config.yaml"))
        logger.info(f"Default branch: {default_branch}")
    except Exception as e:
        logger.error(f"Failed to determine default branch: {e}")
        return 1
    workflow_state = build_workflow_state(prd_path=args.prd, plan_path=args.plan)
    ticket_count = len(workflow_state.ralph.tickets) if workflow_state.ralph else 0
    logger.info(f"Built workflow state: found {ticket_count} tickets")

    # Pre-flight: verify test suite is green before processing tickets
    if not args.dry_run and not args.skip_preflight:
        from commands.preflight import run_preflight_check

        preflight_passed = run_preflight_check(config_file)
        if not preflight_passed:
            return 1

    if args.dry_run:
        logger.info("DRY RUN MODE - No Claude invocations will be made")

    try:
        result = run_orchestrator(
            prd_path=args.prd,
            plan_path=args.plan,
            workflow_state=workflow_state,
            config_file=config_file,
            dry_run=args.dry_run,
        )

        logger.info(f"Orchestrator {result.status}: completed={result.completed_count}, blocked={result.blocked_count}")

        if result.status == "complete":
            return 0
        elif result.status == "blocked":
            return 2  # Partial completion
        else:
            return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        if args.verbose:
            logger.exception("Error in orchestrator:")
        else:
            logger.error(f"Error: {e}")
        return 1


def status_command(args: argparse.Namespace) -> int:
    """Execute the status command - show workflow status."""
    from commands.status import show_status

    logger = logging.getLogger(__name__)

    if not args.state_file.exists():
        logger.error(f"State file not found: {args.state_file}")
        return 1

    try:
        show_status(args.state_file)
        return 0
    except Exception as e:
        logger.error(f"Status error: {e}")
        return 1


def reset_command(args: argparse.Namespace) -> int:
    """Execute the reset command - reset a blocked ticket."""
    from commands.ticket_reset import reset_ticket

    logger = logging.getLogger(__name__)

    try:
        success = reset_ticket(args.ticket_id)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Reset error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
