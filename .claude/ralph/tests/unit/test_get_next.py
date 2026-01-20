"""Unit tests for the get_next module.

Tests the core functionality of finding the next eligible ticket
based on status and dependency satisfaction.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from commands.get_next import (
    get_next_ticket,
    GetNextResult,
    is_ticket_eligible,
    get_ticket_counts,
)
from core.pm import PMTool, TicketInfo, TicketStatus, PMError
from core.state import WorkflowState, RalphState, Ticket


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def simple_workflow() -> WorkflowState:
    """Create a simple workflow with tickets that have no dependencies."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket",
                status="pending",
                dependencies=[],
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket",
                status="pending",
                dependencies=[],
            ),
            Ticket(
                id="TASK-003",
                title="Third ticket",
                status="pending",
                dependencies=[],
            ),
        ],
    )


@pytest.fixture
def workflow_with_deps() -> WorkflowState:
    """Create a workflow with dependencies."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket - no deps",
                status="pending",
                dependencies=[],
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket - depends on first",
                status="pending",
                dependencies=["TASK-001"],
            ),
            Ticket(
                id="TASK-003",
                title="Third ticket - depends on second",
                status="pending",
                dependencies=["TASK-002"],
            ),
        ],
    )


@pytest.fixture
def workflow_with_completed() -> WorkflowState:
    """Create a workflow with some completed tickets."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket - completed",
                status="completed",
                dependencies=[],
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket - depends on first",
                status="pending",
                dependencies=["TASK-001"],
            ),
            Ticket(
                id="TASK-003",
                title="Third ticket - depends on second",
                status="pending",
                dependencies=["TASK-002"],
            ),
        ],
        completed_count=1,
    )


@pytest.fixture
def workflow_with_blocked() -> WorkflowState:
    """Create a workflow with blocked tickets."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket - blocked",
                status="blocked",
                dependencies=[],
                block_reason="Test failure",
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket - pending",
                status="pending",
                dependencies=[],
            ),
            Ticket(
                id="TASK-003",
                title="Third ticket - pending, blocked dep",
                status="pending",
                dependencies=["TASK-001"],
            ),
        ],
        blocked_count=1,
    )


@pytest.fixture
def workflow_in_progress() -> WorkflowState:
    """Create a workflow with a ticket in progress."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket - in progress",
                status="in_progress",
                dependencies=[],
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket - pending",
                status="pending",
                dependencies=[],
            ),
        ],
        current_ticket="TASK-001",
    )


