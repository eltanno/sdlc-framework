#!/usr/bin/env python3
"""Ralph CLI entry point.

This module provides the command-line interface for Ralph, the automated
workflow orchestrator. It parses arguments and delegates to the appropriate
command modules.

Usage:
    ralph <prd-path> <plan-path> [options]
    ralph status <state-file>
    ralph reset <ticket-id>

Options:
    --dry-run           Preview without invoking Claude
    --max-attempts N    Max retries per ticket (default: 3)
    --verbose           Show debug output and stack traces
    --help              Show help message
"""

import argparse
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
    ralph docs/prd.md docs/plan.md              # Run full workflow
    ralph docs/prd.md docs/plan.md --dry-run    # Preview without execution
    ralph status state.json                      # Check workflow status
    ralph reset TASK-123                         # Reset blocked ticket
        """,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Main orchestrator (default)
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

    # Also support positional args for backward compatibility
    parser.add_argument("prd", nargs="?", type=Path, help="Path to PRD document")
    parser.add_argument("plan", nargs="?", type=Path, help="Path to plan document")
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
        "--verbose", "-v",
        action="store_true",
        help="Show debug output and stack traces",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for Ralph CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Placeholder - actual implementation in future tickets
    print("Ralph Python CLI - Package structure validated")
    print(f"Arguments: {args}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
