#!/bin/bash
# Parse Plan Dependencies - Extract ticket dependencies from plan markdown
# Usage: parse-plan-deps.sh <plan-path> <ticket-prefix>
#
# Reads ticket dependencies from a plan document and outputs JSON mapping
# ticket IDs to their dependencies.
#
# Supports TWO formats:
#
# FORMAT 1 - Table format:
# | # | Title | Description | Priority | Complexity | Phase | Dependencies |
# |---|-------|-------------|----------|------------|-------|--------------|
# | 1 | Title | Desc        | P1       | 2          | 1     | -            |
# | 2 | Title | Desc        | P1       | 2          | 1     | 1            |
#
# FORMAT 2 - Section format:
# ### TEST-001: Title here
# - **Dependencies:** None (or TEST-001, TEST-002)
#
# Output: JSON object mapping ticket ID to dependency array
# {
#   "AUCT-0161": [],
#   "AUCT-0162": ["AUCT-0161"],
#   "AUCT-0169": ["AUCT-0163", "AUCT-0168"]
# }

set -e

PLAN_PATH="${1:-}"
TICKET_PREFIX="${2:-}"

if [ -z "$PLAN_PATH" ] || [ -z "$TICKET_PREFIX" ]; then
    echo "Usage: parse-plan-deps.sh <plan-path> <ticket-prefix>" >&2
    exit 1
fi

if [ ! -f "$PLAN_PATH" ]; then
    echo "Error: Plan not found: $PLAN_PATH" >&2
    exit 1
fi

# Find the starting ticket number from config.yaml or workflow-state.json
# We need to map plan row # to actual ticket ID
# Use PROJECT_ROOT if passed from parent, otherwise use pwd
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try to get ticket counter start from config.yaml
# The counter in config.yaml is the NEXT number to use, so we need to find
# what the first ticket number was when these tickets were created
#
# Strategy: Look for actual ticket IDs in the plan/PRD and extract the starting number
FIRST_TICKET=$(grep -oE "${TICKET_PREFIX}-[0-9]+" "$PLAN_PATH" 2>/dev/null | head -1)

if [ -z "$FIRST_TICKET" ]; then
    # Try PRD in same directory
    PRD_PATH=$(dirname "$PLAN_PATH")/../prds/$(basename "$PLAN_PATH")
    if [ -f "$PRD_PATH" ]; then
        FIRST_TICKET=$(grep -oE "${TICKET_PREFIX}-[0-9]+" "$PRD_PATH" 2>/dev/null | head -1)
    fi
fi

# For table format, we need a starting number
# For section format, ticket IDs are explicit in the headers
START_NUM=1
if [ -n "$FIRST_TICKET" ]; then
    # Extract the starting number (e.g., "AUCT-0161" -> 161)
    START_NUM=$(echo "$FIRST_TICKET" | sed "s/${TICKET_PREFIX}-0*//" | sed 's/^0*//')
    if [ -z "$START_NUM" ]; then
        START_NUM=1
    fi
fi

# Parse the Tickets table from the plan
# Look for lines that start with | and have a number in the first column
# Format: | # | Title | Description | Priority | Complexity | Phase | Dependencies |

# First, find all ticket rows (lines starting with | followed by a number)
# Extract: row number and dependencies column

declare -A PLAN_NUM_TO_TICKET
declare -A TICKET_DEPS

