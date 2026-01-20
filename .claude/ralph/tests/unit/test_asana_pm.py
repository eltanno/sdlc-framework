"""Unit tests for the AsanaPM HTTP client, authentication, and tag management.

Tests cover:
- AsanaPM initialization with environment variables
- HTTP client authentication with Bearer token
- Error handling for missing credentials
- Error handling for API failures
- Base HTTP request functionality
- Tag management (_get_or_create_tag)
- close_ticket with section move
- add_blocked_label with comment

SDLC-0052: AsanaPM HTTP client and authentication
SDLC-0053: AsanaPM tag management
SDLC-0054: AsanaPM get_ticket_status method
SDLC-0055: AsanaPM claim_ticket and is_ticket_claimed methods
SDLC-0056: AsanaPM close_ticket with section move
SDLC-0057: AsanaPM add_blocked_label with comment
"""

from unittest.mock import MagicMock

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


# =============================================================================
# SDLC-0057: add_blocked_label with comment Tests
# =============================================================================


class TestAsanaPMAddBlockedLabel:
    """Tests for AsanaPM.add_blocked_label method.

    SDLC-0057: Implement blocked tag addition and reason comment posting via stories API.
    """

    def test_add_blocked_label_adds_blocked_tag_to_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID and reason, when add_blocked_label is called, then blocked tag is added."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST /tasks/{task_id}/addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST /tasks/{task_id}/stories succeeds (for comment)
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {
            "data": {"gid": "story-gid", "text": "Blocked: Test reason"}
        }

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        result = pm.add_blocked_label("task-12345", "Test reason")

        assert result is True

    def test_add_blocked_label_posts_comment_with_reason(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID and reason, when add_blocked_label is called, then comment with reason is posted."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST /tasks/{task_id}/addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST /tasks/{task_id}/stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {
            "data": {"gid": "story-gid", "text": "Blocked: Implementation failed"}
        }

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-12345", "Implementation failed")

        # Verify POST was called to stories endpoint
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        stories_call = [c for c in post_calls if "stories" in str(c)]
        assert len(stories_call) > 0

    def test_add_blocked_label_calls_stories_api_with_correct_task_id(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when add_blocked_label is called, then stories API is called with correct task ID."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-xyz-123", "Blocked reason")

        # Verify stories endpoint contains correct task ID
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        stories_call = [c for c in post_calls if "stories" in str(c)]
        if stories_call:
            url = stories_call[0].args[0] if stories_call[0].args else ""
            assert "/tasks/task-xyz-123/stories" in url

    def test_add_blocked_label_sends_reason_in_comment_text(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given reason, when add_blocked_label is called, then reason is included in comment text."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-12345", "Tests are failing with error X")

        # Verify comment text contains the reason
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        stories_call = [c for c in post_calls if "stories" in str(c)]
        if stories_call:
            json_body = stories_call[0].kwargs.get("json", {})
            comment_text = json_body.get("data", {}).get("text", "")
            assert "Tests are failing with error X" in comment_text

    def test_add_blocked_label_creates_blocked_tag_if_not_exists(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given blocked tag doesn't exist, when add_blocked_label is called, then tag is created."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns empty (no blocked tag)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        # Mock: POST to create tag
        mock_create_tag_response = MagicMock()
        mock_create_tag_response.status_code = 201
        mock_create_tag_response.json.return_value = {
            "data": {"gid": "new-blocked-tag-gid", "name": "blocked"}
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_create_tag_response,  # Create tag
            mock_post_add_tag_response,  # Add tag to task
            mock_post_story_response,  # Post comment
        ]

        pm = AsanaPM()
        result = pm.add_blocked_label("task-12345", "Reason")

        assert result is True
        # Verify 3 POST calls were made (create tag, add tag, post story)
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count == 3

    def test_add_blocked_label_returns_false_on_tag_add_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag addition fails, when add_blocked_label is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag fails
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 500
        mock_post_add_tag_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_add_tag_response
        )

        pm = AsanaPM()
        result = pm.add_blocked_label("task-12345", "Reason")

        assert result is False

    def test_add_blocked_label_returns_false_on_comment_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given comment posting fails, when add_blocked_label is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories fails
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 500
        mock_post_story_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        result = pm.add_blocked_label("task-12345", "Reason")

        assert result is False

    def test_add_blocked_label_uses_custom_blocked_label(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given custom blocked_label, when add_blocked_label is called, then custom label is used."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns custom blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "needs-attention-gid", "name": "needs-attention"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM(blocked_label="needs-attention")
        result = pm.add_blocked_label("task-12345", "Reason")

        assert result is True

    def test_add_blocked_label_calls_add_tag_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when add_blocked_label is called, then addTag endpoint is called."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-12345", "Reason")

        # Verify addTag endpoint was called
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        add_tag_call = [c for c in post_calls if "addTag" in str(c)]
        assert len(add_tag_call) > 0

    def test_add_blocked_label_sends_correct_tag_gid(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given blocked tag exists, when add_blocked_label is called, then correct tag GID is sent."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag with specific GID
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "specific-blocked-gid-999", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-12345", "Reason")

        # Verify correct tag GID was sent
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        add_tag_call = [c for c in post_calls if "addTag" in str(c)]
        if add_tag_call:
            json_body = add_tag_call[0].kwargs.get("json", {})
            assert json_body.get("data", {}).get("tag") == "specific-blocked-gid-999"

    def test_add_blocked_label_prefixes_comment_with_blocked(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given reason, when add_blocked_label is called, then comment is prefixed with 'Blocked:'."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns blocked tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "blocked-tag-gid", "name": "blocked"}]
        }

        # Mock: POST addTag succeeds
        mock_post_add_tag_response = MagicMock()
        mock_post_add_tag_response.status_code = 200
        mock_post_add_tag_response.json.return_value = {"data": {}}

        # Mock: POST stories succeeds
        mock_post_story_response = MagicMock()
        mock_post_story_response.status_code = 201
        mock_post_story_response.json.return_value = {"data": {"gid": "story-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_add_tag_response,
            mock_post_story_response,
        ]

        pm = AsanaPM()
        pm.add_blocked_label("task-12345", "Some reason here")

        # Verify comment starts with "Blocked:"
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        stories_call = [c for c in post_calls if "stories" in str(c)]
        if stories_call:
            json_body = stories_call[0].kwargs.get("json", {})
            comment_text = json_body.get("data", {}).get("text", "")
            assert comment_text.startswith("Blocked:")


# =============================================================================
# SDLC-0058: Remaining Methods Tests (get_open_tickets, remove_label, assign_to_self)
# =============================================================================


class TestAsanaPMGetOpenTickets:
    """Tests for AsanaPM.get_open_tickets method.

    SDLC-0058: Implement get_open_tickets to filter open tasks from a list of IDs.
    """

    def test_get_open_tickets_returns_open_tasks_from_list(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given list of task IDs with some open, when get_open_tickets is called, then only open tasks returned."""
        from core.asana_pm import AsanaPM
        from core.pm import TicketStatus

        # Mock: GET for first task (open)
        mock_task_1_response = MagicMock()
        mock_task_1_response.status_code = 200
        mock_task_1_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "[SDLC-0001] First Task",
                "completed": False,
                "tags": [],
            }
        }

        # Mock: GET for second task (completed/closed)
        mock_task_2_response = MagicMock()
        mock_task_2_response.status_code = 200
        mock_task_2_response.json.return_value = {
            "data": {
                "gid": "task-2",
                "name": "[SDLC-0002] Second Task",
                "completed": True,
                "tags": [],
            }
        }

        # Mock: GET for third task (open)
        mock_task_3_response = MagicMock()
        mock_task_3_response.status_code = 200
        mock_task_3_response.json.return_value = {
            "data": {
                "gid": "task-3",
                "name": "[SDLC-0003] Third Task",
                "completed": False,
                "tags": [],
            }
        }

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_1_response,
            mock_task_2_response,
            mock_task_3_response,
        ]

        pm = AsanaPM()
        result = pm.get_open_tickets(["task-1", "task-2", "task-3"])

        assert len(result) == 2
        assert result[0].id == "task-1"
        assert result[0].status == TicketStatus.OPEN
        assert result[1].id == "task-3"
        assert result[1].status == TicketStatus.OPEN

    def test_get_open_tickets_returns_empty_list_for_empty_input(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given empty list, when get_open_tickets is called, then empty list returned."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        result = pm.get_open_tickets([])

        assert result == []
        # No API calls should be made
        assert not mock_httpx_client.return_value.__enter__.return_value.get.called

    def test_get_open_tickets_excludes_blocked_tasks(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task with blocked tag, when get_open_tickets is called, then task is excluded from OPEN results."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns task with blocked tag
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "[SDLC-0001] Blocked Task",
                "completed": False,
                "tags": [{"gid": "blocked-tag-gid", "name": "blocked"}],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.get_open_tickets(["task-1"])

        # Should return empty since the only task is blocked
        assert len(result) == 0

    def test_get_open_tickets_returns_ticket_info_with_title(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given open task, when get_open_tickets is called, then TicketInfo includes title."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "[SDLC-0001] Important Feature",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.get_open_tickets(["task-1"])

        assert len(result) == 1
        assert result[0].title == "[SDLC-0001] Important Feature"

    def test_get_open_tickets_returns_ticket_info_with_labels(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given open task with tags, when get_open_tickets is called, then TicketInfo includes tag names as labels."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "[SDLC-0001] Task",
                "completed": False,
                "tags": [
                    {"gid": "tag-1", "name": "priority-high"},
                    {"gid": "tag-2", "name": "frontend"},
                ],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.get_open_tickets(["task-1"])

        assert len(result) == 1
        assert "priority-high" in result[0].labels
        assert "frontend" in result[0].labels

    def test_get_open_tickets_handles_not_found_task_gracefully(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID that doesn't exist, when get_open_tickets is called, then task is skipped."""
        from core.asana_pm import AsanaPM

        # First task exists and is open
        mock_task_1_response = MagicMock()
        mock_task_1_response.status_code = 200
        mock_task_1_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "[SDLC-0001] Existing Task",
                "completed": False,
                "tags": [],
            }
        }

        # Second task doesn't exist
        mock_task_2_response = MagicMock()
        mock_task_2_response.status_code = 404
        mock_task_2_response.json.return_value = {
            "errors": [{"message": "task not found"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_1_response,
            mock_task_2_response,
        ]

        pm = AsanaPM()
        result = pm.get_open_tickets(["task-1", "nonexistent-task"])

        # Should only return the existing task
        assert len(result) == 1
        assert result[0].id == "task-1"

    def test_get_open_tickets_calls_correct_api_endpoint_for_each_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given list of task IDs, when get_open_tickets is called, then correct endpoints are called."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task-1",
                "name": "Test",
                "completed": False,
                "tags": [],
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.get_open_tickets(["task-1", "task-2"])

        # Verify GET was called twice
        assert mock_httpx_client.return_value.__enter__.return_value.get.call_count == 2

        # Verify correct endpoints were called
        calls = mock_httpx_client.return_value.__enter__.return_value.get.call_args_list
        urls = [call.args[0] for call in calls]
        assert any("/tasks/task-1" in url for url in urls)
        assert any("/tasks/task-2" in url for url in urls)


class TestAsanaPMRemoveLabel:
    """Tests for AsanaPM.remove_label method.

    SDLC-0058: Implement remove_label to remove a tag from a task.
    """

    def test_remove_label_removes_tag_from_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task with tag, when remove_label is called, then tag is removed."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns the tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "ralph-1-gid", "name": "ralph-1"}]
        }

        # Mock: POST /tasks/{task_id}/removeTag succeeds
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
        result = pm.remove_label("task-12345", "ralph-1")

        assert result is True

    def test_remove_label_calls_remove_tag_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID and label, when remove_label is called, then removeTag endpoint is called."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns tag
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
        pm.remove_label("task-12345", "ralph-1")

        # Verify POST was called with removeTag endpoint
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        remove_tag_call = [c for c in post_calls if "removeTag" in str(c)]
        assert len(remove_tag_call) > 0

    def test_remove_label_sends_correct_tag_gid(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given label, when remove_label is called, then correct tag GID is sent in request."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns tag with specific GID
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "specific-tag-gid-123", "name": "ralph-2"}]
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
        pm.remove_label("task-12345", "ralph-2")

        # Verify correct tag GID was sent
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        remove_tag_call = [c for c in post_calls if "removeTag" in str(c)]
        if remove_tag_call:
            json_body = remove_tag_call[0].kwargs.get("json", {})
            assert json_body.get("data", {}).get("tag") == "specific-tag-gid-123"

    def test_remove_label_returns_false_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails when removing tag, when remove_label is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns tag
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
        result = pm.remove_label("task-12345", "ralph-1")

        assert result is False

    def test_remove_label_returns_false_when_tag_not_found(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag doesn't exist in workspace, when remove_label is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns empty tags list (tag doesn't exist)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        pm = AsanaPM()
        result = pm.remove_label("task-12345", "nonexistent-tag")

        # Should return False since tag doesn't exist (can't remove what doesn't exist)
        assert result is False


class TestAsanaPMAssignToSelf:
    """Tests for AsanaPM.assign_to_self method.

    SDLC-0058: Implement assign_to_self to assign a task to the current user.
    """

    def test_assign_to_self_assigns_task_to_me(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when assign_to_self is called, then task is assigned to 'me'."""
        from core.asana_pm import AsanaPM

        # Mock: PUT /tasks/{task_id} succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "Test Task",
                "assignee": {"gid": "user-gid", "name": "Current User"},
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.assign_to_self("task-12345")

        assert result is True

    def test_assign_to_self_calls_put_with_assignee_me(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when assign_to_self is called, then PUT is called with assignee='me'."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.assign_to_self("task-12345")

        # Verify PUT was called with correct endpoint and data
        put_call = mock_httpx_client.return_value.__enter__.return_value.put.call_args
        url = put_call.args[0] if put_call.args else ""
        assert "/tasks/task-12345" in url

        json_body = put_call.kwargs.get("json", {})
        assert json_body.get("data", {}).get("assignee") == "me"

    def test_assign_to_self_returns_false_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when assign_to_self is called, then False is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.assign_to_self("task-12345")

        assert result is False

    def test_assign_to_self_returns_false_on_not_found(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task doesn't exist, when assign_to_self is called, then False is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "task not found"}]}
        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.assign_to_self("nonexistent-task")

        assert result is False

    def test_assign_to_self_uses_correct_api_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when assign_to_self is called, then correct API endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.put.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.assign_to_self("task-99999")

        # Verify correct endpoint
        put_call = mock_httpx_client.return_value.__enter__.return_value.put.call_args
        url = put_call.args[0] if put_call.args else ""
        assert "https://app.asana.com/api/1.0/tasks/task-99999" in url


# =============================================================================
# SDLC-0060: Task Creation Methods for /ticket command
# =============================================================================


class TestAsanaPMCreateTask:
    """Tests for AsanaPM.create_task method.

    SDLC-0060: Implement task creation for /ticket slash command.
    """

    def test_create_task_creates_new_asana_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task details, when create_task is called, then new task is created."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks succeeds
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "gid": "new-task-gid",
                "name": "[SDLC-0001] Test Task",
                "notes": "Task description",
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.create_task(
            name="[SDLC-0001] Test Task",
            notes="Task description",
        )

        assert result == "new-task-gid"

    def test_create_task_sends_correct_name_and_notes(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task name and notes, when create_task is called, then correct data is sent."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"gid": "task-gid", "name": "Test", "notes": "Notes"}
        }
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.create_task(
            name="[SDLC-0067] Feature Implementation",
            notes="## Description\n\nImplement feature X",
        )

        # Verify POST was called with correct data
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        json_body = post_call.kwargs.get("json", {})
        data = json_body.get("data", {})
        assert data.get("name") == "[SDLC-0067] Feature Implementation"
        assert "Implement feature X" in data.get("notes", "")

    def test_create_task_uses_correct_project_id(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project ID from env, when create_task is called, then task is added to project."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"gid": "task-gid"}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.create_task(name="Test Task", notes="Description")

        # Verify project ID is included
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        json_body = post_call.kwargs.get("json", {})
        data = json_body.get("data", {})
        # Project ID should be in the projects list
        assert "project-12345" in str(data)

    def test_create_task_adds_task_tag(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given create_task is called, then 'task' tag is added to the created task."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns existing task tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "task-tag-gid", "name": "task"}]
        }

        # Mock: POST /tasks succeeds
        mock_post_task_response = MagicMock()
        mock_post_task_response.status_code = 201
        mock_post_task_response.json.return_value = {"data": {"gid": "new-task-gid"}}

        # Mock: POST /tasks/{task_id}/addTag succeeds
        mock_post_tag_response = MagicMock()
        mock_post_tag_response.status_code = 200
        mock_post_tag_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = [
            mock_post_task_response,
            mock_post_tag_response,
        ]

        pm = AsanaPM()
        pm.create_task(name="Test Task", notes="Description", add_task_tag=True)

        # Verify addTag was called
        post_calls = mock_httpx_client.return_value.__enter__.return_value.post.call_args_list
        add_tag_call = [c for c in post_calls if "addTag" in str(c)]
        assert len(add_tag_call) > 0

    def test_create_task_raises_pm_error_on_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when create_task is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError):
            pm.create_task(name="Test Task", notes="Description")

    def test_create_task_calls_tasks_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task details, when create_task is called, then /tasks endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"gid": "task-gid"}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.create_task(name="Test Task", notes="Description")

        # Verify correct endpoint
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        url = post_call.args[0] if post_call.args else ""
        assert "/tasks" in url


class TestAsanaPMCreateSubtask:
    """Tests for AsanaPM.create_subtask method.

    SDLC-0060: Implement subtask creation for acceptance criteria.
    """

    def test_create_subtask_creates_subtask_under_parent(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given parent task ID, when create_subtask is called, then subtask is created."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{parent_id}/subtasks succeeds
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "gid": "subtask-gid",
                "name": "Acceptance Criterion 1",
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.create_subtask(
            parent_task_id="parent-task-gid",
            name="Acceptance Criterion 1",
        )

        assert result == "subtask-gid"

    def test_create_subtask_uses_correct_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given parent task ID, when create_subtask is called, then subtasks endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"gid": "subtask-gid"}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.create_subtask(parent_task_id="parent-123", name="Subtask name")

        # Verify correct endpoint
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        url = post_call.args[0] if post_call.args else ""
        assert "/tasks/parent-123/subtasks" in url

    def test_create_subtask_sends_correct_name(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given subtask name, when create_subtask is called, then name is sent correctly."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"gid": "subtask-gid"}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.create_subtask(
            parent_task_id="parent-123",
            name="User can login with valid credentials",
        )

        # Verify name is sent
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        json_body = post_call.kwargs.get("json", {})
        data = json_body.get("data", {})
        assert data.get("name") == "User can login with valid credentials"

    def test_create_subtask_raises_pm_error_on_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when create_subtask is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "Parent not found"}]}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError):
            pm.create_subtask(parent_task_id="nonexistent", name="Subtask")

    def test_create_subtask_handles_multiple_subtasks(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given multiple subtasks, when create_subtask is called multiple times, then all are created."""
        from core.asana_pm import AsanaPM

        # Create responses for multiple subtasks
        responses = []
        for i in range(3):
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"data": {"gid": f"subtask-{i}"}}
            responses.append(mock_response)

        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = responses

        pm = AsanaPM()
        subtask_ids = []
        for i in range(3):
            subtask_id = pm.create_subtask(
                parent_task_id="parent-123",
                name=f"Acceptance Criterion {i + 1}",
            )
            subtask_ids.append(subtask_id)

        assert subtask_ids == ["subtask-0", "subtask-1", "subtask-2"]


class TestAsanaPMAddDependencies:
    """Tests for AsanaPM.add_dependencies method.

    SDLC-0060: Implement dependency linking for /ticket command.
    """

    def test_add_dependencies_sets_task_dependencies(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task and dependency IDs, when add_dependencies is called, then dependencies are set."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{task_id}/addDependencies succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.add_dependencies(
            task_id="task-3",
            dependency_ids=["task-1", "task-2"],
        )

        assert result is True

    def test_add_dependencies_uses_correct_endpoint(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when add_dependencies is called, then addDependencies endpoint is used."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.add_dependencies(task_id="task-123", dependency_ids=["dep-1"])

        # Verify correct endpoint
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        url = post_call.args[0] if post_call.args else ""
        assert "/tasks/task-123/addDependencies" in url

    def test_add_dependencies_sends_correct_dependency_gids(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given dependency IDs, when add_dependencies is called, then IDs are sent in request."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        pm.add_dependencies(
            task_id="task-3",
            dependency_ids=["task-1-gid", "task-2-gid"],
        )

        # Verify dependency IDs are sent
        post_call = mock_httpx_client.return_value.__enter__.return_value.post.call_args
        json_body = post_call.kwargs.get("json", {})
        data = json_body.get("data", {})
        assert "task-1-gid" in str(data)
        assert "task-2-gid" in str(data)

    def test_add_dependencies_returns_true_on_empty_list(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given empty dependency list, when add_dependencies is called, then True is returned without API call."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        result = pm.add_dependencies(task_id="task-123", dependency_ids=[])

        assert result is True
        # No API call should be made
        assert not mock_httpx_client.return_value.__enter__.return_value.post.called

    def test_add_dependencies_returns_false_on_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when add_dependencies is called, then False is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_response
        )

        pm = AsanaPM()
        result = pm.add_dependencies(task_id="task-123", dependency_ids=["dep-1"])

        assert result is False


class TestAsanaPMEnsureRequiredTags:
    """Tests for AsanaPM.ensure_required_tags method.

    SDLC-0060: Create required tags (task, blocked, ralph-0 through ralph-5) if they don't exist.
    """

    def test_ensure_required_tags_creates_missing_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tags don't exist, when ensure_required_tags is called, then tags are created."""
        from core.asana_pm import AsanaPM

        # Mock: GET /workspaces/{workspace_id}/tags returns empty (no tags)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        # Mock: POST /workspaces/{workspace_id}/tags creates each tag
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"data": {"gid": "new-tag-gid", "name": "tag"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.ensure_required_tags()

        assert result is True
        # Should have created: task, blocked, ralph-0 through ralph-5 = 8 tags
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count >= 8

    def test_ensure_required_tags_skips_existing_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given some tags exist, when ensure_required_tags is called, then only missing tags are created."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns some existing tags
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [
                {"gid": "task-gid", "name": "task"},
                {"gid": "blocked-gid", "name": "blocked"},
            ]
        }

        # Mock: POST creates missing tags
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"data": {"gid": "new-tag-gid"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.ensure_required_tags()

        assert result is True
        # Should have created only ralph-0 through ralph-5 = 6 tags (task and blocked exist)
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count == 6

    def test_ensure_required_tags_creates_ralph_tags_0_through_5(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given ralph tags don't exist, when ensure_required_tags is called, then ralph-0 through ralph-5 are created."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns task and blocked tags (but no ralph tags)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [
                {"gid": "task-gid", "name": "task"},
                {"gid": "blocked-gid", "name": "blocked"},
            ]
        }

        # Track created tags
        created_tags = []

        def mock_post_side_effect(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 201
            json_body = kwargs.get("json", {})
            tag_name = json_body.get("data", {}).get("name", "")
            created_tags.append(tag_name)
            mock_response.json.return_value = {
                "data": {"gid": f"{tag_name}-gid", "name": tag_name}
            }
            return mock_response

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = (
            mock_post_side_effect
        )

        pm = AsanaPM()
        pm.ensure_required_tags()

        # Verify ralph-0 through ralph-5 were created
        for i in range(6):
            assert f"ralph-{i}" in created_tags, f"ralph-{i} was not created"

    def test_ensure_required_tags_returns_false_on_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tag creation fails, when ensure_required_tags is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET returns empty
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": []}

        # Mock: POST fails
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
        result = pm.ensure_required_tags()

        assert result is False


# =============================================================================
# SDLC-0062: add_pr_comment Tests
# =============================================================================


class TestAsanaPMAddPrComment:
    """Tests for AsanaPM add_pr_comment method.

    SDLC-0062: Update /pr slash command - Add Asana task comment with PR link
    """

    def test_add_pr_comment_posts_comment_with_pr_link(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given PR URL, when add_pr_comment is called, then comment is posted to task."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{task_id}/stories succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "data": {"gid": "comment-gid-123", "text": "PR: https://github.com/org/repo/pull/42"}
        }

        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.add_pr_comment("task-12345", "https://github.com/org/repo/pull/42")

        assert result is True

        # Verify POST was called to stories endpoint
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        url = post_call_args.args[0] if post_call_args.args else ""
        assert "/tasks/task-12345/stories" in url

    def test_add_pr_comment_formats_comment_text_correctly(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given PR URL, when add_pr_comment is called, then comment text includes PR link."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{task_id}/stories succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm.add_pr_comment("task-12345", "https://github.com/org/repo/pull/42")

        # Verify the comment text was sent
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        json_body = post_call_args.kwargs.get("json", {})
        comment_text = json_body.get("data", {}).get("text", "")
        assert "https://github.com/org/repo/pull/42" in comment_text

    def test_add_pr_comment_returns_false_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when add_pr_comment is called, then False is returned."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{task_id}/stories fails
        mock_post_response = MagicMock()
        mock_post_response.status_code = 500
        mock_post_response.json.return_value = {
            "errors": [{"message": "Server error"}]
        }

        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        result = pm.add_pr_comment("task-12345", "https://github.com/org/repo/pull/42")

        assert result is False

    def test_add_pr_comment_handles_network_error_gracefully(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given network error, when add_pr_comment is called, then False is returned (no exception)."""
        import httpx

        from core.asana_pm import AsanaPM

        # Mock: POST fails with network error
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = (
            httpx.ConnectError("Connection failed")
        )

        pm = AsanaPM()
        result = pm.add_pr_comment("task-12345", "https://github.com/org/repo/pull/42")

        assert result is False

    def test_add_pr_comment_includes_pr_prefix_in_message(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given PR URL, when add_pr_comment is called, then comment has descriptive prefix."""
        from core.asana_pm import AsanaPM

        # Mock: POST /tasks/{task_id}/stories succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"data": {}}

        mock_httpx_client.return_value.__enter__.return_value.post.return_value = (
            mock_post_response
        )

        pm = AsanaPM()
        pm.add_pr_comment("task-12345", "https://github.com/org/repo/pull/42")

        # Verify the comment text has descriptive prefix
        post_call_args = (
            mock_httpx_client.return_value.__enter__.return_value.post.call_args
        )
        json_body = post_call_args.kwargs.get("json", {})
        comment_text = json_body.get("data", {}).get("text", "")
        # Should have some prefix like "Pull Request:" or "PR:"
        assert "PR" in comment_text or "Pull Request" in comment_text

    def test_add_pr_comment_has_correct_method_signature(self, mock_env_asana):
        """Given AsanaPM class, when checking add_pr_comment, then it accepts task_id and pr_url."""
        from core.asana_pm import AsanaPM
        import inspect

        pm = AsanaPM()
        assert hasattr(pm, "add_pr_comment")
        sig = inspect.signature(pm.add_pr_comment)
        params = list(sig.parameters.keys())
        # Should have task_id and pr_url parameters
        assert len(params) >= 2


# =============================================================================
# SDLC-0063: get_task_details for /implement command Tests
# =============================================================================


class TestAsanaPMGetTaskDetails:
    """Tests for AsanaPM.get_task_details method.

    SDLC-0063: Update /implement slash command - Add Asana task detail fetch
    when pm.tool: asana. Include subtasks in context.
    """

    def test_get_task_details_returns_task_info(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given valid task ID, when get_task_details is called, then task info is returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task details
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "[SDLC-0001] Implement Feature",
                "notes": "Task description here",
                "completed": False,
            }
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_get_response
        )

        pm = AsanaPM()
        result = pm.get_task_details("task-12345")

        assert result is not None
        assert result["gid"] == "task-12345"
        assert result["name"] == "[SDLC-0001] Implement Feature"
        assert result["notes"] == "Task description here"

    def test_get_task_details_includes_subtasks(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task with subtasks, when get_task_details is called, then subtasks are included."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task details
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "[SDLC-0001] Implement Feature",
                "notes": "Task description",
                "completed": False,
            }
        }

        # Mock: GET /tasks/{task_id}/subtasks returns acceptance criteria
        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {
            "data": [
                {"gid": "sub-1", "name": "Given X, when Y, then Z", "completed": False},
                {"gid": "sub-2", "name": "Given A, when B, then C", "completed": True},
            ]
        }

        # Configure mock to return different responses for different calls
        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response,
            mock_subtasks_response,
        ]

        pm = AsanaPM()
        result = pm.get_task_details("task-12345")

        assert "subtasks" in result
        assert len(result["subtasks"]) == 2
        assert result["subtasks"][0]["name"] == "Given X, when Y, then Z"
        assert result["subtasks"][1]["completed"] is True

    def test_get_task_details_handles_no_subtasks(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task without subtasks, when get_task_details is called, then empty subtasks list."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task details
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "[SDLC-0001] Implement Feature",
                "notes": "Task description",
                "completed": False,
            }
        }

        # Mock: GET /tasks/{task_id}/subtasks returns empty list
        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response,
            mock_subtasks_response,
        ]

        pm = AsanaPM()
        result = pm.get_task_details("task-12345")

        assert "subtasks" in result
        assert result["subtasks"] == []

    def test_get_task_details_calls_correct_endpoints(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task ID, when get_task_details is called, then correct API endpoints are used."""
        from core.asana_pm import AsanaPM

        # Mock responses
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {"gid": "task-12345", "name": "Task", "notes": ""}
        }

        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response,
            mock_subtasks_response,
        ]

        pm = AsanaPM()
        pm.get_task_details("task-12345")

        # Verify both calls were made
        get_calls = mock_httpx_client.return_value.__enter__.return_value.get.call_args_list
        assert len(get_calls) == 2

        # First call: /tasks/{task_id}
        first_url = get_calls[0].args[0]
        assert "/tasks/task-12345" in first_url
        assert "subtasks" not in first_url

        # Second call: /tasks/{task_id}/subtasks
        second_url = get_calls[1].args[0]
        assert "/tasks/task-12345/subtasks" in second_url

    def test_get_task_details_raises_error_for_invalid_task(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given non-existent task ID, when get_task_details is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Mock: GET /tasks/{task_id} returns 404
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"errors": [{"message": "Not found"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = (
            mock_response
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm.get_task_details("nonexistent-task")

        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)

    def test_get_task_details_includes_tags(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task with tags, when get_task_details is called, then tags are included."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task with tags
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "[SDLC-0001] Implement Feature",
                "notes": "Description",
                "completed": False,
                "tags": [
                    {"gid": "tag-1", "name": "task"},
                    {"gid": "tag-2", "name": "ralph-1"},
                ],
            }
        }

        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response,
            mock_subtasks_response,
        ]

        pm = AsanaPM()
        result = pm.get_task_details("task-12345")

        assert "tags" in result
        assert len(result["tags"]) == 2
        assert result["tags"][0]["name"] == "task"

    def test_get_task_details_includes_dependencies(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given task with dependencies, when get_task_details is called, then dependencies are included."""
        from core.asana_pm import AsanaPM

        # Mock: GET /tasks/{task_id} returns task with dependencies
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {
                "gid": "task-12345",
                "name": "[SDLC-0002] Feature",
                "notes": "Description",
                "completed": False,
                "dependencies": [
                    {"gid": "dep-1", "name": "[SDLC-0001] First Task"},
                ],
            }
        }

        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {"data": []}

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response,
            mock_subtasks_response,
        ]

        pm = AsanaPM()
        result = pm.get_task_details("task-12345")

        assert "dependencies" in result
        assert len(result["dependencies"]) == 1
        assert result["dependencies"][0]["name"] == "[SDLC-0001] First Task"

    def test_get_task_details_method_exists(self, mock_env_asana):
        """Given AsanaPM class, when checking for get_task_details, then method exists."""
        from core.asana_pm import AsanaPM
        import inspect

        pm = AsanaPM()
        assert hasattr(pm, "get_task_details")
        sig = inspect.signature(pm.get_task_details)
        params = list(sig.parameters.keys())
        # Should have task_id parameter
        assert "task_id" in params


