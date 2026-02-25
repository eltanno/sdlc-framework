# Ralph Loop - Launch Ralph orchestrator with concurrent support

**Launch one or more Ralph implementation loops and monitor them.**

## Important Rules

- **DO NOT** make fixes, edits, or intervene in any loop in any way
- **DO NOT** run code, install packages, or modify files while loops are running
- **ONLY** observe log files and report progress to the user
- If a loop encounters errors, report them — do not attempt to fix them
- Each loop runs as a separate subprocess — crashes in one do not affect others

## Action

### Phase 1: Detect PRD and Plan

1. Find the most recent PRD and matching plan from `docs/prds/` and `docs/plans/` (or use arguments if provided)
2. Show the user the detected PRD and plan paths and ask for confirmation before proceeding
3. Read `config.yaml` to get `git.default_branch` and `ralph.max_concurrent_loops`
4. The loop count is `ralph.max_concurrent_loops` from config (no assessment needed). Display it to the user and ask for confirmation or override (1-4).

### Phase 2: Launch

Based on the confirmed loop count:

#### If loop count == 1 (Single-Loop Mode)

5. Run the existing single-loop flow — no worktree setup needed:
   ```bash
   mkdir -p tmp
   .claude/ralph/ralph run <prd> <plan> 2>&1 | tee tmp/ralph-0-$(date +%Y-%m-%d).log
   ```
   Launch with Bash `run_in_background: true`.

6. Skip to **Phase 3: Monitor** (single log file mode).

#### If loop count > 1 (Concurrent Mode)

5. Setup worktrees and sync .env files:
   ```bash
   cd <project_root> && PYTHONPATH=.claude/ralph:$PYTHONPATH python3 -c "
   from pathlib import Path
   from commands.concurrent import WorktreeManager, EnvSyncer

   project_root = Path('.')
   manager = WorktreeManager(project_root.resolve())
   paths = manager.ensure_worktrees(count=<loop_count - 1>, default_branch='<default_branch>')
   print(f'Created/updated {len(paths)} worktrees:')
   for p in paths:
       print(f'  {p}')

   syncer = EnvSyncer()
   root_env = project_root / '.env'
   for i, p in enumerate(paths, start=1):
       syncer.sync_env(root_env.resolve(), p, f'ralph-{i}')
       print(f'Synced .env to ralph-{i}')
   "
   ```

6. Launch all loops using the Python launcher:
   ```bash
   mkdir -p tmp
   cd <project_root> && PYTHONPATH=.claude/ralph:$PYTHONPATH python3 -c "
   import json
   from pathlib import Path
   from commands.concurrent import LoopLauncher

   project_root = Path('.').resolve()
   launcher = LoopLauncher(project_root)
   worktree_paths = [project_root / '.git-worktrees' / f'ralph-{i}' for i in range(1, <loop_count>)]
   results = launcher.launch(
       count=<loop_count>,
       prd_path=Path('<prd_path>'),
       plan_path=Path('<plan_path>'),
       worktree_paths=worktree_paths,
   )
   for r in results:
       print(f'{r.label}: pid={r.process.pid}, log={r.log_file}')
   # Keep PIDs for monitoring
   pids = {r.label: r.process.pid for r in results}
   print(f'PIDS: {json.dumps(pids)}')
   "
   ```
   Launch with Bash `run_in_background: true`.

7. Tell user all loops are running and list the log file paths.

### Phase 3: Monitor

8. **For single-loop mode:** First check after 5 minutes, then every 15 minutes: read the last 10 lines of the log file to check progress.

9. **For concurrent mode:** First check after 5 minutes, then every 15 minutes:
    - Read the last 10 lines of EACH log file (`tmp/ralph-{N}-{date}.log`)
    - Report a brief status for each loop (current ticket, tickets completed so far)
    - Check for stalled loops (no output for >30 minutes) and flag them

10. On each check, report a brief status update per loop.

### Phase 4: Completion and Summary

11. When all loops finish (background task completes):

    **For single-loop mode:** Read the full log and report:
    - Tickets completed vs blocked
    - Time per ticket
    - Any retries or failures

    **For concurrent mode:** Generate a consolidated summary:
    ```bash
    cd <project_root> && PYTHONPATH=.claude/ralph:$PYTHONPATH python3 -c "
    from pathlib import Path
    from commands.concurrent import ConsolidatedSummary, CompletionResult

    # Build completion results from log files and exit codes
    completions = [
        CompletionResult(label='ralph-0', exit_code=<exit_0>, runtime_seconds=<runtime_0>, log_file=Path('<log_0>')),
        # ... one per loop
    ]
    gen = ConsolidatedSummary()
    report = gen.generate(completions)
    print(gen.format_report(report))
    "
    ```

### Phase 5b: Update SYSTEM.md

After all loops complete and the summary has been generated, update `docs/SYSTEM.md` exactly once. This step runs here (not inside each orchestrator loop) to avoid conflicts when multiple loops run concurrently.

12b. **Gather completed ticket IDs** from the log output of all loops. Look for lines like `Ticket SLCA-XXXX completed` or extract from the summary.

12c. **Invoke SYSTEM.md update** (only if at least one ticket was completed):
    ```bash
    cd <project_root> && PYTHONPATH=.claude/ralph:$PYTHONPATH python3 -c "
    from pathlib import Path
    from commands.orchestrator import (
        update_system_manifest,
        OrchestratorResult,
        OrchestratorConfig,
        TicketResult,
    )

    # Build a combined result from ALL loops' completed tickets
    completed_ticket_ids = [<list of completed ticket ID strings, e.g. 'SLCA-0083', 'SLCA-0084'>]
    ticket_results = [
        TicketResult(ticket_id=tid, status='completed')
        for tid in completed_ticket_ids
    ]
    result = OrchestratorResult(
        status='complete',
        completed_count=len(ticket_results),
        ticket_results=ticket_results,
    )
    config = OrchestratorConfig(default_branch='<default_branch>')

    update_system_manifest(
        prd_path=Path('<prd_path>'),
        plan_path=Path('<plan_path>'),
        result=result,
        config=config,
    )
    print('SYSTEM.md update complete')
    "
    ```
    This is a best-effort operation. If it fails, log the error and continue to cleanup.

### Phase 6: Post-Loop Cleanup

12. **Post-loop checkout:** Read `config.yaml` to get `default_branch`, then:
    - `git checkout <default_branch>`
    - `git pull`
    - Verify all merged PRs are in the branch: `git log --oneline -<ticket_count>`
    - Run `git status` to confirm clean working tree

13. **For concurrent mode:** Reset all worktrees to clean state:
    ```bash
    cd <project_root> && PYTHONPATH=.claude/ralph:$PYTHONPATH python3 -c "
    from pathlib import Path
    from commands.concurrent import WorktreeManager

    project_root = Path('.').resolve()
    manager = WorktreeManager(project_root)
    for name in manager.list_worktrees():
        try:
            path = manager.worktree_path(name)
            manager.update_worktree(path, '<default_branch>')
            print(f'Reset {name} to origin/<default_branch>')
        except Exception as e:
            print(f'WARNING: Could not reset {name}: {e}')
    "
    ```

14. Report final state to user:
    - Consolidated summary (for concurrent mode)
    - All worktree states
    - Any cleanup warnings

## Arguments

$ARGUMENTS

If provided, use as PRD and plan paths. Otherwise auto-detect.
Format: `<prd_path> <plan_path>` or just `<prd_path>` (plan auto-detected from matching filename).
