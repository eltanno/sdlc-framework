# Coding Standards

Code quality and implementation standards for engineers.

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

### Test Naming Convention
```
test_<function>_<scenario>_<expected>

Examples:
- test_login_valid_credentials_returns_token
- test_login_invalid_password_raises_auth_error
- test_user_create_duplicate_email_raises_conflict
```

### Coverage Requirements
- Minimum: 80% line coverage
- Target: 90%+ for critical paths
- All public functions must have tests

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
type(scope): description

Types: feat, fix, docs, test, refactor, chore
Scope: component or area affected

Examples:
- feat(auth): add JWT token refresh endpoint
- fix(api): handle null user in profile response
- test(user): add integration tests for signup flow
- refactor(db): extract connection pooling to module
```

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

```
project/
├── src/              # Application code
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   ├── api/          # API endpoints
│   └── utils/        # Shared utilities
├── tests/            # Test files
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── e2e/          # End-to-end tests
├── scripts/          # Build/deploy scripts (not deployed)
├── docs/             # Documentation
│   └── plans/        # Feature plans
└── tmp/              # Temporary files (gitignored)
```

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

## Security Checklist

Every implementation should verify:
- [ ] Input validation on all user input
- [ ] Output encoding to prevent XSS
- [ ] Parameterized queries (no SQL injection)
- [ ] Authentication checked on protected routes
- [ ] Authorization checked for resource access
- [ ] No secrets in code or logs
- [ ] Sensitive data encrypted at rest and in transit
