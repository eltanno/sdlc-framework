# Integration Tests: /analyze-codebase Command

**Test Suite:** analyze-codebase
**Created:** 2026-01-19
**Ticket:** AUCT-0196
**Status:** Ready for Manual Execution

---

## Overview

This document defines integration tests for the `/analyze-codebase` slash command. Since this is a prompt-based feature (not executable code), tests are executed manually by running the command against sample projects.

## Test Fixtures

Three sample projects are provided for testing:

| Fixture | Location | Stack |
|---------|----------|-------|
| TypeScript | `test/fixtures/typescript-sample/` | TypeScript, Express, Jest, ESLint |
| Python | `test/fixtures/python-sample/` | Python 3.11, FastAPI, pytest, ruff |
| Go | `test/fixtures/go-sample/` | Go 1.21, Gin |

Each fixture includes:
- Project configuration files (package.json, pyproject.toml, go.mod)
- Source code structure (routes, services, models)
- TODO/FIXME/HACK comments for Concerns analysis
- External API integration patterns
- Health check endpoints

---

## Test Cases

### TC-01: Command Recognition

**Requirement:** FR-1 (Slash Command Registration)
**Priority:** P1

**Steps:**
1. Open Claude Code CLI
2. Type `/analyze-codebase`
3. Press Enter

**Expected Result:**
- Command is recognized and begins execution
- Clarifying questions are presented to user

**Pass Criteria:**
- [ ] Command starts without "unrecognized command" error
- [ ] Q&A phase begins with 3 optional questions

---

### TC-02: Skip All Questions

**Requirement:** FR-2 (Optional Clarifying Questions)
**Priority:** P1

**Steps:**
1. Run `/analyze-codebase`
2. When prompted, respond with "skip all"

**Expected Result:**
- Analysis begins immediately without further questions
- No error occurs

**Pass Criteria:**
- [ ] Analysis proceeds without asking individual questions
- [ ] All 8 documents are generated

---

### TC-03: Provide Context Answers

**Requirement:** FR-2 (Optional Clarifying Questions)
**Priority:** P1

**Steps:**
1. Run `/analyze-codebase` on typescript-sample fixture
2. Answer questions:
   - Purpose: "REST API for user management"
   - Concerns: "authentication and rate limiting"
   - Pain points: "no real database, using in-memory storage"

**Expected Result:**
- Answers are captured and passed to analysis agents
- CONCERNS.md mentions authentication and rate limiting
- Analysis reflects provided context

**Pass Criteria:**
- [ ] User-provided concerns appear in CONCERNS.md
- [ ] Pain points are addressed with recommendations

---

### TC-04: TypeScript Project Analysis

**Requirement:** FR-3 to FR-10 (All Analysis Documents)
**Priority:** P1

**Setup:**
```bash
cd test/fixtures/typescript-sample
```

**Steps:**
1. Run `/analyze-codebase` in the typescript-sample directory
2. Wait for completion
3. Check `docs/legacy/` directory

**Expected Results:**

| Document | Key Content |
|----------|-------------|
| STACK.md | TypeScript 5.3.2, Node.js 18+, Express 4.18.2, Jest |
| ARCHITECTURE.md | Express routes, service layer pattern |
| STRUCTURE.md | src/ with routes/, services/ subdirectories |
| CONVENTIONS.md | TypeScript strict mode, ESLint configuration |
| TESTING.md | Jest framework, tests in test/ directory |
| INTEGRATIONS.md | axios for external API calls |
| CONCERNS.md | TODO/FIXME/HACK comments found |
| NEXT-STEPS.md | P1/P2/P3 priorities, SDLC guidance |

**Pass Criteria:**
- [ ] All 8 files exist in docs/legacy/
- [ ] STACK.md correctly identifies TypeScript and Express
- [ ] ARCHITECTURE.md describes routes → service pattern
- [ ] STRUCTURE.md lists src/, routes/, services/
- [ ] CONVENTIONS.md mentions strict TypeScript
- [ ] TESTING.md identifies Jest
- [ ] INTEGRATIONS.md finds axios/external API
- [ ] CONCERNS.md lists TODO/FIXME/HACK comments
- [ ] NEXT-STEPS.md has P1/P2/P3 sections

---

### TC-05: Python Project Analysis

**Requirement:** NFR-3 (Compatibility - Python)
**Priority:** P2

**Setup:**
```bash
cd test/fixtures/python-sample
```

**Steps:**
1. Run `/analyze-codebase` in the python-sample directory
2. Wait for completion
3. Check `docs/legacy/` directory

**Expected Results:**

| Document | Key Content |
|----------|-------------|
| STACK.md | Python 3.11, FastAPI, pydantic, SQLAlchemy |
| ARCHITECTURE.md | FastAPI routers, service layer |
| STRUCTURE.md | src/ with api/, models/, services/, core/ |
| CONVENTIONS.md | ruff, mypy strict mode |
| TESTING.md | pytest, pytest-asyncio |
| INTEGRATIONS.md | httpx for external API calls |
| CONCERNS.md | TODO/FIXME/HACK comments found |
| NEXT-STEPS.md | P1/P2/P3 priorities |

