# Handover Document Generator

Create a handover document at `tmp/handover.md` to preserve context for the next session.

## Instructions

Write a comprehensive handover document that includes:

1. **What Was Done** - Summary of the work completed in this session
2. **Problem** - What issue was being addressed
3. **Solution Implemented** - Technical details of the fix/implementation
4. **Files Modified** - Table of all files changed with brief descriptions
5. **What Needs Testing** - Specific steps to verify the work
6. **Expected Outcome** - What success looks like
7. **If It Still Fails** - Troubleshooting steps and fallback options

## Output Location

Save to: `tmp/handover.md`

## Purpose

This document allows the next Claude session (after devcontainer rebuild or context reset) to quickly understand:
- What was accomplished
- What state the work is in
- What needs to be done next
