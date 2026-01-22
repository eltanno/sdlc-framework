"""Unit tests for config module.

Tests cover:
- Valid YAML loading with typed config access
- Environment variable overrides (RALPH_LABEL)
- Missing/malformed config file handling
- Default values for missing keys
- Instance label validation
- Use assignee flag
- Instance label prefix
- PM tool type loading and validation
- Repo tool type loading and validation
"""

import pytest
from pathlib import Path

from core.config import (
    Config,
    ConfigError,
    load_config,
    get_instance_label,
    get_instance_label_prefix,
    get_use_assignee,
    get_pm_tool_type,
    get_repo_tool_type,
    matches_instance_prefix,
    VALID_PM_TOOLS,
    VALID_REPO_TOOLS,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_valid_yaml_returns_typed_config(self, tmp_path: Path) -> None:
        """Given a valid config.yaml file exists, when config loads,
        then all configuration values are accessible as typed attributes.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
  use_assignee: false
  sonnet_threshold: 2
  max_attempts: 3
""")
        config = load_config(config_file)

        assert isinstance(config, Config)
        assert config.ralph.instance_label_prefix == "ralph-"
        assert config.ralph.use_assignee is False
        assert config.ralph.sonnet_threshold == 2
        assert config.ralph.max_attempts == 3

    def test_load_config_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Given config.yaml is missing, when config loads,
        then a clear error message is raised with the file path.
        """
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        assert "nonexistent.yaml" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_load_config_malformed_yaml_raises_error(self, tmp_path: Path) -> None:
        """Given config.yaml is malformed, when config loads,
        then a clear error message is raised with the file path and issue.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
  use_assignee: [invalid yaml
""")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        error_msg = str(exc_info.value).lower()
        assert "config.yaml" in str(exc_info.value)
        assert "yaml" in error_msg or "parse" in error_msg

    def test_load_config_uses_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        """Given default values are defined, when a config key is missing,
        then the default value is used.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  use_assignee: true
""")
        config = load_config(config_file)

        # instance_label_prefix should default to "ralph-"
        assert config.ralph.instance_label_prefix == "ralph-"
        # sonnet_threshold should default to 2
        assert config.ralph.sonnet_threshold == 2
        # max_attempts should default to 3
        assert config.ralph.max_attempts == 3

    def test_load_config_empty_ralph_section_uses_all_defaults(self, tmp_path: Path) -> None:
        """Given config has empty ralph section, all defaults are applied."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph: {}
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "ralph-"
        assert config.ralph.use_assignee is True
        assert config.ralph.sonnet_threshold == 2
        assert config.ralph.max_attempts == 3

    def test_load_config_missing_ralph_section_uses_defaults(self, tmp_path: Path) -> None:
        """Given config has no ralph section, defaults are applied."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
dev:
  runtime: node
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "ralph-"
        assert config.ralph.use_assignee is True


class TestGetInstanceLabel:
    """Tests for get_instance_label function."""

    def test_get_instance_label_from_env_var(self, tmp_path: Path, monkeypatch) -> None:
        """Given RALPH_LABEL env var is set, when config loads,
        then the instance_label reflects the environment value.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")
        monkeypatch.setenv("RALPH_LABEL", "ralph-2")

        label = get_instance_label(config_file)

        assert label == "ralph-2"

    def test_get_instance_label_defaults_to_prefix_1(self, tmp_path: Path, monkeypatch) -> None:
        """Given RALPH_LABEL not set, when getting label,
        then default to {prefix}1.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")
        monkeypatch.delenv("RALPH_LABEL", raising=False)

        label = get_instance_label(config_file)

        assert label == "ralph-1"

    def test_get_instance_label_validates_format(self, tmp_path: Path, monkeypatch) -> None:
        """Given RALPH_LABEL has invalid format, when getting label,
        then raise error.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")
        monkeypatch.setenv("RALPH_LABEL", "my-custom-label")

        with pytest.raises(ConfigError) as exc_info:
            get_instance_label(config_file)

        assert "ralph-" in str(exc_info.value)
        assert "pattern" in str(exc_info.value).lower()

    def test_get_instance_label_with_custom_prefix(self, tmp_path: Path, monkeypatch) -> None:
        """Given custom prefix in config and matching env var, label is valid."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "worker-"
""")
        monkeypatch.setenv("RALPH_LABEL", "worker-3")

        label = get_instance_label(config_file)

        assert label == "worker-3"

    def test_get_instance_label_custom_prefix_default(self, tmp_path: Path, monkeypatch) -> None:
        """Given custom prefix, default label uses that prefix."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ci-"
""")
        monkeypatch.delenv("RALPH_LABEL", raising=False)

        label = get_instance_label(config_file)

        assert label == "ci-1"


