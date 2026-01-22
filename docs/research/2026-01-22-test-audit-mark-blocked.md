# Test Audit: test_mark_blocked.py

**Date:** 2026-01-22
**File:** `.claude/ralph/tests/unit/test_mark_blocked.py`
**Focus:** Test meaningfulness (not format compliance)

## Executive Summary

**Total Tests:** 20
**Meaningful:** 12 (60%)
**Weak:** 3 (15%)
**Tautological:** 1 (5%)
**Implementation-Coupled:** 4 (20%)

**Overall Assessment:** Mixed quality. Core business logic tests are solid, but several tests verify implementation details (subprocess calls, CLI invocation patterns) rather than outcomes. Some assertions are too loose to catch real bugs.

## Detailed Test Analysis

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|----------------------|------------------|------------|-------|
| `test_mark_blocked_returns_result` | Function successfully marks a ticket as blocked and returns confirmation | Checks result dict structure, blocked_ticket, reason, timestamp fields | **WEAK** | Doesn't verify state was actually persisted. Could return correct dict but fail to save. Should verify file contents. |
| `test_mark_blocked_requires_ticket_id` | Empty ticket_id is rejected with clear error | Raises ValueError with message containing "ticket_id.*required" | **MEANINGFUL** | Good validation test. Error message check ensures useful feedback. |
| `test_mark_blocked_uses_default_reason_if_empty` | Empty reason gets replaced with a default value | `result["reason"] != ""` | **WEAK** | Too loose. Doesn't verify it's a MEANINGFUL default. Could be a space, garbage, or any non-empty string. Should check for specific default like "No reason provided". |
| `test_mark_blocked_raises_on_missing_state_file` | Missing state file causes clear failure | Raises FileNotFoundError | **MEANINGFUL** | Important edge case. Correct exception type. |
| `test_mark_blocked_raises_on_unknown_ticket` | Attempting to block non-existent ticket fails | Raises ValueError with "not found" in message | **MEANINGFUL** | Prevents silent corruption. Good validation. |
| `test_mark_blocked_adds_to_ralph_blocked` | Blocking a ticket persists it in ralph.blocked with reason | Reads file, checks `"TASK-001" in updated["ralph"]["blocked"]` and reason matches | **MEANINGFUL** | Core business logic. Verifies persistence. |
| `test_mark_blocked_clears_current_ticket` | Blocking the current ticket clears current_ticket field | Reads file, checks `updated["current_ticket"] is None` | **MEANINGFUL** | Important state transition. Prevents system confusion. |
| `test_mark_blocked_does_not_increment_blocked_count` | v2 format doesn't use legacy blocked_count field | Checks `blocked_count == 0` but ticket is in ralph.blocked | **MEANINGFUL** | Ensures v2 format behavior. Prevents regression to v1. |
| `test_mark_blocked_calls_pm_tool_add_blocked_label` | PM tool integration: adds blocked label with reason | Asserts `add_blocked_label` called once with correct args | **IMPLEMENTATION-COUPLED** | Tests HOW (method call) not WHAT (label actually added). Mock swallows real behavior. Better: verify via pm_tool.get_labels() or similar. |
| `test_mark_blocked_calls_pm_tool_remove_label` | PM tool integration: removes ralph label when blocking | Asserts `remove_label` called once with correct args | **IMPLEMENTATION-COUPLED** | Same issue. Tests mock interaction, not actual outcome. |
| `test_mark_blocked_skips_remove_label_without_ralph_label` | Without ralph_label parameter, no label removal occurs | Asserts `remove_label.assert_not_called()` | **IMPLEMENTATION-COUPLED** | Tests internal decision (to call or not), not external effect. |
| `test_mark_blocked_with_pm_tool_skips_subprocess` | When using pm_tool API, doesn't fall back to subprocess | Asserts `subprocess.run.assert_not_called()` | **IMPLEMENTATION-COUPLED** | This is pure implementation detail. If subprocess was called but pm_tool also worked, bug? No bug? Can't tell. Should test outcome (label exists) not path taken. |
| `test_mark_blocked_continues_on_pm_tool_failure` | PM tool failure doesn't prevent state update (graceful degradation) | pm_tool.add_blocked_label returns False, but state file still updated | **MEANINGFUL** | Important resilience test. Ensures local state is source of truth. |
| `test_mark_blocked_looks_up_issue_without_pm_tool` | Without pm_tool, function finds GitHub issue via CLI | Mocks subprocess to return issue, checks result["issue_number"] == 42 | **WEAK** | Verifies return value but not that lookup logic is correct. Doesn't test error handling of malformed JSON, multiple matches, etc. |
| `test_mark_blocked_uses_provided_issue_number` | When issue_number provided, skip lookup | Provides issue_number=99, checks result["issue_number"] == 99 | **TAUTOLOGICAL** | Literally tests "function returns what I gave it." No actual logic being verified. Would pass even if function did nothing. |
| `test_mark_blocked_adds_blocked_label_via_gh` | GitHub CLI integration: adds blocked label | Checks subprocess call_args_list contains "--add-label" and "blocked" | **IMPLEMENTATION-COUPLED** | Tests command construction, not effect. If command is built wrong but label gets added another way, this test fails incorrectly. |
| `test_mark_blocked_handles_no_issue_found` | No matching GitHub issue doesn't fail operation | Empty stdout ("[]"), result has issue_number=None, state still updated | **MEANINGFUL** | Good graceful degradation test. Verifies state update is independent of GitHub lookup. |
| `test_mark_blocked_handles_gh_cli_error` | GitHub CLI failure doesn't prevent state update | Mock returncode=1, verify state still updated | **MEANINGFUL** | Essential resilience test. Local state must survive external tool failures. |

