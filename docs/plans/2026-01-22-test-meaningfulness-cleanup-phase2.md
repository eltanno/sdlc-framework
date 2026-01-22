# Plan: Ralph Test Suite Meaningfulness Cleanup - Phase 2

**Date:** 2026-01-22
**Status:** Ready for Execution
**Scope:** Improve remaining test files (40-83% meaningful)

---

## Summary

Phase 1 fixed the 11 worst files (< 40% meaningful). Phase 2 addresses the remaining 16 files that still have room for improvement. These range from 30% to 83% meaningful.

**Goal:** Bring all files to > 80% meaningful tests.

---

## Progress Tracking

| Phase | Status | Tasks |
|-------|--------|-------|
| Phase 6: Critical (< 50%) | Complete | 4/4 |
| Phase 7: Medium (50-70%) | Complete | 4/4 |
| Phase 8: Polish (> 70%) | In Progress | 7/8 |

---

## Execution Strategy

**Approach:** Same as Phase 1 - fix one file at a time, run tests after each.
**Model:** Sonnet for engineer agents (escalate to Opus if needed)

**Priority Order:**
1. Critical files (< 50% meaningful) - biggest impact
2. Medium files (50-70%) - moderate improvements needed
3. Polish files (> 70%) - minor fixes, quick wins

---

## Phase 6: Critical Files (< 50% meaningful)

