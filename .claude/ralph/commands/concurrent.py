"""Concurrent loop orchestration for Ralph.

This module manages git worktrees, .env files, parallel subprocess
launching, monitoring, and consolidated summaries for running multiple
Ralph instances in parallel. It provides:

- WorktreeManager: Create, update, list, and manage .git-worktrees/ralph-N directories
- EnvSyncer: .env file synchronization with RALPH_LABEL preservation
- LoopLauncher: Parallel subprocess management for Ralph loops
- LaunchResult: Dataclass holding per-process launch metadata
- CompletionResult: Dataclass holding per-process completion data
- LoopMonitor: Progress tracking, stall detection, and process polling
- LoopProgress: Dataclass holding per-loop progress snapshot
- StalledLoopWarning: Dataclass holding stall detection details
- ConsolidatedSummary: Generates per-loop and aggregate summary reports
- LoopSummary: Dataclass holding per-loop summary statistics
- SummaryReport: Dataclass holding the full consolidated summary
- ConcurrentRunResult: Dataclass holding full concurrent run outcome
- run_concurrent_loops: Full lifecycle integration function
- LaunchError: Raised when subprocess startup fails
- DirtyWorktreeError: Raised when a worktree has uncommitted changes
- WorktreeError: Raised when git worktree operations fail

Example:
    >>> from commands.concurrent import WorktreeManager, EnvSyncer
    >>> manager = WorktreeManager(project_root=Path("/path/to/project"))
    >>> manager.ensure_worktrees(count=3, default_branch="develop-working")
    >>> syncer = EnvSyncer()
    >>> syncer.sync_env(Path(".env"), Path(".git-worktrees/ralph-1"), "ralph-1")
    >>> launcher = LoopLauncher(project_root=Path("/path/to/project"))
    >>> results = launcher.launch(3, prd_path, plan_path, worktree_paths)
    >>> monitor = LoopMonitor()
    >>> completions = monitor.monitor(results)
    >>> summary_gen = ConsolidatedSummary()
    >>> report = summary_gen.generate(completions)
    >>> print(summary_gen.format_report(report))
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory name for worktrees inside project root
WORKTREES_DIR_NAME = ".git-worktrees"


class WorktreeError(Exception):
    """Raised when a git worktree operation fails.

    Attributes:
        message: Human-readable error message.
        worktree_name: Name of the worktree involved (if applicable).
        stderr: Standard error output from the git command.
    """

    def __init__(
        self,
        message: str,
        worktree_name: str | None = None,
        stderr: str | None = None,
    ) -> None:
        self.worktree_name = worktree_name
        self.stderr = stderr
        parts = [message]
        if worktree_name:
            parts.append(f"worktree={worktree_name}")
        if stderr:
            parts.append(stderr.strip())
        super().__init__(": ".join(parts))


class DirtyWorktreeError(WorktreeError):
    """Raised when a worktree has uncommitted changes.

    This signals that the worktree cannot be safely updated. The caller
    should warn the user and offer a resolution path (not silently discard).

    Attributes:
        worktree_path: Path to the dirty worktree.
        dirty_files: List of dirty file paths.
    """

    def __init__(
        self,
        worktree_path: Path,
        dirty_files: list[str] | None = None,
    ) -> None:
        self.worktree_path = worktree_path
        self.dirty_files = dirty_files or []
        name = worktree_path.name
        file_list = ", ".join(self.dirty_files[:5])
        if len(self.dirty_files) > 5:
            file_list += f" (and {len(self.dirty_files) - 5} more)"
        msg = (
            f"Worktree '{name}' has uncommitted changes: {file_list}. "
            f"Resolve manually before updating (e.g., git -C {worktree_path} reset --hard)."
        )
        super().__init__(msg, worktree_name=name)


@dataclass
class WorktreeInfo:
    """Information about an existing worktree.

    Attributes:
        name: Worktree name (e.g., "ralph-1").
        path: Absolute path to the worktree directory.
        is_valid: True if the worktree has a .git marker file.
    """

    name: str
    path: Path
    is_valid: bool


class WorktreeManager:
    """Manages git worktrees for concurrent Ralph instances.

    Worktrees are stored in {project_root}/.git-worktrees/ralph-{N}.
    The main project directory is always ralph-0 (no worktree created for it).

    Args:
        project_root: Absolute path to the project root directory.
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    @property
    def base_dir(self) -> Path:
        """Base directory for all worktrees."""
        return self._project_root / WORKTREES_DIR_NAME

    def worktree_path(self, name: str) -> Path:
        """Compute the absolute path for a named worktree.

        Args:
            name: Worktree name (e.g., "ralph-1").

        Returns:
            Absolute path to the worktree directory.
        """
        return self.base_dir / name

    def worktree_names(self, count: int) -> list[str]:
        """Generate worktree names for the given count.

        Names follow the pattern ralph-1 through ralph-N.
        ralph-0 is never included (the main directory is ralph-0).

        Args:
            count: Number of worktree names to generate.

        Returns:
            List of worktree names.
        """
        return [f"ralph-{i}" for i in range(1, count + 1)]

    def worktree_exists(self, name: str) -> bool:
        """Check if a named worktree exists and is valid.

        A valid worktree has a directory with a .git marker file.

        Args:
            name: Worktree name (e.g., "ralph-1").

        Returns:
            True if the worktree exists and has a .git marker.
        """
        wt_path = self.worktree_path(name)
        return wt_path.is_dir() and (wt_path / ".git").exists()

    def is_dirty(self, worktree_path: Path) -> bool:
        """Check if a worktree has uncommitted changes.

        Runs git status --porcelain in the worktree directory and returns
        True if there is any output (meaning uncommitted changes exist).

        Args:
            worktree_path: Absolute path to the worktree directory.

        Returns:
            True if the worktree has uncommitted changes.
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )
        return bool(result.stdout.strip())

    def list_worktrees(self) -> list[str]:
        """List all existing Ralph worktrees.

        Scans .git-worktrees/ for directories matching the ralph-N pattern
        that have a .git marker file (indicating a valid git worktree).

        Returns:
            Sorted list of worktree names (e.g., ["ralph-1", "ralph-2"]).
        """
        if not self.base_dir.exists():
            return []

        pattern = re.compile(r"^ralph-\d+$")
        results = []

        for entry in self.base_dir.iterdir():
            if (
                entry.is_dir()
                and pattern.match(entry.name)
                and (entry / ".git").exists()
            ):
                results.append(entry.name)

        return sorted(results)

    def ensure_worktrees(
        self,
        count: int,
        default_branch: str,
    ) -> list[Path]:
        """Create or update worktrees to match the requested count.

        For each worktree ralph-1 through ralph-N:
        - If it doesn't exist: create it from origin/{default_branch}
        - If it exists and is clean: update it (fetch + reset)
        - If it exists and is dirty: raise DirtyWorktreeError

        Always fetches origin before creating/updating worktrees.

        Args:
            count: Number of worktrees to ensure (ralph-1 through ralph-N).
            default_branch: Default branch name (e.g., "develop-working").

        Returns:
            List of paths to the ensured worktrees.

        Raises:
            DirtyWorktreeError: If any existing worktree has uncommitted changes.
            WorktreeError: If git worktree operations fail.
        """
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Fetch latest from origin
        self._fetch_origin()

        names = self.worktree_names(count)
        paths = []

        for name in names:
            wt_path = self.worktree_path(name)

            if self.worktree_exists(name):
                # Existing worktree -- update it
                self.update_worktree(wt_path, default_branch)
            else:
                # New worktree -- create it
                self._create_worktree(name, default_branch)

            paths.append(wt_path)

        return paths

    def update_worktree(
        self,
        worktree_path: Path,
        default_branch: str,
    ) -> None:
        """Update an existing worktree to the latest default branch.

        Checks for dirty state first. If dirty, raises DirtyWorktreeError.
        If clean, resets the worktree to origin/{default_branch}.

        Args:
            worktree_path: Absolute path to the worktree directory.
            default_branch: Default branch name (e.g., "develop-working").

        Raises:
            DirtyWorktreeError: If the worktree has uncommitted changes.
            WorktreeError: If git operations fail.
        """
        # Check for dirty state first
        if self.is_dirty(worktree_path):
            dirty_files = self._get_dirty_files(worktree_path)
            raise DirtyWorktreeError(worktree_path, dirty_files)

        # Fetch latest (in case not already done)
        self._fetch_in_worktree(worktree_path)

        # Reset to origin/{default_branch}
        ref = f"origin/{default_branch}"
        result = subprocess.run(
            ["git", "reset", "--hard", ref],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to reset worktree to {ref}",
                worktree_name=worktree_path.name,
                stderr=result.stderr,
            )

        logger.info("Updated worktree %s to %s", worktree_path.name, ref)

    def _create_worktree(self, name: str, default_branch: str) -> None:
        """Create a new git worktree.

        Creates a worktree at .git-worktrees/{name} checked out at
        origin/{default_branch}. Uses detached HEAD to avoid branch conflicts.

        Args:
            name: Worktree name (e.g., "ralph-1").
            default_branch: Default branch name.

        Raises:
            WorktreeError: If git worktree add fails.
        """
        wt_path = str(self.worktree_path(name))
        ref = f"origin/{default_branch}"

        result = subprocess.run(
            ["git", "worktree", "add", "--detach", wt_path, ref],
            capture_output=True,
            text=True,
            cwd=self._project_root,
        )

        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to create worktree '{name}'",
                worktree_name=name,
                stderr=result.stderr,
            )

        logger.info("Created worktree %s at %s", name, ref)

    def _fetch_origin(self) -> None:
        """Fetch latest from origin in the project root.

        Raises:
            WorktreeError: If git fetch fails.
        """
        result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=self._project_root,
        )
        if result.returncode != 0:
            raise WorktreeError(
                "Failed to fetch from origin",
                stderr=result.stderr,
            )

    def _fetch_in_worktree(self, worktree_path: Path) -> None:
        """Fetch latest from origin within a worktree.

        Args:
            worktree_path: Path to the worktree directory.

        Raises:
            WorktreeError: If git fetch fails.
        """
        result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )
        if result.returncode != 0:
            raise WorktreeError(
                "Failed to fetch origin in worktree",
                worktree_name=worktree_path.name,
                stderr=result.stderr,
            )

    def _get_dirty_files(self, worktree_path: Path) -> list[str]:
        """Get list of dirty files in a worktree.

        Args:
            worktree_path: Path to the worktree directory.

        Returns:
            List of dirty file paths.
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=worktree_path,
        )
        files = []
        for line in result.stdout.splitlines():
            if len(line) >= 3:
                files.append(line[3:].strip())
        return files


