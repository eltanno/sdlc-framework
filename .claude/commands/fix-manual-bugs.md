---
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Task, mcp__playwright__*
description: Read the manual test bug report with annotated screenshots and fix all reported issues
---

You are processing a manual test bug report from the user. The report contains annotated screenshots and text descriptions of issues found during manual testing.

## Step 1: Read the Report

1. Read `docs/todo/manual-test/report.md` for the text descriptions
2. Read ALL image files in `docs/todo/manual-test/` (PNG, JPG, etc.) — you are multimodal and can see annotations (circles, arrows, highlights)
3. For each bug entry, match the screenshot filename to the section in report.md

## Step 2: Triage

For each reported issue:
1. Understand what's wrong (from the screenshot + description)
2. Identify the likely file(s) involved
3. Categorize severity: Critical, Major, Moderate, Low
4. Add it to `docs/todo/playtest-bugs.md` with the next sequential BUG-XXX ID

## Step 3: Fix (Delegate to Engineer)

Launch a SINGLE `engineer` subagent to fix all reported issues. Include:
- The full content of the manual test report
- Description of each screenshot (what you saw in the image)
- The relevant file paths you identified
- Instructions to run tests after fixing

## Step 4: Verify

After the engineer returns:
1. Run `npm test --workspace=frontend` and `npm test --workspace=backend` to confirm no regressions
2. If the app needs visual verification, start servers and use Playwright to check the fixes
3. Update `docs/todo/playtest-bugs.md` with fix status
4. Update `docs/todo/manual-test/report.md` — add a "FIXED" note to each resolved item

## Important Notes

- READ EVERY IMAGE FILE — the annotations are the most important part
- The user annotates with circles, arrows, and text to highlight exactly what's wrong
- Match screenshot numbers to report.md sections
- Preserve the manual test report as a record (don't delete it)
- If a bug is unclear, ask the user before fixing
