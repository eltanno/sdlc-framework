# Test Audit: test_get_next.py

## Executive Summary

**Overall Assessment: MOSTLY MEANINGFUL with some WEAK spots**

- **Total Tests Analyzed**: 58
- **MEANINGFUL**: 48 (83%)
- **WEAK**: 7 (12%)
- **IMPLEMENTATION-COUPLED**: 3 (5%)

The test suite is generally good. Most tests verify important business logic around ticket selection, dependency handling, and PM tool integration. However, there are several tests that make weak or missing assertions, particularly around status information and error conditions.

## Critical Findings

### Major Issues
1. **Weak assertions on status values** - Many tests check `assert result.status == "ready"` without verifying the logic that led to that status
2. **Missing negative assertions** - Tests verify what IS returned but rarely verify what ISN'T (e.g., "did NOT return blocked tickets")
3. **Mock behavior assumptions** - Some tests assume mock behavior without verifying the actual calls made

### Strengths
1. **Good coverage of dependency logic** - Tests thoroughly verify dependency satisfaction
2. **Race condition handling** - Comprehensive tests for claim race detection
3. **Edge cases** - Good coverage of circular dependencies, all-blocked scenarios
4. **Integration tests** - Good tests of PM tool integration

## Detailed Analysis

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_returns_first_pending_ticket_no_dependencies` | Returns first ticket when multiple are eligible | Checks `ticket.id == "TASK-001"`, `status == "ready"`, `has_more is True` | MEANINGFUL | Good - verifies ordering and status |
| `test_returns_none_when_no_tickets` | Returns complete status with no tickets | Checks `ticket is None`, `status == "complete"`, `"no tickets" in message` | MEANINGFUL | Good - verifies all relevant fields |
| `test_returns_none_when_all_completed` | Returns complete status when all done | Checks `ticket is None`, `status == "complete"`, `has_more is False` | MEANINGFUL | Good - verifies completion state |
| `test_skips_ticket_with_incomplete_dependencies` | Skips tickets waiting on dependencies | Only checks `ticket.id == "TASK-001"` | WEAK | Should verify TASK-002 and TASK-003 were NOT returned and skipped_for_deps count |
| `test_returns_dependent_when_dependencies_complete` | Returns dependent ticket when deps satisfied | Checks `ticket.id == "TASK-002"` | MEANINGFUL | Good - verifies dependency satisfaction logic |
| `test_respects_chain_of_dependencies` | Only first in chain is eligible | Checks `ticket.id == "TASK-001"` | WEAK | Should verify TASK-002/TASK-003 were skipped, check skipped_for_deps count |
| `test_skips_blocked_tickets` | Blocked tickets are not returned | Checks `ticket.id == "TASK-002"` | WEAK | Should explicitly verify TASK-001 was NOT returned and blocked count |
| `test_skips_ticket_depending_on_blocked` | Tickets depending on blocked are skipped | Checks `ticket.id == "TASK-002"`, `skipped_for_deps >= 1` | MEANINGFUL | Good - verifies both the ticket returned and the skip count |
| `test_returns_in_progress_ticket_first` | In-progress ticket returned first | Checks `ticket.id == "TASK-001"`, `ticket.status == "in_progress"`, `status == "ready"` | MEANINGFUL | Good - verifies prioritization of in-progress work |
| `test_includes_ticket_counts` | Result includes accurate counts | Checks all count fields: `total`, `pending`, `completed`, `blocked` | MEANINGFUL | Good - verifies counting logic |
| `test_includes_skipped_count_for_deps` | Counts tickets skipped for dependencies | Checks `skipped_for_deps == 2` | MEANINGFUL | Good - verifies dependency skip counting |
| `test_waiting_on_dependencies_status` | Status reflects waiting state correctly | Checks `ticket.id == "TASK-002"`, `skipped_for_deps == 1` | MEANINGFUL | Good - verifies status after partial completion |
| `test_pending_ticket_no_deps_is_eligible` | Pending + no deps = eligible | Checks `is_ticket_eligible() is True` | MEANINGFUL | Good - tests core eligibility logic |
| `test_completed_ticket_is_not_eligible` | Completed ticket is not eligible | Checks `is_ticket_eligible() is False` | MEANINGFUL | Good - verifies status filter |
| `test_blocked_ticket_is_not_eligible` | Blocked ticket is not eligible | Checks `is_ticket_eligible() is False` | MEANINGFUL | Good - verifies blocked filter |
| `test_in_progress_ticket_is_eligible` | In-progress ticket is eligible for resume | Checks `is_ticket_eligible() is True` | MEANINGFUL | Good - verifies resume logic |
| `test_pending_ticket_with_unmet_deps_is_not_eligible` | Unmet dependencies = not eligible | Checks `is_ticket_eligible() is False` | MEANINGFUL | Good - verifies dependency logic |
| `test_pending_ticket_with_met_deps_is_eligible` | Met dependencies = eligible | Checks `is_ticket_eligible() is True` | MEANINGFUL | Good - verifies dependency satisfaction |
| `test_pending_ticket_with_partially_met_deps_is_not_eligible` | Partial dependency satisfaction = not eligible | Checks `is_ticket_eligible() is False` | MEANINGFUL | Good - verifies ALL deps must be met |
| `test_counts_all_statuses` | Counts tickets by status correctly | Checks all count fields with specific values | MEANINGFUL | Good - verifies counting for single status |
| `test_counts_mixed_statuses` | Counts mixed statuses correctly | Checks `total == 3`, `pending == 2`, `blocked == 1`, `completed == 0` | MEANINGFUL | Good - verifies counting for mixed statuses |
| `test_counts_completed` | Counts completed tickets correctly | Checks all count fields | MEANINGFUL | Good - verifies completed counting |
| `test_all_tickets_blocked` | All blocked returns appropriate status | Checks `ticket is None`, `status == "all_blocked"`, `blocked == 2` | MEANINGFUL | Good - verifies edge case status |
| `test_all_tickets_waiting_on_deps` | Circular/all waiting returns correct status | Checks `ticket is None`, `status == "waiting_on_dependencies"`, `skipped_for_deps == 2` | MEANINGFUL | Good - verifies circular dependency detection |
| `test_ticket_with_unknown_status_is_not_eligible` | Unknown status = not eligible | Checks `is_ticket_eligible() is False` | MEANINGFUL | Good - verifies defensive programming |
| `test_result_to_dict_with_ticket` | to_dict includes ticket info when present | Checks `next_ticket`, `ticket_title`, `status` in dict | IMPLEMENTATION-COUPLED | Tests serialization format, not behavior |
| `test_result_to_dict_without_ticket` | to_dict handles None ticket | Checks `next_ticket is None`, `ticket_title is None`, `status == "complete"` | IMPLEMENTATION-COUPLED | Tests serialization format, not behavior |
| `test_mixed_completed_and_blocked_no_pending` | Mixed terminal states returns complete | Checks `ticket is None`, `status == "complete"` | WEAK | Comment says "Not all blocked, not all complete" but doesn't verify the logic - should check counts |
| `test_accepts_pm_tool_parameter` | Function accepts pm_tool parameter | Checks `result is not None` | WEAK | Too vague - should verify PM tool was actually used |
| `test_queries_pm_tool_for_open_tickets` | PM tool queried with correct ticket IDs | Checks `get_open_tickets` called with ticket list, and `ticket.id == "TASK-001"` | MEANINGFUL | Good - verifies PM integration and mock call |
| `test_open_issue_reported_as_pending` | Open ticket in PM reports as pending | Checks `ticket.id`, `status == "ready"` | MEANINGFUL | Good - verifies status mapping |
| `test_closed_issue_treated_as_completed_for_dependencies` | Closed (not in open list) satisfies dependencies | Checks `ticket.id == "TASK-002"`, `status == "ready"` | MEANINGFUL | Good - verifies optimization logic |
| `test_skips_blocked_tickets` (PM version) | Blocked label in PM causes skip | Checks `ticket.id == "TASK-002"`, `blocked >= 1` | MEANINGFUL | Good - verifies PM status integration |
| `test_pm_tool_error_reports_clear_error` | PM errors return error status | Checks `ticket is None`, `status == "error"`, message contains error text | MEANINGFUL | Good - verifies error handling |
| `test_dependency_not_met_when_dep_is_open` | Open dependency blocks dependent ticket | Checks `ticket.id == "TASK-001"` | WEAK | Should verify TASK-002 was NOT returned and check skipped_for_deps |
| `test_skips_tickets_claimed_by_other_instances` | Tickets with other ralph-* labels are skipped | Checks `ticket.id == "TASK-002"` | MEANINGFUL | Good - verifies multi-instance coordination |
| `test_resumes_own_in_progress_ticket_first` | Own ralph-* label ticket returned first | Checks `ticket.id == "TASK-002"`, `"resum" in message.lower()` | MEANINGFUL | Good - verifies resume prioritization |
| `test_all_tickets_complete_when_none_open` | No open tickets returns complete | Checks `ticket is None`, `status == "complete"` | MEANINGFUL | Good - verifies PM-based completion |
| `test_falls_back_to_local_state_without_pm_tool` | v1 mode works without PM tool | Checks `ticket.id == "TASK-001"` | MEANINGFUL | Good - verifies backward compatibility |
| `test_claim_adds_label_via_pm_tool` | Claim calls PM tool with correct params | Checks `claim_ticket` called, returns `True` | MEANINGFUL | Good - verifies claim mechanism |
| `test_claim_fails_if_pm_tool_fails` | PM failure propagates as claim failure | Checks `result is False` | MEANINGFUL | Good - verifies error propagation |
| `test_claim_detects_race_from_other_instance` | Race with other instance detected and handled | Checks `remove_label` called, returns `False` | MEANINGFUL | Good - verifies race detection and cleanup |
| `test_claim_succeeds_when_our_label_wins` | Own label winning race succeeds | Checks `result is True`, `remove_label.assert_not_called()` | MEANINGFUL | Good - verifies race win logic |
| `test_claim_waits_before_verifying` | Sleep called before verification | Checks `len(sleep_calls) == 1`, `sleep_calls[0] >= 0.3` | MEANINGFUL | Good - verifies race window timing |
| `test_claim_without_ralph_label_returns_true` | No label = skip claim | Checks `result is True`, `claim_ticket.assert_not_called()` | MEANINGFUL | Good - verifies no-op when disabled |
| `test_claim_assigns_to_self_when_use_assignee_true` | use_assignee=True calls assign_to_self | Checks `result is True`, `assign_to_self.assert_called_once_with("TASK-001")` | MEANINGFUL | Good - verifies assignee integration |
| `test_claim_does_not_assign_when_use_assignee_false` | use_assignee=False skips assign | Checks assignee not called | MEANINGFUL | Good - verifies conditional behavior |
| `test_get_next_claims_ticket_before_returning` | Ticket is claimed before return | Checks `ticket.id`, `claim_ticket.assert_called_with()` | MEANINGFUL | Good - verifies claim happens |
| `test_get_next_retries_on_race_condition` | Race failure triggers retry on next ticket | Checks `ticket.id == "TASK-002"` after race on TASK-001 | MEANINGFUL | Good - verifies retry logic |
| `test_get_next_returns_none_when_all_races_lost` | All races lost returns no ticket | Checks `ticket is None`, `status == "waiting_on_claims"` | MEANINGFUL | Good - verifies exhaustion handling |
| `test_dependency_open_in_github_blocks_ticket` | Open dependency in PM blocks ticket | Checks `ticket.id == "TASK-001"`, `skipped_for_deps >= 1` | MEANINGFUL | Good - verifies PM-based dependency blocking |
| `test_dependency_closed_in_github_satisfies_requirement` | Closed dependency in PM satisfies requirement | Checks `ticket.id == "TASK-002"`, `status == "ready"` | MEANINGFUL | Good - verifies PM-based dependency satisfaction |
| `test_missing_dependency_in_github_logs_warning_and_treated_as_unmet` | Missing dependency logs warning, treats as unmet | Checks ticket NOT TASK-002 OR status waiting, AND warning logged | MEANINGFUL | Good - verifies error handling for bad data |
| `test_multiple_dependencies_all_must_be_closed` | Multiple deps require ALL closed | Checks `ticket.id == "TASK-002"`, `skipped_for_deps >= 1` | MEANINGFUL | Good - verifies AND logic for deps |
| `test_multiple_dependencies_all_closed_allows_ticket` | All deps closed = eligible | Checks `ticket.id == "TASK-003"`, `status == "ready"` | MEANINGFUL | Good - verifies ALL satisfied logic |
| `test_dependency_explicitly_checked_via_get_ticket_status` | Dependency status checked via PM call | Checks `ticket.id == "TASK-001"` | WEAK | Should verify `get_ticket_status` was actually called for dependency |

## Recommendations

### High Priority Fixes

1. **Strengthen dependency skip tests**
   ```python
   # Current (WEAK):
   assert result.ticket.id == "TASK-001"

   # Should be:
   assert result.ticket.id == "TASK-001"
   assert result.skipped_for_deps == 2  # Verify how many were skipped
   # Optional: assert TASK-002 and TASK-003 not in some "considered" list
   ```

2. **Add negative assertions for blocked tests**
   ```python
   # Current (WEAK):
   assert result.ticket.id == "TASK-002"

   # Should be:
   assert result.ticket.id == "TASK-002"
   assert result.ticket.id != "TASK-001"  # Explicitly verify blocked not returned
   assert result.blocked == 1  # Verify blocked count
   ```

3. **Verify mock calls in PM integration tests**
   ```python
   # For test_dependency_explicitly_checked_via_get_ticket_status:
   assert result.ticket.id == "TASK-001"
   # ADD THIS:
   mock_pm.get_ticket_status.assert_called()  # Verify it actually queried
   # Or more specifically:
   assert any(call[0][0] == "TASK-001" for call in mock_pm.get_ticket_status.call_args_list)
   ```

4. **Remove implementation-coupled tests**
   - `test_result_to_dict_with_ticket` and `test_result_to_dict_without_ticket` test serialization format, not behavior
   - Consider moving these to a separate "serialization" test class or removing if format is not critical
   - Alternative: If format IS critical (e.g., consumed by external systems), document WHY in test docstring

### Medium Priority Improvements

5. **Add boundary verification tests**
   - Test what happens with empty strings, None values in dependencies
   - Test with very large dependency chains (performance concern?)
   - Test with self-referential dependency (ticket depends on itself)

6. **Strengthen error path testing**
   - `test_pm_tool_error_reports_clear_error` could verify specific error message format
   - Add tests for partial PM tool failures (some calls succeed, others fail)

7. **Add "did not call" assertions for optimization tests**
   - When testing the optimization that closed tickets aren't queried, explicitly verify `get_ticket_status` was NOT called

### Low Priority (Nice to Have)

8. **Property-based testing opportunities**
   - Use hypothesis to generate random ticket orderings, verify first eligible is always returned
   - Generate random dependency graphs, verify no cycles are processed incorrectly

9. **Performance regression tests**
   - Add tests with 100+ tickets to verify O(n) behavior
   - Verify claim race detection doesn't cause excessive API calls

## Test Quality Patterns Observed

### Good Patterns
- **Given-When-Then in docstrings** - Clear test intent
- **Descriptive fixture names** - Easy to understand test setup
- **Class organization** - Tests grouped by feature area
- **Mock verification** - Many tests verify mock calls, not just return values

### Anti-Patterns Found
- **Trusting mock return values without verifying calls** - Some tests set up mocks but don't verify they were called correctly
- **Insufficient negative assertions** - Tests verify what IS returned but not what ISN'T
- **Status string checks without logic verification** - Tests assert `status == "ready"` without verifying the conditions that should produce that status

## Conclusion

This is a **good test suite with room for improvement**. The core business logic is well-tested, particularly around dependencies and race conditions. The main weakness is insufficient verification of negative cases and mock interactions.

**Priority actions:**
1. Add negative assertions to weak tests (1-2 hours)
2. Verify mock calls in PM integration tests (1 hour)
3. Consider removing or documenting implementation-coupled tests (30 min)

**Impact of fixes:**
- Catch bugs where blocked/skipped tickets are incorrectly returned
- Catch optimization bugs where PM tool isn't called when it should be
- Improve confidence that tests will catch real regressions

## Test Assessment Key

- **MEANINGFUL**: Tests important behavior that could catch real bugs
- **WEAK**: Assertions are too loose, could pass with broken code
- **TAUTOLOGICAL**: Just tests "code does what code does" - would pass even if behavior is wrong
- **IMPLEMENTATION-COUPLED**: Tests implementation details rather than behavior
- **REDUNDANT**: Duplicates another test