# Key that identifies a Ralph instance; never propagated from root .env
RALPH_LABEL_KEY = "RALPH_LABEL"


class EnvSyncer:
    """Synchronizes .env files between the project root and worktrees.

    The root .env is the single source of truth for all configuration
    variables. Each worktree gets a copy of the root .env with one
    exception: the RALPH_LABEL variable is set per-worktree (e.g.,
    ``ralph-1``, ``ralph-2``) and is never overwritten from the root.

    The root .env is only ever read -- it is never modified by this class.

    Example:
        >>> syncer = EnvSyncer()
        >>> syncer.sync_env(Path(".env"), Path(".git-worktrees/ralph-1"), "ralph-1")
    """

    # ------------------------------------------------------------------
    # Static helpers: parse / merge / write
    # ------------------------------------------------------------------

    @staticmethod
    def parse_env(env_path: Path) -> dict[str, str]:
        """Parse a .env file into an ordered dictionary.

        Handles:
        - ``KEY=VALUE`` and ``KEY="VALUE"`` and ``KEY='VALUE'``
        - ``export KEY=VALUE`` prefix
        - Comment lines (starting with ``#``)
        - Blank lines
        - Inline comments for unquoted values (``KEY=val # comment``)
        - Values containing ``=`` (only the first ``=`` splits key/value)
        - Whitespace around keys and values

        Args:
            env_path: Path to the .env file. If the file does not exist,
                returns an empty dict.

        Returns:
            Ordered dict of environment variable names to their values.
        """
        if not env_path.exists():
            return {}

        variables: dict[str, str] = {}

        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()

            # Skip blanks and comments
            if not line or line.startswith("#"):
                continue

            # Strip optional ``export `` prefix
            if line.startswith("export "):
                line = line[len("export "):]

            # Split on the first ``=``
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            # Handle quoted values
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ('"', "'")
            ):
                value = value[1:-1]
            else:
                # Strip inline comments from unquoted values
                # (only when there is `` # `` with a space before the #)
                comment_idx = value.find(" #")
                if comment_idx != -1:
                    value = value[:comment_idx].rstrip()

            variables[key] = value

        return variables

    @staticmethod
    def write_env(env_path: Path, variables: dict[str, str]) -> None:
        """Write an ordered dictionary to a .env file.

        Values containing spaces are wrapped in double quotes. All other
        values are written bare. The file ends with a trailing newline.

        Args:
            env_path: Path to write the .env file.
            variables: Ordered dict of environment variables.
        """
        lines: list[str] = []
        for key, value in variables.items():
            if " " in value:
                lines.append(f'{key}="{value}"')
            else:
                lines.append(f"{key}={value}")

        content = "\n".join(lines)
        if lines:
            content += "\n"
        env_path.write_text(content)

    @staticmethod
    def merge_env(
        root_vars: dict[str, str],
        worktree_vars: dict[str, str],
        ralph_label: str,
    ) -> dict[str, str]:
        """Merge root .env variables into a worktree .env.

        The root .env is the source of truth. All root variables are
        copied to the result, replacing any existing worktree values.
        The ``RALPH_LABEL`` key is always set to *ralph_label*,
        regardless of the root or worktree values.

        Worktree-only variables (not present in the root) are removed.
        The root's ``RALPH_LABEL`` is never propagated.

        Args:
            root_vars: Variables from the root .env.
            worktree_vars: Variables from the worktree .env (used only
                for informational purposes; values are not preserved).
            ralph_label: Label to assign to this worktree (e.g., ``ralph-1``).

        Returns:
            Merged dict suitable for writing to the worktree .env.
        """
        merged: dict[str, str] = {}

        for key, value in root_vars.items():
            if key == RALPH_LABEL_KEY:
                continue  # Never propagate root's label
            merged[key] = value

        # Set the worktree's own label
        merged[RALPH_LABEL_KEY] = ralph_label

        return merged

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def sync_env(
        self,
        root_env_path: Path,
        worktree_path: Path,
        ralph_label: str,
    ) -> None:
        """Synchronize the root .env into a worktree directory.

        Reads the root .env, reads the worktree .env (if it exists),
        merges the two (root is source of truth, RALPH_LABEL preserved),
        and writes the result to the worktree's ``.env``.

        The root .env is **never modified**.

        Args:
            root_env_path: Absolute path to the root .env file.
            worktree_path: Absolute path to the worktree directory.
            ralph_label: Label to assign (e.g., ``ralph-1``).
        """
        root_vars = self.parse_env(root_env_path)

        wt_env_path = worktree_path / ".env"
        worktree_vars = self.parse_env(wt_env_path)

        merged = self.merge_env(root_vars, worktree_vars, ralph_label)
        self.write_env(wt_env_path, merged)

        logger.info(
            "Synced .env to %s (%d variables, RALPH_LABEL=%s)",
            worktree_path.name,
            len(merged),
            ralph_label,
        )


