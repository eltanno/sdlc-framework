"""Configuration loading and management for Ralph orchestrator.

This module handles loading and parsing YAML configuration files and
environment variables, providing typed access to configuration values.

Replaces: .claude/scripts/ralph/config-helpers.sh

Example:
    >>> from core.config import load_config
    >>> config = load_config(Path("config.yaml"))
    >>> print(config.ralph.instance_label_prefix)
    'ralph-'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Valid PM tool types
VALID_PM_TOOLS: frozenset[str] = frozenset({"github", "trello", "asana", "none"})

# Valid repository tool types
VALID_REPO_TOOLS: frozenset[str] = frozenset({"github", "gitlab"})


class ConfigError(Exception):
    """Raised when configuration loading or validation fails.

    Attributes:
        file_path: Path to the config file that caused the error.
        message: Human-readable error message.
    """

    def __init__(self, message: str, file_path: Path | None = None) -> None:
        self.file_path = file_path
        self.message = message
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.file_path:
            return f"{self.file_path}: {self.message}"
        return self.message


@dataclass
class Codebase:
    """Configuration for a single codebase in a monorepo.

    Attributes:
        name: Name identifier for the codebase (e.g., "mobile", "backend")
        path: Relative path from project root to codebase directory
        typecheck_command: Command to run type checking (empty string if not configured)
        lint_command: Command to run linting (empty string if not configured)
        test_command: Command to run tests (empty string if not configured)
        build_command: Command to run build (empty string if not configured)
    """

    name: str
    path: str
    typecheck_command: str = ""
    lint_command: str = ""
    test_command: str = ""
    build_command: str = ""


@dataclass
class RalphConfig:
    """Configuration settings for the Ralph orchestrator.

    Attributes:
        instance_label_prefix: Prefix for instance labels (default: "ralph-").
        use_assignee: Whether to use GitHub issue assignment (default: True).
        sonnet_threshold: Complexity threshold for model selection (default: 2).
        max_attempts: Maximum retry attempts per ticket (default: 3).
        state_directory: Directory for state files (default: "docs/state").
        keep_state_files: Whether to keep state files as audit trail (default: True).
        validator_model: Model for validation analysis (default: "sonnet").
        engineer_timeout: Timeout in minutes for engineer (default: 30).
        validator_timeout: Timeout in minutes for validator (default: 10).
        review_model: Model for post-loop batch review in /execution-report (default: "opus").
            Opus is justified as final safety net for batch-level review.
        review_timeout: Timeout in minutes for post-loop review (default: 5).
        max_concurrent_loops: Maximum parallel Ralph instances (1-4, default: 4).
    """

    instance_label_prefix: str = "ralph-"
    use_assignee: bool = True
    sonnet_threshold: int = 2
    max_attempts: int = 3
    state_directory: str = "docs/state"
    keep_state_files: bool = True
    validator_model: str = "sonnet"
    engineer_timeout: int = 30
    validator_timeout: int = 10
    review_model: str = "opus"
    review_timeout: int = 5
    max_concurrent_loops: int = 4


@dataclass
class Config:
    """Top-level configuration container.

    Supports both Ralph orchestrator settings and validation configuration.
    For validation, supports both single-codebase and monorepo configurations.

    Attributes:
        ralph: Ralph-specific configuration settings.
        typecheck_command: Type checking command (single-codebase mode).
        lint_command: Linting command (single-codebase mode).
        test_command: Test command (single-codebase mode).
        build_command: Build command (single-codebase mode).
        is_monorepo: True if dev.codebases section exists.
        codebases: List of Codebase configs (empty for single-codebase).
    """

    ralph: RalphConfig = field(default_factory=RalphConfig)
    typecheck_command: str = ""
    lint_command: str = ""
    test_command: str = ""
    build_command: str = ""
    is_monorepo: bool = False
    codebases: list[Codebase] = field(default_factory=list)


def load_config(config_path: str | Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Config object with all configuration values.

    Raises:
        ConfigError: If the file is missing or contains invalid YAML.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(
            f"Configuration file not found: {path}",
            file_path=path
        )

    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        raise ConfigError(
            f"Failed to parse YAML: {e}",
            file_path=path
        ) from e

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration dictionary into Config object.

    Args:
        data: Raw configuration dictionary from YAML.

    Returns:
        Config object with defaults applied for missing values.
    """
    # Parse Ralph orchestrator settings
    ralph_data = data.get("ralph", {}) or {}

    ralph_config = RalphConfig(
        instance_label_prefix=ralph_data.get("instance_label_prefix", "ralph-"),
        use_assignee=ralph_data.get("use_assignee", True),
        sonnet_threshold=ralph_data.get("sonnet_threshold", 2),
        max_attempts=ralph_data.get("max_attempts", 3),
        state_directory=ralph_data.get("state_directory", "docs/state"),
        keep_state_files=ralph_data.get("keep_state_files", True),
        validator_model=ralph_data.get("validator_model", "sonnet"),
        engineer_timeout=ralph_data.get("engineer_timeout", 30),
        validator_timeout=ralph_data.get("validator_timeout", 10),
        review_model=ralph_data.get("review_model", "opus"),
        review_timeout=ralph_data.get("review_timeout", 5),
        max_concurrent_loops=ralph_data.get("max_concurrent_loops", 4),
    )

    # Parse validation settings from dev section
    dev_data = data.get("dev", {}) or {}

    # Check for monorepo configuration
    codebases_data = dev_data.get("codebases", []) or []
    is_monorepo = len(codebases_data) > 0

    codebases = []
    if isinstance(codebases_data, dict):
        # YAML mapping format: {backend: {path: ..., ...}, frontend: {...}}
        for name, cb in codebases_data.items():
            cb = cb or {}
            codebases.append(Codebase(
                name=name,
                path=cb.get("path", ""),
                typecheck_command=cb.get("typecheck_command", cb.get("typecheck", "")),
                lint_command=cb.get("lint_command", cb.get("lint", "")),
                test_command=cb.get("test_command", cb.get("test", "")),
                build_command=cb.get("build_command", cb.get("build", "")),
            ))
    else:
        # List format: [{name: backend, path: ..., ...}, ...]
        for cb in codebases_data:
            codebases.append(Codebase(
                name=cb.get("name", ""),
                path=cb.get("path", ""),
                typecheck_command=cb.get("typecheck_command", cb.get("typecheck", "")),
                lint_command=cb.get("lint_command", cb.get("lint", "")),
                test_command=cb.get("test_command", cb.get("test", "")),
                build_command=cb.get("build_command", cb.get("build", "")),
            ))

    return Config(
        ralph=ralph_config,
        typecheck_command=dev_data.get("typecheck_command", dev_data.get("typecheck", "")),
        lint_command=dev_data.get("lint_command", dev_data.get("lint", "")),
        test_command=dev_data.get("test_command", dev_data.get("test", "")),
        build_command=dev_data.get("build_command", dev_data.get("build", "")),
        is_monorepo=is_monorepo,
        codebases=codebases,
    )


