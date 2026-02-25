"""Unit tests for scripted checks framework.

Tests the ScriptedCheckResult dataclass and run_scripted_checks() framework
function. This implements AIUI-0057: Create scripted checks framework.

These tests verify:
- ScriptedCheckResult correctly stores check name, pass/fail status, and details
- run_scripted_checks() runs all registered checks
- run_scripted_checks() aggregates results correctly
- run_scripted_checks() fails fast when any check fails
- run_scripted_checks() completes quickly (under 30 seconds)
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from commands.scripted_checks import (
    ScriptedCheckResult,
    ScriptedChecksResult,
    run_scripted_checks,
)


class TestScriptedCheckResult:
    """Tests for the ScriptedCheckResult dataclass."""

    def test_create_passing_check(self) -> None:
        """ScriptedCheckResult should store a passing check with details."""
        result = ScriptedCheckResult(
            name="merge_commits",
            passed=True,
            details="PASS: All tickets merged",
        )

        assert result.name == "merge_commits"
        assert result.passed is True
        assert result.details == "PASS: All tickets merged"

    def test_create_failing_check(self) -> None:
        """ScriptedCheckResult should store a failing check with details."""
        result = ScriptedCheckResult(
            name="orphaned_branches",
            passed=False,
            details="FAIL: feature/AIUI-0038-implementation not merged",
        )

        assert result.name == "orphaned_branches"
        assert result.passed is False
        assert result.details == "FAIL: feature/AIUI-0038-implementation not merged"

    def test_check_result_equality(self) -> None:
        """Two ScriptedCheckResults with same values should be equal."""
        result1 = ScriptedCheckResult(
            name="bypass_language",
            passed=False,
            details="FAIL: Bypass language found in docs/state/AIUI-0039/attempt-1/engineer-state.md",
        )
        result2 = ScriptedCheckResult(
            name="bypass_language",
            passed=False,
            details="FAIL: Bypass language found in docs/state/AIUI-0039/attempt-1/engineer-state.md",
        )

        assert result1 == result2


class TestScriptedChecksResult:
    """Tests for the ScriptedChecksResult aggregate class."""

    def test_all_passed_when_all_checks_pass(self) -> None:
        """all_passed should be True when all individual checks pass."""
        result = ScriptedChecksResult(
            checks=[
                ScriptedCheckResult(name="check1", passed=True, details="PASS"),
                ScriptedCheckResult(name="check2", passed=True, details="PASS"),
            ]
        )

        assert result.all_passed is True

    def test_all_passed_false_when_any_check_fails(self) -> None:
        """all_passed should be False when any individual check fails."""
        result = ScriptedChecksResult(
            checks=[
                ScriptedCheckResult(name="check1", passed=True, details="PASS"),
                ScriptedCheckResult(name="check2", passed=False, details="FAIL"),
            ]
        )

        assert result.all_passed is False

    def test_all_passed_false_when_empty(self) -> None:
        """all_passed should be False when no checks were run."""
        result = ScriptedChecksResult(checks=[])

        assert result.all_passed is False

    def test_failed_checks_returns_only_failures(self) -> None:
        """failed_checks should return only checks that failed."""
        result = ScriptedChecksResult(
            checks=[
                ScriptedCheckResult(name="check1", passed=True, details="PASS"),
                ScriptedCheckResult(name="check2", passed=False, details="FAIL: reason 1"),
                ScriptedCheckResult(name="check3", passed=False, details="FAIL: reason 2"),
            ]
        )

        failed = result.failed_checks
        assert len(failed) == 2
        assert failed[0].name == "check2"
        assert failed[1].name == "check3"

    def test_get_summary_with_all_passing(self) -> None:
        """get_summary should report all checks passed."""
        result = ScriptedChecksResult(
            checks=[
                ScriptedCheckResult(name="merge_commits", passed=True, details="PASS: All tickets merged"),
                ScriptedCheckResult(name="state_files", passed=True, details="PASS: All state files exist"),
            ]
        )

        summary = result.get_summary()
        assert "PASS" in summary
        assert "merge_commits" in summary
        assert "state_files" in summary

    def test_get_summary_with_failures(self) -> None:
        """get_summary should clearly show failures."""
        result = ScriptedChecksResult(
            checks=[
                ScriptedCheckResult(name="merge_commits", passed=True, details="PASS: All tickets merged"),
                ScriptedCheckResult(name="orphaned_branches", passed=False, details="FAIL: feature/AIUI-0038 not merged"),
            ]
        )

        summary = result.get_summary()
        assert "FAIL" in summary
        assert "orphaned_branches" in summary


class TestRunScriptedChecks:
    """Tests for run_scripted_checks() framework function."""

    def test_runs_all_registered_checks(self) -> None:
        """run_scripted_checks should execute all provided check functions."""
        call_log: list[str] = []

        def check1(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            call_log.append("check1")
            return ScriptedCheckResult(name="check1", passed=True, details="PASS")

        def check2(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            call_log.append("check2")
            return ScriptedCheckResult(name="check2", passed=True, details="PASS")

        result = run_scripted_checks(
            ticket_ids=["AIUI-0001", "AIUI-0002"],
            state_dir=Path("docs/state"),
            checks=[check1, check2],
        )

        assert "check1" in call_log
        assert "check2" in call_log
        assert len(result.checks) == 2

    def test_passes_ticket_ids_to_checks(self) -> None:
        """run_scripted_checks should pass ticket_ids to each check function."""
        received_ids: list[str] = []

        def capture_ids_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            received_ids.extend(ticket_ids)
            return ScriptedCheckResult(name="capture", passed=True, details="PASS")

        run_scripted_checks(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=Path("docs/state"),
            checks=[capture_ids_check],
        )

        assert received_ids == ["AIUI-0001", "AIUI-0002", "AIUI-0003"]

    def test_passes_state_dir_to_checks(self) -> None:
        """run_scripted_checks should pass state_dir to each check function."""
        received_path: list[Path] = []

        def capture_path_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            received_path.append(state_dir)
            return ScriptedCheckResult(name="capture", passed=True, details="PASS")

        run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("/custom/state/dir"),
            checks=[capture_path_check],
        )

        assert received_path[0] == Path("/custom/state/dir")

    def test_aggregates_all_passed_results(self) -> None:
        """run_scripted_checks should return all_passed=True when all checks pass."""
        def passing_check1(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            return ScriptedCheckResult(name="check1", passed=True, details="PASS")

        def passing_check2(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            return ScriptedCheckResult(name="check2", passed=True, details="PASS")

        result = run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            checks=[passing_check1, passing_check2],
        )

        assert result.all_passed is True

    def test_aggregates_failed_results(self) -> None:
        """run_scripted_checks should return all_passed=False when any check fails."""
        def passing_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            return ScriptedCheckResult(name="passing", passed=True, details="PASS")

        def failing_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            return ScriptedCheckResult(name="failing", passed=False, details="FAIL: Something wrong")

        result = run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            checks=[passing_check, failing_check],
        )

        assert result.all_passed is False
        assert len(result.failed_checks) == 1
        assert result.failed_checks[0].name == "failing"

    def test_returns_empty_when_no_checks(self) -> None:
        """run_scripted_checks should return result with no checks if empty list provided."""
        result = run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            checks=[],
        )

        assert len(result.checks) == 0
        assert result.all_passed is False  # No checks = not passed

    def test_handles_check_exception(self) -> None:
        """run_scripted_checks should handle exceptions from check functions."""
        def crashing_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            raise RuntimeError("Check crashed!")

        result = run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            checks=[crashing_check],
        )

        assert result.all_passed is False
        assert len(result.checks) == 1
        assert result.checks[0].passed is False
        assert "crashed" in result.checks[0].details.lower() or "error" in result.checks[0].details.lower()

    def test_completes_within_timeout(self) -> None:
        """run_scripted_checks framework overhead should be minimal (<1 second)."""
        # Create 10 fast checks to test framework overhead
        def fast_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            return ScriptedCheckResult(name="fast", passed=True, details="PASS")

        checks = [fast_check] * 10

        start = time.time()
        run_scripted_checks(
            ticket_ids=["AIUI-0001"] * 100,  # 100 tickets
            state_dir=Path("docs/state"),
            checks=checks,
        )
        elapsed = time.time() - start

        # Framework overhead should be well under 1 second for simple checks
        assert elapsed < 1.0, f"Framework overhead too high: {elapsed:.2f}s"

    def test_includes_duration_in_result(self) -> None:
        """run_scripted_checks should track total duration."""
        import time

        def slow_check(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
            time.sleep(0.1)  # 100ms
            return ScriptedCheckResult(name="slow", passed=True, details="PASS")

        result = run_scripted_checks(
            ticket_ids=["AIUI-0001"],
            state_dir=Path("docs/state"),
            checks=[slow_check],
        )

        # Duration should be at least 100ms
        assert result.duration_seconds >= 0.1


class TestCheckMergeCommits:
    """Tests for check_merge_commits() function (AIUI-0058)."""

    @pytest.fixture(autouse=True)
    def mock_default_branch(self, monkeypatch) -> None:
        """Mock get_default_branch to return 'develop' for all merge commit tests."""
        monkeypatch.setattr(
            "commands.scripted_checks.get_default_branch",
            lambda: "develop",
        )

    def test_all_tickets_merged_passes(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should pass when all tickets have merge commits on develop."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        # Mock git log output showing all tickets merged
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = """\
abc123 Merge branch 'feature/AIUI-0001-test' into 'develop'
def456 Merge branch 'feature/AIUI-0002-test' into 'develop'
ghi789 Merge branch 'feature/AIUI-0003-test' into 'develop'
"""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is True
        assert "PASS" in result.details
        assert "All tickets merged" in result.details

    def test_missing_merge_commit_fails(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should fail when any ticket is missing merge commit."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        # Mock git log output showing AIUI-0002 is NOT merged
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = """\
abc123 Merge branch 'feature/AIUI-0001-test' into 'develop'
ghi789 Merge branch 'feature/AIUI-0003-test' into 'develop'
"""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0002" in result.details
        assert "not merged" in result.details

    def test_multiple_missing_tickets_reports_all(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should report all missing tickets when multiple are not merged."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        # Mock git log output showing only AIUI-0002 is merged
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = """\
def456 Merge branch 'feature/AIUI-0002-test' into 'develop'
"""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is False
        assert "AIUI-0001" in result.details
        assert "AIUI-0003" in result.details
        # AIUI-0002 should NOT be in the failure details
        assert result.details.count("AIUI-0002") == 0 or "not merged" not in result.details

    def test_empty_ticket_list_passes(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should pass when no tickets to check."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=[],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is True
        assert "No tickets to check" in result.details or "PASS" in result.details

    def test_git_command_failure_fails_check(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should fail gracefully when git command fails."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 128
                stdout = ""
                stderr = "fatal: not a git repository"
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is False
        assert "FAIL" in result.details

    def test_handles_different_merge_message_formats(self, monkeypatch, tmp_path) -> None:
        """check_merge_commits should recognize different merge commit message formats."""
        import subprocess
        from commands.scripted_checks import check_merge_commits

        # Different formats: GitLab, GitHub, manual merge
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = """\
abc123 Merge branch 'feature/AIUI-0001-test' into 'develop'
def456 Merge pull request #42 from feature/AIUI-0002-test
ghi789 Merge AIUI-0003: Add feature
"""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_merge_commits(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "merge_commits"
        assert result.passed is True
        assert "PASS" in result.details


class TestCheckOrphanedBranches:
    """Tests for check_orphaned_branches() function (AIUI-0059)."""

    @pytest.fixture(autouse=True)
    def mock_default_branch(self, monkeypatch) -> None:
        """Mock get_default_branch to return 'develop' for all orphaned branches tests."""
        monkeypatch.setattr(
            "commands.scripted_checks.get_default_branch",
            lambda: "develop",
        )

    def test_all_branches_merged_passes(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should pass when all feature branches are merged or deleted."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        # Mock git branch -a output showing only merged branches
        def mock_run(cmd, **kwargs):
            # Handle both "git branch -a" and "git branch --merged develop"
            if "--merged" in cmd:
                # All feature branches are merged
                result = Result()
                result.stdout = """\
  feature/AIUI-0001-test
  feature/AIUI-0002-test
  feature/AIUI-0003-test
