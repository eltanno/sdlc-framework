"""Main orchestrator loop for Ralph workflow.

This module implements the core Ralph loop that:
- Gets the next eligible ticket
- Invokes Claude to implement the ticket
- Handles success/failure outcomes
- Progresses through all tickets until completion
"""
