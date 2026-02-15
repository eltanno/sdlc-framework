---
allowed-tools: Bash(*), mcp__playwright__*, Read, Write, Edit, Glob, Grep
description: Start the app and run a full Playwright playtest as a new user and returning user
---

You are a QA tester performing a comprehensive playtest of the AI-MUD application using Playwright.

**CRITICAL: You must actually PLAY THE GAME.** This is not just a UI check — you must navigate through pages, use exits, explore areas, interact with NPCs/items, and try to progress through the adventure like a real player would. If you cannot play the game as an adventure (move between areas, find things to do, progress), that is a critical bug.

## Setup

1. **Kill any existing processes** on ports 3000 and 5173-5180
2. **Start the backend** in background: `cd /home/jim/workspace/ai-mud && npm run dev --workspace=backend`
3. **Start the frontend** in background: `cd /home/jim/workspace/ai-mud && npm run dev --workspace=frontend`
4. **Wait** for both to be ready (backend on 3000, frontend on 5173 or 5174+)
5. **Read the .env file** to get the ANTHROPIC_API_KEY for LLM setup

## Test Flow

### Phase 1: New User Registration
1. Navigate to the frontend URL
2. Observe the splash page — verify all sections render
3. Click "Begin Your Journey" or navigate to /register
4. Register a new account with a unique username (e.g., "PlaytestUser_" + timestamp)
5. Verify redirect to onboarding

### Phase 2: Onboarding
1. **Step 1 - LLM Setup**: Select "Anthropic" provider, enter the API key from .env, test connection, select "Claude Haiku 4.5" model
2. **Step 2 - World Intro**: Watch text animation, enter a character name
3. **Step 3 - Companion Creation**: Chat to create a companion (suggest a form, name, personality). Verify:
   - Intro text appears IN the chat area (not as separate fading text above)
   - Once companion is confirmed, the chat input is disabled/hidden
   - "ENTER THE WORLD" button appears only after companion is fully formed
4. **Step 4 - Enter World**: Review summary, click to enter the game

### Phase 3: Game Page Verification
1. **Left Panel**: Check if current area shows real data (name, description, exits, entities, items) — NOT "..." placeholders
2. **Center Chat**: Send a message to the companion, verify response
3. **Right Panel**: Check all tabs (Inventory, Keywords, Quests, Companion, Settings)
4. **Header**: Verify gold, HP, player name, season text
5. **Footer**: Verify area name, connection status, LLM provider AND model name (e.g., "LLM: Anthropic · Claude Haiku 4.5")
6. **World Map**: Check that map shows actual visitable pages (not just region labels or "Test Map Node")
7. **Settings**: Verify there is a way to change the LLM model (e.g., a "Change LLM Settings" button)

### Phase 4: PLAY THE GAME (Most Important Phase)
**This is the core test. You must actually play the adventure as a real user would.**

1. **Read your current area** — understand where you are, what the description says
2. **Look at exits** — there should be clickable exits to other areas
3. **Click an exit** — navigate to a different area. Verify the left panel updates with new area data.
4. **Explore at least 3-4 different areas** — move around the world, verify each area has a name, description, and exits
5. **Talk to your companion** in different areas — ask about the area, ask for advice
6. **Check for NPCs** — if any are present in an area, try to interact
7. **Check for items** — if any are visible, try to interact
8. **Check the map** — does it update as you explore? Does it show where you've been?
9. **Try to progress** — look for quests, objectives, things to do
10. **If you get stuck** (no exits, can't navigate, nothing to do) — this is a CRITICAL bug

The game should feel like a playable text adventure/MUD. If it doesn't, document exactly where it breaks down.

### Phase 5: Returning User
1. Log out
2. Log back in with the same credentials
3. Verify: session restores correctly, conversation history persists, stores are hydrated
4. Verify: no duplicate welcome message, area data loads
5. Verify: you are in the same area you were in when you logged out

### Phase 6: Page Refresh
1. On the game page, refresh the browser (navigate to same URL)
2. Verify: session survives, stores re-hydrate, game loads correctly
3. Verify: area data persists after refresh

## Reporting

### Fresh vs Continuing Playtest

Check if `docs/todo/playtest-bugs.md` exists:

- **If it does NOT exist** (first playtest of a new release cycle): Start fresh. Create `docs/todo/playtest-bugs.md` from scratch. Assign bugs starting from BUG-001. No regression checking needed — this is a clean baseline.
- **If it DOES exist** (continuing an existing release cycle): This is a cumulative living document. Follow the cumulative rules below.

### Cumulative Bug List Rules (when file exists)

Update `docs/todo/playtest-bugs.md` following these rules:
- READ the existing bug list — do NOT start from scratch
- Verify all previously-fixed bugs still work (move to FIXED if regressed, keep in FIXED if still working)
- Verify all still-open bugs — move to FIXED section if now resolved
- Assign NEW bugs sequential IDs continuing from the highest existing number (e.g., if last is BUG-015, next is BUG-016)
- Categorize each bug: Critical, Major, Moderate, Low
- Include: date of test, what's working, what's still broken, what was fixed since last test
- Preserve the full bug history — this is a living document across runs
- **Include a "GAMEPLAY TEST" section** documenting: areas visited, exits used, what worked, what didn't, whether the game feels playable

Take screenshots of any issues found.
