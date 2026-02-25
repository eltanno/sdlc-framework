# Release Phase - Orchestrator Instructions

> **⚠️ MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You are the orchestrator. This is a self-executed phase - you update the README and finalize the release.**

---

## ⚡ FIRST ACTION (MANDATORY)

**Before doing ANYTHING else, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.phase = "release"'
```

This updates the statusline to show the current phase. Do this NOW before proceeding.

---

## Purpose

The Release phase closes the loop between planning and execution:
- **Discovery docs** capture what was *planned*
- **README** captures what the software *actually does*

After each iteration, README must be updated to reflect the current state of the product.

## Prerequisites Check

Before proceeding, verify:

1. All tickets from the plan are complete (or explicitly deferred)
2. All PRs have been merged
3. Validation has passed
4. Execution report has been created (`/execution-report`)
5. System review has been completed (`/system-review`)

```bash
# Check git status - should be clean on the default branch
git status
git log --oneline -5

# Check if on the default branch (see git.default_branch in config.yaml)
git branch --show-current
```

If not on the default branch or have uncommitted changes, resolve first.

## Gather Release Information

### 1. Identify the Discovery and PRD

Find the discovery and PRD documents for this iteration:

```bash
# List recent discovery docs
ls -la docs/discovery/

# List recent PRDs
ls -la docs/prds/

# List recent plans
ls -la docs/plans/
```

### 2. Review What Was Shipped

Read the relevant documents to understand what was built:
- Discovery doc for the iteration scope
- PRD for acceptance criteria
- Plan for technical details
- Git log for actual changes

```bash
# See commits since last release/tag
git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD~20)..HEAD
```

## Update README.md

### What to Update

Based on the shipped features, update README.md to include:

1. **New features** - What can users now do?
2. **Changed behaviors** - What works differently?
3. **New configuration options** - New env vars, settings?
4. **Updated prerequisites** - New dependencies?
5. **Version number** - If using semver

### Update Strategy

Read the current README:
```bash
cat README.md
```

Then edit to add/update sections as needed. Focus on:
- Feature descriptions in the appropriate sections
- Updated examples if APIs changed
- New configuration options
- Any breaking changes

### Example Updates

**Adding a new feature:**
```markdown
## Features

- **User Authentication** - Login, registration, session management
- **OAuth Integration** - Sign in with Google or GitHub (NEW)
```

**Updating version:**
```markdown
# My App v1.1.0
```

## Optional: Tag the Release

If the project uses git tags for releases:

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Release v1.1.0: OAuth integration"

# Push tag to remote
git push origin v1.1.0
```

## Commit the README Update

After updating README:

```bash
git add README.md
git commit -m "docs(readme): update for v1.1.0 release

- Add OAuth integration documentation
- Update feature list
- Bump version number

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

## ✅ FINAL ACTION (MANDATORY)

**After README is committed, update the workflow state:**

```bash
.claude/scripts/update-workflow-state.sh '.completed = (.completed + ["release"] | unique)'
```

Do NOT forget this step - it marks the phase as complete in the statusline.

**Optional: Reset for next iteration:**
```bash
.claude/scripts/update-workflow-state.sh '.phase = "idle" | .completed = []'
```

---

## After Release

Suggest next steps to the user:

1. **Start next iteration** - "Ready for the next planning cycle? Run `/discover` to start v1.2"
2. **Execution report** - "Want to document lessons learned? Run `/execution-report`"
3. **System review** - "Want to improve the process? Run `/system-review`"

## Deliverable

Report to user:

```
RELEASE COMPLETE

Version: v1.1.0 (or iteration name)
Branch: [default branch from config.yaml]

## What Was Shipped
- Feature 1: Brief description
- Feature 2: Brief description

## README Updates
- Added: New features section
- Updated: Configuration options
- Changed: Version number

## Git Tag
v1.1.0 (if created)

## Next Steps
- Run `/discover` to start planning the next iteration
- Run `/execution-report` to document this iteration
```

## Arguments

$ARGUMENTS
