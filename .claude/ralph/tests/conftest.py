"""Shared pytest fixtures for Ralph tests.

This module provides fixtures that are shared across all test modules:
- mock_gh: Mock for gh CLI commands
- mock_git: Mock for git CLI commands
- tmp_config: Temporary config file fixture
- tmp_state: Temporary state file fixture
"""

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def mock_subprocess_run(mocker):
    """Mock subprocess.run for external CLI calls.

    This is a general-purpose mock that can be configured for specific
    commands in individual tests.

    Returns:
        MagicMock configured for subprocess.run
    """
    mock = mocker.patch("subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    return mock


@pytest.fixture
def mock_gh(mocker):
    """Mock gh CLI commands.

    This fixture mocks the subprocess.run calls specifically for gh commands.
    By default, it returns empty results with success status.

    Returns:
        MagicMock that can be configured with side_effect or return_value
    """
    mock = mocker.patch("core.github.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = "[]"
    mock.return_value.stderr = ""
    return mock


@pytest.fixture
def mock_git(mocker):
    """Mock git CLI commands.

    This fixture mocks the subprocess.run calls specifically for git commands.
    By default, it returns empty output with success status.

    Returns:
        MagicMock that can be configured with side_effect or return_value
    """
    mock = mocker.patch("core.git.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    return mock


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a temporary config.yaml file.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path to the temporary config file
    """
    config_content = """
# Test configuration
project:
  name: test-project

dev:
  test_command: pytest
  lint_command: ruff check .
  typecheck_command: mypy .
  build_command: python -m build
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def tmp_state(tmp_path: Path) -> Path:
    """Create a temporary state file.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path to the temporary state file
    """
    state_content: dict[str, Any] = {
        "version": "1.0",
        "prd_path": "docs/prds/test-prd.md",
        "plan_path": "docs/plans/test-plan.md",
        "tickets": [
            {
                "id": "TASK-001",
                "title": "Test ticket",
                "status": "pending",
                "dependencies": [],
                "attempts": 0,
            }
        ],
        "current_ticket": None,
        "completed_count": 0,
        "blocked_count": 0,
    }
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state_content, indent=2))
    return state_file


@pytest.fixture
def sample_prd(tmp_path: Path) -> Path:
    """Create a sample PRD file for testing.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path to the sample PRD file
    """
    prd_content = """# Test PRD

## Summary
This is a test PRD for unit testing.

## Requirements
- FR-1: Feature one
- FR-2: Feature two
"""
    prd_file = tmp_path / "test-prd.md"
    prd_file.write_text(prd_content)
    return prd_file


@pytest.fixture
def sample_plan(tmp_path: Path) -> Path:
    """Create a sample plan file for testing.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path to the sample plan file
    """
    plan_content = """# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First task | - |
| TASK-002 | Second task | TASK-001 |
| TASK-003 | Third task | TASK-001, TASK-002 |
"""
    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text(plan_content)
    return plan_file
