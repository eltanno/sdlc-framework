"""Integration tests for PM tool flow.

This module tests the PM tool integration including:
- Full workflow: setup -> get_next -> ticket_done
- Parallel instance simulation (race condition handling)
- Dependency checking against closed issues
- State reset on PRD/state mismatch

These tests mock the gh CLI subprocess calls to simulate GitHub operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from core.pm import (
    LocalPM,
    PMError,
    TicketStatus,
    TicketInfo,
)
from core.state import (
    WorkflowState,
    Ticket,
    RalphState,
    load_workflow_state,
    save_workflow_state,
)
from commands.get_next import (
    get_next_ticket,
    claim_ticket_with_race_detection,
)
from commands.ticket_done import ticket_done
from commands.setup import run_setup, detect_ticket_mismatch


# ============================================================================
# Mock PM Tool for Testing
# ============================================================================


class MockPMTool:
    """Mock PM tool for testing that simulates GitHub-like behavior.

    This mock allows precise control over ticket states and label operations
    for testing complex scenarios like race conditions.
    """

    def __init__(self) -> None:
        """Initialize mock with empty state."""
        # Ticket state: {ticket_id: {"status": TicketStatus, "labels": set[str]}}
        self._tickets: dict[str, dict[str, Any]] = {}
        # Track operation calls for verification
        self._operations: list[tuple[str, Any]] = []

    def add_ticket(
        self,
        ticket_id: str,
        status: TicketStatus = TicketStatus.OPEN,
        labels: list[str] | None = None,
        title: str | None = None,
    ) -> None:
        """Add a ticket to the mock state."""
        self._tickets[ticket_id] = {
            "status": status,
            "labels": set(labels or []),
            "title": title or f"Ticket {ticket_id}",
        }

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of a ticket."""
        self._operations.append(("get_ticket_status", ticket_id))
        if ticket_id not in self._tickets:
            raise PMError(f"Ticket {ticket_id} not found")
        return self._tickets[ticket_id]["status"]

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a ticket by adding a label."""
        self._operations.append(("claim_ticket", (ticket_id, label)))
        if ticket_id not in self._tickets:
            return False
        self._tickets[ticket_id]["labels"].add(label)
        return True

    def close_ticket(self, ticket_id: str) -> bool:
        """Close a ticket."""
        self._operations.append(("close_ticket", ticket_id))
        if ticket_id not in self._tickets:
            return False
        self._tickets[ticket_id]["status"] = TicketStatus.CLOSED
        return True

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark a ticket as blocked."""
        self._operations.append(("add_blocked_label", (ticket_id, reason)))
        if ticket_id not in self._tickets:
            return False
        self._tickets[ticket_id]["labels"].add("blocked")
        self._tickets[ticket_id]["status"] = TicketStatus.BLOCKED
        return True

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if a ticket is claimed by any Ralph instance."""
        self._operations.append(("is_ticket_claimed", ticket_id))
        if ticket_id not in self._tickets:
            return (False, None)

        labels = self._tickets[ticket_id]["labels"]
        for label in labels:
            if label.startswith("ralph-"):
                return (True, label)

        return (False, None)

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open tickets from the provided list."""
        self._operations.append(("get_open_tickets", ticket_ids))
        result = []
        for ticket_id in ticket_ids:
            if ticket_id in self._tickets:
                ticket = self._tickets[ticket_id]
                if ticket["status"] in (TicketStatus.OPEN, TicketStatus.BLOCKED):
                    result.append(
                        TicketInfo(
                            id=ticket_id,
                            title=ticket["title"],
                            status=ticket["status"],
                            labels=list(ticket["labels"]),
                        )
                    )
        return result

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a label from a ticket."""
        self._operations.append(("remove_label", (ticket_id, label)))
        if ticket_id not in self._tickets:
            return False
        self._tickets[ticket_id]["labels"].discard(label)
        return True

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign a ticket to the current user."""
        self._operations.append(("assign_to_self", ticket_id))
        return True

    def get_operations(self) -> list[tuple[str, Any]]:
        """Get list of operations that were called."""
        return self._operations.copy()

    def clear_operations(self) -> None:
        """Clear operation history."""
        self._operations.clear()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pm() -> MockPMTool:
    """Create a mock PM tool instance."""
    return MockPMTool()


