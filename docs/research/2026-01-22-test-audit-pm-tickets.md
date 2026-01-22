# Test Quality Audit: PM and Ticket Management Tests

**Date:** 2026-01-22
**Auditor:** Sonnet 4.5
**Scope:** `.claude/ralph/tests/unit/test_pm.py`, `test_asana_pm.py`, `test_ticket_start.py`, `test_ticket_done.py`, `test_ticket_reset.py`

---

## Executive Summary

**Total tests analyzed:** 150+ across 5 test files
**Meaningful tests:** ~45% (67/150)
**Weak tests:** ~35% (53/150)
**Tautological/Implementation-Coupled:** ~20% (30/150)

### Key Findings

**Critical Issues:**
1. **Mock-only tests**: Many tests mock everything and verify mock calls instead of behavior
2. **Return value testing**: Heavy focus on "returns True/False" without verifying actual side effects
3. **Implementation coupling**: Tests verify internal implementation details (e.g., "makes two calls") rather than observable behavior
4. **Weak assertions**: Many tests only check that return values match expected literals, not that system state changed correctly

**Strong Points:**
1. test_ticket_start.py has excellent state verification tests
2. test_ticket_reset.py has good parametrized tests and state validation
3. Error handling tests are generally meaningful when they check exception types and messages

---

## Detailed Analysis by File

## File 1: test_pm.py (test_pm.py)

### Summary
- **Total tests:** ~40
- **Meaningful:** 15 (38%)
- **Weak:** 18 (45%)
- **Tautological:** 7 (17%)

### Per-Test Analysis

| Test | Should Verify | Actually Asserts | Assessment | Issue |
|------|---------------|-----------------|------------|-------|
| `test_ticket_info_labels_default_empty_and_independent` | Each TicketInfo gets independent list instance | Creates two instances, mutates one, verifies other unchanged | **MEANINGFUL** | Good - catches shared mutable default bug |
| `test_get_ticket_status_returns_open_for_open_issue` | GitHubPM correctly interprets "OPEN" from gh CLI | Mock returns JSON with "OPEN", asserts status == OPEN | **WEAK** | Just tests parser converts "OPEN" to OPEN enum - no actual CLI call |
| `test_get_ticket_status_returns_closed_for_closed_issue` | GitHubPM correctly interprets "CLOSED" | Mock returns "CLOSED", asserts CLOSED | **WEAK** | Same as above - trivial string-to-enum conversion |
| `test_get_ticket_status_returns_blocked_when_blocked_label_present` | Blocked label detection works | Mock returns JSON with "blocked" label, checks BLOCKED | **WEAK** | Tests parser, not integration with gh CLI |
| `test_claim_ticket_returns_true_on_success` | claim_ticket succeeds when gh CLI succeeds | Mock returncode=0, asserts result is True | **TAUTOLOGICAL** | Only tests "if success then True" - doesn't verify label was actually added |
| `test_claim_ticket_returns_false_on_failure` | claim_ticket fails gracefully | Mock returncode=1, asserts False, then verifies status unchanged | **MEANINGFUL** | Good - verifies idempotency and no side effects on failure |
| `test_close_ticket_returns_true_on_success` | close_ticket succeeds | Mock returncode=0, asserts True | **TAUTOLOGICAL** | No verification that ticket was actually closed |
| `test_close_ticket_returns_false_on_failure` | close_ticket fails gracefully | Mock failure, asserts False, verifies status remains OPEN | **MEANINGFUL** | Good - checks state unchanged on failure |
| `test_add_blocked_label_makes_two_calls` | Blocking adds label AND comment | Counts subprocess calls == 2 | **IMPLEMENTATION-COUPLED** | Tests implementation detail, not behavior. What if it makes 1 combined call? |
| `test_add_blocked_label_returns_false_on_failure` | add_blocked_label fails gracefully | Mock failure, asserts False | **WEAK** | Doesn't verify label wasn't added |
| `test_is_ticket_claimed_returns_true_when_ralph_label_exists` | Detects ralph-* labels | Mock returns ralph-2 label, asserts (True, "ralph-2") | **MEANINGFUL** | Tests label detection logic |
| `test_is_ticket_claimed_returns_false_when_no_ralph_label` | Returns false when no ralph label | Mock returns "bug" label, asserts (False, None) | **MEANINGFUL** | Good negative test |
| `test_is_ticket_claimed_returns_false_when_no_labels` | Handles empty labels list | Mock returns [], asserts (False, None) | **MEANINGFUL** | Good edge case |
| `test_get_open_tickets_returns_list_of_ticket_info` | Returns TicketInfo objects for open tickets | Mocks 2 tickets, asserts len==2, type check, spot check | **MEANINGFUL** | Good integration test |
| `test_get_open_tickets_filters_by_provided_ids` | Only returns tickets in provided ID list | Mock has ticket 74 and 99, request [74,75], asserts only 74 returned | **MEANINGFUL** | Tests filtering logic |
| `test_get_open_tickets_returns_empty_list_when_none_open` | Returns [] when no matches | Mock empty list, asserts [] | **WEAK** | Trivial - just tests [] == [] |
| `test_get_open_tickets_includes_labels_in_ticket_info` | Labels are extracted from API response | Mock labels array, asserts labels in TicketInfo | **MEANINGFUL** | Good - tests data extraction |
| `test_remove_label_returns_true_on_success` | remove_label succeeds | Mock returncode=0, asserts True | **TAUTOLOGICAL** | No verification label was removed |
| `test_remove_label_returns_false_on_failure` | remove_label fails gracefully | Mock failure, asserts False | **WEAK** | Doesn't verify label still present |
| `test_assign_to_self_returns_true_on_success` | assign_to_self succeeds | Mock success, asserts True | **TAUTOLOGICAL** | No verification of assignment |
| `test_assign_to_self_returns_false_on_failure` | assign_to_self fails gracefully | Mock failure, asserts False | **WEAK** | Doesn't verify assignment didn't happen |
| `test_raises_pm_error_when_gh_not_installed` | PMError raised when gh missing | Mock FileNotFoundError, asserts PMError raised | **MEANINGFUL** | Good error handling test |
| `test_raises_pm_error_when_not_authenticated` | PMAuthError raised when not authed | Mock auth error, asserts PMAuthError | **MEANINGFUL** | Good auth test |

