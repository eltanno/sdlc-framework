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
   - Node.js, Python, Go, Java version requirements
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
| Java | `pom.xml` (maven.compiler.source), `build.gradle` (sourceCompatibility) |
| Rust | `Cargo.toml` (rust-version), `rust-toolchain.toml` |

**Framework Detection Patterns:**
- React: Look for `react` in package.json dependencies, `jsx`/`tsx` files
- Express/Fastify: Look in package.json, trace from main entry point
- Django/FastAPI: Look in pyproject.toml/requirements.txt, find main app module
- Gin/Echo: Look in go.mod, find main.go imports

### Output

Create `docs/legacy/STACK.md` with this structure:

```markdown
# Stack Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name from config or directory name]

## Summary

[2-3 sentence overview of the technology stack]

## Findings

### Primary Languages
| Language | Version | Proportion | Source |
|----------|---------|------------|--------|
| [Language] | [version] | [%] | [where version was found] |

### Frameworks
| Framework | Version | Purpose |
|-----------|---------|---------|
| [Framework] | [version] | [purpose] |

### Runtime Environment
| Runtime | Version | Notes |
|---------|---------|-------|
| [e.g., Node.js] | [version] | [requirements source] |

### Build Tools
| Tool | Purpose |
|------|---------|
| [Tool] | [purpose] |

### Package Manager
- Primary: [npm/yarn/pip/poetry/go mod]
- Lock file: [yes/no]

### Development Tools
| Tool | Purpose | Configuration |
|------|---------|---------------|
| [Linter/Formatter] | [purpose] | [config file] |

## Recommendations

- [Recommendation based on findings]

---
*Generated by `/analyze-codebase`*
```

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
| Java | `Application.java`, `Main.java`, `*Application.java` |

### Output

Create `docs/legacy/ARCHITECTURE.md` with this structure:

```markdown
# Architecture Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of architectural approach]

## Findings

### System Type
| Aspect | Value | Evidence |
|--------|-------|----------|
| Architecture Style | [Monolith/Microservices/Serverless/etc] | [what indicates this] |
| Frontend/Backend | [Split/Unified/N/A] | [directory structure or config] |
| Entry Point(s) | [file path(s)] | [how determined] |

### Design Patterns
| Pattern | Location | Description |
|---------|----------|-------------|
| [Pattern name] | [directories/files] | [how it's implemented] |

### Data Flow
```
[Request] → [Entry Point] → [Handler/Controller] → [Service] → [Data Layer] → [Response]
```

**Data Flow Description:**
1. **Input:** [How data enters - HTTP, events, CLI, etc.]
2. **Processing:** [Key transformation/business logic layers]
3. **Output:** [How data exits - responses, events, files, etc.]

### Data Layer
| Component | Technology | Details |
|-----------|------------|---------|
| Database | [PostgreSQL/MongoDB/etc] | [connection string location, schema files] |
| ORM/Query | [Prisma/TypeORM/etc or "Raw SQL"] | [config file, model locations] |
| Migrations | [Tool or "None"] | [migration directory if present] |
| Caching | [Redis/Memcached/None] | [if applicable] |

### API Structure
| Attribute | Value | Notes |
|-----------|-------|-------|
| Style | [REST/GraphQL/gRPC/etc] | [library used] |
| Base Path | [/api, /graphql, etc] | [where defined] |
| Auth Pattern | [JWT/Session/OAuth/None] | [middleware location] |

**Endpoint Organization:**
- [Description of how routes/endpoints are organized]
- [Key route files and their responsibilities]

### Component Communication
| Communication Type | Where Used | Pattern |
|-------------------|------------|---------|
| [Direct calls/Events/Queue/etc] | [between what components] | [sync/async, library used] |

### Module Boundaries
| Module/Service | Responsibility | Dependencies |
|----------------|---------------|--------------|
| [module name] | [what it does] | [what it depends on] |

## Recommendations

- [Architectural recommendations based on findings]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
ARCHITECTURE ANALYSIS COMPLETE
Document: docs/legacy/ARCHITECTURE.md
Architecture: [1-2 sentence summary]
```
```

---

### 3.3 Structure Analyzer Agent

```markdown
## STRUCTURE ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

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
| Java | `*Application.java`, `Main.java`; check `pom.xml` or `build.gradle` for main class |
| Ruby | `config.ru`, `app.rb`, `Rakefile`; Rails: `config/application.rb` |
| Rust | `src/main.rs` (binary), `src/lib.rs` (library) |
| .NET | `Program.cs`, `Startup.cs`; check `.csproj` for entry point |

