"""Integration tests for Asana PM workflow using real API calls.

These tests are gated by the RUN_ASANA_INTEGRATION_TESTS environment variable.
They require real Asana credentials to run:
- ASANA_ACCESS_TOKEN: Personal Access Token
- ASANA_WORKSPACE_ID: Workspace GID
- ASANA_PROJECT_ID: Project GID for testing

**IMPORTANT:** These tests create and modify real Asana tasks. Use a dedicated
test project, not a production workspace.

Test Coverage:
- Full workflow: create task -> claim -> complete
- Blocked flow: mark blocked, verify tag and comment
- Race condition handling: two labels added, verify claim detection
- Tag management: verify tags are created when missing
- Dependency satisfaction: verify dependency checking

SDLC-0066: Integration tests for Asana flow
"""

import os

import pytest

# Skip all tests if RUN_ASANA_INTEGRATION_TESTS is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_ASANA_INTEGRATION_TESTS") != "1",
    reason="Integration tests require RUN_ASANA_INTEGRATION_TESTS=1 environment variable",
)


# =============================================================================
# Fixtures for Integration Tests
# =============================================================================


@pytest.fixture(scope="module")
def asana_pm():
    """Create an AsanaPM instance for integration testing.

    This fixture creates a real AsanaPM instance using environment credentials.
    It's module-scoped to reuse the same instance across tests in this module.

    Requires:
        ASANA_ACCESS_TOKEN, ASANA_WORKSPACE_ID, ASANA_PROJECT_ID

    Returns:
        AsanaPM instance configured with real credentials
    """
    from core.asana_pm import AsanaPM

    return AsanaPM()


@pytest.fixture
def test_task(asana_pm):
    """Create a test task and clean it up after the test.

    Creates a task with a unique name for testing, then archives it
    after the test completes to avoid cluttering the project.

    Yields:
        Tuple of (task_gid, task_name)
    """
    import time

    # Generate unique task name with timestamp
    timestamp = int(time.time())
    task_name = f"[SDLC-TEST-{timestamp}] Integration Test Task"

    # Create the test task
    task_gid = asana_pm.create_task(
        name=task_name,
        notes="This is an automated integration test task. It should be archived.",
        add_task_tag=True,
    )

    yield task_gid, task_name

    # Cleanup: archive the task after the test
    # Note: Asana doesn't have a direct "delete" - we use complete + potentially archive
    try:
        asana_pm.close_ticket(task_gid)
    except Exception:
        pass  # Best effort cleanup


# =============================================================================
# Full Workflow Tests
# =============================================================================


class TestFullWorkflow:
    """Tests for the complete create -> claim -> complete workflow."""

    def test_create_task_returns_valid_gid(self, asana_pm, test_task):
        """Given AsanaPM, when creating a task, then a valid GID is returned.

        SDLC-0066: Full workflow - task creation
        """
        task_gid, task_name = test_task

        # Verify GID is a non-empty string (Asana GIDs are numeric strings)
        assert task_gid is not None
        assert isinstance(task_gid, str)
        assert len(task_gid) > 0
        assert task_gid.isdigit(), f"Task GID should be numeric: {task_gid}"

    def test_claim_ticket_adds_ralph_tag(self, asana_pm, test_task):
        """Given a task, when claiming it with ralph-1, then the tag is added.

        SDLC-0066: Full workflow - claim ticket
        """
        task_gid, _ = test_task

        # Claim the ticket
        result = asana_pm.claim_ticket(task_gid, "ralph-1")
        assert result is True

        # Verify claim by checking is_ticket_claimed
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is True
        assert label == "ralph-1"

    def test_close_ticket_marks_complete(self, asana_pm, test_task):
        """Given a task, when closing it, then it is marked complete.

        SDLC-0066: Full workflow - close ticket
        """
        from core.pm import TicketStatus

        task_gid, _ = test_task

        # Close the ticket
        result = asana_pm.close_ticket(task_gid)
        assert result is True

        # Verify status is CLOSED
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.CLOSED

    def test_get_ticket_status_returns_open_for_new_task(self, asana_pm, test_task):
        """Given a new task, when getting status, then OPEN is returned.

        SDLC-0066: Full workflow - status check
        """
        from core.pm import TicketStatus

        task_gid, _ = test_task

        # New task should be OPEN
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.OPEN

    def test_full_workflow_create_claim_complete(self, asana_pm):
        """Test the complete workflow: create -> claim -> complete.

        This test verifies the entire happy path without using the test_task
        fixture to ensure isolation.

        SDLC-0066: Full workflow - complete cycle
        """
        import time

        from core.pm import TicketStatus

        timestamp = int(time.time())
        task_name = f"[SDLC-WORKFLOW-{timestamp}] Full Workflow Test"

        try:
            # 1. CREATE
            task_gid = asana_pm.create_task(
                name=task_name,
                notes="Testing full workflow: create -> claim -> complete",
                add_task_tag=True,
            )
            assert task_gid is not None

            # 2. Verify OPEN status
            status = asana_pm.get_ticket_status(task_gid)
            assert status == TicketStatus.OPEN

            # 3. CLAIM
            claim_result = asana_pm.claim_ticket(task_gid, "ralph-0")
            assert claim_result is True

            # 4. Verify claim
            is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
            assert is_claimed is True
            assert label == "ralph-0"

            # 5. COMPLETE
            close_result = asana_pm.close_ticket(task_gid)
            assert close_result is True

            # 6. Verify CLOSED status
            status = asana_pm.get_ticket_status(task_gid)
            assert status == TicketStatus.CLOSED

        finally:
            # Cleanup
            try:
                asana_pm.close_ticket(task_gid)
            except Exception:
                pass