# ======================================================================
# Parallel Loop Launcher
# ======================================================================


class LaunchError(Exception):
    """Raised when a subprocess fails to start during launch.

    Attributes:
        label: Label of the Ralph instance that failed to start.
        cause: Original exception that caused the failure.
    """

    def __init__(self, label: str, cause: Exception) -> None:
        self.label = label
        self.cause = cause
        super().__init__(f"Failed to launch {label}: {cause}")


@dataclass
class LaunchResult:
    """Metadata for a launched Ralph subprocess.

    Attributes:
        process: The Popen process handle.
        label: Instance label (e.g., "ralph-0", "ralph-1").
        cwd: Working directory the process was started in.
        log_file: Path to the dedicated log file for this instance.
        start_time: When the process was launched.
    """

    process: Any  # subprocess.Popen, but typed as Any for test mockability
    label: str
    cwd: Path
    log_file: Path
    start_time: datetime


@dataclass
class CompletionResult:
    """Result of a completed Ralph subprocess.

    Attributes:
        label: Instance label (e.g., "ralph-0", "ralph-1").
        exit_code: Process exit code (0 = success, non-zero = failure).
        runtime_seconds: Wall-clock time in seconds from start to completion.
        log_file: Path to the log file for this instance.
    """

    label: str
    exit_code: int
    runtime_seconds: float
    log_file: Path