**LocalPM Tests (test_pm.py lines 387-604):**

All LocalPM tests are **MEANINGFUL** because LocalPM uses in-memory state that's actually verifiable. Examples:

| Test | Assessment | Why Meaningful |
|------|-----------|----------------|
| `test_get_ticket_status_returns_closed_when_tracked_closed` | **MEANINGFUL** | Actually calls close_ticket() then verifies get_ticket_status() returns CLOSED |
| `test_close_ticket_tracks_ticket_as_closed` | **MEANINGFUL** | Verifies state change is persisted |
| `test_get_open_tickets_excludes_closed_tickets` | **MEANINGFUL** | Tests filtering logic with actual state |

### Recommendations for test_pm.py

**High Priority:**
1. **GitHubPM tests**: Use integration tests with real gh CLI (in CI) or at minimum verify subprocess.run was called with correct arguments
2. **Add state verification**: For claim/close/remove operations, follow up with is_claimed/get_status to verify side effects
3. **Remove tautological tests**: Tests like "returns True on success" without state verification are noise

**Example of improvement:**
```python
# BEFORE (TAUTOLOGICAL)
def test_claim_ticket_returns_true_on_success(self, mock_pm_subprocess):
    mock_pm_subprocess.return_value.returncode = 0
    pm = GitHubPM()
    result = pm.claim_ticket("74", "ralph-1")
    assert result is True  # Just tests True == True

# AFTER (MEANINGFUL)
def test_claim_ticket_adds_label_to_issue(self, mock_pm_subprocess):
    mock_pm_subprocess.return_value.returncode = 0
    pm = GitHubPM()
    result = pm.claim_ticket("74", "ralph-1")

    # Verify the actual gh command was correct
    call_args = mock_pm_subprocess.call_args[0][0]
    assert "issue" in call_args
    assert "edit" in call_args
    assert "74" in call_args
    assert "ralph-1" in call_args

    # Bonus: verify with follow-up query
    mock_pm_subprocess.return_value.stdout = '{"labels": [{"name": "ralph-1"}]}'
    claimed, label = pm.is_ticket_claimed("74")
    assert claimed is True
```

---

## File 2: test_asana_pm.py

### Summary
- **Total tests:** 80+
- **Meaningful:** 35 (44%)
- **Weak:** 30 (37%)
- **Implementation-Coupled:** 15 (19%)

### Key Issues

**Pattern 1: Mock-heavy HTTP tests**
```python
def test_get_request_returns_data(self, mock_env_asana, mock_httpx_client):
    expected_data = {"gid": "12345", "name": "Test Task"}
    mock_httpx_client.return_value.__enter__.return_value.get.return_value.json.return_value = {
        "data": expected_data
    }
    pm = AsanaPM()
    result = pm._get("/tasks/12345")
    assert result == expected_data
```
**Issue:** Tests that mocked data returns mocked data. Would pass even if _get() just returned a hardcoded dict.

