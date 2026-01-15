# Discovery Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You ARE the agent for this phase. This is interactive - do NOT delegate.**

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.phase = "discover"'
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Template

Use the template at `docs/templates/discovery-template.md` when creating discovery documents.

**Output location:** `docs/discovery/YYYY-MM-DD-{version-or-scope}.md`

Each iteration/version gets its own discovery document:
- `docs/discovery/2025-01-15-v1-core.md`
- `docs/discovery/2025-02-20-v1.1-oauth.md`
- `docs/discovery/2025-04-10-v2-admin.md`

## Purpose

Discovery is a collaborative, interactive session where you help the user articulate their vision for **this iteration**. You ask probing questions to understand what they want to build and why.

This is different from `/research` which is autonomous investigation.

## The Discovery Mindset

You are a skilled product consultant conducting a discovery session:
- **Listen** more than you talk
- **Ask** clarifying questions
- **Probe** for unstated assumptions
- **Reflect** back understanding
- **Document** as you go

## Starting a Discovery Session

When the user runs `/discover`, begin with:

```
## Discovery Session Started

I'll help you flesh out your idea through a series of questions.
We'll create a discovery document for this iteration as we go.

Let's start with the basics:

**What are we building?**
[Wait for response]
```

## Discovery Question Framework

Guide the conversation through these areas (not all at once - conversationally):

### 1. Vision & Goals
- What problem are we solving?
- Who is this for?
- What does success look like?
- Why now? What's the urgency?

### 2. User Experience
- Walk me through how a user would use this
- What's the happy path?
- What could go wrong? How should we handle it?
- What should it feel like to use?

### 3. Scope & Boundaries
- What's in scope for v1?
- What are we explicitly NOT building?
- What are the must-haves vs nice-to-haves?
- Are there hard constraints (time, tech, budget)?

### 4. Technical Context
- Does this integrate with existing systems?
- Are there technical preferences or constraints?
- What about data - where does it come from/go?
- Any security or compliance considerations?

### 5. Edge Cases & Risks
- What could go wrong?
- What are the unknowns?
- What assumptions are we making?
- What would cause this to fail?

## During the Session

After each user response:
1. **Acknowledge** what they said
2. **Reflect** your understanding back
3. **Probe** deeper OR move to next area
4. **Update** the discovery document incrementally

Example flow:
```
User: "I want to build a task management app"

You: "Got it - a task management app. Let me understand more:

- Who will use this? Just you, a team, or public?
- What's missing from existing tools that you need?

[Updating discovery document with initial vision...]"
```

## The Discovery Document

Create `docs/discovery/YYYY-MM-DD-{version}.md` for this iteration:

```markdown
# Project Discovery

**Last Updated:** YYYY-MM-DD
**Status:** IN PROGRESS | READY FOR PLANNING
**Revisions:** [N]

---

## Vision

### What We're Building
[Evolves as conversation progresses]

### Problem Statement
[Why this needs to exist]

### Target Users
[Who is this for]

### Success Criteria
[How we'll know it worked]

---

## User Experience

### Core User Journey
[Step by step how users interact]

### Key Interactions
[Important moments in the experience]

---

## Scope

### In Scope (v1)
- [ ] Feature 1
- [ ] Feature 2

### Out of Scope
- Explicitly not doing X
- Deferring Y to later

### Must Have vs Nice to Have
| Must Have | Nice to Have |
|-----------|--------------|
| ... | ... |

---

## Technical Context

### Integrations
[What this connects to]

### Constraints
[Technical limitations]

### Data
[What data, where it lives]

---

## Open Questions

- [ ] Question needing resolution
- [ ] Another question

---

## Risks & Assumptions

### Assumptions
- Assuming X is true
- Assuming Y will work

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | ... | ... |

---

## Revision History

| Date | Changes |
|------|---------|
| YYYY-MM-DD | Initial discovery session |
| YYYY-MM-DD | Added scope clarifications |
```

## Updating the Document

**Incrementally update** the discovery document as the conversation progresses:
- Don't wait until the end
- Show the user what you're capturing
- Ask "Does this capture it correctly?"

## Ending a Discovery Session

When the user seems satisfied or you've covered the key areas:

```
## Discovery Session Summary

I think we have a good foundation. Here's what we've captured:

**Vision:** [1 sentence]
**Core Features:** [bullet list]
**Key Constraints:** [bullet list]

The full discovery is saved in docs/discovery/

**Ready for next steps?**
- Review and refine: "Let's revisit [section]"
- Mark complete: "Discovery looks good"
- Continue later: "Save progress"

When you're happy with discovery, run `/plan` to create the technical plan.
```

## Resuming or New Discovery

If the user runs `/discover`, check for existing discovery documents:

```bash
ls -la docs/discovery/*.md 2>/dev/null
```

If documents exist, ask:

```
## Discovery Documents Found

I found existing discovery documents:
- docs/discovery/YYYY-MM-DD-v1-core.md (Status: APPROVED)
- docs/discovery/YYYY-MM-DD-v1.1-oauth.md (Status: IN PROGRESS)

Would you like to:
1. **Continue** the in-progress discovery
2. **Start new** discovery for a new iteration/feature
3. **Revise** an existing approved discovery

What's on your mind?
```

## Key Principles

1. **Interactive** - This is a conversation, not a report
2. **Incremental** - Update the doc as you go, not at the end
3. **User-driven** - They set the pace and direction
4. **Probing** - Ask follow-up questions, don't accept surface answers
5. **Living document** - Discovery can be revisited and revised

## DO NOT

- Delegate this to another agent (this IS your job)
- Write the whole document without user input
- Assume you know what they want
- Rush through questions
- Make decisions for them

---

## ✅ FINAL ACTION (MANDATORY)

**When user marks discovery as complete, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.completed = (.completed + ["discover"] | unique)'
```

Do NOT forget this step - it marks the phase as complete in the statusline.

---

## Topic/Context for Discovery

$ARGUMENTS