**Configuration File Detection:**

| File | Purpose | Ecosystem |
|------|---------|-----------|
| `package.json` | Dependencies, scripts, metadata | Node.js |
| `tsconfig.json` | TypeScript compiler options | TypeScript |
| `pyproject.toml`, `setup.py`, `setup.cfg` | Python package config | Python |
| `requirements.txt`, `Pipfile` | Python dependencies | Python |
| `go.mod`, `go.sum` | Go module definition | Go |
| `Cargo.toml` | Rust package config | Rust |
| `pom.xml`, `build.gradle` | Java build config | Java |
| `Gemfile` | Ruby dependencies | Ruby |
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

Create `docs/legacy/STRUCTURE.md` with this structure:

```markdown
# Structure Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of project structure]

## Findings

### Top-Level Layout
```
project/
├── [dir]/ - [purpose]
├── [dir]/ - [purpose]
└── [file] - [purpose]
```

### Source Organization
| Attribute | Value | Evidence |
|-----------|-------|----------|
| Pattern | [feature-based/layer-based/domain-driven/etc] | [what indicates this] |
| Main Source Directory | [path] | [e.g., src/, lib/, app/] |
| Shared Code Location | [path or "none"] | [utils/, common/, shared/] |
| Module Boundaries | [clear/unclear/none] | [how modules are separated] |

**Directory Purpose Map:**
| Directory | Purpose | Key Contents |
|-----------|---------|--------------|
| [dir/] | [purpose] | [notable files or subdirectories] |

### Entry Points
| Type | Path | Purpose |
|------|------|---------|
| Main Application | [file path] | [what it starts] |
| CLI | [file path or "N/A"] | [command-line interface] |
| Tests | [entry approach] | [how tests are run] |
| Build | [entry approach] | [how builds are triggered] |

### Configuration Files
| File | Purpose | Key Settings |
|------|---------|--------------|
| [file] | [purpose] | [notable configuration] |

### Monorepo Structure
[If applicable - otherwise state "Not a monorepo"]
| Package/App | Path | Purpose |
|-------------|------|---------|
| [name] | [path] | [purpose] |

### Documentation
| Location | Type | Coverage |
|----------|------|----------|
| [path] | [README/API docs/guides] | [what's documented] |

### Notable Patterns
- [Pattern 1]: [description of any unique structural choices]
- [Pattern 2]: [description]

## Recommendations

- [Structure recommendations based on findings]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
STRUCTURE ANALYSIS COMPLETE
Document: docs/legacy/STRUCTURE.md
Organization: [1-2 sentence summary]
```
```

---

### 3.4 Conventions Analyzer Agent

```markdown
## CONVENTIONS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

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
| Rust | Clippy | rustfmt | `clippy.toml`, `rustfmt.toml`, `.rustfmt.toml` |
| Java | Checkstyle, SpotBugs | google-java-format | `checkstyle.xml`, `spotbugs-exclude.xml` |
| Ruby | RuboCop | RuboCop | `.rubocop.yml` |

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
| PascalCase | `UserProfile.tsx`, `ApiClient.java` | React components, Java classes |
| snake_case | `user_profile.py`, `api_client.rb` | Python, Ruby modules |
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
| Rustdoc | `///` or `//!` comments | Rust |
| Javadoc | `/** ... */` with `@param`, `@return` | Java |

**Git Convention Detection:**
- Run `git log --oneline -20` to see recent commit messages
- Look for patterns: Conventional Commits (`feat:`, `fix:`), ticket references (`[JIRA-123]`), imperative mood
- Check for `.github/PULL_REQUEST_TEMPLATE.md` or `.gitlab/merge_request_templates/`
- Check for `.gitmessage` or commit-msg hooks in `.husky/` or `.git/hooks/`

### Output

Create `docs/legacy/CONVENTIONS.md` with this structure:

```markdown
# Conventions Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of code conventions and tooling maturity]

## Findings

### Naming Conventions

| Element | Convention | Examples | Consistency |
|---------|------------|----------|-------------|
| Variables | [camelCase/snake_case/etc] | [example names found] | [High/Medium/Low] |
| Functions | [convention] | [example names found] | [High/Medium/Low] |
| Classes/Types | [convention] | [example names found] | [High/Medium/Low] |
| Constants | [convention] | [example names found] | [High/Medium/Low] |
| Files | [convention] | [example patterns] | [High/Medium/Low] |

**Notable Patterns:**
- [Any unique naming conventions observed]
- [Prefix/suffix patterns used]

### Linting & Formatting

**Linter Configuration:**
| Tool | Config File | Key Rules |
|------|-------------|-----------|
| [ESLint/Ruff/etc] | [file path] | [notable non-default rules] |

**Formatter Configuration:**
| Tool | Config File | Key Settings |
|------|-------------|--------------|
| [Prettier/Black/etc] | [file path] | [notable settings like line length, quotes] |

**Type Checking:**
| Tool | Config File | Strictness |
|------|-------------|------------|
| [TypeScript/mypy/etc] | [file path] | [strict/moderate/loose] |

**Automation:**
- Pre-commit hooks: [yes/no - tool if yes]
- CI lint checks: [yes/no - where configured]
- Editor integration: [.editorconfig present? VS Code settings?]

### Code Organization

**Import Style:**
| Aspect | Convention | Enforced By |
|--------|------------|-------------|
| Grouping | [external → internal → relative / alphabetical / none] | [ESLint rule or "not enforced"] |
| Path style | [absolute / relative / mixed] | [tsconfig paths / pyproject / none] |
| Default vs named | [preference observed] | [not typically enforced] |

**Export Patterns:**
- [Barrel exports (index files) / direct exports / mixed]
- [Default exports vs named exports preference]

**Module Structure:**
- [How files are organized within directories]
- [Co-location patterns (tests with source, styles with components)]

### Documentation Style

| Aspect | Convention | Coverage |
|--------|------------|----------|
| Format | [JSDoc/docstrings/Godoc/etc] | [High/Medium/Low/None] |
| Public APIs | [documented/partial/undocumented] | [percentage estimate] |
| Internal code | [documented/partial/undocumented] | [percentage estimate] |
| README quality | [comprehensive/basic/minimal/missing] | N/A |

**Comment Patterns:**
- TODO count: [approximate count]
- FIXME count: [approximate count]
- Inline comment style: [description of how comments are used]

### Git Conventions

**Commit Messages:**
| Aspect | Observed Pattern | Examples |
|--------|------------------|----------|
| Style | [Conventional Commits/Imperative/Free-form] | [sample messages] |
| Ticket references | [yes - format / no] | [example if yes] |
| Co-author tags | [yes/no] | [example if yes] |

**Branch Naming:**
- Pattern: [feature/xxx, fix/xxx, etc. or "not determinable"]

**PR/MR Templates:**
- Template present: [yes - path / no]
- Template quality: [comprehensive/basic/none]

### EditorConfig / IDE Settings

| Setting | Value | File |
|---------|-------|------|
| Indent style | [spaces/tabs] | [.editorconfig or inferred] |
| Indent size | [2/4/etc] | [source] |
| End of line | [lf/crlf/auto] | [source] |
| Trim trailing whitespace | [yes/no] | [source] |
| Final newline | [yes/no] | [source] |

## Consistency Assessment

| Area | Consistency | Notes |
|------|-------------|-------|
| Naming | [High/Medium/Low] | [brief note] |
| Formatting | [High/Medium/Low] | [brief note] |
| Documentation | [High/Medium/Low] | [brief note] |
| Imports | [High/Medium/Low] | [brief note] |

**Overall Convention Maturity:** [Mature/Developing/Minimal]

## Recommendations

- [Recommendation 1: specific, actionable improvement]
- [Recommendation 2: specific, actionable improvement]
- [Recommendation 3: specific, actionable improvement]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
CONVENTIONS ANALYSIS COMPLETE
Document: docs/legacy/CONVENTIONS.md
Style: [1-2 sentence summary including primary language conventions and tooling]
Convention Maturity: [Mature/Developing/Minimal]
```
```

---

### 3.5 Testing Analyzer Agent

```markdown
## TESTING ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

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

- Find test directories and files
- Read test configuration (jest.config, pytest.ini, etc.)
- Sample test files to understand patterns
- Look for coverage reports or config

### Output

Create `docs/legacy/TESTING.md` with this structure:

```markdown
# Testing Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of testing state]

## Findings

### Test Framework
- Unit: [framework]
- Integration: [framework or "none"]
- E2E: [framework or "none"]

### Test Organization
- Location: [where tests live]
- Naming: [file naming pattern]
- Helpers: [utility location if any]

### Test Patterns
- Assertions: [style]
- Mocking: [approach]
- Fixtures: [approach]

### Coverage Assessment
**Well Tested:**
- [area/module]
- [area/module]

**Gaps Identified:**
- [area/module lacking tests]
- [area/module lacking tests]

### CI/CD
- Test Command: [command]
- CI Integration: [yes/no and details]
- Coverage Reporting: [yes/no]

## Recommendations

- [Testing recommendations]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
TESTING ANALYSIS COMPLETE
Document: docs/legacy/TESTING.md
Testing: [1-2 sentence summary]
```