### Task 6.1: test_asana_pm.py
**File:** `.claude/ralph/tests/unit/test_asana_pm.py`
**Current:** 30% → ~80% meaningful (117 → 123 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Tests mock calls, not Asana state
- Verifies mocks were called without checking outcomes
- No verification of actual Asana API behavior

**Fixes Applied:**
- [x] Deleted 26 weak/tautological/implementation-coupled tests
- [x] Deleted entire TestAsanaPMProtocolConformance class (8 tautological tests)
- [x] Removed implementation-coupled URL verification tests
- [x] All 123 remaining tests pass

**Acceptance Criteria:**
- Tests verify data passed to Asana API is correct
- Tests verify returned data is properly processed
- No "just assert mock was called" tests

**Audit Reference:** `docs/research/2026-01-22-test-audit-asana-pm.md`

---

### Task 6.2: test_pm.py
**File:** `.claude/ralph/tests/unit/test_pm.py`
**Current:** 46% → 98% meaningful (69 → 41 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- 33% of tests are tautological (test Python, not app)
- Tests that dataclass fields exist
- Tests that enum values exist

**Fixes Applied:**
- [x] Deleted 28 tautological/implementation-coupled tests
- [x] Deleted entire TestTicketStatus, TestPMToolProtocol, TestPMToolProtocolConformance classes
- [x] Strengthened 9 weak tests with proper assertions
- [x] All 41 remaining tests pass

**Acceptance Criteria:**
- No tautological tests remain
- Tests verify PM tool behavior, not Python features

**Audit Reference:** `docs/research/2026-01-22-test-audit-pm.md`

---

### Task 6.3: test_asana_flow.py
**File:** `.claude/ralph/tests/integration/test_asana_flow.py`
**Current:** 48% → 85% meaningful (27 → 25 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Trusts return values without verification
- Missing negative assertions
- Doesn't verify Asana state changes

**Fixes Applied:**
- [x] Strengthened 11 weak/tautological tests with behavior verification
- [x] Added state verification via `get_ticket_status()` and `get_task_details()`
- [x] Added idempotency verification (no duplicate tags)
- [x] Documented API constraints where full verification impractical
- [x] 25 tests collected and load correctly

**Acceptance Criteria:**
- Tests verify both positive and negative cases
- Return values verified against expected structure

**Audit Reference:** `docs/research/2026-01-22-test-audit-asana-flow.md`

---

### Task 6.4: test_pm_flow.py
**File:** `.claude/ralph/tests/integration/test_pm_flow.py`
**Current:** 48% → 85% meaningful (21 → 20 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Missing negative assertions
- Only checks positive cases
- Doesn't verify exclusion of invalid states

**Fixes Applied:**
- [x] Deleted 3 tautological mismatch detection tests
- [x] Added negative assertions to 6 weak tests
- [x] Strengthened 2 implementation-coupled tests
- [x] Improved assertion specificity in dependency tests
- [x] All 20 remaining tests pass

**Acceptance Criteria:**
- All tests have negative assertions where applicable
- Business rules explicitly tested

**Audit Reference:** `docs/research/2026-01-22-test-audit-pm-flow.md`

---

## Phase 7: Medium Files (50-70% meaningful)

### Task 7.1: test_ticket_start.py
**File:** `.claude/ralph/tests/unit/test_ticket_start.py`
**Current:** 58% → 91% meaningful (12 → 11 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Weak branch creation tests
- Doesn't verify exact branch names
- Missing error case coverage

**Fixes Applied:**
- [x] Deleted 2 tautological tests (redundant field/flag checks)
- [x] Strengthened 3 weak tests with state file verification
- [x] Added idempotency verification to same-branch test
- [x] All 11 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-ticket-start.md`

---

### Task 7.2: test_mark_blocked.py
**File:** `.claude/ralph/tests/unit/test_mark_blocked.py`
**Current:** 60% → 88% meaningful (20 → 17 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Over-mocking external dependencies
- Tests mock structure, not behavior

**Fixes Applied:**
- [x] Deleted 1 tautological test (echo input test)
- [x] Strengthened 3 weak tests with state persistence verification
- [x] Strengthened 5 implementation-coupled tests to verify outcomes
- [x] All 17 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-mark-blocked.md`

---

### Task 7.3: test_get_next_flow.py
**File:** `.claude/ralph/tests/integration/test_get_next_flow.py`
**Current:** 60% → 100% meaningful (20 → 13 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Over-tests trivial properties
- Tests obvious things instead of behavior

**Fixes Applied:**
- [x] Deleted 7 redundant/tautological/weak tests
- [x] Removed entire TestCountAccuracy and TestStateFileIntegration classes
- [x] Strengthened in-progress resumption test with business rule docs
- [x] All 13 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-get-next-flow.md`

---

### Task 7.4: test_validate.py
**File:** `.claude/ralph/tests/unit/test_validate.py`
**Current:** 64% → 89% meaningful (22 → 18 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Working directory tests don't verify behavior
- Missing validation of actual command execution

**Fixes Applied:**
- [x] Deleted 2 tautological tests (dataclass creation, basic dict mapping)
- [x] Strengthened 3 implementation-coupled tests with outcome verification
- [x] All 18 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-validate.md`

---

## Phase 8: Polish Files (> 70% meaningful)

### Task 8.1: test_parse_deps.py
**File:** `.claude/ralph/tests/unit/test_parse_deps.py`
**Current:** 71% → ~88% meaningful (21 → 17 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Cycle detection tests are weak
- Missing edge cases

**Fixes Applied:**
- [x] Deleted 4 weak/tautological tests (redundant empty deps, redundant dash format, dataclass creation, to_dict)
- [x] Strengthened 3 circular dependency tests with exact cycle path verification
- [x] All 17 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-parse-deps.md`

---

### Task 8.2: test_ticket_done.py
**File:** `.claude/ralph/tests/unit/test_ticket_done.py`
**Current:** 71% → ~91% meaningful (24 → 22 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- GitHub tests are implementation-coupled
- Tests mock structure instead of behavior

**Fixes Applied:**
- [x] Deleted 2 redundant tests (label handling duplicates)
- [x] Strengthened 2 weak tests with proper assertions
- [x] Fixed 4 implementation-coupled tests to mock at helper boundary
- [x] All 22 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-trial-ticket-done.md`

---

### Task 8.3: test_ticket_reset.py
**File:** `.claude/ralph/tests/unit/test_ticket_reset.py`
**Current:** 73% → ~87% meaningful (15 → 15 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Redundant error case tests
- Some tests overlap

**Fixes Applied:**
- [x] Deleted 2 redundant tests, consolidated into parametrized test
- [x] Strengthened 2 weak tests (removed tautological assertion, added boundary testing)
- [x] Added blocked_count boundary case (1→0)
- [x] All 15 tests pass (parametrized)

**Audit Reference:** `docs/research/2026-01-22-test-audit-ticket-reset.md`

---

### Task 8.4: test_legacy_comparison.py
**File:** `.claude/ralph/tests/integration/test_legacy_comparison.py`
**Current:** 77% → ~90% meaningful (33 → 32 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Good behavioral focus but minor improvements possible

**Fixes Applied:**
- [x] Deleted 1 tautological test (type safety test)
- [x] Strengthened 4 weak tests (field type checks, cycle detection behavior docs, state persistence)
- [x] Renamed atomic writes test to state persistence (behavior over implementation)
- [x] All 32 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-legacy-comparison.md`

---

### Task 8.5: test_config.py
**File:** `.claude/ralph/tests/unit/test_config.py`
**Current:** 81% → ~100% meaningful (47 → 44 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Some PM tool tests are tautological

**Fixes Applied:**
- [x] Consolidated 5 tautological PM tool tests into 1 parametrized test
- [x] Deleted 2 implementation-coupled constant test classes (TestValidPmTools, TestValidRepoTools)
- [x] Strengthened 1 weak test with better docstring
- [x] All 44 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-config.md`

---

### Task 8.6: test_state.py
**File:** `.claude/ralph/tests/unit/test_state.py`
**Current:** 81% → ~93% meaningful (80 → 75 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Minor markdown generation weakness

**Fixes Applied:**
- [x] Deleted 4 tautological dataclass tests (TestDataclasses class)
- [x] Deleted 1 tautological logging test
- [x] Fixed 1 implementation-coupled test (atomic write → behavior test)
- [x] Strengthened 1 weak test (JSON fallback assertion)
- [x] All 75 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-state.md`

---

### Task 8.7: test_get_next.py
**File:** `.claude/ralph/tests/unit/test_get_next.py`
**Current:** 83% → ~95% meaningful (56 → 54 tests after cleanup)
**Status:** [x] Complete

**Issues:**
- Missing negative assertions

**Fixes Applied:**
- [x] Deleted 2 implementation-coupled to_dict tests
- [x] Strengthened 7 weak tests with negative assertions (skipped_for_deps, blocked counts, mock calls)
- [x] All 54 remaining tests pass

**Audit Reference:** `docs/research/2026-01-22-test-audit-get-next.md`

---

### Task 8.8: test_setup.py
**File:** `.claude/ralph/tests/unit/test_setup.py`
**Current:** 83% meaningful (47 tests)
**Status:** [ ] Not Started

**Issues:**
- 2 dataclass tests are tautological

**Fixes Required:**
- [ ] Remove 2 tautological dataclass tests
- [ ] Run tests to verify no regressions

**Audit Reference:** `docs/research/2026-01-22-test-audit-setup.md`

---

## Verification Commands

```bash
# Run all ralph tests
cd .claude/ralph && python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_asana_pm.py -v

# Run with coverage
python -m pytest tests/ --cov=ralph --cov-report=term-missing
```

---

## Files to Modify

| File | Current | Target | Action |
|------|---------|--------|--------|
| test_asana_pm.py | 30% | >80% | Major rewrite |
| test_pm.py | 46% | >80% | Delete tautological, strengthen |
| test_asana_flow.py | 48% | >80% | Add negative assertions |
| test_pm_flow.py | 48% | >80% | Add negative assertions |
| test_ticket_start.py | 58% | >80% | Strengthen assertions |
| test_mark_blocked.py | 60% | >80% | Reduce mocking |
| test_get_next_flow.py | 60% | >80% | Remove trivial tests |
| test_validate.py | 64% | >80% | Verify behavior |
| test_parse_deps.py | 71% | >85% | Strengthen cycle tests |
| test_ticket_done.py | 71% | >85% | Fix GitHub coupling |
| test_ticket_reset.py | 73% | >85% | Consolidate redundant |
| test_legacy_comparison.py | 77% | >85% | Minor improvements |
| test_config.py | 81% | >90% | Remove tautological |
| test_state.py | 81% | >90% | Fix markdown tests |
| test_get_next.py | 83% | >90% | Add negative assertions |
| test_setup.py | 83% | >90% | Remove 2 tautological |

---

## Success Metrics

After completion:
- All files > 80% meaningful
- No tautological tests remain
- All tests have appropriate negative assertions
- Test suite still passes
