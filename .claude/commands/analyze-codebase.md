# Analyze Codebase - Orchestrator Instructions

> **MANDATORY: READ THIS ENTIRE FILE BEFORE PROCEEDING.**
> **You must confirm you have read and understood all sections.**

**You ARE the orchestrator for this command. You conduct the optional Q&A yourself, then delegate analysis to specialized agents.**

---

## Purpose

Deep, non-destructive analysis of any existing codebase to produce comprehensive documentation. This command helps teams understand brownfield/legacy projects and plan SDLC adoption.

**Output:** 8 structured documents in `docs/legacy/`

## When to Use

- Onboarding to an unfamiliar codebase
- Planning SDLC adoption for legacy projects
- Technical debt assessment
- Architecture documentation for existing systems
- Before major refactoring efforts

## Non-Destructive Guarantee

**CRITICAL:** This command is strictly READ-ONLY.
- Only creates files in `docs/legacy/`
- Never modifies source code
- Never changes configuration files
- `git status` should show only `docs/legacy/` changes after completion

## Analysis Scope Exclusions

**IMPORTANT:** The following directories and files should be EXCLUDED from analysis:

1. **`.claude/` directory** - Contains Claude Code configuration, commands, and agents. This is tooling, not application code.

2. **All gitignored paths** - Before analyzing, check `.gitignore` and exclude any matching paths. Common exclusions:
   - `node_modules/`, `__pycache__/`, `.venv/`, `venv/`
   - `dist/`, `build/`, `.next/`, `out/`
   - `.env` files (but DO analyze `.env.example`)
   - IDE directories (`.idea/`, `.vscode/` settings)
   - Log files, coverage reports, etc.

**How to apply exclusions:**
- When using `Glob`, exclude these paths from results
- When using `Grep`, avoid searching in excluded directories
- When counting files/lines, filter out excluded paths
- Focus analysis on actual application source code

---

## Phase 1: Optional Clarifying Questions (Self-Executed)

Before spawning analysis agents, ask the user these optional questions to focus the analysis. Users can skip any or all questions.

### Start with:

```
## Analyze Codebase

I'll analyze this codebase and generate comprehensive documentation in `docs/legacy/`.

Before I begin, a few optional questions to help focus the analysis:

1. **What's the main purpose of this project?**
   (Skip with "skip" or similar - I'll infer from the code)

2. **Any specific areas of concern or focus?**
   (e.g., "the authentication system feels fragile", "performance issues")

3. **Known pain points or technical debt?**
   (Things you already know are problematic)

You can answer these questions to focus the analysis, or just say "skip all" to start the analysis immediately.
```

### Handling Responses:

- If user says "skip", "not sure", "don't know", or similar - proceed without that context
- If user says "skip all" or "just start" - begin analysis immediately
- Otherwise, capture their answers to pass to analysis agents

---

## Phase 2: Directory Setup

Before spawning agents, create the output directory:

```bash
mkdir -p docs/legacy
```

---

## Phase 3: Spawn Analysis Agents (Parallel)

**CRITICAL: Spawn these 7 agents IN PARALLEL** using multiple Task tool invocations in a single message.

Each agent produces one document. They are independent and can run concurrently.

### Agent Template

For each analyzer, use:

```
Task({
  subagent_type: "general-purpose",
  model: "opus",
  prompt: <see individual agent prompts below>
})
```

---

## Agent Prompts

### 3.1 Stack Analyzer Agent

```markdown
## STACK ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze the technology stack of this codebase and document your findings.

### Analysis Areas

1. **Primary Languages**
   - Identify all programming languages used
   - Note relative proportions if multiple languages
   - Identify language versions from config files

2. **Frameworks & Libraries**
   - Major frameworks (React, Express, Django, FastAPI, etc.)
   - Key libraries and their purposes
   - Version information where available

3. **Runtime Environment**
   - Node.js, Python, Go version requirements
   - Container configuration if present (Docker, etc.)
   - Cloud platform indicators (AWS, GCP, Azure)

4. **Build Tools**
   - Build systems (webpack, vite, esbuild, make, etc.)
   - Package managers (npm, yarn, pip, poetry, go mod)
   - Task runners and scripts

5. **Development Tools**
   - Linters and formatters configured
   - Type checking tools
   - Development dependencies

### How to Analyze

Use these tools to gather information:
- `Glob` for file patterns: `**/*.ts`, `**/*.py`, `**/package.json`, etc.
- `Read` to examine config files: package.json, pyproject.toml, go.mod, etc.
- `Grep` to find import patterns and dependencies

**Language-Specific Version Detection:**

| Ecosystem | Version Sources |
|-----------|-----------------|
| TypeScript | `tsconfig.json` (target, lib), `package.json` (typescript version), `.nvmrc` or `engines.node` |
| Python | `pyproject.toml` (requires-python), `.python-version`, `setup.py`, `runtime.txt` |
| Go | `go.mod` (go directive), `Dockerfile` (FROM golang:version) |

**Framework Detection Patterns:**
- React: Look for `react` in package.json dependencies, `jsx`/`tsx` files
- Express/Fastify: Look in package.json, trace from main entry point
- Django/FastAPI: Look in pyproject.toml/requirements.txt, find main app module
- Gin/Echo: Look in go.mod, find main.go imports

### Output

Create `docs/legacy/STACK.md` using the template at `docs/templates/analyze-codebase-stack.md`.

### Return

After creating the document, return:
```
STACK ANALYSIS COMPLETE
Document: docs/legacy/STACK.md
Primary stack: [1-2 sentence summary]
```
```

---

### 3.2 Architecture Analyzer Agent

```markdown
## ARCHITECTURE ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze the architectural patterns and data flow of this codebase.

### Analysis Areas

1. **System Architecture**
   - Monolith vs microservices vs serverless
   - Client-server separation
   - Frontend/backend split if applicable

2. **Design Patterns**
   - MVC, MVVM, Clean Architecture, etc.
   - Repository pattern, Service layer
   - Event-driven patterns

3. **Data Flow**
   - How data enters the system
   - How data is processed/transformed
   - How data exits the system

4. **Data Layer**
   - Database types (SQL, NoSQL, file-based)
   - ORM usage and patterns
   - Data models and schemas

5. **API Structure**
   - REST, GraphQL, gRPC
   - Endpoint organization
   - Authentication/authorization patterns

6. **Inter-Component Communication**
   - How modules talk to each other
   - Message queues, events, direct calls
   - Shared state patterns

### How to Analyze

Use these tools to gather information:
- `Glob` for file patterns: `**/routes/**`, `**/controllers/**`, `**/models/**`, `**/services/**`
- `Read` to examine entry points, config files, and key modules
- `Grep` to find patterns like imports, decorators, and API definitions

**Architecture Detection Patterns:**

| Architecture | Detection Indicators |
|--------------|---------------------|
| Monolith | Single entry point, all code in one repo, shared database |
| Microservices | Multiple entry points, docker-compose with multiple services, separate package files |
| Serverless | Lambda handlers, `serverless.yml`, Vercel/Netlify configs |
| Monorepo | Multiple `package.json` files, workspaces config, Nx/Turborepo config |
| Frontend/Backend Split | Separate `client`/`server` or `frontend`/`backend` directories |

**Design Pattern Detection:**

| Pattern | Detection Indicators |
|---------|---------------------|
| MVC | `controllers/`, `models/`, `views/` directories; Rails/Django/Express patterns |
| Clean Architecture | `domain/`, `usecases/`, `infrastructure/` directories; dependency inversion |
| Repository Pattern | `*Repository` classes, `repositories/` directory |
| Service Layer | `*Service` classes, `services/` directory |
| Event-Driven | Event emitters, message queue imports (RabbitMQ, Kafka, Redis pub/sub) |
| CQRS | Separate read/write models, `commands/`, `queries/` directories |

**Data Layer Detection:**

| ORM/Database | Detection Patterns |
|--------------|-------------------|
| Prisma | `prisma/schema.prisma`, `@prisma/client` imports |
| TypeORM | `@Entity`, `@Column` decorators, `ormconfig.json` |
| Sequelize | `sequelize` imports, `models/index.js` pattern |
| SQLAlchemy | `from sqlalchemy` imports, `models.py` with Base class |
| Django ORM | `models.py` with `models.Model`, migrations directory |
| Mongoose | `mongoose.Schema`, `mongoose.model` patterns |
| Drizzle | `drizzle.config.ts`, `@drizzle-orm` imports |
| Raw SQL | Direct `pg`, `mysql2`, `sqlite3` imports without ORM |

**API Structure Detection:**

| API Style | Detection Patterns |
|-----------|-------------------|
| REST | Route files with HTTP methods (GET, POST, PUT, DELETE), `/api/` paths |
| GraphQL | `typeDefs`, `resolvers`, `.graphql` files, Apollo/Yoga/Mercurius |
| gRPC | `.proto` files, gRPC package imports |
| tRPC | `trpc` imports, router definitions |
| WebSocket | `socket.io`, `ws` imports, WebSocket handlers |

**Entry Point Detection:**

| Ecosystem | Common Entry Points |
|-----------|-------------------|
| Node.js | `src/index.ts`, `app.ts`, `server.ts`, `main.ts` (check `package.json` "main") |
| Python | `main.py`, `app.py`, `manage.py`, `wsgi.py`, `asgi.py` |
| Go | `main.go`, `cmd/*/main.go` |

### Output

Create `docs/legacy/ARCHITECTURE.md` using the template at `docs/templates/analyze-codebase-architecture.md`.

### Return

After creating the document, return a brief summary of the architecture found.

---

### 3.3 Structure Analyzer Agent

```markdown
## STRUCTURE ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze the directory organization and file structure of this codebase.

