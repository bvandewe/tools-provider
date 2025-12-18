"""Tests for OIDCDiscoveryService.

Tests cover:
- Discovery document fetching and parsing
- Token endpoint extraction
- Caching behavior
- Error handling
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.adapters.oidc_discovery import OIDCDiscoveryDocument, OIDCDiscoveryError, OIDCDiscoveryService, _CacheEntry

# ============================================================================
# OIDC DISCOVERY DOCUMENT TESTS
# ============================================================================


class TestOIDCDiscoveryDocument:
    """Test OIDCDiscoveryDocument dataclass."""

    def test_create_discovery_document(self) -> None:
        """Test creating discovery document with all fields."""
        doc = OIDCDiscoveryDocument(
            issuer="https://keycloak.example.com/realms/test",
            token_endpoint="https://keycloak.example.com/realms/test/protocol/openid-connect/token",
            jwks_uri="https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
            authorization_endpoint="https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
            userinfo_endpoint="https://keycloak.example.com/realms/test/protocol/openid-connect/userinfo",
            scopes_supported=["openid", "profile", "email"],
            grant_types_supported=["authorization_code", "client_credentials", "urn:ietf:params:oauth:grant-type:token-exchange"],
        )

        assert doc.issuer == "https://keycloak.example.com/realms/test"
        assert doc.token_endpoint == "https://keycloak.example.com/realms/test/protocol/openid-connect/token"
        assert "client_credentials" in doc.grant_types_supported
        assert "urn:ietf:params:oauth:grant-type:token-exchange" in doc.grant_types_supported

    def test_create_discovery_document_minimal(self) -> None:
        """Test creating discovery document with only required fields."""
        doc = OIDCDiscoveryDocument(
            issuer="https://keycloak.example.com/realms/test",
            token_endpoint="https://keycloak.example.com/realms/test/protocol/openid-connect/token",
            jwks_uri="https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
        )

        assert doc.issuer == "https://keycloak.example.com/realms/test"
        assert doc.token_endpoint == "https://keycloak.example.com/realms/test/protocol/openid-connect/token"
        assert doc.jwks_uri == "https://keycloak.example.com/realms/test/protocol/openid-connect/certs"
        assert doc.authorization_endpoint is None
        assert doc.scopes_supported == []
        assert doc.grant_types_supported == []

    def test_from_dict_parses_discovery_response(self) -> None:
        """Test from_dict() creates document from raw response."""
        data = {
            "issuer": "https://keycloak.example.com/realms/test",
            "token_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/token",
            "jwks_uri": "https://keycloak.example.com/realms/test/protocol/openid-connect/certs",
            "authorization_endpoint": "https://keycloak.example.com/realms/test/protocol/openid-connect/auth",
            "scopes_supported": ["openid", "profile"],
            "grant_types_supported": ["client_credentials"],
        }

        doc = OIDCDiscoveryDocument.from_dict(data)

        assert doc.issuer == data["issuer"]
        assert doc.token_endpoint == data["token_endpoint"]
        assert doc.jwks_uri == data["jwks_uri"]
        assert doc.scopes_supported == ["openid", "profile"]

    def test_supports_token_exchange(self) -> None:
        """Test supports_token_exchange() method."""
        doc = OIDCDiscoveryDocument(
            issuer="https://test.com",
            token_endpoint="https://test.com/token",
            jwks_uri="https://test.com/certs",
            grant_types_supported=["client_credentials", "urn:ietf:params:oauth:grant-type:token-exchange"],
        )

        assert doc.supports_token_exchange() is True
        assert doc.supports_grant_type("client_credentials") is True
        assert doc.supports_grant_type("password") is False


# ============================================================================
# OIDC DISCOVERY SERVICE TESTS
# ============================================================================


class TestOIDCDiscoveryService:
    """Test OIDCDiscoveryService functionality."""

    @pytest.fixture
    def service(self) -> OIDCDiscoveryService:
        """Create a fresh discovery service for each test."""
        return OIDCDiscoveryService()

    @pytest.fixture
    def mock_discovery_response(self) -> dict:
        """Sample OIDC discovery response."""
        return {
            "issuer": "https://external-kc.example.com/realms/myrealm",
            "token_endpoint": "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/token",
            "authorization_endpoint": "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/auth",
            "userinfo_endpoint": "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/userinfo",
            "jwks_uri": "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/certs",
            "scopes_supported": ["openid", "profile", "email", "address", "phone"],
            "grant_types_supported": [
                "authorization_code",
                "implicit",
                "refresh_token",
                "password",
                "client_credentials",
                "urn:ietf:params:oauth:grant-type:token-exchange",
            ],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        }

    @pytest.mark.asyncio
    async def test_get_discovery_document_fetches_and_parses(self, service: OIDCDiscoveryService, mock_discovery_response: dict) -> None:
        """Test get_discovery_document() fetches and parses OIDC configuration."""
        issuer_url = "https://external-kc.example.com/realms/myrealm"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_discovery_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            doc = await service.get_discovery_document(issuer_url)

            assert doc.issuer == "https://external-kc.example.com/realms/myrealm"
            assert doc.token_endpoint == "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/token"
            mock_client.get.assert_called_once_with(f"{issuer_url}/.well-known/openid-configuration")

    @pytest.mark.asyncio
    async def test_get_discovery_document_handles_trailing_slash(self, service: OIDCDiscoveryService, mock_discovery_response: dict) -> None:
        """Test get_discovery_document() handles issuer URL with trailing slash."""
        issuer_url = "https://external-kc.example.com/realms/myrealm/"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_discovery_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            await service.get_discovery_document(issuer_url)

            # Should strip trailing slash before appending .well-known
            expected_url = "https://external-kc.example.com/realms/myrealm/.well-known/openid-configuration"
            mock_client.get.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_get_discovery_document_caches_result(self, service: OIDCDiscoveryService, mock_discovery_response: dict) -> None:
        """Test get_discovery_document() caches and reuses results."""
        issuer_url = "https://external-kc.example.com/realms/myrealm"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_discovery_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            # First call should fetch
            doc1 = await service.get_discovery_document(issuer_url)
            # Second call should use cache
            doc2 = await service.get_discovery_document(issuer_url)

            assert doc1.issuer == doc2.issuer
            # HTTP client should only be called once due to caching
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_token_endpoint_returns_endpoint(self, service: OIDCDiscoveryService, mock_discovery_response: dict) -> None:
        """Test get_token_endpoint() returns token endpoint from discovery."""
        issuer_url = "https://external-kc.example.com/realms/myrealm"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_discovery_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            token_endpoint = await service.get_token_endpoint(issuer_url)

            assert token_endpoint == "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/token"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestOIDCDiscoveryServiceErrors:
    """Test OIDCDiscoveryService error handling."""

    @pytest.fixture
    def service(self) -> OIDCDiscoveryService:
        """Create a fresh discovery service for each test."""
        return OIDCDiscoveryService()

    @pytest.mark.asyncio
    async def test_get_discovery_document_raises_on_http_error(self, service: OIDCDiscoveryService) -> None:
        """Test get_discovery_document() raises OIDCDiscoveryError on HTTP error."""
        issuer_url = "https://nonexistent.example.com/realms/test"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OIDCDiscoveryError) as exc_info:
                await service.get_discovery_document(issuer_url)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_discovery_document_raises_on_invalid_json(self, service: OIDCDiscoveryService) -> None:
        """Test get_discovery_document() raises OIDCDiscoveryError on invalid JSON response."""
        issuer_url = "https://external-kc.example.com/realms/test"

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OIDCDiscoveryError):
                await service.get_discovery_document(issuer_url)

    @pytest.mark.asyncio
    async def test_get_discovery_document_raises_on_missing_token_endpoint(self, service: OIDCDiscoveryService) -> None:
        """Test get_discovery_document() raises OIDCDiscoveryError when token_endpoint is missing."""
        issuer_url = "https://external-kc.example.com/realms/test"
        incomplete_response = {
            "issuer": "https://external-kc.example.com/realms/test",
            # token_endpoint is missing
            "jwks_uri": "https://external-kc.example.com/realms/test/certs",
        }

        with patch("infrastructure.adapters.oidc_discovery.httpx.AsyncClient") as mock_async_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = incomplete_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(OIDCDiscoveryError) as exc_info:
                await service.get_discovery_document(issuer_url)

            assert "token_endpoint" in str(exc_info.value).lower()


# ============================================================================
# CACHE MANAGEMENT TESTS
# ============================================================================


class TestOIDCDiscoveryServiceCacheManagement:
    """Test OIDCDiscoveryService cache management."""

    @pytest.fixture
    def service(self) -> OIDCDiscoveryService:
        """Create a fresh discovery service for each test."""
        return OIDCDiscoveryService()

    def test_clear_cache_empties_cache(self, service: OIDCDiscoveryService) -> None:
        """Test clear_cache() removes all cached entries."""
        doc = OIDCDiscoveryDocument(
            issuer="https://example.com",
            token_endpoint="https://example.com/token",
            jwks_uri="https://example.com/certs",
        )
        service._cache["https://example.com"] = _CacheEntry(
            document=doc,
            fetched_at=time.time(),
            ttl_seconds=3600,
        )

        assert len(service._cache) == 1

        service.clear_cache()

        assert len(service._cache) == 0

    def test_invalidate_removes_specific_entry(self, service: OIDCDiscoveryService) -> None:
        """Test clear_cache(issuer_url) removes specific cached entry."""
        doc1 = OIDCDiscoveryDocument(
            issuer="https://example1.com",
            token_endpoint="https://example1.com/token",
            jwks_uri="https://example1.com/certs",
        )
        doc2 = OIDCDiscoveryDocument(
            issuer="https://example2.com",
            token_endpoint="https://example2.com/token",
            jwks_uri="https://example2.com/certs",
        )
        service._cache["https://example1.com"] = _CacheEntry(
            document=doc1,
            fetched_at=time.time(),
            ttl_seconds=3600,
        )
        service._cache["https://example2.com"] = _CacheEntry(
            document=doc2,
            fetched_at=time.time(),
            ttl_seconds=3600,
        )

        service.clear_cache("https://example1.com")

        assert "https://example1.com" not in service._cache
        assert "https://example2.com" in service._cache
