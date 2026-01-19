# PRD: Ralph Loop Python Port

**Date:** 2026-01-19
**Status:** APPROVED
**Discovery:** [docs/discovery/2026-01-19-ralph-python-port.md](../discovery/2026-01-19-ralph-python-port.md)
**Plan:** [docs/plans/2026-01-19-ralph-python-port.md](../plans/2026-01-19-ralph-python-port.md)
**Owner:** Development Team
**Stakeholders:** SDLC Framework Users

---

## Discovery Reference

**Note:** This PRD covers the full Python port of the Ralph orchestrator loop, representing a complete rewrite of the shell-based implementation.

**Iteration Vision:**
Port the Ralph orchestrator loop from shell scripts (~5,830 lines across 16 files) to Python to gain testability, maintainability, and reliability while maintaining identical functionality.

**How This Feature Fits:**
This is the sole feature for this iteration. The Ralph loop is the core automation engine of the SDLC framework, and porting it to Python addresses critical limitations in testing, debugging, and cross-platform compatibility that have accumulated as the shell scripts grew in complexity.

---

## Executive Summary

### Problem Statement

The Ralph orchestrator loop has grown into a complex procedure spanning 16 shell scripts with approximately 5,830 lines of code. Shell scripting limitations make the codebase:

- **Hard to test** - No unit testing framework for bash; existing tests are shell scripts that are brittle and hard to maintain
- **Prone to bugs** - Changes frequently introduce regressions due to lack of type safety and proper testing
- **Difficult to maintain** - Complex control flow in shell is hard to read, modify, and debug
- **Not fully portable** - Bash-specific features may not work consistently across Linux, macOS, and WSL

### Solution Summary

Rewrite the Ralph orchestrator loop in Python 3.10+, creating a well-structured package with clear separation of concerns (core utilities vs. commands), comprehensive unit and integration tests using pytest, and a thin shell wrapper to maintain the existing invocation pattern. The solution will use PyYAML as the only external dependency and leverage Python's built-in `json` module to replace jq.

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Unit Test Coverage | 0% | >90% | pytest-cov on core modules |
| Integration Test Coverage | ~50% (shell tests) | 100% happy paths | pytest integration suite |
| Regression Rate | Unmeasured | 0 during migration | Manual validation against legacy scripts |
| Cross-platform Compatibility | Bash-dependent | Linux/macOS/WSL | CI matrix testing |
| Documentation | Minimal | Complete getting started guide | Doc review |

---

## Requirements

### Functional Requirements

#### FR-1: Configuration Loading

**Priority:** P1 (Must Have)

**Description:** The system must load and parse YAML configuration files (config.yaml) and environment variables, providing typed access to configuration values.

**Acceptance Criteria:**
- [ ] Given a valid config.yaml file exists, when the config module loads, then all configuration values are accessible as typed attributes
- [ ] Given the RALPH_LABEL environment variable is set, when config loads, then the instance_label reflects the environment value
- [ ] Given config.yaml is missing or malformed, when config loads, then a clear error message is raised with the file path and issue
- [ ] Given default values are defined, when a config key is missing, then the default value is used

#### FR-2: State Management

**Priority:** P1 (Must Have)

**Description:** The system must manage workflow state including ticket status, current work, and progress tracking via state files.

**Acceptance Criteria:**
- [ ] Given a new workflow starts, when state is initialized, then a state file is created with correct structure
- [ ] Given a ticket transitions status, when state is updated, then the change is persisted atomically (no partial writes)
- [ ] Given multiple tickets exist, when querying state, then all ticket statuses are accurately returned
- [ ] Given a state file exists, when state is read, then it matches the last written state exactly
- [ ] Given a corrupted state file, when state is read, then a clear error is raised (not a silent failure)

#### FR-3: GitHub Operations

**Priority:** P1 (Must Have)

**Description:** The system must interact with GitHub via the gh CLI for issue management, PR operations, and repository queries.

**Acceptance Criteria:**
- [ ] Given valid credentials, when listing issues, then all matching issues are returned with correct metadata
- [ ] Given an issue number, when fetching issue details, then title, body, labels, and status are returned
- [ ] Given a PR is created, when the operation completes, then the PR URL is returned and issue is linked
- [ ] Given the gh CLI is not authenticated, when any GitHub operation is attempted, then a clear error indicates authentication is needed
- [ ] Given a rate limit is hit, when a GitHub operation fails, then the error message indicates rate limiting