# Relative path from project root to the Ralph CLI entry point
_RALPH_CLI_RELATIVE = Path(".claude") / "ralph" / "ralph"


class LoopLauncher:
    """Launches parallel Ralph subprocesses.

    Each loop runs as a separate subprocess via ``subprocess.Popen``,
    executing ``.claude/ralph/ralph run <prd> <plan> --skip-preflight``
    with the appropriate ``cwd`` set to the project root (ralph-0) or
    worktree directory (ralph-1..N). Each subprocess writes stdout and
    stderr to a dedicated log file in ``tmp/``.

    The main project directory is always ralph-0. Worktrees are ralph-1
    through ralph-N. A 3-loop run = main dir + 2 worktrees.

    Args:
        project_root: Absolute path to the project root directory.
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    @property
    def tmp_dir(self) -> Path:
        """Directory for log files."""
        return self._project_root / "tmp"

    def log_file_path(self, label: str) -> Path:
        """Compute the log file path for a given instance label.

        Log files follow the pattern ``tmp/ralph-{N}-{YYYY-MM-DD}.log``.

        Args:
            label: Instance label (e.g., "ralph-0").

        Returns:
            Absolute path to the log file.
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.tmp_dir / f"{label}-{date_str}.log"

    def launch(
        self,
        count: int,
        prd_path: Path,
        plan_path: Path,
        worktree_paths: list[Path],
    ) -> list[LaunchResult]:
        """Start N Ralph subprocesses in parallel.

        ralph-0 runs in the project root directory.
        ralph-1 through ralph-N run in the provided worktree directories.

        Each subprocess executes:
        ``{cwd}/.claude/ralph/ralph run <prd> <plan> --skip-preflight``

        The ``--skip-preflight`` flag is included because the caller
        (the ``/ralph-loop`` command) runs preflight once before launching.

        Args:
            count: Total number of loops to launch (1 = ralph-0 only,
                2 = ralph-0 + ralph-1, etc.).
            prd_path: Path to the PRD document.
            plan_path: Path to the plan document.
            worktree_paths: Paths to worktree directories for ralph-1..N.
                Must have length ``count - 1``.

        Returns:
            List of LaunchResult objects, one per launched process.

        Raises:
            LaunchError: If any subprocess fails to start. Already-started
                processes are terminated before the error propagates.
        """
        # Ensure tmp/ exists for log files
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        # Build the list of (label, cwd) pairs
        instances: list[tuple[str, Path]] = [("ralph-0", self._project_root)]
        for i, wt_path in enumerate(worktree_paths, start=1):
            instances.append((f"ralph-{i}", wt_path))

        # Sanity check: we should have exactly `count` instances
        assert len(instances) == count, (
            f"Expected {count} instances but got {len(instances)}. "
            f"worktree_paths should have {count - 1} entries."
        )

        results: list[LaunchResult] = []

        for label, cwd in instances:
            log_path = self.log_file_path(label)

            # Build the command: {cwd}/.claude/ralph/ralph run <prd> <plan> --skip-preflight
            ralph_cli = cwd / _RALPH_CLI_RELATIVE
            cmd = [
                str(ralph_cli),
                "run",
                str(prd_path),
                str(plan_path),
                "--skip-preflight",
            ]

            try:
                log_handle = open(log_path, "w")
                proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except Exception as e:
                # Clean up already-started processes
                for r in results:
                    try:
                        r.process.terminate()
                    except Exception:
                        pass
                raise LaunchError(label, e) from e

            results.append(
                LaunchResult(
                    process=proc,
                    label=label,
                    cwd=cwd,
                    log_file=log_path,
                    start_time=datetime.now(),
                )
            )
            logger.info(
                "Launched %s (pid=%s) in %s, log=%s",
                label, proc.pid, cwd, log_path,
            )

        return results

    def wait_all(
        self,
        launch_results: list[LaunchResult],
    ) -> list[CompletionResult]:
        """Wait for all launched processes to complete.

        Calls ``process.wait()`` on each process sequentially. Does NOT
        terminate remaining processes when one crashes — all processes
        are allowed to finish independently.

        Args:
            launch_results: List of LaunchResult from ``launch()``.

        Returns:
            List of CompletionResult with exit codes and runtimes.
        """
        completions: list[CompletionResult] = []

        for lr in launch_results:
            exit_code = lr.process.wait()
            end_time = datetime.now()
            runtime = (end_time - lr.start_time).total_seconds()

            if exit_code != 0:
                logger.warning(
                    "Process %s exited with code %d after %.1fs",
                    lr.label, exit_code, runtime,
                )
            else:
                logger.info(
                    "Process %s completed successfully in %.1fs",
                    lr.label, runtime,
                )

            completions.append(
                CompletionResult(
                    label=lr.label,
                    exit_code=exit_code,
                    runtime_seconds=runtime,
                    log_file=lr.log_file,
                )
            )

        return completions


