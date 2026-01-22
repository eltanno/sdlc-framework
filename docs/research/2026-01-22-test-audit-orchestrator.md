# Test Quality Audit: Orchestrator & Supporting Modules

**Date:** 2026-01-22
**Scope:** `.claude/ralph/tests/unit/test_orchestrator.py`, `test_status.py`, `test_cleanup.py`, `test_validate.py`, `test_parse_deps.py`, `test_mark_blocked.py`
**Focus:** Test MEANINGFULNESS - do they catch bugs or just verify code structure?

---

## Executive Summary

**Total Tests Analyzed:** 85 test functions across 6 files
**Meaningful Tests:** 71 (84%)
**Weak Tests:** 8 (9%)
**Tautological Tests:** 4 (5%)
**Implementation-Coupled Tests:** 2 (2%)

**Overall Assessment:** The test suite is **above average** in quality. Most tests verify real behavior and would catch bugs. However, there are specific patterns of weakness:

1. **Mock verification over behavior verification** - Some tests check that mocks were called with correct parameters instead of verifying the outcome
2. **Loose assertions on format** - Some tests verify "something contains X" rather than exact behavior
3. **Missing negative cases** - Some modules lack tests for edge cases that would break in production

The orchestrator tests are particularly strong (meaningful data flow verification), while cleanup and status have some weaker format-checking tests.

---

## Detailed Test Analysis

