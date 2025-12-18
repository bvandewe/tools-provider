"""Tests for AuthConfig value object.

Tests cover:
- Standard auth types (bearer, oauth2, api_key, http_basic, none)
- External IDP configuration (oauth2_external factory)
- Serialization (to_dict, from_dict)
- Property accessors (uses_external_idp, get_external_idp_token_url)
"""

from domain.models import AuthConfig
from tests.fixtures.factories import AuthConfigFactory

# ============================================================================
# AUTH CONFIG FACTORY METHOD TESTS
# ============================================================================


class TestAuthConfigFactoryMethods:
    """Test AuthConfig static factory methods."""

    def test_bearer_creates_bearer_auth(self) -> None:
        """Test bearer() factory creates correct config."""
        config = AuthConfig.bearer(token="my-token")

        assert config.auth_type == "bearer"
        assert config.bearer_token == "my-token"

    def test_oauth2_creates_oauth2_auth(self) -> None:
        """Test oauth2() factory creates correct config."""
        config = AuthConfig.oauth2(
            token_url="https://auth.example.com/token",
            client_id="client-123",
            client_secret="secret-456",  # pragma: allowlist secret
            scopes=["read", "write"],
        )

        assert config.auth_type == "oauth2"
        assert config.oauth2_token_url == "https://auth.example.com/token"
        assert config.oauth2_client_id == "client-123"
        assert config.oauth2_client_secret == "secret-456"  # pragma: allowlist secret
        assert config.oauth2_scopes == ["read", "write"]
        assert config.uses_external_idp is False

    def test_api_key_creates_api_key_auth(self) -> None:
        """Test api_key() factory creates correct config."""
        config = AuthConfig.api_key(
            name="X-API-Key",
            value="key-value",
            location="header",
        )

        assert config.auth_type == "api_key"
        assert config.api_key_name == "X-API-Key"  # pragma: allowlist secret
        assert config.api_key_value == "key-value"  # pragma: allowlist secret
        assert config.api_key_in == "header"  # pragma: allowlist secret

    def test_http_basic_creates_basic_auth(self) -> None:
        """Test http_basic() factory creates correct config."""
        config = AuthConfig.http_basic(
            username="user",
            password="pass",  # pragma: allowlist secret
        )

        assert config.auth_type == "http_basic"
        assert config.basic_username == "user"
        assert config.basic_password == "pass"  # pragma: allowlist secret

    def test_none_creates_no_auth(self) -> None:
        """Test none() factory creates correct config."""
        config = AuthConfig.none()

        assert config.auth_type == "none"


# ============================================================================
# EXTERNAL IDP TESTS
# ============================================================================


