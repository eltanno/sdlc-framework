#!/usr/bin/env python3
"""Ralph CLI entry point.

This module provides the command-line interface for Ralph, the automated
workflow orchestrator. It parses arguments and delegates to the appropriate
command modules.

Usage:
    ralph <prd-path> <plan-path> [options]
    ralph status <state-file>
    ralph reset <ticket-id> --state-file <state-file>

Options:
    --dry-run           Preview without invoking Claude
    --max-attempts N    Max retries per ticket (default: 3)
    --verbose           Show debug output and stack traces
    --help              Show help message
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any

from commands.status import display_status
from commands.ticket_reset import reset_ticket, TicketResetError


def run_orchestrator(
    prd_path: Path,
    plan_path: Path,
    dry_run: bool = False,
    max_attempts: int = 3,
    verbose: bool = False,
) -> int:
    """Run the orchestrator loop.

    This function coordinates the full workflow execution:
    - Setup: Initialize state from PRD/plan
    - Loop: Get next ticket, invoke Claude, handle result
    - Cleanup: Archive state and report summary

    Args:
        prd_path: Path to PRD document
        plan_path: Path to plan document
        dry_run: If True, preview without invoking Claude
        max_attempts: Maximum retry attempts per ticket
        verbose: If True, show debug output

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Validate files exist
    if not prd_path.exists():
        print(f"Error: PRD file not found: {prd_path}", file=sys.stderr)
        return 1

    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        return 1

    # For now, just print status - orchestrator.py will be fully implemented
    # in SDLC-0031 (dependency of this ticket)
    print("Ralph Python CLI")
    print(f"PRD:          {prd_path}")
    print(f"Plan:         {plan_path}")
    print(f"Dry run:      {dry_run}")
    print(f"Max attempts: {max_attempts}")
    print(f"Verbose:      {verbose}")

    if dry_run:
        print("\n[DRY RUN] Would process tickets from plan")
        return 0

    # Placeholder for actual orchestrator invocation
    # TODO: Import and call orchestrator.run() once SDLC-0031 is complete
    print("\n[INFO] Orchestrator not yet implemented - see SDLC-0031")
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    The parser supports two usage patterns:
    1. Direct: ralph <prd> <plan> [options] - runs the orchestrator (handled by main())
    2. Subcommands: ralph status|reset|run <args>

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="ralph",
        description="Ralph - Automated workflow orchestrator for PRD/plan execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ralph docs/prd.md docs/plan.md              # Run full workflow
    ralph docs/prd.md docs/plan.md --dry-run    # Preview without execution
    ralph status state.json                      # Check workflow status
    ralph reset TASK-123 --state-file state.json # Reset blocked ticket
        """,
    )

    # Create subparsers for explicit commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'run' subcommand (explicit version of default behavior)
    run_parser = subparsers.add_parser(
        "run",
        help="Run the orchestrator loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
        "--verbose",
        "-v",
        action="store_true",
        help="Show debug output and stack traces",
    )

    # 'status' subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Show workflow status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.add_argument("state_file", type=Path, help="Path to state file")

    # 'reset' subcommand
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset a blocked ticket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    reset_parser.add_argument("ticket_id", help="Ticket ID to reset (e.g., TASK-123)")
    reset_parser.add_argument(
        "--state-file",
        type=Path,
        required=False,
        help="Path to state file (default: docs/state/workflow.json)",
    )
    reset_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show debug output and stack traces",
    )

    # Top-level optional flags (for direct invocation pattern)
    # Note: positional args for direct invocation are handled in main() by
    # prepending 'run' when detecting file path arguments
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without invoking Claude",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum retry attempts per ticket (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show debug output and stack traces",
    )

    return parser


def _handle_status(args: argparse.Namespace, verbose: bool = False) -> int:
    """Handle the status command.

    Args:
        args: Parsed arguments containing state_file
        verbose: Whether to show detailed output

    Returns:
        Exit code (0 for success)
    """
    try:
        output = display_status(args.state_file)
        print(output)
        return 0
    except Exception as e:
        print(f"Error reading status: {e}", file=sys.stderr)
        if verbose:
            traceback.print_exc()
        return 1


def _handle_reset(args: argparse.Namespace, verbose: bool = False) -> int:
    """Handle the reset command.

    Args:
        args: Parsed arguments containing ticket_id and state_file
        verbose: Whether to show detailed output

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    state_file = getattr(args, "state_file", None)
    if state_file is None:
        # Default state file location
        state_file = Path("docs/state/workflow.json")

    try:
        result = reset_ticket(args.ticket_id, state_file)
        print(f"Successfully reset ticket {result.ticket_id}")
        print(f"  Previous status: {result.previous_status}")
        print(f"  New status:      {result.new_status}")
        if result.state_cleaned:
            print("  State files cleaned")
        return 0
    except TicketResetError as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if verbose:
            traceback.print_exc()
        return 1


def _handle_run(args: argparse.Namespace) -> int:
    """Handle the run command (explicit or implicit).

    Args:
        args: Parsed arguments containing prd, plan, and options

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    verbose = getattr(args, "verbose", False)

    try:
        return run_orchestrator(
            prd_path=args.prd,
            plan_path=args.plan,
            dry_run=getattr(args, "dry_run", False),
            max_attempts=getattr(args, "max_attempts", 3),
            verbose=verbose,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            traceback.print_exc()
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main entry point for Ralph CLI.

    Parses command-line arguments and dispatches to appropriate handlers:
    - No subcommand + prd/plan: Run orchestrator (auto-prepends 'run')
    - 'run' subcommand: Run orchestrator
    - 'status' subcommand: Display workflow status
    - 'reset' subcommand: Reset blocked ticket

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()

    # Handle the case where first arg looks like a file path (backward compat)
    if argv is None:
        argv = sys.argv[1:]

    # Make a mutable copy
    argv = list(argv)

    # Check if first argument is a file path (not a subcommand)
    # This enables: ralph docs/prd.md docs/plan.md
    if argv and not argv[0].startswith("-") and argv[0] not in ("run", "status", "reset"):
        # Check if it looks like a file path
        if "/" in argv[0] or argv[0].endswith(".md"):
            # Insert 'run' subcommand to handle it properly
            argv = ["run"] + argv

    args = parser.parse_args(argv)
    verbose = getattr(args, "verbose", False)

    # Route to appropriate handler based on command
    if args.command == "status":
        return _handle_status(args, verbose)
    elif args.command == "reset":
        return _handle_reset(args, verbose)
    elif args.command == "run":
        return _handle_run(args)
    else:
        # No command and no files specified - show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