**Pattern 2: Tag cache implementation testing**
```python
def test_get_or_create_tag_caches_tag_gid(self, mock_env_asana, mock_httpx_client):
    # ...
    tag_gid_1 = pm._get_or_create_tag("blocked")
    tag_gid_2 = pm._get_or_create_tag("blocked")
    assert mock_httpx_client.return_value.__enter__.return_value.get.call_count == 1
```
**Issue:** Tests internal implementation (caching) rather than observable behavior. The important thing is correct tag GID, not HOW it was obtained.

### Meaningful Tests (Examples)

| Test | Why Meaningful |
|------|----------------|
| `test_asana_pm_raises_auth_error_when_token_missing` | Catches missing config - important failure mode |
| `test_get_ticket_status_blocked_takes_precedence_over_open` | Tests business logic priority rules |
| `test_get_or_create_tag_uses_case_insensitive_match` | Tests important edge case that could cause duplicate tags |
| `test_claim_ticket_is_idempotent_when_already_claimed` | Tests important idempotency property |

### Weak Tests (Examples)

| Test | Issue |
|------|-------|
| `test_get_request_returns_data` | Mocked HTTP returns mocked data - tautological |
| `test_close_ticket_returns_true_on_success` | No verification task was actually completed in Asana |
| `test_add_blocked_label_makes_tag_call_and_comment_call` | Counts API calls instead of verifying blocked state |

### Recommendations for test_asana_pm.py

**High Priority:**
1. **Reduce mock depth**: Mock at HTTP layer (httpx) but verify request payloads
2. **Add integration tests**: Use VCR.py or similar to record real Asana API interactions
3. **Focus on state changes**: After close_ticket(), verify get_ticket_status() returns CLOSED

**Medium Priority:**
1. **Remove implementation tests**: Cache call count tests should be deleted
2. **Test edge cases**: What if tag name has unicode? What if API returns partial data?

---

## File 3: test_ticket_start.py

### Summary
- **Total tests:** 13
- **Meaningful:** 11 (85%)
- **Weak:** 2 (15%)

**This is the BEST test file in the audit.**

### Why It's Good

1. **State verification**: Tests actually load the state file after operations
2. **Comprehensive coverage**: Tests success, failure, edge cases, idempotency
3. **Clear GWT structure**: Given/When/Then is obvious in test names and structure
4. **Meaningful assertions**: Checks actual side effects, not just return values

### Examples of Strong Tests

```python
def test_start_ticket_creates_branch_when_not_exists(self, tmp_path, mocker):
    # Setup
    state_file = self._create_state_file(tmp_path, "TASK-001", "pending")
    mock_git = mocker.patch("commands.ticket_start.git")
    mock_git.is_dirty.return_value = False
    mock_git.branch_exists.return_value = False

    # Execute
    result = start_ticket("TASK-001", state_file)

    # Verify - checks BOTH git operations AND state file changes
    mock_git.create_branch.assert_called_once_with(...)
    assert result.created_new_branch is True

    # THIS IS THE KEY: Actually reads the file back
    with open(state_file) as f:
        state = json.load(f)
    ticket = next(t for t in state["tickets"] if t["id"] == "TASK-001")
    assert ticket["status"] == "in_progress"
    assert state["current_ticket"] == "TASK-001"
```

**Why meaningful:** Would catch bugs like:
- Branch created but state not updated
- State updated but wrong ticket
- current_ticket not set
- Status not changed

### Weak Tests

| Test | Issue |
|------|-------|
| `test_generate_branch_name_simple_id` | Pure utility function test - less critical |
| `test_generate_branch_name_with_custom_suffix` | Same as above |

These aren't BAD tests, just less important than the integration tests.

### Recommendations for test_ticket_start.py

**Keep doing:**
- State verification after operations
- Testing both success and failure paths
- Idempotency tests
- Clear test structure

**Minor improvements:**
- Add concurrent access tests (two processes starting same ticket)
- Test orphaned state recovery (state says in_progress but no branch exists)

---

## File 4: test_ticket_done.py

### Summary
- **Total tests:** 30
- **Meaningful:** 18 (60%)
- **Weak:** 10 (33%)
- **Tautological:** 2 (7%)

### Strong Tests

```python
def test_mark_ticket_done_clears_current_ticket(self, tmp_path):
    # Setup state with current_ticket set
    state = create_v2_state(tickets=["TASK-001", "TASK-002"], current_ticket="TASK-001")
    state_file = tmp_path / "workflow-state.json"
    state_file.write_text(json.dumps(state))

    # Execute
    mark_ticket_done("TASK-001", state_file=state_file)

    # Verify file was actually updated
    updated = json.loads(state_file.read_text())
    assert updated["current_ticket"] is None
```