def _load_raw_yaml(config_path: str | Path) -> tuple[Path, dict[str, Any]]:
    """Load and parse raw YAML data from a config file.

    This is a shared helper for accessor functions that need raw YAML data
    beyond what load_config() parses (e.g., pm.tool, git.default_branch,
    tickets.prefix, repo.type).

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Tuple of (resolved Path, parsed YAML dict).

    Raises:
        ConfigError: If the file is missing or contains invalid YAML.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(
            f"Configuration file not found: {path}",
            file_path=path,
        )

    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        raise ConfigError(
            f"Failed to parse YAML: {e}",
            file_path=path,
        ) from e

    return path, data


def get_pm_tool_type(config_path: str | Path) -> str:
    """Get the configured project management tool type.

    Reads pm.tool from the config file and validates it against
    VALID_PM_TOOLS. This setting is required - there is no default.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        PM tool type string (github | trello | asana | none).

    Raises:
        ConfigError: If config file is missing, pm.tool is not set,
            or pm.tool has an invalid value.
    """
    path, data = _load_raw_yaml(config_path)

    # Get pm section
    pm_data = data.get("pm", {}) or {}
    tool = pm_data.get("tool")

    # Validate pm.tool is set
    if tool is None or tool == "":
        raise ConfigError(
            "pm.tool is not configured. "
            f"Must be one of: {', '.join(sorted(VALID_PM_TOOLS))}",
            file_path=path
        )

    # Validate pm.tool value
    if tool not in VALID_PM_TOOLS:
        raise ConfigError(
            f"Invalid pm.tool value: '{tool}'. "
            f"Must be one of: {', '.join(sorted(VALID_PM_TOOLS))}",
            file_path=path
        )

    return tool


def get_default_branch(config_path: str | Path = Path("config.yaml")) -> str:
    """Get the configured default git branch.

    Raises ConfigError if git.default_branch is not set — never silently
    falls back to 'main'.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Default branch name string (e.g., "develop-working").

    Raises:
        ConfigError: If config.yaml is missing, unparseable, or
            git.default_branch is not set.
    """
    path, data = _load_raw_yaml(config_path)

    git_data = data.get("git", {}) or {}
    branch = git_data.get("default_branch")

    if not branch:
        raise ConfigError(
            "git.default_branch is not set in config.yaml. "
            "This is required — add e.g.: git:\n  default_branch: develop-working",
            file_path=path,
        )

    return branch


def get_ticket_prefix(config_path: str | Path) -> str | None:
    """Get the ticket ID prefix from config (e.g., "SLCA").

    Reads tickets.prefix from config.yaml. Returns None if not set.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Ticket prefix string or None.
    """
    path = Path(config_path)
    if not path.exists():
        return None

    try:
        _, data = _load_raw_yaml(config_path)
    except ConfigError:
        return None

    tickets_data = data.get("tickets", {}) or {}
    return tickets_data.get("prefix") or None


def get_repo_tool_type(config_path: str | Path) -> str:
    """Get the configured repository tool type.

    Reads repo.type from the config file and validates it against
    VALID_REPO_TOOLS. Defaults to "github" if not specified.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Repo tool type string ("github" | "gitlab").

    Raises:
        ConfigError: If config file is missing, has invalid YAML,
            or repo.type has an invalid value.
    """
    path, data = _load_raw_yaml(config_path)

    # Get repo section
    repo_data = data.get("repo", {}) or {}
    tool = repo_data.get("type")

    # Default to github if not set or empty
    if tool is None or tool == "":
        return "github"

    # Validate repo.type value
    if tool not in VALID_REPO_TOOLS:
        raise ConfigError(
            f"Invalid repo.type value: '{tool}'. "
            f"Must be one of: {', '.join(sorted(VALID_REPO_TOOLS))}",
            file_path=path
        )

    return tool
