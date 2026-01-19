# Test Directory

This directory contains test fixtures and integration test documentation for the SDLC framework.

## Directory Structure

```
test/
├── README.md                     # This file
├── fixtures/                     # Sample projects for testing
│   ├── typescript-sample/        # TypeScript/Express sample project
│   ├── python-sample/            # Python/FastAPI sample project
│   └── go-sample/                # Go/Gin sample project
└── integration/                  # Integration test documentation
    └── analyze-codebase.integration.test.md
```

## Test Fixtures

### Purpose

Test fixtures are minimal but realistic sample projects used to validate the `/analyze-codebase` command. Each fixture includes:

- Project configuration files
- Source code with typical patterns
- Intentional TODO/FIXME/HACK comments for testing Concerns analysis
- External API integration patterns

### Available Fixtures

| Fixture | Stack | Use Case |
|---------|-------|----------|
| `typescript-sample` | TypeScript, Express, Jest, ESLint | Testing TypeScript/Node.js analysis |
| `python-sample` | Python 3.11, FastAPI, pytest, ruff | Testing Python analysis |
| `go-sample` | Go 1.21, Gin | Testing Go analysis |

### Using Fixtures

To test `/analyze-codebase` with a fixture:

```bash
# Navigate to the fixture directory
cd test/fixtures/typescript-sample

# Run the analyze-codebase command
# (In Claude Code CLI)
/analyze-codebase

# Check generated documentation
ls docs/legacy/
```

### Cleaning Up After Tests

After running tests, clean the generated docs:

```bash
rm -rf test/fixtures/typescript-sample/docs/legacy
rm -rf test/fixtures/python-sample/docs/legacy
rm -rf test/fixtures/go-sample/docs/legacy
```

## Integration Tests

Integration tests are documented in markdown files with manual execution steps. See `integration/` directory for test case documentation.

### Running Integration Tests

1. Read the test case documentation
2. Execute steps manually in Claude Code CLI
3. Record results in the test execution log

## Contributing

When adding new test fixtures:

1. Create a realistic but minimal project structure
2. Include typical project configuration files
3. Add some TODO/FIXME/HACK comments for Concerns testing
4. Include at least one external integration pattern
5. Document the fixture in this README

---

*Part of the SDLC Framework test infrastructure*