# =============================================================================
# Blocked Flow Tests
# =============================================================================


class TestBlockedFlow:
    """Tests for the blocked task workflow."""

    def test_add_blocked_label_adds_tag(self, asana_pm, test_task):
        """Given a task, when marking blocked, then the blocked tag is added.

        SDLC-0066: Blocked flow - tag addition
        """
        from core.pm import TicketStatus

        task_gid, _ = test_task

        # Mark as blocked
        result = asana_pm.add_blocked_label(task_gid, "Test failure: unit tests failing")
        assert result is True

        # Verify status is BLOCKED
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.BLOCKED

    def test_add_blocked_label_posts_comment(self, asana_pm, test_task):
        """Given a task, when marking blocked with reason, then a comment is posted.

        SDLC-0066: Blocked flow - comment posting
        """
        task_gid, _ = test_task

        # Mark as blocked with a unique reason
        unique_reason = f"Test blocked reason: {task_gid}"
        result = asana_pm.add_blocked_label(task_gid, unique_reason)
        assert result is True

        # Note: Verifying the comment would require fetching task stories,
        # which is an additional API call. For now, we trust the success result.
        # A more thorough test would fetch stories and verify the comment exists.

    def test_blocked_task_stays_blocked_even_when_incomplete(self, asana_pm, test_task):
        """Given a blocked incomplete task, when getting status, then BLOCKED is returned.

        This verifies that BLOCKED takes precedence over OPEN status.

        SDLC-0066: Blocked flow - status precedence
        """
        from core.pm import TicketStatus

        task_gid, _ = test_task

        # Verify task is open first
        initial_status = asana_pm.get_ticket_status(task_gid)
        assert initial_status == TicketStatus.OPEN

        # Mark as blocked
        asana_pm.add_blocked_label(task_gid, "Blocked for testing")

        # Verify status is BLOCKED (not OPEN)
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.BLOCKED

    def test_remove_blocked_label_unblocks_task(self, asana_pm, test_task):
        """Given a blocked task, when removing blocked label, then task is unblocked.

        SDLC-0066: Blocked flow - unblock
        """
        from core.pm import TicketStatus

        task_gid, _ = test_task

        # Mark as blocked
        asana_pm.add_blocked_label(task_gid, "Temporarily blocked")

        # Verify blocked
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.BLOCKED

        # Remove blocked label
        remove_result = asana_pm.remove_label(task_gid, "blocked")
        assert remove_result is True

        # Verify no longer blocked (should be OPEN now)
        status = asana_pm.get_ticket_status(task_gid)
        assert status == TicketStatus.OPEN


# =============================================================================
# Tag Management Tests
# =============================================================================