## Findings by Category

### Strong Tests (Would Catch Real Bugs)
- Validation tests (empty ticket_id, unknown ticket, missing file)
- State persistence tests (adds to ralph.blocked, clears current_ticket)
- Graceful degradation tests (continues on PM tool failure, handles gh CLI error, handles no issue found)
- Format compliance (doesn't increment blocked_count in v2)

### Weak Tests (Could Pass with Broken Code)
1. **`test_mark_blocked_returns_result`**: Checks return dict but not persistence. Could return success while failing to save.
2. **`test_mark_blocked_uses_default_reason_if_empty`**: Assertion `result["reason"] != ""` is too loose. Any non-empty string passes.
3. **`test_mark_blocked_looks_up_issue_without_pm_tool`**: Only tests happy path with mocked return value. Doesn't verify lookup logic robustness.

### Implementation-Coupled Tests (Test HOW, Not WHAT)
1. **`test_mark_blocked_calls_pm_tool_add_blocked_label`**: Verifies mock.add_blocked_label was called, not that label exists.
2. **`test_mark_blocked_calls_pm_tool_remove_label`**: Same issue.
3. **`test_mark_blocked_skips_remove_label_without_ralph_label`**: Tests internal branching logic.
4. **`test_mark_blocked_with_pm_tool_skips_subprocess`**: Tests code path (subprocess not called) rather than outcome.
5. **`test_mark_blocked_adds_blocked_label_via_gh`**: Tests CLI command construction, not label application.

### Tautological Tests (Test Nothing)
1. **`test_mark_blocked_uses_provided_issue_number`**: Literally "function echoes input." Zero logic verified.

## Root Causes

### 1. Over-Mocking
Many tests mock external tools (pm_tool, subprocess) then verify the mock was called. This tests:
- "Did I write the mock correctly?"
- NOT: "Does the function achieve its goal?"

**Example:**
```python
mock_pm.add_blocked_label.assert_called_once_with("42", "Validation failed")
```
This passes if the function calls the mock. It doesn't test if the label actually gets added, or if calling with these parameters works, or if error handling exists.

### 2. Testing Return Values Instead of Side Effects
`mark_blocked` is fundamentally a side-effect function (writes state file, modifies GitHub). But several tests only verify return values, not outcomes.

**Example:**
```python
assert result["reason"] != ""  # Checks output
# Should also: assert json.loads(state_file.read_text())["ralph"]["blocked"]["TASK-001"] == expected_reason
```

### 3. Assertion Looseness
Some assertions are so permissive they'd pass with clearly wrong behavior.

**Example:**
```python
assert result["reason"] != ""  # Could be " " or "\n" or "asdfgh"
```

## Recommendations

### High Priority Fixes

1. **`test_mark_blocked_returns_result`**
   ```python
   # ADD verification of state persistence:
   updated = json.loads(state_file.read_text())
   assert "TASK-001" in updated["ralph"]["blocked"]
   assert updated["ralph"]["blocked"]["TASK-001"] == "Test failure"
   assert updated["current_ticket"] is None
   ```

2. **`test_mark_blocked_uses_default_reason_if_empty`**
   ```python
   # Replace loose assertion:
   assert result["reason"] != ""  # TOO LOOSE

   # With specific check:
   assert result["reason"] == "No reason provided"  # or whatever the default is
   # AND verify it's persisted:
   updated = json.loads(state_file.read_text())
   assert updated["ralph"]["blocked"]["TASK-001"] == "No reason provided"
   ```

3. **Delete `test_mark_blocked_uses_provided_issue_number`**
   - This test verifies no logic. It's literally `return input`.
   - If you must keep it, at least verify the provided issue_number is used in the PM tool call or gh CLI call.

### Medium Priority Refactoring

4. **PM Tool Tests Should Verify Effects, Not Calls**

   Current approach:
   ```python
   mock_pm.add_blocked_label.assert_called_once_with("42", "Validation failed")
   ```

   Better approach (requires test doubles with state):
   ```python
   # Use a FakePMTool that tracks labels
   fake_pm = FakePMTool()
   mark_blocked(..., pm_tool=fake_pm)

   # Verify outcome:
   assert fake_pm.has_label("42", "blocked")
   assert fake_pm.get_blocked_reason("42") == "Validation failed"
   assert not fake_pm.has_label("42", "ralph-1")
   ```

5. **GitHub CLI Tests Should Verify End State**

   Current:
   ```python
   assert any("--add-label" in c and "blocked" in c for c in calls)
   ```

   Better (integration test):
   ```python
   # Use actual gh CLI against test repo, or
   # Use fake that simulates gh behavior and verify label exists after
   ```

### Low Priority (Acceptable as-is)

6. **`test_mark_blocked_looks_up_issue_without_pm_tool`**
   - Currently only tests happy path
   - Consider adding: malformed JSON, multiple matches, no matches
   - But existing test is better than nothing

## Strategic Questions

### Should We Test Implementation Details?

The subprocess/pm_tool call verification tests ARE valuable for:
- **Preventing regressions** when refactoring integration code
- **Documentation** of expected API usage
- **Fast execution** (no real subprocess calls)

But they're NOT sufficient alone. They should be SUPPLEMENTED with outcome verification.

**Recommendation:** Keep these tests but mark them clearly as integration/regression tests, not behavior tests. Add outcome verification in separate tests or same test.

### Mock vs. Fake vs. Real

Current tests use mocks exclusively. Consider:

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Mock** | Fast, isolated | Tests interactions not behavior | Quick regression checks |
| **Fake** | Tests behavior, still fast | More setup code | Core business logic |
| **Real** | Highest confidence | Slow, environment dependencies | Critical paths (e.g., state persistence) |

**For this file:**
- State file writes: Use REAL (already doing this - good!)
- PM tool: Consider Fake (FakePMTool class)
- GitHub CLI: Mock for unit tests, real for integration tests in separate file

## Conclusion

The test suite has a solid foundation:
- Validation and error handling are well-tested
- State persistence is verified (the most critical behavior)
- Resilience to external failures is tested

The weaknesses are:
- Over-reliance on mocking for external integrations
- Some assertions too loose to catch subtle bugs
- Testing code structure (how) instead of outcomes (what)

**Verdict:** This is NOT "test theater." The core tests are meaningful. But ~25% of tests are implementation-coupled and could be improved by focusing on outcomes rather than internal mechanics.

**Priority:** Medium. The critical paths (state persistence, validation) are well-tested. The improvements would increase confidence but aren't urgent.
