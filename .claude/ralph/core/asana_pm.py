"""Asana PM tool implementation using the Asana REST API.

This module provides a PMTool Protocol implementation for Asana, enabling
Ralph to manage tasks in Asana projects. Authentication uses Bearer tokens
via the ASANA_ACCESS_TOKEN environment variable.

SDLC-0052: AsanaPM HTTP client and authentication
SDLC-0053: AsanaPM tag management
SDLC-0054: AsanaPM get_ticket_status method
SDLC-0055: AsanaPM claim_ticket and is_ticket_claimed methods
SDLC-0056: AsanaPM close_ticket with section move
SDLC-0057: AsanaPM add_blocked_label with comment
"""

import logging
import os
import re
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
    # Tag Management (SDLC-0053)
    # =========================================================================

    def _get_or_create_tag(self, name: str) -> str:
        """Get or create a tag in the workspace, returning its GID.

        Uses case-insensitive matching and caches results for performance.
        Tags are workspace-scoped in Asana.

        Args:
            name: Tag name (e.g., "ralph-1", "blocked", "task")

        Returns:
            Tag GID as string

        Raises:
            PMError: If API call fails
        """
        # Check cache first (case-insensitive key)
        cache_key = name.lower()
        if cache_key in self._tag_cache:
            logger.debug(f"Tag '{name}' found in cache: {self._tag_cache[cache_key]}")
            return self._tag_cache[cache_key]

        # Query workspace tags
        endpoint = f"/workspaces/{self._workspace_id}/tags"
        tags = self._get(endpoint)

        # Handle case where tags is a list (from API response)
        if isinstance(tags, list):
            tags_list = tags
        else:
            # Fallback if response structure is different
            tags_list = []

        # Search for existing tag (case-insensitive)
        for tag in tags_list:
            tag_name = tag.get("name", "")
            if tag_name.lower() == name.lower():
                tag_gid = tag.get("gid", "")
                # Cache with lowercase key
                self._tag_cache[cache_key] = tag_gid
                logger.debug(f"Tag '{name}' found in workspace: {tag_gid}")
                return tag_gid

        # Tag doesn't exist - create it
        logger.info(f"Tag '{name}' not found in workspace, creating...")
        create_endpoint = f"/workspaces/{self._workspace_id}/tags"
        result = self._post(create_endpoint, {"name": name, "workspace": self._workspace_id})

        tag_gid = result.get("gid", "")
        self._tag_cache[cache_key] = tag_gid
        logger.info(f"Tag '{name}' created with GID: {tag_gid}")
        return tag_gid

    # =========================================================================
    # PMTool Protocol Methods (stub implementations for SDLC-0052)
    # These will be fully implemented in subsequent tickets
    # =========================================================================

    def get_ticket_status(self, ticket_id: str) -> TicketStatus:
        """Get the current status of an Asana task.

        Checks task completion status and blocked tag to determine state:
        - If task has blocked tag -> BLOCKED
        - If task is completed -> CLOSED
        - Otherwise -> OPEN

        Note: Blocked tag is checked first, so a blocked task returns BLOCKED
        even if it's incomplete (which is the expected behavior).

        Args:
            ticket_id: Task GID in Asana

        Returns:
            TicketStatus indicating current state

        Raises:
            PMError: If operation fails (e.g., task not found)
        """
        # Fetch task with tags included
        task_data = self._get(f"/tasks/{ticket_id}")

        # Extract task completion status
        completed = task_data.get("completed", False)

        # Check for blocked tag (case-insensitive)
        tags = task_data.get("tags", [])
        for tag in tags:
            tag_name = tag.get("name", "")
            if tag_name.lower() == self._blocked_label.lower():
                return TicketStatus.BLOCKED

        # Check completion status
        if completed:
            return TicketStatus.CLOSED

        return TicketStatus.OPEN

    def claim_ticket(self, ticket_id: str, label: str) -> bool:
        """Claim a task by adding a tag.

        Adds the specified ralph-* tag to the task. The tag is created
        if it doesn't exist in the workspace.

        Args:
            ticket_id: Task GID in Asana
            label: Tag name to add (e.g., "ralph-1")

        Returns:
            True if claim succeeded, False otherwise
        """
        try:
            # Get or create the tag
            tag_gid = self._get_or_create_tag(label)

            # Add the tag to the task
            self._post(f"/tasks/{ticket_id}/addTag", {"tag": tag_gid})

            logger.info(f"Successfully claimed ticket {ticket_id} with label {label}")
            return True
        except PMError as e:
            logger.warning(f"Failed to claim ticket {ticket_id} with label {label}: {e}")
            return False

    def close_ticket(self, ticket_id: str) -> bool:
        """Complete an Asana task and optionally move to Done section.

        Marks the task as complete via the Asana API. If a "Done" section
        exists in the project, the task is also moved to that section.
        Section move failures are handled gracefully (task is still marked
        complete).

        Args:
            ticket_id: Task GID in Asana

        Returns:
            True if close succeeded, False otherwise

        SDLC-0056: AsanaPM close_ticket with section move
        """
        try:
            # 1. Mark task as complete (required)
            self._put(f"/tasks/{ticket_id}", {"completed": True})
            logger.info(f"Marked task {ticket_id} as complete")

            # 2. Try to move to Done section (optional)
            try:
                done_section_gid = self._find_done_section()
                if done_section_gid:
                    self._move_to_section(ticket_id, done_section_gid)
                    logger.info(f"Moved task {ticket_id} to Done section")
                else:
                    logger.debug(
                        f"No Done section found for project {self._project_id}, "
                        "skipping section move"
                    )
            except PMError as e:
                # Graceful degradation - section move is optional
                logger.warning(f"Failed to move task to Done section: {e}")

            return True
        except PMError as e:
            logger.warning(f"Failed to close ticket {ticket_id}: {e}")
            return False

    def _find_done_section(self) -> str | None:
        """Find the Done section in the configured project.

        Searches for a section named "Done" (case-insensitive) in the
        project configured via ASANA_PROJECT_ID.

        Returns:
            Section GID if found, None otherwise

        SDLC-0056: Section discovery for Done state
        """
        endpoint = f"/projects/{self._project_id}/sections"
        sections = self._get(endpoint)

        # Handle list response from API
        if isinstance(sections, list):
            sections_list = sections
        else:
            sections_list = []

        # Search for Done section (case-insensitive)
        for section in sections_list:
            section_name = section.get("name", "")
            if section_name.lower() == "done":
                return section.get("gid", "")

        return None

    def _move_to_section(self, ticket_id: str, section_gid: str) -> None:
        """Move a task to a specific section.

        Args:
            ticket_id: Task GID to move
            section_gid: Section GID to move the task to

        Raises:
            PMError: If the API call fails

        SDLC-0056: Moving tasks to Done section
        """
        endpoint = f"/sections/{section_gid}/addTask"
        self._post(endpoint, {"task": ticket_id})

    def add_blocked_label(self, ticket_id: str, reason: str) -> bool:
        """Mark a task as blocked with a comment.

        Adds the blocked tag to the task and posts a comment with the
        reason for blocking via the Asana stories API.

        Args:
            ticket_id: Task GID in Asana
            reason: Reason why the task is blocked

        Returns:
            True if operation succeeded, False otherwise

        SDLC-0057: AsanaPM add_blocked_label with comment
        """
        try:
            # 1. Get or create the blocked tag
            blocked_tag_gid = self._get_or_create_tag(self._blocked_label)

            # 2. Add the blocked tag to the task
            self._post(f"/tasks/{ticket_id}/addTag", {"tag": blocked_tag_gid})
            logger.info(f"Added blocked tag to task {ticket_id}")

            # 3. Post a comment with the reason via stories API
            comment_text = f"Blocked: {reason}"
            self._post(f"/tasks/{ticket_id}/stories", {"text": comment_text})
            logger.info(f"Posted blocked reason comment to task {ticket_id}")

            return True
        except PMError as e:
            logger.warning(f"Failed to add blocked label to ticket {ticket_id}: {e}")
            return False

    def is_ticket_claimed(self, ticket_id: str) -> tuple[bool, str | None]:
        """Check if a task is claimed by any Ralph instance.

        Looks for any tag starting with "ralph-" followed by a digit.
        This matches the pattern used by claim_ticket (ralph-0 through ralph-5).

        Args:
            ticket_id: Task GID in Asana

        Returns:
            Tuple of (is_claimed, claiming_label) where claiming_label
            is the ralph-* label if claimed, None otherwise
        """
        try:
            # Fetch task with tags
            task_data = self._get(f"/tasks/{ticket_id}")

            # Check for ralph-N tags (where N is a digit)
            tags = task_data.get("tags", [])
            for tag in tags:
                tag_name = tag.get("name", "")
                # Match "ralph-" followed by one or more digits
                if re.match(r"^ralph-\d+$", tag_name):
                    return (True, tag_name)

            return (False, None)
        except PMError as e:
            logger.warning(f"Failed to check claim status for ticket {ticket_id}: {e}")
            return (False, None)

    def get_open_tickets(self, ticket_ids: list[str]) -> list[TicketInfo]:
        """Get information about open tasks from the provided list.

        Fetches each task by ID and returns TicketInfo objects only for tasks
        that are OPEN (not completed and not blocked). Tasks that don't exist
        or fail to fetch are skipped gracefully.

        Args:
            ticket_ids: List of task GIDs to check

        Returns:
            List of TicketInfo for tasks that are open

        SDLC-0058: AsanaPM remaining methods
        """
        if not ticket_ids:
            return []

        open_tickets: list[TicketInfo] = []

        for ticket_id in ticket_ids:
            try:
                # Fetch task data
                task_data = self._get(f"/tasks/{ticket_id}")

                # Check completion status
                completed = task_data.get("completed", False)
                if completed:
                    continue  # Skip closed tasks

                # Check for blocked tag
                tags = task_data.get("tags", [])
                tag_names = [tag.get("name", "") for tag in tags]

                is_blocked = any(
                    name.lower() == self._blocked_label.lower() for name in tag_names
                )
                if is_blocked:
                    continue  # Skip blocked tasks

                # Task is open - create TicketInfo
                open_tickets.append(
                    TicketInfo(
                        id=ticket_id,
                        title=task_data.get("name", ""),
                        status=TicketStatus.OPEN,
                        labels=tag_names,
                    )
                )
            except PMError as e:
                # Skip tasks that fail to fetch (e.g., not found)
                logger.warning(f"Failed to fetch ticket {ticket_id}: {e}")
                continue

        return open_tickets

    def remove_label(self, ticket_id: str, label: str) -> bool:
        """Remove a tag from a task.

        Looks up the tag by name and removes it from the task using the
        Asana removeTag endpoint. If the tag doesn't exist in the workspace,
        returns False (can't remove a non-existent tag).

        Args:
            ticket_id: Task GID in Asana
            label: Tag name to remove

        Returns:
            True if removal succeeded, False otherwise

        SDLC-0058: AsanaPM remaining methods
        """
        try:
            # Look up the tag (don't create if it doesn't exist)
            tag_gid = self._find_tag(label)
            if tag_gid is None:
                logger.warning(
                    f"Cannot remove tag '{label}' - tag doesn't exist in workspace"
                )
                return False

            # Remove the tag from the task
            self._post(f"/tasks/{ticket_id}/removeTag", {"tag": tag_gid})

            logger.info(f"Successfully removed label '{label}' from ticket {ticket_id}")
            return True
        except PMError as e:
            logger.warning(
                f"Failed to remove label '{label}' from ticket {ticket_id}: {e}"
            )
            return False

    def _find_tag(self, name: str) -> str | None:
        """Find a tag by name in the workspace without creating it.

        Uses case-insensitive matching. Unlike _get_or_create_tag, this method
        does NOT create the tag if it doesn't exist.

        Args:
            name: Tag name to find

        Returns:
            Tag GID if found, None otherwise

        SDLC-0058: Helper for remove_label
        """
        # Check cache first (case-insensitive key)
        cache_key = name.lower()
        if cache_key in self._tag_cache:
            return self._tag_cache[cache_key]

        # Query workspace tags
        endpoint = f"/workspaces/{self._workspace_id}/tags"
        tags = self._get(endpoint)

        # Handle case where tags is a list (from API response)
        if isinstance(tags, list):
            tags_list = tags
        else:
            tags_list = []

        # Search for existing tag (case-insensitive)
        for tag in tags_list:
            tag_name = tag.get("name", "")
            if tag_name.lower() == name.lower():
                tag_gid = tag.get("gid", "")
                # Cache with lowercase key
                self._tag_cache[cache_key] = tag_gid
                return tag_gid

        # Tag doesn't exist
        return None

    def assign_to_self(self, ticket_id: str) -> bool:
        """Assign a task to the current user.

        Uses the Asana special value "me" to assign the task to the user
        associated with the access token.

        Args:
            ticket_id: Task GID in Asana

        Returns:
            True if assignment succeeded, False otherwise

        SDLC-0058: AsanaPM remaining methods
        """
        try:
            # Update the task with assignee="me"
            # "me" is a special Asana value that refers to the authenticated user
            self._put(f"/tasks/{ticket_id}", {"assignee": "me"})

            logger.info(f"Successfully assigned ticket {ticket_id} to self")
            return True
        except PMError as e:
            logger.warning(f"Failed to assign ticket {ticket_id} to self: {e}")
            return False

    # =========================================================================
    # Task Creation Methods (SDLC-0060)
    # =========================================================================

    def create_task(
        self,
        name: str,
        notes: str,
        add_task_tag: bool = False,
    ) -> str:
        """Create a new Asana task in the configured project.

        Creates a task with the given name and notes in the project specified
        by ASANA_PROJECT_ID. Optionally adds the 'task' tag.

        Args:
            name: Task name/title (e.g., "[SDLC-0001] Feature Implementation")
            notes: Task description/notes (supports markdown)
            add_task_tag: If True, add the 'task' tag after creation

        Returns:
            Task GID as string

        Raises:
            PMError: If task creation fails

        SDLC-0060: Task creation for /ticket command
        """
        # Create the task
        task_data = {
            "name": name,
            "notes": notes,
            "projects": [self._project_id],
        }

        result = self._post("/tasks", task_data)
        task_gid = result.get("gid", "")

        logger.info(f"Created task '{name}' with GID: {task_gid}")

        # Optionally add the 'task' tag
        if add_task_tag:
            try:
                tag_gid = self._get_or_create_tag("task")
                self._post(f"/tasks/{task_gid}/addTag", {"tag": tag_gid})
                logger.info(f"Added 'task' tag to task {task_gid}")
            except PMError as e:
                logger.warning(f"Failed to add 'task' tag to task {task_gid}: {e}")
                # Continue - task creation succeeded, tag is optional

        return task_gid

    def create_subtask(self, parent_task_id: str, name: str) -> str:
        """Create a subtask under a parent task.

        Creates a subtask (used for acceptance criteria) under the specified
        parent task. Subtasks appear as checklist items in Asana.

        Args:
            parent_task_id: GID of the parent task
            name: Subtask name (e.g., acceptance criterion text)

        Returns:
            Subtask GID as string

        Raises:
            PMError: If subtask creation fails

        SDLC-0060: Subtask creation for acceptance criteria
        """
        subtask_data = {"name": name}

        result = self._post(f"/tasks/{parent_task_id}/subtasks", subtask_data)
        subtask_gid = result.get("gid", "")

        logger.debug(f"Created subtask '{name}' under task {parent_task_id}")
        return subtask_gid

    def add_dependencies(self, task_id: str, dependency_ids: list[str]) -> bool:
        """Add dependencies to a task.

        Sets up dependency relationships so the task depends on the specified
        tasks. In Asana, this means the task cannot start until dependencies
        are complete.

        Args:
            task_id: GID of the task to add dependencies to
            dependency_ids: List of GIDs of tasks this task depends on

        Returns:
            True if dependencies were added, False on failure

        SDLC-0060: Dependency linking for /ticket command
        """
        if not dependency_ids:
            # No dependencies to add
            return True

        try:
            # Asana API expects dependencies as an array of GIDs
            self._post(
                f"/tasks/{task_id}/addDependencies",
                {"dependencies": dependency_ids},
            )

            logger.info(
                f"Added {len(dependency_ids)} dependencies to task {task_id}"
            )
            return True
        except PMError as e:
            logger.warning(f"Failed to add dependencies to task {task_id}: {e}")
            return False

    def ensure_required_tags(self) -> bool:
        """Ensure required tags exist in the workspace.

        Creates the following tags if they don't exist:
        - "task": Applied to all tasks created by /ticket
        - "blocked": Applied to blocked tasks
        - "ralph-0" through "ralph-5": Used for claiming tickets

        This should be called before creating the first task to ensure
        all required tags are available.

        Returns:
            True if all tags exist/were created, False on failure

        SDLC-0060: Create required tags on first /ticket run
        """
        required_tags = ["task", "blocked"] + [f"ralph-{i}" for i in range(6)]

        try:
            for tag_name in required_tags:
                # _get_or_create_tag handles creation if missing
                self._get_or_create_tag(tag_name)
                logger.debug(f"Ensured tag '{tag_name}' exists")

            logger.info(f"All {len(required_tags)} required tags exist")
            return True
        except PMError as e:
            logger.warning(f"Failed to ensure required tags: {e}")
            return False