# Read the plan and find ticket table rows
IN_TABLE=false
while IFS= read -r line; do
    # Detect table start (header row)
    if echo "$line" | grep -qE '^\|\s*#\s*\|.*\|.*Dependencies'; then
        IN_TABLE=true
        continue
    fi

    # Skip separator rows
    if echo "$line" | grep -qE '^\|[-|]+\|$'; then
        continue
    fi

    # If we're in the table and hit a non-table line, we're done
    if [ "$IN_TABLE" = true ] && ! echo "$line" | grep -qE '^\|'; then
        break
    fi

    # Parse table rows
    if [ "$IN_TABLE" = true ] && echo "$line" | grep -qE '^\|\s*[0-9]+\s*\|'; then
        # Extract the row number (first column after |)
        ROW_NUM=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')

        # Extract dependencies (last column before final |)
        # Count the columns and get the last one
        DEPS=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $NF); gsub(/^[ \t]+|[ \t]+$/, "", $(NF-1)); print $(NF-1)}')

        # Calculate actual ticket ID
        # Plan row 1 = START_NUM, row 2 = START_NUM+1, etc.
        TICKET_NUM=$((START_NUM + ROW_NUM - 1))
        # Format with leading zeros (4 digits)
        TICKET_ID=$(printf "%s-%04d" "$TICKET_PREFIX" "$TICKET_NUM")

        # Store mapping
        PLAN_NUM_TO_TICKET[$ROW_NUM]="$TICKET_ID"

        # Parse dependencies (could be "-", "1", "1, 2", etc.)
        if [ "$DEPS" = "-" ] || [ -z "$DEPS" ]; then
            TICKET_DEPS[$TICKET_ID]=""
        else
            # Convert "1, 2, 3" to actual ticket IDs
            DEP_IDS=""
            for dep in $(echo "$DEPS" | tr ',' ' '); do
                dep=$(echo "$dep" | tr -d ' ')
                if [ -n "$dep" ] && [[ "$dep" =~ ^[0-9]+$ ]]; then
                    DEP_NUM=$((START_NUM + dep - 1))
                    DEP_ID=$(printf "%s-%04d" "$TICKET_PREFIX" "$DEP_NUM")
                    if [ -n "$DEP_IDS" ]; then
                        DEP_IDS="$DEP_IDS,$DEP_ID"
                    else
                        DEP_IDS="$DEP_ID"
                    fi
                fi
            done
            TICKET_DEPS[$TICKET_ID]="$DEP_IDS"
        fi
    fi
done < "$PLAN_PATH"

# If no tickets found using table format, try section format
# Section format uses: ### PREFIX-XXX: Title
#                      - **Dependencies:** PREFIX-YYY, PREFIX-ZZZ (or "None")
if [ ${#TICKET_DEPS[@]} -eq 0 ]; then
    CURRENT_TICKET=""
    while IFS= read -r line; do
        # Match section headers like "### TEST-001:" or "### AUCT-0161:"
        if echo "$line" | grep -qE "^### ${TICKET_PREFIX}-[0-9]+:"; then
            CURRENT_TICKET=$(echo "$line" | grep -oE "${TICKET_PREFIX}-[0-9]+")
            # Initialize with empty deps
            TICKET_DEPS[$CURRENT_TICKET]=""
        fi

        # Match dependencies line like "- **Dependencies:** TEST-001, TEST-002" or "- **Dependencies:** None"
        if [ -n "$CURRENT_TICKET" ] && echo "$line" | grep -qiE '^\- \*\*Dependencies:?\*\*:?'; then
            # Extract everything after "Dependencies:**" or "Dependencies:**:"
            DEPS_VALUE=$(echo "$line" | sed -E 's/^.*\*\*[Dd]ependencies:?\*\*:?\s*//')

            # Check if it's "None", "-", or empty
            if echo "$DEPS_VALUE" | grep -qiE '^(none|-)?\s*$'; then
                TICKET_DEPS[$CURRENT_TICKET]=""
            else
                # Extract ticket IDs from the dependencies (PREFIX-NNN format)
                DEP_IDS=""
                for dep_id in $(echo "$DEPS_VALUE" | grep -oE "${TICKET_PREFIX}-[0-9]+"); do
                    if [ -n "$DEP_IDS" ]; then
                        DEP_IDS="$DEP_IDS,$dep_id"
                    else
                        DEP_IDS="$dep_id"
                    fi
                done
                TICKET_DEPS[$CURRENT_TICKET]="$DEP_IDS"
            fi
        fi
    done < "$PLAN_PATH"
fi

# Output as JSON
echo "{"
FIRST=true
for ticket_id in $(echo "${!TICKET_DEPS[@]}" | tr ' ' '\n' | sort); do
    deps="${TICKET_DEPS[$ticket_id]}"

    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        echo ","
    fi

    # Convert comma-separated deps to JSON array
    if [ -z "$deps" ]; then
        printf '  "%s": []' "$ticket_id"
    else
        dep_array=$(echo "$deps" | sed 's/,/","/g')
        printf '  "%s": ["%s"]' "$ticket_id" "$dep_array"
    fi
done
echo ""
echo "}"