"""
                return result
            else:
                # List all branches
                result = Result()
                result.stdout = """\
  main
  develop
  remotes/origin/feature/AIUI-0001-test
  remotes/origin/feature/AIUI-0002-test
  remotes/origin/feature/AIUI-0003-test
"""
                return result

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is True
        assert "PASS" in result.details
        assert "No orphaned branches" in result.details

    def test_unmerged_branch_fails(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should fail when a feature branch is not merged."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        # Mock git commands
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            if "--merged" in cmd:
                # Only AIUI-0001 and AIUI-0003 are merged
                result = Result()
                result.stdout = """\
  feature/AIUI-0001-test
  feature/AIUI-0003-test
"""
                return result
            else:
                # All three branches exist
                result = Result()
                result.stdout = """\
  main
  develop
  remotes/origin/feature/AIUI-0001-test
  remotes/origin/feature/AIUI-0002-test
  remotes/origin/feature/AIUI-0003-test
"""
                return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0002" in result.details
        assert "not merged" in result.details

    def test_multiple_unmerged_branches_reports_all(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should report all unmerged branches."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        # Mock git commands
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            if "--merged" in cmd:
                # Only AIUI-0002 is merged
                result = Result()
                result.stdout = """\
  feature/AIUI-0002-test
"""
                return result
            else:
                # All three branches exist
                result = Result()
                result.stdout = """\
  main
  develop
  remotes/origin/feature/AIUI-0001-test
  remotes/origin/feature/AIUI-0002-test
  remotes/origin/feature/AIUI-0003-test