class TestAuthConfigExternalIdp:
    """Test AuthConfig external IDP functionality."""

    def test_oauth2_external_creates_external_idp_config(self) -> None:
        """Test oauth2_external() factory creates config with external IDP fields."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external-kc.example.com/realms/myrealm",
            client_id="ext-client",
            client_secret="ext-secret",  # pragma: allowlist secret
            scopes=["openid", "profile"],
            realm="myrealm",
        )

        assert config.auth_type == "oauth2"
        assert config.external_idp_issuer_url == "https://external-kc.example.com/realms/myrealm"
        assert config.external_idp_client_id == "ext-client"
        assert config.external_idp_realm == "myrealm"
        assert config.oauth2_client_secret == "ext-secret"  # pragma: allowlist secret
        assert config.oauth2_scopes == ["openid", "profile"]

    def test_oauth2_external_without_optional_fields(self) -> None:
        """Test oauth2_external() with only required fields."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external-kc.example.com/realms/test",
            client_id="my-client",
        )

        assert config.auth_type == "oauth2"
        assert config.external_idp_issuer_url == "https://external-kc.example.com/realms/test"
        assert config.external_idp_client_id == "my-client"
        assert config.external_idp_realm is None
        assert config.oauth2_client_secret is None
        assert config.oauth2_scopes == []  # Defaults to empty list, not None

    def test_uses_external_idp_true_when_external_issuer_set(self) -> None:
        """Test uses_external_idp returns True when external IDP is configured."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external.example.com/realms/test",
            client_id="client",
        )

        assert config.uses_external_idp is True

    def test_uses_external_idp_false_for_standard_oauth2(self) -> None:
        """Test uses_external_idp returns False for standard OAuth2."""
        config = AuthConfig.oauth2(
            token_url="https://local.example.com/token",
            client_id="client",
            client_secret="secret",  # pragma: allowlist secret
        )

        assert config.uses_external_idp is False

    def test_uses_external_idp_false_for_bearer(self) -> None:
        """Test uses_external_idp returns False for bearer auth."""
        config = AuthConfig.bearer(token="token")

        assert config.uses_external_idp is False

    def test_get_external_idp_token_url_extracts_from_issuer(self) -> None:
        """Test get_external_idp_token_url() derives token URL from issuer."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external-kc.example.com/realms/myrealm",
            client_id="client",
        )

        token_url = config.get_external_idp_token_url()

        assert token_url == "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/token"

    def test_get_external_idp_token_url_handles_trailing_slash(self) -> None:
        """Test get_external_idp_token_url() handles trailing slash in issuer."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external-kc.example.com/realms/myrealm/",
            client_id="client",
        )

        token_url = config.get_external_idp_token_url()

        assert token_url == "https://external-kc.example.com/realms/myrealm/protocol/openid-connect/token"

    def test_get_external_idp_token_url_returns_none_for_standard_oauth2(self) -> None:
        """Test get_external_idp_token_url() returns None for non-external config."""
        config = AuthConfig.oauth2(
            token_url="https://local.example.com/token",
            client_id="client",
            client_secret="secret",  # pragma: allowlist secret
        )

        assert config.get_external_idp_token_url() is None


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================


class TestAuthConfigSerialization:
    """Test AuthConfig serialization to/from dict."""

    def test_to_dict_includes_external_idp_fields(self) -> None:
        """Test to_dict() includes external IDP fields when set."""
        config = AuthConfig.oauth2_external(
            issuer_url="https://external.example.com/realms/test",
            client_id="ext-client",
            realm="test",
        )

        data = config.to_dict()

        assert data["external_idp_issuer_url"] == "https://external.example.com/realms/test"
        assert data["external_idp_client_id"] == "ext-client"
        assert data["external_idp_realm"] == "test"

    def test_to_dict_omits_none_external_idp_fields(self) -> None:
        """Test to_dict() omits external IDP fields when None."""
        config = AuthConfig.oauth2(
            token_url="https://local.example.com/token",
            client_id="client",
            client_secret="secret",  # pragma: allowlist secret
        )

        data = config.to_dict()

        # Fields should be absent (not present with None value)
        assert "external_idp_issuer_url" not in data or data.get("external_idp_issuer_url") is None
        assert "external_idp_client_id" not in data or data.get("external_idp_client_id") is None
        assert "external_idp_realm" not in data or data.get("external_idp_realm") is None

    def test_from_dict_restores_external_idp_fields(self) -> None:
        """Test from_dict() restores external IDP configuration."""
        data = {
            "auth_type": "oauth2",
            "external_idp_issuer_url": "https://external.example.com/realms/test",
            "external_idp_client_id": "ext-client",
            "external_idp_realm": "test",
            "oauth2_client_secret": "secret",  # pragma: allowlist secret
        }

        config = AuthConfig.from_dict(data)

        assert config.external_idp_issuer_url == "https://external.example.com/realms/test"
        assert config.external_idp_client_id == "ext-client"
        assert config.external_idp_realm == "test"
        assert config.uses_external_idp is True

    def test_round_trip_serialization_external_idp(self) -> None:
        """Test AuthConfig survives round-trip through dict serialization."""
        original = AuthConfig.oauth2_external(
            issuer_url="https://external.example.com/realms/prod",
            client_id="prod-client",
            client_secret="prod-secret",  # pragma: allowlist secret
            scopes=["openid", "email"],
            realm="prod",
        )

        data = original.to_dict()
        restored = AuthConfig.from_dict(data)

        assert restored.external_idp_issuer_url == original.external_idp_issuer_url
        assert restored.external_idp_client_id == original.external_idp_client_id
        assert restored.external_idp_realm == original.external_idp_realm
        assert restored.oauth2_client_secret == original.oauth2_client_secret
        assert restored.oauth2_scopes == original.oauth2_scopes
        assert restored.uses_external_idp == original.uses_external_idp


# ============================================================================
# FACTORY TESTS
# ============================================================================


class TestAuthConfigFactories:
    """Test AuthConfigFactory test fixtures."""

    def test_create_oauth2_external_factory(self) -> None:
        """Test AuthConfigFactory.create_oauth2_external() creates valid config."""
        config = AuthConfigFactory.create_oauth2_external()

        assert config.auth_type == "oauth2"
        assert config.external_idp_issuer_url == "https://external-keycloak.example.com/realms/external"
        assert config.external_idp_client_id == "external-client-id"
        assert config.uses_external_idp is True

    def test_create_oauth2_external_factory_with_overrides(self) -> None:
        """Test AuthConfigFactory.create_oauth2_external() with custom values."""
        config = AuthConfigFactory.create_oauth2_external(
            issuer_url="https://custom.kc.io/realms/custom",
            client_id="custom-client",
            client_secret="custom-secret",  # pragma: allowlist secret
            scopes=["custom-scope"],
            realm="custom",
        )

        assert config.external_idp_issuer_url == "https://custom.kc.io/realms/custom"
        assert config.external_idp_client_id == "custom-client"
        assert config.oauth2_client_secret == "custom-secret"  # pragma: allowlist secret
        assert config.oauth2_scopes == ["custom-scope"]
        assert config.external_idp_realm == "custom"
