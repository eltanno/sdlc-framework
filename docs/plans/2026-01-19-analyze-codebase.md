# Implementation Plan: Analyze Codebase Command

**Date:** 2026-01-19
**Status:** APPROVED
**PRD:** [docs/prds/2026-01-19-analyze-codebase.md](../prds/2026-01-19-analyze-codebase.md)
**Discovery:** [docs/discovery/2026-01-19-import-legacy.md](../discovery/2026-01-19-import-legacy.md)
**Author:** Architect Agent

---

## Summary

We are building the `/analyze-codebase` slash command that performs deep, non-destructive analysis of any codebase and produces 8 structured documents in `docs/legacy/`. The command uses the established orchestrator-agent delegation pattern, spawning 7 parallel analysis agents for different dimensions (Stack, Architecture, Structure, Conventions, Testing, Integrations, Concerns), followed by a synthesizer agent that creates the NEXT-STEPS.md document from the combined analysis.

## Goals

### Primary Goals

- Create a fully functional `/analyze-codebase` slash command
- Generate 8 comprehensive, actionable documents in `docs/legacy/`
- Enable parallel agent execution for efficient analysis
- Support language-agnostic analysis (works with any codebase)
- Maintain non-destructive (read-only) operation

### Secondary Goals

- Provide optional clarifying questions to focus analysis
- Ensure documents are self-contained and human-readable
- Make output suitable for SDLC adoption planning

## Non-Goals

*What this plan explicitly does NOT cover.*

- Modifying existing SDLC commands
- CI/CD integration or setup
- Automated code modifications
- Enforcement gates based on analysis
- Integration with project management tools beyond existing capabilities

## Technical Approach

### Architecture Overview

The `/analyze-codebase` command follows the established SDLC pattern where a slash command file provides instructions to the orchestrator, which then delegates to specialist agents.

```
User runs: /analyze-codebase
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (you)                                      │
│                                                          │
│  1. Optional Q&A (interactive)                           │
│     - Purpose of project?                                │
│     - Areas of concern?                                  │
│     - Known pain points?                                 │
│                                                          │
│  2. Create docs/legacy/ directory                        │
│                                                          │
│  3. Spawn 7 Analysis Agents (PARALLEL)                   │
│     ┌─────────┬─────────┬─────────┬─────────┐           │
│     │  Stack  │  Arch   │ Struct  │ Conven  │           │
│     └────┬────┴────┬────┴────┬────┴────┬────┘           │
│     ┌────┴────┬────┴────┬────┴────┐                     │
│     │ Testing │ Integr  │Concerns │                     │
│     └────┬────┴────┬────┴────┬────┘                     │
│          │         │         │                           │
│          ▼         ▼         ▼                           │
│     [7 analysis docs written to docs/legacy/]            │
│                                                          │
│  4. Spawn Synthesizer Agent (SEQUENTIAL - after all 7)   │
│     - Reads all 7 analysis docs                          │
│     - Creates NEXT-STEPS.md                              │
│                                                          │
│  5. Summary to user                                      │
└──────────────────────────────────────────────────────────┘
```

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| `.claude/commands/analyze-codebase.md` | Orchestrator instructions and agent prompts | New |
| `docs/legacy/` | Output directory for analysis documents | New (created at runtime) |

### Key Technical Decisions

#### Decision 1: Single Command File with Embedded Prompts

**Choice:** All 8 agent prompts are embedded within the single command file (`.claude/commands/analyze-codebase.md`)

**Rationale:**
- Follows existing pattern (see `/research.md`, `/discover.md`)
- Keeps everything in one place for easier maintenance
- No need for separate agent definition files
- Command file acts as comprehensive documentation of the feature

**Alternatives Considered:**
- Separate files for each agent prompt - rejected due to fragmentation
- Skill-based approach - rejected as skills are for reusable capabilities, not one-off features

#### Decision 2: Self-Executed Q&A, Delegated Analysis

**Choice:** The orchestrator handles the optional Q&A itself (like `/discover`), then delegates analysis to agents

**Rationale:**
- Q&A is interactive and requires conversation with user
- Analysis is autonomous and benefits from parallel execution
- Matches the pattern: interactive = orchestrator, autonomous = agent

**Alternatives Considered:**
- Delegate Q&A to an agent - rejected as it requires user interaction
- Skip Q&A entirely - rejected as user context significantly improves analysis quality

#### Decision 3: Parallel Agent Execution for Independent Analyses

**Choice:** The 7 analysis agents run in parallel; the synthesizer runs sequentially after all complete

**Rationale:**
- Stack, Architecture, Structure, Conventions, Testing, Integrations, and Concerns are independent analyses
- Parallel execution reduces total time significantly
- NEXT-STEPS.md depends on all 7 analyses, so must run after

**Alternatives Considered:**
- Sequential execution of all 8 - rejected due to poor performance
- Fully parallel including synthesizer - rejected as synthesizer needs all inputs

#### Decision 4: Agent Model Selection

**Choice:** Use `opus` model for all 8 agents (7 analyzers + 1 synthesizer)

