"""Claude CLI utility functions.

Shared utilities for invoking the Claude CLI and parsing its output.
Used by commands/orchestrator.py and commands/scripted_checks.py.
"""

from __future__ import annotations

import json


def parse_stream_json_result(output: str) -> str:
    """Parse Claude CLI stream-json output to extract the result text.

    The Claude CLI with --output-format stream-json emits one JSON object
    per line. The final result is in a line with {"type": "result", "result": "..."}.

    This function scans the output for that line and returns the result text.
    If no result line is found, returns the full output as a fallback.

    Args:
        output: Raw stdout+stderr from a Claude CLI invocation

    Returns:
        The extracted result text, or the full output if no result line found
    """
    if not output:
        return ""

    for line in output.splitlines():
        if '"type"' in line and '"result"' in line:
            try:
                data = json.loads(line)
                if data.get("type") == "result":
                    result_text = data.get("result", "")
                    if result_text:
                        return result_text
            except json.JSONDecodeError:
                continue

    # No result JSON found -- return full output as fallback
    return output
