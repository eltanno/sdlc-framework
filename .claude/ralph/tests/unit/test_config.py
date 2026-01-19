"""Unit tests for core/config.py - Configuration loading.

Tests configuration loading from YAML files and environment variables,
supporting both single-codebase and monorepo project structures.
"""

import os
from pathlib import Path

import pytest

from core import config


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_valid_yaml_file(self, tmp_path: Path) -> None:
        """Given a valid config.yaml file, when loaded, then returns Config object."""
        config_content = """
dev:
  typecheck_command: "npm run typecheck"
  lint_command: "npm run lint"
  test_command: "npm test"
  build_command: "npm run build"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)

        assert isinstance(result, config.Config)
        assert result.typecheck_command == "npm run typecheck"
        assert result.lint_command == "npm run lint"
        assert result.test_command == "npm test"
        assert result.build_command == "npm run build"

    def test_load_config_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Given a missing config file, when loaded, then raises ConfigError."""
        missing_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(config.ConfigError) as exc_info:
            config.load_config(missing_file)

        assert "not found" in str(exc_info.value).lower()
        assert str(missing_file) in str(exc_info.value)

    def test_load_config_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Given a malformed YAML file, when loaded, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(config.ConfigError) as exc_info:
            config.load_config(config_file)

        assert "malformed" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    def test_load_config_uses_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        """Given a config with missing dev keys, when loaded, then defaults are used."""
        config_content = """
project:
  name: test-project
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)

        # Default values should be empty strings or None
        assert result.typecheck_command == ""
        assert result.lint_command == ""
        assert result.test_command == ""
        assert result.build_command == ""

    def test_load_config_handles_echo_skip_commands(self, tmp_path: Path) -> None:
        """Given config with echo commands, when loaded, then they are preserved."""
        config_content = """
dev:
  typecheck_command: "echo 'No typecheck'"
  lint_command: "echo 'No lint'"
  test_command: "pytest"
  build_command: "echo 'No build'"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)

        assert result.typecheck_command == "echo 'No typecheck'"
        assert result.lint_command == "echo 'No lint'"
        assert result.test_command == "pytest"


class TestMonorepoConfig:
    """Tests for monorepo configuration with multiple codebases."""

    def test_load_config_detects_monorepo(self, tmp_path: Path) -> None:
        """Given config with codebases section, when loaded, then is_monorepo is True."""
        config_content = """
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

        result = config.load_config(config_file)

        assert result.is_monorepo is True
        assert len(result.codebases) == 2

    def test_load_config_single_codebase(self, tmp_path: Path) -> None:
        """Given config without codebases section, when loaded, then is_monorepo is False."""
        config_content = """
dev:
  test_command: "npm test"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)

        assert result.is_monorepo is False
        assert len(result.codebases) == 0

    def test_codebase_has_all_fields(self, tmp_path: Path) -> None:
        """Given a codebase config, when loaded, then all fields are accessible."""
        config_content = """
dev:
  codebases:
    mobile:
      path: "mobile"
      typecheck_command: "npx tsc --noEmit"
      lint_command: "npm run lint"
      test_command: "npm test"
      build_command: "npm run build"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)
        mobile = result.codebases[0]

        assert mobile.name == "mobile"
        assert mobile.path == "mobile"
        assert mobile.typecheck_command == "npx tsc --noEmit"
        assert mobile.lint_command == "npm run lint"
        assert mobile.test_command == "npm test"
        assert mobile.build_command == "npm run build"


class TestEnvironmentVariableOverrides:
    """Tests for environment variable overrides."""

    def test_ralph_label_from_env(self, tmp_path: Path, monkeypatch) -> None:
        """Given RALPH_LABEL env var, when config loads, then instance_label reflects it."""
        config_content = """
ralph:
  instance_label_prefix: "ralph-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        monkeypatch.setenv("RALPH_LABEL", "worker-1")

        result = config.load_config(config_file)

        assert result.instance_label == "worker-1"

    def test_ralph_label_not_set(self, tmp_path: Path, monkeypatch) -> None:
        """Given no RALPH_LABEL env var, when config loads, then instance_label is None."""
        config_content = """
ralph:
  instance_label_prefix: "ralph-"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        monkeypatch.delenv("RALPH_LABEL", raising=False)

        result = config.load_config(config_file)

        assert result.instance_label is None


class TestConfigDataclass:
    """Tests for the Config dataclass structure."""

    def test_config_has_expected_attributes(self, tmp_path: Path) -> None:
        """Given any config, when accessed, then has expected validation attributes."""
        config_content = """
dev:
  test_command: "pytest"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)

        # These attributes must exist
        assert hasattr(result, "typecheck_command")
        assert hasattr(result, "lint_command")
        assert hasattr(result, "test_command")
        assert hasattr(result, "build_command")
        assert hasattr(result, "is_monorepo")
        assert hasattr(result, "codebases")


class TestCodebaseDataclass:
    """Tests for the Codebase dataclass structure."""

    def test_codebase_defaults(self, tmp_path: Path) -> None:
        """Given a minimal codebase config, when loaded, then defaults are used."""
        config_content = """
dev:
  codebases:
    api:
      path: "api"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        result = config.load_config(config_file)
        api = result.codebases[0]

        assert api.name == "api"
        assert api.path == "api"
        assert api.typecheck_command == ""
        assert api.lint_command == ""
        assert api.test_command == ""
        assert api.build_command == ""