### Analysis Areas

1. **Top-Level Organization**
   - What directories exist at root
   - Purpose of each major directory
   - Configuration files at root

2. **Source Code Organization**
   - Feature-based vs layer-based structure
   - Module boundaries
   - Shared code location

3. **Entry Points**
   - Main application entry
   - CLI entry points
   - Test entry points

4. **Configuration Files**
   - Build configuration
   - Environment configuration
   - Tool configuration

5. **Documentation Location**
   - README and docs
   - API documentation
   - Code comments patterns

### How to Analyze

Use these tools to gather information:
- `Bash` with `ls -la` to list root directory contents
- `Glob` for file patterns: `**/src/**`, `**/lib/**`, `**/app/**`
- `Read` to examine README files and configuration
- `Grep` to find import patterns revealing module structure

**Organization Pattern Detection:**

| Pattern | Detection Indicators |
|---------|---------------------|
| Feature-based | Directories named after features: `auth/`, `users/`, `billing/`, `products/` with each containing full stack (components, services, tests) |
| Layer-based | Directories named after layers: `controllers/`, `services/`, `models/`, `views/`, `repositories/` |
| Domain-Driven | `domain/`, `application/`, `infrastructure/` directories; bounded context separation |
| Modular Monolith | `modules/` or `packages/` with self-contained modules; clear module boundaries |
| Flat | Most files at root or single `src/` with no sub-organization |
| Hybrid | Mix of feature and layer patterns; common in evolved codebases |

**Common Directory Purposes:**

| Directory | Common Purposes |
|-----------|-----------------|
| `src/`, `lib/`, `app/` | Main application source code |
| `test/`, `tests/`, `__tests__/`, `spec/` | Test files |
| `config/`, `conf/` | Configuration files |
| `scripts/`, `bin/` | Build/deploy/utility scripts |
| `docs/`, `documentation/` | Documentation |
| `public/`, `static/`, `assets/` | Static files served directly |
| `dist/`, `build/`, `out/` | Build output (usually gitignored) |
| `vendor/`, `third_party/` | Vendored dependencies |
| `migrations/`, `db/` | Database migrations |
| `templates/`, `views/` | Template files for rendering |
| `.github/`, `.gitlab/` | CI/CD configuration |
| `cmd/` | Go command entry points |
| `internal/`, `pkg/` | Go internal/public packages |
| `apps/`, `packages/` | Monorepo sub-projects |

**Entry Point Detection by Ecosystem:**

| Ecosystem | Common Entry Points |
|-----------|-------------------|
| Node.js/TypeScript | Check `package.json` "main", "module", "exports"; look for `src/index.ts`, `src/main.ts`, `app.ts`, `server.ts` |
| Python | `main.py`, `app.py`, `__main__.py`, `manage.py` (Django), `wsgi.py`, `asgi.py`; check `pyproject.toml` [tool.poetry.scripts] |
| Go | `main.go` at root, `cmd/*/main.go` for multi-binary projects |
| .NET | `Program.cs`, `Startup.cs`; check `.csproj` for entry point |

**Configuration File Detection:**

| File | Purpose | Ecosystem |
|------|---------|-----------|
| `package.json` | Dependencies, scripts, metadata | Node.js |
| `tsconfig.json` | TypeScript compiler options | TypeScript |
| `pyproject.toml`, `setup.py`, `setup.cfg` | Python package config | Python |
| `requirements.txt`, `Pipfile` | Python dependencies | Python |
| `go.mod`, `go.sum` | Go module definition | Go |
| `Makefile` | Build automation | Cross-platform |
| `docker-compose.yml`, `Dockerfile` | Container config | Docker |
| `.env`, `.env.example` | Environment variables | Cross-platform |
| `.eslintrc*`, `.prettierrc*` | Linting/formatting | JavaScript/TypeScript |
| `jest.config.*`, `vitest.config.*` | Test framework config | JavaScript/TypeScript |
| `pytest.ini`, `pyproject.toml [tool.pytest]` | Test config | Python |
| `.github/workflows/*.yml` | CI/CD pipelines | GitHub Actions |
| `.gitlab-ci.yml` | CI/CD pipeline | GitLab CI |
| `vercel.json`, `netlify.toml` | Deployment config | Serverless/JAMstack |

**Monorepo Detection:**

| Indicator | Tool/Pattern |
|-----------|-------------|
| `workspaces` in package.json | npm/yarn workspaces |
| `pnpm-workspace.yaml` | pnpm workspaces |
| `lerna.json` | Lerna monorepo |
| `nx.json`, `project.json` files | Nx monorepo |
| `turbo.json` | Turborepo |
| Multiple `package.json` in subdirs | Generic monorepo |
| `apps/` and `packages/` structure | Common monorepo layout |

### Output

Create `docs/legacy/STRUCTURE.md` using the template at `docs/templates/analyze-codebase-structure.md`.

### Return

After creating the document, return a brief summary of the structure found.

---

### 3.4 Conventions Analyzer Agent

