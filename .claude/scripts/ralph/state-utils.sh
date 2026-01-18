#!/bin/bash
#
# State Utilities for Ralph Loop V2
#
# Functions for managing engineer state files, validation reports, and summaries.
#
# Usage: source this file from ralph-prd.sh
#
# Depends on: jq
#

# Colors (inherit from parent or set defaults)
RED="${RED:-\033[0;31m}"
GREEN="${GREEN:-\033[0;32m}"
YELLOW="${YELLOW:-\033[1;33m}"
CYAN="${CYAN:-\033[0;36m}"
BOLD="${BOLD:-\033[1m}"
NC="${NC:-\033[0m}"

# State directory (configurable via config.yaml or default)
STATE_DIRECTORY="${STATE_DIRECTORY:-docs/state}"

# ============================================================================
# Directory Management
# ============================================================================

# Ensure state directory exists for a ticket/attempt
# Usage: ensure_state_dir <ticket_id> <attempt>
# Returns: path to the attempt directory
ensure_state_dir() {
    local ticket_id="$1"
    local attempt="$2"

    if [ -z "$ticket_id" ] || [ -z "$attempt" ]; then
        echo "ERROR: ensure_state_dir requires ticket_id and attempt" >&2
        return 1
    fi

    local dir="$STATE_DIRECTORY/$ticket_id/attempt-$attempt"
    mkdir -p "$dir"
    echo "$dir"
}

# Get path to ticket state directory
# Usage: get_ticket_state_dir <ticket_id>
get_ticket_state_dir() {
    local ticket_id="$1"
    echo "$STATE_DIRECTORY/$ticket_id"
}

# ============================================================================
# Attempt Management
# ============================================================================

# Get the latest attempt number for a ticket
# Usage: get_latest_attempt <ticket_id>
# Returns: highest attempt number, or 0 if none exist
get_latest_attempt() {
    local ticket_id="$1"
    local ticket_dir="$STATE_DIRECTORY/$ticket_id"

    if [ ! -d "$ticket_dir" ]; then
        echo "0"
        return
    fi

    # Find attempt directories and get the highest number
    local max_attempt=0
    for dir in "$ticket_dir"/attempt-*; do
        if [ -d "$dir" ]; then
            local attempt_num=$(basename "$dir" | sed 's/attempt-//')
            if [ "$attempt_num" -gt "$max_attempt" ] 2>/dev/null; then
                max_attempt=$attempt_num
            fi
        fi
    done

    echo "$max_attempt"
}

# ============================================================================
# State File Reading
# ============================================================================

# Get previous engineer state file (markdown or JSON)
# Usage: get_previous_state <ticket_id> [attempt]
# If attempt not specified, uses latest attempt
# Returns: contents of engineer-state.md (preferred) or .json, or empty string if not found
get_previous_state() {
    local ticket_id="$1"
    local attempt="${2:-}"

    if [ -z "$attempt" ]; then
        attempt=$(get_latest_attempt "$ticket_id")
    fi

    if [ "$attempt" -eq 0 ]; then
        echo ""
        return
    fi

    local state_dir="$STATE_DIRECTORY/$ticket_id/attempt-$attempt"
    local md_file="$state_dir/engineer-state.md"
    local json_file="$state_dir/engineer-state.json"

    if [ -f "$md_file" ]; then
        cat "$md_file"
    elif [ -f "$json_file" ]; then
        # Fallback: convert JSON to readable format
        jq -r 'to_entries | .[] | "**\(.key):** \(.value)"' "$json_file" 2>/dev/null || cat "$json_file"
    else
        echo ""
    fi
}

# Get previous validation report (markdown or JSON)
# Usage: get_previous_validation <ticket_id> [attempt]
# If attempt not specified, uses latest attempt
# Returns: contents of validation.md (preferred) or .json, or empty string if not found
get_previous_validation() {
    local ticket_id="$1"
    local attempt="${2:-}"

    if [ -z "$attempt" ]; then
        attempt=$(get_latest_attempt "$ticket_id")
    fi

    if [ "$attempt" -eq 0 ]; then
        echo ""
        return
    fi

    local state_dir="$STATE_DIRECTORY/$ticket_id/attempt-$attempt"
    local md_file="$state_dir/validation.md"
    local json_file="$state_dir/validation.json"

    if [ -f "$md_file" ]; then
        cat "$md_file"
    elif [ -f "$json_file" ]; then
        # Fallback: convert JSON to readable format
        jq -r 'to_entries | .[] | "**\(.key):** \(.value)"' "$json_file" 2>/dev/null || cat "$json_file"
    else
        echo ""
    fi
}

