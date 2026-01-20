# Engineer State: SDLC-0063

## Task Summary
- **Ticket:** SDLC-0063
- **Title:** Update /implement slash command - Add Asana task detail fetch
- **Branch:** feature/SDLC-0063-implementation
- **Attempt:** 1

## Implementation Details

### Changes Made

1. **`.claude/ralph/core/asana_pm.py`** - Added `get_task_details()` method
   - Fetches task details from Asana API (name, notes, completion status)
   - Fetches subtasks via separate API call (acceptance criteria)
   - Includes optional fields: tags, dependencies
   - Proper error handling with PMError for not found cases

2. **`.claude/commands/implement.md`** - Added Asana task fetch section
   - Added "Fetch Ticket Details from PM Tool" section
   - Included Python code example using `AsanaPM.get_task_details()`
   - Included REST API curl examples for direct API access
   - Added GitHub alternative (`gh issue view`)
   - Notes importance of including both PM tool details and PRD

3. **`.claude/ralph/tests/unit/test_asana_pm.py`** - Added 8 unit tests
   - `test_get_task_details_returns_task_info`
   - `test_get_task_details_includes_subtasks`
   - `test_get_task_details_handles_no_subtasks`
   - `test_get_task_details_calls_correct_endpoints`
   - `test_get_task_details_raises_error_for_invalid_task`
   - `test_get_task_details_includes_tags`
   - `test_get_task_details_includes_dependencies`
   - `test_get_task_details_method_exists`

### Acceptance Criteria Status

- [x] Given `pm.tool: asana` and a task ID, when `/implement` is run, then task details are fetched via Asana API
- [x] Given task has subtasks (acceptance criteria), when details are fetched, then subtasks are included in context

### Test Results

```
============================= test session starts ==============================
tests/unit/test_asana_pm.py::TestAsanaPMGetTaskDetails - 8 passed
============================= 131 passed in 1.30s ==============================
(Full test suite: 815 passed)
```

### Verification Checklist

- [x] Typecheck: PASS (N/A - framework project)
- [x] Lint: PASS (N/A - framework project)
- [x] Tests: PASS (815 tests, including 8 new tests)
- [x] Build: PASS (N/A - framework project)
- [x] No debug statements in production code
- [x] Commit message references ticket [SDLC-0063]

## Commit Information

- **SHA:** 34e5fe5
- **Message:** feat(asana): add get_task_details method for /implement command [SDLC-0063]
