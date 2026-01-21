# Implementation Plan: GitLab Repository Tool Integration

**Date:** 2026-01-21
**Status:** APPROVED
**PRD:** [docs/prds/2026-01-21-gitlab-repo-tool.md](../prds/2026-01-21-gitlab-repo-tool.md)
**Discovery:** [docs/discovery/2026-01-21-gitlab-repo-tool.md](../discovery/2026-01-21-gitlab-repo-tool.md)
**Author:** Claude (Architect)

---

## Summary

This plan details how to add GitLab support to the SDLC framework by creating a `gitlab.py` module that wraps the `glab` CLI, mirroring the existing `github.py` interface. The implementation follows the existing patterns for swappable tools (like PM tools), using configuration to select between GitHub and GitLab, and updating `pr_flow.py` to use the configured repo tool dynamically.

## Goals

### Primary Goals

- Enable GitLab users to use `/pr` and `/validate` workflows with their self-hosted GitLab instances
- Maintain 100% backward compatibility with existing GitHub workflows
- Achieve >80% test coverage for new GitLab module

### Secondary Goals

- Provide clear error messages when `glab` CLI is missing or not authenticated
- Support environment variable configuration for private GitLab servers

## Non-Goals

- GitLab Issues integration (using Asana/Trello for ticket management)
- GitLab CI/CD pipeline integration
- Direct REST API calls (using `glab` CLI instead)
- Abstract `RepoTool` Protocol (can add later if more tools needed)
- Integration tests against real GitLab instances

## Technical Approach

### Architecture Overview

The implementation introduces a new `gitlab.py` module and configuration support, with `pr_flow.py` updated to use the configured tool:

```
                              +-----------------+
                              |   config.yaml   |
                              | repo.tool: X    |
                              +--------+--------+
                                       |
                                       v
+---------------+            +------------------+
|  pr_flow.py   | <--------> |  get_repo_tool() |
+-------+-------+            +--------+---------+
        |                             |
        v                             v
+-------+-------+            +--------+---------+
| repo_tool API |            |  github | gitlab |
+---------------+            +------------------+
        |                             |
        v                             v
+---------------+            +--------+---------+
|  gh / glab    |            |  subprocess.run  |
+---------------+            +------------------+
```

### Components

| Component | Description | New/Modified |
|-----------|-------------|--------------|
| `.claude/ralph/core/gitlab.py` | Wrapper for `glab` CLI, mirrors `github.py` interface | New |
| `.claude/ralph/core/config.py` | Add `VALID_REPO_TOOLS`, `get_repo_tool_type()` | Modified |
| `.claude/ralph/commands/pr_flow.py` | Use repo tool abstraction instead of direct import | Modified |
| `.claude/ralph/tests/unit/test_gitlab.py` | Unit tests for GitLab module | New |
| `.claude/ralph/tests/unit/test_config.py` | Add tests for repo tool configuration | Modified |

### Key Technical Decisions

#### Decision 1: CLI Wrapper vs Direct API

**Choice:** Wrap `glab` CLI using subprocess calls

**Rationale:**
- Consistent with existing `github.py` pattern
- `glab` handles authentication complexity (OAuth, tokens, self-hosted)
- Simpler implementation - no pagination, rate limiting, or session management
- Easy to test with mocked subprocess

**Alternatives Considered:**
- Direct GitLab REST API calls using `httpx` - rejected due to complexity increase
- Python-gitlab library - rejected due to adding dependency and different pattern

#### Decision 2: Module Interface

**Choice:** Create identical function signatures to `github.py` using GitLab terminology

**Rationale:**
- Allows `pr_flow.py` to call the same functions regardless of tool
- Maps semantically equivalent operations (PR = MR)
- Minimal changes to consuming code

**Function Mapping:**

| GitHub Function | GitLab Function | Notes |
|-----------------|-----------------|-------|
| `create_pull_request()` | `create_merge_request()` | Same signature, returns `MergeRequestResult` |
| `get_pull_request()` | `get_merge_request()` | Same signature |
| `list_pull_requests()` | `list_merge_requests()` | Same signature |
| `merge_pull_request()` | `merge_merge_request()` | Same signature |
| `find_merged_pr()` | `find_merged_mr()` | Same signature |
| `delete_remote_branch()` | `delete_remote_branch()` | Identical |