"""
                return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is False
        assert "AIUI-0001" in result.details
        assert "AIUI-0003" in result.details
        # AIUI-0002 should NOT be in failure details (it's merged)
        assert "AIUI-0002" not in result.details or "not merged" not in result.details

    def test_empty_ticket_list_passes(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should pass when no tickets to check."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=[],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is True
        assert "No tickets to check" in result.details or "PASS" in result.details

    def test_git_command_failure_fails_check(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should fail gracefully when git command fails."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 128
                stdout = ""
                stderr = "fatal: not a git repository"
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is False
        assert "FAIL" in result.details

    def test_handles_branches_without_remotes(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should handle local branches without remotes."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        # Mock git commands
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            if "--merged" in cmd:
                # AIUI-0001 is merged
                result = Result()
                result.stdout = """\
  feature/AIUI-0001-test
"""
                return result
            else:
                # Only local branches, no remotes
                result = Result()
                result.stdout = """\
  main
  develop
  feature/AIUI-0001-test
  feature/AIUI-0002-test
"""
                return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001", "AIUI-0002"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is False
        assert "AIUI-0002" in result.details

    def test_branch_naming_patterns(self, monkeypatch, tmp_path) -> None:
        """check_orphaned_branches should match different branch naming patterns."""
        import subprocess
        from commands.scripted_checks import check_orphaned_branches

        # Mock git commands with various branch name formats
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            if "--merged" in cmd:
                # All are merged
                result = Result()
                result.stdout = """\
  feature/AIUI-0001-short-name
  feature/AIUI-0002-longer-description-with-dashes
  feature/AIUI-0003-description