# ======================================================================
# Loop Monitor
# ======================================================================

# Regex patterns for parsing log files
_TICKET_COMPLETED_RE = re.compile(r"(\w+-\d+)\s+COMPLETED")
_TICKET_BLOCKED_RE = re.compile(r"(\w+-\d+)\s+BLOCKED")
_TICKET_CLAIMING_RE = re.compile(r"(?:Claiming|Working on)\s+(\w+-\d+)")

# Default number of tail lines to read from a log file
_DEFAULT_TAIL_LINES = 50


@dataclass
class LoopProgress:
    """Snapshot of a single loop's progress.

    Attributes:
        label: Instance label (e.g., "ralph-0").
        current_ticket: The ticket ID currently being worked on, or None.
        tickets_completed: Number of tickets completed so far.
        last_output_line: The last non-empty line from the log file.
    """

    label: str
    current_ticket: str | None
    tickets_completed: int
    last_output_line: str


@dataclass
class StalledLoopWarning:
    """Warning that a loop appears to have stalled.

    Attributes:
        label: Instance label of the stalled loop.
        log_file: Path to the loop's log file.
        last_modified: When the log file was last modified.
        minutes_stalled: How many minutes since the last log output.
    """

    label: str
    log_file: Path
    last_modified: datetime
    minutes_stalled: float


