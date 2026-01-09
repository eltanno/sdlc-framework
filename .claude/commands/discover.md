# Discovery Phase - Orchestrator Instructions

**You ARE the agent for this phase. This is interactive - do NOT delegate.**

## Purpose

Discovery is a collaborative, interactive session where you help the user articulate their vision. You ask probing questions to understand what they want to build and why.

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
We'll build up docs/discovery.md together as we go.

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
4. **Update** docs/discovery.md incrementally

Example flow:
```
User: "I want to build a task management app"

You: "Got it - a task management app. Let me understand more:

- Who will use this? Just you, a team, or public?
- What's missing from existing tools that you need?

[Updating discovery.md with initial vision...]"
```

## The Discovery Document

Maintain `docs/discovery.md` as a living document:

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

**Incrementally update** docs/discovery.md as the conversation progresses:
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

The full discovery is in docs/discovery.md

**Ready for next steps?**
- Review and refine: "Let's revisit [section]"
- Mark complete: "Discovery looks good"
- Continue later: "Save progress"

When you're happy with discovery, run `/plan` to create the technical plan.
```

## Resuming Discovery

If the user runs `/discover` and docs/discovery.md exists:

```
## Resuming Discovery

I found an existing discovery document (last updated: YYYY-MM-DD).

Would you like to:
1. **Continue** where we left off
2. **Revise** a specific section
3. **Start fresh** (will archive current version)

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

## Topic/Context for Discovery

$ARGUMENTS
