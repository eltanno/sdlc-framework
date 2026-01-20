"""Unit tests for the AsanaPM HTTP client and authentication.

Tests cover:
- AsanaPM initialization with environment variables
- HTTP client authentication with Bearer token
- Error handling for missing credentials
- Error handling for API failures
- Base HTTP request functionality

SDLC-0052: AsanaPM HTTP client and authentication
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
