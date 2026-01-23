# Coding Standards

Code quality and implementation standards for engineers.

---

## Philosophy

This codebase will outlive you. Every shortcut becomes someone else's burden. Every hack compounds into technical debt that slows the whole team down.

You are not just writing code. You are shaping the future of this project. The patterns you establish will be copied. The corners you cut will be cut again.

Fight entropy. Leave the codebase better than you found it.


## Language Preference

**Default: TypeScript** for all new projects.

Use JavaScript only for:
- Legacy projects already in JavaScript
- Simple scripts where types add no value

When using JavaScript, follow TypeScript conventions without type annotations.

---

## TDD Workflow (Mandatory)

Every implementation follows Red-Green-Refactor:

```
1. RED: Write a failing test first
   - Test describes the expected behavior
   - Run test, confirm it fails

2. GREEN: Write minimal code to pass
   - Only enough code to make the test pass
   - No extra features or "improvements"

3. REFACTOR: Clean up while green
   - Improve code structure
   - Run tests after each change
   - Tests must stay green
```

### Test File Naming

| Test Type | Location | File Pattern |
|-----------|----------|--------------|
| Unit tests | `test/unit/` | `*.test.ts` |
| Integration tests | `test/integration/` | `*.integration.test.ts` |
| E2E tests | `test/e2e/` | `*.spec.ts` |

**Important:** Tests go in the `test/` directory, NOT co-located with source code.

### Test Naming Convention

**Python:**
```
test_<function>_<scenario>_<expected>

Examples:
- test_login_valid_credentials_returns_token
- test_login_invalid_password_raises_auth_error
```

**TypeScript/JavaScript:**
```typescript
describe('ComponentName', () => {
  describe('methodName', () => {
    it('should return X when given Y', () => {
      // test
    });

    it('should throw error when given invalid input', () => {
      // test
    });
  });
});
```

### Test Quality (Critical)

**The test must answer: "If this code was subtly broken, would this test catch it?"**

```python
# BAD - passes even if function returns wrong data
def test_get_user():
    result = get_user(42)
    assert result is not None  # Would pass for ANY non-None value

# GOOD - verifies correct behavior
def test_get_user():
    result = get_user(42)
    assert result["id"] == 42
    assert result["email"] == "expected@example.com"
```

**Rules:**
1. **Assert specific values**, not just existence (`== "completed"` not `is not None`)
2. **Verify outcomes**, not implementation (`assert user.is_active` not `mock.assert_called()`)
3. **Include negative assertions** (`assert blocked_ticket not in result`)
4. **Don't test Python** - dataclass assignment, enum existence, etc. already work

If your test would pass with a hardcoded return value, it's not testing behavior.

### Coverage Requirements
- Minimum: 80% line coverage
- Target: 90%+ for critical paths
- All public functions must have tests
- **Coverage without meaningful assertions is theater**

---

## Code Style

### Python
```python
# PEP 8 compliant, 88 char lines (Black formatter)
# Type hints required on all functions
# Google-style docstrings

def calculate_total(items: list[Item], tax_rate: float = 0.1) -> Decimal:
    """Calculate total price including tax.

    Args:
        items: List of items to total.
        tax_rate: Tax rate as decimal. Defaults to 0.1 (10%).

    Returns:
        Total price including tax as Decimal.

    Raises:
        ValueError: If tax_rate is negative.
    """
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")

    subtotal = sum(item.price for item in items)
    return Decimal(str(subtotal * (1 + tax_rate)))
```

**Rules:**
- f-strings over .format() or %
- dataclasses for data containers
- pathlib over os.path
- Type hints on all function signatures

### TypeScript
```typescript
// Strict mode always
// const > let, never var
// Arrow functions for callbacks
// async/await over promise chains

interface UserCreateInput {
  email: string;
  name: string;
  role?: UserRole;
}

const createUser = async (input: UserCreateInput): Promise<User> => {
  const { email, name, role = UserRole.Member } = input;

  const existing = await db.user.findUnique({ where: { email } });
  if (existing) {
    throw new ConflictError(`User with email ${email} already exists`);
  }

  return db.user.create({
    data: { email, name, role },
  });
};
```

**Rules:**
- Explicit return types on functions
- Interface over type for object shapes
- Destructure in function parameters
- Throw typed errors, not strings

---

## Git Practices

### Branch Naming
```
feature/TASK-{id}-{short-description}
fix/TASK-{id}-{short-description}
refactor/TASK-{id}-{short-description}

Examples:
- feature/TASK-123-user-authentication
- fix/TASK-456-login-timeout
- refactor/TASK-789-extract-auth-middleware
```

### Commit Messages
```
type(scope): description [TICKET-ID]

Types: feat, fix, docs, test, refactor, chore
Scope: component or area affected
Ticket: reference to task tracker (Trello, Jira, etc.)

Examples:
- feat(auth): add JWT token refresh endpoint [TASK-123]
- fix(api): handle null user in profile response [TASK-456]
- test(user): add integration tests for signup flow [TASK-789]
- refactor(db): extract connection pooling to module [TASK-101]
- docs(readme): update setup instructions
```

Note: Ticket ID is optional for docs/chore commits that aren't tied to a specific task.