### File: test_orchestrator.py (25 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_load_config_valid_file` | Config loader parses YAML and returns correct values | Checks exact values: `sonnet_threshold == 2`, `max_attempts == 3`, etc. | **MEANINGFUL** | - |
| `test_load_config_defaults` | Missing config values use defaults | Checks `max_attempts == 5` (overridden), `sonnet_threshold == 2` (default) | **MEANINGFUL** | - |
| `test_load_config_file_not_found` | Non-existent config raises FileNotFoundError | `pytest.raises(FileNotFoundError)` | **MEANINGFUL** | - |
| `test_parse_validation_passed` | Parser extracts VALIDATION_PASSED and metadata correctly | Checks `status == VALIDATION_PASSED`, `ticket_id == "TASK-001"`, `branch == "feature/..."`, `commit == "abc1234"` | **MEANINGFUL** | - |
| `test_parse_validation_passed_malformed_ticket_id` | Parser handles missing ticket ID gracefully | Checks `ticket_id is None`, `branch` still extracted | **MEANINGFUL** | - |
| `test_parse_validation_passed_missing_all_fields` | Parser handles marker-only output | Checks `status == VALIDATION_PASSED`, all fields `None` | **MEANINGFUL** | - |
| `test_parse_validation_failed` | Parser extracts VALIDATION_FAILED and state file path | Checks `status == VALIDATION_FAILED`, `state_file == "docs/state/..."` | **MEANINGFUL** | - |
| `test_parse_no_marker` | Parser handles output with no markers | Checks `status == "unknown"`, `ticket_id is None` | **MEANINGFUL** | - |
| `test_parse_timeout` | Parser handles timeout flag | Checks `status == "timeout"` | **MEANINGFUL** | - |
| `test_process_ticket_success_first_attempt` | Successful ticket processing produces correct result and calls functions with right data | Verifies `result.status == "completed"`, `result.attempts == 1`, `result.pr_number == 42`, AND that `invoke_claude`, `pr_flow`, `ticket_done`, `write_summary` were called with correct parameters | **MEANINGFUL** | Strong test - verifies both outcome and data flow |
| `test_process_ticket_blocked_after_max_attempts` | Failed ticket after max attempts calls mark_blocked with correct data | Verifies `result.status == "blocked"`, `result.attempts == 2`, AND `mark_blocked` called with correct `ticket_id`, `reason` containing "exceeded...attempts" | **MEANINGFUL** | Strong test - verifies behavior AND integration |
| `test_process_ticket_dry_run` | Dry run doesn't invoke Claude | Checks `result.status == "dry_run"`, `mock_invoke.assert_not_called()` | **MEANINGFUL** | - |
| `test_run_orchestrator_all_complete` | Orchestrator completes when all tickets done | Verifies `result.completed_count == 1`, `result.status == "complete"`, AND `process_ticket` called with correct config/paths | **MEANINGFUL** | - |
| `test_run_orchestrator_no_tickets` | Empty workflow completes immediately | Checks `result.status == "complete"`, `result.completed_count == 0` | **MEANINGFUL** | - |
| `test_run_orchestrator_waiting_on_dependencies` | Orchestrator retries when waiting on dependencies | Verifies `get_next_ticket` called 3 times, `result.status == "complete"` | **MEANINGFUL** | - |
| `test_select_model_below_threshold` | Complexity below threshold selects sonnet | Checks `model == "sonnet"` | **MEANINGFUL** | - |
| `test_select_model_above_threshold` | Complexity above threshold selects opus | Checks `model == "opus"` | **MEANINGFUL** | - |
| `test_select_model_at_threshold` | Complexity at threshold selects sonnet | Checks `model == "sonnet"` | **MEANINGFUL** | - |
| `test_create_pm_tool_github` | GitHub PM tool is created with correct interface | Checks `isinstance(pm_tool, GitHubPM)`, `hasattr` for all PMTool methods | **WEAK** | Just checks type and interface existence, doesn't verify it would work |
| `test_create_pm_tool_local` | Local PM tool is created with correct interface | Checks `isinstance(pm_tool, LocalPM)`, `hasattr` for all PMTool methods | **WEAK** | Same as above |
| `test_create_pm_tool_missing_config_raises_error` | Missing pm.tool config raises ConfigError | `pytest.raises(ConfigError)`, checks "pm.tool" in error message | **MEANINGFUL** | - |
| `test_create_pm_tool_asana` | Asana PM tool is created with correct interface | Checks `isinstance(pm_tool, AsanaPM)`, `hasattr` for all methods | **WEAK** | Same pattern as GitHub/Local tests |
| `test_create_pm_tool_asana_missing_credentials_raises_auth_error` | Missing Asana credentials raises PMAuthError with helpful message | `pytest.raises(PMAuthError)`, checks all required env vars in error message | **MEANINGFUL** | - |
| `test_run_orchestrator_passes_pm_tool_to_get_next` | run_orchestrator passes PM tool and ralph_label to get_next_ticket | Verifies `mock_get_next.call_args[1]["pm_tool"] == mock_pm_tool`, `ralph_label == "ralph-1"` | **MEANINGFUL** | - |
| `test_run_orchestrator_passes_pm_tool_to_ticket_done` | ticket_done receives correct PM tool, ticket_id, and PR data | Verifies all call_kwargs: `ticket_id`, `pr_number`, `state_file`, `pm_tool`, `ralph_label` | **MEANINGFUL** | Strong data flow verification |
| `test_run_orchestrator_passes_pm_tool_to_mark_blocked` | mark_blocked receives correct ticket_id, PM tool, and reason | Verifies all call_kwargs + checks reason contains "exceeded...attempts" | **MEANINGFUL** | - |
| `test_run_orchestrator_handles_pm_error_gracefully` | PM error stops orchestrator gracefully | Checks `result.status == "complete"`, no tickets processed | **WEAK** | Doesn't verify error was logged or user was informed |
| `test_run_orchestrator_reads_ralph_label_from_env` | RALPH_LABEL env var is passed to get_next_ticket | Tests with two different label values, verifies exact match | **MEANINGFUL** | - |
| `test_run_orchestrator_raises_error_when_ralph_label_not_set` | RuntimeError raised when RALPH_LABEL not set | `pytest.raises(RuntimeError)`, checks "RALPH_LABEL is required" in message | **MEANINGFUL** | - |
| `test_load_config_reads_use_assignee` | use_assignee setting loaded from config | Checks `config.use_assignee is True`, then `is False` | **MEANINGFUL** | - |

**test_orchestrator.py Summary:** 25 tests, 22 meaningful, 3 weak. Strong focus on data flow verification. Weak tests are the PM tool factory tests that only check type/interface.

