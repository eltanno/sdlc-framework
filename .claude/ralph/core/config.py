"""Configuration loading from YAML files and environment variables.

This module handles loading and parsing config.yaml files, supporting
environment variable overrides and providing typed access to configuration
values through dataclasses.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    """Configuration container with typed access to settings.

    Attributes:
        project_name: Name of the project
        test_command: Command to run tests
        lint_command: Command to run linter
        typecheck_command: Command to run type checker
        build_command: Command to build the project
        default_branch: Default git branch (main, master, etc.)
        instance_label: Label for this Ralph instance (e.g., "ralph-1")
        instance_label_prefix: Prefix for instance labels (e.g., "ralph-")
        use_assignee: Whether to use GitHub assignee for issue claiming
        codebases: Dictionary of codebase configurations for monorepos
    """

    project_name: str
    test_command: str = ""
    lint_command: str = ""
    typecheck_command: str = ""
    build_command: str = ""
    default_branch: str = "main"
    instance_label: str = "ralph-1"
    instance_label_prefix: str = "ralph-"
    use_assignee: bool = True
    codebases: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_monorepo(self) -> bool:
        """Return True if this is a monorepo with multiple codebases."""
        return len(self.codebases) > 0

    def matches_instance_prefix(self, label: str) -> bool:
        """Check if a label matches the instance label prefix.

        Args:
            label: The label to check

        Returns:
            True if the label starts with the instance_label_prefix
        """
        if not label:
            return False
        return label.startswith(self.instance_label_prefix)


def load_config(config_path: Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file

    Returns:
        Config object with parsed configuration

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the YAML is invalid or RALPH_LABEL format is wrong
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        content = config_path.read_text()
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    if data is None:
        data = {}

    # Extract project settings
    project = data.get("project", {})
    project_name = project.get("name", "unknown")

    # Extract dev settings
    dev = data.get("dev", {})
    test_command = dev.get("test_command", "")
    lint_command = dev.get("lint_command", "")
    typecheck_command = dev.get("typecheck_command", "")
    build_command = dev.get("build_command", "")
    default_branch = dev.get("default_branch", "main")

    # Extract codebases for monorepo support
    codebases = dev.get("codebases", {})
    if codebases is None:
        codebases = {}

    # Extract ralph settings
    ralph = data.get("ralph", {})
    if ralph is None:
        ralph = {}

    instance_label_prefix = ralph.get("instance_label_prefix", "ralph-")
    use_assignee = ralph.get("use_assignee", True)

    # Normalize use_assignee to boolean
    if isinstance(use_assignee, str):
        use_assignee = use_assignee.lower() in ("true", "yes", "1")

    # Get instance label from environment or default
    instance_label = os.environ.get("RALPH_LABEL", "")
    if not instance_label:
        instance_label = f"{instance_label_prefix}1"
    else:
        # Validate format: must match {prefix}{number}
        pattern = f"^{re.escape(instance_label_prefix)}[0-9]+$"
        if not re.match(pattern, instance_label):
            raise ValueError(
                f"RALPH_LABEL must match pattern '{instance_label_prefix}<number>' "
                f"(e.g., {instance_label_prefix}1, {instance_label_prefix}2). "
                f"Got: '{instance_label}'"
            )

    return Config(
        project_name=project_name,
        test_command=test_command,
        lint_command=lint_command,
        typecheck_command=typecheck_command,
        build_command=build_command,
        default_branch=default_branch,
        instance_label=instance_label,
        instance_label_prefix=instance_label_prefix,
        use_assignee=use_assignee,
        codebases=codebases,
    )


def load_config_from_directory(directory: Path) -> Config:
    """Load configuration from a directory containing config.yaml.

    Args:
        directory: Path to the directory containing config.yaml

    Returns:
        Config object with parsed configuration

    Raises:
        FileNotFoundError: If config.yaml doesn't exist in the directory
        ValueError: If the YAML is invalid
    """
    config_path = directory / "config.yaml"
    return load_config(config_path)
