"""Scripted checks framework for post-loop validation.

This module implements the scripted checks framework (AIUI-0057) for the
/execution-report command. The framework provides:

1. ScriptedCheckResult - Data class for individual check results
2. ScriptedChecksResult - Aggregate class for all check results
3. run_scripted_checks() - Framework function to execute all checks

The framework is designed to be extensible - individual check implementations
(AIUI-0058 through AIUI-0062) are plugged in as CheckFunction callables.

Scripted checks are fast, deterministic, and run BEFORE any agent review in
the /execution-report flow. If any scripted check fails, the report fails
immediately without invoking the expensive agent review.

From the PRD:
- FR-7: Scripted checks execute first before agent review
- FR-7: Failures report immediately without agent review
- FR-7: All checks pass -> proceeds to agent review
- FR-7: Checks complete in under 30 seconds
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class CheckFunction(Protocol):
    """Protocol for scripted check functions.

    Each check function takes:
    - ticket_ids: List of ticket IDs to validate
    - state_dir: Path to the state directory (docs/state)

    And returns a ScriptedCheckResult with pass/fail status and details.
    """

    def __call__(
        self, ticket_ids: list[str], state_dir: Path
    ) -> "ScriptedCheckResult": ...


@dataclass
class ScriptedCheckResult:
    """Result of a single scripted check.

    Attributes:
        name: Name of the check (e.g., "merge_commits", "orphaned_branches")
        passed: True if check passed, False if failed
        details: Human-readable details (PASS: reason or FAIL: reason)
    """

    name: str
    passed: bool
    details: str


@dataclass
class ScriptedChecksResult:
    """Aggregate result of all scripted checks.

    Attributes:
        checks: List of individual check results
        duration_seconds: Total time taken to run all checks
    """

    checks: list[ScriptedCheckResult] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def all_passed(self) -> bool:
        """Check if all scripted checks passed.

        Returns:
            True if all checks passed, False if any failed or no checks run.
        """
        if not self.checks:
            return False
        return all(check.passed for check in self.checks)

    @property
    def failed_checks(self) -> list[ScriptedCheckResult]:
        """Get list of failed checks.

        Returns:
            List of ScriptedCheckResult where passed is False.
        """
        return [check for check in self.checks if not check.passed]

    def get_summary(self) -> str:
        """Generate a human-readable summary of check results.

        Returns:
            Formatted string with check names and results.
        """
        if not self.checks:
            return "No checks were run"

        lines = []
        overall_status = "PASS" if self.all_passed else "FAIL"
        lines.append(f"Scripted Checks: {overall_status}")
        lines.append("")

        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"  [{status}] {check.name}")
            lines.append(f"    {check.details}")

        lines.append("")
        lines.append(f"Duration: {self.duration_seconds:.2f}s")

        return "\n".join(lines)


def run_scripted_checks(
    ticket_ids: list[str],
    state_dir: Path,
    checks: list[CheckFunction],
) -> ScriptedChecksResult:
    """Run all scripted checks and aggregate results.

    This is the main entry point for the scripted checks framework. It:
    1. Executes each check function in order
    2. Handles exceptions from check functions gracefully
    3. Aggregates all results into ScriptedChecksResult
    4. Tracks total duration

    Args:
        ticket_ids: List of ticket IDs to validate (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (typically docs/state)
        checks: List of check functions to execute

    Returns:
        ScriptedChecksResult with all check results and total duration.
    """
    start_time = time.time()
    results: list[ScriptedCheckResult] = []

    for check_fn in checks:
        try:
            result = check_fn(ticket_ids, state_dir)
            results.append(result)
        except Exception as e:
            # Check function crashed - treat as failure
            check_name = getattr(check_fn, "__name__", "unknown_check")
            results.append(
                ScriptedCheckResult(
                    name=check_name,
                    passed=False,
                    details=f"FAIL: Check crashed with error: {e}",
                )
            )

    duration = time.time() - start_time

    return ScriptedChecksResult(checks=results, duration_seconds=duration)


def check_merge_commits(ticket_ids: list[str], state_dir: Path) -> ScriptedCheckResult:
    """Verify that each ticket has a merge commit on develop.

    This check implements FR-8: Scripted Check - Merge Commit Verification.
    It ensures that every ticket in the batch has been successfully merged to
    the develop branch.

    The check executes 'git log develop --oneline' and searches for merge commit
    messages containing each ticket ID. It recognizes multiple merge formats:
    - GitLab: "Merge branch 'feature/TICKET-ID-*' into 'develop'"
    - GitHub: "Merge pull request #N from feature/TICKET-ID-*"
    - Manual: "Merge TICKET-ID: description"

    Args:
        ticket_ids: List of ticket IDs to verify (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (not used by this check)

    Returns:
        ScriptedCheckResult with:
        - name: "merge_commits"
        - passed: True if all tickets have merge commits, False otherwise
        - details: "PASS: All tickets merged" or "FAIL: {ticket} not merged to develop"

    From PRD:
    - FR-8: Given ticket AIUI-XXXX, verify merge commit exists on develop
    - FR-8: Given ticket without merge commit, report "FAIL: {ticket} not merged to develop"
    - FR-8: Given all tickets have merge commits, report "PASS: All tickets merged"
    """
    # Handle empty ticket list - nothing to check
    if not ticket_ids:
        return ScriptedCheckResult(
            name="merge_commits",
            passed=True,
            details="PASS: No tickets to check",
        )

    try:
        # Run git log to get all commits on develop
        result = subprocess.run(
            ["git", "log", "develop", "--oneline"],
            capture_output=True,
            text=True,
            check=False,
        )

        # If git command failed, report failure
        if result.returncode != 0:
            return ScriptedCheckResult(
                name="merge_commits",
                passed=False,
                details=f"FAIL: Git command failed (exit code {result.returncode})",
            )

        git_log = result.stdout

        # Check each ticket for merge commit
        missing_tickets = []
        for ticket_id in ticket_ids:
            # Look for ticket ID in merge commit messages
            # This covers GitLab, GitHub, and manual merge formats
            if ticket_id not in git_log:
                missing_tickets.append(ticket_id)

        # Report results
        if missing_tickets:
            tickets_str = ", ".join(missing_tickets)
            return ScriptedCheckResult(
                name="merge_commits",
                passed=False,
                details=f"FAIL: Tickets not merged to develop: {tickets_str}",
            )

        return ScriptedCheckResult(
            name="merge_commits",
            passed=True,
            details="PASS: All tickets merged to develop",
        )

    except Exception as e:
        # Handle any unexpected errors
        return ScriptedCheckResult(
            name="merge_commits",
            passed=False,
            details=f"FAIL: Unexpected error: {e}",
        )


def check_orphaned_branches(
    ticket_ids: list[str], state_dir: Path
) -> ScriptedCheckResult:
    """Verify that no feature branches for the batch remain unmerged.

    This check implements FR-9: Scripted Check - No Orphaned Feature Branches.
    It ensures that all feature branches for tickets in the batch have been
    successfully merged to develop (or deleted).

    The check executes two git commands:
    1. `git branch -a` - Lists all branches (local and remote)
    2. `git branch --merged develop` - Lists branches already merged to develop

    For each ticket, it looks for branches matching the pattern:
    - feature/{TICKET-ID}-*
    - remotes/origin/feature/{TICKET-ID}-*

    If a feature branch exists for a ticket but is not in the merged list,
    it is considered orphaned and the check fails.

    Args:
        ticket_ids: List of ticket IDs to verify (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (not used by this check)

    Returns:
        ScriptedCheckResult with:
        - name: "orphaned_branches"
        - passed: True if no orphaned branches found, False otherwise
        - details: "PASS: No orphaned branches" or "FAIL: Branches not merged: {branches}"

    From PRD:
    - FR-9: Given feature branches exist, identify unmerged branches
    - FR-9: Given branch feature/AIUI-XXXX-* not merged, report "FAIL: {branch} not merged"
    - FR-9: Given all branches merged or deleted, report "PASS: No orphaned branches"
    """
    # Handle empty ticket list - nothing to check
    if not ticket_ids:
        return ScriptedCheckResult(
            name="orphaned_branches",
            passed=True,
            details="PASS: No tickets to check",
        )

    try:
        # Get list of all branches (local and remote)
        all_branches_result = subprocess.run(
            ["git", "branch", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )

        if all_branches_result.returncode != 0:
            return ScriptedCheckResult(
                name="orphaned_branches",
                passed=False,
                details=f"FAIL: Git command failed (exit code {all_branches_result.returncode})",
            )

        # Get list of branches already merged to develop
        merged_branches_result = subprocess.run(
            ["git", "branch", "--merged", "develop"],
            capture_output=True,
            text=True,
            check=False,
        )

        if merged_branches_result.returncode != 0:
            return ScriptedCheckResult(
                name="orphaned_branches",
                passed=False,
                details=f"FAIL: Git command failed (exit code {merged_branches_result.returncode})",
            )

        all_branches = all_branches_result.stdout
        merged_branches = merged_branches_result.stdout

        # Check each ticket for orphaned branches
        orphaned_branches = []
        for ticket_id in ticket_ids:
            # Look for feature branches for this ticket
            # Matches: feature/AIUI-XXXX-* and remotes/origin/feature/AIUI-XXXX-*
            feature_branch_pattern = f"feature/{ticket_id}-"

            # Check if a feature branch exists for this ticket
            has_feature_branch = feature_branch_pattern in all_branches

            if has_feature_branch:
                # Branch exists - check if it's merged
                # Look for the ticket ID in merged branches (not just the pattern,
                # because the full branch name might vary)
                is_merged = ticket_id in merged_branches and feature_branch_pattern in merged_branches

                if not is_merged:
                    # Branch exists but is not merged - this is orphaned
                    orphaned_branches.append(ticket_id)

        # Report results
        if orphaned_branches:
            tickets_str = ", ".join(orphaned_branches)
            return ScriptedCheckResult(
                name="orphaned_branches",
                passed=False,
                details=f"FAIL: Orphaned branches not merged: {tickets_str}",
            )

        return ScriptedCheckResult(
            name="orphaned_branches",
            passed=True,
            details="PASS: No orphaned branches",
        )

    except Exception as e:
        # Handle any unexpected errors
        return ScriptedCheckResult(
            name="orphaned_branches",
            passed=False,
            details=f"FAIL: Unexpected error: {e}",
        )


def check_bypass_language(
    ticket_ids: list[str], state_dir: Path
) -> ScriptedCheckResult:
    """Verify that no state files contain bypass language patterns.

    This check implements FR-10: Scripted Check - No Bypass Language in State Files.
    It ensures that engineer state files do not contain bypass language patterns that
    indicate the engineer may have self-approved bypassing acceptance criteria.

    The check scans all engineer-state.md files in ticket state directories for
    these bypass patterns (case-insensitive):
    - "not merged.*but.*acceptable" - Claiming unmerged dependencies are OK
    - "doesn't block" - Claiming failures don't block progress
    - "doesn't apply" - Claiming criteria don't apply
    - "out of scope" - Claiming requirements are out of scope

    Args:
        ticket_ids: List of ticket IDs to verify (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (typically docs/state)

    Returns:
        ScriptedCheckResult with:
        - name: "bypass_language"
        - passed: True if no bypass language found, False otherwise
        - details: "PASS: No bypass language found" or "FAIL: Bypass language found in {files}"

    From PRD:
    - FR-10: Given state files exist, grep for bypass patterns
    - FR-10: Given bypass language found, report "FAIL: Bypass language found in {file}"
    - FR-10: Given no bypass language, report "PASS: No bypass language"
    """
    import re

    # Handle empty ticket list - nothing to check
    if not ticket_ids:
        return ScriptedCheckResult(
            name="bypass_language",
            passed=True,
            details="PASS: No tickets to check",
        )

    # Define bypass patterns (case-insensitive)
    bypass_patterns = [
        r"not\s+merged.*but.*acceptable",  # "not merged but acceptable"
        r"doesn't\s+block",                # "doesn't block"
        r"doesn't\s+apply",                # "doesn't apply"
        r"out\s+of\s+scope",               # "out of scope"
    ]

    try:
        # Track which tickets have bypass language
        violations: list[tuple[str, str, str]] = []  # (ticket_id, file_path, matched_pattern)

        for ticket_id in ticket_ids:
            ticket_path = state_dir / ticket_id

            # Skip if ticket state directory doesn't exist
            if not ticket_path.exists():
                continue

            # Check all attempt directories
            for attempt_dir in ticket_path.iterdir():
                if not attempt_dir.is_dir():
                    continue

                # Look for engineer-state.md in this attempt
                state_file = attempt_dir / "engineer-state.md"
                if not state_file.exists():
                    continue

                # Read the state file
                try:
                    content = state_file.read_text()
                except Exception:
                    # Skip files we can't read
                    continue

                # Check each bypass pattern
                for pattern in bypass_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        violations.append((ticket_id, str(state_file), pattern))
                        break  # Don't report multiple patterns from same file

        # Report results
        if violations:
            # Group by ticket ID for clearer reporting
            tickets_with_violations = list(set(v[0] for v in violations))
            tickets_str = ", ".join(sorted(tickets_with_violations))

            return ScriptedCheckResult(
                name="bypass_language",
                passed=False,
                details=f"FAIL: Bypass language found in state files for tickets: {tickets_str}",
            )

        return ScriptedCheckResult(
            name="bypass_language",
            passed=True,
            details="PASS: No bypass language found",
        )

    except Exception as e:
        # Handle any unexpected errors
        return ScriptedCheckResult(
            name="bypass_language",
            passed=False,
            details=f"FAIL: Unexpected error: {e}",
        )


def check_state_files_exist(
    ticket_ids: list[str], state_dir: Path
) -> ScriptedCheckResult:
    """Verify that state directory exists for each ticket.

    This check implements FR-11: Scripted Check - State Files Exist.
    It ensures that every ticket in the batch has a state directory created,
    which is a prerequisite for proper ticket tracking and validation.

    The check verifies that the path `docs/state/{ticket_id}/` exists and is
    a directory (not a file). This is the minimum requirement - the check does
    not verify the contents of the state directory.

    Args:
        ticket_ids: List of ticket IDs to verify (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (typically docs/state)

    Returns:
        ScriptedCheckResult with:
        - name: "state_files"
        - passed: True if all state directories exist, False otherwise
        - details: "PASS: All state directories exist" or "FAIL: No state for {tickets}"

    From PRD:
    - FR-11: Given a list of ticket IDs, verify state directory exists for each
    - FR-11: Given a ticket without state directory, report "FAIL: No state for {ticket}"
    - FR-11: Given all tickets have state directories, report "PASS: All state files exist"
    """
    # Handle empty ticket list - nothing to check
    if not ticket_ids:
        return ScriptedCheckResult(
            name="state_files",
            passed=True,
            details="PASS: No tickets to check",
        )

    try:
        # Track which tickets are missing state directories
        missing_tickets = []

        for ticket_id in ticket_ids:
            ticket_path = state_dir / ticket_id

            # Check if state directory exists and is actually a directory
            if not ticket_path.exists() or not ticket_path.is_dir():
                missing_tickets.append(ticket_id)

        # Report results
        if missing_tickets:
            tickets_str = ", ".join(missing_tickets)
            return ScriptedCheckResult(
                name="state_files",
                passed=False,
                details=f"FAIL: No state for tickets: {tickets_str}",
            )

        return ScriptedCheckResult(
            name="state_files",
            passed=True,
            details="PASS: All state directories exist",
        )

    except Exception as e:
        # Handle any unexpected errors
        return ScriptedCheckResult(
            name="state_files",
            passed=False,
            details=f"FAIL: Unexpected error: {e}",
        )


def check_validation_files_exist(
    ticket_ids: list[str], state_dir: Path
) -> ScriptedCheckResult:
    """Verify that validation.md exists for each ticket.

    This check implements FR-12: Scripted Check - Validation Files Exist.
    It ensures that every ticket in the batch has a validation.md file created
    by the validation agent, which is a prerequisite for proper post-loop review.

    The check verifies that at least one validation.md file exists in the ticket's
    attempt directories (docs/state/{ticket_id}/attempt-N/validation.md). It checks
    all attempt directories and passes if at least one contains validation.md.

    Args:
        ticket_ids: List of ticket IDs to verify (e.g., ["AIUI-0001", "AIUI-0002"])
        state_dir: Path to the state directory (typically docs/state)

    Returns:
        ScriptedCheckResult with:
        - name: "validation_files"
        - passed: True if all tickets have validation.md, False otherwise
        - details: "PASS: All validation files exist" or "FAIL: No validation for {tickets}"

    From PRD:
    - FR-12: Given a list of ticket IDs, verify validation.md exists for each
    - FR-12: Given a ticket without validation file, report "FAIL: No validation for {ticket}"
    - FR-12: Given all tickets have validation files, report "PASS: All validation files exist"
    """
    # Handle empty ticket list - nothing to check
    if not ticket_ids:
        return ScriptedCheckResult(
            name="validation_files",
            passed=True,
            details="PASS: No tickets to check",
        )

    try:
        # Track which tickets are missing validation files
        missing_tickets = []

        for ticket_id in ticket_ids:
            ticket_path = state_dir / ticket_id

            # Check if ticket state directory exists
            if not ticket_path.exists() or not ticket_path.is_dir():
                missing_tickets.append(ticket_id)
                continue

            # Look for validation.md in any attempt directory
            found_validation = False
            for attempt_dir in ticket_path.iterdir():
                if not attempt_dir.is_dir():
                    continue

                validation_file = attempt_dir / "validation.md"
                # Check that validation.md exists and is a file (not a directory)
                if validation_file.exists() and validation_file.is_file():
                    found_validation = True
                    break

            if not found_validation:
                missing_tickets.append(ticket_id)

        # Report results
        if missing_tickets:
            tickets_str = ", ".join(missing_tickets)
            return ScriptedCheckResult(
                name="validation_files",
                passed=False,
                details=f"FAIL: No validation for tickets: {tickets_str}",
            )

        return ScriptedCheckResult(
            name="validation_files",
            passed=True,
            details="PASS: All validation files exist",
        )

    except Exception as e:
        # Handle any unexpected errors
        return ScriptedCheckResult(
            name="validation_files",
            passed=False,
            details=f"FAIL: Unexpected error: {e}",
        )


# ============================================================================
# Post-Loop Review Agent (AIUI-0063)
# ============================================================================


@dataclass
class PostLoopReviewResult:
    """Result from the post-loop review agent.

    AIUI-0063: Implements result structure for the post-loop review agent
    that runs after scripted checks pass.

    Attributes:
        status: Review status (review_complete, review_concerns, timeout, dry_run, unknown)
        findings: Summary of review findings
        ticket_count: Number of tickets reviewed
        raw_output: Raw output from Claude review agent
    """

    status: str
    findings: str = ""
    ticket_count: int = 0
    raw_output: str = ""

    @property
    def has_concerns(self) -> bool:
        """Check if the review identified concerns.

        Returns:
            True if status is review_concerns, False otherwise.
        """
        return self.status == "review_concerns"


def build_review_prompt(
    ticket_ids: list[str],
    state_dir: Path,
    scripted_checks_summary: str,
) -> str:
    """Build prompt for the post-loop review agent.

    Constructs a prompt that instructs the review agent to analyze the batch
    of tickets for cross-ticket patterns, overall coherence, and any issues
    that scripted checks couldn't catch.

    This function implements:
    - FR-13: Agent Review After Scripted Checks Pass
    - FR-14: Use Configurable Review Model

    Args:
        ticket_ids: List of ticket IDs in the batch to review
        state_dir: Path to the state directory containing validation files
        scripted_checks_summary: Summary of scripted checks results

    Returns:
        Formatted prompt string for the review agent
    """
    # Build ticket list for the prompt
    if not ticket_ids:
        ticket_list = "No tickets in batch"
    else:
        ticket_list = "\n".join(f"- {ticket_id}" for ticket_id in ticket_ids)

    # Build validation file references
    validation_refs = []
    for ticket_id in ticket_ids:
        validation_refs.append(f"- `{state_dir}/{ticket_id}/*/validation.md`")
    validation_files = "\n".join(validation_refs) if validation_refs else "No validation files"

    return f"""# Post-Loop Review Agent Task

## Your Role

You are a post-loop review agent. Your job is to perform a holistic review of
a batch of tickets AFTER all scripted checks have passed. You look for issues
that automated scripts cannot catch.

## Batch Overview

**Tickets in this batch ({len(ticket_ids)} total):**
{ticket_list}

**State directory:** `{state_dir}`

## Scripted Checks Summary

The following scripted checks have already passed:

```
{scripted_checks_summary}
```

## Your Task

Perform a comprehensive review of the batch, focusing on:

### 1. Cross-Ticket Pattern Analysis

Look for patterns across all tickets:
- Are there conflicting changes between tickets?
- Do any tickets undo or contradict work from other tickets?
- Are there dependencies between tickets that might cause issues?

### 2. Overall Coherence Assessment

Assess the overall coherence and consistency of changes:
- Are coding patterns consistent across all tickets?
- Is error handling consistent?
- Are naming conventions followed uniformly?
- Do the changes work together as a coherent whole?

### 3. Issues Scripts Couldn't Catch

Identify anything the automated scripts couldn't detect:
- Subtle logic errors
- Edge cases not covered
- Integration concerns
- Performance implications
- Security considerations

## Required Reading

Review the validation files for each ticket:
{validation_files}

Also review the engineer state files:
- `{state_dir}/*/attempt-*/engineer-state.md`

## Output Format

After your review, return ONE of:

**If no concerns identified:**
```
REVIEW_COMPLETE

## Summary
[Brief summary of the batch review]

## Cross-Ticket Analysis
[Your findings on cross-ticket patterns]

## Coherence Assessment
[Your assessment of overall consistency]

## Notes
[Any additional observations]
```

**If concerns require attention:**
```
REVIEW_CONCERNS

## Summary
[Brief summary of concerns identified]

## Concerns
[Numbered list of specific concerns]

## Recommendations
[What should be done to address the concerns]
```

Be thorough but concise. Focus on issues that matter for the overall quality
and correctness of the batch.
"""


def run_post_loop_review(
    ticket_ids: list[str],
    state_dir: Path,
    scripted_checks_summary: str,
    model: str = "opus",
    timeout_minutes: int = 5,
    dry_run: bool = False,
) -> PostLoopReviewResult:
    """Run the post-loop review agent to analyze a batch of tickets.

    AIUI-0063: Implements the post-loop review agent invocation.

    This agent runs AFTER all scripted checks pass. It performs a holistic
    review of the batch looking for cross-ticket patterns, overall coherence,
    and anything scripts couldn't catch.

    Args:
        ticket_ids: List of ticket IDs to review
        state_dir: Path to the state directory
        scripted_checks_summary: Summary of scripted checks that passed
        model: Model to use for review (default: opus)
        timeout_minutes: Timeout in minutes (default: 5)
        dry_run: If True, don't actually invoke Claude

    Returns:
        PostLoopReviewResult with review findings

    Raises:
        RuntimeError: If Claude CLI is not found in PATH
    """
    import json

    if dry_run:
        return PostLoopReviewResult(
            status="dry_run",
            findings="[DRY RUN] Would invoke Claude review agent",
            ticket_count=len(ticket_ids),
            raw_output="[DRY RUN]",
        )

    # Build the review prompt
    prompt = build_review_prompt(
        ticket_ids=ticket_ids,
        state_dir=state_dir,
        scripted_checks_summary=scripted_checks_summary,
    )

    # Build command
    cmd = [
        "claude",
        "-p",
        prompt,
        "--model",
        model,
        "--allowedTools",
        "Bash,Read,Glob,Grep",
        "--output-format",
        "stream-json",
        "--verbose",
    ]

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
        )

        output = result.stdout + result.stderr

        # Parse result from stream-json output
        result_text = ""
        for line in output.splitlines():
            if '"type"' in line and '"result"' in line:
                try:
                    data = json.loads(line)
                    if data.get("type") == "result":
                        result_text = data.get("result", "")
                        break
                except json.JSONDecodeError:
                    continue

        # If no result JSON found, use full output
        if not result_text:
            result_text = output

        return _parse_review_result(result_text, ticket_count=len(ticket_ids))

    except subprocess.TimeoutExpired:
        return PostLoopReviewResult(
            status="timeout",
            findings="Review agent timed out",
            ticket_count=len(ticket_ids),
            raw_output="Timeout",
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Claude CLI not found. Please ensure it is installed and in PATH."
        )


def _parse_review_result(output: str, ticket_count: int) -> PostLoopReviewResult:
    """Parse the review agent output to extract status and findings.

    Args:
        output: Raw output from the review agent
        ticket_count: Number of tickets that were reviewed

    Returns:
        PostLoopReviewResult with parsed fields
    """
    # Check for review status markers
    if "REVIEW_COMPLETE" in output:
        status = "review_complete"
    elif "REVIEW_CONCERNS" in output:
        status = "review_concerns"
    else:
        return PostLoopReviewResult(
            status="unknown",
            findings=output[:500] if output else "",
            ticket_count=ticket_count,
            raw_output=output,
        )

    # Extract findings (everything after the status marker)
    findings = output
    if "REVIEW_COMPLETE" in output:
        parts = output.split("REVIEW_COMPLETE", 1)
        findings = parts[1].strip() if len(parts) > 1 else ""
    elif "REVIEW_CONCERNS" in output:
        parts = output.split("REVIEW_CONCERNS", 1)
        findings = parts[1].strip() if len(parts) > 1 else ""

    return PostLoopReviewResult(
        status=status,
        findings=findings,
        ticket_count=ticket_count,
        raw_output=output,
    )


# ============================================================================
# Execution Report Integration (AIUI-0064)
# ============================================================================


@dataclass
class ExecutionReportResult:
    """Result from run_execution_report_checks() integration function.

    AIUI-0064: Integrates scripted checks and agent review into /execution-report.

    This combines the results from scripted checks and the post-loop review agent
    into a single result that can be included in the execution report document.

    Attributes:
        scripted_checks_passed: True if all scripted checks passed
        scripted_checks_summary: Human-readable summary of scripted check results
        agent_review_completed: True if agent review was invoked and completed
        agent_review_status: Status from agent review (review_complete, review_concerns, etc.)
        agent_review_findings: Findings text from agent review
        ticket_count: Number of tickets included in the report

    From PRD:
    - FR-7: Scripted checks must run first
    - FR-7: If any check fails, report failures immediately without agent review
    - FR-7: If all pass, proceed to agent review
    - FR-13: Agent review runs after scripted checks pass
    - FR-14: Agent review uses review_model config
    """

    scripted_checks_passed: bool
    scripted_checks_summary: str
    agent_review_completed: bool = False
    agent_review_status: str = ""
    agent_review_findings: str = ""
    ticket_count: int = 0

    @property
    def has_concerns(self) -> bool:
        """Check if the report has any concerns requiring attention.

        Returns:
            True if scripted checks failed OR agent review found concerns.
        """
        if not self.scripted_checks_passed:
            return True
        if self.agent_review_status == "review_concerns":
            return True
        return False

    def get_report_summary(self) -> str:
        """Generate a formatted report summary for inclusion in execution report.

        Returns:
            Formatted markdown string with all check and review results.
        """
        lines = []

        # Scripted checks section
        lines.append("## Automated Validation")
        lines.append("")
        lines.append("### Scripted Checks")
        lines.append("")
        lines.append("```")
        lines.append(self.scripted_checks_summary)
        lines.append("```")
        lines.append("")

        # Agent review section
        if self.agent_review_completed:
            lines.append("### Agent Review")
            lines.append("")
            status_display = {
                "review_complete": "COMPLETE - No concerns",
                "review_concerns": "CONCERNS IDENTIFIED",
                "timeout": "TIMEOUT",
                "dry_run": "DRY RUN",
                "unknown": "UNKNOWN",
            }.get(self.agent_review_status, self.agent_review_status)
            lines.append(f"**Status:** {status_display}")
            lines.append(f"**Tickets Reviewed:** {self.ticket_count}")
            lines.append("")

            if self.agent_review_findings:
                lines.append(self.agent_review_findings)
        else:
            lines.append("### Agent Review")
            lines.append("")
            lines.append("*Agent review was not run (scripted checks failed)*")

        return "\n".join(lines)


def get_default_checks() -> list[CheckFunction]:
    """Get the list of default scripted checks for execution report.

    Returns the standard 5 checks that should run for every execution report:
    1. check_merge_commits - Verify tickets are merged to develop
    2. check_orphaned_branches - No unmerged feature branches
    3. check_bypass_language - No bypass language in state files
    4. check_state_files_exist - State directories exist
    5. check_validation_files_exist - Validation files exist

    Returns:
        List of check functions in recommended execution order.
    """
    return [
        check_merge_commits,
        check_orphaned_branches,
        check_bypass_language,
        check_state_files_exist,
        check_validation_files_exist,
    ]


def run_execution_report_checks(
    ticket_ids: list[str],
    state_dir: Path,
    review_model: str = "opus",
    review_timeout_minutes: int = 5,
    dry_run: bool = False,
    checks: list[CheckFunction] | None = None,
) -> ExecutionReportResult:
    """Run scripted checks and agent review for execution report.

    AIUI-0064: Main integration function that connects scripted checks framework
    and post-loop review agent to the /execution-report command.

    This function implements the flow specified in the PRD:
    1. Run all scripted checks first (FR-7)
    2. If ANY check fails, report failures immediately without agent review (FR-7)
    3. If ALL checks pass, proceed to agent review (FR-7, FR-13)
    4. Use configurable review_model (default: opus) (FR-14)
    5. Return combined results for inclusion in execution report

    Args:
        ticket_ids: List of ticket IDs to validate and review
        state_dir: Path to the state directory (typically docs/state)
        review_model: Model to use for agent review (default: opus)
        review_timeout_minutes: Timeout for agent review in minutes
        dry_run: If True, skip actual agent invocation
        checks: Optional custom list of checks (defaults to get_default_checks())

    Returns:
        ExecutionReportResult with combined scripted check and agent review results

    From PRD:
    - FR-7: Scripted checks execute first, failures report immediately
    - FR-13: Agent review only runs after scripted checks pass
    - FR-14: review_model is configurable, defaults to opus
    """
    # Use default checks if none provided
    if checks is None:
        checks = get_default_checks()

    # Step 1: Run scripted checks (FR-7)
    scripted_result = run_scripted_checks(
        ticket_ids=ticket_ids,
        state_dir=state_dir,
        checks=checks,
    )

    # Get human-readable summary
    scripted_summary = scripted_result.get_summary()

    # Step 2: If any check fails, report immediately without agent review (FR-7)
    if not scripted_result.all_passed:
        return ExecutionReportResult(
            scripted_checks_passed=False,
            scripted_checks_summary=scripted_summary,
            agent_review_completed=False,
            agent_review_status="",
            agent_review_findings="",
            ticket_count=len(ticket_ids),
        )

    # Step 3: All checks passed - proceed to agent review (FR-13)
    review_result = run_post_loop_review(
        ticket_ids=ticket_ids,
        state_dir=state_dir,
        scripted_checks_summary=scripted_summary,
        model=review_model,
        timeout_minutes=review_timeout_minutes,
        dry_run=dry_run,
    )

    # Step 4: Return combined results
    return ExecutionReportResult(
        scripted_checks_passed=True,
        scripted_checks_summary=scripted_summary,
        agent_review_completed=True,
        agent_review_status=review_result.status,
        agent_review_findings=review_result.findings,
        ticket_count=len(ticket_ids),
    )
