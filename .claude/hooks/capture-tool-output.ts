#!/usr/bin/env bun

/**
 * capture-tool-output.ts - PostToolUse Hook
 *
 * Automatically logs tool executions to daily JSONL files
 * for auditing and debugging purposes.
 *
 * Log location: .logs/tool-outputs/YYYY-MM/YYYY-MM-DD_tool-outputs.jsonl
 */

import { appendFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';

interface ToolUseData {
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_response: Record<string, unknown>;
  conversation_id: string;
  timestamp: string;
}

// Tools worth logging (skip Read for noise reduction)
const INTERESTING_TOOLS = ['Bash', 'Edit', 'Write', 'Task', 'NotebookEdit'];

async function main() {
  try {
    // Read input from stdin
    const input = await Bun.stdin.text();
    if (!input || input.trim() === '') {
      process.exit(0);
    }

    const data: ToolUseData = JSON.parse(input);

    // Only capture interesting tools
    if (!INTERESTING_TOOLS.includes(data.tool_name)) {
      process.exit(0);
    }

    // Get today's date for organization
    const now = new Date();
    const today = now.toISOString().split('T')[0]; // YYYY-MM-DD

    // Log to .logs/tool-outputs/ in current working directory
    const captureDir = join(process.cwd(), '.logs', 'tool-outputs');

    // Ensure capture directory exists
    if (!existsSync(captureDir)) {
      mkdirSync(captureDir, { recursive: true });
    }

    // Format output as JSONL (one JSON object per line)
    const captureFile = join(captureDir, `${today}-tool-outputs.jsonl`);
    const captureEntry = JSON.stringify({
      timestamp: data.timestamp || now.toISOString(),
      tool: data.tool_name,
      input: data.tool_input,
      output: data.tool_response,
      session: data.conversation_id
    }) + '\n';

    // Append to daily log
    appendFileSync(captureFile, captureEntry);

    // Exit successfully (code 0 = continue normally)
    process.exit(0);
  } catch (error) {
    // Silent failure - don't disrupt workflow
    console.error(`[Hook] PostToolUse error: ${error}`);
    process.exit(0);
  }
}

main();
