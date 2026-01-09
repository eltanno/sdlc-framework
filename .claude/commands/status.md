# Workflow Status

Show the current status of the SDLC workflow for this project.

## Your Task

Analyze the project and report on workflow status.

## Status Check Process

### 1. Check for Artifacts

Search for existing workflow artifacts:

```bash
# Discovery documents
ls -la docs/discovery/*.md 2>/dev/null

# Plans
ls -la docs/plans/*.md 2>/dev/null

# PRDs
ls -la docs/prds/*.md 2>/dev/null

# Active branches
git branch -a 2>/dev/null
```

### 2. Analyze Document Status

For each document found, check:
- Status field (DRAFT vs APPROVED)
- Completion of sections
- Links to related documents

### 3. Check Git Status

```bash
# Current branch
git branch --show-current

# Uncommitted changes
git status --short

# Recent commits
git log --oneline -5
```

### 4. Generate Status Report

## Output Format

```markdown
# SDLC Workflow Status

**Generated:** YYYY-MM-DD HH:MM
**Current Branch:** {branch}

## Active Work

### In Progress
- [ ] {Phase}: {Description} - {Status}

### Pending Review
- [ ] {Document/PR}: Awaiting approval

## Artifacts

### Discovery Documents
| Document | Status | Date |
|----------|--------|------|
| ... | DRAFT/APPROVED | ... |

### Plans
| Document | Status | Date |
|----------|--------|------|
| ... | DRAFT/APPROVED | ... |

### PRDs
| Document | Status | Date | Tickets |
|----------|--------|------|---------|
| ... | DRAFT/APPROVED | ... | TASK-XXX |

## Git Status

- **Branch:** {current branch}
- **Uncommitted Changes:** {yes/no}
- **Ahead/Behind Main:** {status}

## Recommendations

1. Next recommended action
2. Any blockers or issues

## Quick Commands

- Start discovery: `/discover {topic}`
- Create plan: `/plan {feature}`
- Create PRD: `/prd {feature}`
- Check tickets: `/ticket {prd-path}`
- Implement: `/implement TASK-XXX`
- Create PR: `/pr TASK-XXX`
- Validate: `/validate {pr-number}`
```

## What to Look For

### Red Flags
- PRDs without ticket IDs (tickets not created)
- Branches without associated tickets
- DRAFT documents older than a week
- Multiple features in progress simultaneously

### Good Signs
- Clear progression through phases
- All documents have APPROVED status
- Tickets linked in PRDs
- Commits reference ticket IDs

---

Report the current workflow status for this project.
