# Project Discovery: Ralph Loop Python Port

**Last Updated:** 2026-01-19
**Status:** READY FOR PLANNING
**Revisions:** 1

---

## Vision

### What We're Building

Port the Ralph orchestrator loop from shell scripts (~5,830 lines across 16 files) to Python. The goal is to maintain identical functionality while gaining testability, maintainability, and reliability.

### Problem Statement

The Ralph loop scripts have grown into an integral and complex procedure. Shell scripting limitations make it:
- **Hard to test** - No unit testing framework for bash
- **Prone to bugs** - Changes frequently introduce regressions
- **Difficult to maintain** - Complex control flow in shell is hard to read/modify
- **Not portable** - Bash-specific features may not work everywhere

### Target Users

- Developers using the SDLC framework
- Multiple users across different environments (Linux, macOS, WSL)

### Success Criteria

1. **Feature parity** - All current functionality preserved
2. **High test coverage** - Unit tests for functions, integration tests for flows
3. **Same invocation pattern** - `.claude/ralph/ralph <prd> <plan>` works like before
4. **Documentation** - Getting started guide with installation instructions
5. **Zero regressions** - Existing workflows continue to work

---

## Scope

### In Scope

**Scripts to Port (16 files, ~5,830 lines):**

| Script | Lines | Purpose |
|--------|-------|---------|
| `ralph-prd.sh` | 1,439 | Main orchestrator loop |
| `state-utils.sh` | 693 | State file management |
| `ticket-start.sh` | 385 | Start work on ticket |
| `get-next-ticket.sh` | 362 | Find next available ticket |
| `config-helpers.sh` | 343 | Config loading from YAML |
| `pr-flow.sh` | 272 | PR creation workflow |
| `validate.sh` | 247 | Run validation checks |
| `ticket-done.sh` | 225 | Mark ticket complete |
| `setup.sh` | 219 | Initialize ralph for a PRD |
| `parse-plan-deps.sh` | 202 | Parse ticket dependencies |
| `mark-blocked.sh` | 168 | Mark ticket as blocked |
| `cleanup.sh` | 119 | Clean up after completion |
| `ticket-reset.sh` | 113 | Reset blocked ticket |
| `status.sh` | 87 | Show current status |

**Test files to replace with pytest:**
- `test-get-next-ticket.sh` (384 lines)
- `test-ticket-done.sh` (304 lines)
- `test-mark-blocked.sh` (268 lines)

**Commands to update:**
- `/ralph-cmd` - Update command output to show Python invocation
- `/ticket-reset` - Update script path references

**Documentation to create/update:**
- Getting started guide with `requirements.txt` installation instructions

### Out of Scope

**Scripts to KEEP as shell (not part of this port):**
- `.claude/scripts/update-workflow-state.sh` - Used by many slash commands
- `.claude/scripts/statusline.sh` - Used by settings.json for statusline
- `.claude/scripts/create-project.sh` - Used by /new-project command

These may be ported later but are not dependent on Ralph.

### Must Have vs Nice to Have

| Must Have | Nice to Have |
|-----------|--------------|
| All 16 scripts ported | Type hints throughout |
| Unit tests for all functions | 100% test coverage |
| Integration tests for flows | Performance improvements |
| Same CLI interface | Async operations |
| Installation documentation | Rich CLI output (colors) |

---

## Technical Approach

### Language Choice: Python

**Rationale:**
- Lower learning curve (most devs know Python)
- Excellent testing ecosystem (pytest)
- Good subprocess handling for git/gh commands
- Built-in JSON support (replaces jq)
- More readable than shell for complex logic

### Execution Interface

**Entry point:** `.claude/ralph/ralph` (thin shell wrapper)

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/cli.py" "$@"
```

**Why this approach:**
- Same invocation pattern as current shell scripts
- No pip install required for users (just Python 3.8+)
- No PYTHONPATH manipulation
- Works across Linux, macOS, WSL

### Package Structure

```
.claude/ralph/
├── ralph                 # Shell wrapper (entry point)
├── cli.py               # Main CLI (argparse)
├── requirements.txt     # External dependencies (PyYAML)
├── core/
│   ├── __init__.py
│   ├── config.py        # Config loading (replaces config-helpers.sh)
│   ├── state.py         # State management (replaces state-utils.sh)
│   ├── github.py        # GitHub operations (gh CLI wrapper)
│   └── git.py           # Git operations
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
    ├── conftest.py      # Shared fixtures
    ├── unit/
    │   ├── test_config.py
    │   ├── test_state.py
    │   ├── test_github.py
    │   └── test_git.py
    └── integration/
        ├── test_get_next_flow.py
        ├── test_ticket_lifecycle.py
        └── test_orchestrator.py
