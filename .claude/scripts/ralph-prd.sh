#!/bin/bash
#
# Ralph PRD Orchestrator - Runs OUTSIDE Claude, invokes Claude only for LLM work
#
# Usage: .claude/scripts/ralph-prd.sh <prd-path> <plan-path> [--dry-run] [--max-attempts N]
#
# This script handles all mechanical work directly and only calls Claude
# for the parts that require intelligence:
#   - Planning implementation approach
#   - Writing code (TDD)
#   - Fixing test failures
#   - Analyzing blocked tickets
#
# Everything else (state management, validation, git, PRs) runs without LLM.
#
# Run /ralph-cmd in Claude to get the exact command to execute.
#

set -e

# ============================================================================
# Configuration
# ============================================================================

PRD_PATH="${1:-}"
PLAN_PATH="${2:-}"
DRY_RUN=false
MAX_ATTEMPTS=3
VALIDATION_RETRIES=2

# Parse optional flags
shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --max-attempts)
            MAX_ATTEMPTS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Find script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RALPH_SCRIPTS="$SCRIPT_DIR/ralph"
cd "$PROJECT_ROOT"

# ============================================================================
# Logging Setup
# ============================================================================

# Create logs directory with timestamp
RUN_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_DIR="$PROJECT_ROOT/.logs/ralph/$RUN_TIMESTAMP"
mkdir -p "$LOG_DIR"

# Main log file
MAIN_LOG="$LOG_DIR/ralph-run.log"
touch "$MAIN_LOG"

# Usage metrics file
METRICS_FILE="$LOG_DIR/usage-metrics.json"

# Function to log with timestamp (both console and file)
log_to_file() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" >> "$MAIN_LOG"
}

# Tee function - output to both console and log
tee_log() {
    while IFS= read -r line; do
        echo "$line"
        # Strip color codes for log file
        echo "$line" | sed 's/\x1b\[[0-9;]*m//g' >> "$MAIN_LOG"
    done
}

# Log environment info at startup
log_environment() {
    {
        echo "========================================"
        echo "RALPH ORCHESTRATOR RUN"
        echo "========================================"
        echo "Timestamp: $(date -Iseconds)"
        echo "Run ID: $RUN_TIMESTAMP"
        echo "Log directory: $LOG_DIR"
        echo ""
        echo "--- Environment ---"
        echo "User: $(whoami)"
        echo "Working directory: $PROJECT_ROOT"
        echo "Shell: $SHELL"
        echo "Bash version: $BASH_VERSION"
        echo ""
        echo "--- Git Status ---"
        echo "Branch: $(git branch --show-current 2>/dev/null || echo 'N/A')"
        echo "Last commit: $(git log -1 --format='%h %s' 2>/dev/null || echo 'N/A')"
        echo "Clean tree: $(git status --porcelain 2>/dev/null | wc -l | xargs) uncommitted files"
        echo ""
        echo "--- Configuration ---"
        echo "PRD: $PRD_PATH"
        echo "Plan: $PLAN_PATH"
        echo "Max attempts: $MAX_ATTEMPTS"
        echo "Validation retries: $VALIDATION_RETRIES"
        echo "Dry run: $DRY_RUN"
        echo ""
        echo "========================================"
        echo ""
    } >> "$MAIN_LOG"
}

# Save workflow state snapshot
save_state_snapshot() {
    local label="$1"
    local snapshot_file="$LOG_DIR/state-${label}-$(date +%H%M%S).json"
    if [ -f "workflow-state.json" ]; then
        cp workflow-state.json "$snapshot_file"
        log_to_file "State snapshot saved: $snapshot_file"
    fi
}

