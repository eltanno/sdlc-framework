# PRD: GitLab Repository Tool Integration

**Date:** 2026-01-21
**Status:** APPROVED
**Discovery:** [docs/discovery/2026-01-21-gitlab-repo-tool.md](../discovery/2026-01-21-gitlab-repo-tool.md)
**Plan:** TBD (to be created after PRD approval)
**Owner:** Claude (Architect)
**Stakeholders:** SDLC Framework Users

---

## Discovery Reference

**Note:** This PRD is for ONE feature/epic within this iteration. The discovery document contains the iteration's scope and vision.

**Iteration Vision:**
The SDLC framework currently only supports GitHub for repository operations. This iteration adds GitLab support to enable teams using self-hosted GitLab instances to leverage the full SDLC workflow.

**How This Feature Fits:**
This feature implements the core GitLab integration by creating a `gitlab.py` module that wraps the `glab` CLI, mirroring the existing `github.py` interface. It enables teams with private GitLab servers to use `/pr`, `/validate`, and merge workflows while continuing to use their preferred ticket management system (Asana, Trello, etc.).

---

## Executive Summary

### Problem Statement

Teams using self-hosted GitLab servers cannot use the SDLC framework's PR workflow. The framework's repository operations (`/pr`, `/validate`, merge) are hardcoded to use GitHub via the `gh` CLI. This excludes a significant portion of potential users who prefer or are required to use GitLab.

### Solution Summary

Create a `gitlab.py` module that wraps the `glab` CLI with the same interface as `github.py`. Add configuration support for `repo.tool: gitlab` in `config.yaml`. Update `pr_flow.py` to use the configured repo tool instead of directly importing the GitHub module. This approach mirrors the existing pattern for swappable PM tools and minimizes code changes.

### Success Metrics

| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| GitLab MR operations supported | 0 | 5 (create, merge, list, get, delete branch) | Feature completion |
| Existing GitHub tests passing | 100% | 100% | CI pipeline |
| GitLab module test coverage | 0% | >80% | pytest-cov |
| Breaking changes to existing workflows | N/A | 0 | Manual verification |

---

## Requirements

### Functional Requirements

#### FR-1: GitLab Module Implementation

**Priority:** P1 (Must Have)

**Description:** Create a `gitlab.py` module in `.claude/ralph/core/` that wraps the `glab` CLI and provides the same public interface as `github.py` for MR (Merge Request) operations.

**Acceptance Criteria:**
- [ ] Given the `glab` CLI is installed and authenticated, when `create_merge_request(title, body)` is called, then a new MR is created on GitLab and the MR URL and number are returned
- [ ] Given an existing MR number, when `merge_merge_request(mr_number, strategy="squash")` is called, then the MR is merged using the specified strategy
- [ ] Given no parameters, when `list_merge_requests()` is called, then all open MRs for the repository are returned as a list of dictionaries
- [ ] Given a branch name, when `list_merge_requests(head=branch)` is called, then only MRs from that source branch are returned
- [ ] Given an MR number, when `get_merge_request(mr_number)` is called, then the MR details are returned including number, title, state, and URL
- [ ] Given a search term, when `find_merged_mr(search_term)` is called, then the MR number of a matching merged MR is returned (or None)
- [ ] Given a branch name, when `delete_remote_branch(branch_name)` is called, then the branch is deleted from the remote

#### FR-2: GitLab Error Handling

**Priority:** P1 (Must Have)

**Description:** Implement custom exception classes for GitLab operations that mirror the GitHub error hierarchy.

**Acceptance Criteria:**
- [ ] Given the `glab` CLI is not installed, when any GitLab function is called, then `GitLabNotInstalledError` is raised with a helpful message including installation instructions
- [ ] Given the `glab` CLI is not authenticated, when any GitLab function is called, then `GitLabAuthError` is raised with a message explaining how to authenticate
- [ ] Given any other `glab` command failure, when a GitLab function is called, then `GitLabError` is raised with the command and stderr in the message

#### FR-3: Configuration Support

**Priority:** P1 (Must Have)

**Description:** Add `repo.tool` configuration option to specify which repository tool to use (github or gitlab).

**Acceptance Criteria:**
- [ ] Given `repo.tool: gitlab` in config.yaml, when `get_repo_tool_type()` is called, then "gitlab" is returned
- [ ] Given `repo.tool: github` in config.yaml, when `get_repo_tool_type()` is called, then "github" is returned
- [ ] Given no `repo.tool` setting in config.yaml, when `get_repo_tool_type()` is called, then "github" is returned (default)
- [ ] Given an invalid `repo.tool` value (e.g., "bitbucket"), when configuration is loaded, then `ConfigError` is raised with valid options listed

#### FR-4: PR Flow Integration

**Priority:** P1 (Must Have)

**Description:** Update `pr_flow.py` to use the configured repo tool instead of directly importing `github`.

**Acceptance Criteria:**
- [ ] Given `repo.tool: github` in config.yaml, when `pr_flow()` is executed, then all operations use the `github` module (existing behavior)
- [ ] Given `repo.tool: gitlab` in config.yaml, when `pr_flow()` is executed, then all operations use the `gitlab` module
- [ ] Given `repo.tool: gitlab` and a successful PR flow, when the PR is merged, then the MR URL uses GitLab format (e.g., `https://gitlab.example.com/group/project/-/merge_requests/123`)

