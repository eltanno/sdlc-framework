# Test Audit: orchestrator.py Unit Tests

**Date**: 2026-01-22
**File**: `.claude/ralph/tests/unit/test_orchestrator.py`
**Auditor**: Claude Opus 4.5

## Executive Summary

**Total Tests**: 20
**Meaningful**: 7 (35%)
**Weak**: 6 (30%)
**Tautological**: 4 (20%)
**Implementation-Coupled**: 3 (15%)

**Critical Finding**: Over 60% of tests are problematic. Most tests verify mocking setup or data structure presence rather than business logic correctness.

---

## Per-Test Analysis

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_load_config_valid_file` | Config parser correctly extracts all values from YAML | Specific config values match expected | **MEANINGFUL** | Good - verifies parsing logic |
| `test_load_config_defaults` | Default values are applied when config keys are missing | Default values are used | **MEANINGFUL** | Good - verifies fallback behavior |
| `test_load_config_file_not_found` | System fails gracefully when config file doesn't exist | FileNotFoundError is raised | **MEANINGFUL** | Good - verifies error handling |
| `test_parse_validation_passed` | Parser extracts correct data from VALIDATION_PASSED output | Status equals constant, ticket_id/branch/commit extracted | **WEAK** | Only checks string parsing, not semantic meaning. Doesn't verify what happens if format is malformed. |
| `test_parse_validation_failed` | Parser handles VALIDATION_FAILED and extracts state file path | Status equals constant, state_file is not None | **WEAK** | Doesn't verify the state_file path is correct, just that something exists |
| `test_parse_no_marker` | Parser handles output without validation markers | Status is "unknown", ticket_id is None | **MEANINGFUL** | Good - verifies error case |
| `test_parse_timeout` | Parser recognizes timeout conditions | Status is "timeout" | **WEAK** | Trivial check - just tests parameter passing |
| `test_process_ticket_success_first_attempt` | A successful ticket processing triggers PR flow and marks ticket done | result.status=="completed", result.attempts==1, mocks called once | **TAUTOLOGICAL** | Just verifies mocks were called. Doesn't verify WHAT is passed to mocks or if flow order is correct |
| `test_process_ticket_blocked_after_max_attempts` | After max_attempts failures, ticket is marked blocked | result.status=="blocked", result.attempts==max_attempts | **WEAK** | Only checks the result object, not whether mark_blocked was actually called with correct parameters |
| `test_process_ticket_dry_run` | Dry run mode prevents actual execution | mock_invoke not called, status=="dry_run" | **MEANINGFUL** | Good - verifies dry run prevents side effects |
| `test_run_orchestrator_all_complete` | Orchestrator processes all tickets until none remain | result.completed_count==1, result.status=="complete" | **TAUTOLOGICAL** | Just checks the result matches the mocked response. Doesn't verify actual logic |
| `test_run_orchestrator_no_tickets` | Orchestrator handles empty ticket list gracefully | result.status=="complete", completed_count==0 | **MEANINGFUL** | Good - verifies edge case |
| `test_run_orchestrator_waiting_on_dependencies` | Orchestrator retries when tickets are waiting on dependencies | result.status=="complete", doesn't crash | **WEAK** | Doesn't verify retry count, backoff behavior, or what happens if max_wait_retries is exceeded |
| `test_select_model_below_threshold` | Complexity < threshold selects sonnet | model=="sonnet" | **MEANINGFUL** | Good - verifies business rule |
| `test_select_model_above_threshold` | Complexity > threshold selects opus | model=="opus" | **MEANINGFUL** | Good - verifies business rule |
| `test_select_model_at_threshold` | Complexity == threshold selects sonnet | model=="sonnet" | **MEANINGFUL** | Good - verifies boundary condition |
| `test_create_pm_tool_github` | Factory creates GitHubPM when config specifies github | isinstance check | **IMPLEMENTATION-COUPLED** | Tests factory implementation, not behavior. Doesn't verify the tool works correctly |
| `test_create_pm_tool_local` | Factory creates LocalPM when config specifies none | isinstance check | **IMPLEMENTATION-COUPLED** | Same issue - just checks type, not behavior |
| `test_create_pm_tool_missing_config_raises_error` | Factory fails when pm.tool is missing from config | ConfigError raised with "pm.tool" in message | **MEANINGFUL** | Good - verifies validation |
| `test_create_pm_tool_asana` | Factory creates AsanaPM when config specifies asana | isinstance check | **IMPLEMENTATION-COUPLED** | Same as other factory tests |
| `test_create_pm_tool_asana_missing_credentials_raises_auth_error` | AsanaPM fails when credentials are missing | PMAuthError raised with required env vars listed | **MEANINGFUL** | Good - verifies validation and error message quality |
| `test_run_orchestrator_passes_pm_tool_to_get_next` | Orchestrator passes PM tool to get_next_ticket | pm_tool argument matches mock, ralph_label passed | **TAUTOLOGICAL** | Just verifies the mock received parameters. Doesn't test behavior if pm_tool is wrong/None |
| `test_run_orchestrator_passes_pm_tool_to_ticket_done` | After successful validation, ticket_done receives PM tool | ticket_done called with pm_tool and ralph_label | **TAUTOLOGICAL** | Same issue - only tests mock calls, not logic |
| `test_run_orchestrator_passes_pm_tool_to_mark_blocked` | After max attempts, mark_blocked receives PM tool | mark_blocked called with pm_tool and ralph_label | **TAUTOLOGICAL** | Same issue |
| `test_run_orchestrator_handles_pm_error_gracefully` | PMError from get_next_ticket doesn't crash orchestrator | result is not None, status is "complete" or "error" | **WEAK** | Too loose - doesn't verify error is logged, state is consistent, or recovery behavior |
| `test_run_orchestrator_reads_ralph_label_from_env` | RALPH_LABEL environment variable is read and passed through | ralph_label argument matches env value | **TAUTOLOGICAL** | Just verifies parameter passing, not what happens if label is invalid |
| `test_run_orchestrator_raises_error_when_ralph_label_not_set` | Orchestrator fails fast when RALPH_LABEL is missing | RuntimeError raised with helpful message | **MEANINGFUL** | Good - verifies validation |
| `test_run_orchestrator_reads_use_assignee_from_config` | use_assignee setting is loaded from config | hasattr check or True (stub) | **TAUTOLOGICAL** | Incomplete test - just checks attribute exists |

---

## Detailed Issues by Category

### 1. Tautological Tests (Just Test "Code Does What Code Does")

**Examples**:
- `test_process_ticket_success_first_attempt`: Asserts that mocks were called, but doesn't verify the CORRECT data was passed or that the flow order is correct
- `test_run_orchestrator_passes_pm_tool_to_get_next`: Only checks that a parameter was passed to a mock, not what happens if that parameter is wrong
- `test_run_orchestrator_passes_pm_tool_to_ticket_done`: Same issue
- `test_run_orchestrator_passes_pm_tool_to_mark_blocked`: Same issue

**Why This Is Bad**: These tests would pass even if:
- Wrong data is passed to the functions
- Functions are called in the wrong order
- Critical steps are skipped
- Error handling is missing

**What They Should Test Instead**:
```python
# CURRENT (Tautological)
mock_ticket_done.assert_called()
assert call_kwargs.get("pm_tool") == mock_pm_tool