# Log error with full context
log_error_context() {
    local error_msg="$1"
    local context="$2"
    local error_file="$LOG_DIR/error-$(date +%H%M%S).log"

    {
        echo "========================================"
        echo "ERROR CONTEXT"
        echo "========================================"
        echo "Timestamp: $(date -Iseconds)"
        echo "Error: $error_msg"
        echo ""
        echo "--- Context ---"
        echo "$context"
        echo ""
        echo "--- Workflow State ---"
        cat workflow-state.json 2>/dev/null || echo "workflow-state.json not found"
        echo ""
        echo "--- Git Status ---"
        git status 2>/dev/null || echo "git status failed"
        echo ""
        echo "--- Recent Git Log ---"
        git log --oneline -5 2>/dev/null || echo "git log failed"
        echo ""
        echo "========================================"
    } > "$error_file"

    log_to_file "Error details saved: $error_file"
}

# ============================================================================
# Helper Functions
# ============================================================================

log_header() {
    echo "" | tee_log
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}" | tee_log
    echo -e "${BOLD}${CYAN}  $1${NC}" | tee_log
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}" | tee_log
    echo "" | tee_log
    log_to_file "=== $1 ==="
}

log_step() {
    echo -e "${GREEN}▶${NC} $1" | tee_log
    log_to_file "STEP: $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1" | tee_log
    log_to_file "WARN: $1"
}

log_error() {
    echo -e "${RED}✖${NC} $1" | tee_log
    log_to_file "ERROR: $1"
}

log_success() {
    echo -e "${GREEN}✔${NC} $1" | tee_log
    log_to_file "SUCCESS: $1"
}

# Get JSON value from script output
get_json_value() {
    local output="$1"
    local key="$2"
    echo "$output" | sed -n '/---JSON_OUTPUT---/,$p' | tail -n +2 | jq -r "$key"
}

# ============================================================================
# Usage Tracking
# ============================================================================

# Initialize usage tracking variables (METRICS_FILE set earlier in Logging Setup)
USAGE_INVOCATIONS="[]"
TOTAL_DURATION=0

# Capture current usage from ccusage (gets latest daily data)
capture_usage() {
    # Use .daily | last to get most recent day's usage (handles midnight edge case better)
    timeout 15 bunx ccusage daily --json 2>/dev/null | \
        jq -c '(.daily | last) // {
            inputTokens: 0,
            outputTokens: 0,
            cacheCreationTokens: 0,
            cacheReadTokens: 0,
            totalTokens: 0,
            totalCost: 0
        }' 2>/dev/null || echo '{"inputTokens":0,"outputTokens":0,"cacheCreationTokens":0,"cacheReadTokens":0,"totalTokens":0,"totalCost":0}'
}

