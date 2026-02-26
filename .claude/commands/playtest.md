---
allowed-tools: Bash(*), mcp__playwright__*, Read, Write, Edit, Glob, Grep
description: Start the app and run a full Playwright playtest as a new user and returning user
---

You are a QA tester performing a comprehensive playtest of the application using Playwright browser automation.

## STEP 0: Understand the Project

Read `docs/SYSTEM.md` to understand:
- What this application does and who it's for
- The architecture, key user flows, and pages
- Known issues and fragile areas
- API routes and frontend routes

Read `CLAUDE.md` for:
- How to start/stop the dev environment
- Project structure

This context tells you what to test and what to expect.

## Setup

1. **Check if servers are already running** — try navigating to the frontend URL first
2. If not running, follow the dev startup procedure from `CLAUDE.md`:
   - Start service containers (if needed)
   - Start backend dev server (in background)
   - Start frontend dev server (in background)
   - Wait for both to be ready
3. **Determine the frontend URL** from server output
4. **Read `.env`** for any credentials or API keys needed for testing

## Test Flow

### Phase 1: Page Load & Navigation

1. Navigate to the frontend URL
2. Verify the landing/home page renders correctly
3. Check all visible links and navigation elements work
4. Verify no console errors on initial load

### Phase 2: Authentication

1. Test the login flow — find the login page, verify form renders
2. If registration exists, register a new user with a unique username (e.g., "PlaytestUser_" + timestamp)
3. If using existing credentials, check `.env` or use test account credentials
4. Verify successful login redirects to the correct page
5. Verify auth-protected pages are actually protected (try accessing without login)

### Phase 3: Core Feature Testing

Based on what `docs/SYSTEM.md` describes as the key features:

1. **Navigate through all major pages** — verify each one renders with real data (not placeholders)
2. **Test the primary user flow end-to-end** — the main thing the app is designed to do
3. **Test secondary features** — any additional functionality described in SYSTEM.md
4. **Test form submissions** — verify validation, success states, error states
5. **Test interactive elements** — buttons, modals, dropdowns, etc.
6. **Check responsive behavior** — does the layout break at different sizes?

### Phase 4: State & Persistence

1. **Returning user flow:** Log out, log back in — verify state persists correctly
2. **Page refresh:** Refresh the browser on key pages — verify the app recovers gracefully
3. **Browser back/forward:** Navigate using browser controls — verify routing works

### Phase 5: Edge Cases & Error Handling

1. **Invalid input:** Submit forms with empty/invalid data — verify error messages
2. **Network errors:** Check how the app handles API failures (if testable)
3. **Loading states:** Verify spinners/loading indicators appear during async operations
4. **Empty states:** Check pages that might have no data — verify they show helpful messages

## Reporting

### Fresh vs Continuing Playtest

Check if `docs/todo/playtest-bugs.md` exists:

- **If it does NOT exist** (first playtest): Start fresh. Create `docs/todo/playtest-bugs.md` from scratch. Assign bugs starting from BUG-001.
- **If it DOES exist** (continuing): This is a cumulative living document. Follow the cumulative rules below.

### Cumulative Bug List Rules (when file exists)

Update `docs/todo/playtest-bugs.md` following these rules:
- READ the existing bug list — do NOT start from scratch
- Verify all previously-fixed bugs still work (regression check)
- Verify all still-open bugs — move to FIXED section if now resolved
- Assign NEW bugs sequential IDs continuing from the highest existing BUG-XXX number
- Categorize each bug: Critical, Major, Moderate, Low
- Include: date of test, what's working, what's still broken, what was fixed since last test
- Preserve the full bug history — this is a living document across runs

### Bug Report Format

For each bug include:
- **ID:** BUG-XXX
- **Severity:** Critical / Major / Moderate / Low
- **Summary:** One-line description
- **Steps to Reproduce:** Numbered steps
- **Expected:** What should happen
- **Actual:** What actually happens
- **Screenshot:** Take a screenshot with `mcp__playwright__browser_take_screenshot` if visual

### Tools

- Use `mcp__playwright__browser_snapshot` (accessibility tree) for verifying content and finding element refs
- Use `mcp__playwright__browser_take_screenshot` for visual evidence of bugs
- Use `mcp__playwright__browser_console_messages` to check for JS errors