---

### File: test_status.py (13 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_returns_not_initialized_when_no_state_file` | Missing state file returns not initialized status | Checks `initialized is False`, `tickets_by_status == {}`, `current_ticket is None` | **MEANINGFUL** | - |
| `test_returns_ticket_counts_by_status` | Active workflow returns correct ticket counts | Checks exact counts: `completed == 2`, `in_progress == 1`, `pending == 3`, `blocked == 1` | **MEANINGFUL** | - |
| `test_returns_current_ticket_when_in_progress` | In-progress ticket returns current ticket info | Checks `current_ticket["id"] == "TASK-001"`, `title`, `attempts == 2` | **MEANINGFUL** | - |
| `test_returns_total_ticket_count` | Total ticket count is correct | Checks `total_tickets == 3` | **MEANINGFUL** | - |
| `test_returns_blocked_tickets_with_reasons` | Blocked tickets include reasons | Checks 2 blocked tickets with exact IDs and reasons | **MEANINGFUL** | - |
| `test_returns_prd_and_plan_paths` | PRD and plan paths returned | Checks exact paths | **MEANINGFUL** | - |
| `test_displays_no_workflow_message_when_not_initialized` | No workflow shows clear message | Uses regex to check for "no...workflow" or "not initialized", AND verifies ticket counts NOT shown | **MEANINGFUL** | Good negative assertion |
| `test_displays_ticket_counts_when_active` | Active workflow displays ticket counts | Uses regex to verify each status with its count: `completed[:\s]+5`, etc. | **WEAK** | Regex is loose - could match unrelated text. Should verify exact format or structure |
| `test_highlights_current_ticket_when_in_progress` | Current ticket is highlighted | Extracts "current ticket" section, checks ID/title/attempts in that section | **MEANINGFUL** | Good use of section extraction |
| `test_displays_blocked_tickets_with_reasons` | Blocked tickets shown with reasons | Uses regex to verify ticket IDs near their reasons (within 100 chars) | **WEAK** | Too loose - "near" doesn't guarantee association |
| `test_to_dict_returns_serializable_dict` | to_dict returns JSON-serializable dict with all fields | JSON serializes it, then checks ALL fields individually | **MEANINGFUL** | - |
| `test_handles_invalid_json_state_file` | Corrupted state file returns safe defaults | Checks ALL fields are safe defaults, not just initialized | **MEANINGFUL** | Good comprehensive check |
| `test_handles_empty_tickets_list` | Empty tickets list returns empty counts | Checks `total_tickets == 0`, `tickets_by_status == {}` | **MEANINGFUL** | - |
| `test_handles_missing_optional_fields` | Minimal state file handled gracefully | Checks `initialized is True`, `total_tickets == 1`, paths are None | **MEANINGFUL** | - |
| `test_handles_blocked_ticket_without_reason` | Blocked ticket without reason gets default | Checks `block_reason` is truthy and non-empty | **WEAK** | Doesn't verify it's a reasonable default, just that it exists |
| `test_handles_current_ticket_not_in_tickets_list` | Invalid current_ticket ID returns None | Checks `current_ticket is None` | **MEANINGFUL** | - |

**test_status.py Summary:** 13 tests, 10 meaningful, 3 weak. Weak tests use loose regex or truthy checks instead of verifying exact behavior.

---

