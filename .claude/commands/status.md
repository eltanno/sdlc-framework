# Workflow Status - Orchestrator Direct Task

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. This is a coordination task - do it yourself.**

Status checking is lightweight - just read files and report. No delegation needed.

## Status Check Process

### 1. Check Artifact Directories

```bash
# Discovery documents
echo "=== Discovery ==="
ls -la docs/discovery/*.md 2>/dev/null || echo "No discovery docs"

# Plans
echo "=== Plans ==="
ls -la docs/plans/*.md 2>/dev/null || echo "No plans"

# PRDs
echo "=== PRDs ==="
ls -la docs/prds/*.md 2>/dev/null || echo "No PRDs"
```

### 2. Check Document Statuses

```bash
# Find DRAFT documents (need attention)
echo "=== DRAFT (pending approval) ==="
grep -l "Status: DRAFT" docs/**/*.md 2>/dev/null || echo "None"

# Find APPROVED documents
echo "=== APPROVED ==="
grep -l "Status: APPROVED" docs/**/*.md 2>/dev/null || echo "None"
```

### 3. Check Git Status

```bash
# Current branch
echo "=== Git Status ==="
git branch --show-current

# Uncommitted changes
git status --short

# Recent commits
git log --oneline -5 2>/dev/null || echo "No commits yet"

# Open PRs/MRs (check repo.type in config.yaml)
REPO_TYPE=$(grep -E "^\s*type:" config.yaml 2>/dev/null | grep -E "github|gitlab" | awk '{print $2}' || echo "github")
if [ "$REPO_TYPE" = "gitlab" ]; then
  glab mr list 2>/dev/null || echo "No GitLab remote"
else
  gh pr list 2>/dev/null || echo "No GitHub remote"
fi
```

### 4. Check for Active Work

Look for:
- Feature branches (indicates in-progress implementation)
- DRAFT documents (need approval)
- Open PRs (need review/merge)

## Output Format

Generate this status report:

```markdown
# SDLC Workflow Status

**Generated:** YYYY-MM-DD HH:MM
**Project:** test-sdlc-project

## Current State

**Active Phase:** [Discovery / Planning / PRD / Implementation / PR / Validation / None]
**Current Branch:** [branch name]

## Documents

### Discovery
| Document | Status | Date |
|----------|--------|------|
| topic.md | DRAFT/APPROVED | YYYY-MM-DD |

### Plans
| Document | Status | Date |
|----------|--------|------|
| feature.md | DRAFT/APPROVED | YYYY-MM-DD |

### PRDs
| Document | Status | Tickets |
|----------|--------|---------|
| feature.md | DRAFT/APPROVED | TASK-XXX, TASK-YYY |

## Git

- **Branch:** [default branch] / feature/TASK-XXX-desc
- **Uncommitted Changes:** Yes/No
- **Open PRs:** [list or none]

## Workflow Progress

```
[x] Discovery  → document.md (APPROVED)
[x] Plan       → plan.md (APPROVED)
[x] PRD        → prd.md (APPROVED)
[x] Tickets    → TASK-123, TASK-124
[ ] Implement  → in progress on feature branch
[ ] PR         → not started
[ ] Validate   → not started
```

## Recommendations

1. Next action based on current state
2. Any blockers or issues
3. Suggested command to run

## Quick Commands

| Action | Command |
|--------|---------|
| Start discovery | `/discover {topic}` |
| Create plan | `/plan {feature}` |
| Create PRD | `/prd {feature}` |
| Create tickets | `/ticket` |
| Implement | `/implement TASK-XXX` |
| Create PR | `/pr TASK-XXX` |
| Validate | `/validate` |
```

## What to Watch For

### Red Flags
- DRAFT documents older than a week
- Feature branches without PRs
- PRDs without ticket IDs
- Multiple features in progress

### Good Signs
- Clear linear progression through phases
- All documents approved before moving on
- Tickets linked in PRDs
- Commits reference ticket IDs