class LoopMonitor:
    """Monitors running Ralph loops and provides progress reporting.

    Periodically polls running processes, reads their log files for
    progress indicators (tickets completed, current ticket), and detects
    stalled loops (no log output for a configurable threshold).

    Args:
        poll_interval_seconds: Seconds between process polls during
            ``monitor()``. Default is 10 seconds.
    """

    def __init__(self, poll_interval_seconds: float = 10.0) -> None:
        self._poll_interval = poll_interval_seconds

    def check_progress(
        self,
        log_files: dict[str, Path],
    ) -> list[LoopProgress]:
        """Read the tail of each log file and report progress.

        Scans each log file for ticket completion markers (``COMPLETED``)
        and claiming markers (``Claiming``) to determine how many tickets
        have been completed and what is currently being worked on.

        Args:
            log_files: Map of instance label to log file path.

        Returns:
            List of LoopProgress snapshots, one per log file.
        """
        progress_list: list[LoopProgress] = []

        for label, log_path in log_files.items():
            completed = 0
            current_ticket: str | None = None
            last_line = ""

            if log_path.exists():
                content = log_path.read_text()
                lines = content.splitlines()

                # Count completed tickets (scan full file)
                for line in lines:
                    match = _TICKET_COMPLETED_RE.search(line)
                    if match:
                        completed += 1

                # Build set of completed ticket IDs
                completed_ids: set[str] = set()
                for cline in lines:
                    cmatch = _TICKET_COMPLETED_RE.search(cline)
                    if cmatch:
                        completed_ids.add(cmatch.group(1))

                # Find current ticket from the most recent claiming line
                for line in reversed(lines):
                    match = _TICKET_CLAIMING_RE.search(line)
                    if match:
                        candidate = match.group(1)
                        if candidate not in completed_ids:
                            current_ticket = candidate
                        break

                # Get last non-empty line
                for line in reversed(lines):
                    stripped = line.strip()
                    if stripped:
                        last_line = stripped
                        break

            progress_list.append(
                LoopProgress(
                    label=label,
                    current_ticket=current_ticket,
                    tickets_completed=completed,
                    last_output_line=last_line,
                )
            )

        return progress_list

    def detect_stalled(
        self,
        log_files: dict[str, Path],
        threshold_minutes: float = 30.0,
    ) -> list[StalledLoopWarning]:
        """Detect loops that appear to have stalled.

        A loop is considered stalled if its log file has not been modified
        for longer than ``threshold_minutes``. Missing log files are
        silently skipped.

        Args:
            log_files: Map of instance label to log file path.
            threshold_minutes: Minutes of inactivity before flagging.

        Returns:
            List of StalledLoopWarning for stalled loops.
        """
        warnings: list[StalledLoopWarning] = []
        now = time.time()

        for label, log_path in log_files.items():
            if not log_path.exists():
                continue

            mtime = os.path.getmtime(log_path)
            elapsed_minutes = (now - mtime) / 60.0

            if elapsed_minutes > threshold_minutes:
                warnings.append(
                    StalledLoopWarning(
                        label=label,
                        log_file=log_path,
                        last_modified=datetime.fromtimestamp(mtime),
                        minutes_stalled=elapsed_minutes,
                    )
                )

        return warnings

    def monitor(
        self,
        launch_results: list[LaunchResult],
    ) -> list[CompletionResult]:
        """Poll all processes until they complete.

        This is the main monitoring loop. It polls each process's
        ``poll()`` method to check completion, sleeping between polls.
        When all processes have finished, it returns CompletionResult
        objects for each.

        Unlike ``LoopLauncher.wait_all()`` which blocks on each
        process sequentially, this method polls all processes and can
        detect stalls and report progress during execution.

        Args:
            launch_results: List of LaunchResult from the launcher.

        Returns:
            List of CompletionResult with exit codes and runtimes.
        """
        pending = {lr.label: lr for lr in launch_results}
        completions: list[CompletionResult] = []

        while pending:
            finished_labels: list[str] = []

            for label, lr in pending.items():
                exit_code = lr.process.poll()
                if exit_code is not None:
                    end_time = datetime.now()
                    runtime = (end_time - lr.start_time).total_seconds()

                    if exit_code != 0:
                        logger.warning(
                            "Process %s exited with code %d after %.1fs",
                            label, exit_code, runtime,
                        )
                    else:
                        logger.info(
                            "Process %s completed successfully in %.1fs",
                            label, runtime,
                        )

                    completions.append(
                        CompletionResult(
                            label=label,
                            exit_code=exit_code,
                            runtime_seconds=runtime,
                            log_file=lr.log_file,
                        )
                    )
                    finished_labels.append(label)

            for label in finished_labels:
                del pending[label]

            if pending:
                time.sleep(self._poll_interval)

        return completions