#### FR-4: Git Operations

**Priority:** P1 (Must Have)

**Description:** The system must execute git operations for branch management, commits, and repository state queries.

**Acceptance Criteria:**
- [ ] Given a valid branch name, when creating a branch, then the branch is created and checked out
- [ ] Given uncommitted changes exist, when checking repo state, then dirty status is accurately reported
- [ ] Given a commit is requested, when executed, then the commit is created with the correct message and author
- [ ] Given a branch exists remotely, when pushing, then the push succeeds or reports conflict clearly
- [ ] Given git is not installed, when any git operation is attempted, then a clear error indicates git is required

#### FR-5: Get Next Ticket

**Priority:** P1 (Must Have)

**Description:** The system must determine the next ticket to work on based on dependencies, status, and priority.

**Acceptance Criteria:**
- [ ] Given multiple pending tickets with no dependencies, when getting next ticket, then the first by order is returned
- [ ] Given a ticket depends on incomplete tickets, when getting next ticket, then that ticket is skipped
- [ ] Given all dependencies are complete, when getting next ticket, then the dependent ticket becomes available
- [ ] Given no pending tickets exist, when getting next ticket, then null/None is returned with appropriate message
- [ ] Given a ticket is blocked, when getting next ticket, then blocked tickets are skipped

#### FR-6: Ticket Start

**Priority:** P1 (Must Have)

**Description:** The system must initialize work on a ticket by creating a feature branch and updating state.

**Acceptance Criteria:**
- [ ] Given a valid ticket ID, when starting ticket, then a feature branch is created with pattern `feature/TICKET-ID-description`
- [ ] Given ticket start succeeds, when state is checked, then ticket status is "in_progress"
- [ ] Given a branch already exists for the ticket, when starting ticket, then the existing branch is checked out
- [ ] Given uncommitted changes exist, when starting ticket, then an error prevents branch creation (no data loss)

#### FR-7: Ticket Done

**Priority:** P1 (Must Have)

**Description:** The system must mark a ticket as complete, handling PR merges and issue closure.

**Acceptance Criteria:**
- [ ] Given a ticket is in progress with merged PR, when marking done, then ticket status becomes "completed"
- [ ] Given the associated issue exists, when marking done, then the issue is closed
- [ ] Given the ticket has no PR, when marking done, then an error indicates PR is required
- [ ] Given marking done succeeds, when state is checked, then completion timestamp is recorded

#### FR-8: Mark Blocked

**Priority:** P1 (Must Have)

**Description:** The system must mark a ticket as blocked with a reason, removing it from the active queue.

**Acceptance Criteria:**
- [ ] Given a ticket in progress, when marking blocked with reason, then ticket status becomes "blocked"
- [ ] Given a blocked ticket, when querying state, then the block reason is accessible
- [ ] Given a blocked ticket, when getting next ticket, then blocked tickets are excluded

#### FR-9: Ticket Reset

**Priority:** P2 (Should Have)

**Description:** The system must reset a blocked ticket to pending status for retry.

**Acceptance Criteria:**
- [ ] Given a blocked ticket, when resetting, then ticket status becomes "pending"
- [ ] Given a non-blocked ticket, when resetting, then an error indicates only blocked tickets can be reset
- [ ] Given reset succeeds, when state is checked, then block reason is cleared

#### FR-10: Validation

**Priority:** P1 (Must Have)

**Description:** The system must run validation checks including tests, linting, and build verification.

**Acceptance Criteria:**
- [ ] Given validation is requested, when executed, then all configured checks run in sequence
- [ ] Given any check fails, when validation completes, then failure details are reported with exit code
- [ ] Given all checks pass, when validation completes, then success is reported with zero exit code
- [ ] Given validation config specifies commands, when running, then those exact commands are executed

#### FR-11: PR Flow

**Priority:** P1 (Must Have)

**Description:** The system must create pull requests with proper linking to issues and standardized formatting.

**Acceptance Criteria:**
- [ ] Given changes are committed, when creating PR, then PR is created with title matching ticket
- [ ] Given an issue number, when creating PR, then the PR body links to the issue
- [ ] Given PR creation succeeds, when result is returned, then PR URL and number are provided
- [ ] Given no changes to commit, when creating PR, then an error indicates nothing to push