#### FR-5: Environment Variable Support

**Priority:** P1 (Must Have)

**Description:** Support environment variables for GitLab authentication and server configuration.

**Acceptance Criteria:**
- [ ] Given `GITLAB_HOST` environment variable is set to "gitlab.example.com", when `glab` commands are executed, then they target the specified GitLab instance
- [ ] Given `GITLAB_TOKEN` environment variable is set, when `glab` commands are executed, then they use the token for authentication
- [ ] Given neither environment variable is set but `glab` is logged in via `glab auth login`, when `glab` commands are executed, then they succeed using the stored credentials

### Non-Functional Requirements

#### NFR-1: Performance

- MR creation should complete within 10 seconds (network permitting)
- MR listing should complete within 5 seconds for repositories with <100 open MRs

#### NFR-2: Reliability

- All GitLab operations must be idempotent or clearly documented as non-idempotent
- Failed operations must provide actionable error messages
- Network timeouts must not leave the system in an inconsistent state

#### NFR-3: Security

- No credentials stored in code or logs
- Environment variables used for sensitive configuration
- No plaintext tokens in error messages or stack traces

#### NFR-4: Compatibility

- Must work with GitLab Community Edition (self-hosted)
- Must work with GitLab Enterprise Edition (self-hosted)
- Should work with gitlab.com (SaaS)
- Graceful degradation if GitLab version lacks specific features

---

## User Stories

### US-1: GitLab User Creates MR via SDLC Workflow

**Story:** As a developer using a self-hosted GitLab instance, I want to run `/pr` to create a merge request so that I can use the SDLC framework's automated PR workflow.

**Acceptance Criteria:**
- [ ] `/pr` command creates an MR on GitLab when `repo.tool: gitlab` is configured
- [ ] MR title includes ticket ID in the format `[TASK-XXX] Description`
- [ ] MR body includes validation summary and commit information
- [ ] MR URL is displayed after creation

**Notes:** Requires `glab` CLI to be installed and authenticated.

### US-2: GitLab User Merges MR via SDLC Workflow

**Story:** As a developer, I want the SDLC framework to merge my GitLab MR after validation passes so that I can complete the development cycle.

**Acceptance Criteria:**
- [ ] After successful validation, MR is automatically merged (unless `--no-merge` flag is used)
- [ ] Squash merge is used by default
- [ ] Source branch is deleted after merge (unless protected)
- [ ] Local checkout returns to detached HEAD at main

### US-3: Developer Validates GitLab Setup

**Story:** As a developer setting up the SDLC framework with GitLab, I want clear error messages if my configuration is incorrect so that I can quickly resolve issues.

**Acceptance Criteria:**
- [ ] If `glab` is not installed, error message includes installation link
- [ ] If `glab` is not authenticated, error message explains how to run `glab auth login`
- [ ] If `GITLAB_HOST` is needed but not set, error message explains the environment variable

---

## Technical Specifications

### API Changes

#### New Module: `.claude/ralph/core/gitlab.py`

| Function | Signature | Description |
|----------|-----------|-------------|
| `create_merge_request` | `(title: str, body: str, base: str = None, draft: bool = False) -> MergeRequestResult` | Create a new MR |
| `get_merge_request` | `(mr_number: int) -> dict` | Get MR details |
| `list_merge_requests` | `(head: str = None, state: str = None) -> list[dict]` | List MRs |
| `merge_merge_request` | `(mr_number: int, strategy: str = "squash") -> None` | Merge an MR |
| `find_merged_mr` | `(search_term: str) -> int \| None` | Find merged MR by title |
| `delete_remote_branch` | `(branch_name: str, remote: str = "origin") -> None` | Delete remote branch |

**Note:** Issue operations (list_issues, get_issue, close_issue, find_issue_by_title) are NOT included - ticket management uses Asana/Trello, not GitLab Issues.

#### Modified Files

| File | Change |
|------|--------|
| `.claude/ralph/core/config.py` | Add `VALID_REPO_TOOLS`, `get_repo_tool_type()` function |
| `.claude/ralph/commands/pr_flow.py` | Use repo tool abstraction instead of direct `github` import |

### Data Model Changes

#### New Dataclasses

```python
@dataclass
class MergeRequestResult:
    """Result of creating a merge request.

    Attributes:
        url: Full URL of the created MR
        number: MR number (iid in GitLab terminology)
    """
    url: str
    number: int
```

#### New Exception Classes

```python
class GitLabError(Exception):
    """Base exception for GitLab operations."""
    pass

class GitLabNotInstalledError(GitLabError):
    """Raised when glab CLI is not installed."""
    pass

class GitLabAuthError(GitLabError):
    """Raised when glab CLI is not authenticated."""
    pass
```

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `glab` | >=1.30.0 | GitLab CLI (external, user-installed) |

No new Python package dependencies required.

---

## Tickets