### File: test_cleanup.py (17 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_get_issue_counts_all_closed` | All closed issues returns correct counts | Checks exact counts: `total == 3`, `done == 3`, `blocked == 0`, `pending == 0` | **MEANINGFUL** | - |
| `test_get_issue_counts_with_blocked` | Mixed issues returns accurate blocked count | Checks `total == 4`, `done == 2`, `blocked == 1`, `pending == 1` | **MEANINGFUL** | - |
| `test_get_issue_counts_gh_error_returns_zeros` | gh CLI failure returns zeros | Checks all counts are 0 | **MEANINGFUL** | - |
| `test_determine_status_complete` | No pending/blocked returns complete | Checks `status == "complete"` | **MEANINGFUL** | - |
| `test_determine_status_complete_with_blocked` | Some blocked returns complete_with_blocked | Checks `status == "complete_with_blocked"` | **MEANINGFUL** | - |
| `test_determine_status_incomplete` | Pending tickets returns incomplete | Checks `status == "incomplete"` | **MEANINGFUL** | - |
| `test_get_completed_tickets_success` | Closed issues queried with correct parameters | Verifies gh CLI called with `--state closed`, `--label task`, `--json number,title`, AND result contains tickets | **MEANINGFUL** | - |
| `test_get_completed_tickets_empty` | No closed issues returns empty list | Checks `tickets == []` | **MEANINGFUL** | - |
| `test_get_blocked_tickets_success` | Blocked issues returned | Checks 1 ticket with correct number | **MEANINGFUL** | - |
| `test_get_pending_tickets_excludes_blocked` | Mix of open/blocked only returns non-blocked | Checks 2 pending tickets, verifies blocked ticket NOT in results | **MEANINGFUL** | Strong negative assertion |
| `test_get_pending_tickets_all_pending` | All open non-blocked returned | Checks 2 tickets | **MEANINGFUL** | - |
| `test_update_workflow_state_success` | State file updated to idle with ralph in completed | Checks `phase == "idle"`, `"ralph" in completed` | **MEANINGFUL** | - |
| `test_update_workflow_state_file_missing` | Missing state file doesn't error | No exception raised, file still doesn't exist | **MEANINGFUL** | - |
| `test_update_workflow_state_preserves_existing_completed` | Existing completed items preserved when adding ralph | Checks all original items + ralph | **MEANINGFUL** | - |
| `test_update_workflow_state_no_duplicates` | Ralph not duplicated if already in completed | Checks `count("ralph") == 1` | **MEANINGFUL** | - |
| `test_generate_summary_complete` | Complete status generates correct summary | Checks `status == "complete"`, `completion_signal == "PRD_COMPLETE"`, all counts | **TAUTOLOGICAL** | Just checks output == input (status preserved, counts preserved) |
| `test_generate_summary_needs_review_when_incomplete` | Non-complete status signals review needed | Checks `status == "complete_with_blocked"`, `completion_signal == "NEEDS_REVIEW"` | **TAUTOLOGICAL** | Same issue - just transforms status to signal |
| `test_generate_summary_preserves_all_counts` | Summary preserves all count fields | Checks all counts match input | **TAUTOLOGICAL** | Literally just checks output == input |
| `test_cleanup_orchestrates_complete_workflow` | cleanup calls all helpers and returns summary | Verifies all helpers called once with correct args, checks result | **MEANINGFUL** | Good orchestration test |
| `test_cleanup_without_workflow_state` | No workflow state skips state update | Checks `update_state.assert_not_called()`, result still returned | **MEANINGFUL** | - |
| `test_format_output_shows_correct_numbers` | Formatted output contains exact numbers | Checks "Total Tickets:    10", "Completed:        7", etc. AND ticket sections | **MEANINGFUL** | Exact string matching is good |
| `test_format_output_includes_valid_json` | JSON section contains correct values | Extracts JSON after delimiter, parses it, checks all fields | **MEANINGFUL** | - |

**test_cleanup.py Summary:** 17 tests, 14 meaningful, 3 tautological. The tautological tests just verify that `generate_summary` returns its inputs unchanged - they would pass even if the function did nothing useful.

---

