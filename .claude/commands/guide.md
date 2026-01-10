# Guide - SDLC Framework Help

**Help users understand the workflow and find their next step.**

## Purpose

This command helps engineers who are new to Claude Code or this SDLC framework. It provides friendly, non-overwhelming guidance based on where they are.

## When Someone Runs /guide

Respond with a conversational, helpful explanation. Adapt based on context.

---

## Your Response

### Start with Orientation

```markdown
## Welcome to the SDLC Framework

This framework helps you build features using a structured workflow with AI assistance.
Think of it as pair programming where Claude handles much of the implementation work,
but you stay in control of decisions.

**You don't need to know AI or Claude Code** - just know your usual software development
workflow. This builds on that.
```

### Explain the Core Workflow

```markdown
## The Workflow (Simple Version)

```
Discover → PRD → Plan → Tickets → Implement → PR → Validate
```

| Phase | What Happens | Your Role |
|-------|--------------|-----------|
| **Discover** | Define what you're building | Have a conversation about requirements |
| **PRD** | Claude writes formal requirements | Review and approve |
| **Plan** | Claude designs the technical approach | Review and approve |
| **Tickets** | Creates tasks in your PM tool | Verify they look right |
| **Implement** | Claude writes code using TDD | Review commits |
| **PR** | Creates a pull request | Review and merge |
| **Validate** | Runs final checks | Approve for merge |

**Key insight:** You make decisions, Claude does the heavy lifting.
```

### Show Common Commands

```markdown
## Commands You'll Use

| Command | When to Use |
|---------|-------------|
| `/discover` | Starting a new feature - "I want to build X" |
| `/whats-next` | "What should I do now?" - checks your current state |
| `/status` | Quick view of where things stand |
| `/implement TICKET-ID` | Work on a specific ticket |
| `/guide` | You're here! Get help anytime |

**Pro tip:** You can also just describe what you want in plain English.
Claude will figure out the right command.
```

### Detect Current State (Optional)

If you can quickly check the state, add contextual guidance:

```markdown
## Where You Are Now

[Based on checking docs/ and git status]

- **Discovery:** [exists/missing]
- **Active PRD:** [name or none]
- **Active Plan:** [name or none]
- **Current Branch:** [branch name]

**Suggested next step:** [specific recommendation]
```

### Point to Resources

```markdown
## Learn More

- `WORKFLOW.md` - Detailed workflow documentation
- `docs/guides/` - Specific how-to guides
- `/whats-next` - Find your exact next action

**Stuck on something specific?** Just ask! Describe your problem in plain English.
```

---

## Tone Guidelines

- **Friendly, not formal** - "You're in good shape" not "Status: nominal"
- **Encouraging** - They're learning something new
- **Concise** - Don't overwhelm with every detail
- **Practical** - Focus on what they can do right now
- **No jargon** - Avoid Claude/AI terminology unless necessary

## What NOT to Do

- Don't dump the entire WORKFLOW.md on them
- Don't assume they know Claude Code commands
- Don't use technical AI terms (tokens, context, agents)
- Don't make them feel bad for needing help

## If They Ask Follow-Up Questions

Answer specifically. If they ask about a phase, explain just that phase.
If they're confused about something, address that one thing.

## Arguments

$ARGUMENTS

If they provide context (e.g., `/guide implement` or `/guide prd`), focus your explanation on that specific topic.
