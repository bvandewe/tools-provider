"""Infrastructure adapters package.

Contains adapters for external service integrations:
- KeycloakTokenExchanger: RFC 8693 Token Exchange for upstream authentication
- OAuth2ClientCredentialsService: Client credentials grant for service-to-service auth
- OIDCDiscoveryService: OIDC Discovery for external identity providers
- ExternalIdpTokenProvider: Token acquisition from external IDPs
"""

from .external_idp_token_provider import ExternalIdpError, ExternalIdpToken, ExternalIdpTokenProvider
from .keycloak_token_exchanger import KeycloakTokenExchanger, TokenExchangeError, TokenExchangeResult
from .oauth2_client import ClientCredentialsError, ClientCredentialsToken, OAuth2ClientCredentialsService
from .oidc_discovery import OIDCDiscoveryDocument, OIDCDiscoveryError, OIDCDiscoveryService

__all__ = [
    "KeycloakTokenExchanger",
    "TokenExchangeResult",
    "TokenExchangeError",
    "OAuth2ClientCredentialsService",
    "ClientCredentialsToken",
    "ClientCredentialsError",
    "OIDCDiscoveryService",
    "OIDCDiscoveryDocument",
    "OIDCDiscoveryError",
    "ExternalIdpTokenProvider",
    "ExternalIdpToken",
    "ExternalIdpError",
]
