"""Configuration loading and management for Ralph orchestrator.

This module handles loading and parsing YAML configuration files and
environment variables, providing typed access to configuration values.

Replaces: .claude/scripts/ralph/config-helpers.sh

Example:
    >>> from core.config import load_config, get_instance_label
    >>> config = load_config(Path("config.yaml"))
    >>> print(config.ralph.instance_label_prefix)
    'ralph-'
    >>> label = get_instance_label(Path("config.yaml"))
    >>> print(label)
    'ralph-1'
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import yaml


class ConfigError(Exception):
    """Raised when configuration loading or validation fails.

    Attributes:
        file_path: Path to the config file that caused the error.
        message: Human-readable error message.
    """

    def __init__(self, message: str, file_path: Optional[Path] = None) -> None:
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
        keep_state_files: Whether to keep state files for audit (default: True).
        validator_model: Model for validation analysis (default: "haiku").
        engineer_timeout: Timeout in minutes for engineer (default: 30).
        validator_timeout: Timeout in minutes for validator (default: 10).
    """

    instance_label_prefix: str = "ralph-"
    use_assignee: bool = True
    sonnet_threshold: int = 2
    max_attempts: int = 3
    state_directory: str = "docs/state"
    keep_state_files: bool = True
    validator_model: str = "haiku"
    engineer_timeout: int = 30
    validator_timeout: int = 10


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


def load_config(config_path: Union[str, Path]) -> Config:
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
        validator_model=ralph_data.get("validator_model", "haiku"),
        engineer_timeout=ralph_data.get("engineer_timeout", 30),
        validator_timeout=ralph_data.get("validator_timeout", 10),
    )

    # Parse validation settings from dev section
    dev_data = data.get("dev", {}) or {}

    # Check for monorepo configuration
    codebases_data = dev_data.get("codebases", []) or []
    is_monorepo = len(codebases_data) > 0

    codebases = []
    for cb in codebases_data:
        codebases.append(Codebase(
            name=cb.get("name", ""),
            path=cb.get("path", ""),
            typecheck_command=cb.get("typecheck", ""),
            lint_command=cb.get("lint", ""),
            test_command=cb.get("test", ""),
            build_command=cb.get("build", ""),
        ))

    return Config(
        ralph=ralph_config,
        typecheck_command=dev_data.get("typecheck", ""),
        lint_command=dev_data.get("lint", ""),
        test_command=dev_data.get("test", ""),
        build_command=dev_data.get("build", ""),
        is_monorepo=is_monorepo,
        codebases=codebases,
    )


def get_instance_label_prefix(config_path: Union[str, Path]) -> str:
    """Get the instance label prefix from config.

    If the config file doesn't exist or doesn't have the setting,
    returns the default prefix "ralph-".

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Instance label prefix string.
    """
    path = Path(config_path)

    if not path.exists():
        return "ralph-"

    try:
        config = load_config(path)
        return config.ralph.instance_label_prefix
    except ConfigError:
        return "ralph-"


def get_instance_label(config_path: Union[str, Path]) -> str:
    """Get the instance label for this Ralph instance.

    The label is read from the RALPH_LABEL environment variable.
    If not set, defaults to "{prefix}1" where prefix is from config.

    Validates that the label matches the required pattern: {prefix}{number}

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Instance label string (e.g., "ralph-1", "ralph-2").

    Raises:
        ConfigError: If RALPH_LABEL doesn't match the required pattern.
    """
    prefix = get_instance_label_prefix(config_path)
    label = os.environ.get("RALPH_LABEL", "")

    if not label:
        return f"{prefix}1"

    # Validate format: must match {prefix}{number}
    pattern = f"^{re.escape(prefix)}[0-9]+$"
    if not re.match(pattern, label):
        raise ConfigError(
            f"RALPH_LABEL must match pattern '{prefix}<number>' "
            f"(e.g., {prefix}1, {prefix}2), got: '{label}'"
        )

    return label


def get_use_assignee(config_path: Union[str, Path]) -> bool:
    """Get whether to use GitHub issue assignment.

    If the config file doesn't exist or doesn't have the setting,
    returns True (for backward compatibility).

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Boolean indicating whether to use assignee.
    """
    path = Path(config_path)

    if not path.exists():
        return True

    try:
        config = load_config(path)
        return config.ralph.use_assignee
    except ConfigError:
        return True


def matches_instance_prefix(label: Optional[str], prefix: str) -> bool:
    """Check if a label matches the instance label prefix pattern.

    Args:
        label: Label to check (e.g., "ralph-1").
        prefix: Prefix to match against (e.g., "ralph-").

    Returns:
        True if label starts with prefix, False otherwise.
    """
    if not label:
        return False

    return label.startswith(prefix)
