"""Unit tests for the AsanaPM HTTP client, authentication, and tag management.

Tests cover:
- AsanaPM initialization with environment variables
- HTTP client authentication with Bearer token
- Error handling for missing credentials
- Error handling for API failures
- Base HTTP request functionality
- Tag management (_get_or_create_tag)
- close_ticket with section move

SDLC-0052: AsanaPM HTTP client and authentication
SDLC-0053: AsanaPM tag management
SDLC-0054: AsanaPM get_ticket_status method
SDLC-0055: AsanaPM claim_ticket and is_ticket_claimed methods
SDLC-0056: AsanaPM close_ticket with section move
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestAsanaPMInit:
    """Tests for AsanaPM initialization."""

    def test_asana_pm_can_be_instantiated_with_env_vars(self, mock_env_asana):
        """Given Asana env vars are set, when instantiating AsanaPM, then it succeeds."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert pm is not None

    def test_asana_pm_raises_auth_error_when_token_missing(self, monkeypatch):
        """Given ASANA_ACCESS_TOKEN is not set, when instantiating AsanaPM, then PMAuthError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMAuthError

        # Clear env vars
        monkeypatch.delenv("ASANA_ACCESS_TOKEN", raising=False)
        monkeypatch.delenv("ASANA_WORKSPACE_ID", raising=False)
        monkeypatch.delenv("ASANA_PROJECT_ID", raising=False)

        with pytest.raises(PMAuthError) as exc_info:
            AsanaPM()

        assert "ASANA_ACCESS_TOKEN" in str(exc_info.value)

    def test_asana_pm_raises_auth_error_when_workspace_missing(self, monkeypatch):
        """Given ASANA_WORKSPACE_ID is not set, when instantiating AsanaPM, then PMAuthError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMAuthError

        monkeypatch.setenv("ASANA_ACCESS_TOKEN", "test-token")
        monkeypatch.delenv("ASANA_WORKSPACE_ID", raising=False)
        monkeypatch.delenv("ASANA_PROJECT_ID", raising=False)

        with pytest.raises(PMAuthError) as exc_info:
            AsanaPM()

        assert "ASANA_WORKSPACE_ID" in str(exc_info.value)

    def test_asana_pm_raises_auth_error_when_project_missing(self, monkeypatch):
        """Given ASANA_PROJECT_ID is not set, when instantiating AsanaPM, then PMAuthError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMAuthError

        monkeypatch.setenv("ASANA_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("ASANA_WORKSPACE_ID", "test-workspace")
        monkeypatch.delenv("ASANA_PROJECT_ID", raising=False)

        with pytest.raises(PMAuthError) as exc_info:
            AsanaPM()

        assert "ASANA_PROJECT_ID" in str(exc_info.value)

    def test_asana_pm_stores_credentials(self, mock_env_asana):
        """Given env vars are set, when instantiating AsanaPM, then credentials are stored."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()

        assert pm._access_token == "test-token-12345"
        assert pm._workspace_id == "workspace-12345"
        assert pm._project_id == "project-12345"