### Pre-Commit Checklist
Before every commit:
1. All tests pass: `pytest` / `npm test`
2. Linting clean: `ruff check .` / `npx eslint .`
3. Types check: `mypy .` / `npx tsc --noEmit`
4. No secrets in code

---

## Quality Commands

### Python
```bash
# Linting
ruff check . --fix

# Formatting
black .

# Type checking
mypy .

# Tests with coverage
pytest --cov=src --cov-report=term-missing
```

### TypeScript/JavaScript
```bash
# Linting
npx eslint . --fix

# Formatting
npx prettier --write .

# Type checking
npx tsc --noEmit

# Tests with coverage
npm test -- --coverage
```

---

## File Structure Convention

### Single-Codebase Projects
```
project/
├── src/              # Application code only (no tests)
│   ├── components/   # UI components (React, Vue, etc.)
│   ├── hooks/        # Custom hooks
│   ├── services/     # Business logic
│   ├── utils/        # Shared utilities
│   └── types/        # Type definitions
├── test/             # All test files
│   ├── unit/         # Unit tests (*.test.ts)
│   ├── integration/  # Integration tests (*.integration.test.ts)
│   └── e2e/          # End-to-end tests (*.spec.ts)
│       ├── tests/    # Test specs
│       └── helpers/  # Test utilities
├── docs/             # Documentation
│   ├── prds/         # Product requirements
│   ├── plans/        # Implementation plans
│   └── templates/    # Document templates
├── scripts/          # Build/deploy scripts (not deployed)
└── tmp/              # Temporary files (gitignored)
```

### Monorepo Projects

When a project has multiple codebases (e.g., mobile + backend), each codebase lives in its own directory:

```
project/
├── mobile/           # React Native / Expo app
│   ├── src/
│   ├── test/
│   └── package.json
├── backend/          # Django / Node API
│   ├── apps/
│   ├── config/
│   └── requirements/
├── docs/             # Shared documentation
└── config.yaml       # Defines all codebases
```

**Key principle:** Source code and tests are separated. Tests never live alongside source files.

---

## Monorepo Configuration (IMPORTANT)

**Check `config.yaml` before running quality commands.**

### Single-Codebase (default)
If `config.yaml` has NO `dev.codebases` section, run commands from project root:
```bash
npm run typecheck
npm run lint
npm test
```

### Monorepo (multiple codebases)
If `config.yaml` has a `dev.codebases` section, you MUST run commands for EACH codebase:

```yaml
# Example config.yaml
dev:
  codebases:
    mobile:
      path: "mobile"
      test_command: "npm test"
    backend:
      path: "backend"
      test_command: "pytest"
```

**How to run:**
```bash
# For each codebase, cd into its path and run its commands
cd mobile && npm test && cd ..
cd backend && pytest && cd ..
```

**ALL codebases must pass before committing.** A failure in any codebase blocks the commit.

### Interpreting config.yaml

1. Read `config.yaml` at project root
2. Check if `dev.codebases` exists:
   - **Yes**: Iterate each codebase, `cd` into `path`, run its commands
   - **No**: Run top-level `dev.*` commands from project root
3. All checks (typecheck, lint, test, build) must pass for ALL codebases

---

## Legacy Code Rules

When working with existing code (different from greenfield TDD):

1. **Write characterization tests first**
   - Prove CURRENT behavior, bugs and all
   - Lock down what the code does before changing it

2. **Small incremental changes**
   - One refactor at a time
   - Run tests after each change

3. **Never fix bugs during refactoring**
   - Document bugs found
   - Fix in separate PR after refactor complete

4. **Preserve interfaces**
   - Don't change function signatures unless necessary
   - Deprecate before removing

---

## Error Handling

### Python
```python
# Specific exceptions over generic
class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class AuthorizationError(Exception):
    """Raised when user lacks permission."""
    pass

# Catch specific, re-raise or handle
try:
    user = authenticate(token)
except jwt.ExpiredSignatureError:
    raise AuthenticationError("Token expired")
except jwt.InvalidTokenError as e:
    raise AuthenticationError(f"Invalid token: {e}")
```

### TypeScript
```typescript
// Typed error classes
class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`, 'NOT_FOUND', 404);
  }
}
```

---

## Avoid Cruft

**Cruft** = useless code that accumulates. Lint won't catch it - it's syntactically valid but adds noise.

| Pattern | Cruft | Clean |
|---------|-------|-------|
| Single-use intermediate | `x = getData(); y = x; return y` | `return getData()` |
| Lying comment | `x = val  # caching for performance` (used once) | Just use `val` directly |
| No-op assignment | `result = None; result = calc()` | `result = calc()` |
| Over-verbose name | `temporary_variable_for_user_object` | `user` |
| Redundant check | `u = User(); if u is not None: save(u)` | `u = User(); save(u)` |

**Rule:** If you can delete code and tests still pass with no behavior change, delete it.

---

## Security Checklist

Every implementation should verify:
- [ ] Input validation on all user input
- [ ] Output encoding to prevent XSS
- [ ] Parameterized queries (no SQL injection)
- [ ] Authentication checked on protected routes
- [ ] Authorization checked for resource access
- [ ] No secrets in code or logs
- [ ] Sensitive data encrypted at rest and in transit