| ID | Title | Description | Priority | Complexity | Dependency |
|----|-------|-------------|----------|------------|------------|
| SDLC-0067 | Create gitlab.py module with MR operations | Implement core GitLab wrapper module with create/get/list/merge/find MR functions | P1 | 3 | - |
| SDLC-0068 | Add GitLab error classes | Implement GitLabError, GitLabNotInstalledError, GitLabAuthError exceptions | P1 | 2 | - |
| SDLC-0069 | Add repo.tool configuration support | Add VALID_REPO_TOOLS constant and get_repo_tool_type() function to config.py | P1 | 2 | - |
| SDLC-0070 | Update pr_flow.py for repo tool abstraction | Modify pr_flow.py to use configured repo tool instead of hardcoded github import | P1 | 3 | SDLC-0067, SDLC-0069 |
| SDLC-0071 | Add gitlab.py unit tests | Create comprehensive unit tests with mocked subprocess calls | P1 | 3 | SDLC-0067, SDLC-0068 |
| SDLC-0072 | Add config.py tests for repo tool | Add tests for get_repo_tool_type() including defaults and validation | P1 | 2 | SDLC-0069 |
| SDLC-0073 | Update slash command documentation | Update pr.md and validate.md to document GitLab configuration | P2 | 2 | SDLC-0067 - SDLC-0070 |

**Complexity Score (1-5):** Determines which AI model handles implementation.

| Score | Level | Model |
|-------|-------|-------|
| 1 | Trivial | Sonnet |
| 2 | Simple | Sonnet |
| 3 | Moderate | Opus |
| 4 | Complex | Opus |
| 5 | Very Hard | Opus |

---

## Testing Requirements

### Test Cases

| ID | Requirement | Description | Steps | Expected Result |
|----|-------------|-------------|-------|-----------------|
| TC-1 | FR-1 | Create MR returns URL and number | 1. Mock glab mr create output<br>2. Call create_merge_request() | MergeRequestResult with valid URL and number |
| TC-2 | FR-1 | Merge MR with squash strategy | 1. Mock glab mr merge<br>2. Call merge_merge_request(123, "squash") | No exception, subprocess called with --squash |
| TC-3 | FR-1 | List MRs filters by head branch | 1. Mock glab mr list output<br>2. Call list_merge_requests(head="feature") | Only MRs from feature branch returned |
| TC-4 | FR-2 | Missing glab raises GitLabNotInstalledError | 1. Mock subprocess to raise FileNotFoundError<br>2. Call any gitlab function | GitLabNotInstalledError with install instructions |
| TC-5 | FR-2 | Auth failure raises GitLabAuthError | 1. Mock glab to return auth error<br>2. Call any gitlab function | GitLabAuthError with auth instructions |
| TC-6 | FR-3 | Default repo tool is github | 1. Load config without repo.tool<br>2. Call get_repo_tool_type() | Returns "github" |
| TC-7 | FR-3 | Invalid repo tool raises ConfigError | 1. Set repo.tool: bitbucket<br>2. Call get_repo_tool_type() | ConfigError with valid options |
| TC-8 | FR-4 | PR flow uses gitlab module when configured | 1. Set repo.tool: gitlab<br>2. Execute pr_flow() | gitlab.create_merge_request called |

### Test Coverage Requirements

- Unit test coverage: > 80% for gitlab.py
- Unit test coverage: > 80% for config.py changes
- Integration tests: N/A (would require real GitLab instance)
- E2E tests: Manual verification with real GitLab server

---

## Rollout Plan

### Phase 1: Implementation and Testing

- Implement all tickets in dependency order
- Run unit tests with mocked subprocess
- Manual testing with real GitLab instance (developer verification)

### Phase 2: Documentation

- Update CLAUDE.md if needed
- Update slash command documentation
- Add GitLab setup instructions to docs/

### Phase 3: Release

- Merge to main
- Announce feature availability
- Monitor for issues

---

## Rollback Plan

### Triggers

When to rollback:
- Critical bug in github.py (existing functionality broken)
- Configuration parsing breaks existing workflows
- Unexpected interactions between github/gitlab modules

### Process

1. Revert the merge commit on main
2. Re-run tests to verify github functionality restored
3. Create bug ticket for the issue
4. Notify stakeholders of rollback

---

## Open Questions

All questions resolved during discovery:
- [x] CLI vs API? - Use `glab` CLI
- [x] Self-hosted support? - Yes, via GITLAB_HOST
- [x] Issue operations? - No, using Asana/Trello

---

## Out of Scope

*Explicitly list what this PRD does NOT cover:*

- GitLab Issues integration (using Asana/Trello for ticket management)
- GitLab CI/CD integration
- GitLab REST API direct calls (using glab CLI)
- RepoTool Protocol abstraction (can add later if more repo tools needed)
- Integration tests against real GitLab (requires infrastructure)
- Bitbucket or other repo tool support (future feature)

---

## Approval

- [ ] **Product Approved by:** {name} on YYYY-MM-DD
- [ ] **Engineering Approved by:** {name} on YYYY-MM-DD

*Change status to APPROVED when reviewed and accepted by all stakeholders.*