class TestAsanaPMHttpClient:
    """Tests for AsanaPM HTTP client functionality."""

    def test_request_includes_bearer_token(self, mock_env_asana, mock_httpx_client):
        """Given AsanaPM, when making request, then Bearer token is included in headers."""
        from core.asana_pm import AsanaPM

        # Configure mock response
        mock_httpx_client.return_value.__enter__.return_value.get.return_value.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.get.return_value.json.return_value = {"data": {}}

        pm = AsanaPM()
        pm._get("/tasks/12345")

        # Verify Bearer token was sent
        call_args = mock_httpx_client.return_value.__enter__.return_value.get.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token-12345"

    def test_request_uses_correct_base_url(self, mock_env_asana, mock_httpx_client):
        """Given AsanaPM, when making request, then correct base URL is used."""
        from core.asana_pm import AsanaPM

        mock_httpx_client.return_value.__enter__.return_value.get.return_value.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.get.return_value.json.return_value = {"data": {}}

        pm = AsanaPM()
        pm._get("/tasks/12345")

        call_args = mock_httpx_client.return_value.__enter__.return_value.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert url.startswith("https://app.asana.com/api/1.0")

    def test_get_request_returns_data(self, mock_env_asana, mock_httpx_client):
        """Given successful GET request, when calling _get, then data is returned."""
        from core.asana_pm import AsanaPM

        expected_data = {"gid": "12345", "name": "Test Task"}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.get.return_value.json.return_value = {
            "data": expected_data
        }

        pm = AsanaPM()
        result = pm._get("/tasks/12345")

        assert result == expected_data

    def test_post_request_sends_json_body(self, mock_env_asana, mock_httpx_client):
        """Given POST request with data, when calling _post, then JSON body is sent."""
        from core.asana_pm import AsanaPM

        mock_httpx_client.return_value.__enter__.return_value.post.return_value.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.post.return_value.json.return_value = {"data": {}}

        pm = AsanaPM()
        pm._post("/tasks/12345/addTag", {"tag": "tag-gid"})

        call_args = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        json_body = call_args.kwargs.get("json", {})
        assert "data" in json_body
        assert json_body["data"]["tag"] == "tag-gid"

    def test_put_request_sends_json_body(self, mock_env_asana, mock_httpx_client):
        """Given PUT request with data, when calling _put, then JSON body is sent."""
        from core.asana_pm import AsanaPM

        mock_httpx_client.return_value.__enter__.return_value.put.return_value.status_code = 200
        mock_httpx_client.return_value.__enter__.return_value.put.return_value.json.return_value = {"data": {}}

        pm = AsanaPM()
        pm._put("/tasks/12345", {"completed": True})

        call_args = mock_httpx_client.return_value.__enter__.return_value.put.call_args
        json_body = call_args.kwargs.get("json", {})
        assert "data" in json_body
        assert json_body["data"]["completed"] is True


class TestAsanaPMErrorHandling:
    """Tests for AsanaPM error handling."""

    def test_raises_pm_auth_error_for_401(self, mock_env_asana, mock_httpx_client):
        """Given 401 response, when making request, then PMAuthError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMAuthError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errors": [{"message": "Invalid token"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMAuthError) as exc_info:
            pm._get("/tasks/12345")

        assert "Invalid" in str(exc_info.value) or "401" in str(exc_info.value) or "token" in str(exc_info.value).lower()

    def test_raises_pm_error_for_404(self, mock_env_asana, mock_httpx_client):
        """Given 404 response, when making request, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "Not found"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/invalid")

        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)

    def test_raises_pm_error_for_429_rate_limit(self, mock_env_asana, mock_httpx_client):
        """Given 429 response, when making request, then PMError is raised with rate limit message."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"errors": [{"message": "Rate limited"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/12345")

        assert "rate" in str(exc_info.value).lower() or "429" in str(exc_info.value)

    def test_raises_pm_error_for_network_failure(self, mock_env_asana, mock_httpx_client):
        """Given network failure, when making request, then PMError is raised."""
        import httpx

        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/12345")

        assert "connect" in str(exc_info.value).lower() or "network" in str(exc_info.value).lower()

    def test_raises_pm_error_for_500_server_error(self, mock_env_asana, mock_httpx_client):
        """Given 500 response, when making request, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Internal server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/12345")

        assert "500" in str(exc_info.value) or "server" in str(exc_info.value).lower()