# SHOULD BE (Meaningful)
# Verify WHAT data is passed
assert call_kwargs["ticket_id"] == "TASK-001"
assert call_kwargs["pr_number"] == 42
assert call_kwargs["state_file"] == expected_state_file_path

# Verify ORDER matters
# (If ticket_done is called before PR flow, that's a bug)
call_order = [call[0] for call in mock.call_args_list]
assert call_order.index("pr_flow") < call_order.index("ticket_done")

# Verify what happens if pm_tool is None/invalid
config_with_bad_tool = config.copy()
config_with_bad_tool.pm_tool = None
with pytest.raises(ValueError, match="pm_tool is required"):
    process_ticket(ticket, config_with_bad_tool, ...)
```

### 2. Weak Assertions (Could Pass with Broken Code)

**Examples**:
- `test_parse_validation_passed`: Doesn't test what happens if output format is unexpected
- `test_parse_validation_failed`: Only checks `state_file is not None`, not that the correct path is extracted
- `test_process_ticket_blocked_after_max_attempts`: Doesn't verify mark_blocked was called
- `test_run_orchestrator_handles_pm_error_gracefully`: Only checks result exists and status is one of two values

**Why This Is Bad**: These tests have assertions that are too loose. They verify something happened, but not that the RIGHT thing happened.

**What They Should Test Instead**:
```python
# CURRENT (Weak)
assert result.state_file is not None

