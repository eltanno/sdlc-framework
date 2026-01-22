# Plan: Ralph Test Suite Meaningfulness Cleanup

**Date:** 2026-01-22
**Status:** Ready for Execution
**Scope:** Fix ~50% of tests that are "theater" (pass but wouldn't catch real bugs)

---

## Summary

A comprehensive audit found that half of Ralph's 893 tests provide false confidence - they pass but wouldn't catch real bugs. This plan addresses the 11 worst files (< 40% meaningful tests) with specific, trackable tasks.

**Key Finding:** An actual bug exists in `cleanup.py` that current tests don't catch.

---

## Progress Tracking

Check off tasks as they complete. This file is the single source of truth.

| Phase | Status | Tasks |
|-------|--------|-------|
| Phase 1: Quick Wins | Complete | 1/1 |
| Phase 2: Foundation | Complete | 3/3 |
| Phase 3: Higher-Level | Complete | 3/3 |
| Phase 4: Integration | In Progress | 2/3 |
| Phase 5: Special Cases | Not Started | 0/1 |

---

## Execution Strategy

**Approach:** Fix one file at a time, run tests after each to verify nothing breaks.
**Model:** Sonnet for engineer agents (escalate to Opus if needed)
**Orchestration:** Main context coordinates, delegates to engineer agents

**Order:**
1. Quick wins (delete empty tests)
2. Foundation (git/github/gitlab - other tests depend on these)
3. Higher-level functionality (pr_flow, cleanup, status)
4. Integration tests (orchestrator, ticket_lifecycle)
5. Special cases (legacy_backup)

---

## Phase 1: Quick Wins

### Task 1.1: test_package_structure.py
**File:** `.claude/ralph/tests/unit/test_package_structure.py`
**Current:** 36% meaningful (11 tests)
**Status:** [x] Complete (2026-01-22)

**Changes:**
- [x] Delete `test_core_module_importable` (empty body - just `pass`)
- [x] Delete `test_commands_module_importable` (empty body - just `pass`)
- [x] Delete `test_core_module_has_docstring` (tests Python, not app)
- [x] Delete `test_commands_module_has_docstring` (tests Python, not app)
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- No empty tests remain
- No `pass`-only test bodies
- Tests pass

**Result:** 4 tests deleted. 11 meaningful tests remain, all passing.

---

## Phase 2: Foundation Files

### Task 2.1: test_git.py
**File:** `.claude/ralph/tests/unit/test_git.py`
**Current:** 29% meaningful (38 tests - WORST)
**Status:** [x] Complete (2026-01-22)

**Pattern Fixes:**
- [x] Replace all `"git" in args` checks with `assert_called_once_with(["git", ...], ...)`
- [x] Fix `test_commit_returns_commit_sha` - test SHA parsing from realistic git output
- [x] Fix `test_create_branch_*` (7 tests) - verify exact command structure
- [x] Fix `test_has_remote_branch_*` - test actual ls-remote parsing
- [x] Fix `test_merge_*` - test merge behavior, not flag presence
- [x] Add parametrized tests for SHA parsing with multiple git output formats
- [x] Add status parsing test covering all git status flags (M, A, D, R, C, etc.)
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- No `assert "git" in args` patterns remain
- All command tests use exact argument verification
- Tests would fail if commands were malformed

**Result:** 38 tests → 50 tests (added parametrized coverage). All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-git.md`

---

### Task 2.2: test_github.py
**File:** `.claude/ralph/tests/unit/test_github.py`
**Current:** 36% meaningful (28 tests)
**Status:** [x] Complete (2026-01-22)

**Critical Fix:**
- [x] Add assertions to `test_delete_remote_branch_deletes_successfully` (currently NO assertions)

**Pattern Fixes:**
- [x] Fix 12 command structure tests to use `assert_called_once_with()` with exact args
- [x] Tighten error assertions (remove `or` logic, verify exact error properties)
- [x] Delete `test_merge_request_result_has_url_and_number` (tautological)
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- All tests have meaningful assertions
- Error assertions verify exact error type and message content
- No tests that only verify mock was called without checking args

**Result:** 28 tests → 27 tests (deleted 1 tautological). ~85% now meaningful. All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-github.md`

---

### Task 2.3: test_gitlab.py
**File:** `.claude/ralph/tests/unit/test_gitlab.py`
**Current:** 41% meaningful (29 tests)
**Status:** [x] Complete (2026-01-22)

**Pattern Fixes:**
- [x] Fix 11 weak CLI argument tests to verify complete command structure
- [x] Delete `test_merge_request_result_has_url_and_number` (tautological)
- [x] Fix `test_delete_remote_branch_deletes_successfully` (currently tests nothing)
- [x] Reduce implementation coupling in `test_merge_merge_request_with_squash`
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Same as test_github.py
- CLI command tests verify exact argument structure

**Result:** 29 tests → 26 tests (deleted 3 tautological/weak). ~100% now meaningful. All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-gitlab.md`

---

## Phase 3: Higher-Level Functionality

### Task 3.1: test_pr_flow.py
**File:** `.claude/ralph/tests/unit/test_pr_flow.py`
**Current:** 31% meaningful (29 tests)
**Status:** [x] Complete (2026-01-22)

**Tests to Delete:**
- [x] `test_pr_flow_result_contains_all_fields` (just tests dataclass)
- [x] `test_pr_flow_error_contains_message` (tests Python exception str())
- [x] `test_sync_with_main_uses_custom_branch` (tests parameter passing)
- [x] `test_pr_flow_dry_run_no_real_operations` (only checks mocks weren't called)

**Tests to Rewrite:**
- [x] `test_stage_and_commit_stages_all_and_commits` → verify commit message format
- [x] `test_push_branch_pushes_with_upstream` → test error handling
- [x] `test_merge_pr_uses_squash_by_default` → verify merge behavior

**Tests to Strengthen:**
- [x] `test_stage_and_commit_adds_coauthor` → exact format assertion
- [x] `test_create_pr_returns_pr_info` → add error cases
- [x] `test_pr_flow_complete_happy_path` → verify commit message format, PR body
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Tests verify outcomes, not just that mocks were called
- Commit message format assertions use exact patterns

**Result:** 29 tests → 30 tests (deleted 4, added 3 error handling). All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-pr-flow.md`

---

### Task 3.2: test_cleanup.py (includes bug fix)
**File:** `.claude/ralph/tests/unit/test_cleanup.py`
**Source File:** `.claude/ralph/commands/cleanup.py`
**Current:** 33% meaningful (21 tests)
**Status:** [x] Complete (2026-01-22)

**CRITICAL - Fix Actual Bug First:**
- [x] Fix `get_pending_tickets()` in cleanup.py - returns blocked tickets but shouldn't
- [x] Add test with mixed open/blocked tickets to verify correct filtering

**Tests to Delete:**
- [x] `test_cleanup_returns_summary_dict` (only checks dict has keys)
- [x] `test_cleanup_without_workflow_state` (only checks one key exists)

**Tests to Rewrite:**
- [x] `test_generate_summary_*` tests → test semantic meaning, not literal strings

**Tests to Strengthen:**
- [x] `test_get_completed_tickets_success` → verify gh CLI parameters
- [x] `test_format_output_returns_string` → verify exact numbers appear
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Bug is fixed and tests verify correct filtering
- Tests verify data correctness, not just structure

**Result:** BUG FIXED in cleanup.py. 21 tests → 22 tests. Added test that catches the bug. All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-cleanup.md`

---

### Task 3.3: test_status.py
**File:** `.claude/ralph/tests/unit/test_status.py`
**Current:** 40% meaningful (15 tests)
**Status:** [x] Complete (2026-01-22)

**Tests to Rewrite (TestFormatStatusDisplay class):**
- [x] `test_displays_no_workflow_message_when_not_initialized` → verify PRIMARY message
- [x] `test_displays_ticket_counts_when_active` → use regex: `r"completed:\s+5"`
- [x] `test_highlights_current_ticket_when_in_progress` → verify prominence
- [x] `test_displays_blocked_tickets_with_reasons` → verify association

**Tests to Fix:**
- [x] `test_to_dict_returns_serializable_dict` → verify ALL fields
- [x] `test_handles_invalid_json_state_file` → assert ALL fields safe
- [x] `test_handles_blocked_ticket_without_reason` → truthy check, not exact string
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Format tests verify structure with regex, not substring existence
- No hardcoded implementation strings

**Result:** 15 tests → 16 tests. All use regex for structure verification. All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-status.md`

---

## Phase 4: Integration Tests

### Task 4.1: test_orchestrator.py (unit)
**File:** `.claude/ralph/tests/unit/test_orchestrator.py`
**Current:** 35% meaningful (20 tests)
**Status:** [x] Complete (2026-01-22)

**Tests to Delete/Rewrite:**
- [x] `test_process_ticket_success_first_attempt` → verify data passed
- [x] `test_run_orchestrator_passes_pm_tool_to_*` (3 tests) → test data flow
- [x] `test_run_orchestrator_all_complete` → verify completion logic

**Tests to Strengthen:**
- [x] `test_parse_validation_passed` → test malformed format handling
- [x] `test_process_ticket_blocked_after_max_attempts` → verify mark_blocked args
- [x] `test_run_orchestrator_handles_pm_error_gracefully` → specific assertion

**Implementation-Coupled to Fix:**
- [x] `test_create_pm_tool_*` tests → verify tool works, not just isinstance
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Tests verify data flow and outcomes
- No tests that just check isinstance or mock called

**Result:** 20 tests → 30 tests (added malformed input tests). All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-orchestrator-unit.md`

---

### Task 4.2: test_orchestrator.py (integration)
**File:** `.claude/ralph/tests/integration/test_orchestrator.py`
**Current:** 32% meaningful (19 tests)
**Status:** [x] Complete (2026-01-22)

**Strategy:** Reduce mocking - integration tests should test integration.

- [x] Identify tests that can use real components instead of mocks
- [x] For tests requiring mocks, verify outcomes not just calls
- [x] Add end-to-end flow tests with minimal mocking
- [x] Run tests to verify no regressions

**Acceptance Criteria:**
- Integration tests actually test integration
- Heavy mocking is reduced where possible

**Result:** 19 tests → 18 tests (removed 1 tautological). All verify data flow and outcomes. All pass.

**Audit Reference:** `docs/research/2026-01-22-test-audit-orchestrator-integration.md`

---

### Task 4.3: test_ticket_lifecycle.py
**File:** `.claude/ralph/tests/integration/test_ticket_lifecycle.py`
**Current:** 40% meaningful (20 tests)
**Status:** [ ] Not Started

- [ ] Add business logic validation tests
- [ ] Verify ticket state transitions are correct
- [ ] Add negative assertions (e.g., blocked ticket not returned by get_next)
- [ ] Run tests to verify no regressions

**Acceptance Criteria:**
- Business rules are tested explicitly
- State transitions have dedicated tests

**Audit Reference:** `docs/research/2026-01-22-test-audit-ticket-lifecycle.md`

---

## Phase 5: Special Cases

### Task 5.1: test_legacy_backup.py
**File:** `.claude/ralph/tests/integration/test_legacy_backup.py`
**Current:** 0% meaningful (10 tests)
**Status:** [ ] Not Started

**Recommended Approach:** Rename + document (these are structure verification tests, not functionality tests)

- [ ] Rename file to `test_migration_structure.py`
- [ ] Add docstring explaining these are structure verification tests
- [ ] Consider adding `test_migration_functionality.py` with behavioral tests (optional)
- [ ] Run tests to verify no regressions

**Acceptance Criteria:**
- Test file name reflects what it actually tests
- Clear documentation of test purpose

**Audit Reference:** `docs/research/2026-01-22-test-audit-legacy-backup.md`

---

## Verification Commands

```bash
# Run all ralph tests
cd .claude/ralph && python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_git.py -v

# Run with coverage
python -m pytest tests/ --cov=ralph --cov-report=term-missing
```

---

## Files to Modify

| File | Action |
|------|--------|
| `.claude/ralph/tests/unit/test_package_structure.py` | Delete 4 tests |
| `.claude/ralph/tests/unit/test_git.py` | Rewrite ~20 tests |
| `.claude/ralph/tests/unit/test_github.py` | Rewrite ~15 tests |
| `.claude/ralph/tests/unit/test_gitlab.py` | Rewrite ~12 tests |
| `.claude/ralph/tests/unit/test_pr_flow.py` | Delete 4, rewrite ~8 tests |
| `.claude/ralph/tests/unit/test_cleanup.py` | Delete 2, rewrite ~5 tests |
| `.claude/ralph/src/ralph/cleanup.py` | **Fix bug** in `get_pending_tickets()` |
| `.claude/ralph/tests/unit/test_status.py` | Rewrite ~8 tests |
| `.claude/ralph/tests/unit/test_orchestrator.py` | Rewrite ~10 tests |
| `.claude/ralph/tests/integration/test_orchestrator.py` | Reduce mocking |
| `.claude/ralph/tests/integration/test_ticket_lifecycle.py` | Add business logic tests |
| `.claude/ralph/tests/integration/test_legacy_backup.py` | Rename |

---

## Common Fix Patterns Reference

```python
# 1. Substring → Exact Match
# BAD
assert "git" in command_args

# GOOD
mock_subprocess.assert_called_once_with(["git", "checkout", "-b", "feature/TASK-001"], ...)

# 2. Mock Call → Outcome Verification
# BAD
mock_subprocess.assert_called_once()

# GOOD
mock_subprocess.assert_called_once_with(["git", "push", "origin", "main"])
result = get_current_branch()
assert result == "main"

# 3. Existence → Specific Value
# BAD
assert result is not None
assert "status" in result

# GOOD
assert result["status"] == "completed"
assert result["ticket_id"] == "TASK-001"

# 4. Weak Error Assertions → Specific
# BAD
assert "error" in str(exc) or "failed" in str(exc)

# GOOD
assert isinstance(exc, GitHubError)
assert exc.command == ["gh", "pr", "view", "999"]
assert "not found" in exc.message.lower()

# 5. Format Tests → Regex
# BAD
assert "5" in output

# GOOD
assert re.search(r"completed:\s+5", output)
```

---

## Success Metrics

After completion:
- All priority files should be > 70% meaningful
- No empty/pass-only tests
- No `assert "x" in args` patterns for command verification
- Bug in cleanup.py is fixed
- Test suite still passes (100% green)
