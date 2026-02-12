---
allowed-tools: Bash(*), mcp__playwright__*, Read, Write, Edit, Glob, Grep
description: Start the app and run a full Playwright playtest as a new user and returning user
---

You are a QA tester performing a comprehensive playtest of the AI-MUD application using Playwright.

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
3. **Step 3 - Companion Creation**: Chat to create a companion (suggest a form, name, personality)
4. **Step 4 - Enter World**: Review summary, click to enter the game

### Phase 3: Game Page Testing
1. **Left Panel**: Check if current area shows real data (name, description, exits, entities, items)
2. **Center Chat**: Send a message to the companion, verify response
3. **Right Panel**: Check all tabs (Inventory, Keywords, Quests, Companion, Settings)
4. **Header**: Verify gold, HP, player name, season text
5. **Footer**: Verify area name, connection status, LLM provider
6. **World Map**: Check if map nodes appear

### Phase 4: Returning User
1. Log out
2. Log back in with the same credentials
3. Verify: session restores correctly, conversation history persists, stores are hydrated
4. Verify: no duplicate welcome message, area data loads

### Phase 5: Page Refresh
1. On the game page, refresh the browser (navigate to same URL)
2. Verify: session survives, stores re-hydrate, game loads correctly

## Reporting

After completing all tests, update `docs/todo/playtest-bugs.md` with:
- Date of test
- What's working
- What's still broken (with severity)
- What was fixed since last test

Take screenshots of any issues found.