# ============================================================================
# State File Writing
# ============================================================================

# Write JSON and generate markdown file
# Usage: write_json_and_md <output_dir> <base_name> <json_content> <template_type>
# template_type: "engineer-state" | "validation" | "summary"
write_json_and_md() {
    local output_dir="$1"
    local base_name="$2"
    local json_content="$3"
    local template_type="$4"

    mkdir -p "$output_dir"

    # Write JSON file
    echo "$json_content" > "$output_dir/${base_name}.json"

    # Generate markdown based on template type
    case "$template_type" in
        engineer-state)
            generate_engineer_state_md "$json_content" > "$output_dir/${base_name}.md"
            ;;
        validation)
            generate_validation_md "$json_content" > "$output_dir/${base_name}.md"
            ;;
        summary)
            generate_summary_md "$json_content" > "$output_dir/${base_name}.md"
            ;;
        *)
            echo "ERROR: Unknown template type: $template_type" >&2
            return 1
            ;;
    esac
}

# Generate engineer state markdown from JSON
generate_engineer_state_md() {
    local json_content="$1"

    local ticket_id=$(echo "$json_content" | jq -r '.ticket_id // "UNKNOWN"')
    local attempt=$(echo "$json_content" | jq -r '.attempt // 1')
    local timestamp=$(echo "$json_content" | jq -r '.timestamp // "N/A"')
    local status=$(echo "$json_content" | jq -r '.status // "unknown"')
    local branch=$(echo "$json_content" | jq -r '.branch // "N/A"')
    local last_commit=$(echo "$json_content" | jq -r '.last_commit // "N/A"')

    # Validation results
    local typecheck=$(echo "$json_content" | jq -r '.validation_result.typecheck // "skip"')
    local lint=$(echo "$json_content" | jq -r '.validation_result.lint // "skip"')
    local test_result=$(echo "$json_content" | jq -r '.validation_result.test // "skip"')
    local build=$(echo "$json_content" | jq -r '.validation_result.build // "skip"')
    local overall=$(echo "$json_content" | jq -r '.validation_result.overall // "unknown"')

    # Convert status to display text
    status_display() {
        case "$1" in
            pass) echo "PASS" ;;
            fail) echo "FAIL" ;;
            skip) echo "SKIP" ;;
            *) echo "$1" ;;
        esac
    }

    # Generate list sections
    local work_completed=$(echo "$json_content" | jq -r '(.work_completed // []) | if length == 0 then "- No work items recorded" else .[] | "- " + . end')
    local files_modified=$(echo "$json_content" | jq -r '(.files_modified // []) | if length == 0 then "- No files recorded" else .[] | "- `" + . + "`" end')
    local known_issues=$(echo "$json_content" | jq -r '(.known_issues // []) | if length == 0 then "- No known issues" else .[] | "- " + . end')
    local next_steps=$(echo "$json_content" | jq -r '(.next_steps // []) | if length == 0 then "- No next steps specified" else to_entries | .[] | "\(.key + 1). \(.value)" end')
    local tests_written=$(echo "$json_content" | jq -r '(.tests_written // []) | if length == 0 then "No tests recorded" else .[] | "### " + .file + "\n\n" + (.tests | map("- " + .) | join("\n")) end')

    cat << HEREDOC
# Engineer State: $ticket_id