```

### Dependencies

**External (in requirements.txt):**
- `pyyaml` - For config.yaml parsing

**Standard library (no install):**
- `json` - Replaces jq
- `subprocess` - For git/gh commands
- `pathlib` - File path handling
- `argparse` - CLI argument parsing
- `dataclasses` - Data structures
- `typing` - Type hints

**Dev dependencies (requirements-dev.txt):**
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

### Dependency Mapping

| Shell Dependency | Python Replacement |
|-----------------|-------------------|
| `jq` | `json` module (built-in) |
| `gh` | `subprocess.run(['gh', ...])` |
| `git` | `subprocess.run(['git', ...])` |
| `grep/sed/awk` | Python string methods, `re` module |
| `source script.sh` | Python imports |

---

## Testing Strategy

### Unit Tests

Test individual functions in isolation:

```python
# Example: test_config.py
def test_get_instance_label_from_env(monkeypatch):
    monkeypatch.setenv('RALPH_LABEL', 'ralph-worker-1')
    config = Config.load()
    assert config.instance_label == 'ralph-worker-1'

def test_get_instance_label_default():
    config = Config.load()
    assert config.instance_label is None
```

### Integration Tests

Test complete flows with mocked external commands:

```python
# Example: test_ticket_lifecycle.py
def test_ticket_start_to_done(mock_gh, mock_git, tmp_path):
    """Test complete ticket lifecycle."""
    # Setup
    mock_gh.issue_list.return_value = [{'number': 42, 'title': '[PROJ-001] Feature'}]

    # Get next ticket
    result = get_next_ticket()
    assert result.ticket_id == 'PROJ-001'

    # Start ticket
    ticket_start('PROJ-001', issue_number=42)
    mock_git.checkout.assert_called_with('-b', 'feature/PROJ-001-feature')

    # Complete ticket
    ticket_done('PROJ-001', pr_number=99, issue_number=42)
    mock_gh.issue_close.assert_called_with(42)
```

### Mocking Strategy

- **GitHub CLI (`gh`):** Mock subprocess calls, return fixture JSON
- **Git:** Mock subprocess calls, track branch/commit operations
- **File system:** Use pytest's `tmp_path` fixture
- **Config:** Use test fixtures with known values

### Coverage Target

- Unit tests: 90%+ coverage on core modules
- Integration tests: Cover all happy paths and key error scenarios

---

## Migration Plan

### Phase 1: Setup & Core

1. Create package structure
2. Port `config-helpers.sh` → `core/config.py`
3. Port `state-utils.sh` → `core/state.py`
4. Create `core/github.py` and `core/git.py` wrappers
5. Write unit tests for core modules

### Phase 2: Commands

1. Port each command script to Python
2. Write unit tests for each command
3. Order by dependency (config → state → commands)

### Phase 3: Orchestrator

1. Port `ralph-prd.sh` → `commands/orchestrator.py`
2. Write integration tests for full flows
3. Create CLI entry point

### Phase 4: Integration & Documentation

1. Create shell wrapper entry point
2. Update `/ralph-cmd` and `/ticket-reset` commands
3. Write installation section in getting started guide
4. End-to-end testing with real PRD/plan

### Phase 5: Cutover

1. Move old shell scripts to `.claude/scripts/ralph-legacy/` (backup)
2. Update all references to use new Python version
3. Remove legacy scripts after validation period

---

## Documentation Requirements

### Getting Started Guide Update

Add to `docs/getting-started.md` (or create if doesn't exist):

```markdown
## Ralph Orchestrator Setup

### Prerequisites

- Python 3.8 or higher
- GitHub CLI (`gh`) authenticated

### Installation

1. Install Python dependencies:

   ```bash
   pip install -r .claude/ralph/requirements.txt
   ```

   Or with a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r .claude/ralph/requirements.txt
   ```

2. Verify installation:

   ```bash
   .claude/ralph/ralph --help
   ```

### Running Ralph

```bash
.claude/ralph/ralph <prd-path> <plan-path> [options]

# Example:
.claude/ralph/ralph docs/prds/2026-01-19-feature.md docs/plans/2026-01-19-feature.md

# Options:
#   --dry-run         Preview without invoking Claude
#   --max-attempts N  Max retries per ticket (default: 3)
```
```

---

## Risks & Assumptions

### Assumptions

- Python 3.8+ is available on target systems
- Users can install pip packages (or have PyYAML already)
- GitHub CLI (`gh`) behavior is consistent across versions
- Current shell script behavior is correct (we're preserving it, not fixing bugs)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Subtle behavior differences | High | Comprehensive integration tests |
| Missing edge cases | Medium | Port existing test-*.sh test cases |
| Python not installed | Low | Document in prerequisites |
| PyYAML version conflicts | Low | Pin version in requirements.txt |

---

## Open Questions

- [x] Language choice → Python
- [x] Execution interface → Shell wrapper + Python CLI
- [x] Package location → `.claude/ralph/`
- [x] Migration strategy → Full port with tests
- [x] Python minimum version → **3.10+**

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-01-19 | Initial discovery session |