@pytest.fixture
def pm_workflow(tmp_path: Path, mock_pm: MockPMTool) -> tuple[Path, WorkflowState, MockPMTool]:
    """Create a workflow for PM tool testing with mocked tickets.

    Uses hybrid schema with both tickets array (for mark_ticket_done) and
    ralph state (for PM tool operations).

    Returns:
        Tuple of (state_file_path, workflow_state, mock_pm_tool)
    """
    # Add tickets to mock PM tool
    mock_pm.add_ticket("74", TicketStatus.OPEN, title="Create PM tool abstraction layer")
    mock_pm.add_ticket("75", TicketStatus.OPEN, title="Add pm.tool config loading")
    mock_pm.add_ticket("76", TicketStatus.OPEN, title="Implement LocalPM fallback")

    # Create tickets array (needed for mark_ticket_done)
    tickets = [
        Ticket(id="74", title="Create PM tool abstraction layer", status="pending", dependencies=[]),
        Ticket(id="75", title="Add pm.tool config loading", status="pending", dependencies=[]),
        Ticket(id="76", title="Implement LocalPM fallback", status="pending", dependencies=["74"]),
    ]

    # Create Ralph state with PM tool ticket IDs
    ralph = RalphState(
        tickets=["74", "75", "76"],
        dependencies={"76": ["74"]},  # 76 depends on 74
        attempts={},
        blocked={},
        source="github",
    )

    # Create workflow state (hybrid schema for testing)
    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,  # Include tickets array for mark_ticket_done compatibility
        ralph=ralph,
    )

    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)

    return state_file, state, mock_pm


@pytest.fixture
def dependency_workflow(tmp_path: Path, mock_pm: MockPMTool) -> tuple[Path, WorkflowState, MockPMTool]:
    """Create a workflow with dependencies for testing.

    Dependency graph:
    - 74: no dependencies (ready)
    - 75: depends on 74 (blocked until 74 closed)
    - 76: depends on 74 and 75 (blocked until both closed)

    Returns:
        Tuple of (state_file_path, workflow_state, mock_pm_tool)
    """
    mock_pm.add_ticket("74", TicketStatus.OPEN, title="First task")
    mock_pm.add_ticket("75", TicketStatus.OPEN, title="Second task")
    mock_pm.add_ticket("76", TicketStatus.OPEN, title="Third task")

    # Create tickets array (needed for mark_ticket_done)
    tickets = [
        Ticket(id="74", title="First task", status="pending", dependencies=[]),
        Ticket(id="75", title="Second task", status="pending", dependencies=["74"]),
        Ticket(id="76", title="Third task", status="pending", dependencies=["74", "75"]),
    ]

    ralph = RalphState(
        tickets=["74", "75", "76"],
        dependencies={"75": ["74"], "76": ["74", "75"]},
        attempts={},
        blocked={},
        source="github",
    )

    state = WorkflowState(
        version="2.0",
        prd_path=Path("docs/prds/test.md"),
        plan_path=Path("docs/plans/test.md"),
        tickets=tickets,  # Include tickets array for mark_ticket_done compatibility
        ralph=ralph,
    )

    state_file = tmp_path / "workflow-state.json"
    save_workflow_state(state, state_file)

    return state_file, state, mock_pm


# ============================================================================
# Test Cases: Full Workflow (setup -> get_next -> ticket_done)
# ============================================================================