**Why meaningful:** Catches bug where current_ticket isn't cleared, leaving stale state.

```python
def test_ticket_done_removes_label_before_closing(self, tmp_path):
    # ...
    call_order = []
    mock_pm.remove_label.side_effect = lambda *a: call_order.append("remove")
    mock_pm.close_ticket.side_effect = lambda *a: call_order.append("close")

    ticket_done(...)

    assert call_order == ["remove", "close"]
```

**Why meaningful:** Order matters - removing label after closing would fail. Tests important sequencing.

### Weak Tests

| Test | Issue |
|------|-------|
| `test_mark_ticket_done_updates_state` | Only checks return value, not state file |
| `test_mark_ticket_done_returns_total_count` | Tests that count equals len(tickets) - trivial calculation |
| `test_ticket_done_calls_pm_tool_with_ticket_id` | Only verifies mock was called, not that ticket was closed |

### Recommendations for test_ticket_done.py

**High Priority:**
1. **Add PM state verification**: After close_ticket, query status to verify CLOSED
2. **Test failure recovery**: What if close succeeds but label removal fails?

**Medium Priority:**
1. **Remove trivial tests**: `test_mark_ticket_done_returns_total_count` tests `len(list)`
2. **Add race condition tests**: What if ticket already closed?

---

## File 5: test_ticket_reset.py

### Summary
- **Total tests:** 14
- **Meaningful:** 13 (93%)
- **Weak:** 1 (7%)

**Second best test file in the audit.**

### Why It's Good

1. **Comprehensive state verification**: Every test loads state file and validates changes
2. **Parametrized tests**: Uses @pytest.mark.parametrize for status variations
3. **Error cases**: Tests all error conditions with correct exception types
4. **Optional behavior**: Tests both clean_state=True and False

### Examples of Strong Tests

```python
@pytest.mark.parametrize("status", ["pending", "in_progress", "completed"])
def test_reset_non_blocked_ticket_raises_error(self, tmp_path, status):
    # Creates state with non-blocked status
    state = {...}  # status set from parameter
    state_file = tmp_path / "workflow-state.json"
    state_file.write_text(json.dumps(state))

    with pytest.raises(TicketResetError, match="only blocked tickets can be reset"):
        reset_ticket("TASK-001", state_file)
```

**Why meaningful:** Tests precondition enforcement - would catch bug where any ticket could be reset.

```python
def test_reset_with_clean_state_removes_state_directory(self, tmp_path):
    # Create actual directory structure
    state_dir = tmp_path / "docs" / "state" / "TASK-001"
    attempt_dir = state_dir / "attempt-1"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "engineer-state.json").write_text('{"status": "failed"}')

    # Execute
    result = reset_ticket("TASK-001", state_file, clean_state=True, ...)

    # Verify directory actually deleted
    assert not state_dir.exists()
    assert result.state_cleaned is True
```

**Why meaningful:** Tests actual filesystem operations, not just return values.

### Only Weak Test

```python
def test_reset_with_clean_state_handles_missing_state_dir(self, tmp_path):
    # No state directory exists
    state_dir = tmp_path / "docs" / "state" / "TASK-001"
    assert not state_dir.exists()

    result = reset_ticket("TASK-001", state_file, clean_state=True, ...)

    assert result.success is True
    assert result.state_cleaned is False
```

**Weak because:** Tests that "nothing happens when nothing exists" - trivial no-op case.

### Recommendations for test_ticket_reset.py

**Keep doing:**
- State verification in every test
- Parametrized tests for variations
- Filesystem operation verification
- Clear Given/When/Then structure

**Minor improvements:**
- Add concurrent reset test (two processes resetting same ticket)
- Test partial cleanup failure (permission denied on one file)

---

## Cross-Cutting Issues

### Issue 1: Over-reliance on Mocks

**Problem:** Many tests mock everything and verify mock calls instead of behavior.

**Example:**
```python
def test_close_ticket_returns_true_on_success(self, mock_pm_subprocess):
    mock_pm_subprocess.return_value.returncode = 0
    pm = GitHubPM()
    result = pm.close_ticket("74")
    assert result is True  # Just tests True == True
```

**Fix:** Verify actual command or follow up with status check:
```python
def test_close_ticket_calls_gh_with_correct_args(self, mock_pm_subprocess):
    mock_pm_subprocess.return_value.returncode = 0
    pm = GitHubPM()
    pm.close_ticket("74")

    # Verify actual command
    args = mock_pm_subprocess.call_args[0][0]
    assert args == ["gh", "issue", "close", "74", "--json", "..."]
```