# =============================================================================
# SDLC-0064: get_ticket_counts Tests (for /execution-report)
# =============================================================================


class TestAsanaPMGetTicketCounts:
    """Tests for AsanaPM.get_ticket_counts method.

    SDLC-0064: Update /execution-report command - Add Asana task status query for ticket counts.
    """

    def test_get_ticket_counts_returns_correct_counts(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project with tasks in different states, when get_ticket_counts is called, then correct counts are returned."""
        from core.asana_pm import AsanaPM

        # Mock: GET /projects/{project_id}/tasks returns tasks in different states
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                # Open task
                {"gid": "1", "name": "[SDLC-0001] Open Task", "completed": False, "tags": []},
                # Closed task
                {"gid": "2", "name": "[SDLC-0002] Closed Task", "completed": True, "tags": []},
                # Blocked task
                {
                    "gid": "3",
                    "name": "[SDLC-0003] Blocked Task",
                    "completed": False,
                    "tags": [{"gid": "blocked-gid", "name": "blocked"}],
                },
                # Another open task
                {"gid": "4", "name": "[SDLC-0004] Another Open", "completed": False, "tags": []},
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        counts = pm.get_ticket_counts()

        assert counts["open"] == 2
        assert counts["closed"] == 1
        assert counts["blocked"] == 1
        assert counts["total"] == 4

    def test_get_ticket_counts_returns_blocked_tasks_details(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project with blocked tasks, when get_ticket_counts is called, then blocked task details are included."""
        from core.asana_pm import AsanaPM

        # Mock: GET /projects/{project_id}/tasks returns blocked tasks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "gid": "1",
                    "name": "[SDLC-0001] Blocked Feature",
                    "completed": False,
                    "tags": [{"gid": "blocked-gid", "name": "blocked"}],
                },
                {
                    "gid": "2",
                    "name": "[SDLC-0002] Also Blocked",
                    "completed": False,
                    "tags": [{"gid": "blocked-gid", "name": "Blocked"}],  # Capitalized
                },
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        counts = pm.get_ticket_counts()

        assert counts["blocked"] == 2
        assert len(counts["blocked_tasks"]) == 2
        assert counts["blocked_tasks"][0]["gid"] == "1"
        assert counts["blocked_tasks"][0]["name"] == "[SDLC-0001] Blocked Feature"
        assert counts["blocked_tasks"][1]["gid"] == "2"

    def test_get_ticket_counts_queries_correct_project(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project ID in env, when get_ticket_counts is called, then correct project is queried."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        pm.get_ticket_counts()

        # Verify GET was called with correct project ID
        get_call_args = mock_httpx_client.return_value.__enter__.return_value.get.call_args
        url = get_call_args.args[0] if get_call_args.args else ""
        assert "/projects/project-12345/tasks" in url

    def test_get_ticket_counts_handles_empty_project(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given project with no tasks, when get_ticket_counts is called, then zero counts are returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        counts = pm.get_ticket_counts()

        assert counts["open"] == 0
        assert counts["closed"] == 0
        assert counts["blocked"] == 0
        assert counts["total"] == 0
        assert counts["blocked_tasks"] == []

    def test_get_ticket_counts_uses_case_insensitive_blocked_tag_match(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given tasks with different cased blocked tags, when get_ticket_counts is called, then all are counted."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"gid": "1", "name": "Task 1", "completed": False, "tags": [{"name": "blocked"}]},
                {"gid": "2", "name": "Task 2", "completed": False, "tags": [{"name": "Blocked"}]},
                {"gid": "3", "name": "Task 3", "completed": False, "tags": [{"name": "BLOCKED"}]},
            ]
        }
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        counts = pm.get_ticket_counts()

        assert counts["blocked"] == 3

    def test_get_ticket_counts_raises_pm_error_on_api_failure(
        self, mock_env_asana, mock_httpx_client
    ):
        """Given API fails, when get_ticket_counts is called, then PMError is raised."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errors": [{"message": "Internal server error"}]}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMError):
            pm.get_ticket_counts()

    def test_get_ticket_counts_method_exists(self, mock_env_asana):
        """Given AsanaPM class, when checking for get_ticket_counts, then method exists."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        assert hasattr(pm, "get_ticket_counts")
        assert callable(getattr(pm, "get_ticket_counts", None))


# =============================================================================
# SDLC-0065: Additional Edge Case Tests for Coverage
# =============================================================================


class TestAsanaPMTimeoutHandling:
    """Tests for timeout exception handling in HTTP methods.

    SDLC-0065: Unit tests for AsanaPM - timeout edge cases
    """

    def test_get_raises_pm_error_on_timeout(self, mock_env_asana, mock_httpx_client):
        """Given timeout on GET request, when _get is called, then PMError is raised."""
        import httpx
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Make GET raise TimeoutException
        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = (
            httpx.TimeoutException("Request timed out")
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/12345")

        assert "timeout" in str(exc_info.value).lower()

    def test_post_raises_pm_error_on_timeout(self, mock_env_asana, mock_httpx_client):
        """Given timeout on POST request, when _post is called, then PMError is raised."""
        import httpx
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Make POST raise TimeoutException
        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = (
            httpx.TimeoutException("Request timed out")
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._post("/tasks/12345/addTag", {"tag": "tag-gid"})

        assert "timeout" in str(exc_info.value).lower()

    def test_put_raises_pm_error_on_timeout(self, mock_env_asana, mock_httpx_client):
        """Given timeout on PUT request, when _put is called, then PMError is raised."""
        import httpx
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Make PUT raise TimeoutException
        mock_httpx_client.return_value.__enter__.return_value.put.side_effect = (
            httpx.TimeoutException("Request timed out")
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._put("/tasks/12345", {"completed": True})

        assert "timeout" in str(exc_info.value).lower()

    def test_put_raises_pm_error_on_connect_error(self, mock_env_asana, mock_httpx_client):
        """Given connection error on PUT request, when _put is called, then PMError is raised."""
        import httpx
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Make PUT raise ConnectError
        mock_httpx_client.return_value.__enter__.return_value.put.side_effect = (
            httpx.ConnectError("Connection failed")
        )

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._put("/tasks/12345", {"completed": True})

        assert "connection" in str(exc_info.value).lower() or "network" in str(exc_info.value).lower()


class TestAsanaPMResponseParsingEdgeCases:
    """Tests for edge cases in response parsing.

    SDLC-0065: Unit tests for AsanaPM - response parsing edge cases
    """

    def test_handle_response_error_with_malformed_json(self, mock_env_asana, mock_httpx_client):
        """Given error response with invalid JSON, when handling error, then default error message is used."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        with pytest.raises(PMError) as exc_info:
            pm._get("/tasks/12345")

        # Should still raise error with default message
        assert "500" in str(exc_info.value)

    def test_get_or_create_tag_handles_non_list_response(self, mock_env_asana, mock_httpx_client):
        """Given tags API returns non-list data, when _get_or_create_tag is called, then tag is created."""
        from core.asana_pm import AsanaPM

        # First call: GET returns non-list (edge case)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"data": {"unexpected": "format"}}

        # Second call: POST to create tag
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"data": {"gid": "new-tag-gid", "name": "ralph-1"}}

        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_get_response
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_post_response

        pm = AsanaPM()
        tag_gid = pm._get_or_create_tag("ralph-1")

        # Should create tag since list was empty
        assert tag_gid == "new-tag-gid"

    def test_find_done_section_handles_non_list_response(self, mock_env_asana, mock_httpx_client):
        """Given sections API returns non-list data, when _find_done_section is called, then None is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"unexpected": "format"}}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        result = pm._find_done_section()

        assert result is None

    def test_find_tag_handles_non_list_response(self, mock_env_asana, mock_httpx_client):
        """Given tags API returns non-list data, when _find_tag is called, then None is returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"unexpected": "format"}}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        result = pm._find_tag("ralph-1")

        assert result is None

    def test_find_tag_returns_cached_value(self, mock_env_asana, mock_httpx_client):
        """Given tag is in cache, when _find_tag is called, then cached value is returned without API call."""
        from core.asana_pm import AsanaPM

        pm = AsanaPM()
        # Pre-populate cache
        pm._tag_cache["ralph-1"] = "cached-tag-gid"

        result = pm._find_tag("ralph-1")

        assert result == "cached-tag-gid"
        # Verify no API call was made
        mock_httpx_client.return_value.__enter__.return_value.get.assert_not_called()

    def test_get_task_details_handles_non_list_subtasks(self, mock_env_asana, mock_httpx_client):
        """Given subtasks API returns non-list data, when get_task_details is called, then empty subtasks list is returned."""
        from core.asana_pm import AsanaPM

        # Task details response
        mock_task_response = MagicMock()
        mock_task_response.status_code = 200
        mock_task_response.json.return_value = {
            "data": {"gid": "12345", "name": "Test Task", "notes": "Notes", "completed": False}
        }

        # Subtasks response (non-list edge case)
        mock_subtasks_response = MagicMock()
        mock_subtasks_response.status_code = 200
        mock_subtasks_response.json.return_value = {"data": {"unexpected": "format"}}

        mock_httpx_client.return_value.__enter__.return_value.get.side_effect = [
            mock_task_response, mock_subtasks_response
        ]

        pm = AsanaPM()
        result = pm.get_task_details("12345")

        assert result["gid"] == "12345"
        assert result["subtasks"] == []

    def test_get_ticket_counts_handles_non_list_response(self, mock_env_asana, mock_httpx_client):
        """Given project tasks API returns non-list data, when get_ticket_counts is called, then zero counts returned."""
        from core.asana_pm import AsanaPM

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"unexpected": "format"}}
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

        pm = AsanaPM()
        counts = pm.get_ticket_counts()

        assert counts["open"] == 0
        assert counts["closed"] == 0
        assert counts["blocked"] == 0
        assert counts["total"] == 0


class TestAsanaPMCreateTaskEdgeCases:
    """Tests for edge cases in task creation.

    SDLC-0065: Unit tests for AsanaPM - task creation edge cases
    """

    def test_create_task_succeeds_even_when_tag_add_fails(self, mock_env_asana, mock_httpx_client):
        """Given task creation succeeds but tag add fails, when create_task with add_task_tag=True, then task GID is still returned."""
        from core.asana_pm import AsanaPM
        from core.pm import PMError

        # Task creation succeeds
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"data": {"gid": "new-task-gid"}}

        # Tag lookup for adding tag - returns existing tag
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "data": [{"gid": "task-tag-gid", "name": "task"}]
        }

        # Tag add fails
        mock_add_tag_response = MagicMock()
        mock_add_tag_response.status_code = 500
        mock_add_tag_response.json.return_value = {"errors": [{"message": "Server error"}]}

        # Configure side effects for calls in order:
        # 1. POST to create task -> succeeds
        # 2. GET to lookup tag -> succeeds
        # 3. POST to add tag -> fails
        post_responses = [mock_post_response, mock_add_tag_response]
        call_count = [0]

        def post_side_effect(*args, **kwargs):
            result = post_responses[call_count[0]]
            call_count[0] += 1
            return result

        mock_httpx_client.return_value.__enter__.return_value.post.side_effect = post_side_effect
        mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_get_response

        pm = AsanaPM()
        # Should succeed and return task GID even though tag add failed
        task_gid = pm.create_task("Test Task", "Description", add_task_tag=True)

        assert task_gid == "new-task-gid"

    def test_create_task_without_tag_does_not_call_tag_endpoint(self, mock_env_asana, mock_httpx_client):
        """Given add_task_tag=False, when create_task is called, then tag endpoints are not called."""
        from core.asana_pm import AsanaPM

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"data": {"gid": "new-task-gid"}}
        mock_httpx_client.return_value.__enter__.return_value.post.return_value = mock_post_response

        pm = AsanaPM()
        task_gid = pm.create_task("Test Task", "Description", add_task_tag=False)

        assert task_gid == "new-task-gid"
        # Only one POST call (task creation), no tag calls
        assert mock_httpx_client.return_value.__enter__.return_value.post.call_count == 1
