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
# Signal Handling - ensure Ctrl+C kills child processes
# ============================================================================

cleanup() {
    echo ""
    echo "Interrupted - cleaning up..."
    # Kill all child processes in our process group
    pkill -P $$ 2>/dev/null || true
    # Kill any timeout/claude processes we spawned
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 130
}

trap cleanup SIGINT SIGTERM

# ============================================================================
# Configuration
# ============================================================================

PRD_PATH="${1:-}"
PLAN_PATH="${2:-}"
DRY_RUN=false

# Read configuration from config.yaml (with defaults)
read_config() {
    local key="$1"
    local default="$2"
    local value
    # Extract value and strip surrounding quotes (YAML strings may be quoted)
    value=$(grep -E "^\s*${key}:" config.yaml 2>/dev/null | awk '{print $2}' | tr -d '"' | head -1)
    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Load ralph configuration from config.yaml
MAX_ATTEMPTS=$(read_config "max_attempts" "3")
SONNET_THRESHOLD=$(read_config "sonnet_threshold" "2")
STATE_DIRECTORY=$(read_config "state_directory" "docs/state")
VALIDATOR_MODEL=$(read_config "validator_model" "haiku")
ENGINEER_TIMEOUT=$(read_config "engineer_timeout" "30")
VALIDATOR_TIMEOUT=$(read_config "validator_timeout" "10")

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
# Check for required .env file with RALPH_LABEL
# ============================================================================

if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo ""
    echo "Each ralph worktree needs a .env file with a unique RALPH_LABEL."
    echo "This prevents multiple instances from picking up the same ticket."
    echo ""
    echo "Create .env with:"
    echo "  echo 'RALPH_LABEL=ralph-1' > .env    # For first instance"
    echo "  echo 'RALPH_LABEL=ralph-2' > .env    # For second instance"
    echo ""
    echo "Current directory: $PROJECT_ROOT"
    exit 1
fi

# Load .env
set -a
source .env
set +a

if [ -z "$RALPH_LABEL" ]; then
    echo -e "${RED}ERROR: RALPH_LABEL not set in .env${NC}"
    echo ""
    echo "Add RALPH_LABEL to your .env file:"
    echo "  echo 'RALPH_LABEL=ralph-1' >> .env"
    echo ""
    echo "Each worktree must have a unique label (ralph-1, ralph-2, etc.)"
    exit 1
fi

echo -e "${GREEN}✓${NC} Instance label: $RALPH_LABEL"

# Source state utilities (for prompt building and state management)
source "$RALPH_SCRIPTS/state-utils.sh"

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

# Validate config settings
validate_config() {
    local errors=0

    # Check if target_branch exists on remote
    local target_branch=$(read_config "target_branch" "main")
    if [ -n "$target_branch" ]; then
        if ! git ls-remote --heads origin "$target_branch" 2>/dev/null | grep -q "$target_branch"; then
            log_error "Config error: pr.target_branch '$target_branch' does not exist on remote"
            log_step "Available branches on remote:"
            git ls-remote --heads origin 2>/dev/null | awk '{print "  - " $2}' | sed 's|refs/heads/||'
            errors=$((errors + 1))
        fi
    fi

    # Check if default_branch exists on remote
    local default_branch=$(read_config "default_branch" "main")
    if [ -n "$default_branch" ]; then
        if ! git ls-remote --heads origin "$default_branch" 2>/dev/null | grep -q "$default_branch"; then
            log_error "Config error: git.default_branch '$default_branch' does not exist on remote"
            errors=$((errors + 1))
        fi
    fi

    if [ $errors -gt 0 ]; then
        log_error "Config validation failed with $errors error(s)"
        log_step "Fix config.yaml and try again"
        exit 1
    fi

    log_success "Config validation passed"
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

# Get ticket complexity from workflow-state.json
get_ticket_complexity() {
    local ticket_id="$1"
    local complexity=$(jq -r --arg id "$ticket_id" '.ralph.tickets[] | select(.id == $id) | .complexity // 3' workflow-state.json 2>/dev/null)
    # Default to 3 (moderate) if not found
    if [ -z "$complexity" ] || [ "$complexity" = "null" ]; then
        echo "3"
    else
        echo "$complexity"
    fi
}

# Select model based on complexity threshold
select_model_for_complexity() {
    local complexity="$1"
    if [ "$complexity" -le "$SONNET_THRESHOLD" ]; then
        echo "sonnet"
    else
        echo "opus"
    fi
}

# ============================================================================
# Usage Tracking
# ============================================================================

# Initialize usage tracking variables (METRICS_FILE set earlier in Logging Setup)
# NOTE: We use a temp file for invocations because invoke_claude runs in subshells
# (command substitution) which would lose variable changes
INVOCATIONS_FILE="$LOG_DIR/invocations.jsonl"
touch "$INVOCATIONS_FILE"
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

# Add invocation to metrics (writes to file to survive subshells)
# Usage: add_invocation_metric ticket_id task duration delta model complexity
add_invocation_metric() {
    local ticket_id="$1"
    local task="$2"
    local duration="$3"
    local delta="$4"
    local model="${5:-opus}"
    local complexity="${6:-3}"

    # Write as JSON line to file (survives subshell)
    jq -n -c --arg ticket "$ticket_id" \
        --arg task "$task" --argjson duration "$duration" --argjson delta "$delta" \
        --arg model "$model" --argjson complexity "$complexity" \
        '{ticket_id: $ticket, task: $task, duration_seconds: $duration, delta: $delta, model: $model, complexity: $complexity}' \
        >> "$INVOCATIONS_FILE"
}

# Get usage metrics for a specific ticket (for summary files)
# Usage: get_ticket_usage <ticket_id>
# Returns: JSON object with aggregated usage for this ticket
get_ticket_usage() {
    local ticket_id="$1"

    if [ ! -s "$INVOCATIONS_FILE" ]; then
        echo "{}"
        return
    fi

    # Filter invocations for this ticket and aggregate
    jq -s --arg ticket "$ticket_id" '
        map(select(.ticket_id == $ticket)) |
        if length == 0 then {}
        else {
            invocation_count: length,
            duration_seconds: ([.[].duration_seconds] | add // 0),
            input_tokens: ([.[].delta.inputTokens] | add // 0),
            output_tokens: ([.[].delta.outputTokens] | add // 0),
            cache_read_tokens: ([.[].delta.cacheReadTokens] | add // 0),
            cache_creation_tokens: ([.[].delta.cacheCreationTokens] | add // 0),
            total_cost: ([.[].delta.totalCost] | add // 0),
            model: (.[0].model // "unknown"),
            complexity: (.[0].complexity // 0)
        }
        end
    ' "$INVOCATIONS_FILE" 2>/dev/null || echo "{}"
}

# Write final metrics file
write_metrics_file() {
    local default_model="$1"

    # Read invocations from JSONL file (one JSON object per line)
    local USAGE_INVOCATIONS="[]"
    if [ -s "$INVOCATIONS_FILE" ]; then
        # Convert JSONL to JSON array
        USAGE_INVOCATIONS=$(jq -s '.' "$INVOCATIONS_FILE" 2>/dev/null || echo "[]")
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

    # Calculate breakdown by model
    local by_model
    by_model=$(echo "$USAGE_INVOCATIONS" | jq -c '
        group_by(.model) | map({
            model: .[0].model,
            count: length,
            total_duration: ([.[].duration_seconds] | add // 0),
            total_cost: ([.[].delta.totalCost] | add // 0)
        })
    ' 2>/dev/null || echo "[]")

    # Calculate breakdown by complexity
    local by_complexity
    by_complexity=$(echo "$USAGE_INVOCATIONS" | jq -c '
        group_by(.complexity) | map({
            complexity: .[0].complexity,
            model: .[0].model,
            count: length,
            total_duration: ([.[].duration_seconds] | add // 0),
            total_cost: ([.[].delta.totalCost] | add // 0)
        }) | sort_by(.complexity)
    ' 2>/dev/null || echo "[]")

    # Write metrics file
    jq -n --arg run_id "$RUN_TIMESTAMP" --arg default_model "$default_model" \
        --argjson threshold "$SONNET_THRESHOLD" \
        --argjson invocations "$USAGE_INVOCATIONS" --argjson totals "$totals" \
        --argjson by_model "$by_model" --argjson by_complexity "$by_complexity" '{
        run_id: $run_id,
        sonnet_threshold: $threshold,
        invocations: $invocations,
        totals: $totals,
        by_model: $by_model,
        by_complexity: $by_complexity
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

    # Print model breakdown
    echo -e "${BOLD}${CYAN}  MODEL PERFORMANCE${NC}"
    echo -e "${CYAN}  ─────────────────────────────────────────────────────────${NC}"
    echo ""
    printf "  %-10s │ %8s │ %10s │ %10s\n" "Model" "Count" "Time" "Cost"
    echo "  ───────────┼──────────┼────────────┼───────────"

    # Read by_model array and print each
    local model_count=$(jq '.by_model | length' "$METRICS_FILE")
    for ((i=0; i<model_count; i++)); do
        local m_name=$(jq -r ".by_model[$i].model" "$METRICS_FILE")
        local m_count=$(jq -r ".by_model[$i].count" "$METRICS_FILE")
        local m_dur=$(jq -r ".by_model[$i].total_duration" "$METRICS_FILE")
        local m_cost=$(jq -r ".by_model[$i].total_cost" "$METRICS_FILE")
        local m_mins=$((m_dur / 60))
        local m_secs=$((m_dur % 60))
        printf "  %-10s │ %8d │ %6dm %2ds │ \$%8.2f\n" "$m_name" "$m_count" "$m_mins" "$m_secs" "$m_cost"
    done
    echo ""

    # Print complexity breakdown
    echo -e "${BOLD}${CYAN}  BY COMPLEXITY${NC}"
    echo -e "${CYAN}  ─────────────────────────────────────────────────────────${NC}"
    echo ""
    printf "  %-6s │ %-10s │ %8s │ %10s\n" "Level" "Model" "Count" "Cost"
    echo "  ───────┼────────────┼──────────┼───────────"

    local complexity_count=$(jq '.by_complexity | length' "$METRICS_FILE")
    for ((i=0; i<complexity_count; i++)); do
        local c_level=$(jq -r ".by_complexity[$i].complexity" "$METRICS_FILE")
        local c_model=$(jq -r ".by_complexity[$i].model" "$METRICS_FILE")
        local c_count=$(jq -r ".by_complexity[$i].count" "$METRICS_FILE")
        local c_cost=$(jq -r ".by_complexity[$i].total_cost" "$METRICS_FILE")
        printf "  %-6s │ %-10s │ %8d │ \$%8.2f\n" "$c_level" "$c_model" "$c_count" "$c_cost"
    done
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
        echo ""
        echo "--- By Model ---"
        jq -r '.by_model[] | "\(.model): \(.count) invocations, \(.total_duration)s, $\(.total_cost)"' "$METRICS_FILE" 2>/dev/null || true
        echo ""
        echo "--- By Complexity ---"
        jq -r '.by_complexity[] | "Level \(.complexity) (\(.model)): \(.count) invocations, $\(.total_cost)"' "$METRICS_FILE" 2>/dev/null || true
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

    # CRITICAL: Kill all child processes first
    echo "Killing child processes..."
    pkill -P $$ 2>/dev/null || true
    jobs -p | xargs -r kill 2>/dev/null || true
    # Also kill any claude processes we might have spawned
    pkill -f "claude -p" 2>/dev/null || true

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
# Usage: invoke_claude "prompt" [timeout_minutes] [model] [task_label] [complexity]
invoke_claude() {
    local prompt="$1"
    local timeout_mins="${2:-30}"
    local model="${3:-opus}"
    local task_label="${4:-claude}"
    local complexity="${5:-3}"

    # Create ticket-specific log file
    local claude_log="$LOG_DIR/${CURRENT_TICKET:-unknown}-${task_label}-$(date +%H%M%S).log"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would invoke Claude with:${NC}" | tee_log
        echo "$prompt" | head -20 | tee_log
        echo "..." | tee_log
        log_to_file "DRY RUN: Would invoke Claude for $task_label"
        return 0
    fi

    log_step "Invoking Claude (model: $model, timeout: ${timeout_mins}m) at $(date +%H:%M:%S)..."
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
    add_invocation_metric "${CURRENT_TICKET:-unknown}" "$task_label" "$duration" "$usage_delta" "$model" "$complexity"
    log_to_file "Usage delta: $usage_delta (model: $model, complexity: $complexity)"

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
    echo "" | tee_log
    echo -e "${CYAN}Configuration (from config.yaml):${NC}" | tee_log
    echo "  Sonnet threshold: $SONNET_THRESHOLD (complexity 1-$SONNET_THRESHOLD → Sonnet)" | tee_log
    echo "  Max attempts: $MAX_ATTEMPTS" | tee_log
    echo "  Validator model: $VALIDATOR_MODEL" | tee_log
    echo "  State directory: $STATE_DIRECTORY" | tee_log
    [ "$DRY_RUN" = true ] && echo -e "${YELLOW}DRY RUN MODE${NC}" | tee_log
    echo "" | tee_log
    echo -e "${CYAN}Logs:${NC} $LOG_DIR" | tee_log
    echo "" | tee_log

    # Validate configuration
    log_step "Validating configuration..."
    validate_config

    # ========================================================================
    # PHASE 1: Setup (No LLM)
    # ========================================================================

    log_header "PHASE 1: Setup"

    log_step "Running setup script..."
    SETUP_OUTPUT=$("$RALPH_SCRIPTS/setup.sh" "$PRD_PATH" "$PLAN_PATH" 2>&1)
    echo "$SETUP_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

    # Get initial counts (for display only - loop is purely reactive)
    SETUP_SOURCE=$(get_json_value "$SETUP_OUTPUT" ".source")
    INITIAL_OPEN=$(get_json_value "$SETUP_OUTPUT" ".open")
    if [ "$INITIAL_OPEN" = "null" ] || [ -z "$INITIAL_OPEN" ]; then
        # Fallback for local mode
        INITIAL_OPEN=$(get_json_value "$SETUP_OUTPUT" ".total")
    fi
    log_success "Ready to process tickets (${INITIAL_OPEN:-unknown} open)"
    log_to_file "Setup source: $SETUP_SOURCE, Initial open: $INITIAL_OPEN"

    # Save initial state snapshot
    save_state_snapshot "initial"

    # ========================================================================
    # PHASE 2: Ticket Loop (V2 - Single Attempt Loop)
    # ========================================================================

    log_header "PHASE 2: Implementation Loop"

    TICKETS_DONE=0
    TICKETS_BLOCKED=0

    # Outer loop: iterate through tickets
    WAIT_RETRY_COUNT=0
    MAX_WAIT_RETRIES=60  # Max 60 retries (30 minutes at 30s intervals)
    WAIT_INTERVAL=30     # Seconds to wait when dependencies not met

    while true; do
        # Get next ticket (No LLM)
        NEXT_OUTPUT=$("$RALPH_SCRIPTS/get-next-ticket.sh" 2>&1)
        NEXT_TICKET=$(get_json_value "$NEXT_OUTPUT" ".next_ticket")
        HAS_MORE=$(get_json_value "$NEXT_OUTPUT" ".has_more")
        TICKET_STATUS=$(get_json_value "$NEXT_OUTPUT" ".status")

        # Handle waiting_on_dependencies status
        if [ "$TICKET_STATUS" = "waiting_on_dependencies" ]; then
            WAIT_RETRY_COUNT=$((WAIT_RETRY_COUNT + 1))
            SKIPPED_COUNT=$(get_json_value "$NEXT_OUTPUT" ".skipped_for_deps")

            if [ "$WAIT_RETRY_COUNT" -ge "$MAX_WAIT_RETRIES" ]; then
                log_warn "Max wait retries ($MAX_WAIT_RETRIES) reached"
                log_warn "Tickets are still waiting on dependencies from other instances"
                break
            fi

            log_step "Waiting on dependencies ($SKIPPED_COUNT tickets blocked)"
            log_step "Retry $WAIT_RETRY_COUNT/$MAX_WAIT_RETRIES - sleeping ${WAIT_INTERVAL}s..."
            log_to_file "Waiting on dependencies: $SKIPPED_COUNT tickets, retry $WAIT_RETRY_COUNT"
            sleep "$WAIT_INTERVAL"
            continue
        fi

        # Reset wait counter when we get a ticket
        WAIT_RETRY_COUNT=0

        if [ "$HAS_MORE" != "true" ] || [ "$NEXT_TICKET" = "null" ] || [ -z "$NEXT_TICKET" ]; then
            log_success "No more pending tickets"
            break
        fi

        # Set current ticket for logging
        CURRENT_TICKET="$NEXT_TICKET"
        log_to_file "=========================================="
        log_to_file "Starting ticket: $CURRENT_TICKET"

        # Get complexity and select model
        TICKET_COMPLEXITY=$(get_ticket_complexity "$NEXT_TICKET")
        TICKET_MODEL=$(select_model_for_complexity "$TICKET_COMPLEXITY")
        log_to_file "Ticket complexity: $TICKET_COMPLEXITY, Model: $TICKET_MODEL"

        log_header "Ticket: $NEXT_TICKET (complexity: $TICKET_COMPLEXITY → $TICKET_MODEL)"

        # Get current attempt number for this ticket
        local CURRENT_ATTEMPT=$(get_latest_attempt "$NEXT_TICKET")
        CURRENT_ATTEMPT=$((CURRENT_ATTEMPT + 1))

        # Track the branch name for this ticket
        local TICKET_BRANCH="feature/${NEXT_TICKET}-implementation"

        # ====================================================================
        # ATTEMPT LOOP (V2 - single loop, engineer validates itself)
        # ====================================================================

        local TICKET_COMPLETE=false

        while [ "$CURRENT_ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
            log_step "Attempt $CURRENT_ATTEMPT of $MAX_ATTEMPTS"
            log_to_file "Starting attempt $CURRENT_ATTEMPT for $NEXT_TICKET"

            # Create attempt directory
            local ATTEMPT_DIR=$(ensure_state_dir "$NEXT_TICKET" "$CURRENT_ATTEMPT")
            log_to_file "State directory: $ATTEMPT_DIR"

            # Write initial "in_progress" state file
            local INITIAL_STATE_FILE="$STATE_DIRECTORY/$NEXT_TICKET/attempt-$CURRENT_ATTEMPT/engineer-state.json"
            cat > "$INITIAL_STATE_FILE" << ENDJSON
{
  "ticket_id": "$NEXT_TICKET",
  "attempt": $CURRENT_ATTEMPT,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "in_progress",
  "branch": "$TICKET_BRANCH",
  "work_completed": [],
  "files_modified": [],
  "known_issues": [],
  "next_steps": ["Engineer invocation started"]
}
ENDJSON
            log_step "Created initial state file: $INITIAL_STATE_FILE"

            # ================================================================
            # Build prompt (initial or resume based on attempt)
            # ================================================================

            local IMPL_PROMPT=""

            if [ "$CURRENT_ATTEMPT" -eq 1 ]; then
                # First attempt - use initial prompt
                log_step "Building initial implementation prompt..."
                IMPL_PROMPT=$(build_engineer_initial_prompt \
                    "$NEXT_TICKET" \
                    "$PRD_PATH" \
                    "$PLAN_PATH" \
                    "$MAX_ATTEMPTS" 2>/dev/null)
            else
                # Subsequent attempt - use resume prompt with previous context
                log_step "Building resume prompt with previous state context..."
                local PREV_ATTEMPT=$((CURRENT_ATTEMPT - 1))
                local PREV_STATE=$(get_previous_state "$NEXT_TICKET" "$PREV_ATTEMPT")
                local PREV_VALIDATION=$(get_previous_validation "$NEXT_TICKET" "$PREV_ATTEMPT")

                # Extract priority and fixes from validation report if exists
                local PRIORITY_ORDER=""
                local SUGGESTED_FIXES=""
                local validation_json="$STATE_DIRECTORY/$NEXT_TICKET/attempt-$PREV_ATTEMPT/validation.json"
                if [ -f "$validation_json" ]; then
                    PRIORITY_ORDER=$(jq -r '(.priority_order // []) | to_entries | .[] | "\(.key + 1). \(.value)"' "$validation_json" 2>/dev/null | head -5)
                    SUGGESTED_FIXES=$(jq -r '(.suggested_fixes // []) | to_entries | .[] | "\(.key + 1). \(.value)"' "$validation_json" 2>/dev/null | head -5)
                fi

                IMPL_PROMPT=$(build_engineer_resume_prompt \
                    "$NEXT_TICKET" \
                    "$CURRENT_ATTEMPT" \
                    "$MAX_ATTEMPTS" \
                    "$TICKET_BRANCH" \
                    "$PREV_STATE" \
                    "$PREV_VALIDATION" \
                    "$PRIORITY_ORDER" \
                    "$SUGGESTED_FIXES" 2>/dev/null)
            fi

            # ================================================================
            # LLM WORK: Engineer (implements + validates + commits)
            # ================================================================

            log_step "Invoking Claude engineer (model: $TICKET_MODEL, timeout: ${ENGINEER_TIMEOUT}m) at $(date +%H:%M:%S)..."

            local ENGINEER_OUTPUT=""
            local ENGINEER_EXIT=0

            # Capture engineer output
            ENGINEER_OUTPUT=$(invoke_claude "$IMPL_PROMPT" "$ENGINEER_TIMEOUT" "$TICKET_MODEL" "engineer-attempt-$CURRENT_ATTEMPT" "$TICKET_COMPLEXITY" 2>&1) || ENGINEER_EXIT=$?

            # Save engineer output to log
            local engineer_log="$LOG_DIR/${NEXT_TICKET}-engineer-attempt-${CURRENT_ATTEMPT}.log"
            {
                echo "========================================"
                echo "ENGINEER ATTEMPT $CURRENT_ATTEMPT"
                echo "========================================"
                echo "Timestamp: $(date -Iseconds)"
                echo "Ticket: $NEXT_TICKET"
                echo "Model: $TICKET_MODEL"
                echo "Timeout: ${ENGINEER_TIMEOUT}m"
                echo "Exit code: $ENGINEER_EXIT"
                echo ""
                echo "$ENGINEER_OUTPUT"
                echo "========================================"
            } > "$engineer_log"

            # Check if engineer timed out or failed critically
            if [ "$ENGINEER_EXIT" -eq 124 ]; then
                log_error "Engineer timed out after ${ENGINEER_TIMEOUT} minutes"
                log_to_file "Engineer TIMEOUT, log: $engineer_log"

                # Handle timeout: check for uncommitted changes
                local uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
                if [ "$uncommitted" -gt 0 ]; then
                    log_warn "Found $uncommitted uncommitted changes, committing as WIP..."
                    git add -A
                    git commit -m "[$NEXT_TICKET] WIP - engineer timeout

Co-Authored-By: Claude <noreply@anthropic.com>" || true
                fi

                CURRENT_ATTEMPT=$((CURRENT_ATTEMPT + 1))
                continue
            fi

            # ================================================================
            # Check engineer result: VALIDATION_PASSED or VALIDATION_FAILED
            # ================================================================

            if echo "$ENGINEER_OUTPUT" | grep -q "VALIDATION_PASSED"; then
                log_success "Engineer reported: VALIDATION_PASSED"
                TICKET_COMPLETE=true
                break

            elif echo "$ENGINEER_OUTPUT" | grep -q "VALIDATION_FAILED"; then
                log_warn "Engineer reported: VALIDATION_FAILED"
                log_to_file "Engineer validation failed on attempt $CURRENT_ATTEMPT"

                # ============================================================
                # LLM WORK: Validator (analyzes failures, writes report)
                # ============================================================

                if [ "$CURRENT_ATTEMPT" -lt "$MAX_ATTEMPTS" ]; then
                    log_step "Invoking validator (model: $VALIDATOR_MODEL, timeout: ${VALIDATOR_TIMEOUT}m)..."

                    local VALIDATOR_PROMPT=$(build_validator_prompt \
                        "$NEXT_TICKET" \
                        "$CURRENT_ATTEMPT" \
                        "$TICKET_BRANCH" 2>/dev/null)

                    local VALIDATOR_OUTPUT=""
                    VALIDATOR_OUTPUT=$(invoke_claude "$VALIDATOR_PROMPT" "$VALIDATOR_TIMEOUT" "$VALIDATOR_MODEL" "validator-attempt-$CURRENT_ATTEMPT" "1" 2>&1) || true

                    # Save validator output to log
                    local validator_log="$LOG_DIR/${NEXT_TICKET}-validator-attempt-${CURRENT_ATTEMPT}.log"
                    {
                        echo "========================================"
                        echo "VALIDATOR ATTEMPT $CURRENT_ATTEMPT"
                        echo "========================================"
                        echo "Timestamp: $(date -Iseconds)"
                        echo "Ticket: $NEXT_TICKET"
                        echo "Model: $VALIDATOR_MODEL"
                        echo ""
                        echo "$VALIDATOR_OUTPUT"
                        echo "========================================"
                    } > "$validator_log"

                    if echo "$VALIDATOR_OUTPUT" | grep -q "VALIDATION_REPORT_COMPLETE"; then
                        log_success "Validator report created"
                    else
                        log_warn "Validator did not complete report (will continue anyway)"
                    fi

                    # Commit validator state files so they're available for next attempt
                    local validator_uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
                    if [ "$validator_uncommitted" -gt 0 ]; then
                        log_step "Committing validator state files..."
                        git add -A
                        git commit -m "[$NEXT_TICKET] Validation report - attempt $CURRENT_ATTEMPT

Co-Authored-By: Claude <noreply@anthropic.com>" || true
                    fi
                fi

                CURRENT_ATTEMPT=$((CURRENT_ATTEMPT + 1))
                continue

            else
                # Engineer didn't report a clear result - CHECK STATE FILE AS FALLBACK
                log_warn "Engineer did not report clear VALIDATION_PASSED or VALIDATION_FAILED"
                log_step "Checking state file for status fallback..."

                local STATE_FILE="$STATE_DIRECTORY/$NEXT_TICKET/attempt-$CURRENT_ATTEMPT/engineer-state.json"
                if [ -f "$STATE_FILE" ]; then
                    local FILE_STATUS=$(jq -r '.status // "unknown"' "$STATE_FILE" 2>/dev/null)
                    log_step "State file status: $FILE_STATUS"

                    if [ "$FILE_STATUS" = "validation_passed" ]; then
                        log_success "State file indicates validation_passed - proceeding to PR"
                        TICKET_COMPLETE=true
                        break
                    fi
                else
                    log_warn "No state file found at: $STATE_FILE"
                fi

                # If we get here, still treat as failure
                local uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
                if [ "$uncommitted" -gt 0 ]; then
                    log_warn "Found $uncommitted uncommitted changes, committing as WIP..."
                    git add -A
                    git commit -m "[$NEXT_TICKET] WIP - unclear result

Co-Authored-By: Claude <noreply@anthropic.com>" || true
                fi

                CURRENT_ATTEMPT=$((CURRENT_ATTEMPT + 1))
                continue
            fi
        done

        # ====================================================================
        # Post-attempt handling: success or blocked
        # ====================================================================

        if [ "$TICKET_COMPLETE" = true ]; then
            # ================================================================
            # PR Flow (Only when validation passes)
            # ================================================================

            log_step "Running PR flow..."

            PR_ARGS=("$NEXT_TICKET" "[$NEXT_TICKET] Implementation complete")
            [ "$DRY_RUN" = true ] && PR_ARGS+=("--dry-run")

            # Run PR flow, capturing exit code
            PR_OUTPUT=$("$RALPH_SCRIPTS/pr-flow.sh" "${PR_ARGS[@]}" 2>&1) || {
                PR_EXIT_CODE=$?
                log_error "PR flow failed with exit code $PR_EXIT_CODE"
                log_to_file "PR flow output: $PR_OUTPUT"
                log_step "Continuing despite PR flow failure..."
            }
            echo "$PR_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

            # Check if ticket was already done (PR already merged)
            ALREADY_DONE=$(get_json_value "$PR_OUTPUT" ".already_done")
            if [ "$ALREADY_DONE" = "true" ]; then
                PR_NUMBER=$(get_json_value "$PR_OUTPUT" ".pr_number")
                log_success "Ticket $NEXT_TICKET already completed (PR #$PR_NUMBER)"
                write_summary "$NEXT_TICKET" "SUCCESS" "$CURRENT_ATTEMPT" "$PR_NUMBER" "$(get_ticket_usage "$NEXT_TICKET")"
                TICKETS_DONE=$((TICKETS_DONE + 1))
                continue
            fi

            PR_NUMBER=$(get_json_value "$PR_OUTPUT" ".pr_number")
            if [ -z "$PR_NUMBER" ] || [ "$PR_NUMBER" = "null" ]; then
                PR_NUMBER=$(gh pr list --head "$TICKET_BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")
            fi
            log_to_file "PR created/updated: #$PR_NUMBER"

            # Write success summary
            write_summary "$NEXT_TICKET" "SUCCESS" "$((CURRENT_ATTEMPT))" "$PR_NUMBER" "$(get_ticket_usage "$NEXT_TICKET")"

            # Mark ticket complete
            log_step "Marking ticket complete..."
            DONE_OUTPUT=$("$RALPH_SCRIPTS/ticket-done.sh" "$NEXT_TICKET" "$PR_NUMBER" 2>&1)
            echo "$DONE_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

            save_state_snapshot "${NEXT_TICKET}-complete"
            TICKETS_DONE=$((TICKETS_DONE + 1))
            log_success "Ticket $NEXT_TICKET complete!"
            log_to_file "Ticket $NEXT_TICKET completed successfully (PR #$PR_NUMBER)"

        else
            # ================================================================
            # Check if final attempt actually passed before marking blocked
            # ================================================================

            local FINAL_ATTEMPT=$MAX_ATTEMPTS
            local FINAL_STATE_FILE="$STATE_DIRECTORY/$NEXT_TICKET/attempt-$FINAL_ATTEMPT/engineer-state.json"

            if [ -f "$FINAL_STATE_FILE" ]; then
                local FINAL_STATUS=$(jq -r '.status // "unknown"' "$FINAL_STATE_FILE" 2>/dev/null)
                log_step "Final attempt state file status: $FINAL_STATUS"

                if [ "$FINAL_STATUS" = "validation_passed" ]; then
                    log_success "Final attempt passed validation! Proceeding to PR flow..."

                    # Run PR flow
                    PR_ARGS=("$NEXT_TICKET" "[$NEXT_TICKET] Implementation complete")
                    [ "$DRY_RUN" = true ] && PR_ARGS+=("--dry-run")

                    PR_OUTPUT=$("$RALPH_SCRIPTS/pr-flow.sh" "${PR_ARGS[@]}" 2>&1) || {
                        PR_EXIT_CODE=$?
                        log_error "PR flow failed with exit code $PR_EXIT_CODE"
                    }
                    echo "$PR_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

                    PR_NUMBER=$(get_json_value "$PR_OUTPUT" ".pr_number")
                    if [ -z "$PR_NUMBER" ] || [ "$PR_NUMBER" = "null" ]; then
                        PR_NUMBER=$(gh pr list --head "$TICKET_BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")
                    fi

                    if [ -n "$PR_NUMBER" ] && [ "$PR_NUMBER" != "null" ]; then
                        # PR created successfully
                        write_summary "$NEXT_TICKET" "SUCCESS" "$FINAL_ATTEMPT" "$PR_NUMBER" "$(get_ticket_usage "$NEXT_TICKET")"
                        DONE_OUTPUT=$("$RALPH_SCRIPTS/ticket-done.sh" "$NEXT_TICKET" "$PR_NUMBER" 2>&1)
                        echo "$DONE_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log
                        TICKETS_DONE=$((TICKETS_DONE + 1))
                        log_success "Ticket $NEXT_TICKET complete (recovered from unclear status)!"
                        continue  # Skip the BLOCKED logic below
                    else
                        log_warn "PR creation failed, marking as blocked"
                    fi
                fi
            fi

            # If we get here, truly blocked
            log_warn "Max attempts exceeded, marking as blocked"
            write_summary "$NEXT_TICKET" "BLOCKED" "$MAX_ATTEMPTS" "" "$(get_ticket_usage "$NEXT_TICKET")"

            BLOCK_OUTPUT=$("$RALPH_SCRIPTS/mark-blocked.sh" "$NEXT_TICKET" "Exceeded $MAX_ATTEMPTS attempts" 2>&1)
            echo "$BLOCK_OUTPUT" | grep -v "JSON_OUTPUT" | tee_log

            log_error_context "Ticket blocked: max attempts" "Ticket: $NEXT_TICKET, Attempts: $MAX_ATTEMPTS"
            save_state_snapshot "${NEXT_TICKET}-blocked"
            TICKETS_BLOCKED=$((TICKETS_BLOCKED + 1))
        fi

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

    # Get current counts from GitHub (source of truth)
    local FINAL_OPEN=0
    local FINAL_CLOSED=0
    local FINAL_TOTAL=0
    local FINAL_BLOCKED=0

    if [ "$SETUP_SOURCE" = "github" ]; then
        FINAL_OPEN=$(gh issue list --state open --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        FINAL_CLOSED=$(gh issue list --state closed --json number --limit 1000 2>/dev/null | jq 'length' || echo "0")
        FINAL_BLOCKED=$(gh issue list --state open --label blocked --json number --limit 1000 2>/dev/null | jq 'length' 2>/dev/null || echo "0")
        FINAL_TOTAL=$((FINAL_OPEN + FINAL_CLOSED))
    fi

    # Show instance stats
    echo -e "${BOLD}This Instance:${NC}" | tee_log
    echo -e "  Completed:    ${GREEN}$TICKETS_DONE${NC}" | tee_log
    echo -e "  Blocked:      ${YELLOW}$TICKETS_BLOCKED${NC}" | tee_log
    echo "" | tee_log

    # Show overall progress (from GitHub)
    if [ "$SETUP_SOURCE" = "github" ] && [ "$FINAL_TOTAL" -gt 0 ]; then
        echo -e "${BOLD}GitHub Status:${NC}" | tee_log
        echo -e "  Closed:       ${GREEN}$FINAL_CLOSED${NC} / ${CYAN}$FINAL_TOTAL${NC}" | tee_log
        echo -e "  Open:         ${CYAN}$FINAL_OPEN${NC}" | tee_log
        echo -e "  Blocked:      ${YELLOW}$FINAL_BLOCKED${NC}" | tee_log
        echo "" | tee_log
    fi

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
        echo "This instance - Completed: $TICKETS_DONE, Blocked: $TICKETS_BLOCKED"
        [ "$SETUP_SOURCE" = "github" ] && echo "GitHub - Closed: $FINAL_CLOSED/$FINAL_TOTAL, Open: $FINAL_OPEN, Blocked: $FINAL_BLOCKED"
        echo ""
        echo "Log files in: $LOG_DIR"
        echo "========================================"
    } >> "$MAIN_LOG"

    echo "" | tee_log
    echo -e "${CYAN}Full logs:${NC} $LOG_DIR" | tee_log
    echo "" | tee_log

    # Determine if all work is done
    if [ "$SETUP_SOURCE" = "github" ]; then
        if [ "$FINAL_OPEN" -eq 0 ] || [ "$FINAL_OPEN" -eq "$FINAL_BLOCKED" ]; then
            echo -e "${GREEN}${BOLD}PRD_COMPLETE${NC}" | tee_log
            log_to_file "RESULT: PRD_COMPLETE"
            exit 0
        else
            echo -e "${YELLOW}PRD_INCOMPLETE${NC} (${FINAL_OPEN} tickets remaining)" | tee_log
            log_to_file "RESULT: PRD_INCOMPLETE"
            exit 1
        fi
    else
        # Local mode - use local counts
        if [ $TICKETS_DONE -gt 0 ] && [ $TICKETS_BLOCKED -eq 0 ]; then
            echo -e "${GREEN}${BOLD}PRD_COMPLETE${NC}" | tee_log
            log_to_file "RESULT: PRD_COMPLETE"
            exit 0
        else
            echo -e "${YELLOW}PRD_INCOMPLETE${NC}" | tee_log
            log_to_file "RESULT: PRD_INCOMPLETE"
            exit 1
        fi
    fi
}

# ============================================================================
# Run
# ============================================================================

main "$@"
