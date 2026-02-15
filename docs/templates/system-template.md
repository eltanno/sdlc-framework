# {Project Name} System Manifest
<!-- Last updated: YYYY-MM-DD -->
<!-- UPDATE THIS DOCUMENT after each feature merge or architectural change -->

## What This Is

{1-3 sentences: what the project does, who it's for, and the core technical approach. Include key tech stack names.}

## Architecture Overview

```
{ASCII diagram showing major components and how they communicate.
Include: client/server boundaries, data stores, external services, message flow directions.}
```

**Monorepo structure** (if applicable):
- `{package}/` -- {purpose}
- `{package}/` -- {purpose}
- `{package}/` -- {purpose}

**Communication:**
- {Protocol} for {what}
- {Protocol} for {what}
- {External service} for {what}

## Data Model

### Database: {DB engine} via {ORM/query layer}

**Schema files:** `{path/to/schema/}`

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `{table}` | {purpose} | {important columns} |

{Document any non-obvious conventions:}
- **Boolean convention:** {How booleans are stored, if non-standard}
- **JSON convention:** {How structured data is stored in columns}
- **ID convention:** {UUID, auto-increment, CUID, etc.}

### Other Data Sources (if applicable)

{Config files, YAML content, seed data, external APIs, etc. Describe what lives where and how it's loaded.}

## Frontend Architecture

### Key Directories

| Directory | Contains |
|-----------|----------|
| `{path}/` | {what lives here} |

### State Management

| Store/Context | Manages |
|---------------|---------|
| `{store}` | {what state} |

### Key Pipelines / Data Flows

```
{Describe any non-trivial client-side data processing pipelines.
Example: form submission flow, real-time update handling, auth flow, etc.}
```

## Backend Architecture

### API Routes

| Route | Handler | Purpose | Auth |
|-------|---------|---------|------|
| `{METHOD} {path}` | {file} | {purpose} | {auth level} |

{Describe auth mechanism: JWT, session, API key, etc.}

### Real-Time Protocol (if applicable)

#### Client-to-Server Messages

| Type | Data | Purpose |
|------|------|---------|
| `{type}` | `{ field }` | {purpose} |

#### Server-to-Client Messages

| Type | Purpose |
|------|---------|
| `{type}` | {purpose} |

{Note: message validation approach, e.g. "All messages validated with Zod schemas in {path}"}

### Service / Domain Pattern

{Describe how business logic is organized. Example: "Each domain follows: `src/{domain}/service.ts` + `index.ts` barrel export."}

| Domain | Key Responsibility |
|--------|--------------------|
| `{domain}/` | {what it does} |

## Key Architectural Decisions

| # | Decision | Rationale | Source |
|---|----------|-----------|--------|
| 1 | {decision} | {why} | {where this was decided} |

## Conventions & Patterns

### Adding a New {Primary Feature Type} End-to-End

{Step-by-step checklist for the most common type of feature addition. This is the most valuable section for new contributors and AI agents.}

1. **{Layer}** -- {What to do and where}
2. **{Layer}** -- {What to do and where}
3. ...

### File & Test Conventions

- Language: {language(s)}
- Tests location: {where tests live, co-located or separate}
- Test runner: {tool}. Pattern: `{glob}`.
- Coverage target: {percentage}
- Branch naming: `{pattern}`
- Commit format: `{pattern}`

### Import / Module Conventions

{Any project-specific import rules, e.g. ESM extensions, path aliases, barrel exports.}

## Active Constraints & Known Issues

### Known Bugs

{Link to bug tracker or bug list document.}

### Fragile Areas

{List parts of the codebase that are particularly sensitive to changes. For each, explain WHY it's fragile and what to watch out for.}

- **{Area}** -- {Why it's fragile. What breaks if you change it.}

## What NOT to Do

| Anti-pattern | Why it breaks things |
|-------------|---------------------|
| {Bad thing} | {What goes wrong} |

## Document Index

### Vision & Discovery

| What You Need | Document | Location |
|--------------|----------|----------|
| {description} | {name} | `{path}` |

### PRDs / Feature Specs

| Feature | Document | Location |
|---------|----------|----------|
| {feature} | {name} | `{path}` |

### Technical References

| What You Need | Document | Location |
|--------------|----------|----------|
| {description} | {name} | `{path}` |
