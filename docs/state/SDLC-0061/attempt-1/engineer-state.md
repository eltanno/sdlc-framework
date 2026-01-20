# Engineer State: SDLC-0061

**Ticket:** SDLC-0061 - Update /hotfix slash command
**Branch:** feature/SDLC-0061-implementation
**Attempt:** 1 of 3
**Status:** PASSED

---

## Changes Made

### File Modified

- `.claude/commands/hotfix.md` - Complete rewrite to support configurable PM tools

### Changes Summary

1. **Added Step 1: Read PM Tool Configuration**
   - Reads `pm.tool` from `config.yaml`
   - Routes to appropriate implementation based on value

2. **Added Step 2A: Asana Direct API Path**
   - Uses `AsanaPM` class for task creation
   - Creates task with `[HOTFIX]` prefix
   - Generates task URL for reference

3. **Added Step 2B: GitHub CLI Path**
   - Uses `gh issue create` for issue creation
   - Creates issue with `[HOTFIX]` prefix
   - Applies `task` label

4. **Added Step 2C: Trello MCP Path**
   - Uses Trello MCP for card creation
   - Creates card with `[HOTFIX]` prefix

5. **Added Step 2D: Local-only Fallback**
   - Handles `pm.tool: none` with warning
   - Proceeds without external tracking

6. **Updated Step 4: PM Ticket Update**
   - Separate sections for Asana, GitHub, and Trello
   - Adds PR link as comment on resolution

7. **Updated Step 6: Post-Merge Ticket Closure**
   - Separate sections for each PM tool
   - Includes follow-up tech-debt task creation

8. **Removed All MCP References**
   - Replaced `mcp__asana__*` calls with direct API usage
   - No more references to non-existent Asana MCP

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Given `pm.tool: asana`, task created via Asana REST API | PASS | Step 2A uses `AsanaPM.create_task()` |
| Given `pm.tool: github`, issue created via gh CLI | PASS | Step 2B uses `gh issue create` |
| Hotfix title format is `[HOTFIX] {description}` | PASS | All title examples use `[HOTFIX]` prefix |
| PR link added to task description on resolution | PASS | Step 4 adds comment with PR link |

---

## Validation Results

- **Typecheck:** N/A (framework project - markdown only)
- **Lint:** N/A (framework project - markdown only)
- **Tests:** N/A (framework project - no automated tests)
- **Build:** N/A (framework project - no build step)

All validation checks passed (project has no traditional checks).

---

## Commit Information

- **SHA:** d0c60d3
- **Message:** `feat(hotfix): make PM tool configurable via config.yaml [SDLC-0061]`
- **Files:** 1 file changed, 264 insertions(+), 58 deletions(-)
