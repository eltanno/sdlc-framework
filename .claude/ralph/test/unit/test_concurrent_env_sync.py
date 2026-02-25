"""Unit tests for the EnvSyncer in concurrent.py.

Tests cover:
- .env file parsing (key=value, comments, blank lines, quoted values, export prefix)
- .env file writing (round-trip fidelity)
- .env merge logic (root vars merged into worktree, RALPH_LABEL preserved)
- sync_env method (end-to-end sync for a single worktree)
- Root .env is never modified by sync
- New worktrees receive RALPH_LABEL=ralph-N
- Existing worktrees keep their RALPH_LABEL
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestEnvSyncerParseEnv:
    """Tests for .env file parsing."""

    def test_parse_simple_key_value(self, tmp_path: Path):
        """Given a .env with simple key=value, when parsed, then returns correct dict."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\nDB_HOST=localhost\n")

        result = EnvSyncer.parse_env(env_file)

        assert result["API_KEY"] == "secret123"
        assert result["DB_HOST"] == "localhost"

    def test_parse_double_quoted_values(self, tmp_path: Path):
        """Given a .env with double-quoted values, when parsed, then quotes are stripped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text('DB_HOST="localhost"\nSECRET="my secret value"\n')

        result = EnvSyncer.parse_env(env_file)

        assert result["DB_HOST"] == "localhost"
        assert result["SECRET"] == "my secret value"

    def test_parse_single_quoted_values(self, tmp_path: Path):
        """Given a .env with single-quoted values, when parsed, then quotes are stripped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("DB_HOST='localhost'\nSECRET='my secret value'\n")

        result = EnvSyncer.parse_env(env_file)

        assert result["DB_HOST"] == "localhost"
        assert result["SECRET"] == "my secret value"

    def test_parse_skips_comments(self, tmp_path: Path):
        """Given a .env with comment lines, when parsed, then comments are skipped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nAPI_KEY=secret\n# Another comment\n")

        result = EnvSyncer.parse_env(env_file)

        assert len(result) == 1
        assert result["API_KEY"] == "secret"

    def test_parse_skips_blank_lines(self, tmp_path: Path):
        """Given a .env with blank lines, when parsed, then blanks are skipped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret\n\n\nDB_HOST=localhost\n")

        result = EnvSyncer.parse_env(env_file)

        assert len(result) == 2
        assert result["API_KEY"] == "secret"
        assert result["DB_HOST"] == "localhost"

    def test_parse_handles_export_prefix(self, tmp_path: Path):
        """Given a .env with 'export' prefix, when parsed, then prefix is stripped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("export API_KEY=secret\nexport DB_HOST=localhost\n")

        result = EnvSyncer.parse_env(env_file)

        assert result["API_KEY"] == "secret"
        assert result["DB_HOST"] == "localhost"

    def test_parse_handles_values_with_equals(self, tmp_path: Path):
        """Given a .env with values containing '=', when parsed, then only first '=' splits."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("CONNECTION=postgres://user:pass@host/db?opt=val\n")

        result = EnvSyncer.parse_env(env_file)

        assert result["CONNECTION"] == "postgres://user:pass@host/db?opt=val"

    def test_parse_handles_empty_values(self, tmp_path: Path):
        """Given a .env with empty values, when parsed, then value is empty string."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("EMPTY_VAR=\nANOTHER=value\n")

        result = EnvSyncer.parse_env(env_file)

        assert result["EMPTY_VAR"] == ""
        assert result["ANOTHER"] == "value"

    def test_parse_preserves_order(self, tmp_path: Path):
        """Given a .env with multiple vars, when parsed, then insertion order preserved."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("ZEBRA=z\nALPHA=a\nMIDDLE=m\n")

        result = EnvSyncer.parse_env(env_file)

        keys = list(result.keys())
        assert keys == ["ZEBRA", "ALPHA", "MIDDLE"]

    def test_parse_nonexistent_file_returns_empty(self, tmp_path: Path):
        """Given a nonexistent .env file, when parsed, then returns empty dict."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"

        result = EnvSyncer.parse_env(env_file)

        assert result == {}

    def test_parse_handles_inline_comments(self, tmp_path: Path):
        """Given a .env with inline comments, when parsed, then comment is excluded from value."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text('API_KEY=secret # this is inline\nQUOTED="has # inside"\n')

        result = EnvSyncer.parse_env(env_file)

        # Unquoted value: inline comment is stripped
        assert result["API_KEY"] == "secret"
        # Quoted value: # inside quotes is preserved
        assert result["QUOTED"] == "has # inside"

    def test_parse_strips_whitespace_around_key_value(self, tmp_path: Path):
        """Given a .env with spaces around '=', when parsed, then whitespace is stripped."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text("  API_KEY = secret  \n  DB_HOST = localhost  \n")

        result = EnvSyncer.parse_env(env_file)

        assert result["API_KEY"] == "secret"
        assert result["DB_HOST"] == "localhost"


class TestEnvSyncerWriteEnv:
    """Tests for .env file writing."""

    def test_write_simple_key_value(self, tmp_path: Path):
        """Given a dict of vars, when written, then file contains key=value lines."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        variables = {"API_KEY": "secret", "DB_HOST": "localhost"}

        EnvSyncer.write_env(env_file, variables)

        content = env_file.read_text()
        assert "API_KEY=secret\n" in content
        assert "DB_HOST=localhost\n" in content

    def test_write_quotes_values_with_spaces(self, tmp_path: Path):
        """Given a value with spaces, when written, then value is double-quoted."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        variables = {"SECRET": "my secret value"}

        EnvSyncer.write_env(env_file, variables)

        content = env_file.read_text()
        assert 'SECRET="my secret value"\n' in content

    def test_write_preserves_order(self, tmp_path: Path):
        """Given an ordered dict, when written, then order is preserved in file."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        variables = {"ZEBRA": "z", "ALPHA": "a", "MIDDLE": "m"}

        EnvSyncer.write_env(env_file, variables)

        lines = [
            line for line in env_file.read_text().splitlines()
            if line and not line.startswith("#")
        ]
        assert lines[0].startswith("ZEBRA=")
        assert lines[1].startswith("ALPHA=")
        assert lines[2].startswith("MIDDLE=")

    def test_write_handles_empty_values(self, tmp_path: Path):
        """Given an empty value, when written, then key= is written."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        variables = {"EMPTY_VAR": ""}

        EnvSyncer.write_env(env_file, variables)

        content = env_file.read_text()
        assert "EMPTY_VAR=\n" in content

    def test_write_empty_dict_creates_empty_file(self, tmp_path: Path):
        """Given an empty dict, when written, then file is created but empty (or header only)."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        variables = {}

        EnvSyncer.write_env(env_file, variables)

        assert env_file.exists()
        # File should have no key=value lines
        lines = [
            line for line in env_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert len(lines) == 0


class TestEnvSyncerRoundTrip:
    """Tests for parse -> write -> parse round-trip fidelity."""

    def test_round_trip_preserves_all_variables(self, tmp_path: Path):
        """Given a .env file, when parsed and written back, then all variables preserved."""
        from commands.concurrent import EnvSyncer

        original_content = (
            "API_KEY=secret123\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "RALPH_LABEL=ralph-0\n"
        )
        env_file = tmp_path / "original.env"
        env_file.write_text(original_content)

        # Parse
        variables = EnvSyncer.parse_env(env_file)

        # Write to different file
        output_file = tmp_path / "output.env"
        EnvSyncer.write_env(output_file, variables)

        # Parse again
        reparsed = EnvSyncer.parse_env(output_file)

        assert reparsed == variables

    def test_round_trip_preserves_values_with_special_chars(self, tmp_path: Path):
        """Given .env with special characters, when round-tripped, then values preserved."""
        from commands.concurrent import EnvSyncer

        env_file = tmp_path / ".env"
        env_file.write_text(
            'CONNECTION="postgres://user:pass@host/db?opt=val"\n'
            'SECRET="django-insecure-#o=!&pamq4k"\n'
        )

        variables = EnvSyncer.parse_env(env_file)
        output_file = tmp_path / "output.env"
        EnvSyncer.write_env(output_file, variables)
        reparsed = EnvSyncer.parse_env(output_file)

        assert reparsed == variables


class TestEnvSyncerMergeEnv:
    """Tests for .env merge logic."""

    def test_merge_root_vars_override_worktree_vars(self, tmp_path: Path):
        """Given root .env has updated value, when merged, then worktree gets root's value."""
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "new_secret", "DB_HOST": "new_host"}
        worktree_vars = {"API_KEY": "old_secret", "DB_HOST": "old_host"}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        assert result["API_KEY"] == "new_secret"
        assert result["DB_HOST"] == "new_host"

    def test_merge_preserves_worktree_ralph_label(self, tmp_path: Path):
        """Given worktree has RALPH_LABEL, when merged, then worktree's label preserved."""
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "secret", "RALPH_LABEL": "ralph-0"}
        worktree_vars = {"RALPH_LABEL": "ralph-1"}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        assert result["RALPH_LABEL"] == "ralph-1"

    def test_merge_root_ralph_label_never_propagated(self, tmp_path: Path):
        """Given root has RALPH_LABEL=ralph-0, when merged for ralph-2, then ralph-2 label used."""
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "secret", "RALPH_LABEL": "ralph-0"}
        worktree_vars = {}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-2")

        assert result["RALPH_LABEL"] == "ralph-2"

    def test_merge_adds_new_root_vars_to_worktree(self, tmp_path: Path):
        """Given root has new variable, when merged, then worktree gets it."""
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "secret", "NEW_VAR": "new_value"}
        worktree_vars = {"API_KEY": "secret"}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        assert result["NEW_VAR"] == "new_value"
        assert result["RALPH_LABEL"] == "ralph-1"

    def test_merge_sets_ralph_label_on_new_worktree(self, tmp_path: Path):
        """Given a new worktree with no .env, when merged, then RALPH_LABEL is set."""
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "secret", "DB_HOST": "localhost"}
        worktree_vars = {}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        assert result["RALPH_LABEL"] == "ralph-1"
        assert result["API_KEY"] == "secret"
        assert result["DB_HOST"] == "localhost"

    def test_merge_empty_root_still_sets_ralph_label(self, tmp_path: Path):
        """Given empty root .env, when merged, then RALPH_LABEL is still set."""
        from commands.concurrent import EnvSyncer

        root_vars = {}
        worktree_vars = {}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        assert result["RALPH_LABEL"] == "ralph-1"

    def test_merge_preserves_worktree_only_vars_not_in_root(self, tmp_path: Path):
        """Given worktree has extra vars not in root, when merged, then they are removed.

        The merge replaces the worktree's env entirely with root vars + RALPH_LABEL.
        Worktree-only vars are not kept since the root is the source of truth.
        """
        from commands.concurrent import EnvSyncer

        root_vars = {"API_KEY": "secret"}
        worktree_vars = {"API_KEY": "secret", "WORKTREE_ONLY": "local_only"}

        result = EnvSyncer.merge_env(root_vars, worktree_vars, ralph_label="ralph-1")

        # Root is source of truth; worktree-only vars are removed
        assert "WORKTREE_ONLY" not in result
        assert result["API_KEY"] == "secret"
        assert result["RALPH_LABEL"] == "ralph-1"


