"""Test that the Ralph package structure is correct.

Note: Most structural tests were removed as they were tautological (Python/pip
already enforce file existence) or weak (substring matching). Only tests that
catch real configuration bugs are kept here.
"""

import os
from pathlib import Path


# Get the ralph package directory
RALPH_DIR = Path(__file__).parent.parent.parent


class TestShellWrapper:
    """Tests for the shell wrapper entry point."""

    def test_shell_wrapper_is_executable(self):
        """ralph shell wrapper should be executable.

        This catches a real bug: wrapper could exist but lack execute
        permissions, causing 'Permission denied' errors for users.
        """
        wrapper = RALPH_DIR / "ralph"
        assert wrapper.exists(), f"Shell wrapper not found at {wrapper}"
        assert os.access(wrapper, os.X_OK), "Shell wrapper is not executable"
