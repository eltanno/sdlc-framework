# Implementation Plan: Ralph Loop Python Port

**Date:** 2026-01-19
**Status:** APPROVED
**Discovery:** [docs/discovery/2026-01-19-ralph-python-port.md](../discovery/2026-01-19-ralph-python-port.md)
**PRD:** [docs/prds/2026-01-19-ralph-python-port.md](../prds/2026-01-19-ralph-python-port.md)
**Author:** Claude (Architect Agent)

---

## Summary

Port the Ralph orchestrator loop from 16 shell scripts (~5,830 lines) to Python 3.10+, maintaining identical functionality while gaining testability and maintainability. The implementation creates a well-structured Python package in `.claude/ralph/` with a thin shell wrapper for backward-compatible invocation. Uses PyYAML as the only runtime dependency and pytest for comprehensive testing (>90% coverage target).

## Goals

### Primary Goals

- Port all 16 shell scripts to Python with feature parity
- Achieve >90% unit test coverage on core modules
- Maintain backward-compatible CLI invocation pattern
- Create integration tests for all happy paths

### Secondary Goals

- Type hints on all public functions
- Docstrings on all public modules, classes, and functions
- Clear error messages with actionable guidance

## Non-Goals

*What this plan explicitly does NOT cover:*

- Performance optimizations beyond feature parity
- Async/concurrent ticket processing
- Rich CLI output (colors, progress bars) - plain text only initially
- New features not in current shell version
- Porting of scripts outside ralph: `update-workflow-state.sh`, `statusline.sh`, `create-project.sh`

## Technical Approach

### Architecture Overview

The Python port maintains the same logical structure as the shell scripts but reorganizes into a proper Python package:

```
.claude/ralph/
├── ralph                 # Shell wrapper (entry point - ~10 lines)
├── cli.py               # Main CLI using argparse
├── requirements.txt     # PyYAML only
├── requirements-dev.txt # pytest, pytest-cov, pytest-mock
├── core/                # Shared utilities (config, state, external CLIs)
│   ├── __init__.py
│   ├── config.py        # Config loading (replaces config-helpers.sh)
│   ├── state.py         # State management (replaces state-utils.sh)
│   ├── github.py        # GitHub operations via gh CLI
│   └── git.py           # Git operations via git CLI
├── commands/            # Individual command implementations
│   ├── __init__.py
│   ├── orchestrator.py  # Main loop (replaces ralph-prd.sh)
│   ├── get_next.py      # Get next ticket
│   ├── ticket_start.py  # Start ticket
│   ├── ticket_done.py   # Complete ticket
│   ├── mark_blocked.py  # Block ticket
│   ├── validate.py      # Validation
│   ├── pr_flow.py       # PR creation
│   ├── setup.py         # Setup/init
│   ├── status.py        # Status check
│   ├── cleanup.py       # Cleanup
│   ├── ticket_reset.py  # Reset blocked ticket
│   └── parse_deps.py    # Parse plan dependencies
└── tests/
    ├── __init__.py
    ├── conftest.py      # Shared fixtures
    ├── unit/
    │   ├── test_config.py
    │   ├── test_state.py
    │   ├── test_github.py
    │   ├── test_git.py
    │   └── test_parse_deps.py
    └── integration/
        ├── test_get_next_flow.py
        ├── test_ticket_lifecycle.py
        └── test_orchestrator.py
```

### Components

