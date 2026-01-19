# PRD: Analyze Codebase Command

**Date:** 2026-01-19
**Status:** APPROVED
**Discovery:** [docs/discovery/2026-01-19-import-legacy.md](../discovery/2026-01-19-import-legacy.md)
**Plan:** [docs/plans/2026-01-19-analyze-codebase.md](../plans/2026-01-19-analyze-codebase.md)
**Owner:** Architect Agent
**Stakeholders:** Development teams, Legacy project maintainers

---

## Discovery Reference

**Note:** This PRD is for ONE feature: the `/analyze-codebase` slash command within the Legacy Project Import iteration.

**Iteration Vision:**
Create a `/analyze-codebase` slash command that analyzes existing brownfield codebases and creates structured documentation, enabling legacy projects to adopt the SDLC workflow for future feature development.

**How This Feature Fits:**
The `/analyze-codebase` command is the primary deliverable of this iteration. It enables teams with existing codebases to understand what they have before planning improvements. This command produces comprehensive documentation that serves as the foundation for all subsequent SDLC work on legacy projects.

---

## Executive Summary

### Problem Statement

The current SDLC workflow assumes greenfield projects. Teams with existing codebases cannot easily adopt the workflow because there's no process for:
- Understanding what already exists (stack, architecture, conventions)
- Identifying gaps (tests, linting, documentation)
- Creating a roadmap to bring the project into SDLC compatibility

### Solution Summary

Create a `/analyze-codebase` slash command that performs deep, non-destructive analysis of any codebase and produces 8 structured documents in `docs/legacy/`. The command optionally gathers user context via clarifying questions, then spawns parallel analysis agents to examine different dimensions of the codebase. The final output includes a prioritized improvement plan guiding users through SDLC adoption.

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Command exists and documented | N/A | Yes | Command file exists in `.claude/commands/` |
| All 8 documents generated | N/A | 100% | File count in `docs/legacy/` after run |
| Documents contain actionable content | N/A | Yes | Manual review: each doc has >10 meaningful items |
| NEXT-STEPS.md has prioritized items | N/A | Yes | Manual review: P1/P2/P3 sections populated |
| Works on diverse codebases | N/A | 3+ languages | Test on TypeScript, Python, Go projects |

---

## Requirements

### Functional Requirements

#### FR-1: Slash Command Registration

**Priority:** P1 (Must Have)

**Description:** The system must register `/analyze-codebase` as a valid slash command that can be invoked from the Claude Code CLI.

**Acceptance Criteria:**
- [ ] Given the SDLC framework is installed, when user types `/analyze-codebase`, then the command is recognized and begins execution
- [ ] Given the command file exists at `.claude/commands/analyze-codebase.md`, when Claude Code loads commands, then `/analyze-codebase` appears in the available commands
- [ ] Given the user runs `/help` or `/guide`, when viewing available commands, then `/analyze-codebase` is listed with a brief description

#### FR-2: Optional Clarifying Questions

**Priority:** P1 (Must Have)

**Description:** Before analysis begins, the command should ask optional clarifying questions to focus the analysis. Users can skip any or all questions.

**Acceptance Criteria:**
- [ ] Given the command starts, when prompting the user, then these questions are asked: (1) "What's the main purpose of this project?", (2) "Any specific areas of concern or focus?", (3) "Known pain points or technical debt?"
- [ ] Given a user responds "not sure", "skip", or similar to any question, when proceeding, then the analysis continues without that context
- [ ] Given a user provides answers, when analysis runs, then those answers are passed to analysis agents as additional context
- [ ] Given a user wants to skip all questions, when they indicate this, then analysis begins immediately without Q&A

#### FR-3: Stack Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/STACK.md` documenting languages, frameworks, and runtime environment.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/STACK.md` exists
- [ ] Given a TypeScript project, when analyzing stack, then the document identifies TypeScript version, Node.js runtime, and major frameworks (React, Express, etc.)
- [ ] Given a Python project, when analyzing stack, then the document identifies Python version and major packages from requirements.txt/pyproject.toml
- [ ] Given a multi-language project, when analyzing stack, then all primary languages are identified with their relative proportion
- [ ] Given the stack analysis, when reviewing output, then build tools (webpack, vite, esbuild, etc.) are identified if present