class TestTagManagement:
    """Tests for tag creation and management."""

    def test_claim_with_new_ralph_tag_creates_tag(self, asana_pm, test_task):
        """Given a tag that doesn't exist, when claiming ticket, then tag is created.

        SDLC-0066: Tag management - automatic creation
        """
        task_gid, _ = test_task

        # Use a ralph tag (ralph-5 is less commonly used in tests)
        # The _get_or_create_tag method should create it if missing
        result = asana_pm.claim_ticket(task_gid, "ralph-5")
        assert result is True

        # Verify claim was successful
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is True
        assert label == "ralph-5"

    def test_is_ticket_claimed_returns_false_for_unclaimed(self, asana_pm, test_task):
        """Given a task without ralph tags, when checking claim, then False is returned.

        SDLC-0066: Tag management - unclaimed detection
        """
        task_gid, _ = test_task

        # New task should not be claimed
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is False
        assert label is None

    def test_is_ticket_claimed_detects_any_ralph_tag(self, asana_pm, test_task):
        """Given a task with ralph-N tag, when checking claim, then correct label returned.

        SDLC-0066: Tag management - label detection
        """
        task_gid, _ = test_task

        # Claim with ralph-3
        asana_pm.claim_ticket(task_gid, "ralph-3")

        # Verify detection
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is True
        assert label == "ralph-3"

    def test_ensure_required_tags_creates_all_tags(self, asana_pm):
        """Given AsanaPM, when ensuring required tags, then all tags exist.

        SDLC-0066: Tag management - ensure_required_tags
        """
        # This may create tags or just verify they exist
        result = asana_pm.ensure_required_tags()
        assert result is True


# =============================================================================
# Race Condition Simulation Tests
# =============================================================================


class TestRaceConditionHandling:
    """Tests for race condition handling in claiming tickets."""

    def test_multiple_ralph_labels_first_wins(self, asana_pm, test_task):
        """Given a task claimed twice, when checking claim, then first label detected.

        This simulates a race condition where two Ralph instances try to claim
        the same ticket. The is_ticket_claimed method should return the first
        ralph-* tag it finds.

        SDLC-0066: Race condition - first wins
        """
        task_gid, _ = test_task

        # Claim with ralph-1 first
        asana_pm.claim_ticket(task_gid, "ralph-1")

        # Claim with ralph-2 second (simulating a race)
        asana_pm.claim_ticket(task_gid, "ralph-2")

        # Check claim - should detect one of the ralph tags
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is True
        # The label should be either ralph-1 or ralph-2 (order may vary)
        assert label in ["ralph-1", "ralph-2"]

    def test_claim_ticket_is_idempotent(self, asana_pm, test_task):
        """Given an already claimed task, when claiming again with same label, then succeeds.

        SDLC-0066: Race condition - idempotency
        """
        task_gid, _ = test_task

        # Claim twice with the same label
        result1 = asana_pm.claim_ticket(task_gid, "ralph-2")
        result2 = asana_pm.claim_ticket(task_gid, "ralph-2")

        # Both should succeed (idempotent)
        assert result1 is True
        assert result2 is True

        # Should still be claimed with ralph-2
        is_claimed, label = asana_pm.is_ticket_claimed(task_gid)
        assert is_claimed is True
        # Note: Due to adding the same tag twice, Asana may handle this gracefully


# =============================================================================
# Subtask and Dependency Tests
# =============================================================================


class TestSubtasksAndDependencies:
    """Tests for subtask and dependency management."""

    def test_create_subtask_under_task(self, asana_pm, test_task):
        """Given a task, when creating subtask, then subtask is created.

        SDLC-0066: Subtasks - acceptance criteria
        """
        task_gid, _ = test_task

        # Create a subtask (acceptance criterion)
        subtask_gid = asana_pm.create_subtask(
            task_gid, "User can log in with valid credentials"
        )

        assert subtask_gid is not None
        assert isinstance(subtask_gid, str)
        assert len(subtask_gid) > 0

    def test_get_task_details_includes_subtasks(self, asana_pm, test_task):
        """Given a task with subtasks, when getting details, then subtasks included.

        SDLC-0066: Task details - subtask inclusion
        """
        task_gid, task_name = test_task

        # Create a subtask first
        asana_pm.create_subtask(task_gid, "Test subtask for details")

        # Get task details
        details = asana_pm.get_task_details(task_gid)

        assert "subtasks" in details
        assert isinstance(details["subtasks"], list)
        assert len(details["subtasks"]) >= 1
        assert details["name"] == task_name

    def test_add_dependencies_links_tasks(self, asana_pm):
        """Given two tasks, when adding dependency, then tasks are linked.

        SDLC-0066: Dependencies - task linking
        """
        import time

        timestamp = int(time.time())

        try:
            # Create dependency task (must be completed first)
            dep_task_gid = asana_pm.create_task(
                name=f"[SDLC-DEP-{timestamp}] Dependency Task",
                notes="This task must be completed first",
                add_task_tag=True,
            )

            # Create dependent task
            task_gid = asana_pm.create_task(
                name=f"[SDLC-DEPENDENT-{timestamp}] Dependent Task",
                notes="This task depends on the dependency task",
                add_task_tag=True,
            )

            # Add dependency
            result = asana_pm.add_dependencies(task_gid, [dep_task_gid])
            assert result is True

        finally:
            # Cleanup
            try:
                asana_pm.close_ticket(dep_task_gid)
                asana_pm.close_ticket(task_gid)
            except Exception:
                pass


