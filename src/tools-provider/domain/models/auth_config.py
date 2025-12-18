"""AuthConfig value object.

Authentication configuration for upstream source connections.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthConfig:
    """Authentication configuration for upstream source connections.

    Supports multiple authentication methods:
    - Bearer token (static or from environment variable)
    - OAuth2 client credentials flow
    - API key (in header or query parameter)
    - HTTP Basic authentication (RFC 7617)
    - No authentication

    This is an immutable value object used within UpstreamSource aggregate.
    """

    auth_type: str  # "bearer", "oauth2", "api_key", "http_basic", "none"

    # Bearer token auth
    bearer_token: str | None = None
    bearer_token_env_var: str | None = None  # Read from environment

    # OAuth2 client credentials
    oauth2_token_url: str | None = None
    oauth2_client_id: str | None = None
    oauth2_client_secret: str | None = None
    oauth2_scopes: list[str] = field(default_factory=list)

    # API key auth
    api_key_name: str | None = None
    api_key_value: str | None = None
    api_key_in: str | None = None  # "header" or "query"

    # HTTP Basic auth (RFC 7617)
    basic_username: str | None = None
    basic_password: str | None = None

    # External IDP configuration (for auth_mode client_credentials or token_exchange with external Keycloak)
    # When set, tokens are obtained from the external IDP instead of the local Keycloak
    external_idp_issuer_url: str | None = None  # OIDC issuer URL (e.g., https://external-kc.example.com/realms/myrealm)
    external_idp_realm: str | None = None  # External Keycloak realm name (derived from issuer if not set)
    external_idp_client_id: str | None = None  # Client ID at external IDP (for secrets lookup and token requests)

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "auth_type": self.auth_type,
            "bearer_token": self.bearer_token,
            "bearer_token_env_var": self.bearer_token_env_var,
            "oauth2_token_url": self.oauth2_token_url,
            "oauth2_client_id": self.oauth2_client_id,
            "oauth2_client_secret": self.oauth2_client_secret,
            "oauth2_scopes": self.oauth2_scopes,
            "api_key_name": self.api_key_name,
            "api_key_value": self.api_key_value,
            "api_key_in": self.api_key_in,
            "basic_username": self.basic_username,
            "basic_password": self.basic_password,
            "external_idp_issuer_url": self.external_idp_issuer_url,
            "external_idp_realm": self.external_idp_realm,
            "external_idp_client_id": self.external_idp_client_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthConfig":
        """Deserialize from dictionary."""
        return cls(
            auth_type=data.get("auth_type", "none"),
            bearer_token=data.get("bearer_token"),
            bearer_token_env_var=data.get("bearer_token_env_var"),
            oauth2_token_url=data.get("oauth2_token_url"),
            oauth2_client_id=data.get("oauth2_client_id"),
            oauth2_client_secret=data.get("oauth2_client_secret"),
            oauth2_scopes=data.get("oauth2_scopes", []),
            api_key_name=data.get("api_key_name"),
            api_key_value=data.get("api_key_value"),
            api_key_in=data.get("api_key_in"),
            basic_username=data.get("basic_username"),
            basic_password=data.get("basic_password"),
            external_idp_issuer_url=data.get("external_idp_issuer_url"),
            external_idp_realm=data.get("external_idp_realm"),
            external_idp_client_id=data.get("external_idp_client_id"),
        )

    @classmethod
    def none(cls) -> "AuthConfig":
        """Factory method for no authentication."""
        return cls(auth_type="none")

    @classmethod
    def bearer(cls, token: str) -> "AuthConfig":
        """Factory method for bearer token authentication."""
        return cls(auth_type="bearer", bearer_token=token)

    @classmethod
    def bearer_from_env(cls, env_var: str) -> "AuthConfig":
        """Factory method for bearer token from environment variable."""
        return cls(auth_type="bearer", bearer_token_env_var=env_var)

    @classmethod
    def oauth2(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> "AuthConfig":
        """Factory method for OAuth2 client credentials authentication."""
        return cls(
            auth_type="oauth2",
            oauth2_token_url=token_url,
            oauth2_client_id=client_id,
            oauth2_client_secret=client_secret,
            oauth2_scopes=scopes or [],
        )

    @classmethod
    def api_key(cls, name: str, value: str, location: str = "header") -> "AuthConfig":
        """Factory method for API key authentication.

        Args:
            name: The name of the header or query parameter
            value: The API key value
            location: Where to send the key - "header" or "query"
        """
        if location not in ("header", "query"):
            raise ValueError("api_key location must be 'header' or 'query'")
        return cls(
            auth_type="api_key",
            api_key_name=name,
            api_key_value=value,
            api_key_in=location,
        )

    @classmethod
    def http_basic(cls, username: str, password: str) -> "AuthConfig":
        """Factory method for HTTP Basic authentication (RFC 7617).

        Args:
            username: The username for Basic authentication
            password: The password for Basic authentication
        """
        return cls(
            auth_type="http_basic",
            basic_username=username,
            basic_password=password,
        )

    @classmethod
    def oauth2_external(
        cls,
        issuer_url: str,
        client_id: str,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
        realm: str | None = None,
    ) -> "AuthConfig":
        """Factory method for OAuth2 with external Identity Provider.

        Used when the upstream service is authenticated against a different
        Keycloak instance or OAuth2 provider than the Tools Provider's local IDP.

        Args:
            issuer_url: OIDC issuer URL (e.g., https://external-kc.example.com/realms/myrealm)
            client_id: Client ID registered at the external IDP
            client_secret: Client secret (optional - can be loaded from secrets file)
            scopes: OAuth2 scopes to request
            realm: External Keycloak realm name (derived from issuer URL if not provided)
        """
        return cls(
            auth_type="oauth2",
            oauth2_client_id=client_id,
            oauth2_client_secret=client_secret,
            oauth2_scopes=scopes or [],
            external_idp_issuer_url=issuer_url,
            external_idp_realm=realm,
            external_idp_client_id=client_id,
        )

    @property
    def uses_external_idp(self) -> bool:
        """Check if this auth config uses an external Identity Provider."""
        return self.external_idp_issuer_url is not None

    def get_external_idp_token_url(self) -> str | None:
        """Derive the token endpoint URL from the external IDP issuer.

        For Keycloak, the token URL follows the pattern:
        {issuer}/protocol/openid-connect/token

        Returns:
            Token endpoint URL or None if no external IDP configured
        """
        if not self.external_idp_issuer_url:
            return None
        issuer = self.external_idp_issuer_url.rstrip("/")
        return f"{issuer}/protocol/openid-connect/token"