#### FR-12: Setup/Initialize

**Priority:** P1 (Must Have)

**Description:** The system must initialize ralph for a new PRD/plan, creating necessary state files and validating inputs.

**Acceptance Criteria:**
- [ ] Given valid PRD and plan paths, when setup runs, then state file is created with parsed tickets
- [ ] Given PRD file doesn't exist, when setup runs, then a clear error with file path is raised
- [ ] Given plan file doesn't exist, when setup runs, then a clear error with file path is raised
- [ ] Given setup completes, when status is checked, then all tickets from plan are listed

#### FR-13: Status Check

**Priority:** P2 (Should Have)

**Description:** The system must display current workflow status including ticket progress and active work.

**Acceptance Criteria:**
- [ ] Given an active workflow, when status is requested, then ticket counts by status are shown
- [ ] Given a ticket is in progress, when status is requested, then the active ticket is highlighted
- [ ] Given no workflow exists, when status is requested, then a message indicates no active workflow

#### FR-14: Cleanup

**Priority:** P2 (Should Have)

**Description:** The system must clean up after workflow completion, archiving state and removing temporary artifacts.

**Acceptance Criteria:**
- [ ] Given all tickets are complete, when cleanup runs, then state file is archived
- [ ] Given cleanup completes, when checking state, then no active workflow exists
- [ ] Given incomplete tickets exist, when cleanup is forced, then a warning is shown but cleanup proceeds

#### FR-15: Parse Dependencies

**Priority:** P1 (Must Have)

**Description:** The system must parse ticket dependencies from plan documents to determine execution order.

**Acceptance Criteria:**
- [ ] Given a plan with dependency notation, when parsed, then dependency graph is correctly built
- [ ] Given circular dependencies exist, when parsed, then an error identifies the cycle
- [ ] Given no dependencies specified, when parsed, then tickets are independent (no blocking)

#### FR-16: Main Orchestrator Loop

**Priority:** P1 (Must Have)

**Description:** The system must orchestrate the full workflow: getting next ticket, invoking Claude, handling results, and progressing through tickets.

**Acceptance Criteria:**
- [ ] Given pending tickets exist, when orchestrator runs, then tickets are processed in dependency order
- [ ] Given a ticket fails, when max retries reached, then ticket is marked blocked and next ticket starts
- [ ] Given all tickets complete, when orchestrator finishes, then success summary is displayed
- [ ] Given --dry-run flag, when orchestrator runs, then no Claude invocations occur but flow is simulated
- [ ] Given --max-attempts N, when a ticket fails, then up to N retry attempts are made before blocking

### Non-Functional Requirements

#### NFR-1: Portability

**Priority:** P1 (Must Have)

- Must work on Linux (Ubuntu 20.04+, Debian 10+)
- Must work on macOS (11+)
- Must work on Windows WSL2
- Python 3.10+ required (document in prerequisites)
- No OS-specific code paths (use pathlib, not os.path with hardcoded separators)

**Acceptance Criteria:**
- [ ] Given any supported OS, when ralph is invoked, then it executes without OS-specific errors
- [ ] Given the shell wrapper, when executed on bash/zsh, then Python is invoked correctly

#### NFR-2: Testability

**Priority:** P1 (Must Have)

- All external calls (git, gh, file I/O) must be mockable
- No global state that prevents parallel test execution
- Functions should be pure where possible (same input = same output)
- Side effects isolated to specific modules (github.py, git.py)

**Acceptance Criteria:**
- [ ] Given test fixtures, when running unit tests, then no real git/gh commands execute
- [ ] Given pytest, when running full test suite, then tests complete in <30 seconds
- [ ] Given pytest-cov, when measuring coverage, then core modules show >90% coverage

#### NFR-3: Maintainability

**Priority:** P1 (Must Have)

- Clear module boundaries (core vs commands)
- Consistent error handling patterns
- Type hints on all public functions
- Docstrings on all public functions and classes

**Acceptance Criteria:**
- [ ] Given any public function, when inspected, then type hints are present for parameters and return
- [ ] Given any module, when inspected, then a module-level docstring describes its purpose

#### NFR-4: Backward Compatibility

**Priority:** P1 (Must Have)

- Same CLI invocation pattern: `.claude/ralph/ralph <prd> <plan> [options]`
- Same exit codes for success (0) and failure (non-zero)
- Same environment variable support (RALPH_LABEL, etc.)
- State file format compatible with any existing state files