| Component | Description | New/Modified | Replaces |
|-----------|-------------|--------------|----------|
| `core/config.py` | Config loading from YAML, env var support | New | config-helpers.sh |
| `core/state.py` | State file CRUD, prompt building, summary writing | New | state-utils.sh |
| `core/github.py` | gh CLI wrapper for issues/PRs | New | Inline gh calls |
| `core/git.py` | git CLI wrapper for branch/commit/push | New | Inline git calls |
| `commands/orchestrator.py` | Main loop with ticket processing | New | ralph-prd.sh |
| `commands/get_next.py` | Find next available ticket | New | get-next-ticket.sh |
| `commands/ticket_start.py` | Start work on ticket | New | ticket-start.sh |
| `commands/ticket_done.py` | Mark ticket complete | New | ticket-done.sh |
| `commands/mark_blocked.py` | Mark ticket blocked | New | mark-blocked.sh |
| `commands/ticket_reset.py` | Reset blocked ticket | New | ticket-reset.sh |
| `commands/validate.py` | Run validation commands | New | validate.sh |
| `commands/pr_flow.py` | Create and merge PRs | New | pr-flow.sh |
| `commands/setup.py` | Initialize ralph run | New | setup.sh |
| `commands/status.py` | Display current status | New | status.sh |
| `commands/cleanup.py` | Finalize run and archive | New | cleanup.sh |
| `commands/parse_deps.py` | Parse ticket dependencies | New | parse-plan-deps.sh |
| `cli.py` | CLI entry point with argparse | New | N/A |

### Key Technical Decisions

#### Decision 1: subprocess for external CLIs

**Choice:** Use `subprocess.run()` for all `gh` and `git` commands

**Rationale:**
- Mirrors exactly how shell scripts work (shell out to CLI)
- No new dependencies (no pygithub, no gitpython)
- Easier to mock in tests (just mock subprocess.run)
- gh CLI handles authentication, rate limiting, etc.

**Alternatives Considered:**
- PyGithub library: Would add dependency, different auth model
- GitPython library: Would add dependency, more complex

#### Decision 2: Dataclasses for structured data

**Choice:** Use `@dataclass` for config, state, and ticket representations

**Rationale:**
- Built-in to Python 3.10+
- Provides type hints, `__eq__`, `__repr__` automatically
- Easy serialization to/from dict with `asdict()`
- More readable than plain dicts

**Alternatives Considered:**
- Plain dicts: Less type safety, harder to document
- Pydantic: Would add another dependency

#### Decision 3: Module-level functions, not classes

**Choice:** Use module-level functions for most command implementations

**Rationale:**
- Mirrors the shell script model (scripts with functions)
- Simpler to test (just call function with args)
- Classes only where state is necessary (Config, State)

**Alternatives Considered:**
- Command pattern with Command classes: Overkill for this use case
- Single large orchestrator class: Poor separation of concerns

#### Decision 4: JSON for all output parsing

**Choice:** All subprocess output parsed as JSON using Python's built-in `json` module

**Rationale:**
- gh CLI supports `--json` output natively
- Replaces all jq usage with Python's json module
- Consistent structured data handling

**Alternatives Considered:**
- Text parsing with regex: Fragile, hard to maintain
- jq subprocess calls: Adds external dependency

#### Decision 5: Atomic file writes for state

**Choice:** Write state files atomically (write to temp, then rename)

**Rationale:**
- Prevents corrupt state files if interrupted mid-write
- Same pattern used by the shell scripts
- Python's `tempfile` + `os.rename` makes this easy

## Implementation Phases

### Phase 1: Foundation (Tickets 1-6)

**Goal:** Establish package structure and implement all core modules with tests

**Steps:**
1. Create package directory structure, `__init__.py` files, requirements files
2. Implement `core/config.py` with YAML loading and environment variable support
3. Implement `core/state.py` with state file CRUD and atomic writes
4. Implement `core/github.py` with gh CLI wrapper functions
5. Implement `core/git.py` with git CLI wrapper functions
6. Write unit tests for all core modules (>90% coverage)

**Exit Criteria:**
- [ ] Package structure matches design
- [ ] All core modules pass unit tests
- [ ] Requirements files are complete
- [ ] `python -c "from core import config, state, github, git"` works

### Phase 2: Utility Commands (Tickets 7-8)

**Goal:** Implement dependency-light utility commands

**Steps:**
1. Implement `commands/parse_deps.py` for parsing plan dependencies
2. Write unit tests for parse_deps

**Exit Criteria:**
- [ ] parse_deps handles both table and section formats
- [ ] Unit tests pass with >90% coverage