```markdown
## CONVENTIONS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze the code style conventions and standards used in this codebase.

### Analysis Areas

1. **Naming Conventions**
   - Variable naming (camelCase, snake_case, etc.)
   - Function/method naming
   - File naming patterns
   - Class/component naming
   - Constants naming

2. **Linting & Formatting**
   - ESLint, Prettier, Ruff, Black configs
   - Configured rules (key rules that deviate from defaults)
   - Auto-formatting setup
   - Pre-commit hooks

3. **Code Organization**
   - Import organization style
   - File structure within modules
   - Export patterns
   - Module boundary patterns

4. **Comment Patterns**
   - Documentation style (JSDoc, docstrings, etc.)
   - Inline comment patterns
   - TODO/FIXME/HACK usage patterns

5. **Git Conventions**
   - Commit message patterns (if observable from git log)
   - Branch naming (if observable)
   - PR templates if present

### How to Analyze

Use these tools to gather information:
- `Glob` for config files: `**/.eslintrc*`, `**/.prettierrc*`, `**/pyproject.toml`, `**/.editorconfig`
- `Read` to examine linter/formatter configurations
- `Grep` to find naming patterns in code: variable declarations, function definitions, class definitions
- `Bash` with `git log --oneline -20` to observe commit message patterns
- Sample 3-5 representative source files to observe actual conventions in practice

**Linter/Formatter Detection by Ecosystem:**

| Ecosystem | Linter | Formatter | Config Files |
|-----------|--------|-----------|--------------|
| TypeScript/JavaScript | ESLint | Prettier | `.eslintrc.*`, `eslint.config.js`, `.prettierrc.*`, `prettier.config.js` |
| Python | Ruff, Flake8, Pylint | Black, Ruff, YAPF | `pyproject.toml [tool.ruff]`, `.flake8`, `pylintrc`, `.style.yapf` |
| Go | golangci-lint | gofmt, goimports | `.golangci.yml`, `.golangci.yaml` |

**Key ESLint Rules to Document:**

| Rule Category | Example Rules | Why Important |
|---------------|---------------|---------------|
| Naming | `camelcase`, `@typescript-eslint/naming-convention` | Enforces naming standards |
| Imports | `import/order`, `import/no-cycle` | Import organization |
| Code Style | `semi`, `quotes`, `indent`, `max-len` | Basic formatting |
| Best Practices | `no-unused-vars`, `eqeqeq`, `no-console` | Code quality |
| TypeScript | `@typescript-eslint/explicit-function-return-type`, `@typescript-eslint/no-explicit-any` | Type safety |

**Key Prettier Options to Document:**

| Option | Common Values | Impact |
|--------|---------------|--------|
| `printWidth` | 80, 100, 120 | Line length |
| `tabWidth` | 2, 4 | Indentation |
| `semi` | true, false | Semicolon usage |
| `singleQuote` | true, false | Quote style |
| `trailingComma` | "es5", "all", "none" | Trailing commas |
| `arrowParens` | "always", "avoid" | Arrow function parens |

**Python Linting/Formatting Configuration:**

| Tool | Config Location | Key Settings |
|------|-----------------|--------------|
| Ruff | `pyproject.toml [tool.ruff]` | `line-length`, `select`, `ignore`, `target-version` |
| Black | `pyproject.toml [tool.black]` | `line-length`, `target-version`, `skip-string-normalization` |
| isort | `pyproject.toml [tool.isort]` | `profile`, `line_length`, `known_first_party` |
| mypy | `pyproject.toml [tool.mypy]` | `strict`, `ignore_missing_imports` |
| Flake8 | `.flake8` or `setup.cfg` | `max-line-length`, `ignore`, `exclude` |

**Naming Convention Detection Patterns:**

| Convention | Detection Pattern | Common Usage |
|------------|-------------------|--------------|
| camelCase | `[a-z][a-zA-Z0-9]*` | JavaScript/TypeScript variables, functions |
| PascalCase | `[A-Z][a-zA-Z0-9]*` | Classes, React components, TypeScript types |
| snake_case | `[a-z][a-z0-9_]*` | Python variables, functions, modules |
| SCREAMING_SNAKE_CASE | `[A-Z][A-Z0-9_]*` | Constants across languages |
| kebab-case | `[a-z][a-z0-9-]*` | File names, CSS classes, URL slugs |
| Hungarian notation | Prefixes like `str`, `int`, `arr` | Legacy codebases |

**How to Detect Naming Conventions:**
1. Sample variable declarations: `const`, `let`, `var` (JS); assignment statements (Python)
2. Sample function definitions: `function`, `const x = () =>` (JS); `def` (Python)
3. Sample class definitions: `class` keyword across languages
4. Sample file names: use `Glob` to list files and observe patterns
5. Look for constants: `const` with UPPER_CASE (JS); module-level UPPER_CASE (Python)

**Import Organization Detection:**

| Style | Detection Pattern | Example |
|-------|-------------------|---------|
| Grouped by type | External, then internal, then relative | React apps with `import/order` |
| Alphabetical | All imports sorted A-Z | Some auto-formatters |
| Ungrouped | No clear pattern | Legacy or no tooling |
| Absolute imports | `from src/components/...` | Configured in tsconfig/pyproject |
| Relative imports | `from ./`, `from ../` | Common default |
| Barrel exports | `index.ts` re-exports | Component libraries |

**File Naming Convention Detection:**

| Pattern | Examples | Ecosystem |
|---------|----------|-----------|
| kebab-case | `user-profile.ts`, `api-client.py` | Common in Node.js, Python |
| PascalCase | `UserProfile.tsx`, `ApiClient.ts` | React components, TypeScript classes |
| snake_case | `user_profile.py` | Python modules |
| camelCase | `userProfile.ts` | Some JavaScript projects |
| Dot notation | `user.controller.ts`, `user.service.ts` | NestJS, Angular |
| Suffix patterns | `*.spec.ts`, `*.test.js`, `*_test.go` | Test files |

**Documentation Style Detection:**

| Style | Detection Pattern | Ecosystem |
|-------|-------------------|-----------|
| JSDoc | `/** ... */` with `@param`, `@returns` | JavaScript/TypeScript |
| TSDoc | `/** ... */` with `@remarks`, `@example` | TypeScript (stricter) |
| Docstrings | `"""..."""` or `'''...'''` | Python |
| Google-style docstrings | `Args:`, `Returns:`, `Raises:` sections | Python (Google convention) |
| NumPy-style docstrings | `Parameters`, `Returns` with dashes | Python (scientific) |
| Godoc | Comment directly above declaration | Go |

**Git Convention Detection:**
- Run `git log --oneline -20` to see recent commit messages
- Look for patterns: Conventional Commits (`feat:`, `fix:`), ticket references (`[JIRA-123]`), imperative mood
- Check for `.github/PULL_REQUEST_TEMPLATE.md` or `.gitlab/merge_request_templates/`
- Check for `.gitmessage` or commit-msg hooks in `.husky/` or `.git/hooks/`

### Output

Create `docs/legacy/CONVENTIONS.md` using the template at `docs/templates/analyze-codebase-conventions.md`.

### Return

After creating the document, return a brief summary of conventions found and maturity level.

---

### 3.5 Testing Analyzer Agent

```markdown
## TESTING ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze the testing setup, patterns, and coverage in this codebase.

### Analysis Areas

1. **Test Framework**
   - Unit test framework (Jest, pytest, go test, etc.)
   - Integration test setup
   - E2E test framework if present

2. **Test Organization**
   - Where tests live (co-located, separate directory)
   - Naming conventions for test files
   - Test utilities and helpers

3. **Test Patterns**
   - Assertion styles
   - Mocking approaches
   - Fixture patterns
   - Setup/teardown patterns

4. **Coverage**
   - What's tested (identify tested areas)
   - What's not tested (identify gaps)
   - Coverage configuration if present

5. **CI Integration**
   - Test scripts in package.json or equivalent
   - CI configuration for tests
   - Coverage reporting setup

### How to Analyze

Use these tools to gather information:
- `Glob` for test files: `**/*.test.ts`, `**/*.spec.ts`, `**/test_*.py`, `**/*_test.go`, `**/__tests__/**`
- `Read` to examine test configuration files and sample test files
- `Grep` to find test patterns: describe blocks, test functions, assertions
- Check package.json, pyproject.toml, go.mod for test dependencies

**Test Framework Detection by Ecosystem:**

| Ecosystem | Framework | Detection Indicators |
|-----------|-----------|---------------------|
| JavaScript/TypeScript | Jest | `jest` in devDependencies, `jest.config.*`, `@jest/globals` imports |
| JavaScript/TypeScript | Vitest | `vitest` in devDependencies, `vitest.config.*`, `import { describe } from 'vitest'` |
| JavaScript/TypeScript | Mocha | `mocha` in devDependencies, `.mocharc.*`, `mocha.opts` |
| JavaScript/TypeScript | Jasmine | `jasmine` in devDependencies, `jasmine.json` |
| JavaScript/TypeScript | AVA | `ava` in devDependencies, `ava` config in package.json |
| JavaScript/TypeScript | Tape | `tape` in devDependencies, `require('tape')` |
| JavaScript/TypeScript | Node Test Runner | `node:test` imports (Node.js 18+) |
| Python | pytest | `pytest` in requirements/pyproject, `pytest.ini`, `conftest.py`, `test_*.py` files |
| Python | unittest | `import unittest`, `class *Test(unittest.TestCase)` |
| Python | nose/nose2 | `nose`/`nose2` in requirements, `setup.cfg [nosetests]` |
| Python | doctest | `doctest.testmod()`, `>>> ` patterns in docstrings |
| Go | testing | `_test.go` files, `import "testing"`, `func Test*` |
| Go | testify | `github.com/stretchr/testify` imports |
| Go | ginkgo | `github.com/onsi/ginkgo` imports, `*_suite_test.go` |