#### FR-4: Architecture Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/ARCHITECTURE.md` documenting system patterns and data flow.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/ARCHITECTURE.md` exists
- [ ] Given a web application, when analyzing architecture, then the document identifies frontend/backend separation if present
- [ ] Given database files or ORM usage, when analyzing architecture, then data layer patterns are documented
- [ ] Given API routes or endpoints, when analyzing architecture, then API structure is documented
- [ ] Given service files or modules, when analyzing architecture, then the document describes inter-component communication patterns

#### FR-5: Structure Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/STRUCTURE.md` documenting directory organization.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/STRUCTURE.md` exists
- [ ] Given the project root, when analyzing structure, then top-level directories are listed with their purposes
- [ ] Given source code directories, when analyzing structure, then the organization pattern is identified (feature-based, layer-based, etc.)
- [ ] Given configuration files at root, when analyzing structure, then their purposes are documented
- [ ] Given the structure analysis, when reviewing output, then entry points are clearly identified

#### FR-6: Conventions Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/CONVENTIONS.md` documenting code style standards.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/CONVENTIONS.md` exists
- [ ] Given ESLint/Prettier/other linter configs, when analyzing conventions, then configured rules are documented
- [ ] Given code samples across the project, when analyzing conventions, then naming patterns are identified (camelCase, snake_case, etc.)
- [ ] Given the codebase, when analyzing conventions, then file naming conventions are documented
- [ ] Given import statements, when analyzing conventions, then import organization style is documented

