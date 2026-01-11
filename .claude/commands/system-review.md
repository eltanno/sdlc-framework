# System Review - Process Meta-Analysis

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**Analyze process effectiveness, not code quality.**

## Purpose

System review looks for bugs in the *process*, not bugs in the *code*. After completing a feature, analyze:

- Did the workflow work well?
- Where did plans fail to predict reality?
- What should change in our SDLC commands/docs?

**Key Principle:** "You're not looking for bugs in the code - you're looking for bugs in the process."

**This command creates:** `docs/system-reviews/YYYY-MM-DD-{feature-name}.md`

## When to Use

- After completing a significant feature (post `/execution-report`)
- After a hotfix that revealed process gaps
- Periodically to review multiple recent implementations
- When the team feels the process isn't working

## What to Analyze

### The Four Artifacts

1. **The Plan** (`docs/plans/YYYY-MM-DD-*.md`)
   - Was it detailed enough?
   - Were tasks atomic and clear?
   - Did it anticipate edge cases?

2. **The Execution Report** (`docs/execution-reports/YYYY-MM-DD-*.md`)
   - What divergences occurred?
   - What challenges were unexpected?
   - What took longer than expected?

3. **The PRD** (`docs/prds/YYYY-MM-DD-*.md`)
   - Were requirements clear?
   - Did scope creep occur?
   - Were acceptance criteria testable?

4. **The Commands Used**
   - Did `/plan`, `/implement`, `/validate` work well?
   - Were there gaps in the workflow?
   - Did agents have enough context?

## System Review Process

### Step 1: Gather Artifacts

Read:
- The plan that was followed
- The execution report
- The PRD (if applicable)
- Git history for the feature branch

### Step 2: Classify Divergences

For each divergence in the execution report:

**Good Divergences** (Process should allow these):
- Plan had incorrect assumptions
- Better pattern emerged during implementation
- Optimization opportunity discovered
- Requirement clarified during work

**Bad Divergences** (Process should prevent these):
- Ignored constraints from plan
- Created inconsistent architecture
- Misunderstood requirements
- Skipped validation steps

### Step 3: Trace Root Causes

For each bad divergence, identify the root cause:

| Root Cause Category | Example |
|---------------------|---------|
| Unclear Planning | Plan said "add auth" without specifying method |
| Missing Context | Plan didn't reference existing auth patterns |
| Absent Validation | No step to verify against requirements |
| Missing Gotchas | Common pitfall not documented |
| Tool Gap | Needed capability not in workflow |

### Step 4: Generate Improvements

Create specific, actionable recommendations:

- **CLAUDE.md updates** - New conventions to document
- **Command updates** - Changes to `/plan`, `/implement`, etc.
- **Template updates** - Better plan/PRD templates
- **New automation** - Hooks or validations to add
- **Reference docs** - Best practices to document

## System Review Template

Create `docs/system-reviews/YYYY-MM-DD-{feature-slug}.md`:

```markdown
# System Review: {Feature Name}

**Date:** YYYY-MM-DD
**Feature:** {feature name}
**Reviewer:** {who}

---

## Artifacts Analyzed

| Artifact | Path | Status |
|----------|------|--------|
| PRD | `docs/prds/...` | Reviewed |
| Plan | `docs/plans/...` | Reviewed |
| Execution Report | `docs/execution-reports/...` | Reviewed |
| Commits | `feature/...` branch | Reviewed |

---

## Overall Assessment

**Alignment Score:** [1-10]

[Brief narrative: How well did execution match plan? How smooth was the process?]

---

## Divergence Analysis

### Good Divergences (Keep/Encourage)

| Divergence | Why It Was Good | Learning |
|------------|-----------------|----------|
| [What changed] | [Why this was better] | [What to carry forward] |

### Bad Divergences (Prevent in Future)

| Divergence | Root Cause | Prevention |
|------------|------------|------------|
| [What went wrong] | [Why it happened] | [How to prevent] |

---

## Root Cause Analysis

### Planning Phase Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| [Problem in planning] | [What it caused] | [How to improve] |

### Execution Phase Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| [Problem during implementation] | [What it caused] | [How to improve] |

### Validation Phase Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| [Problem in validation] | [What it caused] | [How to improve] |

---

## Pattern Compliance

| Pattern | Expected | Actual | Gap |
|---------|----------|--------|-----|
| Test coverage | 80% | [X]% | [+/-] |
| Commit granularity | Atomic | [assessment] | [gap] |
| Documentation | Updated | [status] | [gap] |
| Code style | Per CLAUDE.md | [assessment] | [gap] |

---

## Recommendations

### Immediate Actions

#### Update CLAUDE.md
```markdown
[Specific text to add/change]
```

#### Update Command: `/plan`
[What to change and why]

#### Update Command: `/implement`
[What to change and why]

#### Update Templates
[What to change and why]

### Future Considerations

- [ ] [Longer-term improvement 1]
- [ ] [Longer-term improvement 2]

### New Gotchas to Document

| Technology | Gotcha | Where to Document |
|------------|--------|-------------------|
| [Tech] | [Pitfall] | [File] |

---

## Key Learnings

1. **[Learning 1]:** [Explanation and action]
2. **[Learning 2]:** [Explanation and action]
3. **[Learning 3]:** [Explanation and action]

---

## Process Health Metrics

| Metric | This Feature | Trend |
|--------|--------------|-------|
| Plan Accuracy | [%] | [up/down/stable] |
| Unexpected Blockers | [count] | [up/down/stable] |
| Rework Required | [low/med/high] | [up/down/stable] |
| Time Estimate Accuracy | [%] | [up/down/stable] |

---

## Follow-up Tasks

- [ ] Apply CLAUDE.md updates
- [ ] Update affected commands
- [ ] Add new gotchas to reference docs
- [ ] Share learnings with team
```

## After System Review

1. **Apply recommendations** - Update CLAUDE.md, commands, templates
2. **Track improvements** - Note what was changed
3. **Share learnings** - If on a team, communicate findings

## DO NOT

- Focus on code quality (that's `/code-review`)
- Blame individuals
- Ignore patterns across multiple reviews
- Skip this step after significant features

## Workflow State Update

At the **start** of this phase, update `workflow-state.json`:

```bash
.claude/scripts/update-workflow-state.sh '.phase = "review"'
```

At the **end** of this phase (after review is created), mark complete and reset for next feature:

```bash
# Mark review complete
.claude/scripts/update-workflow-state.sh '.completed = (.completed + ["review"] | unique)'

# Reset for next feature cycle (optional - keeps history or resets)
# To reset: .claude/scripts/update-workflow-state.sh '.phase = "idle" | .completed = [] | .ralph = {"current": 0, "total": 0, "current_ticket": null, "tickets_done": []}'
```

## Arguments

$ARGUMENTS

If a feature name is provided, use it to find the relevant execution report.
If no arguments, prompt for the feature or list recent execution reports to choose from.
