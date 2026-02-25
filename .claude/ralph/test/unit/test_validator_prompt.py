"""Unit tests for validator prompt builder.

AIUI-0051: Create validator prompt builder function.

Tests for the build_validator_prompt function that constructs prompts for
the validation agent. The validator reads original PRD/plan acceptance
criteria (not the engineer's interpretation) and flags bypass language.

References:
- PRD: docs/prds/2026-01-30-ralph-validation-implementation.md
- Plan: docs/plans/2026-01-30-ralph-validation-implementation.md

FR-2: Validator Reads Original Acceptance Criteria
FR-3: Validator Verifies Dependencies Merged
FR-4: Validator Flags Bypass Language
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestBuildValidatorPrompt:
    """Tests for the build_validator_prompt function."""

    def test_prompt_includes_ticket_id(self) -> None:
        """Given a ticket ID, when prompt is built, then it includes the ticket ID."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "AIUI-0051" in prompt

    def test_prompt_includes_prd_path(self) -> None:
        """Given a PRD path, when prompt is built, then it directs validator to read PRD."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/2026-01-30-feature.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "docs/prds/2026-01-30-feature.md" in prompt

    def test_prompt_includes_plan_path(self) -> None:
        """Given a plan path, when prompt is built, then it directs validator to read plan."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/2026-01-30-plan.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "docs/plans/2026-01-30-plan.md" in prompt

    def test_prompt_includes_engineer_state_path(self) -> None:
        """Given state dir and attempt, when prompt is built, then it includes state path."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=2,
        )

        # The state path should point to the engineer's state file
        assert "docs/state/AIUI-0051/attempt-2" in prompt

    def test_prompt_warns_not_to_trust_engineer_interpretation(self) -> None:
        """FR-2: Prompt must warn NOT to trust engineer's state file for criteria definition."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        # Must contain warning about not trusting engineer interpretation
        prompt_lower = prompt.lower()
        # Check for warning language about not trusting engineer's state file
        assert "original" in prompt_lower or "prd" in prompt_lower
        assert "not" in prompt_lower and "trust" in prompt_lower or "engineer" in prompt_lower

    def test_prompt_includes_bypass_language_patterns(self) -> None:
        """FR-4: Prompt must include bypass language detection patterns."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        # Must include specific bypass patterns from PRD
        prompt_lower = prompt.lower()
        assert "doesn't block" in prompt_lower or "doesn't apply" in prompt_lower
        assert "out of scope" in prompt_lower or "bypass" in prompt_lower

    def test_prompt_includes_dependency_verification_instructions(self) -> None:
        """FR-3: Prompt must include dependency merge verification instructions."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        # Must include instructions to verify dependencies via git
        prompt_lower = prompt.lower()
        assert "dependenc" in prompt_lower  # dependency/dependencies
        assert "merge" in prompt_lower or "git" in prompt_lower

    def test_prompt_specifies_expected_output_format(self) -> None:
        """Prompt must specify VALIDATION_CONFIRMED or VALIDATION_REJECTED output."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "VALIDATION_CONFIRMED" in prompt
        assert "VALIDATION_REJECTED" in prompt

    def test_prompt_specifies_validation_output_location(self) -> None:
        """FR-5: Prompt must specify validation.md output location."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        # Must include instruction to write validation.md
        assert "validation.md" in prompt.lower()
        # Should include the ticket state directory path
        assert "docs/state/AIUI-0051" in prompt

    def test_prompt_distinguishes_original_criteria_from_engineer_interpretation(self) -> None:
        """FR-2: Prompt must clearly distinguish original vs engineer interpretation."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        prompt_lower = prompt.lower()
        # Must mention comparing against original criteria
        assert "original" in prompt_lower or "prd" in prompt_lower
        # And reference what engineer claims
        assert "engineer" in prompt_lower or "claim" in prompt_lower

    def test_prompt_includes_role_description(self) -> None:
        """Prompt must include role description for the validator agent."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        prompt_lower = prompt.lower()
        # Should describe the validator's role
        assert "validat" in prompt_lower  # validator/validation
        assert "agent" in prompt_lower or "role" in prompt_lower or "your job" in prompt_lower


class TestBuildValidatorPromptEdgeCases:
    """Edge case tests for build_validator_prompt."""

    def test_prompt_with_special_characters_in_ticket_id(self) -> None:
        """Given ticket ID with hyphens, when prompt is built, then it handles correctly."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="AIUI-0051-SPECIAL",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "AIUI-0051-SPECIAL" in prompt

    def test_prompt_with_nested_paths(self) -> None:
        """Given nested directory paths, when prompt is built, then paths are correct."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="TASK-001",
            prd_path=Path("docs/prds/2026/01/feature.md"),
            plan_path=Path("docs/plans/2026/01/feature.md"),
            state_dir=Path("docs/state/nested"),
            attempt=1,
        )

        assert "docs/prds/2026/01/feature.md" in prompt
        assert "docs/plans/2026/01/feature.md" in prompt
        assert "docs/state/nested/TASK-001" in prompt

    def test_prompt_with_first_attempt(self) -> None:
        """Given attempt=1, when prompt is built, then state path is correct."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="TASK-001",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=1,
        )

        assert "attempt-1" in prompt

    def test_prompt_with_multiple_attempts(self) -> None:
        """Given attempt>1, when prompt is built, then state path reflects attempt number."""
        from commands.orchestrator import build_validator_prompt

        prompt = build_validator_prompt(
            default_branch="develop-working",
            ticket_id="TASK-001",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            state_dir=Path("docs/state"),
            attempt=3,
        )

        assert "attempt-3" in prompt

