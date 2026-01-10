# RCA: {Issue Title}

**Date:** YYYY-MM-DD
**Issue:** #{issue-number} or description
**Severity:** Critical | High | Medium | Low
**Status:** ANALYZING | FIX PROPOSED | IMPLEMENTED | VERIFIED

---

## Issue Summary

**Reported By:** [who]
**First Reported:** [when]
**Environment:** [dev/staging/prod]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Reproduction Steps
1. Step one
2. Step two
3. Observe error

---

## Investigation

### Affected Components
- `path/to/file.py` - [what role it plays]
- `path/to/other.ts` - [what role it plays]

### Timeline
- [date] - Feature X deployed
- [date] - First report of issue
- [date] - Pattern identified

### Root Cause
[Clear explanation of WHY this is happening]

### Code Analysis
```
# The problematic code
def broken_function():
    # This fails because...
```

---

## Impact Assessment

| Aspect | Assessment |
|--------|------------|
| Users Affected | [number/percentage] |
| Features Broken | [list] |
| Data Impact | [any data corruption?] |
| Security Risk | [yes/no - details] |
| Workaround | [exists/none] |

---

## Proposed Fix

### Approach
[Description of the fix strategy]

### Files to Modify
1. `path/to/file.py`
   - Change: [what to change]
   - Reason: [why this fixes it]

2. `path/to/other.ts`
   - Change: [what to change]
   - Reason: [why this fixes it]

### Code Changes
```
# The fixed code
def fixed_function():
    # Now correctly handles...
```

### Risks of This Fix
- [Potential side effect 1]
- [Potential side effect 2]

### Alternative Approaches
| Approach | Pros | Cons |
|----------|------|------|
| [Alt 1] | ... | ... |
| [Alt 2] | ... | ... |

---

## Testing Requirements

### Unit Tests
- [ ] Test case 1: [description]
- [ ] Test case 2: [description]

### Integration Tests
- [ ] Test scenario: [description]

### Manual Verification
1. [Step to verify fix]
2. [Another verification step]

### Regression Check
- [ ] Feature X still works
- [ ] Feature Y unaffected

---

## Validation Commands

```bash
# Run after fix to validate
pytest tests/test_affected_module.py -v
npm run test -- --grep "affected component"
```

---

## Resolution

**Fix Implemented:** [date or pending]
**Verified By:** [who]
**Deployed To:** [environment]

### Lessons Learned
- [What we learned]
- [How to prevent similar issues]

### Follow-up Items
- [ ] Add monitoring for X
- [ ] Update documentation for Y
