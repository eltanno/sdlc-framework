# Engineer State: SDLC-0059

## Ticket Info
- **Ticket:** SDLC-0059
- **Title:** Orchestrator factory integration
- **Attempt:** 1 of 3
- **Branch:** feature/SDLC-0059-implementation

## Implementation Summary

Updated `create_pm_tool()` factory in orchestrator to instantiate `AsanaPM` when `pm.tool: asana` is configured.

### Changes Made

1. **`.claude/ralph/commands/orchestrator.py`**
   - Added import for `AsanaPM` from `core.asana_pm`
   - Added `elif pm_tool_type == "asana"` case to `create_pm_tool()` function
   - Updated error message to include "asana" in supported tools list

2. **`.claude/ralph/tests/unit/test_orchestrator.py`**
   - Added `asana_config_yaml` fixture for testing Asana configuration
   - Added `test_create_pm_tool_asana` test verifying AsanaPM instantiation
   - Added `test_create_pm_tool_asana_missing_credentials_raises_auth_error` test

### Acceptance Criteria Verification

From PRD FR-10:
- [x] Given `pm.tool: asana` in config.yaml, when `create_pm_tool()` is called, then `AsanaPM` instance is returned
- [x] Given Asana credentials are missing, when `AsanaPM` is instantiated, then `PMAuthError` is raised with helpful message listing required env vars

### Test Results

```
tests/unit/test_orchestrator.py::TestPMToolIntegration::test_create_pm_tool_asana PASSED
tests/unit/test_orchestrator.py::TestPMToolIntegration::test_create_pm_tool_asana_missing_credentials_raises_auth_error PASSED
```

All 781 tests in the test suite pass.

### TDD Workflow Followed

1. **RED:** Wrote failing tests for AsanaPM factory integration
2. **GREEN:** Implemented factory changes to pass tests
3. **REFACTOR:** No refactoring needed - changes were minimal and clean

## Validation Results

- [x] Tests pass (781/781)
- [x] No new lint errors introduced (existing E402 pattern in codebase)
- [x] Code follows existing patterns

## Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `.claude/ralph/commands/orchestrator.py` | Modified | Added AsanaPM import and factory case |
| `.claude/ralph/tests/unit/test_orchestrator.py` | Modified | Added tests for AsanaPM factory integration |