#### Decision 3: Dynamic Import Strategy

**Choice:** Use factory function `get_repo_module()` in `pr_flow.py`

**Rationale:**
- Avoids import-time dependencies on both modules
- Clean separation - tool selection happens at runtime based on config
- Easy to extend if more tools added later

**Implementation:**
```python
def get_repo_module():
    """Get the configured repo tool module."""
    config_path = Path("config.yaml")
    tool = get_repo_tool_type(config_path)  # Returns "github" or "gitlab"
    if tool == "gitlab":
        from core import gitlab
        return gitlab
    else:
        from core import github
        return github
```

#### Decision 4: Error Class Hierarchy

**Choice:** Mirror GitHub error hierarchy exactly

**Rationale:**
- Allows `pr_flow.py` to catch errors uniformly
- Consistent user experience
- Simplifies error handling in consuming code

**Classes:**
- `GitLabError` (base) - mirrors `GitHubError`
- `GitLabNotInstalledError` - mirrors `GitHubNotInstalledError`
- `GitLabAuthError` - mirrors `GitHubAuthError`

## Implementation Phases

### Phase 1: Foundation (Error Classes + Configuration)

**Goal:** Establish configuration support and error handling infrastructure

**Steps:**
1. Add `GitLabError`, `GitLabNotInstalledError`, `GitLabAuthError` to new `gitlab.py` file
2. Add `VALID_REPO_TOOLS = frozenset({"github", "gitlab"})` to `config.py`
3. Add `get_repo_tool_type()` function to `config.py` (mirrors `get_pm_tool_type()` pattern)
4. Add unit tests for configuration validation

**Exit Criteria:**
- [ ] `get_repo_tool_type()` returns "github" by default
- [ ] `get_repo_tool_type()` returns "gitlab" when configured
- [ ] Invalid `repo.tool` values raise `ConfigError`
- [ ] All config tests pass

### Phase 2: GitLab Module Implementation

**Goal:** Create fully functional GitLab wrapper module

**Steps:**
1. Implement `_run_glab_command()` helper with error handling
2. Implement `MergeRequestResult` dataclass
3. Implement `create_merge_request()`
4. Implement `get_merge_request()`
5. Implement `list_merge_requests()`
6. Implement `merge_merge_request()`
7. Implement `find_merged_mr()`
8. Implement `delete_remote_branch()`

**Exit Criteria:**
- [ ] All MR operations implemented with same signatures as GitHub equivalents
- [ ] Error handling matches GitHub module pattern
- [ ] All GitLab unit tests pass with >80% coverage

### Phase 3: PR Flow Integration

**Goal:** Connect GitLab module to PR workflow

**Steps:**
1. Add `get_repo_module()` factory function to `pr_flow.py`
2. Replace direct `github` imports with dynamic module
3. Update function calls to use module reference
4. Update exception handling to catch both `GitHubError` and `GitLabError`

**Exit Criteria:**
- [ ] PR flow works with `repo.tool: github` (existing tests pass)
- [ ] PR flow works with `repo.tool: gitlab` (new tests pass)
- [ ] No breaking changes to existing workflows

### Phase 4: Documentation and Polish

**Goal:** Complete documentation and final validation

**Steps:**
1. Update `docs/commands/pr.md` to document GitLab configuration
2. Update `docs/commands/validate.md` if needed
3. Add GitLab setup instructions
4. Final test coverage check

**Exit Criteria:**
- [ ] Documentation updated with GitLab configuration
- [ ] All tests pass
- [ ] Test coverage >80% for new code

## Test Strategy

### Unit Tests

- [ ] `test_gitlab.py` - All MR operations with mocked subprocess (mirrors `test_github.py` structure)
- [ ] `test_config.py` - `get_repo_tool_type()` validation and defaults
- [ ] `test_pr_flow.py` - PR flow with both GitHub and GitLab configurations

### Integration Tests

- Not applicable - would require real GitLab instance

### End-to-End Tests

- Not applicable for this feature

### Manual Testing

