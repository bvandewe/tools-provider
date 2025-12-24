"""OpenAPI configuration for Knowledge Manager API."""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.routing import Mount

from application.settings import Settings

log = logging.getLogger(__name__)


def configure_mounted_apps_openapi_prefix(app: FastAPI) -> None:
    """Annotate mounted sub-apps with their mount path for OpenAPI path rendering.

    This function iterates over all mounted sub-apps in the root application and
    sets the `openapi_path_prefix` attribute on each sub-app's state. This prefix
    is used by the OpenAPI schema generation to render full URLs in Swagger UI.

    Args:
        app: Root FastAPI application with mounted sub-apps
    """
    for route in app.routes:
        if isinstance(route, Mount) and hasattr(route, "app") and route.app is not None:
            mount_path = route.path or ""
            # Normalize to leading slash, but treat root mount as empty prefix
            if mount_path and not mount_path.startswith("/"):
                mount_path = f"/{mount_path}"
            normalized_prefix = mount_path.rstrip("/") if mount_path not in ("", "/") else ""
            log.debug(f"Mounted sub-app '{route}' at '{normalized_prefix}'")
            route.app.state.openapi_path_prefix = normalized_prefix  # type: ignore[attr-defined]


def _resolve_mount_prefix(app: FastAPI) -> str:
    """Return the normalized mount prefix ('' when mounted at root)."""
    prefix = getattr(app.state, "openapi_path_prefix", "")
    if not prefix:
        return ""
    normalized = prefix if prefix.startswith("/") else f"/{prefix}"
    normalized = normalized.rstrip("/")
    return normalized


def get_openapi_config(app: FastAPI, settings: Settings) -> dict[str, Any]:
    """Generate OpenAPI schema with custom configuration.

    Args:
        app: FastAPI application
        settings: Application settings

    Returns:
        OpenAPI schema dictionary
    """
    # Load description from markdown file
    description_file = Path(__file__).parent.parent / "description.md"
    if description_file.exists():
        description = description_file.read_text()
    else:
        description = "Knowledge Manager API"

    openapi_schema = get_openapi(
        title="Knowledge Manager API",
        version=settings.app_version,
        description=description,
        routes=app.routes,
        tags=[
            {
                "name": "Namespaces",
                "description": "Manage knowledge namespaces",
            },
            {
                "name": "Terms",
                "description": "Manage terms within namespaces",
            },
            {
                "name": "Health",
                "description": "Health check endpoints",
            },
            {
                "name": "Auth",
                "description": "Authentication endpoints",
            },
        ],
    )

    # Set server URL to the mount prefix (e.g., /api)
    prefix = _resolve_mount_prefix(app)
    if prefix:
        openapi_schema["servers"] = [{"url": prefix}]

    # Add security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token from Keycloak",
        },
        "OAuth2": {
            "type": "oauth2",
            "description": "OAuth2 authentication via Keycloak",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/auth",
                    "tokenUrl": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
                    "scopes": {
                        "openid": "OpenID Connect scope",
                        "profile": "User profile",
                        "email": "User email",
                    },
                }
            },
        },
    }

    # Apply security globally
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"OAuth2": ["openid", "profile", "email"]},
    ]

    return openapi_schema


def configure_swagger_ui(app: FastAPI, settings: Settings) -> None:
    """Configure Swagger UI with OAuth2 client credentials and PKCE.

    This sets up the Swagger UI initOAuth parameters to:
    - Pre-fill the client_id in the authorization dialog
    - Enable PKCE for secure authorization code flow

    Args:
        app: FastAPI application instance
        settings: Application settings with Keycloak configuration
    """
    # Configure OAuth init with PKCE enabled
    app.swagger_ui_init_oauth = {
        "clientId": settings.keycloak_client_id,
        "usePkceWithAuthorizationCodeGrant": True,
    }

    # Configure Swagger UI parameters
    existing_params = getattr(app, "swagger_ui_parameters", None)
    if not isinstance(existing_params, dict):
        existing_params = {}
    app.swagger_ui_parameters = {
        **existing_params,
        "persistAuthorization": True,
        "docExpansion": "none",
        "operationsSorter": "alpha",
        "tagsSorter": "alpha",
    }


def setup_openapi(app: FastAPI, settings: Settings) -> None:
    """Configure OpenAPI schema for the application.

    Args:
        app: FastAPI application
        settings: Application settings
    """

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = get_openapi_config(app, settings)
        return app.openapi_schema

    app.openapi = custom_openapi

    # Configure Swagger UI with PKCE
    configure_swagger_ui(app, settings)