# Calculate usage delta between two snapshots
calculate_usage_delta() {
    local before="$1"
    local after="$2"

    jq -n --argjson before "$before" --argjson after "$after" '{
        inputTokens: (($after.inputTokens // 0) - ($before.inputTokens // 0)),
        outputTokens: (($after.outputTokens // 0) - ($before.outputTokens // 0)),
        cacheCreationTokens: (($after.cacheCreationTokens // 0) - ($before.cacheCreationTokens // 0)),
        cacheReadTokens: (($after.cacheReadTokens // 0) - ($before.cacheReadTokens // 0)),
        totalTokens: (($after.totalTokens // 0) - ($before.totalTokens // 0)),
        totalCost: (($after.totalCost // 0) - ($before.totalCost // 0))
    }'
}

# Add invocation to metrics
add_invocation_metric() {
    local ticket_id="$1"
    local task="$2"
    local duration="$3"
    local delta="$4"

    USAGE_INVOCATIONS=$(echo "$USAGE_INVOCATIONS" | jq -c --arg ticket "$ticket_id" \
        --arg task "$task" --argjson duration "$duration" --argjson delta "$delta" \
        '. + [{ticket_id: $ticket, task: $task, duration_seconds: $duration, delta: $delta}]')

    TOTAL_DURATION=$((TOTAL_DURATION + duration))
}

# Write final metrics file
write_metrics_file() {
    local model="$1"

    # Ensure USAGE_INVOCATIONS is valid JSON array
    if [ -z "$USAGE_INVOCATIONS" ] || ! echo "$USAGE_INVOCATIONS" | jq empty 2>/dev/null; then
        USAGE_INVOCATIONS="[]"
    fi

    # Calculate totals from invocations
    local totals
    totals=$(echo "$USAGE_INVOCATIONS" | jq -c '{
        inputTokens: ([.[].delta.inputTokens] | add // 0),
        outputTokens: ([.[].delta.outputTokens] | add // 0),
        cacheCreationTokens: ([.[].delta.cacheCreationTokens] | add // 0),
        cacheReadTokens: ([.[].delta.cacheReadTokens] | add // 0),
        totalTokens: ([.[].delta.totalTokens] | add // 0),
        totalCost: ([.[].delta.totalCost] | add // 0),
        duration_seconds: ([.[].duration_seconds] | add // 0),
        invocation_count: (. | length)
    }' 2>/dev/null)

    # Provide default if totals calculation failed
    if [ -z "$totals" ]; then
        totals='{"inputTokens":0,"outputTokens":0,"cacheCreationTokens":0,"cacheReadTokens":0,"totalTokens":0,"totalCost":0,"duration_seconds":0,"invocation_count":0}'
    fi

    # Write metrics file
    jq -n --arg run_id "$RUN_TIMESTAMP" --arg model "$model" \
        --argjson invocations "$USAGE_INVOCATIONS" --argjson totals "$totals" '{
        run_id: $run_id,
        model: $model,
        invocations: $invocations,
        totals: $totals
    }' > "$METRICS_FILE"

    log_to_file "Usage metrics written to: $METRICS_FILE"
}

# Print usage summary
print_usage_summary() {
    if [ ! -f "$METRICS_FILE" ]; then
        return
    fi

    local totals=$(jq '.totals' "$METRICS_FILE")
    local input_tokens=$(echo "$totals" | jq -r '.inputTokens')
    local output_tokens=$(echo "$totals" | jq -r '.outputTokens')
    local cache_created=$(echo "$totals" | jq -r '.cacheCreationTokens')
    local cache_read=$(echo "$totals" | jq -r '.cacheReadTokens')
    local total_cost=$(echo "$totals" | jq -r '.totalCost')
    local duration=$(echo "$totals" | jq -r '.duration_seconds')
    local count=$(echo "$totals" | jq -r '.invocation_count')

    # Format duration as Xm Ys
    local mins=$((duration / 60))
    local secs=$((duration % 60))

    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  USAGE SUMMARY${NC}"
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    printf "  Claude invocations: %'d\n" "$count"
    printf "  Input tokens:       %'d\n" "$input_tokens"
    printf "  Output tokens:      %'d\n" "$output_tokens"
    printf "  Cache created:      %'d\n" "$cache_created"
    printf "  Cache read:         %'d\n" "$cache_read"
    printf "  Total cost:         \$%.2f\n" "$total_cost"
    printf "  Compute time:       %dm %ds\n" "$mins" "$secs"
    echo ""
    echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Also log to file
    {
        echo ""
        echo "========================================"
        echo "USAGE SUMMARY"
        echo "========================================"
        echo "Claude invocations: $count"
        echo "Input tokens: $input_tokens"
        echo "Output tokens: $output_tokens"
        echo "Cache created: $cache_created"
        echo "Cache read: $cache_read"
        echo "Total cost: \$$total_cost"
        echo "Compute time: ${mins}m ${secs}s"
        echo "========================================"
    } >> "$MAIN_LOG"
}

# Current ticket being processed (set by main loop)
CURRENT_TICKET=""

# ============================================================================
# Signal Handling
# ============================================================================

cleanup_on_interrupt() {
    echo ""
    log_warn "Interrupted by user (Ctrl+C)"
    log_to_file "INTERRUPTED: User sent SIGINT/SIGTERM"

    # Save state snapshot
    save_state_snapshot "interrupted"

    # Log summary
    {
        echo ""
        echo "========================================"
        echo "RUN INTERRUPTED"
        echo "========================================"
        echo "Time: $(date -Iseconds)"
        echo "Current ticket: ${CURRENT_TICKET:-none}"
        echo "Log directory: $LOG_DIR"
        echo "========================================"
    } >> "$MAIN_LOG"

    echo ""
    echo -e "${YELLOW}Run interrupted. State saved.${NC}"
    echo -e "Logs: $LOG_DIR"
    echo -e "Resume with same command to continue from last ticket."

    exit 130
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup_on_interrupt SIGINT SIGTERM

# Invoke Claude for LLM work
# Usage: invoke_claude "prompt" [timeout_minutes] [model] [task_label]
invoke_claude() {
    local prompt="$1"
    local timeout_mins="${2:-30}"
    local model="${3:-opus}"
    local task_label="${4:-claude}"

    # Create ticket-specific log file
    local claude_log="$LOG_DIR/${CURRENT_TICKET:-unknown}-${task_label}-$(date +%H%M%S).log"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would invoke Claude with:${NC}" | tee_log
        echo "$prompt" | head -20 | tee_log
        echo "..." | tee_log
        log_to_file "DRY RUN: Would invoke Claude for $task_label"
        return 0
    fi

    log_step "Invoking Claude (model: $model, timeout: ${timeout_mins}m)..."
    log_to_file "Claude invocation: model=$model, timeout=${timeout_mins}m, task=$task_label"
    log_to_file "Claude log file: $claude_log"

    # Capture usage BEFORE invocation
    local usage_before=$(capture_usage)
    log_to_file "Usage before: $usage_before"

    # Log the prompt to the claude-specific log
    {
        echo "========================================"
        echo "CLAUDE INVOCATION"
        echo "========================================"
        echo "Timestamp: $(date -Iseconds)"
        echo "Ticket: $CURRENT_TICKET"
        echo "Task: $task_label"
        echo "Model: $model"
        echo "Timeout: ${timeout_mins}m"
        echo ""
        echo "--- PROMPT ---"
        echo "$prompt"
        echo ""
        echo "--- RESPONSE ---"
    } > "$claude_log"

    echo ""

    # Use claude CLI with the prompt
    # -p / --print: outputs response without interactive mode
    # --agent: use the engineer agent (defined in .claude/agents/engineer.md)
    # --model: specify model
    # --allowedTools: limit tools to what's needed
    # timeout: prevent runaway sessions
    local start_time=$(date +%s)
    local exit_code=0

    timeout "${timeout_mins}m" claude -p "$prompt" \
        --agent engineer \
        --model "$model" \
        --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Task,TodoWrite" \
        2>&1 | tee -a "$claude_log" || exit_code=$?

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Capture usage AFTER invocation
    local usage_after=$(capture_usage)
    log_to_file "Usage after: $usage_after"

    # Calculate delta and add to metrics
    local usage_delta=$(calculate_usage_delta "$usage_before" "$usage_after")
    add_invocation_metric "${CURRENT_TICKET:-unknown}" "$task_label" "$duration" "$usage_delta"
    log_to_file "Usage delta: $usage_delta"

    # Log completion info
    {
        echo ""
        echo "--- END RESPONSE ---"
        echo ""
        echo "Duration: ${duration}s"
        echo "Exit code: $exit_code"
        echo ""
        echo "--- USAGE ---"
        echo "Before: $usage_before"
        echo "After: $usage_after"
        echo "Delta: $usage_delta"
        echo "========================================"
    } >> "$claude_log"

    if [ $exit_code -ne 0 ]; then
        if [ $exit_code -eq 124 ]; then
            log_error "Claude timed out after ${timeout_mins} minutes"
            log_to_file "Claude TIMEOUT after ${timeout_mins}m (${duration}s elapsed)"
        else
            log_error "Claude exited with code $exit_code"
            log_to_file "Claude FAILED with exit code $exit_code after ${duration}s"
        fi
        log_error_context "Claude invocation failed" "Task: $task_label, Exit code: $exit_code, Duration: ${duration}s, Log: $claude_log"
        return $exit_code
    fi

    log_to_file "Claude completed successfully in ${duration}s"
    echo ""
}

# ============================================================================
# Main Orchestration
# ============================================================================

main() {
    log_header "RALPH ORCHESTRATOR"

    # Validate inputs
    if [ -z "$PRD_PATH" ] || [ -z "$PLAN_PATH" ]; then
        echo "Usage: .claude/scripts/ralph-prd.sh <prd-path> <plan-path> [--dry-run] [--max-attempts N]"
        echo ""
        echo "Options:"
        echo "  --dry-run        Show what would happen without invoking Claude"
        echo "  --max-attempts N Max attempts per ticket before marking blocked (default: 3)"
        exit 1
    fi

    if [ ! -f "$PRD_PATH" ]; then
        log_error "PRD not found: $PRD_PATH"
        exit 1
    fi

    if [ ! -f "$PLAN_PATH" ]; then
        log_error "Plan not found: $PLAN_PATH"
        exit 1
    fi

    # Log environment info at startup
    log_environment

    echo "PRD:  $PRD_PATH" | tee_log
    echo "Plan: $PLAN_PATH" | tee_log
    echo "Max attempts per ticket: $MAX_ATTEMPTS" | tee_log
    [ "$DRY_RUN" = true ] && echo -e "${YELLOW}DRY RUN MODE${NC}" | tee_log
    echo "" | tee_log
    echo -e "${CYAN}Logs:${NC} $LOG_DIR" | tee_log
    echo "" | tee_log

    # ========================================================================
    # PHASE 1: Setup (No LLM)
    # ========================================================================

    log_header "PHASE 1: Setup"

    log_step "Running setup script..."
    SETUP_OUTPUT=$("$RALPH_SCRIPTS/setup.sh" "$PRD_PATH" "$PLAN_PATH" 2>&1)
    echo "$SETUP_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

    TOTAL_TICKETS=$(get_json_value "$SETUP_OUTPUT" ".total")
    log_success "Initialized with $TOTAL_TICKETS tickets"

    # Save initial state snapshot
    save_state_snapshot "initial"

    # ========================================================================
    # PHASE 2: Ticket Loop
    # ========================================================================

    log_header "PHASE 2: Implementation Loop"

    TICKETS_DONE=0
    TICKETS_BLOCKED=0

    while true; do
        # Get next ticket (No LLM)
        NEXT_OUTPUT=$("$RALPH_SCRIPTS/get-next-ticket.sh" 2>&1)
        NEXT_TICKET=$(get_json_value "$NEXT_OUTPUT" ".next_ticket")
        HAS_MORE=$(get_json_value "$NEXT_OUTPUT" ".has_more")

        if [ "$HAS_MORE" != "true" ] || [ "$NEXT_TICKET" = "null" ] || [ -z "$NEXT_TICKET" ]; then
            log_success "No more pending tickets"
            break
        fi

        # Set current ticket for logging
        CURRENT_TICKET="$NEXT_TICKET"
        log_to_file "=========================================="
        log_to_file "Starting ticket: $CURRENT_TICKET"

        log_header "Ticket: $NEXT_TICKET"

        # Start ticket (No LLM)
        log_step "Marking ticket as in-progress..."
        START_OUTPUT=$("$RALPH_SCRIPTS/ticket-start.sh" "$NEXT_TICKET" 2>&1)
        ATTEMPTS=$(get_json_value "$START_OUTPUT" ".attempts")

        echo "Attempt: $ATTEMPTS / $MAX_ATTEMPTS" | tee_log

        if [ "$ATTEMPTS" -gt "$MAX_ATTEMPTS" ]; then
            log_warn "Max attempts exceeded, marking as blocked"
            BLOCK_OUTPUT=$("$RALPH_SCRIPTS/mark-blocked.sh" "$NEXT_TICKET" "Exceeded $MAX_ATTEMPTS attempts" 2>&1)
            echo "$BLOCK_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log
            log_error_context "Ticket blocked: max attempts" "Ticket: $NEXT_TICKET, Attempts: $ATTEMPTS"
            save_state_snapshot "${NEXT_TICKET}-blocked"
            TICKETS_BLOCKED=$((TICKETS_BLOCKED + 1))
            continue
        fi

        # ====================================================================
        # LLM WORK: Implementation
        # ====================================================================

        log_step "Invoking Claude for implementation..."

        IMPL_PROMPT="## Engineer Task: Implement $NEXT_TICKET

## Context
- PRD: $PRD_PATH
- Plan: $PLAN_PATH
- Coding Standards: docs/coding-standards.md
- This is attempt $ATTEMPTS of $MAX_ATTEMPTS

## Required Reading (do this first)
1. Read docs/coding-standards.md and follow all standards
2. Read the PRD for acceptance criteria for $NEXT_TICKET
3. Read the Plan for technical approach for $NEXT_TICKET

## Implementation Steps
1. Create feature branch: feature/${NEXT_TICKET}-implementation
2. Implement using TDD:
   - Write failing tests first (cover acceptance criteria)
   - Implement minimum code to pass tests
   - Refactor while keeping tests green
3. Commit with message: [$NEXT_TICKET] <description>

## Important Rules
- Follow coding standards strictly
- Do NOT run validation (tests/lint/build) - orchestrator handles this
- Do NOT create PRs - orchestrator handles this
- Do NOT skip TDD - tests must exist before implementation
- Commit your work before finishing

## When Done
Output exactly: IMPLEMENTATION_COMPLETE"

        if ! invoke_claude "$IMPL_PROMPT" 30 "opus" "implement"; then
            log_error "Claude failed during implementation"
            log_error_context "Implementation failed" "Ticket: $NEXT_TICKET, Attempt: $ATTEMPTS"
            save_state_snapshot "${NEXT_TICKET}-impl-failed"
            continue  # Will retry on next loop with incremented attempts
        fi

        # ====================================================================
        # Validation (No LLM)
        # ====================================================================

        log_step "Running validation..."

        VALIDATION_PASSED=false
        for ((retry=1; retry<=VALIDATION_RETRIES; retry++)); do
            log_to_file "Validation attempt $retry/$VALIDATION_RETRIES for $NEXT_TICKET"

            # Capture validation output
            VALIDATION_OUTPUT=$("$RALPH_SCRIPTS/validate.sh" 2>&1) && VALIDATION_PASSED=true || VALIDATION_PASSED=false

            # Save validation output to log
            local validation_log="$LOG_DIR/${NEXT_TICKET}-validation-${retry}.log"
            {
                echo "========================================"
                echo "VALIDATION ATTEMPT $retry"
                echo "========================================"
                echo "Timestamp: $(date -Iseconds)"
                echo "Ticket: $NEXT_TICKET"
                echo ""
                echo "$VALIDATION_OUTPUT"
                echo ""
                echo "Result: $([ "$VALIDATION_PASSED" = true ] && echo 'PASSED' || echo 'FAILED')"
                echo "========================================"
            } > "$validation_log"

            if [ "$VALIDATION_PASSED" = true ]; then
                log_to_file "Validation PASSED on attempt $retry"
                break
            else
                log_warn "Validation failed (attempt $retry/$VALIDATION_RETRIES)"
                log_to_file "Validation FAILED, log: $validation_log"

                if [ $retry -lt $VALIDATION_RETRIES ]; then
                    # ========================================================
                    # LLM WORK: Fix failures
                    # ========================================================

                    log_step "Invoking Claude to fix failures..."

                    FIX_PROMPT="The validation for $NEXT_TICKET failed.

## Validation Output
\`\`\`
$VALIDATION_OUTPUT
\`\`\`

## Instructions
1. Analyze the failures above
2. Fix the issues in the code
3. Commit your fixes with message: [$NEXT_TICKET] Fix validation issues

When done, output exactly: FIXES_COMPLETE"

                    invoke_claude "$FIX_PROMPT" 15 "opus" "fix-validation" || true
                fi
            fi
        done

        if [ "$VALIDATION_PASSED" != true ]; then
            log_error "Validation failed after $VALIDATION_RETRIES attempts"
            log_error_context "Validation failed" "Ticket: $NEXT_TICKET, Attempts: $VALIDATION_RETRIES, Last output: $validation_log"
            save_state_snapshot "${NEXT_TICKET}-validation-failed"
            continue  # Will retry whole ticket on next loop
        fi

        log_success "Validation passed"

        # ====================================================================
        # PR Flow (No LLM)
        # ====================================================================

        log_step "Running PR flow..."

        PR_ARGS=("$NEXT_TICKET" "[$NEXT_TICKET] Implementation complete")
        [ "$DRY_RUN" = true ] && PR_ARGS+=("--dry-run")
        PR_OUTPUT=$("$RALPH_SCRIPTS/pr-flow.sh" "${PR_ARGS[@]}" 2>&1)
        echo "$PR_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

        PR_NUMBER=$(get_json_value "$PR_OUTPUT" ".pr_number")
        log_to_file "PR created/updated: #$PR_NUMBER"

        # ====================================================================
        # Complete Ticket (No LLM)
        # ====================================================================

        log_step "Marking ticket complete..."

        DONE_OUTPUT=$("$RALPH_SCRIPTS/ticket-done.sh" "$NEXT_TICKET" "$PR_NUMBER" 2>&1)
        echo "$DONE_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

        # Save state snapshot after ticket completion
        save_state_snapshot "${NEXT_TICKET}-complete"

        TICKETS_DONE=$((TICKETS_DONE + 1))
        log_success "Ticket $NEXT_TICKET complete!"
        log_to_file "Ticket $NEXT_TICKET completed successfully (PR #$PR_NUMBER)"

    done

    # ========================================================================
    # PHASE 3: Cleanup (No LLM)
    # ========================================================================

    log_header "PHASE 3: Cleanup"

    CLEANUP_OUTPUT=$("$RALPH_SCRIPTS/cleanup.sh" 2>&1)
    echo "$CLEANUP_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

    # Save final state snapshot
    save_state_snapshot "final"

    # Write usage metrics file
    write_metrics_file "opus"

    # ========================================================================
    # Summary
    # ========================================================================

    log_header "ORCHESTRATION COMPLETE"

    echo -e "Total tickets:  ${CYAN}$TOTAL_TICKETS${NC}" | tee_log
    echo -e "Completed:      ${GREEN}$TICKETS_DONE${NC}" | tee_log
    echo -e "Blocked:        ${YELLOW}$TICKETS_BLOCKED${NC}" | tee_log
    echo "" | tee_log

    if [ $TICKETS_BLOCKED -gt 0 ]; then
        echo -e "${YELLOW}Some tickets were blocked and need manual review.${NC}" | tee_log
        echo "Run: .claude/scripts/ralph/status.sh for details" | tee_log
    fi

    # Print usage summary
    print_usage_summary

    # Write final summary to log
    {
        echo ""
        echo "========================================"
        echo "RUN COMPLETE"
        echo "========================================"
        echo "End time: $(date -Iseconds)"
        echo "Total tickets: $TOTAL_TICKETS"
        echo "Completed: $TICKETS_DONE"
        echo "Blocked: $TICKETS_BLOCKED"
        echo ""
        echo "Log files in: $LOG_DIR"
        echo "========================================"
    } >> "$MAIN_LOG"

    echo "" | tee_log
    echo -e "${CYAN}Full logs:${NC} $LOG_DIR" | tee_log
    echo "" | tee_log

    if [ $TICKETS_DONE -eq $TOTAL_TICKETS ]; then
        echo -e "${GREEN}${BOLD}PRD_COMPLETE${NC}" | tee_log
        log_to_file "RESULT: PRD_COMPLETE"
        exit 0
    else
        echo -e "${YELLOW}PRD_INCOMPLETE${NC}" | tee_log
        log_to_file "RESULT: PRD_INCOMPLETE"
        exit 1
    fi
}

# ============================================================================
# Run
# ============================================================================

main "$@"
