"""Authentication and authorization module.

Provides:
- JWT validation against Keycloak JWKS
- Role-based access control (RBAC)
- Scope-based access control (OAuth2 scopes)
- Combined role + scope checkers for defense-in-depth
"""

from app.auth.dependencies import (
    # Scope definitions
    OAUTH2_SCOPES,
    AnyAuthenticated,
    ChefOnly,
    ChefOrManager,
    # Pre-configured role checkers
    CustomerOnly,
    KitchenReader,
    KitchenWriter,
    ManagerOnly,
    # Pre-configured combined role+scope checkers
    MenuReader,
    MenuWriter,
    OrderCanceller,
    OrderPayer,
    OrderReader,
    OrderWriter,
    RoleAndScopeChecker,
    # Core dependencies
    RoleChecker,
    ScopeChecker,
    UserInfo,
    get_current_user,
    require_roles,
    require_scopes,
)

__all__ = [
    # Core dependencies
    "get_current_user",
    "require_roles",
    "require_scopes",
    "RoleChecker",
    "ScopeChecker",
    "RoleAndScopeChecker",
    "UserInfo",
    # Scope definitions
    "OAUTH2_SCOPES",
    # Pre-configured role checkers
    "CustomerOnly",
    "ChefOnly",
    "ManagerOnly",
    "ChefOrManager",
    "AnyAuthenticated",
    # Pre-configured combined role+scope checkers
    "MenuReader",
    "MenuWriter",
    "OrderReader",
    "OrderWriter",
    "OrderPayer",
    "OrderCanceller",
    "KitchenReader",
    "KitchenWriter",
]
