# Audit Tests - Test Meaningfulness Audit

> **Systematically evaluate whether tests protect against bugs or are just theater.**

**Reference Guide:** [docs/guides/how-to-audit-tests-are-valid.md](../../docs/guides/how-to-audit-tests-are-valid.md)

## Purpose

This command audits test files to determine if they verify **correct behavior** rather than just **current behavior**.

**The core question:** "If this code was subtly broken, would this test catch it?"

**This command creates:** `docs/research/YYYY-MM-DD-test-audit-{filename}.md`

## When to Use

- After major test refactoring
- When inheriting a test suite
- Before trusting tests for a critical deployment
- When test coverage is high but bugs slip through
- As part of code quality reviews

## Arguments

$ARGUMENTS

Specify which tests to audit:
- File path: `/audit-tests tests/test_auth.py`
- Directory: `/audit-tests tests/unit/`
- Pattern description: `/audit-tests "all tests related to authentication"`
- Nothing: `/audit-tests` (will ask what to audit)

## The Five Categories

Classify each test as:

| Category | Description | Action |
|----------|-------------|--------|
| **MEANINGFUL** | Tests important behavior that could catch real bugs | Keep |
| **WEAK** | Assertions too loose - could pass with broken code | Strengthen |
| **TAUTOLOGICAL** | Tests "code does what code does" - tests language, not logic | Delete |
| **IMPLEMENTATION-COUPLED** | Tests HOW code works, not WHAT it achieves | Refactor |
| **REDUNDANT** | Duplicates another test | Delete or merge |

## Audit Process

### Step 1: Identify Test Files

Based on $ARGUMENTS, determine which test files to audit.

If no arguments provided, ask:
```
What tests would you like to audit?
- A specific file (e.g., tests/test_auth.py)
- A directory (e.g., tests/unit/)
- A pattern (e.g., "all tests for the API layer")
```

### Step 2: Spawn Audit Agents

For each test file, spawn an agent with this prompt:

```markdown
## Context
We need to audit test quality - not format compliance, but whether tests are MEANINGFUL.

## Objective
Audit `{TEST_FILE_PATH}` for TEST MEANINGFULNESS.

For each test function, answer:

1. **What behavior should this test verify?** (the specification, not the implementation)
2. **What does it actually assert?** (look at the actual assertions)
3. **Is this a meaningful test?** Answer one of:
   - **MEANINGFUL**: Tests important behavior that could catch real bugs
   - **WEAK**: Assertions are too loose, could pass with broken code
   - **TAUTOLOGICAL**: Just tests "code does what code does" - would pass even if behavior is wrong
   - **IMPLEMENTATION-COUPLED**: Tests implementation details rather than behavior
   - **REDUNDANT**: Duplicates another test
4. **If not MEANINGFUL, what's wrong?** Be specific.
5. **What SHOULD it test?** If the test is weak, what assertions would make it meaningful?

## Critical Thinking Required
- Don't assume a test is good just because it passes
- Look at WHAT is being asserted, not just that something is asserted
- Ask: "If the implementation was subtly broken, would this test catch it?"
- Ask: "Does this test verify business logic or just code structure?"

## Example Analysis Depth

BAD analysis: "test_foo asserts result is not None. Does it do that? Yes. Meaningful? Yes."

GOOD analysis: "test_foo asserts result is not None. But the function should return
a specific structure with ticket_id and status fields. Asserting 'not None' would
pass even if the function returned an empty dict, wrong ticket_id, or wrong status.
This is WEAK. Should assert: result['ticket_id'] == expected_id, result['status'] == 'completed'."

## Deliverable
Write analysis to: `docs/research/{DATE}-test-audit-{filename}.md`

Structure:
1. **Executive Summary** - How many meaningful vs problematic tests
2. **Per-Test Analysis Table**:
   | Test | Should Verify | Actually Asserts | Assessment | Issue |
3. **Statistics** - Breakdown by category
4. **Recommendations** - Priority fixes, tests to delete, tests to strengthen
```

### Step 3: Consolidate Results

After all audit agents complete, create a summary report at:
`docs/research/{DATE}-test-meaningfulness-audit-summary.md`

Include:
- **Aggregate statistics** - Total tests by category across all files
- **Worst offenders** - Files with lowest meaningful percentage
- **Common anti-patterns** - Recurring issues across the codebase
- **Priority recommendations** - What to fix first

## Anti-Patterns to Flag

Watch for these common issues:

1. **Mock Verification Without Outcome** - `mock.assert_called()` without checking results
2. **Substring Instead of Exact Match** - `assert "git" in cmd` vs `assert cmd == ["git", "push"]`
3. **Existence Instead of Correctness** - `assert result is not None` vs `assert result.status == "ok"`
4. **Missing Negative Assertions** - Only testing the happy path
5. **Testing Language Features** - `ticket.id == "TASK-001"` when dataclass guarantees this
6. **Empty/Pass Tests** - `def test_foo(): pass`

## Health Thresholds

| Rating | Meaningful % | Tautological % | Empty Tests |
|--------|--------------|----------------|-------------|
| Healthy | >70% | <10% | 0 |
| Concerning | 50-70% | 10-20% | 1+ |
| Critical | <50% | >20% | Any |

## After the Audit

1. **Delete empty tests** - They provide false confidence
2. **Delete tautological tests** - They test the language, not your code
3. **Strengthen weak tests** - Add specific value assertions
4. **Add negative assertions** - Verify exclusion, not just inclusion
5. **Refactor implementation-coupled tests** - Test outcomes, not internals

## Model Selection

- Use `sonnet` for audit agents (sufficient for analysis, cost-effective)
- Use `opus` for summary consolidation if complex patterns emerge

## Example Output

```
## Test Audit Summary - 2026-01-23

### Files Audited
- tests/test_auth.py (15 tests)
- tests/test_api.py (23 tests)

### Overall Statistics
| Category | Count | % |
|----------|-------|---|
| Meaningful | 22 | 58% |
| Weak | 8 | 21% |
| Tautological | 5 | 13% |
| Implementation-Coupled | 2 | 5% |
| Redundant | 1 | 3% |

### Priority Actions
1. DELETE: 5 tautological tests in test_auth.py
2. STRENGTHEN: 4 weak assertions in test_api.py
3. REFACTOR: test_login_calls_auth_service (implementation-coupled)
```