**E2E/Integration Framework Detection:**

| Framework | Detection Indicators | Purpose |
|-----------|---------------------|---------|
| Playwright | `@playwright/test` in deps, `playwright.config.*` | Browser E2E |
| Cypress | `cypress` in deps, `cypress.config.*`, `cypress/` directory | Browser E2E |
| Puppeteer | `puppeteer` in deps, often custom test setup | Browser automation |
| Selenium | `selenium-webdriver` or language bindings | Browser E2E |
| WebdriverIO | `webdriverio` in deps, `wdio.conf.*` | Browser E2E |
| Supertest | `supertest` in deps, used with Jest/Mocha | HTTP API testing |
| TestContainers | `testcontainers` imports | Integration with Docker |
| pytest-docker | `pytest-docker` plugin | Python integration tests |
| httptest | `net/http/httptest` imports | Go HTTP testing |

**Test File Location Patterns:**

| Pattern | Location | Common In |
|---------|----------|-----------|
| Co-located | `src/utils/helper.ts` → `src/utils/helper.test.ts` | Modern JS/TS projects |
| Separate `__tests__` | `src/utils/__tests__/helper.test.ts` | React/CRA convention |
| Root `test/` directory | `test/unit/`, `test/integration/`, `test/e2e/` | Many frameworks |
| Root `tests/` directory | `tests/` | Python convention |

**Test File Naming Conventions:**

| Convention | Pattern | Ecosystem |
|------------|---------|-----------|
| `.test.ts/js` | `*.test.ts`, `*.test.js` | Jest, Vitest (common) |
| `.spec.ts/js` | `*.spec.ts`, `*.spec.js` | Jasmine, Angular, Playwright |
| `_test.go` | `*_test.go` | Go (required convention) |
| `test_*.py` | `test_*.py`, `*_test.py` | pytest (both supported) |

**Configuration File Detection:**

| Framework | Config Files | Key Settings to Note |
|-----------|--------------|---------------------|
| Jest | `jest.config.js/ts/mjs`, `package.json "jest"` | `testEnvironment`, `collectCoverage`, `coverageThreshold`, `setupFilesAfterEnv` |
| Vitest | `vitest.config.ts/js`, `vite.config.ts` (test section) | `environment`, `coverage`, `include/exclude` |
| pytest | `pytest.ini`, `pyproject.toml [tool.pytest]`, `setup.cfg`, `conftest.py` | `testpaths`, `addopts`, `markers` |
| Mocha | `.mocharc.*`, `package.json "mocha"` | `reporter`, `timeout`, `recursive` |
| Playwright | `playwright.config.ts/js` | `projects`, `use.baseURL`, `retries` |
| Cypress | `cypress.config.ts/js` | `e2e`, `component`, `baseUrl` |

**Assertion Library Detection:**

| Library | Detection Indicators | Style |
|---------|---------------------|-------|
| Jest/Vitest expect | `expect().toBe()`, `expect().toEqual()` | Matcher-based |
| Chai | `expect().to.equal()`, `should.equal()`, `assert.equal()` | BDD/TDD styles |
| Node assert | `import assert from 'assert'` | Built-in Node.js |
| pytest assert | `assert x == y` (with rewrite) | Plain Python assert |
| testify assert | `assert.Equal(t, expected, actual)` | Go testify |

**Mocking Framework Detection:**

| Framework | Detection Indicators | Ecosystem |
|-----------|---------------------|-----------|
| Jest mocks | `jest.mock()`, `jest.fn()`, `jest.spyOn()` | JavaScript/TypeScript |
| Vitest mocks | `vi.mock()`, `vi.fn()`, `vi.spyOn()` | JavaScript/TypeScript |
| Sinon | `sinon.stub()`, `sinon.spy()`, `sinon.mock()` | JavaScript/TypeScript |
| unittest.mock | `from unittest.mock import Mock, patch`, `@patch` | Python |
| pytest-mock | `mocker` fixture, `mocker.patch()` | Python |
| gomock | `mockgen`, `EXPECT()`, `ctrl.Finish()` | Go |
| testify/mock | `mock.Mock`, `On().Return()` | Go |

**Test Utility Detection:**

| Utility Type | Common Names/Patterns | Purpose |
|--------------|----------------------|---------|
| Test helpers | `test/helpers/`, `testutils/`, `test/support/` | Shared test utilities |
| Fixtures | `fixtures/`, `__fixtures__/`, `test/fixtures/` | Test data files |
| Factories | `factories/`, `*Factory.ts` | Test data generation |
| Mocks | `__mocks__/`, `mocks/`, `test/mocks/` | Mock implementations |
| Setup files | `setupTests.ts`, `conftest.py` | Global test setup |

**Coverage Tool Detection:**

| Tool | Detection Indicators | Ecosystem |
|------|---------------------|-----------|
| Istanbul/nyc | `nyc` in deps, `.nycrc`, `c8` in deps | JavaScript/TypeScript |
| Jest coverage | `--coverage` flag, `collectCoverage: true` | Jest built-in |
| Vitest coverage | `coverage` config, `@vitest/coverage-v8` or `@vitest/coverage-istanbul` | Vitest |
| coverage.py | `coverage` in deps, `.coveragerc`, `[tool.coverage]` | Python |
| pytest-cov | `pytest-cov` in deps, `--cov` flag | Python |
| go test -cover | `-cover`, `-coverprofile` flags | Go built-in |

**CI Test Configuration Detection:**

| CI Platform | Config File | Test Section Indicators |
|-------------|-------------|------------------------|
| GitHub Actions | `.github/workflows/*.yml` | `npm test`, `pytest`, `go test`, job names with "test" |
| GitLab CI | `.gitlab-ci.yml` | `test` stage, script commands |
| CircleCI | `.circleci/config.yml` | `test` jobs |
| Travis CI | `.travis.yml` | `script` section |
| Jenkins | `Jenkinsfile` | `stage('Test')` |
| Azure Pipelines | `azure-pipelines.yml` | Test tasks |

**How to Assess Coverage Gaps:**

1. **Compare source directories vs test directories:**
   - List all source modules: `Glob` for `src/**/*.ts` or equivalent
   - List all test files: `Glob` for `**/*.test.ts` or equivalent
   - Identify modules without corresponding tests

2. **Check for common untested areas:**
   - Error handling paths
   - Edge cases (null, empty, boundary values)
   - Integration points (API calls, database queries)
   - Authentication/authorization logic
   - Configuration/environment handling

3. **Look for coverage configuration:**
   - Coverage thresholds if configured
   - Excluded files/directories
   - Coverage reports in CI artifacts

### Output

Create `docs/legacy/TESTING.md` using the template at `docs/templates/analyze-codebase-testing.md`.

### Return

After creating the document, return a brief summary of testing state and maturity level.

**Special Cases:**
- If no tests exist, note this in the summary and focus recommendations on establishing testing from scratch.
- If tests exist but no coverage tooling, recommend adding coverage measurement as a P2 item.

---

### 3.6 Integrations Analyzer Agent