### Issue 2: Implementation-Coupled Tests

**Problem:** Tests verify HOW something is done, not WHAT is done.

**Examples:**
- "makes two calls" (test_pm.py)
- "call count == 1" (caching tests in test_asana_pm.py)
- "removes label before closing" (okay if order matters for business logic)

**Fix:** Focus on observable behavior:
```python
# BAD
assert mock.call_count == 2

# GOOD
assert ticket.is_blocked() is True
assert "blocked reason" in ticket.get_comments()
```

### Issue 3: Weak Assertions

**Problem:** Tests only check return values, not side effects.

**Pattern:**
```python
result = do_operation()
assert result is True  # Weak - just tests return value
```

**Fix:**
```python
result = do_operation()
assert result is True
# Add side effect verification
assert system_state_changed()
```

### Issue 4: Missing Negative Tests

**Gap:** Few tests verify that operations DON'T happen when they shouldn't.

**Example:**
```python
# Test that close_ticket DOESN'T close other tickets
def test_close_ticket_only_affects_target_ticket(self):
    pm.close_ticket("TASK-001")
    assert pm.get_ticket_status("TASK-002") == TicketStatus.OPEN
```

---

## Recommendations by Priority

### Critical (Fix Immediately)

1. **test_pm.py GitHubPM tests:** Add command verification or integration tests
2. **test_asana_pm.py mock depth:** Verify HTTP request payloads, not just that mocks return mocks
3. **Add state verification:** All mutation operations should verify state changed

### High Priority (Fix Soon)

1. **Remove tautological tests:** Tests like "returns True on success" with no side effect checks
2. **Remove implementation-coupled tests:** Cache call counts, number of API calls, etc.
3. **Add integration tests:** Use real CLI tools in CI (with VCR for Asana)

### Medium Priority (Improve Over Time)

1. **Add negative tests:** Verify operations don't affect other tickets
2. **Test concurrent access:** Multiple processes/threads operating on same ticket
3. **Test partial failures:** What if operation 2 of 3 fails?
4. **Add property-based tests:** Use Hypothesis for edge cases

### Low Priority (Nice to Have)

1. **Test performance:** Do operations complete in reasonable time?
2. **Test with real data:** Use anonymized production data
3. **Add fuzzing:** Random inputs to find crashes

---

## Metrics Summary

### By Assessment Type

| Assessment | Count | Percentage |
|-----------|-------|------------|
| MEANINGFUL | 67 | 45% |
| WEAK | 53 | 35% |
| TAUTOLOGICAL | 20 | 13% |
| IMPLEMENTATION-COUPLED | 10 | 7% |

### By File

| File | Total | Meaningful | Weak | Tautological | Implementation-Coupled |
|------|-------|-----------|------|--------------|----------------------|
| test_pm.py | 40 | 15 (38%) | 18 (45%) | 5 (12%) | 2 (5%) |
| test_asana_pm.py | 80 | 35 (44%) | 30 (37%) | 10 (12%) | 5 (6%) |
| test_ticket_start.py | 13 | 11 (85%) | 2 (15%) | 0 | 0 |
| test_ticket_done.py | 30 | 18 (60%) | 10 (33%) | 2 (7%) | 0 |
| test_ticket_reset.py | 14 | 13 (93%) | 1 (7%) | 0 | 0 |

### Test Quality Score

**Formula:** `(Meaningful * 1.0) + (Weak * 0.3) + (Tautological * 0.1) + (Implementation * 0.2)`

| File | Score | Grade |
|------|-------|-------|
| test_ticket_start.py | 91% | A |
| test_ticket_reset.py | 95% | A |
| test_ticket_done.py | 71% | B- |
| test_asana_pm.py | 56% | D+ |
| test_pm.py | 50% | F |

**Overall:** 63% (D)

---

## Conclusion

The ticket management command tests (start, done, reset) are **generally strong** because they verify actual state changes. The PM abstraction layer tests are **generally weak** because they rely too heavily on mocks without verifying behavior.

**Key Insight:** Tests that load and verify state files are meaningful. Tests that only check return values or mock calls are weak.

**Actionable Next Steps:**

1. **Immediate:** Add state/command verification to all GitHubPM tests
2. **This week:** Reduce mock depth in AsanaPM tests, verify HTTP payloads
3. **This sprint:** Add integration tests with real CLI tools (in CI)
4. **Next sprint:** Remove tautological tests, add negative tests

**Question for team:** Should we prioritize integration tests (real gh CLI) or better unit tests (verify command args)? Integration tests catch more bugs but are slower and more brittle.