class TestGetInstanceLabelPrefix:
    """Tests for get_instance_label_prefix function."""

    def test_get_prefix_from_config(self, tmp_path: Path) -> None:
        """Given configured prefix, returns that prefix."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "my-prefix-"
""")

        prefix = get_instance_label_prefix(config_file)

        assert prefix == "my-prefix-"

    def test_get_prefix_defaults_to_ralph(self, tmp_path: Path) -> None:
        """Given no prefix configured, defaults to 'ralph-'."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  use_assignee: true
""")

        prefix = get_instance_label_prefix(config_file)

        assert prefix == "ralph-"

    def test_get_prefix_missing_file_returns_default(self, tmp_path: Path) -> None:
        """Given missing config file, returns default prefix."""
        config_file = tmp_path / "nonexistent.yaml"

        prefix = get_instance_label_prefix(config_file)

        assert prefix == "ralph-"

    def test_get_prefix_malformed_yaml_returns_default(self, tmp_path: Path) -> None:
        """Given malformed YAML config file, returns default prefix."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: [invalid yaml
""")

        prefix = get_instance_label_prefix(config_file)

        assert prefix == "ralph-"


class TestGetUseAssignee:
    """Tests for get_use_assignee function."""

    def test_get_use_assignee_false(self, tmp_path: Path) -> None:
        """Given use_assignee is false, returns False."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  use_assignee: false
""")

        result = get_use_assignee(config_file)

        assert result is False

    def test_get_use_assignee_true(self, tmp_path: Path) -> None:
        """Given use_assignee is true, returns True."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  use_assignee: true
""")

        result = get_use_assignee(config_file)

        assert result is True

    def test_get_use_assignee_defaults_to_true(self, tmp_path: Path) -> None:
        """Given use_assignee not configured, defaults to True."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")

        result = get_use_assignee(config_file)

        assert result is True

    def test_get_use_assignee_missing_file_returns_default(self, tmp_path: Path) -> None:
        """Given missing config file, returns default True."""
        config_file = tmp_path / "nonexistent.yaml"

        result = get_use_assignee(config_file)

        assert result is True

    def test_get_use_assignee_malformed_yaml_returns_default(self, tmp_path: Path) -> None:
        """Given malformed YAML config file, returns default True."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  use_assignee: [invalid yaml
""")

        result = get_use_assignee(config_file)

        assert result is True


class TestMatchesInstancePrefix:
    """Tests for matches_instance_prefix function."""

    def test_matching_label_returns_true(self) -> None:
        """Given label matches prefix, returns True."""
        assert matches_instance_prefix("ralph-1", "ralph-") is True
        assert matches_instance_prefix("ralph-99", "ralph-") is True

    def test_non_matching_label_returns_false(self) -> None:
        """Given label doesn't match prefix, returns False."""
        assert matches_instance_prefix("worker-1", "ralph-") is False
        assert matches_instance_prefix("other-label", "ralph-") is False

    def test_empty_label_returns_false(self) -> None:
        """Given empty label, returns False."""
        assert matches_instance_prefix("", "ralph-") is False

    def test_none_label_returns_false(self) -> None:
        """Given None label, returns False (defensive programming - None shouldn't crash)."""
        assert matches_instance_prefix(None, "ralph-") is False  # type: ignore

    def test_custom_prefix_matching(self) -> None:
        """Given custom prefix, matches correctly."""
        assert matches_instance_prefix("ci-agent-1", "ci-") is True
        assert matches_instance_prefix("worker-5", "worker-") is True
        assert matches_instance_prefix("ci-agent-1", "worker-") is False