```markdown
## INTEGRATIONS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Analyze external integrations, services, and third-party dependencies in this codebase.

### Analysis Areas

1. **External APIs**
   - Third-party APIs called (REST, GraphQL, SOAP)
   - API client libraries used
   - Authentication methods for external services
   - Rate limiting and retry configurations

2. **Cloud Services**
   - AWS, GCP, Azure services used
   - Cloud SDK usage and configuration
   - Infrastructure dependencies (compute, storage, messaging)
   - Serverless function integrations

3. **Databases & Storage**
   - Database connections and drivers
   - Cache services (Redis, Memcached)
   - File storage (S3, GCS, Azure Blob, local)
   - Search engines (Elasticsearch, Algolia)
   - Message queues (RabbitMQ, Kafka, SQS)

4. **Third-Party SDKs**
   - Payment processors (Stripe, PayPal, Braintree)
   - Auth providers (Auth0, Okta, Firebase Auth, Clerk)
   - Analytics (Segment, Amplitude, Mixpanel, Google Analytics)
   - Email services (SendGrid, Mailchimp, SES)
   - SMS/Communication (Twilio, Vonage)
   - Monitoring (Datadog, New Relic, Sentry)
   - Other SaaS integrations

5. **Environment Dependencies**
   - Required environment variables
   - Configuration for external services
   - Secrets management approach
   - Feature flags and remote config

### How to Analyze

Use these tools to gather information:
- `Glob` for config files: `**/.env*`, `**/docker-compose*`, `**/*config*`
- `Read` to examine configuration files and SDK initialization
- `Grep` to find SDK imports, API calls, and environment variable usage
- Check package.json, requirements.txt, go.mod for service SDKs

**Cloud Provider SDK Detection:**

| Provider | SDK Packages | Config Files | Environment Indicators |
|----------|--------------|--------------|------------------------|
| AWS | `@aws-sdk/*`, `aws-sdk`, `boto3`, `aws-sdk-go` | `~/.aws/`, `aws.config.*` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` |
| GCP | `@google-cloud/*`, `google-cloud-*`, `cloud.google.com/go` | `gcloud/`, `*.json` (service account) | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT` |
| Azure | `@azure/*`, `azure-*`, `Azure.*` | `azure.config.*` | `AZURE_*` env vars |
| Firebase | `firebase`, `firebase-admin`, `@firebase/*` | `firebase.json`, `firebaserc` | `FIREBASE_*` env vars |
| Vercel | `@vercel/*`, `vercel` | `vercel.json` | `VERCEL_*` env vars |
| Netlify | `netlify-*`, `@netlify/*` | `netlify.toml` | `NETLIFY_*` env vars |

**AWS Service Detection:**

| Service | SDK Imports/Patterns | Common Env Vars |
|---------|---------------------|-----------------|
| S3 | `S3Client`, `@aws-sdk/client-s3`, `boto3.client('s3')` | `AWS_S3_BUCKET`, `S3_BUCKET` |
| DynamoDB | `DynamoDBClient`, `@aws-sdk/client-dynamodb` | `DYNAMODB_TABLE` |
| SQS | `SQSClient`, `@aws-sdk/client-sqs`, `boto3.client('sqs')` | `SQS_QUEUE_URL` |
| SNS | `SNSClient`, `@aws-sdk/client-sns` | `SNS_TOPIC_ARN` |
| Lambda | `LambdaClient`, `@aws-sdk/client-lambda` | `LAMBDA_FUNCTION_NAME` |
| SES | `SESClient`, `@aws-sdk/client-ses` | `SES_*` |
| Cognito | `CognitoIdentityProviderClient` | `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` |
| CloudWatch | `CloudWatchClient`, `CloudWatchLogsClient` | N/A |
| Secrets Manager | `SecretsManagerClient` | N/A |
| RDS | Connection strings, `RDS.*` | `DATABASE_URL`, `RDS_*` |

**GCP Service Detection:**

| Service | SDK Imports/Patterns | Common Env Vars |
|---------|---------------------|-----------------|
| Cloud Storage | `@google-cloud/storage`, `google.cloud.storage` | `GCS_BUCKET`, `GOOGLE_CLOUD_BUCKET` |
| Firestore | `@google-cloud/firestore`, `firebase-admin/firestore` | `FIRESTORE_*` |
| BigQuery | `@google-cloud/bigquery` | `BIGQUERY_*` |
| Pub/Sub | `@google-cloud/pubsub` | `PUBSUB_TOPIC` |
| Cloud Functions | Function signatures, `@google-cloud/functions-framework` | `FUNCTION_*` |
| Cloud Run | Container signatures | `CLOUD_RUN_*`, `K_SERVICE` |
| Cloud SQL | Connection patterns | `CLOUD_SQL_CONNECTION_NAME` |

**Database Driver Detection:**

| Database | Packages | Connection Patterns | Common Env Vars |
|----------|----------|---------------------|-----------------|
| PostgreSQL | `pg`, `psycopg2`, `asyncpg`, `lib/pq` | `postgres://`, `postgresql://` | `DATABASE_URL`, `POSTGRES_*`, `PG_*` |
| MySQL | `mysql2`, `mysqlclient`, `PyMySQL`, `go-sql-driver/mysql` | `mysql://` | `MYSQL_*`, `DATABASE_URL` |
| MongoDB | `mongodb`, `mongoose`, `pymongo`, `mongo-go-driver` | `mongodb://`, `mongodb+srv://` | `MONGODB_URI`, `MONGO_URL` |
| Redis | `redis`, `ioredis`, `redis-py`, `go-redis` | `redis://`, `rediss://` | `REDIS_URL`, `REDIS_HOST` |
| SQLite | `better-sqlite3`, `sqlite3` | `.db`, `.sqlite` file paths | `DATABASE_PATH` |
| Elasticsearch | `@elastic/elasticsearch`, `elasticsearch-py` | `http://localhost:9200` | `ELASTICSEARCH_URL`, `ES_*` |

**Cache Service Detection:**

| Service | Packages | Patterns |
|---------|----------|----------|
| Redis | `redis`, `ioredis`, `redis-py` | `createClient`, `Redis()` |
| Memcached | `memcached`, `pylibmc`, `memcache` | `Memcached()` |
| In-memory | `node-cache`, `lru-cache`, `cachetools` | `LRUCache`, `NodeCache` |

**Message Queue Detection:**

| Service | Packages | Patterns | Env Vars |
|---------|----------|----------|----------|
| RabbitMQ | `amqplib`, `pika`, `amqp` | `amqp://` | `RABBITMQ_URL`, `AMQP_URL` |
| Kafka | `kafkajs`, `kafka-python`, `confluent-kafka` | Kafka client initialization | `KAFKA_BROKERS`, `KAFKA_*` |
| AWS SQS | See AWS section | `SQSClient` | `SQS_QUEUE_URL` |
| GCP Pub/Sub | See GCP section | `PubSub` | `PUBSUB_*` |
| Redis Streams | `redis` with `XREAD`, `XADD` | Stream commands | See Redis |
| BullMQ | `bullmq`, `bull` | `Queue`, `Worker` | `REDIS_URL` (uses Redis) |

**Payment Processor Detection:**

| Provider | Packages | Initialization Patterns | Env Vars |
|----------|----------|------------------------|----------|
| Stripe | `stripe`, `@stripe/stripe-js` | `Stripe(apiKey)`, `new Stripe()` | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` |
| PayPal | `@paypal/checkout-server-sdk`, `paypal-rest-sdk` | PayPal client init | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` |
| Braintree | `braintree` | `braintree.BraintreeGateway` | `BRAINTREE_*` |
| Square | `square`, `@square/web-sdk` | `Client` initialization | `SQUARE_ACCESS_TOKEN` |
| Adyen | `@adyen/api-library` | Adyen client | `ADYEN_*` |

**Auth Provider Detection:**

| Provider | Packages | Patterns | Env Vars |
|----------|----------|----------|----------|
| Auth0 | `auth0`, `@auth0/auth0-react`, `@auth0/nextjs-auth0` | `Auth0Provider`, `handleAuth` | `AUTH0_SECRET`, `AUTH0_ISSUER_BASE_URL`, `AUTH0_CLIENT_ID` |
| Okta | `@okta/okta-sdk-nodejs`, `@okta/okta-react` | `OktaAuth` | `OKTA_*` |
| Clerk | `@clerk/clerk-sdk-node`, `@clerk/nextjs` | `ClerkProvider` | `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_*` |
| Firebase Auth | `firebase/auth`, `firebase-admin` | `getAuth`, `signInWith*` | `FIREBASE_*` |
| Supabase Auth | `@supabase/supabase-js` | `supabase.auth.*` | `SUPABASE_URL`, `SUPABASE_ANON_KEY` |
| NextAuth | `next-auth`, `@auth/core` | `NextAuth()`, `getServerSession` | `NEXTAUTH_SECRET`, `NEXTAUTH_URL` |
| Passport.js | `passport`, `passport-*` | `passport.use()`, strategy patterns | Provider-specific |
| JWT/Custom | `jsonwebtoken`, `jose` | `jwt.sign`, `jwt.verify` | `JWT_SECRET` |

**Analytics & Monitoring Detection:**

| Service | Packages | Initialization | Env Vars |
|---------|----------|---------------|----------|
| Segment | `analytics-node`, `@segment/analytics-next` | `Analytics()` | `SEGMENT_WRITE_KEY` |
| Amplitude | `@amplitude/analytics-node`, `amplitude-js` | `amplitude.init()` | `AMPLITUDE_API_KEY` |
| Mixpanel | `mixpanel`, `mixpanel-browser` | `mixpanel.init()` | `MIXPANEL_TOKEN` |
| PostHog | `posthog-node`, `posthog-js` | `posthog.init()` | `POSTHOG_API_KEY` |
| Google Analytics | `@google-analytics/data`, gtag.js | `gtag()` | `GA_TRACKING_ID`, `GA_MEASUREMENT_ID` |
| Datadog | `dd-trace`, `datadog-metrics` | `tracer.init()` | `DD_API_KEY`, `DD_APP_KEY` |
| New Relic | `newrelic` | `require('newrelic')` | `NEW_RELIC_LICENSE_KEY` |
| Sentry | `@sentry/node`, `@sentry/react`, `sentry-sdk` | `Sentry.init()` | `SENTRY_DSN` |
| LogRocket | `logrocket` | `LogRocket.init()` | `LOGROCKET_APP_ID` |

**Email Service Detection:**

| Service | Packages | Patterns | Env Vars |
|---------|----------|----------|----------|
| SendGrid | `@sendgrid/mail`, `sendgrid` | `sgMail.send()` | `SENDGRID_API_KEY` |
| AWS SES | See AWS section | `SESClient` | `SES_*` |
| Mailchimp/Mandrill | `@mailchimp/mailchimp_transactional` | API calls | `MAILCHIMP_API_KEY` |
| Postmark | `postmark` | `postmark.Client` | `POSTMARK_API_TOKEN` |
| Resend | `resend` | `Resend()` | `RESEND_API_KEY` |
| Nodemailer | `nodemailer` | `createTransport()` | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS` |

**SMS/Communication Detection:**

| Service | Packages | Patterns | Env Vars |
|---------|----------|----------|----------|
| Twilio | `twilio` | `Twilio(accountSid, authToken)` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| Vonage/Nexmo | `@vonage/server-sdk`, `nexmo` | `Vonage()` | `VONAGE_API_KEY`, `VONAGE_API_SECRET` |
| AWS SNS | See AWS section | SMS via SNS | `SNS_*` |
| MessageBird | `messagebird` | `messagebird()` | `MESSAGEBIRD_API_KEY` |

**Search Engine Detection:**

| Service | Packages | Patterns | Env Vars |
|---------|----------|----------|----------|
| Elasticsearch | `@elastic/elasticsearch`, `elasticsearch` | `Client({ node: ... })` | `ELASTICSEARCH_URL`, `ES_HOST` |
| Algolia | `algoliasearch`, `@algolia/client-search` | `algoliasearch(appId, apiKey)` | `ALGOLIA_APP_ID`, `ALGOLIA_API_KEY` |
| Meilisearch | `meilisearch` | `MeiliSearch({ host: ... })` | `MEILI_HOST`, `MEILI_MASTER_KEY` |
| Typesense | `typesense` | `Typesense.Client` | `TYPESENSE_*` |

**Feature Flag Detection:**

| Service | Packages | Patterns | Env Vars |
|---------|----------|----------|----------|
| LaunchDarkly | `launchdarkly-node-server-sdk` | `LDClient.init()` | `LAUNCHDARKLY_SDK_KEY` |
| Unleash | `unleash-client` | `Unleash.initialize()` | `UNLEASH_*` |
| Split | `@splitsoftware/splitio` | `SplitFactory` | `SPLIT_API_KEY` |
| Flagsmith | `flagsmith-nodejs` | `flagsmith.init()` | `FLAGSMITH_*` |
| ConfigCat | `configcat-node` | `configcat.getClient()` | `CONFIGCAT_SDK_KEY` |
| PostHog | See Analytics | Feature flag methods | See PostHog |

**Environment Variable Detection:**

Search for environment variable usage patterns:

| Ecosystem | Patterns to Search |
|-----------|-------------------|
| Node.js | `process.env.VAR_NAME`, `process.env['VAR_NAME']` |
| Python | `os.environ['VAR']`, `os.getenv('VAR')`, `environ.get('VAR')` |
| Go | `os.Getenv("VAR")`, `os.LookupEnv("VAR")` |
| .NET | `Environment.GetEnvironmentVariable("VAR")`, `Configuration["VAR"]` |

**Configuration File Locations:**

| File | Purpose | Common Integrations |
|------|---------|---------------------|
| `.env`, `.env.local`, `.env.production` | Environment variables | All services |
| `docker-compose.yml` | Container services | Databases, Redis, etc. |
| `config/*.json`, `config/*.yaml` | App configuration | Service URLs, API keys |
| `serverless.yml` | Serverless config | AWS Lambda, API Gateway |
| `vercel.json`, `netlify.toml` | Deployment config | Platform services |
| `firebase.json` | Firebase config | Firebase services |

**API Call Pattern Detection:**

Search for HTTP client usage indicating external API calls:

| Library | Patterns to Search |
|---------|-------------------|
| fetch | `fetch('https://api.`, `fetch(` with external URLs |
| axios | `axios.get('https://`, `axios.create({ baseURL:` |
| got | `got('https://`, `got.extend({ prefixUrl:` |
| requests (Python) | `requests.get('https://`, `requests.post(` |
| httpx (Python) | `httpx.get(`, `httpx.AsyncClient` |
| http.Client (Go) | `http.Get(`, `http.NewRequest` |
| RestSharp (.NET) | `RestClient`, `RestRequest` |

### Output

Create `docs/legacy/INTEGRATIONS.md` using the template at `docs/templates/analyze-codebase-integrations.md`.

### Return

After creating the document, return a brief summary of integrations found.

**Special Cases:**
- If no external integrations detected, note the application is self-contained.
- If only database integrations, focus on the database layer and note this as a characteristic.

---

### 3.7 Concerns Analyzer Agent

```markdown
## CONCERNS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]
User pain points: [if provided in Q&A]

### Exclusions
**IMPORTANT:** Exclude from analysis:
- `.claude/` directory (tooling, not application code)
- All paths matching `.gitignore` patterns (node_modules, __pycache__, dist, build, .venv, etc.)
- Focus only on actual application source code

### Objective
Identify technical debt, code smells, and areas of concern in this codebase. Focus on actionable findings that impact maintainability, reliability, and developer productivity.

### Analysis Areas

1. **Code Complexity**
   - Large files (>500 lines)
   - Complex functions (high cyclomatic complexity indicators)
   - Deep nesting (>4 levels)
   - Long parameter lists (>5 parameters)
   - Long functions (>50 lines)

2. **Technical Debt Markers**
   - TODO comments
   - FIXME comments
   - HACK comments
   - XXX comments
   - Deprecated usage warnings
   - @deprecated annotations

3. **Dependency Health**
   - Outdated dependencies (major versions behind)
   - Security vulnerabilities (if detectable)
   - Unused dependencies
   - Duplicate dependencies
   - Deprecated packages

4. **Code Smells**
   - Duplicate code patterns
   - Dead code (unused exports, unreachable code)
   - Inconsistent patterns
   - Magic numbers/strings
   - Hardcoded values that should be config

5. **Architectural Concerns**
   - Circular dependencies
   - Tight coupling indicators
   - Missing abstractions
   - God classes/modules (doing too much)
   - Leaky abstractions

6. **User-Reported Issues**
   - If user provided pain points in Q&A, investigate those specifically

### How to Analyze

Use these tools to gather information:
- `Bash` with `find . -name "*.ts" -exec wc -l {} \;` or similar for file sizes
- `Grep` to search for TODO/FIXME/HACK patterns
- `Read` to examine package.json, requirements.txt for dependency versions
- `Glob` to find patterns indicating code smells
- Sample problematic files to understand the nature of concerns

**Code Complexity Detection:**

| Metric | Threshold | How to Detect | Risk Level |
|--------|-----------|---------------|------------|
| File size | >500 lines | `wc -l` on source files | Medium |
| File size | >1000 lines | `wc -l` on source files | High |
| Function length | >50 lines | Manual inspection or linter output | Medium |
| Function length | >100 lines | Manual inspection or linter output | High |
| Nesting depth | >4 levels | Look for deeply nested if/for/while | Medium |
| Parameter count | >5 params | Grep for function signatures | Medium |
| Class size | >20 methods | Manual inspection of class files | Medium |

**Finding Large Files by Ecosystem:**

| Ecosystem | Command Pattern | File Extensions |
|-----------|-----------------|-----------------|
| TypeScript/JavaScript | `find . -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx"` then `wc -l` | `.ts`, `.tsx`, `.js`, `.jsx` |
| Python | `find . -name "*.py"` then `wc -l` | `.py` |
| Go | `find . -name "*.go"` then `wc -l` | `.go` |
| C#/.NET | `find . -name "*.cs"` then `wc -l` | `.cs` |

**Technical Debt Marker Detection:**

| Marker | Grep Pattern | Severity | Action Implied |
|--------|--------------|----------|----------------|
| TODO | `TODO:?\s*`, `@todo` | Low | Work to be done, not urgent |
| FIXME | `FIXME:?\s*`, `@fixme` | Medium | Known bug or issue to fix |
| HACK | `HACK:?\s*`, `@hack` | High | Workaround that needs proper solution |
| XXX | `XXX:?\s*` | Medium | Attention needed |
| BUG | `BUG:?\s*`, `@bug` | High | Known bug |
| OPTIMIZE | `OPTIMIZE:?\s*` | Low | Performance improvement needed |
| REFACTOR | `REFACTOR:?\s*` | Low | Code needs restructuring |
| DEPRECATED | `@deprecated`, `# deprecated`, `// deprecated` | Medium | Code should be removed/replaced |
| TEMP | `TEMP:?\s*`, `TEMPORARY` | High | Temporary code that should be removed |
| REMOVEME | `REMOVEME`, `REMOVE_ME`, `DELETE_ME` | High | Code marked for deletion |

**Deprecated Usage Detection:**

| Ecosystem | Indicators | How to Find |
|-----------|------------|-------------|
| TypeScript/JavaScript | `@deprecated` JSDoc, console warnings | Grep for `@deprecated`, check linter output |
| Python | `warnings.warn("deprecated")`, `@deprecated` decorator | Grep for deprecation patterns |
| Go | `// Deprecated:` comment convention | Grep for deprecation comments |

**Dependency Health Detection:**

| Ecosystem | How to Check | What to Look For |
|-----------|--------------|------------------|
| Node.js | `npm outdated`, check package.json vs npm registry | Major version differences, deprecated packages |
| Python | `pip list --outdated`, compare pyproject.toml versions | Packages multiple major versions behind |
| Go | `go list -m -u all`, check go.mod | Modules with available updates |

**Dependency Age Indicators:**

| Risk Level | Condition | Example |
|------------|-----------|---------|
| Critical | Security advisory exists | Known CVE in package version |
| High | >2 major versions behind | Using React 16 when 18 is current |
| Medium | >1 major version behind | Using Express 3 when 4 is current |
| Low | Minor/patch updates available | Normal maintenance updates |

**Unused Dependency Detection:**

| Ecosystem | Detection Method | Tools/Patterns |
|-----------|------------------|----------------|
| Node.js | No imports found for package | `depcheck`, grep for package imports |
| Python | No imports in codebase | `vulture`, grep for module imports |
| Go | Compiler enforces (automatic) | `go mod tidy` shows removals |

**Code Smell Detection Patterns:**

| Smell | Detection Pattern | Risk |
|-------|-------------------|------|
| Magic numbers | Numeric literals in logic (not 0, 1, -1) | Medium |
| Magic strings | Repeated string literals not in constants | Medium |
| Hardcoded URLs | `http://`, `https://` in source code | Medium |
| Hardcoded IPs | IP address patterns in source | High |
| Hardcoded credentials | Password/key patterns in source | Critical |
| Dead imports | Import statements for unused modules | Low |
| Commented code blocks | Large sections of commented-out code | Low |
| Console/print statements | Debug statements in production code | Low |
| Empty catch blocks | `catch {}` or `except: pass` | Medium |
| Identical code blocks | Repeated code across files | Medium |

**Magic Number/String Detection:**

| Type | Grep Patterns | Exceptions |
|------|---------------|------------|
| Magic numbers | `[^0-9][2-9][0-9]*[^0-9]` in logic | Array indices, common values (100, 1000), port numbers in config |
| Hardcoded strings | Repeated identical strings in multiple files | Standard strings like "utf-8", HTTP methods |
| Hardcoded URLs | `https?://[a-zA-Z]` in source (not config) | Docs, comments, tests |
| Hardcoded paths | Absolute paths in source | Config files intended for paths |

**Console/Debug Statement Detection:**

| Ecosystem | Patterns to Find | Should Be |
|-----------|------------------|-----------|
| JavaScript/TypeScript | `console.log`, `console.debug`, `console.warn`, `debugger` | Removed or logger |
| Python | `print(`, `pdb.set_trace()`, `breakpoint()` | Removed or logger |
| Go | `fmt.Println`, `fmt.Printf` (in non-main) | `log` package |

**Architectural Concern Detection:**

| Concern | Detection Method | Indicators |
|---------|------------------|------------|
| Circular dependencies | Import analysis | A imports B imports A |
| God class/module | File size + method count | >1000 lines, >20 methods/functions |
| Tight coupling | Import frequency | One module imported by >50% of files |
| Missing abstraction | Duplicate patterns | Same code structure in multiple places |
| Leaky abstraction | Implementation details exposed | Internal types/functions in public API |
| Feature envy | Cross-module data access | Module frequently accesses another's internals |
| Shotgun surgery | Related changes scattered | Similar changes needed across many files |

**Circular Dependency Detection:**

| Ecosystem | Detection Method | Tools |
|-----------|------------------|-------|
| TypeScript/JavaScript | Import graph analysis | `madge --circular`, `dpdm` |
| Python | Import tracing | `pydeps`, manual import analysis |
| Go | Compiler catches (built-in) | Compiler errors on circular imports |

**God Class/Module Indicators:**

| Indicator | Threshold | Description |
|-----------|-----------|-------------|
| File lines | >500-1000 | Too much code in one place |
| Method/function count | >15-20 | Class doing too many things |
| Import count | >15-20 | Depends on too many things |
| Public method count | >10 | API surface too large |
| Mixed responsibilities | N/A | Unrelated functionality in same class |

**Security Concern Detection:**

| Concern | Patterns to Search | Risk Level |
|---------|-------------------|------------|
| Hardcoded secrets | `password`, `secret`, `api_key`, `token` in source | Critical |
| SQL injection risk | String concatenation in SQL queries | Critical |
| Unsafe deserialization | `pickle.loads`, `eval()`, `exec()` | Critical |
| Path traversal risk | User input in file paths | High |
| XSS risk | Unescaped user content in HTML | High |
| Insecure randomness | `Math.random()` for security | Medium |
| Missing input validation | Direct use of user input | Medium |

**Hardcoded Secret Patterns:**

| Pattern Type | Example Patterns |
|--------------|------------------|
| AWS Keys | `AKIA[0-9A-Z]{16}` |
| Generic API Key | `api[_-]?key.*=.*['"][a-zA-Z0-9]{20,}` |
| Generic Secret | `secret.*=.*['"][a-zA-Z0-9]{8,}` |
| Generic Password | `password.*=.*['"].+['"]` |
| Private Key | `-----BEGIN.*PRIVATE KEY-----` |
| Generic Token | `token.*=.*['"][a-zA-Z0-9]{20,}` |
| JWT | `eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*` |
| Connection strings | `(mysql|postgres|mongodb)://[^:]+:[^@]+@` |

**How to Prioritize Findings:**

| Priority | Criteria | Examples |
|----------|----------|----------|
| P1 Critical | Security risk, data loss risk, production impact | Hardcoded secrets, SQL injection, missing error handling in critical paths |
| P2 Important | Maintainability, reliability, developer productivity | Large files, missing tests for critical code, circular dependencies |
| P3 Nice-to-have | Code quality, consistency, minor cleanup | Magic numbers, console logs, minor code smells |

### Output

Create `docs/legacy/CONCERNS.md` using the template at `docs/templates/analyze-codebase-concerns.md`.

### Return

After creating the document, return a brief summary including top concern and tech debt level.

**Special Cases:**
- If no significant concerns found, note the codebase shows good technical health.
- If user provided pain points, give those areas special attention.

---

## Phase 4: Spawn Synthesizer Agent (Sequential)

**CRITICAL: Wait for ALL 7 analysis agents to complete before spawning the synthesizer.**

### 4.1 Next Steps Synthesizer Agent

```markdown
## NEXT STEPS SYNTHESIZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Objective
Synthesize all 7 analysis documents into a prioritized improvement plan.

### Prerequisites
The following documents must exist before you begin:
- `docs/legacy/STACK.md`
- `docs/legacy/ARCHITECTURE.md`
- `docs/legacy/STRUCTURE.md`
- `docs/legacy/CONVENTIONS.md`
- `docs/legacy/TESTING.md`
- `docs/legacy/INTEGRATIONS.md`
- `docs/legacy/CONCERNS.md`

### Your Task

1. **Read all 7 documents** to understand the full picture
2. **Synthesize a summary** of the project's current state
3. **Identify gaps** for SDLC adoption
4. **Prioritize improvements** using P1/P2/P3 classification
5. **Provide SDLC workflow guidance**

### Priority Definitions

- **P1 (Critical):** Blockers for safe development. Security issues, missing tests for critical paths, build problems.
- **P2 (Important):** Significant improvements for productivity. Linting, type checking, documentation gaps.
- **P3 (Nice to Have):** Polish and optimization. Code cleanup, minor refactoring, style consistency.

### How to Analyze

Use the `Read` tool to examine each document systematically. Cross-reference findings to identify patterns.

**Step 1: Read All Documents**

```
Read docs/legacy/STACK.md
Read docs/legacy/ARCHITECTURE.md
Read docs/legacy/STRUCTURE.md
Read docs/legacy/CONVENTIONS.md
Read docs/legacy/TESTING.md
Read docs/legacy/INTEGRATIONS.md
Read docs/legacy/CONCERNS.md
```

**Step 2: Cross-Reference Analysis**

Look for patterns that span multiple documents:

| Cross-Reference | Documents to Compare | What to Look For |
|-----------------|---------------------|------------------|
| Untested critical paths | ARCHITECTURE + TESTING | API endpoints, auth flows, data mutations without tests |
| Inconsistent conventions | CONVENTIONS + STRUCTURE | Naming patterns that don't match directory organization |
| Integration risks | INTEGRATIONS + CONCERNS | External dependencies flagged as concerns |
| Stack misalignment | STACK + CONVENTIONS | Build tools that don't match linting/formatting setup |
| Architecture debt | ARCHITECTURE + CONCERNS | Coupling patterns, missing abstraction layers |

**Step 3: Priority Classification Criteria**

Use these concrete criteria to classify items:

**P1 (Critical) Indicators:**
- TESTING.md shows "No tests found" or <30% coverage on critical paths
- CONCERNS.md lists security vulnerabilities or data integrity risks
- STACK.md shows outdated dependencies with known CVEs
- ARCHITECTURE.md reveals no error handling patterns
- Build/deploy broken or unreliable (from any analysis)

**P2 (Important) Indicators:**
- CONVENTIONS.md shows no linting configured
- TESTING.md shows tests exist but no integration/e2e tests
- STRUCTURE.md reveals inconsistent organization patterns
- CONCERNS.md lists moderate technical debt (TODO/FIXME count >20)
- INTEGRATIONS.md shows undocumented external dependencies

**P3 (Nice to Have) Indicators:**
- CONVENTIONS.md shows minor style inconsistencies
- STRUCTURE.md suggests reorganization for clarity
- TESTING.md shows good coverage but missing edge cases
- CONCERNS.md lists small code smells (long files <5)

**Step 4: Quick Wins Identification**

A quick win meets ALL these criteria:
1. **Low effort:** Can be done in <1 hour
2. **Low risk:** No behavior change, no dependencies affected
3. **Immediate value:** Visible improvement right away

Common quick wins by document:
- CONVENTIONS.md: Add .editorconfig, configure prettier
- TESTING.md: Add test script to package.json if missing
- STRUCTURE.md: Create missing standard directories (docs/, test/)
- CONCERNS.md: Fix obvious typos in TODO comments, remove dead code

**Step 5: SDLC Gap Analysis**

The SDLC workflow requires certain foundations. Check for these gaps:

| SDLC Requirement | Source Document | Gap Indicator |
|------------------|-----------------|---------------|
| Test infrastructure | TESTING.md | No test framework configured |
| Lint/format pipeline | CONVENTIONS.md | No linter/formatter in package.json/pyproject.toml |
| Type safety | STACK.md | JavaScript without TypeScript, Python without type hints |
| Clear architecture | ARCHITECTURE.md | No identifiable patterns, spaghetti data flow |
| Organized structure | STRUCTURE.md | Mixed concerns in directories, no clear entry points |
| Documented integrations | INTEGRATIONS.md | Environment variables without documentation |

### Output

Create `docs/legacy/NEXT-STEPS.md` using the template at `docs/templates/analyze-codebase-next-steps.md`.

### Return

After creating the document, return the top 3 priorities and recommended first action.

---

## Phase 5: Summary to User

After all 8 agents complete, summarize for the user:

```
## Analysis Complete

I've analyzed your codebase and created 8 documents in `docs/legacy/`:

| Document | Summary |
|----------|---------|
| STACK.md | [1-line from agent] |
| ARCHITECTURE.md | [1-line from agent] |
| STRUCTURE.md | [1-line from agent] |
| CONVENTIONS.md | [1-line from agent] |
| TESTING.md | [1-line from agent] |
| INTEGRATIONS.md | [1-line from agent] |
| CONCERNS.md | [1-line from agent] |
| NEXT-STEPS.md | [1-line from agent] |

### Key Findings

[Synthesize the most important points from NEXT-STEPS.md]

### Recommended Next Steps

1. Review `docs/legacy/NEXT-STEPS.md` for the full prioritized improvement plan
2. Pick a P1 item and run `/discover` to start planning the improvement
3. Follow the SDLC workflow for structured implementation

**Ready to start improving? Run `/discover` and describe your first improvement.**
```

---

## Error Handling

### If an Agent Fails

- Other agents should continue
- Note which analysis failed in the summary
- Partial results are still valuable

### If Directory Creation Fails

- Alert user about permission issues
- Do not proceed with analysis

---

## Important Rules

1. **Q&A is self-executed** - you conduct the optional questions yourself
2. **Analysis is delegated** - spawn agents for all analysis work
3. **7 agents run in parallel** - use multiple Task invocations in one message
4. **Synthesizer runs after** - wait for all 7 before spawning synthesizer
5. **Non-destructive** - never modify source code
6. **All 8 documents required** - verify all exist before summarizing
7. **Respect exclusions** - always exclude `.claude/` and gitignored paths from analysis

---

## Topic/Context for Analysis

$ARGUMENTS