**Note:** If no tests exist, explicitly state "No tests found" and focus recommendations on establishing testing.
```

---

### 3.6 Integrations Analyzer Agent

```markdown
## INTEGRATIONS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]

### Objective
Analyze external integrations, services, and third-party dependencies.

### Analysis Areas

1. **External APIs**
   - Third-party APIs called
   - API client libraries used
   - Authentication methods for external services

2. **Cloud Services**
   - AWS, GCP, Azure services
   - Cloud SDK usage
   - Infrastructure dependencies

3. **Databases & Storage**
   - Database connections
   - Cache services (Redis, Memcached)
   - File storage (S3, GCS, local)

4. **Third-Party SDKs**
   - Payment processors (Stripe, PayPal)
   - Auth providers (Auth0, Okta)
   - Analytics (Segment, Amplitude)
   - Other SaaS integrations

5. **Environment Dependencies**
   - Required environment variables
   - Configuration for external services
   - Secrets management

### How to Analyze

- Search for API client instantiation
- Look for SDK imports
- Examine environment variable usage
- Check for service configuration files

### Output

Create `docs/legacy/INTEGRATIONS.md` with this structure:

```markdown
# Integrations Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of external integrations]

## Findings

### External APIs
| Service | Purpose | Auth Method |
|---------|---------|-------------|
| [service] | [purpose] | [method] |

### Cloud Services
- Provider: [AWS/GCP/Azure/none]
- Services Used:
  - [service]: [purpose]

### Databases & Storage
- Primary Database: [type and details]
- Cache: [type or "none"]
- File Storage: [type or "local"]

### Third-Party SDKs
| SDK | Purpose | Version |
|-----|---------|---------|
| [sdk] | [purpose] | [version] |

### Environment Dependencies
| Variable | Purpose | Required |
|----------|---------|----------|
| [var] | [purpose] | [yes/no] |

## Recommendations

- [Integration recommendations]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
INTEGRATIONS ANALYSIS COMPLETE
Document: docs/legacy/INTEGRATIONS.md
Integrations: [1-2 sentence summary]
```

**Note:** If no external integrations detected, state "No external integrations detected" clearly.
```

---

### 3.7 Concerns Analyzer Agent

```markdown
## CONCERNS ANALYZER AGENT

### Context
Project directory: [current working directory]
User context: [answers from Q&A, or "No user context provided"]
User pain points: [if provided in Q&A]

### Objective
Identify technical debt, code smells, and areas of concern in this codebase.

### Analysis Areas

1. **Code Complexity**
   - Large files (>500 lines)
   - Complex functions (high cyclomatic complexity indicators)
   - Deep nesting
   - Long parameter lists

2. **Technical Debt Markers**
   - TODO comments
   - FIXME comments
   - HACK comments
   - Deprecated usage

3. **Dependency Health**
   - Outdated dependencies
   - Security vulnerabilities (if detectable)
   - Unused dependencies
   - Duplicate dependencies

4. **Code Smells**
   - Duplicate code patterns
   - Dead code
   - Inconsistent patterns
   - Magic numbers/strings

5. **Architectural Concerns**
   - Circular dependencies
   - Tight coupling indicators
   - Missing abstractions
   - God classes/modules

6. **User-Reported Issues**
   - If user provided pain points in Q&A, investigate those specifically

### How to Analyze

- Find large files: `wc -l` or analyze file sizes
- Search for TODO/FIXME/HACK: `Grep` for these patterns
- Check dependency age: package.json, requirements.txt versions
- Look for obvious code smells through sampling

### Output

Create `docs/legacy/CONCERNS.md` with this structure:

```markdown
# Concerns Analysis

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Summary

[2-3 sentence overview of technical debt state]

## Findings

### Code Complexity
**Large Files (>500 lines):**
| File | Lines | Concern |
|------|-------|---------|
| [file] | [lines] | [why it's concerning] |

**Complex Areas:**
- [area]: [concern]

### Technical Debt Markers
**TODOs:** [count]
| Location | Content |
|----------|---------|
| [file:line] | [TODO text] |

**FIXMEs:** [count]
| Location | Content |
|----------|---------|
| [file:line] | [FIXME text] |

**HACKs:** [count]
| Location | Content |
|----------|---------|
| [file:line] | [HACK text] |

### Dependency Health
- Outdated: [count or "none detected"]
- Security Concerns: [count or "none detected"]
- Notable Issues:
  - [package]: [issue]

### Code Smells
- [smell]: [location and description]

### Architectural Concerns
- [concern]: [description]

### User-Reported Pain Points
[If user provided pain points, analyze those specifically]
- [pain point]: [findings]

## Priority Assessment

### Critical (Address Immediately)
- [issue]: [why critical]

### Important (Address Soon)
- [issue]: [why important]

### Low Priority (When Time Permits)
- [issue]: [why low priority]

## Recommendations

- [Concern remediation recommendations]

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
CONCERNS ANALYSIS COMPLETE
Document: docs/legacy/CONCERNS.md
Top Concern: [most critical issue]
Tech Debt Level: [Low/Medium/High]
```
```

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

### Output

Create `docs/legacy/NEXT-STEPS.md` with this structure:

```markdown
# Next Steps for SDLC Adoption

**Generated:** YYYY-MM-DD
**Project:** [project name]

## Project Summary

[1 paragraph synthesizing the project state based on all analyses]

## SDLC Readiness Assessment

| Dimension | Status | Notes |
|-----------|--------|-------|
| Stack | [Good/Needs Work] | [brief note] |
| Architecture | [Good/Needs Work] | [brief note] |
| Structure | [Good/Needs Work] | [brief note] |
| Conventions | [Good/Needs Work] | [brief note] |
| Testing | [Good/Needs Work] | [brief note] |
| Integrations | [Good/Needs Work] | [brief note] |
| Technical Debt | [Low/Medium/High] | [brief note] |

## Prioritized Improvements

### Priority 1: Critical (Do First)

These items block safe, productive development.

#### 1.1 [Issue Title]
**Problem:** [What's wrong]
**Impact:** [Why it matters]
**Action:** [What to do]
**Effort:** [Low/Medium/High]

#### 1.2 [Issue Title]
...

### Priority 2: Important (Do Soon)

These items significantly improve development experience.

#### 2.1 [Issue Title]
**Problem:** [What's wrong]
**Impact:** [Why it matters]
**Action:** [What to do]
**Effort:** [Low/Medium/High]

#### 2.2 [Issue Title]
...

### Priority 3: Nice to Have (When Time Permits)

These items are polish and optimization.

#### 3.1 [Issue Title]
**Problem:** [What's wrong]
**Impact:** [Why it matters]
**Action:** [What to do]
**Effort:** [Low/Medium/High]

## How to Proceed with SDLC

Now that you have documentation of your codebase, here's how to start using the SDLC workflow:

### Step 1: Pick Your First Improvement
Choose a P1 item from above. Start small - success builds momentum.

### Step 2: Run Discovery
```
/discover
```
Describe the improvement you want to make. The discovery process will help you define scope and requirements.

### Step 3: Follow the Workflow
After discovery, the SDLC workflow guides you through:
- `/prd` - Create detailed requirements
- `/plan` - Design the technical approach
- `/ticket` - Break into actionable tasks
- `/implement` - TDD implementation
- `/pr` - Code review
- `/validate` - Pre-merge verification

### Step 4: Iterate
After your first improvement, pick the next P1 item. Work through priorities systematically.

## Quick Wins

If you want to start immediately with minimal process, these items can be done quickly:

- [Quick win 1]
- [Quick win 2]
- [Quick win 3]

## References

- [STACK.md](./STACK.md) - Technology stack details
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [STRUCTURE.md](./STRUCTURE.md) - Project organization
- [CONVENTIONS.md](./CONVENTIONS.md) - Code style standards
- [TESTING.md](./TESTING.md) - Test coverage and patterns
- [INTEGRATIONS.md](./INTEGRATIONS.md) - External dependencies
- [CONCERNS.md](./CONCERNS.md) - Technical debt details

---
*Generated by `/analyze-codebase`*
```

### Return

After creating the document, return:
```
NEXT STEPS SYNTHESIS COMPLETE
Document: docs/legacy/NEXT-STEPS.md

Top 3 Priorities:
1. [P1 item]
2. [P1 item]
3. [P2 item if no more P1s]

Recommended First Action: [most impactful quick win]
```
```

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

---

## Topic/Context for Analysis

$ARGUMENTS