**Pass Criteria:**
- [ ] All 8 files exist in docs/legacy/
- [ ] STACK.md correctly identifies Python 3.11 and FastAPI
- [ ] ARCHITECTURE.md describes FastAPI router pattern
- [ ] CONVENTIONS.md mentions ruff and mypy
- [ ] TESTING.md identifies pytest

---

### TC-06: Go Project Analysis

**Requirement:** NFR-3 (Compatibility - Go)
**Priority:** P2

**Setup:**
```bash
cd test/fixtures/go-sample
```

**Steps:**
1. Run `/analyze-codebase` in the go-sample directory
2. Wait for completion
3. Check `docs/legacy/` directory

**Expected Results:**

| Document | Key Content |
|----------|-------------|
| STACK.md | Go 1.21, Gin framework |
| ARCHITECTURE.md | Gin handlers, service layer |
| STRUCTURE.md | handlers/, services/, models/ packages |
| CONVENTIONS.md | Go module structure |
| TESTING.md | No tests found (fixture has no tests) |
| INTEGRATIONS.md | godotenv for environment |
| CONCERNS.md | TODO/FIXME/HACK comments found |
| NEXT-STEPS.md | P1/P2/P3 priorities |

**Pass Criteria:**
- [ ] All 8 files exist in docs/legacy/
- [ ] STACK.md correctly identifies Go 1.21 and Gin
- [ ] ARCHITECTURE.md describes Gin handler pattern
- [ ] TESTING.md states "No tests found" and recommends testing
- [ ] CONCERNS.md lists TODO/FIXME/HACK comments

---

### TC-07: Non-Destructive Operation

**Requirement:** FR-11 (Non-Destructive Operation)
**Priority:** P1

**Steps:**
1. Navigate to any fixture directory
2. Run `git status` (or note existing files)
3. Run `/analyze-codebase`
4. Run `git status` again

**Expected Result:**
- Only `docs/legacy/` files are created
- No source files are modified

**Pass Criteria:**
- [ ] No source files (.ts, .py, .go) are modified
- [ ] No config files (package.json, etc.) are modified
- [ ] Only docs/legacy/*.md files are created

---

### TC-08: Directory Creation

**Requirement:** FR-13 (Output Directory Creation)
**Priority:** P1

**Steps:**
1. Ensure `docs/legacy/` does not exist
2. Run `/analyze-codebase`
3. Check if directory was created

**Expected Result:**
- `docs/legacy/` directory is created
- All 8 documents are placed inside

**Pass Criteria:**
- [ ] docs/legacy/ directory exists after completion
- [ ] docs/ directory created if it didn't exist

---

### TC-09: Document Quality - Meaningful Content

**Requirement:** Success Metric (>10 meaningful items)
**Priority:** P2

**Steps:**
1. Run `/analyze-codebase` on typescript-sample
2. Review each generated document

**Expected Result:**
- Each document has substantive content
- Not just template boilerplate

**Pass Criteria:**
- [ ] STACK.md lists >5 specific technologies with versions
- [ ] ARCHITECTURE.md describes >3 patterns or components
- [ ] STRUCTURE.md lists >5 directories/files with purposes
- [ ] CONVENTIONS.md identifies >3 style conventions
- [ ] TESTING.md provides >3 testing-related findings
- [ ] INTEGRATIONS.md lists external dependencies
- [ ] CONCERNS.md identifies >3 specific issues
- [ ] NEXT-STEPS.md has items in each P1/P2/P3 section

---

### TC-10: NEXT-STEPS.md Structure

**Requirement:** FR-10 (Next Steps Document)
**Priority:** P1

**Steps:**
1. Run `/analyze-codebase` on any fixture
2. Open NEXT-STEPS.md
3. Verify structure

**Expected Result:**
- Document has required sections
- Priorities are actionable

**Pass Criteria:**
- [ ] Summary section exists (1 paragraph)
- [ ] Priority 1 (Critical) section exists
- [ ] Priority 2 (Important) section exists
- [ ] Priority 3 (Nice to Have) section exists
- [ ] "How to Proceed with SDLC" section exists
- [ ] References to `/discover` command included

---

## Test Execution Log

| Date | Fixture | Tester | Result | Notes |
|------|---------|--------|--------|-------|
| _YYYY-MM-DD_ | _typescript-sample_ | _Name_ | _Pass/Fail_ | _Notes_ |
| _YYYY-MM-DD_ | _python-sample_ | _Name_ | _Pass/Fail_ | _Notes_ |
| _YYYY-MM-DD_ | _go-sample_ | _Name_ | _Pass/Fail_ | _Notes_ |

---

## Known Limitations

1. **Manual execution required** - No automated test runner for prompt-based commands
2. **Fixture isolation** - Fixtures should be copied/cleaned between test runs
3. **Output variability** - Agent analysis may vary between runs

---

## Verification Checklist

Before marking AUCT-0196 complete:

- [ ] All 3 fixtures created (TypeScript, Python, Go)
- [ ] TC-01 through TC-10 documented
- [ ] Each test case has clear pass criteria
- [ ] Test execution log template provided

---

*Generated for `/analyze-codebase` integration testing*