### Phase 3: Individual Commands (Tickets 9-17)

**Goal:** Port all individual command scripts to Python

**Steps:**
1. Implement commands in dependency order (see ticket table)
2. Each command gets unit tests
3. Commands are standalone-runnable for testing

**Exit Criteria:**
- [ ] All 10 command modules implemented
- [ ] Each command has unit tests
- [ ] Commands can be imported and called directly

### Phase 4: Orchestrator (Tickets 18-19)

**Goal:** Implement main orchestrator loop and CLI

**Steps:**
1. Implement `commands/orchestrator.py` with full workflow logic
2. Implement `cli.py` with argparse and subcommand routing
3. Create shell wrapper entry point

**Exit Criteria:**
- [ ] Orchestrator coordinates all commands correctly
- [ ] CLI supports all flags: --dry-run, --max-attempts, --verbose
- [ ] Shell wrapper invokes Python correctly

### Phase 5: Integration Testing (Ticket 20)

**Goal:** Create comprehensive integration test suite

**Steps:**
1. Create integration test fixtures (mock gh/git responses)
2. Implement test_get_next_flow.py
3. Implement test_ticket_lifecycle.py
4. Implement test_orchestrator.py

**Exit Criteria:**
- [ ] All happy paths have integration tests
- [ ] Key error scenarios are tested
- [ ] Tests run in <30 seconds

### Phase 6: Documentation and Cutover (Tickets 21-24)

**Goal:** Update documentation and complete migration

**Steps:**
1. Update getting started guide with Python installation
2. Update `/ralph-cmd` and `/ticket-reset` commands
3. Move shell scripts to `ralph-legacy/` backup
4. End-to-end validation with real PRD/plan

**Exit Criteria:**
- [ ] Documentation is complete
- [ ] Commands point to Python version
- [ ] Legacy scripts are backed up
- [ ] E2E test passes with real workflow

## Test Strategy

### Unit Tests

Each core module and command has dedicated unit tests:

| Module | Test File | Key Test Cases |
|--------|-----------|----------------|
| config.py | test_config.py | Valid YAML, missing file, env var override, defaults |
| state.py | test_state.py | Create, read, update, atomic write, corruption handling |
| github.py | test_github.py | List issues, get issue, close issue, create PR, auth errors |
| git.py | test_git.py | Branch create, checkout, commit, push, dirty detection |
| parse_deps.py | test_parse_deps.py | No deps, linear deps, complex graph, both formats |

### Integration Tests

| Flow | Test File | Scenarios |
|------|-----------|-----------|
| Get Next | test_get_next_flow.py | Empty queue, deps satisfied, deps blocked, all complete |
| Lifecycle | test_ticket_lifecycle.py | Start->done, start->block->reset->done, resume |
| Orchestrator | test_orchestrator.py | Happy path, retry flow, all blocked, completion |

### Mocking Strategy

All external CLI calls are mocked in tests:

| External System | Mock Approach |
|-----------------|---------------|
| GitHub CLI (gh) | Mock `subprocess.run`, return fixture JSON |
| Git CLI | Mock `subprocess.run`, track operations |
| File system | pytest `tmp_path` fixture |
| Config files | Test fixtures with known values |

```python
# Example: conftest.py fixtures
@pytest.fixture
def mock_gh(mocker):
    """Mock all gh CLI calls."""
    mock = mocker.patch("core.github.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = '[]'
    return mock

@pytest.fixture
def mock_git(mocker):
    """Mock all git CLI calls."""
    mock = mocker.patch("core.git.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = ''
    return mock
```

### Coverage Requirements

- Unit tests: >90% on core modules
- Integration tests: 100% happy paths
- Overall target: 85%+

## Tickets

*Tickets created via GitHub Issues:*

