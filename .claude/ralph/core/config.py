"""Configuration loading from YAML files and environment variables.

This module handles loading and parsing config.yaml files, supporting
environment variable overrides and providing typed access to configuration
values through dataclasses.

Supports both single-codebase and monorepo project structures via the
dev.codebases section in config.yaml.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when configuration loading fails.

    This exception is raised for:
    - Missing configuration files
    - Malformed YAML syntax
    - Invalid configuration values
    """

    pass


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
class Config:
    """Configuration loaded from config.yaml.

    Supports both single-codebase and monorepo configurations:
    - Single-codebase: Uses top-level dev.* commands
    - Monorepo: Uses dev.codebases.* for per-codebase commands

    Attributes:
        typecheck_command: Type checking command (single-codebase mode)
        lint_command: Linting command (single-codebase mode)
        test_command: Test command (single-codebase mode)
        build_command: Build command (single-codebase mode)
        is_monorepo: True if dev.codebases section exists
        codebases: List of Codebase configs (empty for single-codebase)
        instance_label: Ralph instance label from RALPH_LABEL env var
        raw: The raw parsed YAML dict for accessing any config value
    """

    typecheck_command: str = ""
    lint_command: str = ""
    test_command: str = ""
    build_command: str = ""
    is_monorepo: bool = False
    codebases: list[Codebase] = field(default_factory=list)
    instance_label: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def load_config(config_path: Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file

    Returns:
        Config object with all configuration values

    Raises:
        ConfigError: If file not found, malformed YAML, or invalid values
    """
    # Check file exists
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    # Parse YAML
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML in {config_path}: {e}")

    # Handle empty file
    if raw_config is None:
        raw_config = {}

    # Extract dev section
    dev_section = raw_config.get("dev", {}) or {}

    # Check for monorepo configuration
    codebases_section = dev_section.get("codebases", {}) or {}
    is_monorepo = bool(codebases_section)

    # Parse codebases if monorepo
    codebases: list[Codebase] = []
    if is_monorepo:
        for name, cb_config in codebases_section.items():
            if cb_config is None:
                cb_config = {}
            codebases.append(
                Codebase(
                    name=name,
                    path=cb_config.get("path", name),
                    typecheck_command=cb_config.get("typecheck_command", ""),
                    lint_command=cb_config.get("lint_command", ""),
                    test_command=cb_config.get("test_command", ""),
                    build_command=cb_config.get("build_command", ""),
                )
            )

    # Extract instance label from environment
    instance_label = os.environ.get("RALPH_LABEL")

    # Build config object
    return Config(
        typecheck_command=dev_section.get("typecheck_command", ""),
        lint_command=dev_section.get("lint_command", ""),
        test_command=dev_section.get("test_command", ""),
        build_command=dev_section.get("build_command", ""),
        is_monorepo=is_monorepo,
        codebases=codebases,
        instance_label=instance_label,
        raw=raw_config,
    )