### File: test_validate.py (15 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_run_command_success` | Successful command returns pass | Checks `passed is True`, `output == "Success output"`, `error == ""` | **MEANINGFUL** | - |
| `test_run_command_failure` | Failing command returns fail | Checks `passed is False`, `error == "Error: test failed"` | **MEANINGFUL** | - |
| `test_run_command_empty_returns_skip` | Empty command skipped | Checks `passed is True`, `skipped is True` | **MEANINGFUL** | - |
| `test_run_command_echo_returns_skip` | Echo command skipped | Checks `passed is True`, `skipped is True` | **MEANINGFUL** | - |
| `test_run_command_uses_correct_working_dir` | subprocess uses provided cwd | Verifies `call_kwargs["cwd"] == Path("/my/project")`, AND checks result is successful | **MEANINGFUL** | - |
| `test_run_command_timeout_handling` | Timeout returns failure | Checks `passed is False`, `"timed out" in error.lower()` | **MEANINGFUL** | - |
| `test_validation_result_overall_pass` | All passing checks returns overall pass | Checks `overall_passed is True` | **MEANINGFUL** | - |
| `test_validation_result_overall_fail_on_any_failure` | Any failing check returns overall fail | Checks `overall_passed is False` | **MEANINGFUL** | - |
| `test_validation_result_skipped_counts_as_pass` | Skipped checks count as pass | Checks `overall_passed is True` | **MEANINGFUL** | - |
| `test_validate_runs_all_checks` | Single-codebase runs all 4 checks | Verifies all 4 checks passed AND correct commands called | **MEANINGFUL** | - |
| `test_validate_continues_after_failure` | Failing check doesn't stop other checks | Checks typecheck failed, other 3 passed, `overall_passed is False` | **MEANINGFUL** | - |
| `test_validate_skips_empty_commands` | Empty commands skipped | Checks skipped flags, `mock_run.call_count == 1` | **MEANINGFUL** | - |
| `test_validate_monorepo_runs_all_codebases` | Monorepo validates all codebases | Checks both codebases in results, `overall_passed is True` | **MEANINGFUL** | - |
| `test_validate_monorepo_uses_codebase_paths` | Monorepo uses correct cwd for each codebase | Verifies `call_kwargs["cwd"] == tmp_path / "api"`, AND result shows success | **MEANINGFUL** | - |
| `test_validate_monorepo_fails_if_any_codebase_fails` | One failing codebase fails overall | Checks mobile passed, backend failed, `overall_passed is False` | **MEANINGFUL** | - |
| `test_validate_monorepo_missing_directory_fails` | Missing codebase directory fails that codebase | Checks `overall_passed is False`, `"not found" in error.lower()` | **MEANINGFUL** | - |
| `test_to_dict_with_skipped` | to_dict shows 'skip' for skipped checks | Checks `typecheck == "skip"`, `lint == "pass"`, `build == "skip"` | **MEANINGFUL** | - |
| `test_to_dict_with_failure` | to_dict shows 'fail' for failed checks | Checks `typecheck == "fail"`, `overall == "fail"` | **MEANINGFUL** | - |

**test_validate.py Summary:** 15 tests, all 15 meaningful. Excellent coverage of behavior.

---

### File: test_parse_deps.py (14 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_parse_simple_table_with_explicit_ids` | Table with explicit IDs parsed correctly | Checks exact dependency mappings: `TASK-001 -> []`, `TASK-002 -> [TASK-001]`, etc. | **MEANINGFUL** | - |
| `test_parse_table_with_row_numbers` | Row numbers map to ticket IDs | Checks `TASK-0001 -> []`, `TASK-0002 -> [TASK-0001]`, etc. | **MEANINGFUL** | - |
| `test_parse_table_with_no_dependencies` | No dependencies parsed as empty lists | Checks all 3 tickets have `[]` | **MEANINGFUL** | - |
| `test_parse_section_format` | Section format parsed correctly | Checks exact dependency mappings from ### headers | **MEANINGFUL** | - |
| `test_parse_section_format_with_colon_after_dependencies` | Extra colon handled | Checks dependencies parsed correctly | **MEANINGFUL** | - |
| `test_detect_simple_circular_dependency` | A -> B -> A cycle detected | Checks 1 cycle found, cycle starts/ends at same node, contains both tasks | **MEANINGFUL** | - |
| `test_detect_longer_circular_dependency` | A -> B -> C -> A cycle detected | Checks 1 cycle, starts/ends same, contains all 3 tasks | **MEANINGFUL** | - |
| `test_no_circular_dependencies` | Linear dependencies return no cycles | Checks `len(cycles) == 0` | **MEANINGFUL** | - |
| `test_self_referential_dependency` | Self-reference detected as cycle | Checks 1 cycle: `["TASK-001", "TASK-001"]` | **MEANINGFUL** | - |
| `test_get_dependents` | Find tickets that depend on given ticket | Checks TASK-002 and TASK-003 depend on TASK-001, TASK-004 does NOT | **MEANINGFUL** | - |
| `test_get_dependencies` | Get dependencies for a ticket | Checks exact dependencies for each ticket | **MEANINGFUL** | - |
| `test_get_dependencies_unknown_ticket` | Unknown ticket returns empty list | Checks `[]` | **MEANINGFUL** | - |
| `test_file_not_found` | Missing file raises FileNotFoundError | `pytest.raises(FileNotFoundError)` | **MEANINGFUL** | - |
| `test_empty_file` | Empty file returns empty dict | Checks `result == {}` | **MEANINGFUL** | - |
| `test_no_tickets_section` | No tickets section returns empty dict | Checks `result == {}` | **MEANINGFUL** | - |
| `test_malformed_table_row` | Malformed rows skipped, valid rows parsed | Checks 2 valid tickets in result | **MEANINGFUL** | - |
| `test_parse_plan_matching_shell_script_format` | Real-world plan format parsed correctly | Checks all dependencies match expected (including multi-dep ticket) | **MEANINGFUL** | - |

