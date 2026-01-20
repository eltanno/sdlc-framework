"""Unit tests for the AsanaPM HTTP client, authentication, and tag management.

Tests cover:
- AsanaPM initialization with environment variables
- HTTP client authentication with Bearer token
- Error handling for missing credentials
- Error handling for API failures
- Base HTTP request functionality
- Tag management (_get_or_create_tag)

SDLC-0052: AsanaPM HTTP client and authentication
SDLC-0053: AsanaPM tag management
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