class TestFullPMWorkflow:
    """Tests for the complete PM tool workflow."""

    def test_workflow_setup_get_next_done_sequence(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a workflow with open tickets, when running the full flow,
        then tickets are claimed, worked on, and completed correctly."""
        state_file, state, mock_pm = pm_workflow

        # Step 1: Get next ticket (should be 74 - first with no deps)
        result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        assert result.ticket is not None
        assert result.ticket.id == "74"
        assert result.status == "ready"

        # Verify ticket was claimed
        is_claimed, claiming_label = mock_pm.is_ticket_claimed("74")
        assert is_claimed
        assert claiming_label == "ralph-1"

        # Step 2: Complete the ticket
        done_result = ticket_done(
            ticket_id="74",
            pr_number="100",
            issue_number=74,
            state_file=state_file,
            pm_tool=mock_pm,
            ralph_label="ralph-1",
        )

        assert done_result["status"] == "completed"

        # Verify ticket is closed in PM tool
        assert mock_pm.get_ticket_status("74") == TicketStatus.CLOSED

        # Verify label was removed
        is_claimed_after, _ = mock_pm.is_ticket_claimed("74")
        assert not is_claimed_after

        # Step 3: Get next ticket (should be 75 - no deps now, or 76 has dep on 74)
        # Since we closed 74, 76's dependency on 74 is now satisfied
        # But 75 has no dependency in this fixture, and 76 depends on 74 only
        reloaded_state = load_workflow_state(state_file)
        result2 = get_next_ticket(reloaded_state, pm_tool=mock_pm, ralph_label="ralph-1")

        # 75 should be next (76 still depends on 74 which is now closed)
        # But in the fixture, 76 depends on 74 - which is closed
        # So both 75 and 76 should be eligible, 75 comes first
        assert result2.ticket is not None
        assert result2.ticket.id in ["75", "76"]

    def test_workflow_completes_all_tickets(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a workflow, when all tickets are completed,
        then final status is 'complete' with no more tickets."""
        state_file, state, mock_pm = pm_workflow

        ticket_ids = ["74", "75", "76"]

        # Complete all tickets in order
        for ticket_id in ticket_ids:
            # Get next
            current_state = load_workflow_state(state_file)
            result = get_next_ticket(current_state, pm_tool=mock_pm, ralph_label="ralph-1")

            if result.ticket is None:
                # May be waiting on dependencies
                continue

            # Mark done
            ticket_done(
                ticket_id=result.ticket.id,
                pr_number=f"10{ticket_id}",
                issue_number=int(result.ticket.id),
                state_file=state_file,
                pm_tool=mock_pm,
                ralph_label="ralph-1",
            )

        # Verify all tickets are closed
        for ticket_id in ticket_ids:
            assert mock_pm.get_ticket_status(ticket_id) == TicketStatus.CLOSED

        # Final get_next should return complete
        final_state = load_workflow_state(state_file)
        final_result = get_next_ticket(final_state, pm_tool=mock_pm, ralph_label="ralph-1")

        assert final_result.ticket is None
        assert final_result.status == "complete"
        assert final_result.completed == 3

    def test_workflow_resumes_in_progress_ticket(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a ticket claimed by this instance, when getting next ticket,
        then the in-progress ticket is returned for resumption."""
        state_file, state, mock_pm = pm_workflow

        # Simulate a ticket already claimed by this instance
        mock_pm.claim_ticket("74", "ralph-1")

        # Get next ticket
        result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should return the claimed ticket for resumption
        assert result.ticket is not None
        assert result.ticket.id == "74"
        assert "resuming" in result.message.lower()


# ============================================================================
# Test Cases: Parallel Instance Simulation (Race Condition Handling)
# ============================================================================


class TestParallelInstanceSimulation:
    """Tests for race condition handling with multiple Ralph instances."""

    def test_race_condition_detection_other_instance_wins(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given two instances trying to claim the same ticket,
        when another instance wins the race,
        then this instance releases its claim and skips the ticket."""
        state_file, state, mock_pm = pm_workflow

        # Simulate race: after our claim, another instance has already claimed
        original_is_claimed = mock_pm.is_ticket_claimed

        def mock_is_claimed_race(ticket_id: str) -> tuple[bool, str | None]:
            """After we claim, another instance's label appears (they won)."""
            if ticket_id == "74":
                # Return the other instance's label as the winner
                return (True, "ralph-2")
            return original_is_claimed(ticket_id)

        mock_pm.is_ticket_claimed = mock_is_claimed_race  # type: ignore

        # Patch sleep to speed up test
        with patch("commands.get_next.time.sleep"):
            result = claim_ticket_with_race_detection(
                pm_tool=mock_pm,
                ticket_id="74",
                ralph_label="ralph-1",
            )

        # Claim should fail because ralph-2 won
        assert result is False

        # Verify our label was removed (released)
        operations = mock_pm.get_operations()
        remove_ops = [op for op in operations if op[0] == "remove_label"]
        assert len(remove_ops) == 1
        assert remove_ops[0][1] == ("74", "ralph-1")

    def test_race_condition_detection_this_instance_wins(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given two instances trying to claim the same ticket,
        when this instance wins the race,
        then the claim succeeds."""
        state_file, state, mock_pm = pm_workflow

        # Patch sleep to speed up test
        with patch("commands.get_next.time.sleep"):
            result = claim_ticket_with_race_detection(
                pm_tool=mock_pm,
                ticket_id="74",
                ralph_label="ralph-1",
            )

        # Claim should succeed - we added our label first and won
        assert result is True

        # Verify our label is on the ticket
        is_claimed, label = mock_pm.is_ticket_claimed("74")
        assert is_claimed
        assert label == "ralph-1"

    def test_ticket_claimed_by_other_instance_is_skipped(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a ticket already claimed by another instance,
        when getting next ticket,
        then that ticket is skipped."""
        state_file, state, mock_pm = pm_workflow

        # Simulate ticket 74 claimed by another instance
        mock_pm.claim_ticket("74", "ralph-2")

        # Patch sleep to avoid waiting
        with patch("commands.get_next.time.sleep"):
            result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should skip 74 and return 75 (next available without dependencies)
        assert result.ticket is not None
        assert result.ticket.id == "75"

    def test_all_tickets_claimed_by_others_returns_complete(
        self, tmp_path: Path
    ):
        """Given all tickets are pre-claimed by other instances,
        when getting next ticket,
        then status is 'complete' (no pending tickets for this instance).

        Note: Pre-claimed tickets (labels already present) are silently skipped.
        The 'waiting_on_claims' status only occurs when race conditions are detected
        during the claim attempt. When all tickets are already claimed before we
        attempt to claim them, they're effectively not pending for this instance.
        """
        mock_pm = MockPMTool()

        # Add tickets, all claimed by other instances
        mock_pm.add_ticket("74", TicketStatus.OPEN, labels=["ralph-2"])
        mock_pm.add_ticket("75", TicketStatus.OPEN, labels=["ralph-3"])

        ralph = RalphState(
            tickets=["74", "75"],
            dependencies={},
            attempts={},
            blocked={},
            source="github",
        )

        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[],
            ralph=ralph,
        )

        with patch("commands.get_next.time.sleep"):
            result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # All tickets are pre-claimed by others - no pending for this instance
        assert result.ticket is None
        # Status is 'complete' because from this instance's perspective, no tickets are available
        assert result.status == "complete"
        assert result.pending == 2  # Still 2 pending in PM tool

    def test_no_ralph_label_skips_claiming(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given no ralph_label is provided,
        when getting next ticket,
        then claiming is skipped (single-instance mode)."""
        state_file, state, mock_pm = pm_workflow

        # No ralph_label - single instance mode
        result = get_next_ticket(state, pm_tool=mock_pm, ralph_label=None)

        # Should return ticket without claiming
        assert result.ticket is not None
        assert result.ticket.id == "74"

        # No claim operations should be recorded
        operations = mock_pm.get_operations()
        claim_ops = [op for op in operations if op[0] == "claim_ticket"]
        assert len(claim_ops) == 0


# ============================================================================
# Test Cases: Dependency Checking Against Closed Issues
# ============================================================================


class TestDependencyCheckingAgainstClosed:
    """Tests for dependency satisfaction checking against PM tool status."""

    def test_dependency_satisfied_when_issue_closed(
        self, dependency_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a ticket depends on another ticket,
        when the dependency is closed in PM tool,
        then the dependent ticket becomes available."""
        state_file, state, mock_pm = dependency_workflow

        # Initially, 75 depends on 74 (open)
        # Get next should return 74 (no deps)
        result1 = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")
        assert result1.ticket is not None
        assert result1.ticket.id == "74"

        # Close ticket 74 in PM tool
        mock_pm.close_ticket("74")

        # Now 75 should be available (its dependency 74 is closed)
        mock_pm.clear_operations()
        result2 = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        assert result2.ticket is not None
        assert result2.ticket.id == "75"

    def test_dependency_not_satisfied_when_issue_open(
        self, dependency_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a ticket depends on an open ticket,
        when getting next ticket,
        then the dependent ticket is skipped."""
        state_file, state, mock_pm = dependency_workflow

        # Skip ticket 74 for this test (claim it with another instance)
        mock_pm.claim_ticket("74", "ralph-2")

        with patch("commands.get_next.time.sleep"):
            result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # 75 depends on 74 (open), 76 depends on 74 and 75
        # Neither should be available
        # 74 is claimed by another instance
        # Result could be waiting_on_dependencies or waiting_on_claims
        assert result.ticket is None
        # Either all claimed or all waiting on deps
        assert result.status in ["waiting_on_dependencies", "waiting_on_claims"]

    def test_chained_dependencies_resolved_in_order(
        self, dependency_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given chained dependencies (A -> B -> C),
        when completing tickets in order,
        then each subsequent ticket becomes available."""
        state_file, state, mock_pm = dependency_workflow

        # Step 1: Get 74 (no deps)
        result1 = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")
        assert result1.ticket.id == "74"
        mock_pm.close_ticket("74")
        mock_pm.remove_label("74", "ralph-1")

        # Step 2: Get 75 (depends on 74, now closed)
        mock_pm.clear_operations()
        result2 = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")
        assert result2.ticket.id == "75"
        mock_pm.close_ticket("75")
        mock_pm.remove_label("75", "ralph-1")

        # Step 3: Get 76 (depends on 74 and 75, both now closed)
        mock_pm.clear_operations()
        result3 = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")
        assert result3.ticket.id == "76"

    def test_multiple_dependencies_all_must_be_closed(
        self, dependency_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given a ticket with multiple dependencies,
        when only some dependencies are closed,
        then the ticket is not available."""
        state_file, state, mock_pm = dependency_workflow

        # Close only 74, not 75
        mock_pm.close_ticket("74")

        # Ticket 76 depends on both 74 AND 75
        # 76 should not be available yet
        result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should return 75 (its only dep 74 is closed)
        assert result.ticket is not None
        assert result.ticket.id == "75"


# ============================================================================
# Test Cases: State Reset on Mismatch
# ============================================================================


class TestStateResetOnMismatch:
    """Tests for state reset when PRD and state tickets don't match."""

    def test_detect_mismatch_new_tickets_added(self):
        """Given new tickets in PRD that are not in state,
        when detecting mismatch,
        then added tickets are identified."""
        prd_tickets = ["SDLC-001", "SDLC-002", "SDLC-003"]
        state_tickets = ["SDLC-001", "SDLC-002"]

        result = detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert "SDLC-003" in result.added
        assert result.removed == []

    def test_detect_mismatch_tickets_removed(self):
        """Given tickets in state that are not in PRD,
        when detecting mismatch,
        then removed tickets are identified."""
        prd_tickets = ["SDLC-001", "SDLC-002"]
        state_tickets = ["SDLC-001", "SDLC-002", "SDLC-003"]

        result = detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert result.added == []
        assert "SDLC-003" in result.removed

    def test_detect_mismatch_both_added_and_removed(self):
        """Given both new and removed tickets,
        when detecting mismatch,
        then both are identified."""
        prd_tickets = ["SDLC-001", "SDLC-004"]
        state_tickets = ["SDLC-001", "SDLC-002", "SDLC-003"]

        result = detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is True
        assert "SDLC-004" in result.added
        assert "SDLC-002" in result.removed
        assert "SDLC-003" in result.removed

    def test_detect_no_mismatch_when_same(self):
        """Given PRD and state have same tickets,
        when detecting mismatch,
        then no mismatch is reported."""
        prd_tickets = ["SDLC-001", "SDLC-002"]
        state_tickets = ["SDLC-001", "SDLC-002"]

        result = detect_ticket_mismatch(prd_tickets, state_tickets)

        assert result.has_mismatch is False
        assert result.added == []
        assert result.removed == []

    def test_setup_resets_state_on_mismatch_noninteractive(self, tmp_path: Path):
        """Given mismatch between PRD and existing state,
        when running setup in non-interactive mode,
        then state is reset to match PRD with warning."""
        # Create PRD with tickets
        prd_content = """# Test PRD

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-001 | First task | - |
| SDLC-002 | Second task | - |
| SDLC-003 | New task | SDLC-001 |
"""
        prd_file = tmp_path / "prd.md"
        prd_file.write_text(prd_content)

        # Create plan
        plan_content = """# Test Plan

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-001 | First task | - |
| SDLC-002 | Second task | - |
| SDLC-003 | New task | SDLC-001 |
"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        # Create existing state with different tickets
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
            ralph=RalphState(
                tickets=["SDLC-001", "SDLC-002", "SDLC-OLD"],  # SDLC-OLD will be removed
                dependencies={},
                attempts={"SDLC-001": 2},  # Should be preserved
                blocked={},
                source="github",
            ),
        )
        state_file = tmp_path / "workflow-state.json"
        save_workflow_state(existing_state, state_file)

        # Run setup (non-interactive)
        result = run_setup(
            prd_path=prd_file,
            plan_path=plan_file,
            state_file=state_file,
            interactive=False,
        )

        # Setup should succeed with mismatch warning
        assert result.success is True
        assert result.mismatch_detected is True
        assert "SDLC-003" in (result.tickets_added or [])
        assert "SDLC-OLD" in (result.tickets_removed or [])
        assert result.warning is not None
        assert "mismatch" in result.warning.lower() or "reconciled" in result.warning.lower()

        # Verify state was reset to PRD tickets
        reloaded_state = load_workflow_state(state_file)
        assert reloaded_state.ralph is not None
        assert set(reloaded_state.ralph.tickets) == {"SDLC-001", "SDLC-002", "SDLC-003"}
        # Attempt count for SDLC-001 should be preserved
        assert reloaded_state.ralph.attempts.get("SDLC-001") == 2

    def test_setup_preserves_attempt_counts_on_reset(self, tmp_path: Path):
        """Given existing state with attempt counts,
        when state is reset due to mismatch,
        then attempt counts for matching tickets are preserved."""
        # Create PRD with subset of original tickets plus new one
        prd_content = """# Test PRD

## Tickets

| ID | Title | Dependencies |
|----|-------|--------------|
| SDLC-001 | First task | - |
| SDLC-003 | New task | - |
"""
        prd_file = tmp_path / "prd.md"
        prd_file.write_text(prd_content)

        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Test Plan\n")

        # Create existing state with attempt counts
        existing_state = WorkflowState(
            version="2.0",
            prd_path=prd_file,
            plan_path=plan_file,
            tickets=[],
            ralph=RalphState(
                tickets=["SDLC-001", "SDLC-002"],
                dependencies={},
                attempts={"SDLC-001": 3, "SDLC-002": 1},  # SDLC-002 will be lost
                blocked={"SDLC-002": "Test block"},
                source="github",
            ),
        )
        state_file = tmp_path / "workflow-state.json"
        save_workflow_state(existing_state, state_file)

        # Run setup
        result = run_setup(
            prd_path=prd_file,
            plan_path=plan_file,
            state_file=state_file,
            interactive=False,
        )

        assert result.success is True

        # Verify attempt count preserved for SDLC-001, lost for SDLC-002
        reloaded_state = load_workflow_state(state_file)
        assert reloaded_state.ralph is not None
        assert reloaded_state.ralph.attempts.get("SDLC-001") == 3
        assert "SDLC-002" not in reloaded_state.ralph.attempts


# ============================================================================
# Test Cases: Error Handling
# ============================================================================


class TestPMToolErrorHandling:
    """Tests for error handling in PM tool operations."""

    def test_get_next_handles_pm_error(self, tmp_path: Path):
        """Given PM tool raises an error,
        when getting next ticket,
        then error result is returned."""
        mock_pm = MockPMTool()

        # Make get_open_tickets raise an error
        def raise_error(*args: Any) -> list[TicketInfo]:
            raise PMError("API rate limit exceeded")

        mock_pm.get_open_tickets = raise_error  # type: ignore

        ralph = RalphState(
            tickets=["74"],
            dependencies={},
            attempts={},
            blocked={},
            source="github",
        )

        state = WorkflowState(
            version="2.0",
            prd_path=Path("docs/prds/test.md"),
            plan_path=Path("docs/plans/test.md"),
            tickets=[],
            ralph=ralph,
        )

        result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        assert result.ticket is None
        assert result.status == "error"
        assert "rate limit" in result.message.lower()

    def test_claim_failure_moves_to_next_ticket(
        self, pm_workflow: tuple[Path, WorkflowState, MockPMTool]
    ):
        """Given claim fails for first ticket,
        when getting next ticket,
        then next eligible ticket is tried."""
        state_file, state, mock_pm = pm_workflow

        # Make claim fail for ticket 74
        original_claim = mock_pm.claim_ticket

        def claim_fails_for_74(ticket_id: str, label: str) -> bool:
            if ticket_id == "74":
                return False
            return original_claim(ticket_id, label)

        mock_pm.claim_ticket = claim_fails_for_74  # type: ignore

        with patch("commands.get_next.time.sleep"):
            result = get_next_ticket(state, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should return 75 after 74's claim failed
        assert result.ticket is not None
        assert result.ticket.id == "75"


# ============================================================================
# Test Cases: LocalPM Fallback
# ============================================================================


class TestLocalPMFallback:
    """Tests for LocalPM fallback behavior."""

    def test_local_pm_claim_always_succeeds(self):
        """Given LocalPM is used,
        when claiming a ticket,
        then claim always succeeds (no concurrency control)."""
        local_pm = LocalPM()

        result = local_pm.claim_ticket("74", "ralph-1")

        assert result is True

    def test_local_pm_tracks_closed_tickets(self):
        """Given LocalPM is used,
        when closing tickets,
        then they are tracked as closed."""
        local_pm = LocalPM()

        assert local_pm.get_ticket_status("74") == TicketStatus.OPEN

        local_pm.close_ticket("74")

        assert local_pm.get_ticket_status("74") == TicketStatus.CLOSED

    def test_local_pm_tracks_blocked_tickets(self):
        """Given LocalPM is used,
        when blocking tickets,
        then they are tracked as blocked."""
        local_pm = LocalPM()

        local_pm.add_blocked_label("74", "Test failure")

        assert local_pm.get_ticket_status("74") == TicketStatus.BLOCKED
