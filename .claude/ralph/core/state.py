"""State management for Ralph workflow.

This module handles reading and writing state files that track workflow
progress, ticket statuses, and execution history. All writes are atomic
to prevent corruption from interruptions.
"""
