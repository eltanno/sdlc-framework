#!/usr/bin/env bun

/**
 * capture-subagent-summary.ts - SubagentStop Hook
 *
 * Logs when sub-agents complete, capturing their type and output summary.
 * Useful for tracking delegated work and debugging agent workflows.
 *
 * Log location: .logs/history/subagents/YYYY-MM-DD-subagents.jsonl
 */

import { appendFileSync, mkdirSync, existsSync, readFileSync } from 'fs';
import { join } from 'path';

interface HookInput {
  session_id: string;
  transcript_path: string;
  [key: string]: unknown;
}

interface SubagentInfo {
  agentType: string;
  completionMessage: string | null;
  toolsUsed: string[];
}

async function main() {
  try {
    // Read input from stdin with timeout
    const input = await Promise.race([
      Bun.stdin.text(),
      new Promise<string>((_, reject) => setTimeout(() => reject(new Error('timeout')), 500))
    ]);

    if (!input || input.trim() === '') {
      process.exit(0);
    }

    const data: HookInput = JSON.parse(input);

    if (!data.transcript_path) {
      process.exit(0);
    }

    // Analyze the transcript to find sub-agent info
    const subagentInfo = analyzeTranscript(data.transcript_path);

    // Generate timestamp
    const now = new Date();
    const today = now.toISOString().split('T')[0]; // YYYY-MM-DD

    // Ensure directory exists
    const subagentDir = join(process.cwd(), '.logs', 'history', 'subagents');
    if (!existsSync(subagentDir)) {
      mkdirSync(subagentDir, { recursive: true });
    }

    // Log as JSONL
    const logFile = join(subagentDir, `${today}-subagents.jsonl`);
    const logEntry = JSON.stringify({
      timestamp: now.toISOString(),
      session_id: data.session_id,
      agent_type: subagentInfo.agentType,
      completion: subagentInfo.completionMessage,
      tools_used: subagentInfo.toolsUsed
    }) + '\n';

    appendFileSync(logFile, logEntry);

    process.exit(0);
  } catch (error) {
    // Silent failure - don't disrupt workflow
    process.exit(0);
  }
}

function analyzeTranscript(transcriptPath: string): SubagentInfo {
  const result: SubagentInfo = {
    agentType: 'unknown',
    completionMessage: null,
    toolsUsed: []
  };

  try {
    if (!existsSync(transcriptPath)) {
      return result;
    }

    const transcript = readFileSync(transcriptPath, 'utf-8');
    const lines = transcript.trim().split('\n');
    const toolsUsed = new Set<string>();

    // Search through transcript
    for (let i = lines.length - 1; i >= 0; i--) {
      try {
        const entry = JSON.parse(lines[i]);

        // Look for Task tool invocation to get agent type
        if (entry.type === 'assistant' && entry.message?.content) {
          const contents = Array.isArray(entry.message.content)
            ? entry.message.content
            : [entry.message.content];

          for (const content of contents) {
            // Find Task tool use to get subagent_type
            if (content.type === 'tool_use' && content.name === 'Task') {
              if (content.input?.subagent_type) {
                result.agentType = content.input.subagent_type;
              }
            }

            // Track tools used
            if (content.type === 'tool_use' && content.name) {
              toolsUsed.add(content.name);
            }

            // Look for completion message in text
            if (content.type === 'text' && content.text) {
              const completedMatch = content.text.match(/COMPLETED:\s*(.+?)(?:\n|$)/i);
              if (completedMatch && !result.completionMessage) {
                result.completionMessage = completedMatch[1]
                  .replace(/\*+/g, '')
                  .replace(/\[.*?\]/g, '')
                  .trim()
                  .slice(0, 200); // Limit length
              }
            }
          }
        }

        // Also check tool_result for completion messages
        if (entry.type === 'user' && entry.message?.content) {
          const contents = Array.isArray(entry.message.content)
            ? entry.message.content
            : [entry.message.content];

          for (const content of contents) {
            if (content.type === 'tool_result' && content.content) {
              const text = typeof content.content === 'string'
                ? content.content
                : JSON.stringify(content.content);

              const completedMatch = text.match(/COMPLETED:\s*(.+?)(?:\n|$)/i);
              if (completedMatch && !result.completionMessage) {
                result.completionMessage = completedMatch[1]
                  .replace(/\*+/g, '')
                  .replace(/\[.*?\]/g, '')
                  .trim()
                  .slice(0, 200);
              }
            }
          }
        }
      } catch {
        // Skip invalid JSON lines
      }
    }

    result.toolsUsed = Array.from(toolsUsed);
  } catch {
    // Silent failure
  }

  return result;
}

main();