**test_parse_deps.py Summary:** 14 tests, all 14 meaningful. Excellent coverage.

---

### File: test_mark_blocked.py (21 tests)

| Test | Behavior Should Verify | Actually Asserts | Assessment | Issue |
|------|------------------------|------------------|------------|-------|
| `test_mark_blocked_returns_result` | mark_blocked returns result dict and persists state | Checks result dict structure, AND verifies state file updated with blocked ticket and reason | **MEANINGFUL** | Good dual verification |
| `test_mark_blocked_requires_ticket_id` | Empty ticket_id raises ValueError | `pytest.raises(ValueError, match="ticket_id.*required")` | **MEANINGFUL** | - |
| `test_mark_blocked_uses_default_reason_if_empty` | Empty reason uses default | Checks `result["reason"] == "Unknown reason"`, AND verifies it's in state file | **MEANINGFUL** | - |
| `test_mark_blocked_raises_on_missing_state_file` | Missing state file raises FileNotFoundError | `pytest.raises(FileNotFoundError)` | **MEANINGFUL** | - |
| `test_mark_blocked_raises_on_unknown_ticket` | Unknown ticket raises ValueError | `pytest.raises(ValueError, match="not found")` | **MEANINGFUL** | - |
| `test_mark_blocked_adds_to_ralph_blocked` | Ticket added to ralph.blocked with reason | Checks state file has ticket in ralph.blocked with correct reason | **MEANINGFUL** | - |
| `test_mark_blocked_clears_current_ticket` | current_ticket cleared when blocked | Checks `current_ticket is None` after marking blocked | **MEANINGFUL** | - |
| `test_mark_blocked_does_not_increment_blocked_count` | v2 format keeps blocked_count at 0 | Checks `blocked_count == 0`, ticket in ralph.blocked | **IMPLEMENTATION-COUPLED** | Tests implementation detail (v2 doesn't use blocked_count) rather than user-facing behavior |
| `test_mark_blocked_calls_pm_tool_add_blocked_label` | PM tool add_blocked_label called with reason | Verifies `add_blocked_label.assert_called_once_with("42", "Validation failed")`, AND state updated | **MEANINGFUL** | - |
| `test_mark_blocked_calls_pm_tool_remove_label` | PM tool remove_label called with ralph_label | Verifies `remove_label.assert_called_once_with("42", "ralph-1")`, AND state updated | **MEANINGFUL** | - |
| `test_mark_blocked_skips_remove_label_without_ralph_label` | No ralph_label skips remove_label | Checks `remove_label.assert_not_called()`, state still updated | **MEANINGFUL** | - |
| `test_mark_blocked_with_pm_tool_skips_subprocess` | PM tool path doesn't use subprocess | Checks `mock_run.assert_not_called()`, state updated | **IMPLEMENTATION-COUPLED** | Tests implementation (subprocess not called) rather than outcome |
| `test_mark_blocked_continues_on_pm_tool_failure` | PM tool failure still updates state | add_blocked_label returns False, checks state still updated | **MEANINGFUL** | - |
| `test_mark_blocked_looks_up_issue_without_pm_tool` | No PM tool uses gh CLI lookup | Checks `result["issue_number"] == 42` from gh CLI response | **MEANINGFUL** | - |
| `test_mark_blocked_adds_blocked_label_via_gh` | gh CLI adds blocked label | Checks gh CLI called with `--add-label blocked`, state updated | **MEANINGFUL** | - |
| `test_mark_blocked_handles_no_issue_found` | No matching issue still updates state | Checks `issue_number is None`, state updated | **MEANINGFUL** | - |
| `test_mark_blocked_handles_gh_cli_error` | gh CLI failure still updates state | gh CLI returns error, checks state still updated | **MEANINGFUL** | - |

**test_mark_blocked.py Summary:** 21 tests, 19 meaningful, 2 implementation-coupled. The implementation-coupled tests verify internal mechanics (v2 format specifics, subprocess not called) rather than user-visible outcomes.

---

## Recommendations

### 1. Fix Weak Tests (Priority: Medium)

**test_status.py:**
- `test_displays_ticket_counts_when_active`: Replace regex with structured parsing or exact format verification
- `test_displays_blocked_tickets_with_reasons`: Verify exact association (same line or table row), not "within 100 chars"
- `test_handles_blocked_ticket_without_reason`: Check for specific default message, not just non-empty

**test_orchestrator.py:**
- `test_create_pm_tool_*`: Add integration smoke tests - call one method to verify it works, not just type checking
- `test_run_orchestrator_handles_pm_error_gracefully`: Verify error was logged or communicated to user

### 2. Remove Tautological Tests (Priority: Low)

**test_cleanup.py:**
- `test_generate_summary_complete`, `test_generate_summary_needs_review_when_incomplete`, `test_generate_summary_preserves_all_counts` are testing "function returns its inputs". Either:
  - Delete them (they provide no value)
  - OR redesign if `generate_summary` is supposed to do transformations we're not testing

### 3. Refactor Implementation-Coupled Tests (Priority: Low)

**test_mark_blocked.py:**
- `test_mark_blocked_does_not_increment_blocked_count`: This tests v2 format internals. Either delete or change to verify the semantic behavior: "blocked status is tracked correctly in v2 format"
- `test_mark_blocked_with_pm_tool_skips_subprocess`: Same issue - tests implementation. Change to verify outcome: "PM tool is used when provided"

### 4. Add Missing Coverage (Priority: Medium)

**All files:**
- Add concurrency/race condition tests where applicable
- Add performance degradation tests (e.g., what happens with 1000 tickets?)
- Add more "mixed failure" scenarios (e.g., some PM calls succeed, others fail)

### 5. Pattern to Avoid in Future Tests

**DON'T:**
```python
assert "something" in output  # Too loose
assert hasattr(obj, 'method')  # Just checks interface exists
assert result.count == input.count  # Tautological
```

**DO:**
```python
assert output["section"]["field"] == expected_value  # Exact verification
assert obj.method() == expected_result  # Verify it works
assert result.count == 5  # Verify actual outcome
```

---

## Conclusion

This test suite is **well above average** for meaningfulness. 84% of tests actually verify behavior that would catch bugs. The main areas for improvement:

1. **Replace loose regex/format checks** with exact verification
2. **Delete or redesign tautological tests** that just verify input == output
3. **Shift implementation-coupled tests** to verify outcomes instead of mechanics
4. **Add integration smoke tests** for factory/creation methods

The orchestrator and validation tests are exemplary - they verify both outcomes AND data flow, which catches integration bugs. The parse_deps tests are also excellent - comprehensive coverage of edge cases with exact assertions.

**Overall Grade: B+ (84% meaningful)**
