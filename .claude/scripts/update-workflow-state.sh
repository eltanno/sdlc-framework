#!/bin/bash
# Helper script to update workflow-state.json
# Usage: update-workflow-state.sh '<jq expression>'
# Example: update-workflow-state.sh '.phase = "implement"'

set -e

if [ -z "$1" ]; then
    echo "Usage: update-workflow-state.sh '<jq expression>'" >&2
    exit 1
fi

jq "$1" workflow-state.json > tmp.$$.json && mv tmp.$$.json workflow-state.json
