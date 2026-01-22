"""Legacy behavior comparison tests.

This module contains tests that verify the Python implementation matches
the documented behavior of the legacy shell scripts. Since we cannot
directly run the legacy bash scripts (they were backed up and removed),
these tests serve as:

1. Documentation of the legacy behavior patterns
2. Regression tests to ensure Python implementation maintains feature parity
3. Verification of edge cases that the shell scripts handled

The legacy shell scripts being compared:
- get-next-ticket.sh - Ticket selection with dependency resolution
- ticket-start.sh - Claiming and starting work on tickets
- ticket-done.sh - Completing tickets
- mark-blocked.sh - Blocking tickets after failures
- ticket-reset.sh - Resetting blocked tickets

Legacy Behavior Documentation:
==============================

get-next-ticket.sh behavior:
- Returns first pending ticket with all dependencies satisfied
- Prefers in-progress tickets for resumption
- Skips blocked tickets
- Skips tickets with unsatisfied dependencies
- Reports status: "ready", "complete", "all_blocked", "waiting_on_dependencies"

Dependency resolution (legacy):
- Dependencies are ticket IDs that must be completed before this ticket
- A dependency is satisfied when the dependent ticket has status "completed"
- Circular dependencies cause infinite loops (protection added in Python)
- Self-referential dependencies are treated as unsatisfied

Claiming behavior (legacy with GitHub Issues):
- Uses gh CLI to add label to issue
- Uses gh CLI to assign issue to current user (optional)
- Race condition detection: add label, sleep, re-query to verify ownership
- If another ralph-* label appeared, release our claim

Output format expectations:
- JSON output with consistent field names
- Status codes matching defined constants
- Progress counts (completed, pending, blocked, total)
"""

from __future__ import annotations

from pathlib import Path


from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
    load_workflow_state,
    save_workflow_state,
)
from commands.get_next import get_next_ticket, GetNextResult, is_ticket_eligible
from commands.parse_deps import parse_dependencies, detect_circular_dependencies


# ============================================================================
# Legacy get-next-ticket.sh Behavior Comparison
# ============================================================================