# SHOULD BE (Strong)
assert result.state_file == "docs/state/TASK-001/attempt-1/engineer-state.md"
assert Path(result.state_file).exists()  # Verify it's a real path

# CURRENT (Weak)
assert result is not None
assert result.status in ("complete", "error")

# SHOULD BE (Strong)
assert result.status == "error"
assert result.error_message == "PM tool query failed: API rate limit exceeded"
assert result.completed_count == 0  # No tickets processed
assert state_is_consistent(state_file)  # State not corrupted
```

### 3. Implementation-Coupled (Tests Structure, Not Behavior)

**Examples**:
- `test_create_pm_tool_github`: Just checks `isinstance(pm_tool, GitHubPM)`
- `test_create_pm_tool_local`: Just checks `isinstance(pm_tool, LocalPM)`
- `test_create_pm_tool_asana`: Just checks `isinstance(pm_tool, AsanaPM)`

**Why This Is Bad**: These tests depend on internal implementation details (the specific class returned). If you refactor to return a different type that has the same behavior, tests break.

**What They Should Test Instead**:
```python
# CURRENT (Implementation-Coupled)
assert isinstance(pm_tool, GitHubPM)

# SHOULD BE (Behavior-Focused)
# Test the interface/behavior, not the class
pm_tool = create_pm_tool(github_config_yaml)
assert pm_tool is not None

# Verify it has the required interface
assert hasattr(pm_tool, 'get_next_ticket')
assert hasattr(pm_tool, 'mark_done')
assert hasattr(pm_tool, 'mark_blocked')

# Verify it actually works with GitHub
with patch('github.Github') as mock_github:
    mock_github.return_value.get_repo.return_value = mock_repo
    ticket = pm_tool.get_next_ticket(state)
    # Verify GitHub API was called correctly
    mock_github.return_value.get_repo.assert_called_with("owner/repo")
```

---

## Critical Gaps: Untested Behavior

These important behaviors have NO tests:

1. **Retry Logic**: What happens between attempts when validation fails?
   - Is state persisted between attempts?
   - Is the previous attempt's state file passed to the next attempt?
   - Are attempts actually limited to max_attempts?

2. **Error Handling Paths**:
   - What if invoke_claude throws an exception?
   - What if pr_flow fails partway through?
   - What if state file is corrupted?

3. **State Consistency**:
   - After a ticket is blocked, is the state file updated correctly?
   - If orchestrator crashes mid-ticket, can it resume?

4. **Actual Integration**:
   - Does the PM tool actually get tickets with the correct labels?
   - Does ticket_done actually call pm_tool.mark_done with the right data?

5. **Timeout Behavior**:
   - When engineer times out, what happens to the state?
   - Is the timeout recorded? Can it be retried?

---

## Recommendations

### Priority 1: Fix Tautological Tests

**Before** (just checks mock was called):
```python
def test_process_ticket_success_first_attempt(...):
    result = process_ticket(...)
    assert result.status == "completed"
    mock_ticket_done.assert_called_once()