"""
                return result
            else:
                result = Result()
                result.stdout = """\
  main
  develop
  remotes/origin/feature/AIUI-0001-short-name
  remotes/origin/feature/AIUI-0002-longer-description-with-dashes
  remotes/origin/feature/AIUI-0003-description
"""
                return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = check_orphaned_branches(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "orphaned_branches"
        assert result.passed is True
        assert "PASS" in result.details


class TestCheckBypassLanguage:
    """Tests for check_bypass_language() function (AIUI-0060)."""

    def test_no_bypass_language_passes(self, tmp_path) -> None:
        """check_bypass_language should pass when no bypass patterns found."""
        from commands.scripted_checks import check_bypass_language

        # Create state files without bypass language
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Implementation Summary
Implemented the feature as specified in the acceptance criteria.
All tests pass. All checks pass.

## Acceptance Criteria Status
- [x] AC1: Feature works correctly
- [x] AC2: Tests added and passing
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is True
        assert "PASS" in result.details
        assert "No bypass language" in result.details

    def test_detects_not_merged_but_acceptable(self, tmp_path) -> None:
        """check_bypass_language should detect 'not merged but acceptable' pattern."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with bypass language
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Implementation Summary
The dependency is not merged but acceptable because it's not critical.

## Acceptance Criteria Status
- [x] AC1: Feature works
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0001" in result.details or str(state_file) in result.details
        assert "bypass language" in result.details.lower()

    def test_detects_doesnt_block(self, tmp_path) -> None:
        """check_bypass_language should detect \"doesn't block\" pattern."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with bypass language
        ticket_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Notes
The failing test doesn't block the merge because it's flaky.
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0002"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "bypass language" in result.details.lower()

    def test_detects_doesnt_apply(self, tmp_path) -> None:
        """check_bypass_language should detect \"doesn't apply\" pattern."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with bypass language
        ticket_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Acceptance Criteria