# =============================================================================
# Additional Method Tests
# =============================================================================


class TestAdditionalMethods:
    """Tests for additional AsanaPM methods."""

    def test_assign_to_self_sets_assignee(self, asana_pm, test_task):
        """Given a task, when assigning to self, then assignment succeeds.

        SDLC-0066: Additional methods - assign_to_self
        """
        task_gid, _ = test_task

        result = asana_pm.assign_to_self(task_gid)
        assert result is True

    def test_get_open_tickets_returns_only_open(self, asana_pm):
        """Given tasks with mixed states, when getting open tickets, then only open returned.

        SDLC-0066: Additional methods - get_open_tickets
        """
        import time

        timestamp = int(time.time())

        try:
            # Create open task
            open_task_gid = asana_pm.create_task(
                name=f"[SDLC-OPEN-{timestamp}] Open Task",
                notes="This task should be returned",
                add_task_tag=True,
            )

            # Create closed task
            closed_task_gid = asana_pm.create_task(
                name=f"[SDLC-CLOSED-{timestamp}] Closed Task",
                notes="This task should NOT be returned",
                add_task_tag=True,
            )
            asana_pm.close_ticket(closed_task_gid)

            # Get open tickets
            open_tickets = asana_pm.get_open_tickets([open_task_gid, closed_task_gid])

            # Only the open task should be returned
            open_ids = [t.id for t in open_tickets]
            assert open_task_gid in open_ids
            assert closed_task_gid not in open_ids

        finally:
            # Cleanup
            try:
                asana_pm.close_ticket(open_task_gid)
            except Exception:
                pass

    def test_add_pr_comment_posts_to_task(self, asana_pm, test_task):
        """Given a task, when adding PR comment, then comment is posted.

        SDLC-0066: Additional methods - add_pr_comment
        """
        task_gid, _ = test_task

        result = asana_pm.add_pr_comment(
            task_gid, "https://github.com/test/repo/pull/123"
        )
        assert result is True

    def test_get_ticket_counts_returns_valid_counts(self, asana_pm):
        """Given a project with tasks, when getting counts, then valid counts returned.

        SDLC-0066: Additional methods - get_ticket_counts
        """
        counts = asana_pm.get_ticket_counts()

        assert "open" in counts
        assert "closed" in counts
        assert "blocked" in counts
        assert "total" in counts
        assert "blocked_tasks" in counts

        # Counts should be non-negative integers
        assert isinstance(counts["open"], int)
        assert isinstance(counts["closed"], int)
        assert isinstance(counts["blocked"], int)
        assert isinstance(counts["total"], int)
        assert counts["open"] >= 0
        assert counts["closed"] >= 0
        assert counts["blocked"] >= 0
        assert counts["total"] == counts["open"] + counts["closed"] + counts["blocked"]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling with invalid inputs."""

    def test_get_ticket_status_invalid_id_raises_error(self, asana_pm):
        """Given invalid task ID, when getting status, then PMError is raised.

        SDLC-0066: Error handling - invalid task ID
        """
        from core.pm import PMError

        with pytest.raises(PMError) as exc_info:
            asana_pm.get_ticket_status("invalid-task-id-12345")

        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)

    def test_claim_ticket_invalid_id_returns_false(self, asana_pm):
        """Given invalid task ID, when claiming, then False is returned.

        SDLC-0066: Error handling - claim invalid task
        """
        result = asana_pm.claim_ticket("invalid-task-id-12345", "ralph-1")
        assert result is False

    def test_close_ticket_invalid_id_returns_false(self, asana_pm):
        """Given invalid task ID, when closing, then False is returned.

        SDLC-0066: Error handling - close invalid task
        """
        result = asana_pm.close_ticket("invalid-task-id-12345")
        assert result is False