class TestEnvSyncerSyncEnv:
    """Tests for the sync_env end-to-end method."""

    def test_sync_new_worktree_gets_root_vars_plus_label(self, tmp_path: Path):
        """TC-4: Given new worktree with no .env, when synced, then gets all root vars + RALPH_LABEL."""
        from commands.concurrent import EnvSyncer

        # Set up root .env
        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        root_env.write_text("API_KEY=secret\nDB_HOST=localhost\nRALPH_LABEL=ralph-0\n")

        # Set up worktree dir (no .env yet)
        wt_dir = tmp_path / "worktree"
        wt_dir.mkdir()

        syncer = EnvSyncer()
        syncer.sync_env(root_env, wt_dir, "ralph-1")

        # Verify worktree .env
        wt_env = wt_dir / ".env"
        assert wt_env.exists()
        result = EnvSyncer.parse_env(wt_env)
        assert result["RALPH_LABEL"] == "ralph-1"
        assert result["API_KEY"] == "secret"
        assert result["DB_HOST"] == "localhost"

    def test_sync_preserves_existing_ralph_label(self, tmp_path: Path):
        """TC-5: Given existing worktree with RALPH_LABEL, when synced, then label preserved."""
        from commands.concurrent import EnvSyncer

        # Root .env with new variable added
        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        root_env.write_text("API_KEY=secret\nNEW_VAR=value\nRALPH_LABEL=ralph-0\n")

        # Existing worktree .env with its own RALPH_LABEL
        wt_dir = tmp_path / "worktree"
        wt_dir.mkdir()
        wt_env = wt_dir / ".env"
        wt_env.write_text("API_KEY=old_secret\nRALPH_LABEL=ralph-1\n")

        syncer = EnvSyncer()
        syncer.sync_env(root_env, wt_dir, "ralph-1")

        # Verify
        result = EnvSyncer.parse_env(wt_env)
        assert result["RALPH_LABEL"] == "ralph-1"
        assert result["API_KEY"] == "secret"  # Updated from root
        assert result["NEW_VAR"] == "value"  # Added from root

    def test_sync_never_modifies_root_env(self, tmp_path: Path):
        """TC-6: Given root .env, when sync runs, then root .env is unchanged."""
        from commands.concurrent import EnvSyncer

        # Root .env
        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        original_content = "API_KEY=secret\nDB_HOST=localhost\nRALPH_LABEL=ralph-0\n"
        root_env.write_text(original_content)

        # Sync to 3 worktrees
        syncer = EnvSyncer()
        for i in range(1, 4):
            wt_dir = tmp_path / f"worktree-{i}"
            wt_dir.mkdir()
            syncer.sync_env(root_env, wt_dir, f"ralph-{i}")

        # Verify root is unchanged
        assert root_env.read_text() == original_content

    def test_sync_root_label_not_propagated_to_worktree(self, tmp_path: Path):
        """Given root has RALPH_LABEL=ralph-0, when synced for ralph-2, then ralph-2 label used."""
        from commands.concurrent import EnvSyncer

        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        root_env.write_text("API_KEY=secret\nRALPH_LABEL=ralph-0\n")

        wt_dir = tmp_path / "worktree"
        wt_dir.mkdir()

        syncer = EnvSyncer()
        syncer.sync_env(root_env, wt_dir, "ralph-2")

        result = EnvSyncer.parse_env(wt_dir / ".env")
        assert result["RALPH_LABEL"] == "ralph-2"

    def test_sync_handles_real_world_env_file(self, tmp_path: Path):
        """Given a realistic .env file, when synced, then all vars handled correctly."""
        from commands.concurrent import EnvSyncer

        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        root_env.write_text(
            'SERVER_HOST="http://localhost"\n'
            "\n"
            'DB_HOST="host.docker.internal"\n'
            'DB_PORT="5432"\n'
            'DB_USER="postgres"\n'
            'DB_PWD="postgres"\n'
            "\n"
            '# Django settings\n'
            'DJANGO_SECRET_KEY="django-insecure-#o=!&pamq4k"\n'
            'DJANGO_DEBUG="True"\n'
            "\n"
            "RALPH_LABEL=ralph-0\n"
        )

        wt_dir = tmp_path / "worktree"
        wt_dir.mkdir()

        syncer = EnvSyncer()
        syncer.sync_env(root_env, wt_dir, "ralph-1")

        result = EnvSyncer.parse_env(wt_dir / ".env")
        assert result["SERVER_HOST"] == "http://localhost"
        assert result["DB_HOST"] == "host.docker.internal"
        assert result["DB_PORT"] == "5432"
        assert result["DJANGO_SECRET_KEY"] == "django-insecure-#o=!&pamq4k"
        assert result["RALPH_LABEL"] == "ralph-1"

    def test_sync_multiple_worktrees_get_unique_labels(self, tmp_path: Path):
        """Given multiple worktrees, when synced, then each has unique RALPH_LABEL."""
        from commands.concurrent import EnvSyncer

        root_env = tmp_path / "root" / ".env"
        root_env.parent.mkdir()
        root_env.write_text("API_KEY=secret\nRALPH_LABEL=ralph-0\n")

        syncer = EnvSyncer()
        labels = {}
        for i in range(1, 4):
            wt_dir = tmp_path / f"worktree-{i}"
            wt_dir.mkdir()
            syncer.sync_env(root_env, wt_dir, f"ralph-{i}")
            result = EnvSyncer.parse_env(wt_dir / ".env")
            labels[f"ralph-{i}"] = result["RALPH_LABEL"]

        assert labels["ralph-1"] == "ralph-1"
        assert labels["ralph-2"] == "ralph-2"
        assert labels["ralph-3"] == "ralph-3"
