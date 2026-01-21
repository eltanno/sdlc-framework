# Discovery: GitLab Repo Tool Integration

**Date:** 2026-01-21
**Status:** APPROVED
**Author:** Claude (Discovery Session)

---

## Problem Statement

The SDLC framework currently only supports GitHub for repository operations (creating PRs, merging, etc.). Users with private GitLab servers cannot use the framework's `/pr`, `/validate`, and merge workflows.

Adding GitLab support enables teams using self-hosted GitLab instances to leverage the full SDLC workflow while continuing to use their preferred ticket management system (Asana, Trello, etc.).

## Current State

### How It Works Today

The framework uses `github.py` to wrap the `gh` CLI for all repository operations:

| Operation | Function | CLI Command |
|-----------|----------|-------------|
| Create PR | `create_pull_request()` | `gh pr create` |
| Merge PR | `merge_pull_request()` | `gh pr merge` |
| List PRs | `list_pull_requests()` | `gh pr list` |
| Get PR | `get_pull_request()` | `gh pr view` |
| Find merged PR | `find_merged_pr()` | `gh pr list --state merged` |
| Delete branch | `delete_remote_branch()` | `git push --delete` |

The `pr_flow.py` command orchestrates these operations during the `/pr` and merge phases.

### Pain Points

- No support for GitLab repositories
- Teams using private GitLab servers cannot use the SDLC workflow for PR management
- No abstraction layer - `pr_flow.py` directly imports `github` module

### Previous Attempts

None - this is a new feature request.

## Research Findings

### Codebase Analysis

#### Relevant Files

| File | Purpose | Notes |
|------|---------|-------|
| `.claude/ralph/core/github.py` | GitHub CLI wrapper | 418 lines, wraps `gh` CLI |
| `.claude/ralph/core/git.py` | Git CLI wrapper | Branch/commit operations |
| `.claude/ralph/commands/pr_flow.py` | PR workflow orchestration | Main consumer of github.py |
| `.claude/ralph/core/config.py` | Configuration management | Will need `repo.tool` option |
| `.claude/commands/pr.md` | PR slash command | References repo URLs |
| `.claude/commands/validate.md` | Validation command | Reads repo type from config |

#### Existing Patterns

The codebase already has a pattern for swappable tools via configuration:

```yaml
# config.yaml - existing pattern for PM tools
pm:
  tool: asana  # or github, trello, linear, none
```

The same pattern should be used for repo tools:

```yaml
repo:
  tool: gitlab  # or github (default)
```

The `AsanaPM` implementation provides a good reference:
- Environment variables for credentials (`ASANA_ACCESS_TOKEN`, etc.)
- Wrapper around external CLI/API
- Error handling with custom exceptions
- Unit tests with mocked HTTP/subprocess calls

#### Dependencies

Files that will need updates:

| File | Change Required |
|------|-----------------|
| `core/config.py` | Add `VALID_REPO_TOOLS`, `get_repo_tool()` |
| `commands/pr_flow.py` | Use repo tool abstraction instead of direct github import |
| `commands/orchestrator.py` | Add `create_repo_tool()` factory function |
| `.claude/commands/pr.md` | Support GitLab MR URLs |
| `.claude/commands/validate.md` | Support GitLab repo type |

### External Research

#### GitLab CLI (`glab`)

GitLab's official CLI tool mirrors `gh` closely:

| GitHub (`gh`) | GitLab (`glab`) | Notes |
|---------------|-----------------|-------|
| `gh pr create` | `glab mr create` | MR = Merge Request |
| `gh pr merge --squash` | `glab mr merge --squash` | Same merge strategies |
| `gh pr list --head branch` | `glab mr list --source-branch branch` | Different flag name |
| `gh pr view 123 --json` | `glab mr view 123 -F json` | Different JSON flag |
| `gh pr list --state merged` | `glab mr list --merged` | Different state filter |

**Self-hosted GitLab support:**

```bash
# Configure glab for private server
glab auth login --hostname gitlab.yourcompany.com

# Or via environment variables
export GITLAB_HOST=gitlab.yourcompany.com
export GITLAB_TOKEN=<personal-access-token>
```

#### Documentation Review

