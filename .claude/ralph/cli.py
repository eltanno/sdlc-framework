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
    --max-attempts N    Max retries per ticket (default: 3)
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
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum retry attempts per ticket (default: 3)",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show debug output and stack traces",
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
    from commands.setup import run_setup

    # Validate paths
    if not args.prd.exists():
        print(f"Error: PRD file not found: {args.prd}")
        return 1
    if not args.plan.exists():
        print(f"Error: Plan file not found: {args.plan}")
        return 1

    # State file is specific to this PRD (based on PRD filename)
    prd_name = args.prd.stem  # e.g., "2026-01-20-asana-pm-tool-integration"
    state_file = Path(f"ralph-state-{prd_name}.json")

    # Find config.yaml
    config_file = Path("config.yaml")
    if not config_file.exists():
        config_file = None

    print(f"Starting Ralph orchestrator...")
    print(f"  PRD:    {args.prd}")
    print(f"  Plan:   {args.plan}")
    print(f"  State:  {state_file}")
    print(f"  Config: {config_file or 'defaults'}")
    print()

    # Initialize state file if it doesn't exist
    if not state_file.exists():
        print("Initializing workflow state from PRD and plan...")
        setup_result = run_setup(
            prd_path=args.prd,
            plan_path=args.plan,
            state_file=state_file,
        )
        if not setup_result.success:
            print(f"Error during setup: {setup_result.error}")
            return 1
        print(f"  Found {setup_result.ticket_count} tickets")
        print()

    if args.dry_run:
        print("DRY RUN MODE - No Claude invocations will be made")
        print()

    try:
        result = run_orchestrator(
            prd_path=args.prd,
            plan_path=args.plan,
            state_file=state_file,
            config_file=config_file,
            dry_run=args.dry_run,
        )

        print()
        print(f"Orchestrator completed with status: {result.status}")
        print(f"  Tickets completed: {result.completed_count}")
        print(f"  Tickets blocked:   {result.blocked_count}")

        if result.status == "complete":
            return 0
        elif result.status == "blocked":
            return 2  # Partial completion
        else:
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        return 1


def status_command(args: argparse.Namespace) -> int:
    """Execute the status command - show workflow status."""
    from commands.status import show_status

    if not args.state_file.exists():
        print(f"Error: State file not found: {args.state_file}")
        return 1

    try:
        show_status(args.state_file)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def reset_command(args: argparse.Namespace) -> int:
    """Execute the reset command - reset a blocked ticket."""
    from commands.ticket_reset import reset_ticket

    try:
        success = reset_ticket(args.ticket_id)
        return 0 if success else 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