**Acceptance Criteria:**
- [ ] Given existing CLI usage patterns, when invoked with Python version, then behavior is identical
- [ ] Given existing state files, when read by Python version, then they parse correctly

#### NFR-5: Error Handling

**Priority:** P1 (Must Have)

- All errors must be catchable exceptions (not sys.exit in library code)
- Error messages must be actionable (what went wrong, how to fix)
- Stack traces available in verbose mode, hidden by default
- Graceful degradation where possible

**Acceptance Criteria:**
- [ ] Given any error condition, when error occurs, then a human-readable message is displayed
- [ ] Given --verbose flag, when error occurs, then full stack trace is included
- [ ] Given a recoverable error, when encountered, then recovery is attempted before failing

---

## User Stories

### US-1: Run Full Workflow

**Story:** As a developer, I want to run ralph on a PRD and plan so that tickets are automatically implemented in order.

**Acceptance Criteria:**
- [ ] Ralph starts and displays initial status
- [ ] Tickets are processed in dependency order
- [ ] Progress is displayed after each ticket
- [ ] Final summary shows completed/blocked counts

**Notes:** This is the primary use case - fully automated ticket processing.

### US-2: Preview Without Execution

**Story:** As a developer, I want to run ralph in dry-run mode so that I can verify the plan before actual execution.

**Acceptance Criteria:**
- [ ] With --dry-run flag, no Claude invocations occur
- [ ] Ticket order is displayed
- [ ] Dependencies are validated
- [ ] Any configuration issues are reported

### US-3: Resume Interrupted Work

**Story:** As a developer, I want to resume ralph after an interruption so that I don't lose progress.

**Acceptance Criteria:**
- [ ] Running ralph on same PRD/plan resumes from last state
- [ ] Completed tickets are not re-processed
- [ ] In-progress ticket continues or restarts cleanly
- [ ] State file accurately reflects resume point

### US-4: Handle Blocked Tickets

**Story:** As a developer, I want blocked tickets to be skipped so that work continues on other tickets.

**Acceptance Criteria:**
- [ ] When a ticket is blocked, ralph moves to next eligible ticket
- [ ] Block reason is recorded in state
- [ ] Final summary shows blocked ticket count
- [ ] Blocked tickets can be manually reviewed later

### US-5: Reset Blocked Ticket

**Story:** As a developer, I want to reset a blocked ticket so that I can retry it after fixing the underlying issue.

**Acceptance Criteria:**
- [ ] `/ticket-reset` command identifies blocked tickets
- [ ] Selected ticket is reset to pending
- [ ] Block reason is cleared
- [ ] Ticket becomes eligible for next run

### US-6: Check Current Status

**Story:** As a developer, I want to check workflow status so that I can see progress without running ralph.

**Acceptance Criteria:**
- [ ] Status command shows tickets by status (pending/in_progress/completed/blocked)
- [ ] Current active ticket (if any) is highlighted
- [ ] Estimated remaining work is shown
- [ ] No state modifications occur

### US-7: Install and Configure

**Story:** As a new user, I want clear installation instructions so that I can set up ralph quickly.

**Acceptance Criteria:**
- [ ] Getting started guide has Ralph section
- [ ] Prerequisites (Python 3.10+, gh CLI) are listed
- [ ] pip install command is provided
- [ ] Verification command confirms successful setup

---

## Technical Specifications

### Package Structure

```
.claude/ralph/
├── ralph                 # Shell wrapper (entry point, ~10 lines)
├── cli.py               # Main CLI using argparse
├── requirements.txt     # PyYAML only
├── requirements-dev.txt # pytest, pytest-cov, pytest-mock
├── core/
│   ├── __init__.py
│   ├── config.py        # Config loading (replaces config-helpers.sh)
│   ├── state.py         # State management (replaces state-utils.sh)
│   ├── github.py        # GitHub operations via gh CLI
│   └── git.py           # Git operations via git CLI
├── commands/
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
    ├── conftest.py      # Shared fixtures (mock_gh, mock_git, etc.)
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

### CLI Interface

```bash
# Main orchestrator
.claude/ralph/ralph <prd-path> <plan-path> [options]