class TestAsanaPMProtocolConformance:
    """Tests that AsanaPM properly implements PMTool Protocol methods (stubs)."""

    def test_asana_pm_has_get_ticket_status_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then get_ticket_status exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "get_ticket_status", None))

    def test_asana_pm_has_claim_ticket_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then claim_ticket exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "claim_ticket", None))

    def test_asana_pm_has_close_ticket_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then close_ticket exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "close_ticket", None))

    def test_asana_pm_has_add_blocked_label_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then add_blocked_label exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "add_blocked_label", None))

    def test_asana_pm_has_is_ticket_claimed_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then is_ticket_claimed exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "is_ticket_claimed", None))

    def test_asana_pm_has_get_open_tickets_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then get_open_tickets exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "get_open_tickets", None))

    def test_asana_pm_has_remove_label_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then remove_label exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "remove_label", None))

    def test_asana_pm_has_assign_to_self_method(self, mock_env_asana):
        """Given AsanaPM class, when checking methods, then assign_to_self exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert callable(getattr(pm, "assign_to_self", None))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_env_asana(monkeypatch):
    """Set Asana environment variables for testing."""
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "test-token-12345")
    monkeypatch.setenv("ASANA_WORKSPACE_ID", "workspace-12345")
    monkeypatch.setenv("ASANA_PROJECT_ID", "project-12345")


@pytest.fixture
def mock_httpx_client(mocker):
    """Mock httpx.Client for API calls."""
    mock = mocker.patch("core.asana_pm.httpx.Client")
    return mock


# =============================================================================
# SDLC-0053: Tag Management Tests
# =============================================================================


class TestAsanaPMTagManagement:
    """Tests for AsanaPM tag lookup and creation.

    SDLC-0053: AsanaPM tag management
    """

    def test_get_or_create_tag_returns_existing_tag_gid(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag exists in workspace, when _get_or_create_tag is called, then existing tag GID is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns the tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "existing-tag-gid-123", "name": "ralph-1"},
                {"gid": "other-tag-gid", "name": "blocked"},
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        tag_gid = pm._get_or_create_tag("ralph-1")

        assert tag_gid == "existing-tag-gid-123"

    def test_get_or_create_tag_creates_tag_when_not_exists(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag doesn't exist in workspace, when _get_or_create_tag is called, then tag is created."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns empty list
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        # Mock: POST /workspaces/{workspace_id}/tags creates new tag
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "data": {"gid": "new-tag-gid-456", "name": "ralph-2"}
        }

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        tag_gid = pm._get_or_create_tag("ralph-2")

        assert tag_gid == "new-tag-gid-456"
        # Verify POST was called to create the tag
        mock_httpx_client.return_value.__enter__.return_value.post.assert_called()

    def test_get_or_create_tag_caches_tag_gid(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag was previously looked up, when _get_or_create_tag is called again, then cached GID is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns the tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "cached-tag-gid", "name": "blocked"}]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()

        # First call
        tag_gid_1 = pm._get_or_create_tag("blocked")
        # Second call (should use cache)
        tag_gid_2 = pm._get_or_create_tag("blocked")

        assert tag_gid_1 == tag_gid_2 == "cached-tag-gid"
        # GET should only be called once due to caching
        assert (
            mock_httpx_client.return_value.__enter__.return_value.get.call_count == 1
        )

    def test_get_or_create_tag_uses_case_insensitive_match(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag exists with different case, when _get_or_create_tag is called, then existing tag is used."""
        from core.asana_pm import AsanaPM

        # Mock: Tags list returns "Blocked" (capitalized)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "Blocked"}]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        tag_gid = pm._get_or_create_tag("blocked")  # lowercase

        assert tag_gid == "blocked-tag-gid"

    def test_get_or_create_tag_sends_correct_workspace_id(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given workspace ID in env, when _get_or_create_tag is called, then correct workspace is queried."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        # Mock POST for tag creation
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "data": {"gid": "new-tag-gid", "name": "task"}
        }
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm._get_or_create_tag("task")

        # Verify GET was called with correct workspace ID
        get_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.get.call_args
        )
        url = get_call_args.args[0] if get_call_args.args else ""
        assert "workspace-12345" in url

    def test_get_or_create_tag_creates_with_correct_payload(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag doesn't exist, when _get_or_create_tag creates tag, then correct payload is sent."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns empty (tag doesn't exist)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        # Mock: POST creates tag
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "data": {"gid": "new-tag-gid", "name": "ralph-3"}
        }
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm._get_or_create_tag("ralph-3")

        # Verify POST payload contains tag name and workspace
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        json_body = post_call_args.kwargs.get("json", {})
        assert json_body.get("data", {}).get("name") == "ralph-3"
        assert json_body.get("data", {}).get("workspace") == "workspace-12345"

    def test_get_or_create_tag_handles_ralph_tags_0_through_5(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given ralph tags 0-5, when _get_or_create_tag is called, then all are handled correctly."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns empty
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        # Track created tags
        created_tags = []

        def mock_post(*args, **kwargs):
            tag_name = kwargs.get("json", {}).get("data", {}).get("name", "")
            mock_post_response = MagicMock()
            mock_post_response.status_code = 201
            mock_post_response.json.return_value = {
                "data": {"gid": f"gid-for-{tag_name}", "name": tag_name}
            }
            created_tags.append(tag_name)
            return mock_post_response

        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = (
            mock_post
        )

        pm = AsanaPM()

        # Test all ralph tags from 0 to 5
        for i in range(6):
            tag_name = f"ralph-{i}"
            # Clear cache between calls to force API lookup
            pm._tag_cache = {}
            tag_gid = pm._get_or_create_tag(tag_name)
            assert tag_gid == f"gid-for-{tag_name}"

    def test_get_or_create_tag_raises_pm_error_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails during tag lookup, when _get_or_create_tag is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Mock: GET fails with 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "errors": [{"message": "Internal server error"}]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError):
            pm._get_or_create_tag("ralph-1")

    def test_tag_cache_is_empty_on_init(self, mock_env_asana):
        """Given new AsanaPM instance, when checking tag cache, then it is empty."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert pm._tag_cache == {}


# =============================================================================
# SDLC-0054: get_ticket_status Tests
# =============================================================================


class TestAsanaPMGetTicketStatus:
    """Tests for AsanaPM.get_ticket_status method.

    SDLC-0054: Implement status check via task completion state and blocked tag presence.
    """

    def test_get_ticket_status_returns_open_for_incomplete_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task is incomplete and has no blocked tag, when get_ticket_status is called, then OPEN is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns incomplete task without blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [{"gid": "tag-1", "name": "task"}],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.OPEN

    def test_get_ticket_status_returns_closed_for_completed_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task is completed, when get_ticket_status is called, then CLOSED is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns completed task
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": True,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.CLOSED

    def test_get_ticket_status_returns_blocked_when_blocked_tag_present(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has blocked tag, when get_ticket_status is called, then BLOCKED is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns task with blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [
                    {"gid": "tag-1", "name": "task"},
                    {"gid": "blocked-tag-gid", "name": "blocked"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.BLOCKED

    def test_get_ticket_status_blocked_takes_precedence_over_open(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task is incomplete but has blocked tag, when get_ticket_status is called, then BLOCKED is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns incomplete task WITH blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [{"gid": "blocked-tag-gid", "name": "blocked"}],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.BLOCKED

    def test_get_ticket_status_uses_case_insensitive_blocked_tag_match(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has Blocked tag (capitalized), when get_ticket_status is called, then BLOCKED is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns task with capitalized blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [{"gid": "blocked-tag-gid", "name": "Blocked"}],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.BLOCKED

    def test_get_ticket_status_calls_correct_api_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task id, when get_ticket_status is called, then correct API endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.get_ticket_status("12345")

        # Verify GET was called with correct endpoint
        get_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.get.call_args
        )
        url = get_call_args.args[0] if get_call_args.args else ""
        assert "/tasks/12345" in url

    def test_get_ticket_status_raises_pm_error_for_not_found(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task doesn't exist, when get_ticket_status is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "errors": [{"message": "task not found"}]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm.get_ticket_status("nonexistent-task")

        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)

    def test_get_ticket_status_returns_open_when_no_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has no tags at all, when get_ticket_status is called, then OPEN is returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns task with empty tags list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.OPEN

    def test_get_ticket_status_handles_custom_blocked_label(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given AsanaPM with custom blocked_label, when get_ticket_status is called, then custom label is checked."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET /tasks/{task_id} returns task with custom blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "[SDLC-0054] Test Task",
                "completed": False,
                "tags": [{"gid": "custom-tag-gid", "name": "needs-attention"}],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM(blocked_label="needs-attention")
        status = pm.get_ticket_status("12345")

        assert status == TicketStatus.BLOCKED


# =============================================================================
# SDLC-0055: claim_ticket and is_ticket_claimed Tests
# =============================================================================


class TestAsanaPMClaimTicket:
    """Tests for AsanaPM.claim_ticket method.

    SDLC-0055: Implement claiming via ralph-* tags with race condition handling.
    """

    def test_claim_ticket_adds_tag_to_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID and ralph-1 label, when claim_ticket is called, then tag is added to task."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns existing ralph-1 tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "ralph-1-gid", "name": "ralph-1"}]
        }

        # Mock: POST /tasks/{task_id}/addTag succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.claim_ticket("task-12345", "ralph-1")

        assert result is True

    def test_claim_ticket_calls_add_tag_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID and label, when claim_ticket is called, then addTag endpoint is called."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns existing tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "ralph-1-gid", "name": "ralph-1"}]
        }

        # Mock: POST succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm.claim_ticket("task-12345", "ralph-1")

        # Verify POST was called with addTag endpoint
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        add_tag_call = [c for c in post_calls if "addTag" in str(c)]
        assert len(add_tag_call) > 0

    def test_claim_ticket_sends_correct_tag_gid(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given label, when claim_ticket is called, then correct tag GID is sent in request."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns existing tag with specific GID
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "tag-gid-123", "name": "ralph-2"}]
        }

        # Mock: POST succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm.claim_ticket("task-12345", "ralph-2")

        # Verify the tag GID was sent
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        add_tag_call = [c for c in post_calls if "addTag" in str(c)]
        if add_tag_call:
            json_body = add_tag_call[0].kwargs.get("json", {})
            assert json_body.get("data", {}).get("tag") == "tag-gid-123"

    def test_claim_ticket_creates_tag_if_not_exists(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag doesn't exist, when claim_ticket is called, then tag is created first."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns empty tags list (tag doesn't exist)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        # Mock: POST for tag creation returns new tag
        mock_create_tag_response = MagicMock()
        mock_create_tag_response.status_code = 201
        mock_create_tag_response.json.return_value = {
            "data": {"gid": "new-tag-gid", "name": "ralph-3"}
        }

        # Mock: POST for addTag succeeds
        mock_add_tag_response = MagicMock()
        mock_add_tag_response.status_code = 200
        mock_add_tag_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        # First POST creates tag, second POST adds tag to task
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_create_tag_response,
            mock_add_tag_response,
        ]

        pm = AsanaPM()
        result = pm.claim_ticket("task-12345", "ralph-3")

        assert result is True
        # Verify two POST calls were made
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count == 2

    def test_claim_ticket_returns_false_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails when adding tag, when claim_ticket is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns existing tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "ralph-1-gid", "name": "ralph-1"}]
        }

        # Mock: POST fails with 500
        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.json.return_value = {"errors": [{"message": "Server error"}]}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.claim_ticket("task-12345", "ralph-1")

        assert result is False

    def test_claim_ticket_handles_ralph_0_through_5(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given ralph labels 0-5, when claim_ticket is called with each, then all succeed."""
        from core.asana_pm import AsanaPM

        for i in range(6):
            label = f"ralph-{i}"

            # Mock: GET returns tag
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {
                "data": [{"gid": f"gid-{label}", "name": label}]
            }

            # Mock: POST succeeds
            mock_post_response = MagicMock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = {"data": {}}

            mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
                mock_get_response
            )
            mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
                mock_post_response
            )

            pm = AsanaPM()
            result = pm.claim_ticket("task-12345", label)

            assert result is True, f"claim_ticket failed for {label}"


