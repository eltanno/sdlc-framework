# Test Cleanup Execution Plan

**Date:** 2026-01-21
**Based on:** 2026-01-21-test-audit-complete.md
**Status:** APPROVED

---

## CRITICAL: No "v1" Exists

**This is pre-alpha code. There is no legacy format to support.**

The only format is the CURRENT format:
- `ralph.tickets`: List of ticket IDs (e.g., `["TASK-001", "TASK-002"]`)
- `ralph.blocked`: Dict of blocked tickets to reasons (e.g., `{"TASK-001": "Error"}`)
- `ralph.attempts`: Dict of ticket IDs to attempt counts (e.g., `{"TASK-001": 3}`)
- `ralph.dependencies`: Dict of ticket IDs to dependency lists
- `ralph.source`: PM tool source (e.g., `"github"`, `"asana"`)

**DO NOT:**
- Create "hybrid" approaches
- Maintain backward compatibility with anything
- Populate both old and new fields

**DO:**
- Update implementations to use the current format
- Update tests to use the current format
- Delete old code paths that don't match current format

---

## Summary

~65 tests across 7 files need updating to use the current state format.

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