```

**After** (verifies correct data and order):
```python
def test_process_ticket_success_first_attempt(...):
    result = process_ticket(ticket, config, ...)

    # Verify result contains correct data
    assert result.status == "completed"
    assert result.ticket_id == ticket.id
    assert result.attempts == 1
    assert result.pr_number is not None

    # Verify ticket_done was called with correct data
    mock_ticket_done.assert_called_once_with(
        ticket_id="TASK-001",
        pr_number=42,
        pm_tool=mock_pm_tool,
        ralph_label="ralph-test",
        state_file=ANY,  # Path to state file
    )

    # Verify order: engineer -> pr_flow -> ticket_done
    call_order = [
        mock_invoke.call_args,
        mock_pr_flow.call_args,
        mock_ticket_done.call_args,
    ]
    assert all(call is not None for call in call_order)
    assert mock_invoke.call_count == 1
    assert mock_pr_flow.call_count == 1
    assert mock_ticket_done.call_count == 1
```

### Priority 2: Strengthen Weak Assertions

Add assertions that verify:
- **Exact values**, not just presence/type
- **Side effects** (files created, state updated)
- **Error messages** are helpful
- **Boundaries** (what happens at limits)

### Priority 3: Add Missing Behavior Tests

```python
def test_process_ticket_retry_passes_state_from_previous_attempt():
    """Verify that state file from failed attempt is passed to next attempt."""
    # First attempt fails
    mock_invoke.side_effect = [
        EngineerResult(status=VALIDATION_FAILED, state_file="docs/state/TASK-001/attempt-1/state.md"),
        EngineerResult(status=VALIDATION_PASSED, state_file=None),
    ]

    process_ticket(ticket, config, ...)

    # Second call should reference first attempt's state file
    second_call_prompt = mock_invoke.call_args_list[1][0][0]
    assert "attempt-1/state.md" in second_call_prompt
    assert "Previous attempt failed" in second_call_prompt

def test_process_ticket_handles_invoke_exception():
    """Verify that exceptions from invoke_claude are caught and logged."""
    mock_invoke.side_effect = RuntimeError("Claude API timeout")

    result = process_ticket(ticket, config, ...)

    assert result.status == "error"
    assert "Claude API timeout" in result.error_message
    # State should be marked as error, not left in "in_progress"
    state = load_state(state_file)
    assert state.get_ticket("TASK-001").status == "error"

def test_run_orchestrator_stops_when_pm_tool_fails():
    """Verify orchestrator stops gracefully when PM tool is unavailable."""
    mock_get_next.side_effect = PMError("GitHub API unavailable")

    result = run_orchestrator(...)

    assert result.status == "error"
    assert result.error_message == "PM tool failure: GitHub API unavailable"
    # Should not process any tickets
    assert result.completed_count == 0
```

### Priority 4: Replace Implementation-Coupled Tests

Focus on **behavior contracts** rather than concrete classes:

```python
def test_pm_tool_can_filter_by_ralph_label():
    """Verify PM tool respects ralph_label when getting next ticket."""
    pm_tool = create_pm_tool(config)

    # Mock GitHub/Asana to return tickets with different labels
    mock_api_response([
        {"id": "TASK-001", "labels": ["ralph-1"]},
        {"id": "TASK-002", "labels": ["ralph-2"]},
        {"id": "TASK-003", "labels": ["ralph-1"]},
    ])

    result = pm_tool.get_next_ticket(state, ralph_label="ralph-1")

    # Should only return tickets with ralph-1 label
    assert result.ticket_id in ["TASK-001", "TASK-003"]
```

---

## Conclusion

**The tests look comprehensive at first glance (20 tests, 1078 lines), but most verify mocking infrastructure rather than business logic.**

**Key Problems**:
1. Over-reliance on mocks without verifying what data is passed
2. Assertions that are too loose to catch bugs
3. No tests for error recovery, retry logic, or state consistency
4. Tests focus on "did this function get called" rather than "does the system behave correctly"

**To improve**: Focus every test on answering "what bug would this catch?" If the answer is "none" or "only if I completely delete the function", the test needs to be rewritten.
