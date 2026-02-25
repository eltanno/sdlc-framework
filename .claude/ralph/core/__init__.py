"""Core modules for Ralph - configuration, state management, and external CLI wrappers.

This package contains the foundational modules used by Ralph commands:
- claude_cli: Claude CLI utilities (stream-json parsing)
- config: Configuration loading from YAML and environment variables
- errors: Base error classes (CLIError hierarchy)
- state: Workflow state file management with atomic writes
- github: GitHub CLI (gh) wrapper for issue and PR operations
- git: Git CLI wrapper for repository operations
- pm: PM tool abstraction layer (Protocol and implementations)
"""

from core import claude_cli, config, errors, git, github, pm, state

__all__ = ["claude_cli", "config", "errors", "state", "github", "git", "pm"]
