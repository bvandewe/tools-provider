"""File-based secrets store for source authentication credentials.

This module provides a secure way to manage authentication credentials
for upstream sources without storing them in the event stream or database.

Credentials are loaded from a YAML file at startup. In Kubernetes, this
file should be mounted from a Secret. The file is NOT stored in git.

Usage:
    # secrets/sources.yaml (gitignored)
    sources:
      source-id-1:
        auth_type: http_basic
        basic_username: my-user
        basic_password: my-password
      source-id-2:
        auth_type: api_key
        api_key_name: X-API-Key
        api_key_value: secret-key
        api_key_in: header
      source-id-3:
        # External IDP credentials (client_credentials or token_exchange with external Keycloak)
        auth_type: oauth2
        external_idp_issuer_url: https://external-kc.example.com/realms/partner
        external_idp_client_id: partner-api-client
        oauth2_client_secret: client-secret-from-external-idp
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from domain.models import AuthConfig

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)

# Default path relative to the app root
DEFAULT_SECRETS_PATH = "secrets/sources.yaml"  # pragma: allowlist secret


class SourceSecretsStore:
    """File-based secrets store for source authentication credentials.

    Loads credentials from a YAML file at startup and provides
    lookup by source_id. The file is expected to be:
    - Mounted from a Kubernetes Secret in production
    - Created locally (and gitignored) for development

    Thread-safe for reads after initialization.
    """

    def __init__(self, secrets_path: str | Path | None = None):
        """Initialize the secrets store.

        Args:
            secrets_path: Path to the secrets YAML file.
                         Defaults to secrets/sources.yaml relative to CWD.
                         Can also be set via SOURCE_SECRETS_PATH env var.
        """
        self._secrets: dict[str, dict[str, Any]] = {}
        self._path: Path | None = None

        # Resolve path: explicit > env var > default
        if secrets_path:
            self._path = Path(secrets_path)
        elif os.environ.get("SOURCE_SECRETS_PATH"):
            self._path = Path(os.environ["SOURCE_SECRETS_PATH"])
        else:
            self._path = Path(DEFAULT_SECRETS_PATH)

        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from YAML file."""
        if not self._path:
            logger.info("No secrets path configured, source credentials will not be available")
            return

        if not self._path.exists():
            logger.warning(f"Secrets file not found: {self._path}. Sources requiring credentials (HTTP Basic, API Key) will fail. Create {self._path} or set SOURCE_SECRETS_PATH env var.")
            return

        try:
            with open(self._path) as f:
                data = yaml.safe_load(f)

            if data and isinstance(data.get("sources"), dict):
                self._secrets = data["sources"]
                logger.info(f"Loaded credentials for {len(self._secrets)} source(s) from {self._path}")

                # Log source IDs (not credentials!) for debugging
                for source_id in self._secrets:
                    auth_type = self._secrets[source_id].get("auth_type", "unknown")
                    logger.debug(f"  - {source_id}: {auth_type}")
            else:
                logger.warning(f"Secrets file {self._path} has no 'sources' section or is empty")

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse secrets file {self._path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load secrets file {self._path}: {e}")

    def get_auth_config(self, source_id: str) -> AuthConfig | None:
        """Get authentication configuration for a source.

        Args:
            source_id: The source ID to look up

        Returns:
            AuthConfig if credentials exist for this source, None otherwise
        """
        config_dict = self._secrets.get(source_id)
        if not config_dict:
            return None

        try:
            return AuthConfig.from_dict(config_dict)
        except Exception as e:
            logger.error(f"Failed to parse auth config for source {source_id}: {e}")
            return None

    def has_credentials(self, source_id: str) -> bool:
        """Check if credentials exist for a source.

        Args:
            source_id: The source ID to check

        Returns:
            True if credentials are configured for this source
        """
        return source_id in self._secrets

    def get_external_idp_secret(self, source_id: str) -> str | None:
        """Get the client secret for an external IDP.

        Convenience method for retrieving just the client secret needed
        for external IDP authentication (client_credentials or token_exchange).

        Args:
            source_id: The source ID to look up

        Returns:
            The oauth2_client_secret if configured, None otherwise
        """
        config_dict = self._secrets.get(source_id)
        if not config_dict:
            return None
        return config_dict.get("oauth2_client_secret")

    def get_external_idp_credentials(self, source_id: str) -> tuple[str | None, str | None]:
        """Get client_id and client_secret for an external IDP.

        Returns both the client ID and secret for external IDP authentication.
        Useful when the source was registered with only the issuer URL and
        the full credentials are in the secrets file.

        Args:
            source_id: The source ID to look up

        Returns:
            Tuple of (client_id, client_secret), either may be None if not configured
        """
        config_dict = self._secrets.get(source_id)
        if not config_dict:
            return None, None
        return (
            config_dict.get("external_idp_client_id") or config_dict.get("oauth2_client_id"),
            config_dict.get("oauth2_client_secret"),
        )

    def reload(self) -> None:
        """Reload secrets from the file.

        Useful for development or if the file is updated at runtime.
        Note: In production with K8s secrets, a pod restart is typical.
        """
        self._secrets.clear()
        self._load_secrets()

    @property
    def loaded_sources(self) -> list[str]:
        """Get list of source IDs that have credentials loaded.

        Returns:
            List of source IDs with configured credentials
        """
        return list(self._secrets.keys())

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> None:
        """Configure the secrets store in the DI container.

        Args:
            builder: The web application builder
        """
        secrets_path = os.environ.get("SOURCE_SECRETS_PATH", DEFAULT_SECRETS_PATH)
        store = SourceSecretsStore(secrets_path)
        builder.services.add_singleton(SourceSecretsStore, singleton=store)
        logger.info(f"SourceSecretsStore configured (path: {secrets_path})")
