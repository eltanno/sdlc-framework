# Discovery Phase

You are entering the Discovery phase. This is the first step in our SDLC workflow.

## Purpose

Research and document understanding before planning. This phase ensures we understand the problem space, existing code patterns, and constraints before committing to a solution.

## When Required

- New features
- Significant changes to existing functionality
- Unfamiliar areas of the codebase
- Integration with external systems

## Your Task

Create a discovery document at: `docs/discovery/YYYY-MM-DD-{topic}.md`

Use today's date and a kebab-case topic name.

## Discovery Document Structure

```markdown
# Discovery: {Topic}

**Date:** YYYY-MM-DD
**Status:** DRAFT | APPROVED
**Author:** {name}

## Problem Statement

What problem are we solving? Why does it matter?

## Current State

- How does the system work today?
- What are the pain points?
- What has been tried before?

## Research Findings

### Codebase Analysis

- Relevant files and modules
- Existing patterns we should follow
- Dependencies and constraints

### External Research

- Industry best practices
- Similar implementations
- Relevant documentation

## Key Questions

1. Question that needs answering
2. Another question
3. ...

## Constraints

- Technical constraints
- Business constraints
- Timeline constraints

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | ... | ... |

## Recommendation

Brief recommendation based on findings.

## Next Steps

What should happen after this discovery is approved?
```

## Exit Criteria

- [ ] Document created at correct path
- [ ] All sections completed
- [ ] Key questions identified
- [ ] Risks documented
- [ ] User has reviewed and approved (status = APPROVED)

## Important

Do NOT proceed to planning until the user explicitly approves this discovery document.

---

**Topic for this discovery:** $ARGUMENTS
