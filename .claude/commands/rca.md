# RCA - Root Cause Analysis

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Systematically investigate issues before implementing fixes.**

## Purpose

RCA separates analysis from implementation. Before fixing a bug or issue, you must understand:
- What is actually broken
- Why it's broken
- What the fix should be
- What could go wrong with the fix

**This command creates:** `docs/rca/YYYY-MM-DD-{issue-description}.md`

## When to Use

- Before `/hotfix` for production issues
- Before fixing any non-trivial bug
- When the cause isn't immediately obvious
- When the fix could have side effects

## The RCA Process

### Step 1: Gather Issue Details

If a GitHub/GitLab issue ID is provided:
```bash
gh issue view $ISSUE_ID
# or
glab issue view $ISSUE_ID
```

Collect:
- Issue description and reproduction steps
- Error messages or logs
- User reports or screenshots
- When it started (recent deploy?)

### Step 2: Reproduce the Issue

Before analyzing, confirm the issue:
- Follow the reproduction steps
- Capture actual error messages
- Note the environment (dev, staging, prod)

### Step 3: Search the Codebase

Find relevant code:
```bash
# Search for related code
rg "function_name" --type py
rg "ComponentName" --type tsx

# Check recent changes to affected files
git log --oneline -10 -- path/to/file
git blame path/to/file | grep -A5 -B5 "relevant_line"
```

### Step 4: Identify Root Cause

Analyze:
- What component is failing?
- What's the chain of events leading to failure?
- Is this a regression? What commit introduced it?
- Is there a pattern (timing, data, user action)?

### Step 5: Assess Impact

Determine:
- How many users affected?
- What features are broken?
- Is there a workaround?
- Security implications?

### Step 6: Design the Fix

Propose:
- Specific files to modify
- The fix approach
- Potential side effects
- Testing requirements

## RCA Document Template

Create `docs/rca/YYYY-MM-DD-{issue-slug}.md`:

```markdown
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
```python
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
```python
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
```

## After RCA

Once the RCA document is complete:

1. **Review the proposed fix** - Does it make sense?
2. **Run `/implement-fix`** - Execute the fix following the RCA
3. **Update RCA status** - Mark as IMPLEMENTED then VERIFIED

## Arguments

$ARGUMENTS

If an issue number is provided (e.g., `/rca 123`), fetch issue details automatically.
If a description is provided (e.g., `/rca login failing for SSO users`), use as the issue title.