- [ ] Run `/pr` with `repo.tool: gitlab` against real GitLab server
- [ ] Verify MR creation, merge, and branch deletion work
- [ ] Verify error messages when `glab` not installed
- [ ] Verify error messages when `glab` not authenticated

## Tickets

*These will be created after plan approval:*

| # | Title | Description | Priority | Complexity | Phase | Dependencies |
|---|-------|-------------|----------|------------|-------|--------------|
| 1 | Add GitLab error classes | Create `GitLabError`, `GitLabNotInstalledError`, `GitLabAuthError` in new `gitlab.py` | P1 | 2 | 1 | - |
| 2 | Add repo.tool configuration support | Add `VALID_REPO_TOOLS` and `get_repo_tool_type()` to `config.py` | P1 | 2 | 1 | - |
| 3 | Add config tests for repo tool | Add unit tests for `get_repo_tool_type()` including defaults and validation | P1 | 2 | 1 | 2 |
| 4 | Implement gitlab.py MR operations | Create `_run_glab_command()`, `MergeRequestResult`, and all MR functions | P1 | 3 | 2 | 1 |
| 5 | Add gitlab.py unit tests | Create comprehensive unit tests with mocked subprocess calls | P1 | 3 | 2 | 4 |
| 6 | Update pr_flow.py for repo tool abstraction | Add `get_repo_module()` factory, replace direct imports, update error handling | P1 | 3 | 3 | 2, 4 |
| 7 | Update documentation | Update pr.md and validate.md to document GitLab configuration | P2 | 2 | 4 | 6 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Examples | Model |
|-------|-------|----------|-------|
| 1 | Trivial | Config change, rename, add simple field | Sonnet |
| 2 | Simple | Basic function, simple validation, minor UI tweak | Sonnet |
| 3 | Moderate | New feature with tests, API endpoint, form with validation | Opus |
| 4 | Complex | Multi-component feature, significant refactor, integrations | Opus |
| 5 | Very Hard | Architectural change, complex algorithm, security-critical | Opus |

*Current threshold: 1-2 -> Sonnet, 3-5 -> Opus.*

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `glab` CLI differences from `gh` | Medium | Medium | Comprehensive unit tests with mocked responses matching real `glab` output |
| Old GitLab versions missing features | Low | Medium | Document minimum supported version, test graceful degradation |
| Breaking existing GitHub workflows | Low | High | Run all existing tests before merging, maintain separate modules |
| Environment variable conflicts | Low | Low | Use GitLab-specific env vars (`GITLAB_HOST`, `GITLAB_TOKEN`) |

## Environment Considerations

### Local Development

- **Primary OS:** Linux (WSL2), macOS, Windows
- **Known Limitations:** Requires `glab` CLI installed and authenticated

### CI Environment

- **Platform:** GitHub Actions (for SDLC framework repo)
- **Considerations:** Cannot run integration tests against real GitLab

## Dependencies

### External Dependencies

- `glab` CLI >= 1.30.0 (user-installed, not a Python package)

### Internal Dependencies

- `core/config.py` (for configuration loading)
- `core/git.py` (for branch operations - already exists)

### Blocking Items

- None - all prerequisites are met

## Open Questions

All questions resolved during discovery and PRD phases:

- [x] CLI vs API? - Use `glab` CLI
- [x] Self-hosted support? - Yes, via `GITLAB_HOST` environment variable
- [x] Issue operations? - No, using Asana/Trello for tickets
- [x] Configuration method? - Environment variables for credentials, config.yaml for tool selection

## Success Criteria

*How do we know we're done?*

- [ ] `repo.tool: gitlab` configuration recognized and validated
- [ ] `gitlab.py` implements all MR operations with matching interface
- [ ] `pr_flow.py` works with both GitHub and GitLab
- [ ] All existing GitHub tests pass (no regression)
- [ ] GitLab tests achieve >80% coverage
- [ ] Documentation updated with GitLab setup instructions

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

- [ ] All tests pass (unit, integration, E2E)
- [ ] Code committed and pushed
- [ ] PR created and merged (or local merge for local repos)
- [ ] Create execution report: `/execution-report`
- [ ] Create system review: `/system-review`

---

## Approval

- [ ] **Approved by:** {name} on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted.*