**Attempt:** $attempt
**Timestamp:** $timestamp
**Status:** $status
**Branch:** \`$branch\`
**Last Commit:** \`$last_commit\`

---

## Validation Result

| Check | Result |
|-------|--------|
| TypeScript | $(status_display "$typecheck") |
| Lint | $(status_display "$lint") |
| Tests | $(status_display "$test_result") |
| Build | $(status_display "$build") |
| **Overall** | **$(status_display "$overall")** |

---

## Work Completed

$work_completed

---

## Files Modified

$files_modified

---

## Tests Written

$tests_written

---

## Known Issues

$known_issues

---

## Next Steps (If Resuming)

$next_steps
HEREDOC
}

# Generate validation report markdown from JSON
generate_validation_md() {
    local json_content="$1"

    local ticket_id=$(echo "$json_content" | jq -r '.ticket_id // "UNKNOWN"')
    local attempt=$(echo "$json_content" | jq -r '.attempt // 1')
    local timestamp=$(echo "$json_content" | jq -r '.timestamp // "N/A"')
    local overall_result=$(echo "$json_content" | jq -r '.overall_result // "unknown"')

    # Check statuses
    local ts_status=$(echo "$json_content" | jq -r '.checks.typecheck.status // "skip"')
    local ts_errors=$(echo "$json_content" | jq -r '.checks.typecheck.error_count // 0')
    local lint_status=$(echo "$json_content" | jq -r '.checks.lint.status // "skip"')
    local lint_errors=$(echo "$json_content" | jq -r '.checks.lint.error_count // 0')
    local lint_warnings=$(echo "$json_content" | jq -r '.checks.lint.warning_count // 0')
    local test_status=$(echo "$json_content" | jq -r '.checks.test.status // "skip"')
    local test_total=$(echo "$json_content" | jq -r '.checks.test.total // 0')
    local test_passed=$(echo "$json_content" | jq -r '.checks.test.passed // 0')
    local test_failed=$(echo "$json_content" | jq -r '.checks.test.failed // 0')
    local build_status=$(echo "$json_content" | jq -r '.checks.build.status // "skip"')
    local build_errors=$(echo "$json_content" | jq -r '.checks.build.error_count // 0')

    # Generate error lists
    local ts_error_list=$(echo "$json_content" | jq -r '(.checks.typecheck.errors // []) | if length == 0 then "No TypeScript errors" else .[] | "- **" + .file + ":" + (.line | tostring) + "**: " + .message + " (" + .code + ")" end')
    local lint_error_list=$(echo "$json_content" | jq -r '(.checks.lint.errors // []) | if length == 0 then "No lint errors" else .[] | "- **" + .file + ":" + (.line | tostring) + "**: [" + .rule + "] " + .message + " (" + .severity + ")" end')
    local test_failure_list=$(echo "$json_content" | jq -r '(.checks.test.failures // []) | if length == 0 then "No test failures" else .[] | "### " + .file + "\n\n**Test:** " + .test_name + "\n\n**Error:**\n```\n" + .error + "\n```\n\n**Expected:** " + (.expected // "N/A") + "\n**Received:** " + (.received // "N/A") + "\n" end')
    local build_error_list=$(echo "$json_content" | jq -r '(.checks.build.errors // []) | if length == 0 then "No build errors" else .[] | "- **" + .file + "**: " + .message end')
    local root_cause=$(echo "$json_content" | jq -r '.root_cause_analysis // "No analysis provided"')
    local suggested_fixes=$(echo "$json_content" | jq -r '(.suggested_fixes // []) | if length == 0 then "No suggestions provided" else to_entries | .[] | "\(.key + 1). \(.value)" end')
    local priority_order=$(echo "$json_content" | jq -r '(.priority_order // []) | if length == 0 then "No priority order specified" else to_entries | .[] | "\(.key + 1). \(.value)" end')

    cat << HEREDOC
# Validation Report: $ticket_id

**Attempt:** $attempt
**Timestamp:** $timestamp
**Overall Result:** $overall_result

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| TypeScript | $ts_status | $ts_errors errors |
| Lint | $lint_status | $lint_errors errors, $lint_warnings warnings |
| Tests | $test_status | $test_passed/$test_total passed, $test_failed failed |
| Build | $build_status | $build_errors errors |

---

## TypeScript Errors

$ts_error_list

---

## Lint Errors

$lint_error_list

---

## Test Failures

$test_failure_list

---

## Build Errors

$build_error_list

---

## Root Cause Analysis

$root_cause

---

## Suggested Fixes

$suggested_fixes

---

## Priority Order

$priority_order
HEREDOC
}

# Generate summary markdown from JSON
generate_summary_md() {
    local json_content="$1"

    local ticket_id=$(echo "$json_content" | jq -r '.ticket_id // "UNKNOWN"')
    local final_status=$(echo "$json_content" | jq -r '.final_status // "UNKNOWN"')
    local total_attempts=$(echo "$json_content" | jq -r '.total_attempts // 0')
    local completed=$(echo "$json_content" | jq -r '.completed // "N/A"')
    local branch=$(echo "$json_content" | jq -r '.branch // "N/A"')
    local last_commit=$(echo "$json_content" | jq -r '.last_commit // "N/A"')
    local pr_number=$(echo "$json_content" | jq -r '.pr_number // "None (blocked)"')
    local outcome=$(echo "$json_content" | jq -r '.outcome // "No outcome recorded"')

    # Generate list sections
    local attempt_history=$(echo "$json_content" | jq -r '(.attempt_history // []) | if length == 0 then "| - | - | No history recorded |" else .[] | "| " + (.attempt | tostring) + " | " + .status + " | " + .key_issues + " |" end')
    local files_changed=$(echo "$json_content" | jq -r '(.files_changed // []) | if length == 0 then "- No files recorded" else .[] | "- `" + . + "`" end')
    local lessons_learned=$(echo "$json_content" | jq -r '(.lessons_learned // []) | if length == 0 then "- No lessons recorded" else .[] | "- " + . end')

    # Usage metrics section
    local has_usage=$(echo "$json_content" | jq -r 'if .usage then "yes" else "no" end')
    local usage_section=""
    if [ "$has_usage" = "yes" ]; then
        local total_invocations=$(echo "$json_content" | jq -r '.usage.invocation_count // 0')
        local total_duration=$(echo "$json_content" | jq -r '.usage.duration_seconds // 0')
        local total_cost=$(echo "$json_content" | jq -r '.usage.total_cost // 0')
        local input_tokens=$(echo "$json_content" | jq -r '.usage.input_tokens // 0')
        local output_tokens=$(echo "$json_content" | jq -r '.usage.output_tokens // 0')
        local cache_read=$(echo "$json_content" | jq -r '.usage.cache_read_tokens // 0')
        local model_used=$(echo "$json_content" | jq -r '.usage.model // "unknown"')
        local complexity=$(echo "$json_content" | jq -r '.usage.complexity // "unknown"')

        local mins=$((total_duration / 60))
        local secs=$((total_duration % 60))

        usage_section="---

## Usage Metrics

| Metric | Value |
|--------|-------|
| Model | $model_used |
| Complexity | $complexity |
| Invocations | $total_invocations |
| Duration | ${mins}m ${secs}s |
| Input Tokens | $input_tokens |
| Output Tokens | $output_tokens |
| Cache Read | $cache_read |
| **Cost** | \$$(printf '%.4f' $total_cost) |
"
    fi

    cat << HEREDOC
# Ticket Summary: $ticket_id

**Final Status:** $final_status
**Total Attempts:** $total_attempts
**Completed:** $completed

---

## Outcome

$outcome

---

## Attempt History

| Attempt | Status | Key Issues |
|---------|--------|------------|
$attempt_history

---

## Final State

**Branch:** \`$branch\`
**Last Commit:** \`$last_commit\`
**PR:** $pr_number

---

## Files Changed

$files_changed
$usage_section
---

## Lessons Learned

$lessons_learned
HEREDOC
}

# ============================================================================
# Summary Writing
# ============================================================================

# Write ticket summary (called when ticket completes or is blocked)
# Usage: write_summary <ticket_id> <status> <total_attempts> [pr_number] [usage_json]
# status: "SUCCESS" | "BLOCKED"
# usage_json: Optional JSON object with usage metrics for this ticket
write_summary() {
    local ticket_id="$1"
    local status="$2"
    local total_attempts="$3"
    local pr_number="${4:-}"
    local usage_json="${5:-}"

    local ticket_dir="$STATE_DIRECTORY/$ticket_id"
    mkdir -p "$ticket_dir"

    # Build attempt history from existing state files
    local attempt_history="[]"
    for ((i=1; i<=total_attempts; i++)); do
        local state_file="$ticket_dir/attempt-$i/engineer-state.json"
        log_to_file "Checking state file: $state_file" 2>/dev/null || true

        if [ -f "$state_file" ]; then
            log_to_file "  Found state file" 2>/dev/null || true
            local attempt_status=$(jq -r '.status // "unknown"' "$state_file")
            local known_issues=$(jq -r '(.known_issues // []) | join(", ") | if . == "" then "None" else . end' "$state_file")
            attempt_history=$(echo "$attempt_history" | jq --arg a "$i" --arg s "$attempt_status" --arg k "$known_issues" \
                '. + [{"attempt": ($a | tonumber), "status": $s, "key_issues": $k}]')
        else
            log_to_file "  State file NOT found" 2>/dev/null || true
            # Also check if directory exists
            local attempt_dir="$ticket_dir/attempt-$i"
            if [ -d "$attempt_dir" ]; then
                log_to_file "  Directory exists, contents: $(ls -la "$attempt_dir" 2>/dev/null)" 2>/dev/null || true
            fi
            attempt_history=$(echo "$attempt_history" | jq --arg a "$i" \
                '. + [{"attempt": ($a | tonumber), "status": "unknown", "key_issues": "No state file"}]')
        fi
    done

    # Get files changed from git
    local current_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local last_commit=$(git log -1 --format='%h' 2>/dev/null || echo "unknown")
    local files_changed=$(git diff --name-only HEAD~$total_attempts HEAD 2>/dev/null | jq -R -s 'split("\n") | map(select(. != ""))' || echo "[]")

    # Build outcome description
    local outcome
    if [ "$status" = "SUCCESS" ]; then
        outcome="Ticket completed successfully after $total_attempts attempt(s). PR #$pr_number merged."
    else
        outcome="Ticket blocked after $total_attempts attempt(s). Manual intervention required."
    fi

    # Get lessons learned from last state file if blocked
    local lessons="[]"
    if [ "$status" = "BLOCKED" ]; then
        local last_state="$ticket_dir/attempt-$total_attempts/engineer-state.json"
        if [ -f "$last_state" ]; then
            lessons=$(jq '(.known_issues // []) + (.next_steps // [])' "$last_state")
        fi
    fi

    # Build base JSON
    local json_content=$(jq -n \
        --arg ticket_id "$ticket_id" \
        --arg final_status "$status" \
        --argjson total_attempts "$total_attempts" \
        --arg completed "$(date -Iseconds)" \
        --arg outcome "$outcome" \
        --argjson attempt_history "$attempt_history" \
        --arg branch "$current_branch" \
        --arg last_commit "$last_commit" \
        --arg pr_number "${pr_number:-None (blocked)}" \
        --argjson files_changed "$files_changed" \
        --argjson lessons_learned "$lessons" \
        '{
            ticket_id: $ticket_id,
            final_status: $final_status,
            total_attempts: $total_attempts,
            completed: $completed,
            outcome: $outcome,
            attempt_history: $attempt_history,
            branch: $branch,
            last_commit: $last_commit,
            pr_number: $pr_number,
            files_changed: $files_changed,
            lessons_learned: $lessons_learned
        }')

    # Add usage metrics if provided
    if [ -n "$usage_json" ] && echo "$usage_json" | jq empty 2>/dev/null; then
        json_content=$(echo "$json_content" | jq --argjson usage "$usage_json" '. + {usage: $usage}')
    fi

    write_json_and_md "$ticket_dir" "summary" "$json_content" "summary"

    echo "$ticket_dir/summary.md"
}

# ============================================================================
# Prompt Building
# ============================================================================

# Build a prompt from a template file with placeholder substitution
# Usage: build_prompt <template_file> KEY1=value1 KEY2=value2 ...
# Substitutes all {KEY} patterns with provided values
# Also automatically reads commands from config.yaml
build_prompt() {
    local template_file="$1"
    shift

    if [ ! -f "$template_file" ]; then
        echo "ERROR: Template file not found: $template_file" >&2
        return 1
    fi

    local content
    content=$(cat "$template_file")

    # Process all KEY=VALUE arguments
    while [[ $# -gt 0 ]]; do
        local key="${1%%=*}"
        local value="${1#*=}"
        # Escape special characters in value for sed
        local escaped_value=$(printf '%s\n' "$value" | sed -e 's/[&/\]/\\&/g' -e 's/$/\\n/' | tr -d '\n' | sed 's/\\n$//')
        content=$(echo "$content" | sed "s|{$key}|$escaped_value|g")
        shift
    done

    # Substitute REPO_ROOT with the project root (absolute path)
    # Script is at .claude/scripts/ralph/ so go up 3 levels to reach project root
    local repo_root
    repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
    content=$(echo "$content" | sed "s|{REPO_ROOT}|$repo_root|g")

    # Auto-substitute common commands from config.yaml if not already provided
    local config_file="config.yaml"
    if [ -f "$config_file" ]; then
        # Read dev commands
        local typecheck_cmd=$(grep -E "^\s*typecheck_command:" "$config_file" 2>/dev/null | sed 's/.*typecheck_command:\s*"\?\([^"]*\)"\?/\1/' | head -1)
        local lint_cmd=$(grep -E "^\s*lint_command:" "$config_file" 2>/dev/null | sed 's/.*lint_command:\s*"\?\([^"]*\)"\?/\1/' | head -1)
        local test_cmd=$(grep -E "^\s*test_command:" "$config_file" 2>/dev/null | sed 's/.*test_command:\s*"\?\([^"]*\)"\?/\1/' | head -1)
        local build_cmd=$(grep -E "^\s*build_command:" "$config_file" 2>/dev/null | sed 's/.*build_command:\s*"\?\([^"]*\)"\?/\1/' | head -1)
        local default_branch=$(grep -E "^\s*default_branch:" "$config_file" 2>/dev/null | sed 's/.*default_branch:\s*"\?\([^"]*\)"\?/\1/' | head -1)

        # Only substitute if placeholder still exists (wasn't overridden)
        [ -n "$typecheck_cmd" ] && content=$(echo "$content" | sed "s|{TYPECHECK_COMMAND}|$typecheck_cmd|g")
        [ -n "$lint_cmd" ] && content=$(echo "$content" | sed "s|{LINT_COMMAND}|$lint_cmd|g")
        [ -n "$test_cmd" ] && content=$(echo "$content" | sed "s|{TEST_COMMAND}|$test_cmd|g")
        [ -n "$build_cmd" ] && content=$(echo "$content" | sed "s|{BUILD_COMMAND}|$build_cmd|g")
        [ -n "$default_branch" ] && content=$(echo "$content" | sed "s|{DEFAULT_BRANCH}|$default_branch|g")
    fi

    # Warn about any remaining unsubstituted placeholders
    local remaining=$(echo "$content" | grep -oE '\{[A-Z_]+\}' | sort -u)
    if [ -n "$remaining" ]; then
        echo "WARNING: Unsubstituted placeholders remain:" >&2
        echo "$remaining" | while read placeholder; do
            echo "  - $placeholder" >&2
        done
    fi

    echo "$content"
}

# Build initial engineer prompt
# Usage: build_engineer_initial_prompt <ticket_id> <prd_path> <plan_path> <max_attempts>
build_engineer_initial_prompt() {
    local ticket_id="$1"
    local prd_path="$2"
    local plan_path="$3"
    local max_attempts="${4:-3}"

    local template=".claude/prompts/engineer-initial.md"

    build_prompt "$template" \
        "TICKET_ID=$ticket_id" \
        "PRD_PATH=$prd_path" \
        "PLAN_PATH=$plan_path" \
        "MAX_ATTEMPTS=$max_attempts"
}

# Build resume engineer prompt
# Usage: build_engineer_resume_prompt <ticket_id> <attempt> <max_attempts> <branch> <prev_state> <prev_validation> <priority> <fixes>
build_engineer_resume_prompt() {
    local ticket_id="$1"
    local attempt="$2"
    local max_attempts="$3"
    local branch="$4"
    local prev_state="$5"
    local prev_validation="$6"
    local priority="${7:-}"
    local fixes="${8:-}"

    local prev_attempt=$((attempt - 1))
    local template=".claude/prompts/engineer-resume.md"

    build_prompt "$template" \
        "TICKET_ID=$ticket_id" \
        "ATTEMPT=$attempt" \
        "MAX_ATTEMPTS=$max_attempts" \
        "EXISTING_BRANCH=$branch" \
        "PREV_ATTEMPT=$prev_attempt" \
        "PREVIOUS_ENGINEER_STATE=$prev_state" \
        "PREVIOUS_VALIDATION_REPORT=$prev_validation" \
        "PRIORITY_ORDER=$priority" \
        "SUGGESTED_FIXES=$fixes"
}

# Build validator prompt
# Usage: build_validator_prompt <ticket_id> <attempt> <branch>
build_validator_prompt() {
    local ticket_id="$1"
    local attempt="$2"
    local branch="$3"

    local template=".claude/prompts/validator.md"

    build_prompt "$template" \
        "TICKET_ID=$ticket_id" \
        "ATTEMPT=$attempt" \
        "BRANCH=$branch"
}

# ============================================================================
# JSON Output Marker (for script output parsing)
# ============================================================================

# Output JSON with marker for parsing by orchestrator
output_json() {
    local json="$1"
    echo "---JSON_OUTPUT---"
    echo "$json"
}
