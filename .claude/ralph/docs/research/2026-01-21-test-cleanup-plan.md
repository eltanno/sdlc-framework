# Test Cleanup Execution Plan

**Date:** 2026-01-21
**Based on:** 2026-01-21-test-audit-complete.md
**Status:** APPROVED

---

## Summary

~65 tests across 7 files need updating from v1 to v2 format.

---

## Execution Plan

### Task 1: Rewrite test_ticket_reset.py
- **Scope:** 14 tests, ALL use v1 format
- **Work:** Convert to v2 format using `RalphState` with `ralph.blocked`
- **Pattern:** Use `create_v2_state()` helper like test_ticket_done.py
- **Status:** PENDING

### Task 2: Rewrite test_ticket_start.py
- **Scope:** 10 tests use v1 format (3 are format-agnostic)
- **Work:** Convert to v2 format, remove test that tests wrong behavior
- **Note:** `test_start_ticket_updates_state_file` tests v1 behavior (writing status to state) - needs removal or rewrite
- **Status:** PENDING

### Task 3: Update test_status.py
- **Scope:** 10 tests use v1 format
- **Work:** Convert to v2 format or mock PM tool calls for status
- **Status:** PENDING

### Task 4: Update test_get_next.py
- **Scope:** ~25 tests use v1 fixtures
- **Work:** Convert fixtures to v2 format with `RalphState`
- **Status:** PENDING

### Task 5: Update test_get_next_flow.py
- **Scope:** 5 tests use v1 format
- **Work:** Convert to v2 format
- **Status:** PENDING

### Task 6: Fix test_orchestrator.py (unit)
- **Scope:** 3 tests use v1 fixtures + 1 broken assertion
- **Work:** Fix v1 fixtures, fix `or True` bug in assertion
- **Status:** PENDING

### Task 7: Fix test_package_structure.py
- **Scope:** 2 empty tests
- **Work:** Add assertions or remove empty tests
- **Status:** PENDING

---

## Execution Approach

1. One task at a time
2. Each task delegated to engineer agent
3. Run tests after each task to verify
4. Commit after each successful task

---

## Success Criteria

- All 893 tests pass
- No v1 format state usage in tests
- No empty/broken test functions