class TestAsanaPMIsTicketClaimed:
    """Tests for AsanaPM.is_ticket_claimed method.

    SDLC-0055: Check if task is claimed by any Ralph instance via ralph-* tags.
    """

    def test_is_ticket_claimed_returns_true_when_ralph_tag_present(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has ralph-1 tag, when is_ticket_claimed is called, then (True, 'ralph-1') is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task with ralph-1 tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [
                    {"gid": "task-tag-gid", "name": "task"},
                    {"gid": "ralph-1-gid", "name": "ralph-1"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("12345")

        assert is_claimed is True
        assert label == "ralph-1"

    def test_is_ticket_claimed_returns_false_when_no_ralph_tag(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has no ralph-* tags, when is_ticket_claimed is called, then (False, None) is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task without ralph tags
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [
                    {"gid": "task-tag-gid", "name": "task"},
                    {"gid": "blocked-tag-gid", "name": "blocked"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("12345")

        assert is_claimed is False
        assert label is None

    def test_is_ticket_claimed_returns_false_when_no_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has no tags at all, when is_ticket_claimed is called, then (False, None) is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task with empty tags list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("12345")

        assert is_claimed is False
        assert label is None

    def test_is_ticket_claimed_detects_any_ralph_tag_0_through_5(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has ralph-N tag (N=0-5), when is_ticket_claimed is called, then (True, 'ralph-N') is returned."""
        from core.asana_pm import AsanaPM

        for i in range(6):
            label = f"ralph-{i}"

            # Mock: GET returns task with specific ralph tag
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "gid": "12345",
                    "name": "Test Task",
                    "completed": False,
                    "tags": [{"gid": f"gid-{label}", "name": label}],
                }
            }
            mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
                mock_response
            )

            pm = AsanaPM()
            is_claimed, returned_label = pm.is_ticket_claimed("12345")

            assert is_claimed is True, f"is_ticket_claimed failed for {label}"
            assert returned_label == label

    def test_is_ticket_claimed_returns_first_ralph_tag_if_multiple(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has multiple ralph-* tags, when is_ticket_claimed is called, then first one is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns task with multiple ralph tags
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [
                    {"gid": "ralph-2-gid", "name": "ralph-2"},
                    {"gid": "ralph-1-gid", "name": "ralph-1"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("12345")

        assert is_claimed is True
        assert label == "ralph-2"  # First one in the list

    def test_is_ticket_claimed_calls_correct_api_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task id, when is_ticket_claimed is called, then correct API endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.is_ticket_claimed("12345")

        # Verify GET was called with correct endpoint
        get_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.get.call_args
        )
        url = get_call_args.args[0] if get_call_args.args else ""
        assert "/tasks/12345" in url

    def test_is_ticket_claimed_returns_false_on_api_error(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API returns error, when is_ticket_claimed is called, then (False, None) is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "Not found"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("nonexistent")

        assert is_claimed is False
        assert label is None

    def test_is_ticket_claimed_ignores_non_ralph_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task has 'ralph' tag (not 'ralph-N'), when is_ticket_claimed is called, then (False, None) is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns task with 'ralph' tag but not 'ralph-N' pattern
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "12345",
                "name": "Test Task",
                "completed": False,
                "tags": [
                    {"gid": "ralph-tag-gid", "name": "ralph"},
                    {"gid": "ralphy-tag-gid", "name": "ralphy-1"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        is_claimed, label = pm.is_ticket_claimed("12345")

        assert is_claimed is False
        assert label is None


# =============================================================================
# SDLC-0056: close_ticket with section move Tests
# =============================================================================


class TestAsanaPMCloseTicket:
    """Tests for AsanaPM.close_ticket method.

    SDLC-0056: Implement task completion and optional Done section move with graceful degradation.
    """

    def test_close_ticket_marks_task_as_complete(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when close_ticket is called, then task is marked as completed."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns sections
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "done-section-gid", "name": "Done"}]
        }

        # Mock: POST /sections/{section_id}/addTask succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        assert result is True

        # Verify PUT was called with completed=True
        put_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.put.call_args
        )
        json_body = put_call_args.kwargs.get("json", {})
        assert json_body.get("data", {}).get("completed") is True

    def test_close_ticket_moves_task_to_done_section(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project has Done section, when close_ticket is called, then task is moved to Done section."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns Done section
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [
                {"gid": "backlog-section-gid", "name": "Backlog"},
                {"gid": "done-section-gid", "name": "Done"},
            ]
        }

        # Mock: POST /sections/{section_id}/addTask succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        assert result is True

        # Verify POST was called with correct section GID
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        url = post_call_args.args[0] if post_call_args.args else ""
        assert "done-section-gid" in url or "addTask" in url

    def test_close_ticket_succeeds_without_done_section(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project has no Done section, when close_ticket is called, then task is marked complete (graceful degradation)."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns NO Done section
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [
                {"gid": "backlog-section-gid", "name": "Backlog"},
                {"gid": "in-progress-section-gid", "name": "In Progress"},
            ]
        }

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        # Should succeed even without Done section (graceful degradation)
        assert result is True

    def test_close_ticket_uses_case_insensitive_done_section_match(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given Done section has different case, when close_ticket is called, then section is found."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns "DONE" (uppercase)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "uppercase-done-gid", "name": "DONE"}]
        }

        # Mock: POST /sections/{section_id}/addTask succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        assert result is True

        # Verify POST was called to move to section
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        url = post_call_args.args[0] if post_call_args.args else ""
        assert "uppercase-done-gid" in url or "addTask" in url

    def test_close_ticket_calls_correct_task_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when close_ticket is called, then correct API endpoint is used."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns empty
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        pm = AsanaPM()
        pm.close_ticket("task-id-xyz")

        # Verify PUT was called with correct endpoint
        put_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.put.call_args
        )
        url = put_call_args.args[0] if put_call_args.args else ""
        assert "/tasks/task-id-xyz" in url

    def test_close_ticket_returns_false_on_completion_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task completion fails, when close_ticket is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} fails
        mock_put_response = MagicMock()
        mock_put_response.status_code = 500
        mock_put_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        assert result is False

    def test_close_ticket_succeeds_even_if_section_move_fails(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given section move fails, when close_ticket is called, then task is still marked complete (graceful degradation)."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns Done section
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "done-section-gid", "name": "Done"}]
        }

        # Mock: POST /sections/{section_id}/addTask fails
        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.close_ticket("12345")

        # Should still succeed - section move is optional
        assert result is True

    def test_close_ticket_queries_correct_project_for_sections(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project ID in env, when close_ticket is called, then correct project's sections are queried."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            "data": {"gid": "12345", "completed": True}
        }

        # Mock: GET /projects/{project_id}/sections returns empty
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_put_response
        )
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        pm = AsanaPM()
        pm.close_ticket("12345")

        # Verify GET was called with correct project ID (from env fixture: "project-12345")
        get_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.get.call_args
        )
        url = get_call_args.args[0] if get_call_args.args else ""
        assert "project-12345" in url
        assert "/sections" in url


class TestAsanaPMFindDoneSection:
    """Tests for AsanaPM._find_done_section helper method.

    SDLC-0056: Section discovery for Done state.
    """

    def test_find_done_section_returns_gid_when_found(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given Done section exists, when _find_done_section is called, then section GID is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /projects/{project_id}/sections returns Done section
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "backlog-gid", "name": "Backlog"},
                {"gid": "done-gid", "name": "Done"},
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        section_gid = pm._find_done_section()

        assert section_gid == "done-gid"

    def test_find_done_section_returns_none_when_not_found(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given no Done section exists, when _find_done_section is called, then None is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /projects/{project_id}/sections returns no Done section
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "backlog-gid", "name": "Backlog"},
                {"gid": "in-progress-gid", "name": "In Progress"},
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        section_gid = pm._find_done_section()

        assert section_gid is None

    def test_find_done_section_uses_case_insensitive_match(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given Done section with different case, when _find_done_section is called, then section is found."""
        from core.asana_pm import AsanaPM

        # Test various case variations
        test_cases = ["done", "Done", "DONE", "DoNe"]

        for section_name in test_cases:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"gid": "done-gid", "name": section_name}]
            }
            mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
                mock_response
            )

            pm = AsanaPM()
            section_gid = pm._find_done_section()

            assert section_gid == "done-gid", f"Failed for section name: {section_name}"


class TestAsanaPMMoveToSection:
    """Tests for AsanaPM._move_to_section helper method.

    SDLC-0056: Moving tasks to Done section.
    """

    def test_move_to_section_calls_correct_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task and section IDs, when _move_to_section is called, then correct API endpoint is used."""
        from core.asana_pm import AsanaPM

        # Mock: POST /sections/{section_id}/addTask succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm._move_to_section("task-123", "section-456")

        # Verify POST was called with correct endpoint
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        url = post_call_args.args[0] if post_call_args.args else ""
        assert "/sections/section-456/addTask" in url

    def test_move_to_section_sends_correct_task_id(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when _move_to_section is called, then task ID is sent in request body."""
        from core.asana_pm import AsanaPM

        # Mock: POST /sections/{section_id}/addTask succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm._move_to_section("task-123", "section-456")

        # Verify POST body contains task ID
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        json_body = post_call_args.kwargs.get("json", {})
        assert json_body.get("data", {}).get("task") == "task-123"

    def test_move_to_section_raises_pm_error_on_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when _move_to_section is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Mock: POST /sections/{section_id}/addTask fails
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError):
            pm._move_to_section("task-123", "section-456")