Options:
  --dry-run           Preview without invoking Claude
  --max-attempts N    Max retries per ticket (default: 3)
  --verbose           Show debug output and stack traces
  --help              Show help message

# Subcommands (internal, called by orchestrator)
.claude/ralph/ralph status <state-file>
.claude/ralph/ralph reset <ticket-id>
```

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| pyyaml | ^6.0 | YAML config file parsing |
| pytest | ^7.0 | Testing framework (dev) |
| pytest-cov | ^4.0 | Coverage reporting (dev) |
| pytest-mock | ^3.0 | Mocking utilities (dev) |

### Shell Wrapper

```bash
#!/bin/bash
# .claude/ralph/ralph
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/cli.py" "$@"
```

### Dependency Mapping (Shell to Python)

| Shell Tool | Python Replacement |
|------------|-------------------|
| `jq` | `json` module (built-in) |
| `gh` | `subprocess.run(['gh', ...])` |
| `git` | `subprocess.run(['git', ...])` |
| `grep/sed/awk` | Python string methods, `re` module |
| `source script.sh` | Python imports |
| `$VAR` / `${VAR}` | `os.environ.get()` |

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| TBD | Package structure setup | Create directory structure, __init__.py files, requirements.txt, shell wrapper | P1 | 2 | - |
| TBD | Core: config.py | Port config-helpers.sh - YAML loading, env var support, typed config class | P1 | 3 | Package setup |
| TBD | Core: state.py | Port state-utils.sh - state file CRUD, atomic writes, ticket status tracking | P1 | 4 | Config |
| TBD | Core: github.py | Create gh CLI wrapper - issue list/get/close, PR create/get | P1 | 3 | Config |
| TBD | Core: git.py | Create git CLI wrapper - branch ops, commit, push, status | P1 | 3 | Config |
| TBD | Core unit tests | Unit tests for config, state, github, git modules | P1 | 3 | All core modules |
| TBD | Command: parse_deps.py | Port parse-plan-deps.sh - parse plan markdown, build dependency graph | P1 | 3 | State |
| TBD | Command: get_next.py | Port get-next-ticket.sh - find next eligible ticket by deps and status | P1 | 3 | State, parse_deps |
| TBD | Command: ticket_start.py | Port ticket-start.sh - create branch, update state | P1 | 3 | Git, State |
| TBD | Command: ticket_done.py | Port ticket-done.sh - mark complete, close issue | P1 | 3 | GitHub, State |
| TBD | Command: mark_blocked.py | Port mark-blocked.sh - block with reason, update state | P1 | 2 | State |
| TBD | Command: ticket_reset.py | Port ticket-reset.sh - reset blocked to pending | P2 | 2 | State |
| TBD | Command: validate.py | Port validate.sh - run configured validation commands | P1 | 3 | Config |
| TBD | Command: pr_flow.py | Port pr-flow.sh - create PR, link issue | P1 | 3 | Git, GitHub |
| TBD | Command: setup.py | Port setup.sh - initialize state from PRD/plan | P1 | 3 | State, parse_deps |
| TBD | Command: status.py | Port status.sh - display current status | P2 | 2 | State |
| TBD | Command: cleanup.py | Port cleanup.sh - archive state, cleanup | P2 | 2 | State |
| TBD | Command: orchestrator.py | Port ralph-prd.sh main loop - full workflow orchestration | P1 | 5 | All commands |
| TBD | CLI entry point | Create cli.py with argparse, connect to orchestrator | P1 | 3 | Orchestrator |
| TBD | Integration tests | Test get_next flow, ticket lifecycle, full orchestrator | P1 | 4 | CLI |
| TBD | Documentation update | Update getting started guide with Ralph installation section | P1 | 2 | CLI |
| TBD | Command updates | Update /ralph-cmd and /ticket-reset to use Python version | P1 | 2 | CLI |
| TBD | Legacy backup | Move shell scripts to ralph-legacy/, update references | P2 | 2 | All tests passing |
| TBD | Final validation | End-to-end test with real PRD/plan, verify feature parity | P1 | 3 | Legacy backup |

*Note: IDs will be filled in after ticket creation via `/ticket`.*

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Model | Tickets at this level |
|-------|-------|-------|----------------------|
| 1 | Trivial | Sonnet | - |
| 2 | Simple | Sonnet | Package setup, mark_blocked, ticket_reset, status, cleanup, docs, command updates, legacy backup |
| 3 | Moderate | Opus | config, github, git, parse_deps, get_next, ticket_start, ticket_done, validate, pr_flow, setup, CLI |
| 4 | Complex | Opus | state, integration tests |
| 5 | Very Hard | Opus | orchestrator |

---

## Testing Requirements

### Test Categories

#### Unit Tests

| Module | Test Focus | Key Test Cases |
|--------|------------|----------------|
| config.py | Config loading | Valid YAML, missing file, env var override, defaults |
| state.py | State CRUD | Create, read, update, atomic write, corruption handling |
| github.py | gh CLI wrapper | List issues, get issue, close issue, create PR, auth errors |
| git.py | git wrapper | Branch create, checkout, commit, push, dirty detection |
| parse_deps.py | Dependency parsing | No deps, linear deps, complex graph, circular detection |

#### Integration Tests

| Flow | Description | Key Scenarios |
|------|-------------|---------------|
| get_next_flow | Ticket selection | Empty queue, deps satisfied, deps blocked, all complete |
| ticket_lifecycle | Start to done | Start -> work -> done, start -> block -> reset -> done |
| orchestrator | Full workflow | Happy path, failures with retry, all blocked, completion |

### Test Coverage Requirements

- Unit test coverage: >90% on core modules
- Integration tests: 100% of happy paths, key error scenarios
- All existing shell test cases must be ported to pytest

### Mocking Strategy

| External System | Mock Approach |
|-----------------|---------------|
| GitHub CLI (gh) | Mock subprocess.run, return fixture JSON |
| Git CLI | Mock subprocess.run, track operations |
| File system | pytest tmp_path fixture |
| Config files | Test fixtures with known values |

---

## Rollout Plan

### Phase 1: Development & Testing (Tickets 1-20)

1. Implement all code in `.claude/ralph/` directory
2. Run pytest suite to validate functionality
3. Do not modify existing shell scripts yet
4. Keep shell scripts as reference for behavior comparison

### Phase 2: Parallel Testing

1. Run new Python version alongside shell version on test PRDs
2. Compare outputs and state files
3. Fix any discrepancies found
4. Document any intentional behavior changes

### Phase 3: Cutover (Tickets 21-24)

1. Move shell scripts to `.claude/scripts/ralph-legacy/`
2. Update `/ralph-cmd` to output Python invocation
3. Update `/ticket-reset` to use Python version
4. Update documentation

### Phase 4: Validation Period

1. Keep legacy scripts for 2 weeks after cutover
2. Monitor for any issues reported
3. Remove legacy scripts after validation period

---

## Rollback Plan

### Triggers

When to rollback:
- Critical bug in Python version that blocks workflows
- Unexpected behavior difference that causes data loss
- Performance regression >10x slower than shell version

### Process

1. **Immediate:** Restore shell wrapper to call legacy scripts
   ```bash
   # .claude/ralph/ralph (rollback version)
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   exec "$SCRIPT_DIR/../scripts/ralph-legacy/ralph-prd.sh" "$@"
   ```

2. **Restore references:** Update /ralph-cmd and /ticket-reset if modified

3. **Document:** Create issue documenting the rollback reason

4. **Fix forward:** Address the issue in Python version, re-test, re-cutover

### Data Safety

- State files use same format - compatible between versions
- No database migrations needed
- Git branches created by either version are identical

---

## Open Questions

All questions resolved in discovery:
- [x] Language choice - Python 3.10+
- [x] Execution interface - Shell wrapper + Python CLI
- [x] Package location - `.claude/ralph/`
- [x] Migration strategy - Full port with comprehensive tests
- [x] External dependencies - PyYAML only (dev: pytest, pytest-cov, pytest-mock)

---

## Out of Scope

*Explicitly NOT included in this port:*

- `.claude/scripts/update-workflow-state.sh` - Used by many slash commands, not Ralph-specific
- `.claude/scripts/statusline.sh` - Used by VS Code settings.json
- `.claude/scripts/create-project.sh` - Used by /new-project command
- Performance optimizations beyond feature parity
- Async/concurrent ticket processing
- Rich CLI output (colors, progress bars) - plain text only for now
- GUI or web interface
- New features not in current shell version

---

## Approval

- [ ] **Product Approved by:** ____________ on YYYY-MM-DD
- [ ] **Engineering Approved by:** ____________ on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
