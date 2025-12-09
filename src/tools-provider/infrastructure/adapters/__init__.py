"""Infrastructure adapters package.

Contains adapters for external service integrations:
- KeycloakTokenExchanger: RFC 8693 Token Exchange for upstream authentication
"""

from .keycloak_token_exchanger import KeycloakTokenExchanger, TokenExchangeError, TokenExchangeResult

__all__ = [
    "KeycloakTokenExchanger",
    "TokenExchangeResult",
    "TokenExchangeError",
]
