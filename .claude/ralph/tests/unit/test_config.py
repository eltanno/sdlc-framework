"""Unit tests for core/config.py - Configuration loading module.

Tests cover:
- YAML config file loading
- Environment variable overrides
- Default value handling
- Missing/malformed config error handling
- Typed config access

Following TDD: Write failing tests first, then implement.
"""

import os
from pathlib import Path
from typing import Any

import pytest


class TestConfigLoading:
    """Tests for loading configuration from YAML files."""

    def test_load_config_from_yaml_file(self, tmp_path: Path):
        """Given a valid config.yaml, load_config returns parsed config."""
        from core.config import load_config

        config_content = """
project:
  name: test-project

dev:
  test_command: pytest
  lint_command: ruff check .
  typecheck_command: mypy .
  build_command: python -m build
  default_branch: main
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.project_name == "test-project"
        assert config.test_command == "pytest"
        assert config.lint_command == "ruff check ."
        assert config.default_branch == "main"

    def test_load_config_missing_file_raises_error(self, tmp_path: Path):
        """Given a missing config file, load_config raises FileNotFoundError."""
        from core.config import load_config

        missing_file = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(missing_file)

    def test_load_config_invalid_yaml_raises_error(self, tmp_path: Path):
        """Given invalid YAML, load_config raises ValueError."""
        from core.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: {{{")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config(config_file)

    def test_load_config_returns_defaults_for_missing_keys(self, tmp_path: Path):
        """Given a minimal config, missing keys return default values."""
        from core.config import load_config

        config_content = """
project:
  name: minimal
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        # Should have sensible defaults
        assert config.project_name == "minimal"
        assert config.test_command == ""
        assert config.default_branch == "main"


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_ralph_label_env_var_overrides_config(self, tmp_path: Path, monkeypatch):
        """Given RALPH_LABEL env var is set, it overrides config value."""
        from core.config import load_config

        config_content = """
project:
  name: test

ralph:
  instance_label_prefix: "ralph-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        monkeypatch.setenv("RALPH_LABEL", "ralph-5")

        config = load_config(config_file)

        assert config.instance_label == "ralph-5"

    def test_instance_label_defaults_to_prefix_plus_one(self, tmp_path: Path, monkeypatch):
        """Given no RALPH_LABEL env var, instance_label defaults to {prefix}1."""
        from core.config import load_config

        monkeypatch.delenv("RALPH_LABEL", raising=False)

        config_content = """
project:
  name: test

ralph:
  instance_label_prefix: "worker-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.instance_label == "worker-1"
        assert config.instance_label_prefix == "worker-"

    def test_instance_label_validates_format(self, tmp_path: Path, monkeypatch):
        """Given invalid RALPH_LABEL format, load_config raises ValueError."""
        from core.config import load_config

        config_content = """
project:
  name: test

ralph:
  instance_label_prefix: "ralph-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        monkeypatch.setenv("RALPH_LABEL", "invalid-label-format")

        with pytest.raises(ValueError, match="RALPH_LABEL must match pattern"):
            load_config(config_file)


class TestRalphConfigSection:
    """Tests for ralph-specific configuration."""

    def test_use_assignee_defaults_to_true(self, tmp_path: Path):
        """Given no use_assignee setting, it defaults to True."""
        from core.config import load_config

        config_content = """
project:
  name: test
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.use_assignee is True

    def test_use_assignee_can_be_disabled(self, tmp_path: Path):
        """Given use_assignee: false, config reflects that."""
        from core.config import load_config

        config_content = """
project:
  name: test

ralph:
  use_assignee: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.use_assignee is False

    def test_instance_label_prefix_default(self, tmp_path: Path):
        """Given no instance_label_prefix, it defaults to 'ralph-'."""
        from core.config import load_config

        config_content = """
project:
  name: test
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.instance_label_prefix == "ralph-"


class TestConfigDataclass:
    """Tests for the Config dataclass itself."""

    def test_config_has_all_required_attributes(self, tmp_path: Path, monkeypatch):
        """Config dataclass exposes all required attributes."""
        from core.config import load_config

        # Clear RALPH_LABEL to test with ci- prefix
        monkeypatch.delenv("RALPH_LABEL", raising=False)

        config_content = """
project:
  name: full-test

dev:
  test_command: pytest
  lint_command: ruff check .
  typecheck_command: mypy .
  build_command: python -m build
  default_branch: develop

ralph:
  instance_label_prefix: "ci-"
  use_assignee: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        # Project attributes
        assert hasattr(config, "project_name")

        # Dev attributes
        assert hasattr(config, "test_command")
        assert hasattr(config, "lint_command")
        assert hasattr(config, "typecheck_command")
        assert hasattr(config, "build_command")
        assert hasattr(config, "default_branch")

        # Ralph attributes
        assert hasattr(config, "instance_label")
        assert hasattr(config, "instance_label_prefix")
        assert hasattr(config, "use_assignee")

    def test_matches_instance_prefix(self, tmp_path: Path):
        """Config.matches_instance_prefix correctly identifies matching labels."""
        from core.config import load_config

        config_content = """
project:
  name: test

ralph:
  instance_label_prefix: "ralph-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.matches_instance_prefix("ralph-1") is True
        assert config.matches_instance_prefix("ralph-42") is True
        assert config.matches_instance_prefix("worker-1") is False
        assert config.matches_instance_prefix("") is False


class TestCodebasesConfig:
    """Tests for monorepo codebases configuration."""

    def test_load_single_codebase_config(self, tmp_path: Path):
        """Given no codebases section, config represents single codebase."""
        from core.config import load_config

        config_content = """
project:
  name: single-repo

dev:
  test_command: npm test
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.is_monorepo is False
        assert len(config.codebases) == 0

    def test_load_monorepo_config(self, tmp_path: Path):
        """Given codebases section, config includes codebase details."""
        from core.config import load_config

        config_content = """
project:
  name: monorepo

dev:
  codebases:
    mobile:
      path: "mobile"
      test_command: "npm test"
    backend:
      path: "backend"
      test_command: "pytest"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert config.is_monorepo is True
        assert len(config.codebases) == 2
        assert "mobile" in config.codebases
        assert config.codebases["mobile"]["path"] == "mobile"
        assert config.codebases["mobile"]["test_command"] == "npm test"


class TestConfigFromDirectory:
    """Tests for loading config from a directory."""

    def test_load_config_from_directory(self, tmp_path: Path):
        """Given a directory path, load_config finds config.yaml within it."""
        from core.config import load_config_from_directory

        config_content = """
project:
  name: dir-test
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config_from_directory(tmp_path)

        assert config.project_name == "dir-test"

    def test_load_config_from_directory_missing(self, tmp_path: Path):
        """Given a directory without config.yaml, raises FileNotFoundError."""
        from core.config import load_config_from_directory

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_config_from_directory(empty_dir)