#### FR-7: Testing Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/TESTING.md` documenting test frameworks, patterns, and coverage.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/TESTING.md` exists
- [ ] Given test files exist, when analyzing testing, then test framework(s) are identified (Jest, pytest, go test, etc.)
- [ ] Given test directories, when analyzing testing, then test organization is documented (co-located, separate __tests__, etc.)
- [ ] Given the codebase, when analyzing testing, then approximate test coverage areas are identified (what's tested vs untested)
- [ ] Given no tests exist, when analyzing testing, then the document explicitly states "No tests found" and recommends establishing testing

#### FR-8: Integrations Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/INTEGRATIONS.md` documenting external services and APIs.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/INTEGRATIONS.md` exists
- [ ] Given API calls in code, when analyzing integrations, then external services are listed with their purposes
- [ ] Given environment variables, when analyzing integrations, then expected external dependencies are documented (databases, caches, etc.)
- [ ] Given package dependencies, when analyzing integrations, then third-party service SDKs are identified (AWS, Stripe, etc.)
- [ ] Given no external integrations, when analyzing, then the document states "No external integrations detected"

#### FR-9: Concerns Analysis Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/CONCERNS.md` documenting technical debt and fragile areas.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/CONCERNS.md` exists
- [ ] Given large files (>500 lines), when analyzing concerns, then they are flagged as potential complexity issues
- [ ] Given TODO/FIXME/HACK comments, when analyzing concerns, then they are collected and categorized
- [ ] Given circular dependencies or tight coupling patterns, when analyzing concerns, then they are documented
- [ ] Given outdated dependencies, when analyzing concerns, then security/maintenance risks are noted
- [ ] Given user-provided pain points (from FR-2), when analyzing concerns, then those areas receive focused attention

#### FR-10: Next Steps Document

**Priority:** P1 (Must Have)

**Description:** Generate `docs/legacy/NEXT-STEPS.md` with prioritized improvements and SDLC workflow guidance.

**Acceptance Criteria:**
- [ ] Given any codebase, when analysis completes, then `docs/legacy/NEXT-STEPS.md` exists
- [ ] Given the 7 analysis documents, when generating next steps, then a 1-paragraph synthesis summarizes the project state
- [ ] Given identified gaps, when generating next steps, then improvements are categorized as Priority 1 (Critical), Priority 2 (Important), or Priority 3 (Nice to Have)
- [ ] Given Priority 1 items, when generating next steps, then each item explains why it matters and what to do
- [ ] Given the document, when reviewing output, then a "How to Proceed with SDLC" section exists with clear steps
- [ ] Given the SDLC workflow, when generating guidance, then the document references `/discover` as the entry point for improvements

#### FR-11: Non-Destructive Operation

**Priority:** P1 (Must Have)

**Description:** The command must be strictly read-only and never modify existing codebase files.

**Acceptance Criteria:**
- [ ] Given any codebase, when running `/analyze-codebase`, then no files outside `docs/legacy/` are created or modified
- [ ] Given existing source files, when analysis runs, then `git status` shows no changes to source files
- [ ] Given the analysis completes, when checking git diff, then only `docs/legacy/*.md` files are new/modified

#### FR-12: Parallel Agent Execution

**Priority:** P2 (Should Have)

**Description:** Analysis should spawn multiple agents working in parallel to reduce total analysis time.

**Acceptance Criteria:**
- [ ] Given the analysis begins, when spawning agents, then multiple analysis dimensions run concurrently where possible
- [ ] Given independent analysis tasks (STACK, CONVENTIONS, TESTING), when executing, then they do not wait for each other
- [ ] Given dependent tasks (NEXT-STEPS depends on other analyses), when executing, then proper sequencing is maintained

#### FR-13: Output Directory Creation

**Priority:** P1 (Must Have)

**Description:** The command must create the `docs/legacy/` directory if it doesn't exist.

**Acceptance Criteria:**
- [ ] Given `docs/legacy/` does not exist, when analysis completes, then the directory is created
- [ ] Given `docs/` does not exist, when analysis completes, then both `docs/` and `docs/legacy/` are created
- [ ] Given `docs/legacy/` already exists with files, when analysis runs, then existing files are overwritten with new analysis

### Non-Functional Requirements

#### NFR-1: Performance

- Analysis should complete within 5 minutes for codebases up to 10,000 files
- Progress feedback should be shown at least every 30 seconds during analysis
- Agent spawning should not block the main process

#### NFR-2: Reliability

- If one analysis agent fails, others should continue
- Partial results should be saved even if some analyses fail
- Clear error messages should indicate which analysis failed and why

#### NFR-3: Compatibility

- Must work with any programming language (language-agnostic detection)
- Must handle monorepos with multiple projects
- Must handle projects without standard structure (no assumptions about file layout)

#### NFR-4: Usability

- Output documents should be human-readable Markdown
- Technical jargon should be explained or avoided
- Each document should be self-contained (readable without others)

---

## User Stories

### US-1: Legacy Project Onboarding

**Story:** As a developer inheriting a legacy codebase, I want to quickly understand its structure and patterns so that I can make changes safely.

**Acceptance Criteria:**
- [ ] Running `/analyze-codebase` produces comprehensive documentation within 5 minutes
- [ ] The ARCHITECTURE.md document explains how data flows through the system
- [ ] The CONVENTIONS.md document tells me how to write code that fits the existing style
- [ ] The CONCERNS.md document warns me about fragile areas before I touch them

**Notes:** This is the primary use case - a developer new to a codebase needs to get up to speed quickly.

### US-2: SDLC Adoption Planning

**Story:** As a team lead, I want to understand what gaps exist in a legacy project so that I can plan the work needed to adopt SDLC practices.

**Acceptance Criteria:**
- [ ] NEXT-STEPS.md clearly identifies what's missing for effective SDLC usage
- [ ] Priorities (P1/P2/P3) help me sequence improvement work
- [ ] The document explains how to use `/discover` to plan each improvement
- [ ] I can estimate effort based on the identified gaps

**Notes:** This enables planning adoption sprints for legacy projects.

### US-3: Technical Debt Assessment

**Story:** As a technical lead, I want an automated assessment of technical debt so that I can justify remediation work to stakeholders.

**Acceptance Criteria:**
- [ ] CONCERNS.md provides objective evidence of technical debt (file sizes, TODO counts, etc.)
- [ ] Issues are categorized by severity
- [ ] The analysis can be re-run to track improvement over time
- [ ] Output is suitable for sharing with non-technical stakeholders

**Notes:** The analysis serves as documentation for technical debt discussions.

### US-4: Focus Analysis with Context

**Story:** As a developer with specific concerns about a codebase, I want to provide context before analysis so that the output focuses on my areas of concern.

**Acceptance Criteria:**
- [ ] Clarifying questions let me share what I know about the project
- [ ] My answers influence what the analysis prioritizes
- [ ] Pain points I mention get special attention in CONCERNS.md
- [ ] I can skip questions if I don't have useful context

**Notes:** The optional Q&A makes analysis more relevant to the user's actual needs.

---

## Technical Specifications

### New Files to Create

| File | Purpose |
|------|---------|
| `.claude/commands/analyze-codebase.md` | Slash command definition and orchestrator instructions |

### Agent Architecture

The command uses a delegation pattern where the orchestrator spawns analysis agents:

```
/analyze-codebase (orchestrator)
    │
    ├── [Optional Q&A with user]
    │
    ├── Spawn Analysis Agents (parallel where possible)
    │   ├── Stack Analyzer → STACK.md
    │   ├── Architecture Analyzer → ARCHITECTURE.md
    │   ├── Structure Analyzer → STRUCTURE.md
    │   ├── Conventions Analyzer → CONVENTIONS.md
    │   ├── Testing Analyzer → TESTING.md
    │   ├── Integrations Analyzer → INTEGRATIONS.md
    │   └── Concerns Analyzer → CONCERNS.md
    │
    └── Synthesis Agent (after all analyses complete)
        └── NEXT-STEPS.md
```

### Agent Prompt Templates

Each analysis agent receives a prompt with:
1. The specific analysis dimension to focus on
2. User context from clarifying questions (if provided)
3. Project directory path
4. Output file path
5. Expected document structure

### Output Directory Structure

```
docs/
└── legacy/
    ├── STACK.md
    ├── ARCHITECTURE.md
    ├── STRUCTURE.md
    ├── CONVENTIONS.md
    ├── TESTING.md
    ├── INTEGRATIONS.md
    ├── CONCERNS.md
    └── NEXT-STEPS.md
```

### Document Templates

Each generated document follows a consistent structure:

```markdown
# {Analysis Area}

**Generated:** YYYY-MM-DD
**Project:** {project name from package.json/pyproject.toml or directory name}

## Summary

[2-3 sentence overview]

## Findings

### {Category 1}
- Finding with details

### {Category 2}
- Finding with details

## Recommendations

- Recommendation 1
- Recommendation 2

---
*Generated by `/analyze-codebase`*
```

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| None | N/A | Uses existing SDLC framework tools only |

The command uses only existing capabilities:
- `Glob` for file discovery
- `Grep` for pattern searching
- `Read` for file content analysis
- `Write` for document creation
- Agent delegation for parallel analysis

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| [AUCT-0185](https://github.com/eltanno/sdlc-framework/issues/1) | Create analyze-codebase command file | Create `.claude/commands/analyze-codebase.md` with orchestrator instructions and agent delegation logic | P1 | 4 | - |
| [AUCT-0186](https://github.com/eltanno/sdlc-framework/issues/2) | Implement Stack Analyzer agent prompt | Define the agent prompt for analyzing languages, frameworks, and runtime | P1 | 3 | AUCT-0185 |
| [AUCT-0187](https://github.com/eltanno/sdlc-framework/issues/3) | Implement Architecture Analyzer agent prompt | Define the agent prompt for analyzing system patterns and data flow | P1 | 4 | AUCT-0185 |
| [AUCT-0188](https://github.com/eltanno/sdlc-framework/issues/4) | Implement Structure Analyzer agent prompt | Define the agent prompt for analyzing directory organization | P1 | 2 | AUCT-0185 |
| [AUCT-0189](https://github.com/eltanno/sdlc-framework/issues/5) | Implement Conventions Analyzer agent prompt | Define the agent prompt for analyzing code style standards | P1 | 3 | AUCT-0185 |
| [AUCT-0190](https://github.com/eltanno/sdlc-framework/issues/6) | Implement Testing Analyzer agent prompt | Define the agent prompt for analyzing test frameworks and coverage | P1 | 3 | AUCT-0185 |
| [AUCT-0191](https://github.com/eltanno/sdlc-framework/issues/7) | Implement Integrations Analyzer agent prompt | Define the agent prompt for analyzing external services and APIs | P1 | 3 | AUCT-0185 |
| [AUCT-0192](https://github.com/eltanno/sdlc-framework/issues/8) | Implement Concerns Analyzer agent prompt | Define the agent prompt for analyzing technical debt and fragile areas | P1 | 4 | AUCT-0185 |
| [AUCT-0193](https://github.com/eltanno/sdlc-framework/issues/9) | Implement Next Steps Synthesizer agent prompt | Define the agent prompt for generating prioritized improvements from all analyses | P1 | 4 | AUCT-0186 to AUCT-0192 |
| [AUCT-0194](https://github.com/eltanno/sdlc-framework/issues/10) | Implement optional clarifying questions flow | Add interactive Q&A before analysis with skip capability | P1 | 2 | AUCT-0185 |
| [AUCT-0195](https://github.com/eltanno/sdlc-framework/issues/11) | Add command to WORKFLOW.md documentation | Document the new command in workflow reference | P2 | 1 | AUCT-0185 |
| [AUCT-0196](https://github.com/eltanno/sdlc-framework/issues/12) | Create integration tests | Test command on sample TypeScript, Python, and Go projects | P2 | 3 | AUCT-0185 to AUCT-0194 |

*Note: IDs will be filled in after ticket creation via `/ticket`.*

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Model |
|-------|-------|-------|
| 1 | Trivial | Sonnet |
| 2 | Simple | Sonnet |
| 3 | Moderate | Opus |
| 4 | Complex | Opus |
| 5 | Very Hard | Opus |

---

## Testing Requirements

### Test Cases

| ID | Requirement | Description | Steps | Expected Result |
|----|-------------|-------------|-------|-----------------|
| TC-1 | FR-1 | Command recognition | 1. Run `/analyze-codebase` | Command starts without error |
| TC-2 | FR-2 | Skip all questions | 1. Run command<br>2. Answer "skip" to all questions | Analysis proceeds without context |
| TC-3 | FR-2 | Provide context | 1. Run command<br>2. Answer all questions | Context appears in agent prompts |
| TC-4 | FR-3 to FR-9 | Documents created | 1. Run on TypeScript project<br>2. Check `docs/legacy/` | All 7 analysis files exist |
| TC-5 | FR-10 | Next Steps created | 1. Run analysis<br>2. Check NEXT-STEPS.md | File exists with P1/P2/P3 sections |
| TC-6 | FR-11 | Non-destructive | 1. Run `git status`<br>2. Run analysis<br>3. Run `git status` | Only `docs/legacy/` files changed |
| TC-7 | FR-13 | Directory creation | 1. Remove `docs/legacy/`<br>2. Run analysis | Directory created with all files |
| TC-8 | NFR-3 | Python project | 1. Run on Python codebase | Correct Python-specific analysis |
| TC-9 | NFR-3 | Go project | 1. Run on Go codebase | Correct Go-specific analysis |
| TC-10 | US-1 | Useful for onboarding | 1. Run on unfamiliar codebase<br>2. Review output | Can understand codebase from docs alone |

### Test Coverage Requirements

- Manual testing on 3+ different language codebases
- Verification of all 8 output documents
- Validation that documents are useful for SDLC adoption planning

---

## Rollout Plan

### Phase 1: Internal Testing

- Implement all tickets
- Test on this SDLC project itself (`/analyze-codebase` on test-sdlc-project)
- Fix issues found during self-analysis

### Phase 2: Diverse Codebase Testing

- Test on TypeScript/React project
- Test on Python/FastAPI project
- Test on Go project
- Document any language-specific issues

### Phase 3: Documentation and Release

- Add to WORKFLOW.md
- Add to `/guide` command output
- Update README with new capability
- Create example output for reference

---

## Rollback Plan

### Triggers

This is a new command with no existing functionality to break. Rollback is simply removing the command file.

### Process

1. Delete `.claude/commands/analyze-codebase.md`
2. Remove any documentation references
3. Document reason for removal

---

## Open Questions

All questions resolved during discovery:

- [x] Command name? -> `/analyze-codebase`
- [x] Output location? -> `docs/legacy/`
- [x] Interactive questions? -> Yes, optional
- [x] Analysis depth? -> Deep (meaningful, actionable)
- [x] Modify codebase? -> No (read-only)

---

## Out of Scope

*Explicitly list what this PRD does NOT cover:*

- Modifying existing SDLC commands (no changes to `/discover`, `/prd`, etc.)
- Enforcing gates or prerequisites based on analysis results
- Automated code modifications or fixes
- CI/CD setup or configuration
- Project migration tools
- Integration with project management tools (beyond what SDLC already supports)

---

## Approval

- [ ] **Product Approved by:** ________________ on YYYY-MM-DD
- [ ] **Engineering Approved by:** ________________ on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
