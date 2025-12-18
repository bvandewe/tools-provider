"""Tests for ExternalIdpTokenProvider.

Tests cover:
- Client credentials flow with external IDP
- Token exchange flow with external IDP
- Error handling
- Token response parsing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.adapters.external_idp_token_provider import ExternalIdpError, ExternalIdpToken, ExternalIdpTokenProvider
from infrastructure.adapters.oidc_discovery import OIDCDiscoveryService

# ============================================================================
# EXTERNAL IDP TOKEN TESTS
# ============================================================================


class TestExternalIdpToken:
    """Test ExternalIdpToken dataclass."""

    def test_create_token(self) -> None:
        """Test creating token with all fields."""
        token = ExternalIdpToken(
            access_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="Bearer",
            expires_in=300,
            scope="openid profile email",
        )

        assert token.access_token == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "Bearer"
        assert token.expires_in == 300
        assert token.scope == "openid profile email"
        # expires_at should be auto-calculated
        assert token.expires_at is not None

    def test_create_token_minimal(self) -> None:
        """Test creating token with only required fields."""
        token = ExternalIdpToken(
            access_token="token-value",
        )

        assert token.access_token == "token-value"
        assert token.token_type == "Bearer"
        assert token.expires_at is not None

    def test_is_expired_returns_false_for_fresh_token(self) -> None:
        """Test is_expired() returns False for recently created token."""
        token = ExternalIdpToken(
            access_token="token",
            expires_in=300,
        )

        assert token.is_expired() is False

    def test_is_expired_returns_true_for_short_lived_token(self) -> None:
        """Test is_expired() returns True for token expiring soon."""
        token = ExternalIdpToken(
            access_token="token",
            expires_in=30,  # Expires in 30 seconds
        )

        # With default 60 second leeway, this should be considered expired
        assert token.is_expired(leeway_seconds=60) is True


# ============================================================================
# CLIENT CREDENTIALS FLOW TESTS
# ============================================================================


class TestExternalIdpTokenProviderClientCredentials:
    """Test ExternalIdpTokenProvider client_credentials flow."""

    @pytest.fixture
    def mock_discovery_service(self) -> OIDCDiscoveryService:
        """Create mocked discovery service."""
        service = MagicMock(spec=OIDCDiscoveryService)
        service.get_token_endpoint = AsyncMock(return_value="https://external-kc.example.com/realms/test/protocol/openid-connect/token")
        return service

    @pytest.fixture
    def provider(self, mock_discovery_service: OIDCDiscoveryService) -> ExternalIdpTokenProvider:
        """Create token provider with mocked discovery."""
        return ExternalIdpTokenProvider(discovery_service=mock_discovery_service)

    @pytest.fixture
    def mock_token_response(self) -> dict:
        """Sample token response from Keycloak."""
        return {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",  # pragma: allowlist secret
            "token_type": "Bearer",
            "expires_in": 300,
            "scope": "openid profile",
        }

    @pytest.mark.asyncio
    async def test_get_client_credentials_token_success(
        self,
        provider: ExternalIdpTokenProvider,
        mock_token_response: dict,
    ) -> None:
        """Test successful client_credentials token acquisition."""
        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            token = await provider.get_client_credentials_token(
                issuer_url="https://external-kc.example.com/realms/test",
                client_id="ext-client",
                client_secret="ext-secret",  # pragma: allowlist secret
            )

            assert token.access_token == mock_token_response["access_token"]
            assert token.token_type == "Bearer"
            assert token.expires_in == 300

    @pytest.mark.asyncio
    async def test_get_client_credentials_token_sends_correct_payload(
        self,
        provider: ExternalIdpTokenProvider,
        mock_token_response: dict,
    ) -> None:
        """Test client_credentials request sends correct form data."""
        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider.get_client_credentials_token(
                issuer_url="https://external-kc.example.com/realms/test",
                client_id="ext-client",
                client_secret="ext-secret",  # pragma: allowlist secret
            )

            # Verify POST was called with correct data
            call_args = mock_client.post.call_args
            assert call_args is not None

            # Verify correct form data was sent
            data = call_args.kwargs.get("data", {})
            assert data["grant_type"] == "client_credentials"
            assert data["client_id"] == "ext-client"
            assert data["client_secret"] == "ext-secret"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_get_client_credentials_token_with_scopes(
        self,
        provider: ExternalIdpTokenProvider,
        mock_token_response: dict,
    ) -> None:
        """Test client_credentials includes scopes in request."""
        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider.get_client_credentials_token(
                issuer_url="https://external-kc.example.com/realms/test",
                client_id="ext-client",
                client_secret="secret",  # pragma: allowlist secret
                scopes=["custom-scope-1", "custom-scope-2"],
            )

            call_args = mock_client.post.call_args
            data = call_args.kwargs.get("data", {})
            assert "custom-scope-1" in data["scope"]
            assert "custom-scope-2" in data["scope"]


# ============================================================================
# TOKEN EXCHANGE FLOW TESTS
# ============================================================================


class TestExternalIdpTokenProviderTokenExchange:
    """Test ExternalIdpTokenProvider token_exchange flow."""

    @pytest.fixture
    def mock_discovery_service(self) -> OIDCDiscoveryService:
        """Create mocked discovery service."""
        service = MagicMock(spec=OIDCDiscoveryService)
        service.get_token_endpoint = AsyncMock(return_value="https://external-kc.example.com/realms/test/protocol/openid-connect/token")
        return service

    @pytest.fixture
    def provider(self, mock_discovery_service: OIDCDiscoveryService) -> ExternalIdpTokenProvider:
        """Create token provider with mocked discovery."""
        return ExternalIdpTokenProvider(discovery_service=mock_discovery_service)

    @pytest.fixture
    def mock_exchange_response(self) -> dict:
        """Sample token exchange response."""
        return {
            "access_token": "exchanged-access-token-xyz",
            "token_type": "Bearer",
            "expires_in": 300,
            "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }

    @pytest.mark.asyncio
    async def test_exchange_token_success(
        self,
        provider: ExternalIdpTokenProvider,
        mock_exchange_response: dict,
    ) -> None:
        """Test successful token exchange."""
        subject_token = "original-user-token-from-local-kc"

        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_exchange_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            token = await provider.exchange_token(
                issuer_url="https://external-kc.example.com/realms/test",
                subject_token=subject_token,
                client_id="ext-client",
                client_secret="ext-secret",  # pragma: allowlist secret
            )

            assert token.access_token == "exchanged-access-token-xyz"
            assert token.token_type == "Bearer"

    @pytest.mark.asyncio
    async def test_exchange_token_sends_rfc8693_payload(
        self,
        provider: ExternalIdpTokenProvider,
        mock_exchange_response: dict,
    ) -> None:
        """Test token exchange sends RFC 8693 compliant payload."""
        subject_token = "original-user-token"

        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_exchange_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await provider.exchange_token(
                issuer_url="https://external-kc.example.com/realms/test",
                subject_token=subject_token,
                client_id="ext-client",
                client_secret="ext-secret",  # pragma: allowlist secret
                audience="target-api",
            )

            call_args = mock_client.post.call_args
            data = call_args.kwargs.get("data", {})

            # Verify RFC 8693 parameters
            assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
            assert data["subject_token"] == subject_token
            assert data["subject_token_type"] == "urn:ietf:params:oauth:token-type:access_token"
            assert data["audience"] == "target-api"
            assert data["client_id"] == "ext-client"
            assert data["client_secret"] == "ext-secret"  # pragma: allowlist secret


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestExternalIdpTokenProviderErrors:
    """Test ExternalIdpTokenProvider error handling."""

    @pytest.fixture
    def mock_discovery_service(self) -> OIDCDiscoveryService:
        """Create mocked discovery service."""
        service = MagicMock(spec=OIDCDiscoveryService)
        service.get_token_endpoint = AsyncMock(return_value="https://external-kc.example.com/realms/test/protocol/openid-connect/token")
        return service

    @pytest.fixture
    def provider(self, mock_discovery_service: OIDCDiscoveryService) -> ExternalIdpTokenProvider:
        """Create token provider with mocked discovery."""
        return ExternalIdpTokenProvider(discovery_service=mock_discovery_service)

    @pytest.mark.asyncio
    async def test_client_credentials_raises_on_auth_error(
        self,
        provider: ExternalIdpTokenProvider,
    ) -> None:
        """Test client_credentials raises ExternalIdpError on 401."""
        error_response = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials",
        }

        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = error_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ExternalIdpError) as exc_info:
                await provider.get_client_credentials_token(
                    issuer_url="https://external-kc.example.com/realms/test",
                    client_id="ext-client",
                    client_secret="wrong-secret",  # pragma: allowlist secret
                )

            assert exc_info.value.error_code == "invalid_client"
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_exchange_raises_on_invalid_token(
        self,
        provider: ExternalIdpTokenProvider,
    ) -> None:
        """Test token exchange raises ExternalIdpError when subject token is invalid."""
        error_response = {
            "error": "invalid_token",
            "error_description": "Subject token validation failed",
        }

        with patch("infrastructure.adapters.external_idp_token_provider.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = error_response
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ExternalIdpError) as exc_info:
                await provider.exchange_token(
                    issuer_url="https://external-kc.example.com/realms/test",
                    subject_token="invalid-or-untrusted-token",
                    client_id="ext-client",
                    client_secret="secret",  # pragma: allowlist secret
                )

            assert exc_info.value.error_code == "invalid_token"
