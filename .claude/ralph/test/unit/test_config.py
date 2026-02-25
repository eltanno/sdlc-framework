"""Unit tests for config module.

Tests cover:
- Valid YAML loading with typed config access
- Missing/malformed config file handling
- Default values for missing keys
- PM tool type loading and validation
- Repo tool type loading and validation
- Default branch loading
"""

import pytest
from pathlib import Path

from core.config import (
    Config,
    ConfigError,
    load_config,
    get_default_branch,
    get_pm_tool_type,
    get_repo_tool_type,
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
        config_file.write_text("""\
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
        config_file.write_text("""\
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
        config_file.write_text("""\
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

    def test_load_config_max_concurrent_loops_from_yaml(self, tmp_path: Path) -> None:
        """Given ralph.max_concurrent_loops is set in config, when loaded,
        then the value is accessible on RalphConfig."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  max_concurrent_loops: 2
""")
        config = load_config(config_file)

        assert config.ralph.max_concurrent_loops == 2

    def test_load_config_max_concurrent_loops_defaults_to_four(self, tmp_path: Path) -> None:
        """Given ralph.max_concurrent_loops is not set, when loaded,
        then it defaults to 4."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  use_assignee: true
""")
        config = load_config(config_file)

        assert config.ralph.max_concurrent_loops == 4

    def test_load_config_empty_ralph_section_uses_all_defaults(self, tmp_path: Path) -> None:
        """Given config has empty ralph section, all defaults are applied."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph: {}
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "ralph-"
        assert config.ralph.use_assignee is True
        assert config.ralph.sonnet_threshold == 2
        assert config.ralph.max_attempts == 3
        assert config.ralph.max_concurrent_loops == 4

    def test_load_config_missing_ralph_section_uses_defaults(self, tmp_path: Path) -> None:
        """Given config has no ralph section, defaults are applied."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
dev:
  runtime: node
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "ralph-"
        assert config.ralph.use_assignee is True


class TestConfigDataclass:
    """Tests for Config dataclass attributes."""

    def test_config_has_ralph_section(self, tmp_path: Path) -> None:
        """Config has ralph section with expected attributes."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  instance_label_prefix: "test-"
  use_assignee: false
  sonnet_threshold: 3
  max_attempts: 5
  state_directory: "custom/state"
  validator_model: "sonnet"
  engineer_timeout: 60
  validator_timeout: 15
  review_model: "opus"
""")
        config = load_config(config_file)

        assert config.ralph.instance_label_prefix == "test-"
        assert config.ralph.use_assignee is False
        assert config.ralph.sonnet_threshold == 3
        assert config.ralph.max_attempts == 5
        assert config.ralph.state_directory == "custom/state"
        assert config.ralph.validator_model == "sonnet"
        assert config.ralph.engineer_timeout == 60
        assert config.ralph.validator_timeout == 15
        assert config.ralph.review_model == "opus"

    def test_validator_model_defaults_to_sonnet(self, tmp_path: Path) -> None:
        """Given validator_model is not specified, when config loads,
        then validator_model defaults to 'sonnet'.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  instance_label_prefix: "ralph-"
""")
        config = load_config(config_file)

        assert config.ralph.validator_model == "sonnet"

    def test_review_model_defaults_to_opus(self, tmp_path: Path) -> None:
        """Given review_model is not specified, when config loads,
        then review_model defaults to 'opus'.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  instance_label_prefix: "ralph-"
""")
        config = load_config(config_file)

        assert config.ralph.review_model == "opus"

    def test_review_model_accepts_model_name_strings(self, tmp_path: Path) -> None:
        """Given review_model is defined in config, when config loads,
        then review_model accepts model name strings (sonnet, haiku, opus).
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  review_model: "sonnet"
""")
        config = load_config(config_file)

        assert config.ralph.review_model == "sonnet"

    def test_review_model_can_be_set_to_haiku(self, tmp_path: Path) -> None:
        """Given review_model is 'haiku', when config loads,
        then review_model is set to 'haiku'.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  review_model: "haiku"
""")
        config = load_config(config_file)

        assert config.ralph.review_model == "haiku"

    def test_config_has_review_model_attribute(self, tmp_path: Path) -> None:
        """Given config is loaded with review_model set, when accessing the attribute,
        then it should be accessible with documentation for post-loop batch review.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  review_model: "opus"
""")
        config = load_config(config_file)

        # Verify attribute exists and has expected value
        assert hasattr(config.ralph, 'review_model')
        assert config.ralph.review_model == "opus"


class TestGetPmToolType:
    """Tests for get_pm_tool_type function."""

    @pytest.mark.parametrize("tool", ["github", "trello", "asana", "none"])
    def test_get_pm_tool_type_accepts_all_valid_tools(self, tmp_path: Path, tool: str) -> None:
        """Given any valid pm.tool value, when getting PM tool type, then returns that value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"pm:\n  tool: {tool}\n")
        result = get_pm_tool_type(config_file)
        assert result == tool

    def test_get_pm_tool_type_missing_pm_section_raises_error(self, tmp_path: Path) -> None:
        """Given config has no pm section, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
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
        config_file.write_text("""\
pm:
  other_setting: value
""")
        with pytest.raises(ConfigError) as exc_info:
            get_pm_tool_type(config_file)

        assert "pm.tool" in str(exc_info.value).lower()

    def test_get_pm_tool_type_invalid_value_raises_error(self, tmp_path: Path) -> None:
        """Given pm.tool has invalid value, when getting PM tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
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
        config_file.write_text("""\
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
        config_file.write_text("""\
repo:
  type: github
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_gitlab_returns_gitlab(self, tmp_path: Path) -> None:
        """Given repo.type is 'gitlab', when getting repo tool type, then returns 'gitlab'."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
repo:
  type: gitlab
""")
        result = get_repo_tool_type(config_file)

        assert result == "gitlab"

    def test_get_repo_tool_type_missing_repo_section_returns_github_default(self, tmp_path: Path) -> None:
        """Given config has no repo section, when getting repo tool type, then returns 'github' (default)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  instance_label_prefix: "ralph-"
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_missing_type_key_returns_github_default(self, tmp_path: Path) -> None:
        """Given repo section exists but type key missing, when getting repo tool type, then returns "github" (default)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
repo:
  other_setting: value
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_invalid_value_raises_error(self, tmp_path: Path) -> None:
        """Given repo.type has invalid value, when getting repo tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
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
        config_file.write_text("""\
repo:
  type: ""
""")
        result = get_repo_tool_type(config_file)

        assert result == "github"

    def test_get_repo_tool_type_malformed_yaml_raises_error(self, tmp_path: Path) -> None:
        """Given config file has malformed YAML, when getting repo tool type, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
repo:
  type: [invalid yaml
""")
        with pytest.raises(ConfigError) as exc_info:
            get_repo_tool_type(config_file)

        error_msg = str(exc_info.value).lower()
        assert "yaml" in error_msg or "parse" in error_msg


class TestGetDefaultBranch:
    """Tests for get_default_branch function."""

    def test_get_default_branch_returns_configured_value(self, tmp_path: Path) -> None:
        """Given git.default_branch is set, when getting default branch, then returns that value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
git:
  default_branch: develop-working
""")
        result = get_default_branch(config_file)

        assert result == "develop-working"

    def test_get_default_branch_raises_when_no_git_section(self, tmp_path: Path) -> None:
        """Given no git section in config, when getting default branch, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
ralph:
  instance_label_prefix: "ralph-"
""")
        with pytest.raises(ConfigError) as exc_info:
            get_default_branch(config_file)

        assert "git.default_branch" in str(exc_info.value)

    def test_get_default_branch_raises_when_missing_default_branch_key(self, tmp_path: Path) -> None:
        """Given git section exists but default_branch missing, raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
git:
  branch_prefix:
    feature: "feature/"
""")
        with pytest.raises(ConfigError) as exc_info:
            get_default_branch(config_file)

        assert "git.default_branch" in str(exc_info.value)

    def test_get_default_branch_raises_when_file_missing(self, tmp_path: Path) -> None:
        """Given config file doesn't exist, when getting default branch, then raises ConfigError."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            get_default_branch(config_file)

        assert "not found" in str(exc_info.value)

    def test_get_default_branch_raises_on_malformed_yaml(self, tmp_path: Path) -> None:
        """Given config file has malformed YAML, when getting default branch, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
git:
  default_branch: [invalid yaml
""")
        with pytest.raises(ConfigError) as exc_info:
            get_default_branch(config_file)

        error_msg = str(exc_info.value).lower()
        assert "parse" in error_msg or "yaml" in error_msg

    def test_get_default_branch_raises_on_empty_string(self, tmp_path: Path) -> None:
        """Given git.default_branch is empty string, when getting default branch, then raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
git:
  default_branch: ""
""")
        with pytest.raises(ConfigError) as exc_info:
            get_default_branch(config_file)

        assert "git.default_branch" in str(exc_info.value)


class TestConfigDevCommandParsing:
    """Tests for top-level Config dev command parsing with _command suffix."""

    def test_load_config_reads_command_suffix_fields(self, tmp_path: Path) -> None:
        """Given dev section uses _command suffix, when config loads,
        then top-level Config picks up the values correctly.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
dev:
  typecheck_command: "npx tsc --noEmit"
  lint_command: "ruff check ."
  test_command: "pytest"
  build_command: "npm run build"
""")
        config = load_config(config_file)

        assert config.typecheck_command == "npx tsc --noEmit"
        assert config.lint_command == "ruff check ."
        assert config.test_command == "pytest"
        assert config.build_command == "npm run build"

    def test_load_config_reads_short_fields_as_fallback(self, tmp_path: Path) -> None:
        """Given dev section uses short names (no _command suffix), when config loads,
        then top-level Config falls back to the short names.
        """
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
dev:
  typecheck: "npx tsc --noEmit"
  lint: "ruff check ."
  test: "pytest"
  build: "npm run build"
""")
        config = load_config(config_file)

        assert config.typecheck_command == "npx tsc --noEmit"
        assert config.lint_command == "ruff check ."
        assert config.test_command == "pytest"
        assert config.build_command == "npm run build"

    def test_load_config_command_suffix_takes_precedence(self, tmp_path: Path) -> None:
        """Given both _command and short forms exist, the _command variant wins."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
dev:
  typecheck_command: "correct-typecheck"
  typecheck: "wrong-typecheck"
  lint_command: "correct-lint"
  lint: "wrong-lint"
  test_command: "correct-test"
  test: "wrong-test"
  build_command: "correct-build"
  build: "wrong-build"
""")
        config = load_config(config_file)

        assert config.typecheck_command == "correct-typecheck"
        assert config.lint_command == "correct-lint"
        assert config.test_command == "correct-test"
        assert config.build_command == "correct-build"

    def test_load_config_empty_dev_section_defaults_to_empty_strings(self, tmp_path: Path) -> None:
        """Given empty dev section, all command fields default to empty string."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""\
dev: {}
""")
        config = load_config(config_file)

        assert config.typecheck_command == ""
        assert config.lint_command == ""
        assert config.test_command == ""
        assert config.build_command == ""