| ID | Title | Description | Priority | Complexity | Phase | Dependencies |
|----|-------|-------------|----------|------------|-------|--------------|
| SDLC-0013 | Package structure setup | Create directory structure, __init__.py files, requirements.txt, shell wrapper | P1 | 2 | 1 | - |
| SDLC-0014 | Core: config.py | Port config-helpers.sh - YAML loading, env var support, typed config class | P1 | 3 | 1 | SDLC-0013 |
| SDLC-0015 | Core: state.py | Port state-utils.sh - state file CRUD, atomic writes, prompt building | P1 | 4 | 1 | SDLC-0014 |
| SDLC-0016 | Core: github.py | Create gh CLI wrapper - issue list/get/close, PR create/get | P1 | 3 | 1 | SDLC-0014 |
| SDLC-0017 | Core: git.py | Create git CLI wrapper - branch ops, commit, push, status | P1 | 3 | 1 | SDLC-0014 |
| SDLC-0018 | Core unit tests | Unit tests for config, state, github, git modules (>90% coverage) | P1 | 3 | 1 | SDLC-0014, SDLC-0015, SDLC-0016, SDLC-0017 |
| SDLC-0019 | Command: parse_deps.py | Port parse-plan-deps.sh - parse plan markdown, build dependency graph | P1 | 3 | 2 | SDLC-0015 |
| SDLC-0020 | parse_deps unit tests | Unit tests for parse_deps (table and section formats) | P1 | 2 | 2 | SDLC-0019 |
| SDLC-0021 | Command: get_next.py | Port get-next-ticket.sh - find next eligible ticket by deps and status | P1 | 3 | 3 | SDLC-0015, SDLC-0016, SDLC-0019 |
| SDLC-0022 | Command: ticket_start.py | Port ticket-start.sh - claim issue, create branch, update state | P1 | 3 | 3 | SDLC-0015, SDLC-0016, SDLC-0017 |
| SDLC-0023 | Command: ticket_done.py | Port ticket-done.sh - remove label, close issue, update state | P1 | 3 | 3 | SDLC-0015, SDLC-0016 |
| SDLC-0024 | Command: mark_blocked.py | Port mark-blocked.sh - add blocked label, update state | P1 | 2 | 3 | SDLC-0015, SDLC-0016 |
| SDLC-0025 | Command: ticket_reset.py | Port ticket-reset.sh - reset blocked to pending | P2 | 2 | 3 | SDLC-0015 |
| SDLC-0026 | Command: validate.py | Port validate.sh - run configured validation commands | P1 | 3 | 3 | SDLC-0014 |
| SDLC-0027 | Command: pr_flow.py | Port pr-flow.sh - commit, push, create PR, merge | P1 | 3 | 3 | SDLC-0016, SDLC-0017 |
| SDLC-0028 | Command: setup.py | Port setup.sh - initialize state from PRD/plan | P1 | 3 | 3 | SDLC-0015, SDLC-0016, SDLC-0019 |
| SDLC-0029 | Command: status.py | Port status.sh - display current status | P2 | 2 | 3 | SDLC-0015 |
| SDLC-0030 | Command: cleanup.py | Port cleanup.sh - finalize run, archive state | P2 | 2 | 3 | SDLC-0015, SDLC-0016 |
| SDLC-0031 | Command: orchestrator.py | Port ralph-prd.sh main loop - full workflow orchestration | P1 | 5 | 4 | SDLC-0021, SDLC-0022, SDLC-0023, SDLC-0024, SDLC-0026, SDLC-0027, SDLC-0028, SDLC-0030 |
| SDLC-0032 | CLI entry point | Create cli.py with argparse, connect to orchestrator | P1 | 3 | 4 | SDLC-0031 |
| SDLC-0033 | Integration tests | Test get_next flow, ticket lifecycle, full orchestrator | P1 | 4 | 5 | SDLC-0032 |
| SDLC-0034 | Documentation update | Update getting started guide with Ralph installation section | P1 | 2 | 6 | SDLC-0032 |
| SDLC-0035 | Command updates | Update /ralph-cmd and /ticket-reset to use Python version | P1 | 2 | 6 | SDLC-0032 |
| SDLC-0036 | Legacy backup | Move shell scripts to ralph-legacy/, update references | P2 | 2 | 6 | SDLC-0033 |
| SDLC-0037 | Final validation | End-to-end test with real PRD/plan, verify feature parity | P1 | 3 | 6 | SDLC-0036 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, rename | Sonnet |
| 2 | Simple | Package setup, simple commands | Sonnet |
| 3 | Moderate | Most command implementations | Opus |
| 4 | Complex | state.py, integration tests | Opus |
| 5 | Very Hard | orchestrator.py | Opus |

