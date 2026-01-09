# Research Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `general-purpose` agent.**

## Purpose

Autonomous research on a topic - web research, codebase exploration, technical investigation. The agent works independently and returns findings.

This is different from `/discover` which is interactive requirements gathering.

## When to Use

- Technical research on unfamiliar topics
- Exploring existing codebase patterns
- Investigating third-party libraries/APIs
- Competitive analysis
- Best practices research

## Prerequisites Check

Before delegating, verify:
- User has provided a topic to research
- This is research (autonomous) not discovery (interactive)

## Delegation

```
Task({
  subagent_type: "general-purpose",
  model: "sonnet",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the agent:

---

**RESEARCHER AGENT TASK: Technical Research**

## Context

Topic to research: $ARGUMENTS
Project location: /home/jim/workspace/test-sdlc-project

## Objective

Research this topic and return comprehensive findings. Work autonomously - gather information, analyze, synthesize, and report back.

## Your Research Tasks

1. **If this involves existing codebase:**
   - Explore relevant files and modules
   - Identify existing patterns to follow
   - Document dependencies and constraints

2. **If this involves external research:**
   - Search for industry best practices
   - Find relevant documentation
   - Identify similar implementations
   - Compare alternatives

3. **Synthesize findings:**
   - Key facts and insights
   - Pros/cons of different approaches
   - Recommendations with rationale
   - Open questions remaining

## Deliverable

Create a research document at: `docs/research/{todays-date}-{topic-kebab-case}.md`

Structure:
```markdown
# Research: {Topic}

**Date:** YYYY-MM-DD
**Researcher:** Agent

## Summary

[2-3 sentence overview of findings]

## Key Findings

### Finding 1
Details...

### Finding 2
Details...

## Recommendations

1. Recommendation with rationale
2. Another recommendation

## Sources

- Source 1
- Source 2

## Open Questions

- Question that needs further investigation
```

## Output Format

After creating the document, return:

```
RESEARCH COMPLETE

Document: docs/research/YYYY-MM-DD-topic.md

Summary: [2-3 sentence summary of findings]

Key Findings:
- Finding 1
- Finding 2
- Finding 3

Recommendation: [1 sentence top recommendation]

Open Questions:
- Question 1
- Question 2
```

---

## After Agent Returns

1. **Verify** the research document was created
2. **Summarize** findings for user
3. **Identify** how this informs the current work
4. **Suggest** next steps based on findings

## Topic for Research

$ARGUMENTS