**Rationale:**
- Deep analysis requires understanding nuance and patterns
- Synthesizer needs to identify priorities across complex data
- Consistency across all analysis dimensions
- Quality of output is critical for user trust

**Alternatives Considered:**
- Use `sonnet` for simpler analyses - rejected as "deep analysis" is the core requirement
- Mix models based on complexity - rejected for consistency

#### Decision 5: Document Structure Template

**Choice:** Each document follows a consistent structure: Summary, Findings (categorized), Recommendations

**Rationale:**
- Consistency improves user experience
- Self-contained documents can be read independently
- Categories make findings scannable
- Recommendations make findings actionable

**Alternatives Considered:**
- Free-form per document - rejected for inconsistency
- Single consolidated document - rejected per PRD requirement of 8 separate docs

## Implementation Phases

### Phase 1: Command Foundation (Complexity: 3)

**Goal:** Create the command file skeleton with orchestrator instructions and Q&A flow

**Steps:**
1. Create `.claude/commands/analyze-codebase.md` with header and structure
2. Define the optional clarifying questions section
3. Add directory creation instructions (`docs/legacy/`)
4. Add placeholder sections for agent prompts

**Exit Criteria:**
- [ ] Command file exists at `.claude/commands/analyze-codebase.md`
- [ ] Running `/analyze-codebase` triggers the command (recognition works)
- [ ] Q&A flow prompts user with 3 questions
- [ ] User can skip questions with "skip" or similar

### Phase 2: Core Analysis Agents (Complexity: 4)

**Goal:** Implement the 7 analysis agent prompts

**Steps:**
1. Implement Stack Analyzer prompt (languages, frameworks, runtime)
2. Implement Architecture Analyzer prompt (patterns, data flow)
3. Implement Structure Analyzer prompt (directory organization)
4. Implement Conventions Analyzer prompt (code style)
5. Implement Testing Analyzer prompt (frameworks, coverage)
6. Implement Integrations Analyzer prompt (external services)
7. Implement Concerns Analyzer prompt (tech debt, fragile areas)

**Exit Criteria:**
- [ ] All 7 agent prompts are defined in the command file
- [ ] Each prompt includes: objective, analysis areas, output format
- [ ] Prompts receive user context from Q&A (if provided)
- [ ] Parallel execution instructions are clear to orchestrator

### Phase 3: Synthesizer Agent (Complexity: 4)

**Goal:** Implement the NEXT-STEPS.md synthesizer that combines all analyses

**Steps:**
1. Define synthesizer prompt structure
2. Specify how to read and synthesize 7 analysis docs
3. Define prioritization criteria (P1/P2/P3)
4. Add SDLC workflow guidance section template
5. Ensure synthesizer waits for all 7 analyses to complete

**Exit Criteria:**
- [ ] Synthesizer prompt defined in command file
- [ ] Clear instructions for reading 7 input docs
- [ ] Output includes P1/P2/P3 prioritization
- [ ] Output includes "How to Proceed with SDLC" section
- [ ] Sequential execution after parallel phase is enforced

### Phase 4: Integration and Documentation (Complexity: 2)

**Goal:** Complete integration and add documentation

**Steps:**
1. Add command to WORKFLOW.md
2. Add to `/guide` command output
3. Create example output for reference
4. Final review and cleanup

**Exit Criteria:**
- [ ] WORKFLOW.md updated with `/analyze-codebase` documentation
- [ ] `/guide` includes the new command
- [ ] Command file is complete and self-documenting
- [ ] All 8 output documents follow consistent format

## Test Strategy

### Manual Testing (Primary)

Since this is a prompt-engineering feature (no code to unit test), validation is through manual execution:

- [ ] **Test on TypeScript project** - Run on a TypeScript/Node.js codebase, verify all 8 docs generated with relevant content
- [ ] **Test on Python project** - Run on a Python codebase, verify language-specific detection works
- [ ] **Test on Go project** - Run on a Go codebase, verify different ecosystem detected correctly
- [ ] **Test skip Q&A** - Skip all questions, verify analysis still proceeds
- [ ] **Test with context** - Provide answers to Q&A, verify context appears in analysis focus
- [ ] **Test non-destructive** - Run `git status` before/after, verify no source file changes
- [ ] **Test directory creation** - Remove `docs/legacy/`, verify it's created

### Integration Tests

- [ ] **Command recognition** - `/analyze-codebase` is recognized and starts execution
- [ ] **Output completeness** - All 8 files exist after completion
- [ ] **Output quality** - Each document has >10 meaningful items (not boilerplate)
- [ ] **NEXT-STEPS priorities** - P1/P2/P3 sections are populated appropriately

### Acceptance Criteria Verification

Cross-reference against PRD acceptance criteria (FR-1 through FR-13, NFR-1 through NFR-4).

## Tickets

*These will be created after plan approval:*

| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | Create analyze-codebase command skeleton | Create `.claude/commands/analyze-codebase.md` with header, structure, and orchestrator instructions | P1 | 3 | 1 | - |
| 2 | Implement optional Q&A flow | Add interactive clarifying questions section with skip capability | P1 | 2 | 1 | 1 |
| 3 | Implement Stack Analyzer prompt | Define agent prompt for languages, frameworks, runtime analysis → STACK.md | P1 | 3 | 2 | 1 |
| 4 | Implement Architecture Analyzer prompt | Define agent prompt for system patterns, data flow → ARCHITECTURE.md | P1 | 4 | 2 | 1 |
| 5 | Implement Structure Analyzer prompt | Define agent prompt for directory organization → STRUCTURE.md | P1 | 2 | 2 | 1 |
| 6 | Implement Conventions Analyzer prompt | Define agent prompt for code style standards → CONVENTIONS.md | P1 | 3 | 2 | 1 |
| 7 | Implement Testing Analyzer prompt | Define agent prompt for test frameworks, coverage → TESTING.md | P1 | 3 | 2 | 1 |
| 8 | Implement Integrations Analyzer prompt | Define agent prompt for external services, APIs → INTEGRATIONS.md | P1 | 3 | 2 | 1 |
| 9 | Implement Concerns Analyzer prompt | Define agent prompt for tech debt, fragile areas → CONCERNS.md | P1 | 4 | 2 | 1 |
| 10 | Implement Next Steps Synthesizer prompt | Define agent prompt for prioritized improvements → NEXT-STEPS.md | P1 | 4 | 3 | 3-9 |
| 11 | Add command to WORKFLOW.md | Document the new command in workflow reference | P2 | 1 | 4 | 1 |
| 12 | Manual validation on diverse codebases | Test on TypeScript, Python, Go projects | P2 | 3 | 4 | 1-10 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, documentation update | Sonnet |
| 2 | Simple | Basic prompt, minor additions | Sonnet |
| 3 | Moderate | Full agent prompt, structured analysis | Opus |
| 4 | Complex | Complex analysis, synthesis across data | Opus |
| 5 | Very Hard | Architectural decisions, multi-system integration | Opus |

*Current threshold: 1-2 → Sonnet, 3-5 → Opus.*

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Agents produce shallow/generic analysis | Medium | High | Craft detailed prompts with specific exploration instructions; test on real codebases |
| Analysis takes too long (>5 min) | Medium | Medium | Parallel execution; add progress feedback instructions to prompts |
| Output is too technical for stakeholders | Low | Medium | Include jargon explanations in prompts; template includes "why it matters" |
| Language-specific features missed | Medium | Medium | Include language detection in prompts; test on multiple ecosystems |
| One analysis agent fails, blocks others | Low | High | Independent agents continue on failure; partial results saved |
| User context overwhelms agents | Low | Low | Q&A is optional with skip capability; agents can ignore irrelevant context |

## Environment Considerations

### Local Development

- **Primary OS:** Works on any OS with Claude Code CLI
- **Known Limitations:** None - purely prompt-based, no OS-specific code

### CI Environment

- **Platform:** N/A - not applicable for prompt-based command
- **Considerations:** Manual testing only

## Dependencies

### External Dependencies

- None - uses only existing Claude Code capabilities (Glob, Grep, Read, Write, agent delegation)

### Internal Dependencies

- Claude Code CLI with slash command support
- Existing agent delegation pattern from SDLC framework

### Blocking Items

- [ ] None - can proceed immediately after plan approval

## Open Questions

*All questions resolved:*

- [x] How to handle agent failures? → Other agents continue, partial results saved
- [x] What model for agents? → Opus for all (deep analysis requirement)
- [x] Single file or multiple? → Single command file with embedded prompts

## Success Criteria

*How do we know we're done?*

- [ ] `/analyze-codebase` command exists and is recognized
- [ ] Optional Q&A flow works with skip capability
- [ ] All 8 documents generated in `docs/legacy/`
- [ ] Documents contain meaningful, actionable content (not boilerplate)
- [ ] NEXT-STEPS.md has P1/P2/P3 prioritization
- [ ] Works on TypeScript, Python, and Go codebases
- [ ] Non-destructive (no source file changes)
- [ ] WORKFLOW.md updated with new command
- [ ] All PRD acceptance criteria (FR-1 through FR-13) verified

---

## Pre-Implementation Checklist

**CRITICAL: Before delegating ANY implementation work, verify:**

- [ ] Discovery committed: `git log --oneline docs/discovery/`
- [ ] PRD committed: `git log --oneline docs/prds/`
- [ ] This plan committed: `git log --oneline docs/plans/`
- [ ] `git status docs/` shows "nothing to commit"

> **Why this matters:** Untracked files can be lost during branch operations. Documents ARE the state - if they're not committed, implementation has no foundation. See WORKFLOW.md "Artifact Commit Rule" for details.

---

## Post-Implementation Checklist

**After all tickets are complete:**

- [ ] Manual testing on 3+ codebases passed
- [ ] All 8 documents verify quality (>10 meaningful items each)
- [ ] WORKFLOW.md updated
- [ ] Create execution report: `/execution-report`
- [ ] Create system review: `/system-review`

---

## Approval

- [ ] **Approved by:** ________________ on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted.*