@pytest.fixture
def all_completed_workflow() -> WorkflowState:
    """Create a workflow with all tickets completed."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[
            Ticket(
                id="TASK-001",
                title="First ticket",
                status="completed",
                dependencies=[],
            ),
            Ticket(
                id="TASK-002",
                title="Second ticket",
                status="completed",
                dependencies=["TASK-001"],
            ),
        ],
        completed_count=2,
    )


@pytest.fixture
def empty_workflow() -> WorkflowState:
    """Create an empty workflow with no tickets."""
    return WorkflowState(
        version="1.0",
        prd_path="docs/prds/test.md",
        plan_path="docs/plans/test.md",
        tickets=[],
    )


# =============================================================================
# Tests: get_next_ticket - Basic Functionality
# =============================================================================


class TestGetNextTicketBasic:
    """Test basic functionality of get_next_ticket."""

    def test_returns_first_pending_ticket_no_dependencies(
        self, simple_workflow: WorkflowState
    ) -> None:
        """Given multiple pending tickets with no dependencies, return the first by order."""
        result = get_next_ticket(simple_workflow)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.status == "ready"
        assert result.has_more is True

    def test_returns_none_when_no_tickets(
        self, empty_workflow: WorkflowState
    ) -> None:
        """Given no tickets exist, return None with appropriate message."""
        result = get_next_ticket(empty_workflow)

        assert result.ticket is None
        assert result.status == "complete"
        assert result.has_more is False
        assert "no tickets" in result.message.lower()

    def test_returns_none_when_all_completed(
        self, all_completed_workflow: WorkflowState
    ) -> None:
        """Given all tickets are complete, return None with complete status."""
        result = get_next_ticket(all_completed_workflow)

        assert result.ticket is None
        assert result.status == "complete"
        assert result.has_more is False


# =============================================================================
# Tests: get_next_ticket - Dependency Handling
# =============================================================================


class TestGetNextTicketDependencies:
    """Test dependency handling in get_next_ticket."""

    def test_skips_ticket_with_incomplete_dependencies(
        self, workflow_with_deps: WorkflowState
    ) -> None:
        """Given a ticket depends on incomplete tickets, skip that ticket."""
        result = get_next_ticket(workflow_with_deps)

        # Should return TASK-001 (the only one without deps)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

    def test_returns_dependent_when_dependencies_complete(
        self, workflow_with_completed: WorkflowState
    ) -> None:
        """Given all dependencies are complete, the dependent ticket becomes available."""
        result = get_next_ticket(workflow_with_completed)

        # TASK-001 is completed, so TASK-002 should be eligible
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"

    def test_respects_chain_of_dependencies(
        self, workflow_with_deps: WorkflowState
    ) -> None:
        """Given a chain of dependencies, only the first in chain is eligible."""
        # TASK-003 depends on TASK-002 which depends on TASK-001
        # Only TASK-001 should be eligible
        result = get_next_ticket(workflow_with_deps)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"


# =============================================================================
# Tests: get_next_ticket - Blocked Tickets
# =============================================================================


class TestGetNextTicketBlocked:
    """Test blocked ticket handling in get_next_ticket."""

    def test_skips_blocked_tickets(
        self, workflow_with_blocked: WorkflowState
    ) -> None:
        """Given a ticket is blocked, skip it and return next eligible ticket."""
        result = get_next_ticket(workflow_with_blocked)

        # TASK-001 is blocked, should return TASK-002
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"

    def test_skips_ticket_depending_on_blocked(
        self, workflow_with_blocked: WorkflowState
    ) -> None:
        """Given a ticket depends on a blocked ticket, skip it."""
        # TASK-003 depends on blocked TASK-001
        result = get_next_ticket(workflow_with_blocked)

        # Should return TASK-002, not TASK-003
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        # TASK-003 should be counted as skipped due to deps
        assert result.skipped_for_deps >= 1


# =============================================================================
# Tests: get_next_ticket - In Progress Handling
# =============================================================================


class TestGetNextTicketInProgress:
    """Test in-progress ticket handling in get_next_ticket."""

    def test_returns_in_progress_ticket_first(
        self, workflow_in_progress: WorkflowState
    ) -> None:
        """Given a ticket is in progress, return it to resume work."""
        result = get_next_ticket(workflow_in_progress)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.ticket.status == "in_progress"
        assert result.status == "ready"


# =============================================================================
# Tests: get_next_ticket - Status Information
# =============================================================================


class TestGetNextTicketStatus:
    """Test status information in get_next_ticket result."""

    def test_includes_ticket_counts(
        self, simple_workflow: WorkflowState
    ) -> None:
        """Result should include ticket counts."""
        result = get_next_ticket(simple_workflow)

        assert result.total == 3
        assert result.pending == 3
        assert result.completed == 0
        assert result.blocked == 0

    def test_includes_skipped_count_for_deps(
        self, workflow_with_deps: WorkflowState
    ) -> None:
        """Result should include count of tickets skipped for deps."""
        result = get_next_ticket(workflow_with_deps)

        # TASK-002 and TASK-003 should be skipped due to deps
        assert result.skipped_for_deps == 2

    def test_waiting_on_dependencies_status(
        self, workflow_with_deps: WorkflowState
    ) -> None:
        """When only ticket is waiting on deps, status should reflect that."""
        # Complete TASK-001 first
        workflow_with_deps.tickets[0].status = "completed"
        # Now TASK-002 becomes eligible
        # But TASK-003 still waits on TASK-002

        result = get_next_ticket(workflow_with_deps)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        # TASK-003 is skipped for deps
        assert result.skipped_for_deps == 1


# =============================================================================
# Tests: is_ticket_eligible - Helper Function
# =============================================================================


class TestIsTicketEligible:
    """Test the is_ticket_eligible helper function."""

    def test_pending_ticket_no_deps_is_eligible(self) -> None:
        """Pending ticket with no dependencies is eligible."""
        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="pending",
            dependencies=[],
        )
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids) is True

    def test_completed_ticket_is_not_eligible(self) -> None:
        """Completed ticket is not eligible."""
        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="completed",
            dependencies=[],
        )
        completed_ids: set[str] = {"TASK-001"}

        assert is_ticket_eligible(ticket, completed_ids) is False

    def test_blocked_ticket_is_not_eligible(self) -> None:
        """Blocked ticket is not eligible."""
        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="blocked",
            dependencies=[],
            block_reason="Blocked",
        )
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids) is False

    def test_in_progress_ticket_is_eligible(self) -> None:
        """In-progress ticket is eligible (to resume)."""
        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="in_progress",
            dependencies=[],
        )
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids) is True

    def test_pending_ticket_with_unmet_deps_is_not_eligible(self) -> None:
        """Pending ticket with incomplete dependencies is not eligible."""
        ticket = Ticket(
            id="TASK-002",
            title="Test",
            status="pending",
            dependencies=["TASK-001"],
        )
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids) is False

    def test_pending_ticket_with_met_deps_is_eligible(self) -> None:
        """Pending ticket with completed dependencies is eligible."""
        ticket = Ticket(
            id="TASK-002",
            title="Test",
            status="pending",
            dependencies=["TASK-001"],
        )
        completed_ids: set[str] = {"TASK-001"}

        assert is_ticket_eligible(ticket, completed_ids) is True

    def test_pending_ticket_with_partially_met_deps_is_not_eligible(self) -> None:
        """Pending ticket with some incomplete dependencies is not eligible."""
        ticket = Ticket(
            id="TASK-003",
            title="Test",
            status="pending",
            dependencies=["TASK-001", "TASK-002"],
        )
        completed_ids: set[str] = {"TASK-001"}  # Missing TASK-002

        assert is_ticket_eligible(ticket, completed_ids) is False


# =============================================================================
# Tests: get_ticket_counts - Helper Function
# =============================================================================


class TestGetTicketCounts:
    """Test the get_ticket_counts helper function."""

    def test_counts_all_statuses(self, simple_workflow: WorkflowState) -> None:
        """Should count tickets by status correctly."""
        counts = get_ticket_counts(simple_workflow.tickets)

        assert counts["total"] == 3
        assert counts["pending"] == 3
        assert counts["completed"] == 0
        assert counts["blocked"] == 0
        assert counts["in_progress"] == 0

    def test_counts_mixed_statuses(
        self, workflow_with_blocked: WorkflowState
    ) -> None:
        """Should count mixed statuses correctly."""
        counts = get_ticket_counts(workflow_with_blocked.tickets)

        assert counts["total"] == 3
        assert counts["pending"] == 2
        assert counts["blocked"] == 1
        assert counts["completed"] == 0

    def test_counts_completed(
        self, workflow_with_completed: WorkflowState
    ) -> None:
        """Should count completed tickets correctly."""
        counts = get_ticket_counts(workflow_with_completed.tickets)

        assert counts["total"] == 3
        assert counts["completed"] == 1
        assert counts["pending"] == 2


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_all_tickets_blocked(self) -> None:
        """When all tickets are blocked, return appropriate status."""
        workflow = WorkflowState(
            version="1.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[
                Ticket(
                    id="TASK-001",
                    title="Blocked 1",
                    status="blocked",
                    dependencies=[],
                    block_reason="Failed",
                ),
                Ticket(
                    id="TASK-002",
                    title="Blocked 2",
                    status="blocked",
                    dependencies=[],
                    block_reason="Failed",
                ),
            ],
            blocked_count=2,
        )

        result = get_next_ticket(workflow)

        assert result.ticket is None
        assert result.status == "all_blocked"
        assert result.blocked == 2

    def test_all_tickets_waiting_on_deps(self) -> None:
        """When all tickets are waiting on dependencies, return appropriate status."""
        workflow = WorkflowState(
            version="1.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[
                Ticket(
                    id="TASK-001",
                    title="Waiting 1",
                    status="pending",
                    dependencies=["TASK-002"],  # Circular - both wait on each other
                ),
                Ticket(
                    id="TASK-002",
                    title="Waiting 2",
                    status="pending",
                    dependencies=["TASK-001"],
                ),
            ],
        )

        result = get_next_ticket(workflow)

        assert result.ticket is None
        assert result.status == "waiting_on_dependencies"
        assert result.skipped_for_deps == 2

    def test_ticket_with_unknown_status_is_not_eligible(self) -> None:
        """Ticket with unknown status should not be eligible."""
        ticket = Ticket(
            id="TASK-001",
            title="Test",
            status="unknown_status",
            dependencies=[],
        )
        completed_ids: set[str] = set()

        assert is_ticket_eligible(ticket, completed_ids) is False

    def test_result_to_dict_with_ticket(self) -> None:
        """GetNextResult.to_dict should include ticket info when ticket exists."""
        ticket = Ticket(
            id="TASK-001",
            title="Test Ticket",
            status="pending",
            dependencies=[],
        )
        result = GetNextResult(
            ticket=ticket,
            status="ready",
            message="Next ticket: TASK-001",
            has_more=True,
            total=3,
            pending=2,
            completed=1,
            blocked=0,
            in_progress=0,
            skipped_for_deps=0,
        )

        result_dict = result.to_dict()

        assert result_dict["next_ticket"] == "TASK-001"
        assert result_dict["ticket_title"] == "Test Ticket"
        assert result_dict["status"] == "ready"

    def test_result_to_dict_without_ticket(self) -> None:
        """GetNextResult.to_dict should handle None ticket."""
        result = GetNextResult(
            ticket=None,
            status="complete",
            message="All done",
            has_more=False,
            total=2,
            pending=0,
            completed=2,
            blocked=0,
            in_progress=0,
            skipped_for_deps=0,
        )

        result_dict = result.to_dict()

        assert result_dict["next_ticket"] is None
        assert result_dict["ticket_title"] is None
        assert result_dict["status"] == "complete"

    def test_mixed_completed_and_blocked_no_pending(self) -> None:
        """When all tickets are either completed or blocked, return complete."""
        workflow = WorkflowState(
            version="1.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[
                Ticket(
                    id="TASK-001",
                    title="Completed",
                    status="completed",
                    dependencies=[],
                ),
                Ticket(
                    id="TASK-002",
                    title="Blocked",
                    status="blocked",
                    dependencies=[],
                    block_reason="Failed",
                ),
            ],
            completed_count=1,
            blocked_count=1,
        )

        result = get_next_ticket(workflow)

        assert result.ticket is None
        # Not all blocked (only 1 of 2), not all complete (only 1 of 2)
        # No pending tickets and no skipped_for_deps, so it's "complete"
        assert result.status == "complete"


# =============================================================================
# Tests: get_next_ticket - PM Tool Integration
# =============================================================================


def create_mock_pm_tool() -> Mock:
    """Create a mock PM tool for testing."""
    mock = Mock(spec=PMTool)
    mock.get_open_tickets.return_value = []
    mock.get_ticket_status.return_value = TicketStatus.OPEN
    mock.is_ticket_claimed.return_value = (False, None)
    return mock


class TestGetNextTicketWithPMTool:
    """Test get_next_ticket integration with PM tool."""

    def test_accepts_pm_tool_parameter(self) -> None:
        """get_next_ticket should accept an optional pm_tool parameter."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="Test", status=TicketStatus.OPEN, labels=[])
        ]

        # Should not raise - accepts pm_tool parameter
        result = get_next_ticket(workflow, pm_tool=mock_pm)

        assert result is not None

    def test_queries_pm_tool_for_open_tickets(self) -> None:
        """Given tickets in ralph.tickets, when pm_tool provided, then query PM tool for open tickets."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="First Task", status=TicketStatus.OPEN, labels=[]),
            TicketInfo(id="TASK-002", title="Second Task", status=TicketStatus.OPEN, labels=[]),
        ]

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        # Should have called get_open_tickets with ticket IDs from ralph.tickets
        mock_pm.get_open_tickets.assert_called_once_with(["TASK-001", "TASK-002"])
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

    def test_open_issue_reported_as_pending(self) -> None:
        """Given a ticket exists in GitHub Issues as open, when get_next_ticket runs, then it reports as pending."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="Open Task", status=TicketStatus.OPEN, labels=[])
        ]

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
        assert result.status == "ready"

    def test_closed_issue_treated_as_completed_for_dependencies(self) -> None:
        """Given a ticket is closed in GitHub, when checking dependencies, then it's considered completed.

        Optimization: If a ticket is not in the open_tickets list, it's inferred to be closed
        without needing an additional API call. This test verifies that closed dependencies
        (not in open_tickets) satisfy the dependency requirement.
        """
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={"TASK-002": ["TASK-001"]},  # TASK-002 depends on TASK-001
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        # Only TASK-002 is open (TASK-001 is closed, so not in list)
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-002", title="Depends on TASK-001", status=TicketStatus.OPEN, labels=[])
        ]

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        # TASK-002 should be eligible since TASK-001 is closed (not in open list)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert result.status == "ready"
        # No need to query get_ticket_status for TASK-001 since it's not in open_tickets
        # (optimization - if not in open list, it's already closed)

    def test_skips_blocked_tickets(self) -> None:
        """Given a ticket has blocked label in GitHub, when get_next_ticket runs, then it skips the ticket."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="Blocked Task", status=TicketStatus.BLOCKED, labels=["blocked"]),
            TicketInfo(id="TASK-002", title="Open Task", status=TicketStatus.OPEN, labels=[]),
        ]

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        # Should skip TASK-001 (blocked) and return TASK-002
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert result.blocked >= 1

    def test_pm_tool_error_reports_clear_error(self) -> None:
        """Given GitHub API calls fail, when getting next ticket, then report clear error."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.side_effect = PMError("GitHub API rate limited")

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        assert result.ticket is None
        assert result.status == "error"
        assert "error" in result.message.lower() or "failed" in result.message.lower()

    def test_dependency_not_met_when_dep_is_open(self) -> None:
        """Given ticket A depends on B and B is open, then A is not eligible."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={"TASK-002": ["TASK-001"]},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        # Both tickets are open
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="First", status=TicketStatus.OPEN, labels=[]),
            TicketInfo(id="TASK-002", title="Second (depends on first)", status=TicketStatus.OPEN, labels=[]),
        ]
        mock_pm.get_ticket_status.return_value = TicketStatus.OPEN

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        # Should return TASK-001 (no deps), not TASK-002 (dep not met)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"

    def test_skips_tickets_claimed_by_other_instances(self) -> None:
        """Given a ticket has ralph-* label from another instance, skip that ticket."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="Claimed by other", status=TicketStatus.OPEN, labels=["ralph-2"]),
            TicketInfo(id="TASK-002", title="Not claimed", status=TicketStatus.OPEN, labels=[]),
        ]
        # TASK-001 is claimed by ralph-2
        mock_pm.is_ticket_claimed.side_effect = lambda tid: (True, "ralph-2") if tid == "TASK-001" else (False, None)

        # Simulate this instance being ralph-1 (not ralph-2)
        result = get_next_ticket(workflow, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should skip TASK-001 (claimed by ralph-2) and return TASK-002
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"

    def test_resumes_own_in_progress_ticket_first(self) -> None:
        """Given a ticket has this instance's label, resume it first."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = [
            TicketInfo(id="TASK-001", title="Not claimed", status=TicketStatus.OPEN, labels=[]),
            TicketInfo(id="TASK-002", title="In progress by this instance", status=TicketStatus.OPEN, labels=["ralph-1"]),
        ]
        # TASK-002 is claimed by ralph-1 (this instance)
        mock_pm.is_ticket_claimed.side_effect = lambda tid: (True, "ralph-1") if tid == "TASK-002" else (False, None)

        result = get_next_ticket(workflow, pm_tool=mock_pm, ralph_label="ralph-1")

        # Should return TASK-002 first (resume own in-progress work)
        assert result.ticket is not None
        assert result.ticket.id == "TASK-002"
        assert "resum" in result.message.lower()

    def test_all_tickets_complete_when_none_open(self) -> None:
        """Given no tickets are open in PM tool, return complete status."""
        workflow = WorkflowState(
            version="2.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[],
            ralph=RalphState(
                source="github",
                tickets=["TASK-001", "TASK-002"],
                dependencies={},
                attempts={},
                blocked={},
            ),
        )
        mock_pm = create_mock_pm_tool()
        mock_pm.get_open_tickets.return_value = []  # All closed

        result = get_next_ticket(workflow, pm_tool=mock_pm)

        assert result.ticket is None
        assert result.status == "complete"

    def test_falls_back_to_local_state_without_pm_tool(self) -> None:
        """Given no pm_tool provided, fall back to v1 behavior using local state."""
        # This tests backward compatibility
        workflow = WorkflowState(
            version="1.0",
            prd_path="docs/prds/test.md",
            plan_path="docs/plans/test.md",
            tickets=[
                Ticket(id="TASK-001", title="First", status="pending", dependencies=[]),
            ],
        )

        # No pm_tool provided - should work with local state
        result = get_next_ticket(workflow)

        assert result.ticket is not None
        assert result.ticket.id == "TASK-001"
