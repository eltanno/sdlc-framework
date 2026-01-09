# Discovery Phase - Orchestrator Instructions

**You are the orchestrator. Delegate this to the `researcher` agent.**

## Prerequisites Check

Before delegating, verify:
- User has provided a topic to research
- No duplicate discovery document exists for this topic

## Delegation

```
Task({
  subagent_type: "researcher",
  model: "sonnet",
  prompt: <see Agent Prompt below>
})
```

## Agent Prompt

Construct this prompt for the researcher agent:

---

**RESEARCHER AGENT TASK: Discovery Research**

## Context

Topic to research: $ARGUMENTS
Project location: /home/jim/workspace/test-sdlc-project
Template location: docs/templates/discovery-template.md

## Objective

Research and document understanding of the topic before planning begins. Create a comprehensive discovery document.

## Your Research Tasks

1. **If this involves existing codebase:**
   - Explore relevant files and modules
   - Identify existing patterns to follow
   - Document dependencies and constraints

2. **If this involves external research:**
   - Search for industry best practices
   - Find relevant documentation
   - Identify similar implementations

3. **For all discoveries:**
   - Document current state / problem
   - Identify key questions that need answers
   - List constraints (technical, business, timeline)
   - Assess risks with mitigations
   - Make a recommendation

## Deliverable

Create a discovery document at: `docs/discovery/{todays-date}-{topic-kebab-case}.md`

Use the template at `docs/templates/discovery-template.md` as your structure.

**Required sections:**
- Problem Statement
- Current State
- Research Findings
- Key Questions
- Constraints
- Risks
- Recommendation
- Next Steps

Set status to DRAFT (user will approve).

## Output Format

After creating the document, return:

```
DISCOVERY COMPLETE

Document: docs/discovery/YYYY-MM-DD-topic.md
Status: DRAFT (awaiting approval)

Summary: [2-3 sentence summary of findings]

Key Findings:
- Finding 1
- Finding 2
- Finding 3

Recommendation: [1 sentence recommendation]

Next: User should review and approve, then run /plan
```

---

## After Agent Returns

1. **Verify** the discovery document was created
2. **Summarize** findings for user
3. **Prompt** user to review and approve (change status to APPROVED)
4. **Next step:** Once approved, user can run `/plan`

## Topic for Discovery

$ARGUMENTS
