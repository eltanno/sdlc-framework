# Discovery: Legacy Project Import Feature

**Last Updated:** 2026-01-19
**Status:** APPROVED
**Revisions:** 1

---

## Vision

### What We're Building
A `/import-legacy` slash command that analyzes existing brownfield codebases and creates a structured import plan, enabling legacy projects to use the SDLC workflow for future feature development.

### Problem Statement
The current SDLC workflow assumes greenfield projects. Teams with existing codebases cannot easily adopt the workflow - there's no process for:
- Understanding what already exists
- Identifying gaps (tests, linting, documentation)
- Creating a roadmap to bring the project into SDLC compliance

### Target Users
- Developers wanting to adopt SDLC on existing projects
- Teams inheriting legacy codebases
- [Pending clarification on primary persona]

### Success Criteria
- `/analyze-codebase` command exists and is documented
- Running command produces all 8 documents in `docs/legacy/`
- Analysis is deep enough to enable actionable improvement planning
- NEXT-STEPS.md provides clear, prioritized path to SDLC readiness
- User can proceed to `/discover` for improvements after analysis

---

## User Experience

### Core User Journey
1. User copies SDLC framework files into existing project
2. User runs `/analyze-codebase`
3. Command asks optional clarifying questions:
   - "What's the main purpose of this project?"
   - "Any specific areas of concern or focus?"
   - "Known pain points or technical debt?"
   - (User can skip any/all with "not sure" or similar)
4. Command performs deep codebase analysis via parallel agents
5. Command produces 7 analysis documents in `docs/legacy/`
6. Command produces `NEXT-STEPS.md` with prioritized improvements
7. User reviews output and uses `/discover` to plan improvements
8. Once baseline met, user proceeds with normal SDLC workflow for new features

### Key Interactions
- **Optional Q&A** - Focus the analysis if user has context, skip if not
- **Deep analysis** - Thorough examination for meaningful, actionable output
- **8 documents generated** - 7 analysis docs + 1 improvement plan
- **Clear next steps** - Prioritized path to SDLC readiness

---

## Scope

### Analysis Areas (Proposed)
- [ ] Language/framework detection
- [ ] Project structure (monolith, microservices, etc.)
- [ ] Testing coverage (unit tests, e2e tests)
- [ ] Linting/formatting configuration
- [ ] Code style conventions
- [ ] Build system
- [ ] CI/CD presence
- [ ] Documentation state
- [ ] Dependency management

### In Scope (v1)
- `/analyze-codebase` slash command
- 7 analysis documents in `docs/legacy/`
- Improvement plan with recommended next steps
- Guidance on how to proceed with SDLC workflow

### Out of Scope
- Modifying existing SDLC commands
- Enforcing gates/prerequisites based on analysis
- Automated code modifications
- CI/CD setup

### Must Have vs Nice to Have
| Must Have | Nice to Have |
|-----------|--------------|
| 7 analysis documents | Parallel agent execution |
| Improvement plan with next steps | Progress indicators during analysis |
| Command name: `/analyze-codebase` | Integration with project management tools |
| Non-destructive (read-only) | Severity ratings on concerns |

---

## Technical Context

### Integrations
- Existing SDLC slash commands
- Codebase exploration tools (Glob, Grep, Read)
- Agent delegation for analysis

