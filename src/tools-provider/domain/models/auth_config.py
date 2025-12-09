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
    - No authentication

    This is an immutable value object used within UpstreamSource aggregate.
    """

    auth_type: str  # "bearer", "oauth2", "api_key", "none"

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