# ======================================================================
# Consolidated Summary
# ======================================================================


@dataclass
class LoopSummary:
    """Per-loop summary statistics.

    Attributes:
        label: Instance label (e.g., "ralph-0").
        completed_count: Number of tickets completed by this loop.
        blocked_count: Number of tickets blocked in this loop.
        exit_code: Process exit code (0 = success).
        wall_clock_seconds: Wall-clock runtime in seconds.
    """

    label: str
    completed_count: int
    blocked_count: int
    exit_code: int
    wall_clock_seconds: float


@dataclass
class SummaryReport:
    """Consolidated summary of all loops.

    Attributes:
        loop_summaries: Per-loop statistics.
        total_completed: Aggregate completed ticket count.
        total_blocked: Aggregate blocked ticket count.
        overall_wall_clock_seconds: Overall wall-clock time (max of
            all per-loop runtimes, since loops run in parallel).
    """

    loop_summaries: list[LoopSummary]
    total_completed: int
    total_blocked: int
    overall_wall_clock_seconds: float


class ConsolidatedSummary:
    """Generates a consolidated summary from loop completion results.

    Parses each loop's log file to count completed and blocked tickets,
    then aggregates across all loops.

    Example:
        >>> gen = ConsolidatedSummary()
        >>> report = gen.generate(completions)
        >>> print(gen.format_report(report))
    """

    def generate(
        self,
        completions: list[CompletionResult],
    ) -> SummaryReport:
        """Generate a consolidated summary from completion results.

        For each completion, reads the log file and counts ticket
        completion and blocked markers. Produces per-loop and aggregate
        statistics.

        Args:
            completions: List of CompletionResult from the monitor.

        Returns:
            SummaryReport with per-loop and aggregate statistics.
        """
        loop_summaries: list[LoopSummary] = []
        total_completed = 0
        total_blocked = 0
        max_runtime = 0.0

        for cr in completions:
            completed = 0
            blocked = 0

            if cr.log_file.exists():
                content = cr.log_file.read_text()
                for line in content.splitlines():
                    if _TICKET_COMPLETED_RE.search(line):
                        completed += 1
                    if _TICKET_BLOCKED_RE.search(line):
                        blocked += 1

            loop_summaries.append(
                LoopSummary(
                    label=cr.label,
                    completed_count=completed,
                    blocked_count=blocked,
                    exit_code=cr.exit_code,
                    wall_clock_seconds=cr.runtime_seconds,
                )
            )

            total_completed += completed
            total_blocked += blocked
            max_runtime = max(max_runtime, cr.runtime_seconds)

        return SummaryReport(
            loop_summaries=loop_summaries,
            total_completed=total_completed,
            total_blocked=total_blocked,
            overall_wall_clock_seconds=max_runtime,
        )

    @staticmethod
    def format_report(report: SummaryReport) -> str:
        """Format a SummaryReport as human-readable text.

        Produces a multi-line string suitable for logging or display,
        including per-loop statistics and aggregate totals.

        Args:
            report: The SummaryReport to format.

        Returns:
            Human-readable summary string.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("CONSOLIDATED SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        for ls in report.loop_summaries:
            minutes = ls.wall_clock_seconds / 60.0
            status = "OK" if ls.exit_code == 0 else f"CRASHED (exit {ls.exit_code})"
            lines.append(
                f"  {ls.label}: {ls.completed_count} completed, "
                f"{ls.blocked_count} blocked, "
                f"{minutes:.1f} min [{status}]"
            )

        lines.append("")
        lines.append("-" * 60)
        overall_minutes = report.overall_wall_clock_seconds / 60.0
        lines.append(f"  Total completed: {report.total_completed}")
        lines.append(f"  Total blocked:   {report.total_blocked}")
        lines.append(f"  Overall time:    {overall_minutes:.1f} min")
        lines.append("=" * 60)

        return "\n".join(lines)


# ======================================================================
# Integration Functions
# ======================================================================


@dataclass
class ConcurrentRunResult:
    """Result of a full concurrent loop run.

    Attributes:
        summary_report: The consolidated summary from all loops.
        formatted_summary: Human-readable formatted summary text.
        worktree_paths: Paths to worktrees used (empty for single-loop).
        cleanup_warnings: Warnings from post-loop cleanup (e.g., dirty
            worktrees that could not be reset).
    """

    summary_report: SummaryReport
    formatted_summary: str
    worktree_paths: list[Path]
    cleanup_warnings: list[str]

    @property
    def total_completed(self) -> int:
        """Shorthand for summary_report.total_completed."""
        return self.summary_report.total_completed

    @property
    def total_blocked(self) -> int:
        """Shorthand for summary_report.total_blocked."""
        return self.summary_report.total_blocked


def run_concurrent_loops(
    project_root: Path,
    prd_path: Path,
    plan_path: Path,
    loop_count: int,
    default_branch: str,
) -> ConcurrentRunResult:
    """Run the full concurrent loop lifecycle.

    This is the main integration function that ties together all
    concurrent orchestration components:

    1. If loop_count > 1: create/update worktrees, sync .env files
    2. Launch loop_count Ralph subprocesses
    3. Monitor all processes until completion
    4. Generate consolidated summary
    5. Post-loop cleanup: reset worktrees to origin/{default_branch}

    For loop_count == 1: skips worktree setup entirely. The single
    loop runs in the project root directory.

    Args:
        project_root: Absolute path to the project root directory.
        prd_path: Path to the PRD document.
        plan_path: Path to the plan document.
        loop_count: Number of concurrent loops to run (1-4).
        default_branch: Default branch name for worktree operations.

    Returns:
        ConcurrentRunResult with summary and cleanup info.
    """
    worktree_paths: list[Path] = []
    cleanup_warnings: list[str] = []

    # Step 1: Worktree and .env setup (only for multi-loop)
    if loop_count > 1:
        worktree_count = loop_count - 1  # main dir is ralph-0

        wt_manager = WorktreeManager(project_root)
        worktree_paths = wt_manager.ensure_worktrees(
            count=worktree_count,
            default_branch=default_branch,
        )

        # Sync .env to each worktree
        env_syncer = EnvSyncer()
        root_env_path = project_root / ".env"

        for i, wt_path in enumerate(worktree_paths, start=1):
            label = f"ralph-{i}"
            env_syncer.sync_env(root_env_path, wt_path, label)

    # Step 2: Launch loops
    launcher = LoopLauncher(project_root)
    launch_results = launcher.launch(
        count=loop_count,
        prd_path=prd_path,
        plan_path=plan_path,
        worktree_paths=worktree_paths,
    )

    # Step 3: Monitor until all complete
    monitor = LoopMonitor()
    completions = monitor.monitor(launch_results)

    # Step 4: Generate consolidated summary
    summary_gen = ConsolidatedSummary()
    report = summary_gen.generate(completions)
    formatted = summary_gen.format_report(report)

    # Step 5: Post-loop cleanup — reset worktrees to default branch
    if worktree_paths:
        wt_manager = WorktreeManager(project_root)
        for wt_path in worktree_paths:
            try:
                wt_manager.update_worktree(wt_path, default_branch)
            except DirtyWorktreeError as e:
                warning = (
                    f"{wt_path.name} has dirty state after loop completion: {e}. "
                    f"Worktree was not reset."
                )
                logger.warning(warning)
                cleanup_warnings.append(warning)
            except WorktreeError as e:
                warning = f"Failed to reset {wt_path.name}: {e}"
                logger.warning(warning)
                cleanup_warnings.append(warning)

    return ConcurrentRunResult(
        summary_report=report,
        formatted_summary=formatted,
        worktree_paths=worktree_paths,
        cleanup_warnings=cleanup_warnings,
    )