### Constraints
- Must work with ANY language/framework (very broad scope)
- Cannot assume anything about project structure
- Must be non-destructive (analyze only, don't modify)

### Data
- Input: Existing codebase files
- Output location: `docs/legacy/`
  - `docs/legacy/STACK.md` - Languages, frameworks, runtime
  - `docs/legacy/ARCHITECTURE.md` - System patterns, data flow
  - `docs/legacy/STRUCTURE.md` - Directory organization
  - `docs/legacy/CONVENTIONS.md` - Code style standards
  - `docs/legacy/TESTING.md` - Test frameworks, coverage
  - `docs/legacy/INTEGRATIONS.md` - External services, APIs
  - `docs/legacy/CONCERNS.md` - Technical debt, fragile areas
  - `docs/legacy/NEXT-STEPS.md` - Improvement plan and workflow guidance

### NEXT-STEPS.md Structure

```markdown
# Next Steps for SDLC Integration

## Current State Summary
[1-paragraph synthesis of the 7 analysis docs - what is this project,
what shape is it in, what are the main gaps]

## Recommended Improvements

### Priority 1: Critical (blocks effective SDLC development)
- [ ] Item (why it matters, what to do)
- [ ] Item

### Priority 2: Important (significantly improves workflow)
- [ ] Item
- [ ] Item

### Priority 3: Nice to Have (polish and best practices)
- [ ] Item
- [ ] Item

## How to Proceed with SDLC

1. **Address Priority 1 items first**
   - Use `/discover` to plan each improvement as a feature
   - Follow normal `/prd` → `/plan` → `/implement` cycle

2. **Establish baseline**
   - Once Priority 1 complete, project is "SDLC ready"
   - Priority 2/3 can be addressed as time permits

3. **Reference legacy docs during planning**
   - `docs/legacy/*.md` provide context for any future work
   - Agents will use these to understand existing patterns

4. **Proceed with new features**
   - Use `/discover` for new feature development
   - Legacy analysis ensures consistency with existing code
```

---

## Open Questions

- [x] ~~What constitutes "SDLC compliant"?~~ → Advisory only, no enforcement
- [x] ~~Should this modify the codebase?~~ → No, read-only analysis
- [x] ~~Output structure?~~ → 7 docs + NEXT-STEPS.md in `docs/legacy/`
- [x] ~~Command name?~~ → `/analyze-codebase`
- [x] ~~How deep should the analysis go?~~ → Deep analysis for meaningful, actionable output
- [x] ~~Interactive questions before analysis?~~ → Yes, but skip if user doesn't know
- [x] ~~What should NEXT-STEPS.md contain?~~ → Prioritized improvements + SDLC workflow guidance

---

## Risks & Assumptions

### Assumptions
- Project is a software codebase (not documents/configs only)
- User has filesystem access to the project
- Project is in a single directory/repo

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Infinite variety of legacy projects | May miss important patterns | Focus on common patterns, allow manual additions |
| Analysis takes too long | Poor UX | Chunk analysis, show progress |
| Over-prescriptive plans | Users reject recommendations | Make plans actionable suggestions, not mandates |

---

## Research: GSD Pattern Analysis

**Source:** https://github.com/onewithdev/gsd

GSD uses a `/gsd:map-codebase` command that:
- Spawns parallel agents for different analysis dimensions
- Produces 7 structured documents in `.planning/codebase/`
- Auto-loads these during planning for context

### GSD's Seven Dimensions
| Document | Purpose |
|----------|---------|
| `STACK.md` | Languages, frameworks, runtime |
| `ARCHITECTURE.md` | System patterns, data flow |
| `STRUCTURE.md` | Directory organization |
| `CONVENTIONS.md` | Code style standards |
| `TESTING.md` | Test frameworks, coverage |
| `INTEGRATIONS.md` | External services, APIs |
| `CONCERNS.md` | Technical debt, fragile areas |

### Key Insight
GSD separates "understanding" from "planning improvements". The mapping phase just documents what exists - it doesn't prescribe changes.

### Design Decisions Needed
1. Adopt 7-doc structure or consolidate?
2. Just document, or also create improvement plan?
3. How to integrate with existing SDLC workflow?
4. Command naming preference?

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-19 | Initial discovery session |
| 2026-01-19 | Added GSD research, decided on 7+1 doc structure |
| 2026-01-19 | Finalized command name, analysis depth, interactivity |
| 2026-01-19 | Defined NEXT-STEPS.md structure |