- [glab CLI documentation](https://gitlab.com/gitlab-org/cli/-/tree/main/docs)
- [GitLab MR API](https://docs.gitlab.com/ee/api/merge_requests.html)
- [glab installation](https://gitlab.com/gitlab-org/cli#installation)

## Key Questions

All questions resolved during discovery:

1. [x] **CLI vs API?** - Use `glab` CLI (mirrors `gh` pattern, handles auth)
2. [x] **Self-hosted support?** - Yes, via `GITLAB_HOST` environment variable
3. [x] **Issue operations?** - No, using Asana for tickets (repo operations only)
4. [x] **Configuration method?** - Environment variables (`GITLAB_HOST`, `GITLAB_TOKEN`)

## Constraints

### Technical Constraints

- Requires `glab` CLI to be installed on the system
- Must work with self-hosted GitLab (not just gitlab.com)
- GitLab version unknown - implementation must handle gracefully if features missing
- Network access required to reach private GitLab server

### Business Constraints

- Must maintain feature parity with GitHub for MR operations
- Cannot break existing GitHub workflows
- Asana remains the ticket management system (no GitLab Issues integration)

### Timeline Constraints

- None specified

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `glab` CLI differences break assumptions | Medium | Medium | Comprehensive unit tests with mocked responses |
| Old GitLab version missing features | Low | Medium | Feature detection, graceful degradation |
| Auth flow differences between gh/glab | Low | Low | Document setup steps clearly |
| `glab` not installed on user systems | Medium | High | Clear error message with install instructions |

## Options Considered

### Option 1: `glab` CLI Wrapper (Recommended)

**Description:** Create `gitlab.py` module that wraps `glab` CLI, mirroring `github.py` interface.

**Pros:**
- Consistent with existing `github.py` pattern
- `glab` handles authentication complexity
- Simple subprocess calls, easy to test
- Supports self-hosted GitLab out of the box

**Cons:**
- Requires users to install `glab` CLI
- Dependent on `glab` CLI compatibility

### Option 2: GitLab REST API Direct

**Description:** Use `httpx` to call GitLab API directly (like `asana_pm.py`).

**Pros:**
- No CLI dependency
- Full control over API calls

**Cons:**
- More complex implementation (pagination, rate limits, error handling)
- Must handle auth token management
- Different pattern from `github.py`

### Option 3: Abstract RepoTool Protocol

**Description:** Create a `RepoTool` Protocol (like `PMTool`) with GitHub/GitLab implementations.

**Pros:**
- Clean abstraction for future repo tools
- Type-safe interface

**Cons:**
- Over-engineering for just two implementations
- More refactoring required

## Recommendation

**Option 1: `glab` CLI Wrapper**

This approach:
- Mirrors the existing `github.py` pattern exactly
- Minimizes code changes (just add `gitlab.py`, update config)
- Leverages `glab`'s built-in auth and self-hosted support
- Is the simplest path to feature parity

The abstraction (Option 3) can be added later if more repo tools are needed.

## Scope

### In Scope

| Feature | Description |
|---------|-------------|
| `gitlab.py` module | Wrapper for `glab` CLI with same interface as `github.py` |
| MR operations | create, merge, list, get, find merged |
| Branch operations | delete remote branch |
| Configuration | `repo.tool: gitlab` in config.yaml |
| Environment variables | `GITLAB_HOST`, `GITLAB_TOKEN` |
| Error handling | `GitLabError`, `GitLabNotInstalledError`, `GitLabAuthError` |
| Unit tests | Mocked `glab` subprocess calls |
| Integration with pr_flow | Update to use configured repo tool |

### Out of Scope

| Feature | Reason |
|---------|--------|
| GitLab Issues | Using Asana for ticket management |
| GitLab CI/CD | Not part of SDLC workflow |
| Direct API calls | Using `glab` CLI instead |
| RepoTool Protocol | Can add later if needed |
| Integration tests | Would require real GitLab instance |

## Related PRDs

**This section tracks feature-specific PRDs created from this discovery:**

| PRD | Feature | Status | Created |
|-----|---------|--------|---------|
| _None yet_ | - | - | - |

_When creating a new PRD with `/prd`, add it to this table to maintain traceability._

## Next Steps

After this discovery is approved:

1. Run `/prd gitlab-repo-tool` to create the PRD with acceptance criteria
2. Run `/plan` to create the implementation plan
3. Run `/ticket` to create tasks
4. Implement with `/implement`

---

## Approval

- [x] **Approved by:** User on 2026-01-21

*Change status to APPROVED when reviewed and accepted.*
