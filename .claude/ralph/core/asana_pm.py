"""Asana PM tool implementation using the Asana REST API.

This module provides a PMTool Protocol implementation for Asana, enabling
Ralph to manage tasks in Asana projects. Authentication uses Bearer tokens
via the ASANA_ACCESS_TOKEN environment variable.

SDLC-0052: AsanaPM HTTP client and authentication
"""

import logging
import os
from typing import Any

import httpx

from core.pm import PMAuthError, PMError, TicketInfo, TicketStatus

logger = logging.getLogger(__name__)

# Asana API base URL
ASANA_API_BASE = "https://app.asana.com/api/1.0"


class AsanaPM:
    """PM tool implementation using Asana REST API.

    This implementation queries Asana tasks for ticket status and uses
    tags for concurrency control (ralph-* tags for claiming tickets).

    Environment Variables Required:
        ASANA_ACCESS_TOKEN: Personal Access Token for Asana API
        ASANA_WORKSPACE_ID: Workspace GID where tasks are managed
        ASANA_PROJECT_ID: Project GID containing the tasks

    Example:
        >>> pm = AsanaPM()
        >>> status = pm.get_ticket_status("12345")
    """

    def __init__(self, blocked_label: str = "blocked") -> None:
        """Initialize AsanaPM with environment credentials.

        Args:
            blocked_label: Tag name used to mark blocked tickets (default: "blocked")

        Raises:
            PMAuthError: If required environment variables are not set
        """
        self._blocked_label = blocked_label

        # Load and validate credentials from environment
        self._access_token = os.environ.get("ASANA_ACCESS_TOKEN")
        self._workspace_id = os.environ.get("ASANA_WORKSPACE_ID")
        self._project_id = os.environ.get("ASANA_PROJECT_ID")

        missing: list[str] = []
        if not self._access_token:
            missing.append("ASANA_ACCESS_TOKEN")
        if not self._workspace_id:
            missing.append("ASANA_WORKSPACE_ID")
        if not self._project_id:
            missing.append("ASANA_PROJECT_ID")

        if missing:
            raise PMAuthError(
                f"Missing required Asana credentials: {', '.join(missing)}. "
                "Please set these environment variables."
            )

        # Cache for tag GIDs (tag name -> GID)
        self._tag_cache: dict[str, str] = {}

        logger.info(
            f"AsanaPM initialized for workspace {self._workspace_id}, "
            f"project {self._project_id}"
        )

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for Asana API requests.

        Returns:
            Dictionary of headers including Authorization
        """
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Handle error responses from Asana API.

        Args:
            response: The HTTP response to check

        Raises:
            PMAuthError: For 401 Unauthorized responses
            PMError: For other error responses (404, 429, 500, etc.)
        """
        if response.status_code == 200 or response.status_code == 201:
            return

        # Try to extract error message from response
        try:
            error_data = response.json()
            errors = error_data.get("errors", [])
            error_msg = errors[0].get("message", "") if errors else ""
        except Exception:
            error_msg = ""

        if response.status_code == 401:
            raise PMAuthError(
                f"Asana authentication failed (401): {error_msg or 'Invalid token'}. "
                "Check your ASANA_ACCESS_TOKEN."
            )

        if response.status_code == 404:
            raise PMError(
                f"Asana resource not found (404): {error_msg or 'Not found'}"
            )

        if response.status_code == 429:
            raise PMError(
                f"Asana rate limit exceeded (429): {error_msg or 'Rate limited'}. "
                "Please wait before retrying."
            )

        # Generic error for other status codes
        raise PMError(
            f"Asana API error ({response.status_code}): {error_msg or 'Unknown error'}"
        )

    def _get(self, endpoint: str) -> dict[str, Any]:
        """Make a GET request to the Asana API.

        Args:
            endpoint: API endpoint path (e.g., "/tasks/12345")

        Returns:
            Response data from the 'data' field

        Raises:
            PMAuthError: For authentication errors
            PMError: For other API errors
        """
        url = f"{ASANA_API_BASE}{endpoint}"

        try:
            with httpx.Client() as client:
                response = client.get(url, headers=self._get_headers())
                self._handle_response_error(response)
                return response.json().get("data", {})
        except httpx.ConnectError as e:
            raise PMError(
                f"Network connection error: Unable to connect to Asana API. {e}"
            )
        except httpx.TimeoutException as e:
            raise PMError(f"Request timeout: Asana API did not respond in time. {e}")

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to the Asana API.

        Args:
            endpoint: API endpoint path (e.g., "/tasks/12345/addTag")
            data: Request body data (will be wrapped in {"data": ...})

        Returns:
            Response data from the 'data' field

        Raises:
            PMAuthError: For authentication errors
            PMError: For other API errors
        """
        url = f"{ASANA_API_BASE}{endpoint}"

        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self._get_headers(),
                    json={"data": data},
                )
                self._handle_response_error(response)
                return response.json().get("data", {})
        except httpx.ConnectError as e:
            raise PMError(
                f"Network connection error: Unable to connect to Asana API. {e}"
            )
        except httpx.TimeoutException as e:
            raise PMError(f"Request timeout: Asana API did not respond in time. {e}")

    def _put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a PUT request to the Asana API.

        Args:
            endpoint: API endpoint path (e.g., "/tasks/12345")
            data: Request body data (will be wrapped in {"data": ...})

        Returns:
            Response data from the 'data' field

        Raises:
            PMAuthError: For authentication errors
            PMError: For other API errors
        """
        url = f"{ASANA_API_BASE}{endpoint}"

        try:
            with httpx.Client() as client:
                response = client.put(
                    url,
                    headers=self._get_headers(),
                    json={"data": data},
                )
                self._handle_response_error(response)
                return response.json().get("data", {})
        except httpx.ConnectError as e:
            raise PMError(
                f"Network connection error: Unable to connect to Asana API. {e}"
            )
        except httpx.TimeoutException as e:
            raise PMError(f"Request timeout: Asana API did not respond in time. {e}")

    # =========================================================================
    # PMTool Protocol Methods (stub implementations for SDLC-0052)
    # These will be fully implemented in subsequent tickets
    # =========================================================================

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of an Asana task.

        Args:
            ticket_id: Task GID in Asana

        Returns:
            TicketStatus indicating current state

        Raises:
            PMError: If operation fails
        """
        # Stub implementation - will be completed in SDLC-0054
        raise NotImplementedError("get_ticket_status will be implemented in SDLC-0054")

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a task by adding a tag.

        Args:
            ticket_id: Task GID in Asana
            label: Tag name to add (e.g., "ralph-1")

        Returns:
            True if claim succeeded, False otherwise
        """
        # Stub implementation - will be completed in SDLC-0055
        raise NotImplementedError("claim_ticket will be implemented in SDLC-0055")

    def close_ticket(self, ticket_id: str) -> bool:
        """Complete an Asana task.

        Args:
            ticket_id: Task GID in Asana

        Returns:
            True if close succeeded, False otherwise
        """
        # Stub implementation - will be completed in SDLC-0056
        raise NotImplementedError("close_ticket will be implemented in SDLC-0056")

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark a task as blocked with a comment.

        Args:
            ticket_id: Task GID in Asana
            reason: Reason why the task is blocked

        Returns:
            True if operation succeeded, False otherwise
        """
        # Stub implementation - will be completed in SDLC-0057
        raise NotImplementedError("add_blocked_label will be implemented in SDLC-0057")

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if a task is claimed by any Ralph instance.

        Args:
            ticket_id: Task GID in Asana

        Returns:
            Tuple of (is_claimed, claiming_label)
        """
        # Stub implementation - will be completed in SDLC-0055
        raise NotImplementedError("is_ticket_claimed will be implemented in SDLC-0055")

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open tasks from the provided list.

        Args:
            ticket_ids: List of task GIDs to check

        Returns:
            List of TicketInfo for tasks that are open
        """
        # Stub implementation - will be completed in SDLC-0058
        raise NotImplementedError("get_open_tickets will be implemented in SDLC-0058")

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a tag from a task.

        Args:
            ticket_id: Task GID in Asana
            label: Tag name to remove

        Returns:
            True if removal succeeded, False otherwise
        """
        # Stub implementation - will be completed in SDLC-0058
        raise NotImplementedError("remove_label will be implemented in SDLC-0058")

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign a task to the current user.

        Args:
            ticket_id: Task GID in Asana

        Returns:
            True if assignment succeeded, False otherwise
        """
        # Stub implementation - will be completed in SDLC-0058
        raise NotImplementedError("assign_to_self will be implemented in SDLC-0058")