class TestConfigDataclass:
    """Tests for Config dataclass attributes."""

    def test_config_has_ralph_section(self, tmp_path: Path) -> None:
        """Config has ralph section with expected attributes."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "test-"
  use_assignee: false
  sonnet_threshold: 3
  max_attempts: 5
  state_directory: "custom/state"
  keep_state_files: false
  validator_model: "sonnet"
  engineer_timeout: 60
  validator_timeout: 15
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "test-"
        assert config.ralph.use_assignee is False
        assert config.ralph.sonnet_threshold == 3
        assert config.ralph.max_attempts == 5
        assert config.ralph.state_directory == "custom/state"
        assert config.ralph.keep_state_files is False
        assert config.ralph.validator_model == "sonnet"
        assert config.ralph.engineer_timeout == 60
        assert config.ralph.validator_timeout == 15


class TestGetPmToolType:
    """Tests for get_pm_tool_type function."""

    @pytest.mark.parametrize("tool", ["github", "trello", "asana", "linear", "none"])
    def test_get_pm_tool_type_accepts_all_valid_tools(self, tmp_path: Path, tool: str) -> None:
        """Given any valid pm.tool value, when getting PM tool type, then returns that value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"pm:\n  tool: {tool}\n")
        result = get_pm_tool_type(config_file)
        assert result == tool

    def test_get_pm_tool_type_missing_pm_section_raises_error(self, tmp_path: Path) -> None:
        """Given config has no pm section, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")
        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        assert "pm.tool" in str(exc_info.value).lower()
        assert "not configured" in str(exc_info.value).lower() or "not set" in str(exc_info.value).lower()

    def test_get_pm_tool_type_missing_tool_key_raises_error(self, tmp_path: Path) -> None:
        """Given pm section exists but tool key missing, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  other_setting: value
""")
        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        assert "pm.tool" in str(exc_info.value).lower()

    def test_get_pm_tool_type_invalid_value_raises_error(self, tmp_path: Path) -> None:
        """Given pm.tool has invalid value, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: jira
""")
        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        error_msg = str(exc_info.value).lower()
        assert "jira" in error_msg
        assert "invalid" in error_msg or "must be" in error_msg

    def test_get_pm_tool_type_missing_config_file_raises_error(self, tmp_path: Path) -> None:
        """Given config file doesn't exist, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        assert "not found" in str(exc_info.value).lower()

    def test_get_pm_tool_type_empty_string_raises_error(self, tmp_path: Path) -> None:
        """Given pm.tool is empty string, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pm:
  tool: ""
""")
        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        assert "pm.tool" in str(exc_info.value).lower()


class TestGetRepoToolType:
    """Tests for get_repo_tool_type function."""

    def test_get_repo_tool_type_github_returns_github(self, tmp_path: Path) -> None:
        """Given repo.type is 'github', when getting repo tool type, then returns 'github'."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  type: github
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_gitlab_returns_gitlab(self, tmp_path: Path) -> None:
        """Given repo.type is 'gitlab', when getting repo tool type, then returns 'gitlab'."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  type: gitlab
""")
        result = get_repo_tool_type(config_file)

        assert result == "gitlab"

    def test_get_repo_tool_type_missing_repo_section_returns_github_default(self, tmp_path: Path) -> None:
        """Given config has no repo section, when getting repo tool type, then returns 'github' (default)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ralph:
  instance_label_prefix: "ralph-"
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_missing_type_key_returns_github_default(self, tmp_path: Path) -> None:
        """Given repo section exists but type key missing, when getting repo tool type, then returns 'github' (default)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  other_setting: value
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_invalid_value_raises_error(self, tmp_path: Path) -> None:
        """Given repo.type has invalid value, when getting repo tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  type: bitbucket
""")
        with pytest.raises(ConfigError) as exc_info:
            get_repo_tool_type(config_file)

        error_msg = str(exc_info.value).lower()
        assert "bitbucket" in error_msg
        assert "invalid" in error_msg or "must be" in error_msg

    def test_get_repo_tool_type_missing_config_file_raises_error(self, tmp_path: Path) -> None:
        """Given config file doesn't exist, when getting repo tool type, then raises ConfigError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            get_repo_tool_type(config_file)

        assert "not found" in str(exc_info.value).lower()

    def test_get_repo_tool_type_empty_string_returns_github_default(self, tmp_path: Path) -> None:
        """Given repo.type is empty string, when getting repo tool type, then returns 'github' (default)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  type: ""
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_malformed_yaml_raises_error(self, tmp_path: Path) -> None:
        """Given config file has malformed YAML, when getting repo tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repo:
  type: [invalid yaml
""")
        with pytest.raises(ConfigError) as exc_info:
            get_repo_tool_type(config_file)

        error_msg = str(exc_info.value).lower()
        assert "yaml" in error_msg or "parse" in error_msg
