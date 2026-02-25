"""Tests for core.claude_cli module.

Tests the shared stream-json parsing utility extracted from:
- commands/orchestrator.py (invoke_claude, invoke_validator)
- commands/scripted_checks.py (run_post_loop_review)
"""

from core.claude_cli import parse_stream_json_result


class TestParseStreamJsonResult:
    """Tests for parse_stream_json_result()."""

    def test_extracts_result_from_valid_stream_json(self):
        """Given stream-json output with a result line, returns the result text."""
        output = (
            '{"type":"system","message":"Starting..."}\n'
            '{"type":"assistant","content":"Working on it..."}\n'
            '{"type":"result","result":"VALIDATION_PASSED\\n\\nTicket: SLCA-0001"}\n'
        )
        result = parse_stream_json_result(output)
        assert result == "VALIDATION_PASSED\n\nTicket: SLCA-0001"

    def test_extracts_result_with_spaces_in_type_field(self):
        """Given stream-json with spaces around type field, still extracts result."""
        output = '{"type": "result", "result": "Hello world"}\n'
        result = parse_stream_json_result(output)
        assert result == "Hello world"

    def test_returns_full_output_when_no_result_line(self):
        """Given output with no result line, returns the full output as fallback."""
        output = "Some plain text output\nwith multiple lines\n"
        result = parse_stream_json_result(output)
        assert result == output

    def test_returns_empty_string_for_empty_input(self):
        """Given empty input, returns empty string."""
        result = parse_stream_json_result("")
        assert result == ""

    def test_skips_malformed_json_lines(self):
        """Given lines that look like result but are malformed JSON, skips them."""
        output = (
            '{"type":"result" BROKEN JSON\n'
            '{"type":"result","result":"actual result"}\n'
        )
        result = parse_stream_json_result(output)
        assert result == "actual result"

    def test_returns_first_result_line_only(self):
        """Given multiple result lines, returns only the first one."""
        output = (
            '{"type":"result","result":"first result"}\n'
            '{"type":"result","result":"second result"}\n'
        )
        result = parse_stream_json_result(output)
        assert result == "first result"

    def test_ignores_non_result_type_lines(self):
        """Given lines with 'result' in them but type is not 'result', skips them."""
        output = (
            '{"type":"assistant","content":"The result is..."}\n'
            '{"type":"result","result":"actual result"}\n'
        )
        result = parse_stream_json_result(output)
        assert result == "actual result"

    def test_handles_empty_result_field(self):
        """Given result line with empty result field, returns the full output."""
        output = '{"type":"result","result":""}\n'
        result = parse_stream_json_result(output)
        assert result == output

    def test_handles_mixed_stdout_stderr_output(self):
        """Given combined stdout+stderr with result line buried in noise, extracts it."""
        output = (
            "Loading configuration...\n"
            "Warning: some stderr message\n"
            '{"type":"system","message":"init"}\n'
            '{"type":"result","result":"REVIEW_COMPLETE\\n\\nAll good."}\n'
            "Process completed.\n"
        )
        result = parse_stream_json_result(output)
        assert result == "REVIEW_COMPLETE\n\nAll good."