class TestLegacyGetNextBehavior:
    """Tests verifying get_next matches legacy get-next-ticket.sh behavior.

    Legacy shell script behavior:
    1. First looks for in-progress tickets to resume
    2. Then finds first pending ticket with deps satisfied
    3. Returns "complete" when all tickets done
    4. Returns "all_blocked" when only blocked tickets remain
    5. Returns "waiting_on_dependencies" when all pending have unmet deps
    """

    def test_legacy_empty_queue_returns_complete(self, tmp_path: Path):
        """Legacy: Empty workflow returns "complete" status.

        Shell script behavior: If no tickets exist, exit with status=complete.
        """
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[],
            ralph=RalphState(
                tickets=[],
                dependencies={},
                attempts={},
                blocked={},
                source="github",
            ),
        )

        result = get_next_ticket(state)

        # Legacy behavior: empty queue = complete
        assert result.status == "complete"
        assert result.ticket is None
        assert result.message == "No tickets in workflow"
        assert result.total == 0

    def test_legacy_first_pending_by_order(self, tmp_path: Path):
        """Legacy: Returns first pending ticket in definition order.

        Shell script behavior: Iterate tickets array, return first eligible.
        Order is determined by plan document position.
        """
        tickets = [
            Ticket(id="TASK-003", title="Third", status="pending", dependencies=[]),
            Ticket(id="TASK-001", title="First", status="pending", dependencies=[]),
            Ticket(id="TASK-002", title="Second", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        # Legacy: first in array wins (TASK-003 is first despite ID)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-003"

    def test_legacy_in_progress_resumes_before_pending(self, tmp_path: Path):
        """Legacy: In-progress ticket is always returned for resumption.

        Shell script behavior: Check for in_progress first, return it immediately.
        This allows resuming interrupted work.
        """
        tickets = [
            Ticket(id="TASK-001", title="Pending", status="pending", dependencies=[]),
            Ticket(id="TASK-002", title="In Progress", status="in_progress", dependencies=[]),
            Ticket(id="TASK-003", title="Pending Too", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)

        # Legacy: in_progress always wins
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert "resuming" in result.message.lower()

    def test_legacy_all_completed_returns_complete(self, tmp_path: Path):
        """Legacy: All tickets completed returns "complete" status.

        Shell script behavior: If all tickets have status=completed,
        print success message and exit with complete status.
        """
        tickets = [
            Ticket(id="TASK-001", title="Done 1", status="completed", dependencies=[]),
            Ticket(id="TASK-002", title="Done 2", status="completed", dependencies=[]),
            Ticket(id="TASK-003", title="Done 3", status="completed", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            completed_count=3,
        )

        result = get_next_ticket(state)

        assert result.status == "complete"
        assert result.ticket is None
        assert result.message == "All tickets are complete"
        assert result.completed == 3

    def test_legacy_all_blocked_returns_all_blocked(self, tmp_path: Path):
        """Legacy: Only blocked tickets returns "all_blocked" status.

        Shell script behavior: If all remaining tickets are blocked,
        exit with special status for human intervention.
        """
        tickets = [
            Ticket(id="TASK-001", title="Blocked 1", status="blocked", dependencies=[], block_reason="Test"),
            Ticket(id="TASK-002", title="Blocked 2", status="blocked", dependencies=[], block_reason="Test"),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            blocked_count=2,
        )

        result = get_next_ticket(state)

        assert result.status == "all_blocked"
        assert result.ticket is None
        assert result.blocked == 2

    def test_legacy_skips_blocked_selects_pending(self, tmp_path: Path):
        """Legacy: Blocked tickets are skipped when selecting next.

        Shell script behavior: Skip any ticket with status=blocked.
        """
        tickets = [
            Ticket(id="TASK-001", title="Blocked", status="blocked", dependencies=[], block_reason="Test"),
            Ticket(id="TASK-002", title="Pending", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            blocked_count=1,
        )

        result = get_next_ticket(state)

        # Legacy: skip blocked, return first pending
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"


# ============================================================================
# Legacy Dependency Resolution Comparison
# ============================================================================


class TestLegacyDependencyResolution:
    """Tests verifying dependency resolution matches legacy behavior.

    Legacy shell script (get-next-ticket.sh) dependency behavior:
    1. Parse deps from plan markdown table
    2. Check if all deps have status "completed"
    3. If any dep is not completed, ticket is not eligible
    4. Circular deps were not handled (would infinite loop)
    """

    def test_legacy_simple_dependency_chain(self, tmp_path: Path):
        """Legacy: A->B->C chain must be processed in order.

        Shell script: Check deps array for each ticket, all must be completed.
        """
        tickets = [
            Ticket(id="TASK-001", title="First", status="pending", dependencies=[]),
            Ticket(id="TASK-002", title="Second", status="pending", dependencies=["TASK-001"]),
            Ticket(id="TASK-003", title="Third", status="pending", dependencies=["TASK-002"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        # Only TASK-001 should be eligible (no deps)
        result = get_next_ticket(state)
        assert result.ticket.id == "TASK-001"
        assert result.skipped_for_deps == 2

    def test_legacy_dependency_becomes_available_after_completion(self, tmp_path: Path):
        """Legacy: Dependent ticket available after dependency completed.

        Shell script: Re-check deps on each get-next call.
        """
        tickets = [
            Ticket(id="TASK-001", title="First", status="completed", dependencies=[]),
            Ticket(id="TASK-002", title="Second", status="pending", dependencies=["TASK-001"]),
            Ticket(id="TASK-003", title="Third", status="pending", dependencies=["TASK-002"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            completed_count=1,
        )

        # TASK-001 done, so TASK-002 is now eligible
        result = get_next_ticket(state)
        assert result.ticket.id == "TASK-002"
        # TASK-003 still waiting on TASK-002
        assert result.skipped_for_deps == 1

    def test_legacy_multiple_dependencies_all_must_complete(self, tmp_path: Path):
        """Legacy: Ticket with multiple deps waits for all.

        Shell script: Iterate all deps, all must have status=completed.
        """
        tickets = [
            Ticket(id="TASK-001", title="Dep A", status="completed", dependencies=[]),
            Ticket(id="TASK-002", title="Dep B", status="pending", dependencies=[]),
            Ticket(id="TASK-003", title="Needs Both", status="pending", dependencies=["TASK-001", "TASK-002"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            completed_count=1,
        )

        # TASK-003 needs both, only TASK-001 complete, so TASK-002 is next
        result = get_next_ticket(state)
        assert result.ticket.id == "TASK-002"

    def test_legacy_waiting_on_dependencies_status(self, tmp_path: Path):
        """Legacy: Returns waiting_on_dependencies when all pending have unmet deps.

        Shell script: If no eligible ticket found and some have deps, report waiting.
        """
        tickets = [
            Ticket(id="TASK-001", title="Blocked", status="blocked", dependencies=[], block_reason="Test"),
            Ticket(id="TASK-002", title="Waiting", status="pending", dependencies=["TASK-001"]),
            Ticket(id="TASK-003", title="Also Waiting", status="pending", dependencies=["TASK-001"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            blocked_count=1,
        )

        # TASK-001 is blocked (not completed), so deps aren't satisfied
        result = get_next_ticket(state)
        assert result.status == "waiting_on_dependencies"
        assert result.ticket is None
        assert result.skipped_for_deps == 2

    def test_legacy_circular_dependency_protection(self, tmp_path: Path):
        """Python improvement: Circular deps detected and handled.

        Legacy shell script: Would infinite loop on circular deps.
        Python: Detects cycle and treats as waiting_on_dependencies.
        """
        tickets = [
            Ticket(id="TASK-001", title="A", status="pending", dependencies=["TASK-002"]),
            Ticket(id="TASK-002", title="B", status="pending", dependencies=["TASK-001"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        # Both depend on each other, neither can start
        result = get_next_ticket(state)
        assert result.status == "waiting_on_dependencies"
        assert result.ticket is None
        # Both are skipped due to circular dependency
        assert result.skipped_for_deps == 2

    def test_legacy_self_reference_treated_as_unmet(self, tmp_path: Path):
        """Legacy: Self-referential dependency treated as unmet.

        Shell script: Would check if TASK-001 is completed, it's not, so skip.
        """
        tickets = [
            Ticket(id="TASK-001", title="Self Ref", status="pending", dependencies=["TASK-001"]),
            Ticket(id="TASK-002", title="Normal", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        # TASK-001 depends on itself (never satisfied), TASK-002 is eligible
        result = get_next_ticket(state)
        assert result.ticket.id == "TASK-002"


# ============================================================================
# Legacy Output Format Comparison
# ============================================================================


class TestLegacyOutputFormat:
    """Tests verifying output format matches legacy JSON structure.

    Legacy shell scripts output JSON with specific field names.
    These tests verify the Python version maintains compatibility.
    """

    def test_legacy_json_output_fields(self, tmp_path: Path):
        """Legacy: JSON output has specific fields with correct types.

        Shell script: echo '{"next_ticket": "...", "status": "...", ...}'
        """
        tickets = [
            Ticket(id="TASK-001", title="Test Task", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        result = get_next_ticket(state)
        json_output = result.to_dict()

        # Verify all expected fields exist with correct types
        assert isinstance(json_output.get("next_ticket"), (str, type(None)))
        assert isinstance(json_output.get("ticket_title"), (str, type(None)))
        assert isinstance(json_output["status"], str)
        assert isinstance(json_output["message"], str)
        assert isinstance(json_output["has_more"], bool)
        assert isinstance(json_output["total"], int)
        assert isinstance(json_output["pending"], int)
        assert isinstance(json_output["completed"], int)
        assert isinstance(json_output["blocked"], int)
        assert isinstance(json_output["in_progress"], int)
        assert isinstance(json_output["skipped_for_deps"], int)

    def test_legacy_status_values(self, tmp_path: Path):
        """Legacy: Status field uses specific string values.

        Shell script statuses: ready, complete, all_blocked, waiting_on_dependencies
        """
        # Test "ready" status
        state1 = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])],
        )
        result1 = get_next_ticket(state1)
        assert result1.status == "ready"

        # Test "complete" status
        state2 = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="completed", dependencies=[])],
            completed_count=1,
        )
        result2 = get_next_ticket(state2)
        assert result2.status == "complete"

        # Test "all_blocked" status
        state3 = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="blocked", dependencies=[], block_reason="X")],
            blocked_count=1,
        )
        result3 = get_next_ticket(state3)
        assert result3.status == "all_blocked"

        # Test "waiting_on_dependencies" status
        state4 = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[Ticket(id="TASK-001", title="Test", status="pending", dependencies=["TASK-002"])],
        )
        result4 = get_next_ticket(state4)
        assert result4.status == "waiting_on_dependencies"

    def test_legacy_count_accuracy(self, tmp_path: Path):
        """Legacy: Progress counts are accurate.

        Shell script: Count each status type for progress reporting.
        """
        tickets = [
            Ticket(id="TASK-001", title="Completed", status="completed", dependencies=[]),
            Ticket(id="TASK-002", title="Pending 1", status="pending", dependencies=[]),
            Ticket(id="TASK-003", title="Pending 2", status="pending", dependencies=[]),
            Ticket(id="TASK-004", title="Blocked", status="blocked", dependencies=[], block_reason="X"),
            Ticket(id="TASK-005", title="In Progress", status="in_progress", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
            completed_count=1,
            blocked_count=1,
        )

        result = get_next_ticket(state)

        assert result.total == 5
        assert result.completed == 1
        assert result.pending == 2
        assert result.blocked == 1
        assert result.in_progress == 1


# ============================================================================
# Legacy is_ticket_eligible Function Comparison
# ============================================================================


class TestLegacyIsTicketEligible:
    """Tests verifying is_ticket_eligible helper matches legacy behavior.

    This helper function encapsulates the eligibility check logic
    that was inline in the legacy shell script.
    """

    def test_eligible_when_pending_no_deps(self):
        """Legacy: Pending ticket with no deps is eligible."""
        ticket = Ticket(id="TASK-001", title="Test", status="pending", dependencies=[])
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids)

    def test_eligible_when_pending_deps_satisfied(self):
        """Legacy: Pending ticket with all deps completed is eligible."""
        ticket = Ticket(id="TASK-002", title="Test", status="pending", dependencies=["TASK-001"])
        completed_ids: set[str] = {"TASK-001"}

        assert is_ticket_eligible(ticket, completed_ids)

    def test_not_eligible_when_blocked(self):
        """Legacy: Blocked ticket is never eligible."""
        ticket = Ticket(id="TASK-001", title="Test", status="blocked", dependencies=[], block_reason="X")
        completed_ids: set[str] = set()

        assert not is_ticket_eligible(ticket, completed_ids)

    def test_not_eligible_when_completed(self):
        """Legacy: Completed ticket is not eligible (already done)."""
        ticket = Ticket(id="TASK-001", title="Test", status="completed", dependencies=[])
        completed_ids: set[str] = set()

        assert not is_ticket_eligible(ticket, completed_ids)

    def test_not_eligible_when_deps_not_satisfied(self):
        """Legacy: Ticket with unmet dependency is not eligible."""
        ticket = Ticket(id="TASK-002", title="Test", status="pending", dependencies=["TASK-001"])
        completed_ids: set[str] = set()  # TASK-001 not completed

        assert not is_ticket_eligible(ticket, completed_ids)

    def test_not_eligible_when_partial_deps_satisfied(self):
        """Legacy: All dependencies must be satisfied, not just some."""
        ticket = Ticket(id="TASK-003", title="Test", status="pending", dependencies=["TASK-001", "TASK-002"])
        completed_ids: set[str] = {"TASK-001"}  # Only one of two

        assert not is_ticket_eligible(ticket, completed_ids)

    def test_in_progress_is_eligible(self):
        """Legacy: In-progress ticket is eligible (for resumption)."""
        ticket = Ticket(id="TASK-001", title="Test", status="in_progress", dependencies=[])
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids)


# ============================================================================
# Legacy Dependency Parsing Comparison
# ============================================================================


class TestLegacyDependencyParsing:
    """Tests verifying dependency parsing matches legacy parse-plan-deps.sh.

    Legacy shell script:
    - Parse markdown table with ID and Dependencies columns
    - Support both explicit IDs (TASK-001) and row numbers (1, 2, 3)
    - Handle "-" and "None" as empty dependencies
    - Extract comma-separated dependency lists
    """

    def test_legacy_table_format_explicit_ids(self, tmp_path: Path):
        """Legacy: Parse table with explicit ticket IDs."""
        plan = tmp_path / "plan.md"
        plan.write_text("""## Tickets
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | TASK-001 |
| TASK-003 | Third | TASK-001, TASK-002 |
""")

        result = parse_dependencies(plan)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == ["TASK-001"]
        assert set(result["TASK-003"]) == {"TASK-001", "TASK-002"}

    def test_legacy_table_format_row_numbers(self, tmp_path: Path):
        """Legacy: Parse table with row numbers mapped to ticket IDs."""
        plan = tmp_path / "plan.md"
        plan.write_text("""## Tickets
| # | Title | Dependencies |
|---|-------|--------------|
| 1 | First | - |
| 2 | Second | 1 |
| 3 | Third | 1, 2 |
""")

        result = parse_dependencies(plan, ticket_prefix="SDLC", start_num=13)

        # Row 1 -> SDLC-0013, Row 2 -> SDLC-0014, Row 3 -> SDLC-0015
        assert result["SDLC-0013"] == []
        assert result["SDLC-0014"] == ["SDLC-0013"]
        assert set(result["SDLC-0015"]) == {"SDLC-0013", "SDLC-0014"}

    def test_legacy_none_and_dash_as_empty(self, tmp_path: Path):
        """Legacy: Both 'None' and '-' mean no dependencies."""
        plan = tmp_path / "plan.md"
        plan.write_text("""## Tickets
| ID | Title | Dependencies |
|----|-------|--------------|
| TASK-001 | First | - |
| TASK-002 | Second | None |
| TASK-003 | Third |  |
""")

        result = parse_dependencies(plan)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == []
        assert result["TASK-003"] == []

    def test_legacy_section_format(self, tmp_path: Path):
        """Legacy: Parse section-based format with ### headers."""
        plan = tmp_path / "plan.md"
        plan.write_text("""## Implementation

### TASK-001: First Task

- **Dependencies:** None

### TASK-002: Second Task

- **Dependencies:** TASK-001

### TASK-003: Third Task

- **Dependencies:** TASK-001, TASK-002
""")

        result = parse_dependencies(plan)

        assert result["TASK-001"] == []
        assert result["TASK-002"] == ["TASK-001"]
        assert set(result["TASK-003"]) == {"TASK-001", "TASK-002"}


# ============================================================================
# Legacy Circular Dependency Detection
# ============================================================================


class TestLegacyCircularDependencyDetection:
    """Tests for circular dependency detection (Python improvement).

    NOTE: The legacy shell scripts did NOT detect circular dependencies.
    They would infinite loop or produce incorrect results.

    The Python implementation adds this safety feature while maintaining
    all other legacy behaviors.
    """

    def test_detects_simple_cycle(self):
        """Python improvement: Detects A -> B -> A cycle.

        Verifies that when a cycle exists, the system returns
        waiting_on_dependencies status (cannot proceed).
        """
        deps = {
            "TASK-001": ["TASK-002"],
            "TASK-002": ["TASK-001"],
        }

        cycles = detect_circular_dependencies(deps)

        # Verify cycle detection returns cycles
        assert len(cycles) > 0
        # Cycle contains both nodes
        all_nodes = set()
        for cycle in cycles:
            all_nodes.update(cycle)
        assert "TASK-001" in all_nodes
        assert "TASK-002" in all_nodes

        # Verify behavior: tickets with circular deps cannot proceed
        # (tested in test_legacy_circular_dependency_protection and
        # test_improvement_circular_dependency_handling)

    def test_detects_self_reference(self):
        """Python improvement: Detects self-referential dependency.

        Verifies that self-reference is treated as unmet dependency
        (ticket will be skipped, other tickets can proceed).
        """
        deps = {
            "TASK-001": ["TASK-001"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) > 0

        # Verify behavior: self-referential ticket is skipped
        # (tested in test_legacy_self_reference_treated_as_unmet)

    def test_no_false_positives_for_linear_chain(self):
        """Verifies no false positive for valid linear chain."""
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-002"],
            "TASK-004": ["TASK-003"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 0

    def test_no_false_positives_for_diamond(self):
        """Verifies no false positive for diamond dependency pattern."""
        # Diamond: A -> B -> D, A -> C -> D
        deps = {
            "TASK-001": [],
            "TASK-002": ["TASK-001"],
            "TASK-003": ["TASK-001"],
            "TASK-004": ["TASK-002", "TASK-003"],
        }

        cycles = detect_circular_dependencies(deps)

        assert len(cycles) == 0


# ============================================================================
# Intentional Differences Documentation
# ============================================================================


class TestIntentionalDifferencesFromLegacy:
    """Documents and tests intentional improvements over legacy behavior.

    These tests document where the Python implementation intentionally
    differs from the legacy shell scripts for improved robustness.
    """

    def test_improvement_circular_dependency_handling(self, tmp_path: Path):
        """IMPROVEMENT: Python handles circular deps gracefully.

        Legacy: Would infinite loop or crash
        Python: Returns waiting_on_dependencies status
        """
        tickets = [
            Ticket(id="TASK-001", title="A", status="pending", dependencies=["TASK-002"]),
            Ticket(id="TASK-002", title="B", status="pending", dependencies=["TASK-001"]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        # Should NOT hang or crash - returns gracefully
        result = get_next_ticket(state)
        assert result.status == "waiting_on_dependencies"

    def test_improvement_state_persistence(self, tmp_path: Path):
        """IMPROVEMENT: State survives save/load cycles.

        Legacy: Direct file write
        Python: Reliable state persistence with save/load

        Verifies that modifications to state are correctly persisted.
        """
        tickets = [
            Ticket(id="TASK-001", title="Test", status="pending", dependencies=[]),
        ]
        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=tickets,
        )

        state_file = tmp_path / "state.json"
        save_workflow_state(state, state_file)

        # Load and verify data is preserved
        loaded = load_workflow_state(state_file)
        assert loaded.tickets[0].title == "Test"
        assert loaded.tickets[0].status == "pending"

        # Modify and save
        loaded.tickets[0].title = "Modified"
        save_workflow_state(loaded, state_file)

        # Verify modification persisted
        final = load_workflow_state(state_file)
        assert final.tickets[0].title == "Modified"
