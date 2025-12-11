"""Infrastructure adapters package.

Contains adapters for external service integrations:
- KeycloakTokenExchanger: RFC 8693 Token Exchange for upstream authentication
- OAuth2ClientCredentialsService: Client credentials grant for service-to-service auth
"""

from .keycloak_token_exchanger import KeycloakTokenExchanger, TokenExchangeError, TokenExchangeResult
from .oauth2_client import ClientCredentialsError, ClientCredentialsToken, OAuth2ClientCredentialsService

__all__ = [
    "KeycloakTokenExchanger",
    "TokenExchangeResult",
    "TokenExchangeError",
    "OAuth2ClientCredentialsService",
    "ClientCredentialsToken",
    "ClientCredentialsError",
]