- [x] AC1: This criterion doesn't apply to my implementation
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details

    def test_detects_out_of_scope(self, tmp_path) -> None:
        """check_bypass_language should detect 'out of scope' pattern."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with bypass language
        ticket_dir = tmp_path / "AIUI-0004" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Notes
The database migration requirement is out of scope for this ticket.
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0004"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0004" in result.details

    def test_detects_multiple_patterns_in_one_file(self, tmp_path) -> None:
        """check_bypass_language should detect when multiple bypass patterns exist."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with multiple bypass patterns
        ticket_dir = tmp_path / "AIUI-0005" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Notes
The dependency doesn't block this implementation.
Also, the integration test requirement is out of scope.
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0005"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details

    def test_detects_across_multiple_tickets(self, tmp_path) -> None:
        """check_bypass_language should detect bypass language across multiple tickets."""
        from commands.scripted_checks import check_bypass_language

        # Create first ticket - clean
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)
        (ticket1_dir / "engineer-state.md").write_text("All good here.")

        # Create second ticket - has bypass language
        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)
        (ticket2_dir / "engineer-state.md").write_text("This doesn't block the release.")

        # Create third ticket - clean
        ticket3_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket3_dir.mkdir(parents=True)
        (ticket3_dir / "engineer-state.md").write_text("Implemented successfully.")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0002" in result.details

    def test_empty_ticket_list_passes(self, tmp_path) -> None:
        """check_bypass_language should pass when no tickets to check."""
        from commands.scripted_checks import check_bypass_language

        result = check_bypass_language(
            ticket_ids=[],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is True
        assert "No tickets to check" in result.details or "PASS" in result.details

    def test_handles_missing_state_directory(self, tmp_path) -> None:
        """check_bypass_language should handle when state directory doesn't exist."""
        from commands.scripted_checks import check_bypass_language

        # Don't create any state directories
        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        # Should pass because no state files exist to scan
        assert result.name == "bypass_language"
        assert result.passed is True

    def test_handles_missing_engineer_state_file(self, tmp_path) -> None:
        """check_bypass_language should handle when engineer-state.md doesn't exist."""
        from commands.scripted_checks import check_bypass_language

        # Create state directory but no engineer-state.md
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        # Don't create engineer-state.md

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        # Should pass because no state file to scan
        assert result.name == "bypass_language"
        assert result.passed is True

    def test_case_insensitive_pattern_matching(self, tmp_path) -> None:
        """check_bypass_language should detect patterns case-insensitively."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with uppercase/mixed case bypass language
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Notes
This requirement DOESN'T APPLY to this implementation.
Also the test is OUT OF SCOPE.
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details

    def test_ignores_legitimate_similar_phrases(self, tmp_path) -> None:
        """check_bypass_language should not false positive on legitimate similar text."""
        from commands.scripted_checks import check_bypass_language

        # Create state file with phrases that are similar but NOT bypass language
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        state_file = ticket_dir / "engineer-state.md"
        state_file.write_text("""\
# Engineer State

## Implementation Notes
Applied the fix. The changes scope includes authentication.
The dependency was merged successfully. Nothing blocks the PR.

All acceptance criteria met:
- [x] Feature implemented
- [x] Tests added
""")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        # Should pass - "scope includes" is not "out of scope"
        # "nothing blocks" is different from "doesn't block"
        # "merged successfully" is not "not merged but"
        assert result.name == "bypass_language"
        assert result.passed is True

    def test_detects_in_multiple_attempt_directories(self, tmp_path) -> None:
        """check_bypass_language should check all attempt directories."""
        from commands.scripted_checks import check_bypass_language

        # Create attempt-1 - clean
        attempt1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        attempt1_dir.mkdir(parents=True)
        (attempt1_dir / "engineer-state.md").write_text("First attempt - all good.")

        # Create attempt-2 - has bypass language
        attempt2_dir = tmp_path / "AIUI-0001" / "attempt-2"
        attempt2_dir.mkdir(parents=True)
        (attempt2_dir / "engineer-state.md").write_text("Second attempt - doesn't apply.")

        result = check_bypass_language(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "bypass_language"
        assert result.passed is False
        assert "FAIL" in result.details


class TestCheckStateFilesExist:
    """Tests for check_state_files_exist() function (AIUI-0061)."""

    def test_all_state_directories_exist_passes(self, tmp_path) -> None:
        """check_state_files_exist should pass when all tickets have state directories."""
        from commands.scripted_checks import check_state_files_exist

        # Create state directories for all tickets
        (tmp_path / "AIUI-0001").mkdir()
        (tmp_path / "AIUI-0002").mkdir()
        (tmp_path / "AIUI-0003").mkdir()

        result = check_state_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "state_files"
        assert result.passed is True
        assert "PASS" in result.details
        assert "All state" in result.details

    def test_missing_state_directory_fails(self, tmp_path) -> None:
        """check_state_files_exist should fail when any ticket is missing state directory."""
        from commands.scripted_checks import check_state_files_exist

        # Create state directories for only some tickets
        (tmp_path / "AIUI-0001").mkdir()
        # AIUI-0002 is missing
        (tmp_path / "AIUI-0003").mkdir()

        result = check_state_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "state_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0002" in result.details
        assert "No state" in result.details

    def test_multiple_missing_directories_reports_all(self, tmp_path) -> None:
        """check_state_files_exist should report all missing state directories."""
        from commands.scripted_checks import check_state_files_exist

        # Create state directory for only one ticket
        (tmp_path / "AIUI-0002").mkdir()
        # AIUI-0001 and AIUI-0003 are missing

        result = check_state_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "state_files"
        assert result.passed is False
        assert "AIUI-0001" in result.details
        assert "AIUI-0003" in result.details
        # AIUI-0002 should NOT be in failure details (it exists)
        assert result.details.count("AIUI-0002") == 0 or "No state" not in result.details

    def test_empty_ticket_list_passes(self, tmp_path) -> None:
        """check_state_files_exist should pass when no tickets to check."""
        from commands.scripted_checks import check_state_files_exist

        result = check_state_files_exist(
            ticket_ids=[],
            state_dir=tmp_path,
        )

        assert result.name == "state_files"
        assert result.passed is True
        assert "No tickets to check" in result.details or "PASS" in result.details

    def test_state_directory_is_file_not_directory_fails(self, tmp_path) -> None:
        """check_state_files_exist should fail if state path exists but is a file, not a directory."""
        from commands.scripted_checks import check_state_files_exist

        # Create a file instead of a directory
        (tmp_path / "AIUI-0001").touch()

        result = check_state_files_exist(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "state_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0001" in result.details

    def test_nested_state_directory_structure(self, tmp_path) -> None:
        """check_state_files_exist should pass when state directories have nested structure."""
        from commands.scripted_checks import check_state_files_exist

        # Create nested state directory structure (with attempt directories)
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)
        (ticket1_dir / "engineer-state.md").touch()

        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)

        result = check_state_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002"],
            state_dir=tmp_path,
        )

        # Should pass - we only check the ticket directory exists, not its contents
        assert result.name == "state_files"
        assert result.passed is True
        assert "PASS" in result.details


class TestCheckValidationFilesExist:
    """Tests for check_validation_files_exist() function (AIUI-0062)."""

    def test_all_validation_files_exist_passes(self, tmp_path) -> None:
        """check_validation_files_exist should pass when all tickets have validation.md files."""
        from commands.scripted_checks import check_validation_files_exist

        # Create validation files for all tickets
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)
        (ticket1_dir / "validation.md").touch()

        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)
        (ticket2_dir / "validation.md").touch()

        ticket3_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket3_dir.mkdir(parents=True)
        (ticket3_dir / "validation.md").touch()

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is True
        assert "PASS" in result.details
        assert "All validation" in result.details

    def test_missing_validation_file_fails(self, tmp_path) -> None:
        """check_validation_files_exist should fail when any ticket is missing validation.md."""
        from commands.scripted_checks import check_validation_files_exist

        # Create validation files for only some tickets
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)
        (ticket1_dir / "validation.md").touch()

        # AIUI-0002 - no validation.md
        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)

        ticket3_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket3_dir.mkdir(parents=True)
        (ticket3_dir / "validation.md").touch()

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0002" in result.details
        assert "No validation" in result.details

    def test_multiple_missing_files_reports_all(self, tmp_path) -> None:
        """check_validation_files_exist should report all missing validation files."""
        from commands.scripted_checks import check_validation_files_exist

        # Create validation file for only one ticket
        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)
        (ticket2_dir / "validation.md").touch()

        # AIUI-0001 and AIUI-0003 are missing validation files
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)

        ticket3_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket3_dir.mkdir(parents=True)

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "AIUI-0001" in result.details
        assert "AIUI-0003" in result.details

    def test_empty_ticket_list_passes(self, tmp_path) -> None:
        """check_validation_files_exist should pass when no tickets to check."""
        from commands.scripted_checks import check_validation_files_exist

        result = check_validation_files_exist(
            ticket_ids=[],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is True
        assert "No tickets to check" in result.details or "PASS" in result.details

    def test_handles_missing_state_directory(self, tmp_path) -> None:
        """check_validation_files_exist should fail when ticket state directory doesn't exist."""
        from commands.scripted_checks import check_validation_files_exist

        # Don't create any state directories
        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0001" in result.details

    def test_handles_missing_attempt_directory(self, tmp_path) -> None:
        """check_validation_files_exist should fail when ticket has no attempt directories."""
        from commands.scripted_checks import check_validation_files_exist

        # Create state directory but no attempt subdirectory
        (tmp_path / "AIUI-0001").mkdir()

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0001" in result.details

    def test_checks_all_attempt_directories(self, tmp_path) -> None:
        """check_validation_files_exist should look in all attempt directories."""
        from commands.scripted_checks import check_validation_files_exist

        # Create multiple attempt directories, validation.md only in attempt-2
        attempt1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        attempt1_dir.mkdir(parents=True)
        # No validation.md in attempt-1

        attempt2_dir = tmp_path / "AIUI-0001" / "attempt-2"
        attempt2_dir.mkdir(parents=True)
        (attempt2_dir / "validation.md").touch()

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        # Should pass - validation.md exists in at least one attempt directory
        assert result.name == "validation_files"
        assert result.passed is True
        assert "PASS" in result.details

    def test_validation_file_is_directory_not_file_fails(self, tmp_path) -> None:
        """check_validation_files_exist should fail if validation.md exists but is a directory."""
        from commands.scripted_checks import check_validation_files_exist

        # Create validation.md as a directory instead of a file
        ticket_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "validation.md").mkdir()

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "FAIL" in result.details
        assert "AIUI-0001" in result.details

    def test_mixed_success_and_failure(self, tmp_path) -> None:
        """check_validation_files_exist should correctly report mixed results."""
        from commands.scripted_checks import check_validation_files_exist

        # AIUI-0001 - has validation.md
        ticket1_dir = tmp_path / "AIUI-0001" / "attempt-1"
        ticket1_dir.mkdir(parents=True)
        (ticket1_dir / "validation.md").touch()

        # AIUI-0002 - missing validation.md
        ticket2_dir = tmp_path / "AIUI-0002" / "attempt-1"
        ticket2_dir.mkdir(parents=True)

        # AIUI-0003 - has validation.md
        ticket3_dir = tmp_path / "AIUI-0003" / "attempt-1"
        ticket3_dir.mkdir(parents=True)
        (ticket3_dir / "validation.md").touch()

        # AIUI-0004 - missing validation.md
        ticket4_dir = tmp_path / "AIUI-0004" / "attempt-1"
        ticket4_dir.mkdir(parents=True)

        result = check_validation_files_exist(
            ticket_ids=["AIUI-0001", "AIUI-0002", "AIUI-0003", "AIUI-0004"],
            state_dir=tmp_path,
        )

        assert result.name == "validation_files"
        assert result.passed is False
        assert "AIUI-0002" in result.details
        assert "AIUI-0004" in result.details
        # AIUI-0001 and AIUI-0003 should NOT be in failure details
        assert result.details.count("AIUI-0001") == 0
        assert result.details.count("AIUI-0003") == 0
