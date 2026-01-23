# Concerns Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of technical debt state - include overall health assessment and most critical finding]

## Findings

### Code Complexity

**Large Files (>500 lines):**
| File | Lines | Why Concerning | Recommendation |
|------|-------|----------------|----------------|
| [file path] | [count] | [what makes it complex] | [suggested action] |

**Complex Functions/Methods:**
| Location | Lines | Issue | Risk |
|----------|-------|-------|------|
| [file:function] | [count] | [deep nesting/many params/etc] | [High/Medium] |

**Complexity Summary:**
- Total large files: [count]
- Total complex functions: [count]
- Hotspot areas: [directories or modules with most complexity]

### Technical Debt Markers

**Overview:**
| Marker Type | Count | Severity | Oldest |
|-------------|-------|----------|--------|
| TODO | [count] | Low | [date if determinable or "Unknown"] |
| FIXME | [count] | Medium | [date if determinable] |
| HACK | [count] | High | [date if determinable] |
| XXX | [count] | Medium | [date if determinable] |
| DEPRECATED | [count] | Medium | [date if determinable] |

**Critical Items (FIXME, HACK, BUG):**
| Location | Type | Content | Age |
|----------|------|---------|-----|
| [file:line] | [FIXME/HACK] | [content] | [if determinable] |

**TODOs by Category:**
| Category | Count | Examples |
|----------|-------|----------|
| [feature/bug/refactor/etc] | [count] | [sample items] |

**Notable Debt Patterns:**
- [Pattern observed]: [description and locations]

### Dependency Health

**Dependency Age Summary:**
| Status | Count | Examples |
|--------|-------|----------|
| Up to date | [count] | [packages] |
| Minor update available | [count] | [packages] |
| Major update available | [count] | [packages with versions] |
| Deprecated | [count] | [packages] |

**Outdated Dependencies:**
| Package | Current | Latest | Versions Behind | Risk |
|---------|---------|--------|-----------------|------|
| [package] | [current] | [latest] | [major.minor.patch] | [Low/Medium/High] |

**Security Concerns:**
| Package | Issue | Severity | Advisory |
|---------|-------|----------|----------|
| [package or "None detected"] | [vulnerability] | [Critical/High/Medium/Low] | [CVE or link if known] |

**Unused Dependencies:**
| Package | Evidence |
|---------|----------|
| [package or "None detected"] | [no imports found / 0 references] |

**Dependency Health Score:** [Good/Fair/Poor]

### Code Smells

**Magic Numbers/Strings:**
| Location | Value | Suggested Fix |
|----------|-------|---------------|
| [file:line] | [value] | [extract to constant] |

**Debug/Console Statements:**
| Location | Statement | Should Be |
|----------|-----------|-----------|
| [file:line] | [statement] | [removed/logger] |

**Dead/Commented Code:**
| Location | Lines | Description |
|----------|-------|-------------|
| [file:line-range] | [count] | [what the code appears to be] |

**Empty Error Handling:**
| Location | Pattern | Risk |
|----------|---------|------|
| [file:line] | [empty catch/except] | [what could go wrong] |

**Duplicate Code Patterns:**
| Pattern | Locations | Lines | Suggestion |
|---------|-----------|-------|------------|
| [description] | [files] | [total duplicated lines] | [extract to shared utility] |

### Architectural Concerns

**Circular Dependencies:**
| Cycle | Files Involved | Impact |
|-------|----------------|--------|
| [cycle # or "None detected"] | [A → B → A] | [what breaks if changed] |

**God Classes/Modules:**
| File | Lines | Methods | Responsibilities |
|------|-------|---------|------------------|
| [file or "None detected"] | [count] | [count] | [what it does - too much] |

**Tight Coupling:**
| Module | Coupled To | Import Count | Concern |
|--------|------------|--------------|---------|
| [module] | [dependency] | [how many files import it] | [why concerning] |

**Missing Abstractions:**
| Pattern | Locations | Suggestion |
|---------|-----------|------------|
| [repeated pattern] | [where found] | [interface/class to extract] |

### Security Concerns

| Concern | Severity | Location | Description |
|---------|----------|----------|-------------|
| [type or "None detected"] | [Critical/High/Medium/Low] | [file:line] | [what the issue is] |

**Note:** This is a surface-level scan. For comprehensive security analysis, use dedicated security scanning tools.

### User-Reported Pain Points

[If user provided pain points in Q&A, analyze those specifically]

| Pain Point | Findings | Validation |
|------------|----------|------------|
| [user-reported issue] | [what was found] | [confirmed/partially confirmed/not found] |

**Analysis:**
- [Detailed findings for each user-reported pain point]

## Priority Assessment

### Critical (P1) - Address Immediately
Issues that pose security risks, cause production problems, or block development.

| Issue | Location | Impact | Effort |
|-------|----------|--------|--------|
| [issue] | [where] | [what could happen] | [Low/Medium/High] |

### Important (P2) - Address Soon
Issues that significantly impact maintainability or developer productivity.

| Issue | Location | Impact | Effort |
|-------|----------|--------|--------|
| [issue] | [where] | [why it matters] | [Low/Medium/High] |

### Nice to Have (P3) - When Time Permits
Issues that improve code quality but aren't urgent.

| Issue | Location | Impact | Effort |
|-------|----------|--------|--------|
| [issue] | [where] | [benefit of fixing] | [Low/Medium/High] |

## Technical Debt Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Large files (>500 lines) | [count] | [Good <5 / Fair 5-15 / Poor >15] |
| Technical debt markers | [total count] | [Good <20 / Fair 20-50 / Poor >50] |
| Outdated dependencies | [count] | [Good 0 / Fair 1-5 / Poor >5 major] |
| Circular dependencies | [count] | [Good 0 / Fair 1-2 / Poor >2] |
| Security concerns | [count] | [Good 0 / Poor >0] |

**Overall Technical Debt Level:** [Low / Medium / High]

**Debt Trend Indicators:**
- [Observations about whether debt is growing or being managed]

## Recommendations

### Immediate Actions
1. [Most critical action with specific steps]
2. [Second most critical]
3. [Third most critical]

### Short-term Improvements (1-2 sprints)
- [Improvement]: [why and how]

### Long-term Refactoring
- [Larger refactoring effort]: [scope and benefit]

### Process Improvements
- [Process change to prevent future debt]: [recommendation]

---
*Generated by `/analyze-codebase`*