*Current threshold: 1-2 uses Sonnet, 3-5 uses Opus*

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Subtle behavior differences vs shell | Medium | High | Comprehensive integration tests that mirror shell test cases; side-by-side comparison during parallel testing phase |
| Missing edge cases in shell scripts | Medium | Medium | Port existing test-*.sh test cases; review shell scripts carefully for undocumented behavior |
| Python not available on target system | Low | High | Document Python 3.10+ prerequisite clearly; provide version check in shell wrapper |
| PyYAML version conflicts | Low | Low | Pin version in requirements.txt; use standard YAML features only |
| gh/git CLI behavior differences | Low | Medium | Test on all target platforms (Linux, macOS, WSL); use stable CLI flags only |
| State file format incompatibility | Low | High | Use identical JSON structure; test reading existing state files |

## Environment Considerations

### Local Development

- **Primary OS:** Linux (Ubuntu 20.04+)
- **Also supported:** macOS 11+, Windows WSL2
- **Known Limitations:** None - Python and gh CLI work consistently across platforms

### CI Environment

- **Platform:** GitHub Actions (if applicable)
- **Considerations:**
  - Need Python 3.10+ in CI
  - gh CLI authentication for integration tests (optional - tests use mocks)

## Dependencies

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyyaml | ^6.0 | YAML config file parsing |
| pytest | ^7.0 | Testing framework (dev) |
| pytest-cov | ^4.0 | Coverage reporting (dev) |
| pytest-mock | ^3.0 | Mocking utilities (dev) |

### Internal Dependencies

- Python 3.10+ (system)
- gh CLI (system) - authenticated
- git CLI (system)

### Blocking Items

- [ ] None - can begin immediately after plan approval

## Open Questions

*All resolved - none remaining:*

- [x] Language choice - Python 3.10+
- [x] Execution interface - Shell wrapper + Python CLI
- [x] Package location - `.claude/ralph/`
- [x] Migration strategy - Full port with comprehensive tests
- [x] External dependencies - PyYAML only

## Success Criteria

*How do we know we're done?*

- [ ] All 16 shell scripts ported to Python
- [ ] Unit test coverage >90% on core modules
- [ ] All integration test happy paths pass
- [ ] Same CLI invocation pattern works: `.claude/ralph/ralph <prd> <plan>`
- [ ] Dry run mode works correctly
- [ ] State file format is compatible with existing files
- [ ] Documentation updated with installation instructions
- [ ] Legacy scripts backed up to `ralph-legacy/`
- [ ] End-to-end test passes with real PRD/plan

---

## Pre-Implementation Checklist

**CRITICAL: Before delegating ANY implementation work, verify:**

- [ ] Discovery committed: `git log --oneline docs/discovery/`
- [ ] PRD committed: `git log --oneline docs/prds/`
- [ ] This plan committed: `git log --oneline docs/plans/`
- [ ] `git status docs/` shows "nothing to commit"

> **Why this matters:** Untracked files can be lost during branch operations. Documents ARE the state - if they're not committed, implementation has no foundation. See WORKFLOW.md "Artifact Commit Rule" for details.

---

## Post-Implementation Checklist

**After all tickets are complete:**

- [ ] All tests pass (unit, integration)
- [ ] Code committed and pushed
- [ ] PR created and merged
- [ ] Create execution report: `/execution-report`
- [ ] Create system review: `/system-review`

---

## Approval

- [ ] **Approved by:** ____________ on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted.*
