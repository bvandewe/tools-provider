"""
Pizzeria Backend - FastAPI Application Factory

A minimal upstream service demonstrating RBAC with Keycloak integration.
Used for demo and testing of token exchange and role-based access patterns.
Now with MongoDB persistence for menu items and orders.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.dependencies import init_jwks_client
from app.database import close_db, connect_db, init_indexes
from app.routers import kitchen, menu, orders
from app.routers.menu import init_sample_menu

logger = logging.getLogger(__name__)


def get_swagger_ui_oauth2_config() -> dict[str, str | bool]:
    """Get OAuth2 configuration for Swagger UI.

    Includes business-specific scopes for menu, orders, and kitchen operations.
    These scopes can be auto-discovered by Tools Provider from the OpenAPI spec.
    """
    # Use dedicated pizzeria-public client (configured with PKCE in Keycloak)
    client_id = os.getenv("SWAGGER_OAUTH2_CLIENT_ID", "pizzeria-public")

    # Include all available scopes - Keycloak will filter based on client config
    all_scopes = " ".join(
        [
            # Standard OIDC scopes
            "openid",
            "profile",
            "email",
            # Menu scopes
            "menu:read",
            "menu:write",
            # Order scopes
            "orders:read",
            "orders:write",
            "orders:pay",
            "orders:cancel",
            # Kitchen scopes
            "kitchen:read",
            "kitchen:write",
        ]
    )

    return {
        "clientId": client_id,
        "appName": "Pizzeria Backend API",
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": all_scopes,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initializes JWKS client and MongoDB on startup."""
    logger.info("🍕 Pizzeria Backend starting up...")

    # Initialize JWKS client for JWT validation
    await init_jwks_client()
    logger.info("✅ JWKS client initialized")

    # Initialize MongoDB connection
    await connect_db()
    await init_indexes()
    logger.info("✅ MongoDB connection established")

    # Initialize sample menu data if empty
    await init_sample_menu()

    yield

    # Cleanup
    await close_db()
    logger.info("🍕 Pizzeria Backend shutting down...")


def create_app() -> FastAPI:
    """FastAPI application factory."""

    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get external URL for OpenAPI servers definition
    external_url = os.getenv("PIZZERIA_EXTERNAL_URL", "http://localhost:8051")

    app = FastAPI(
        title="Pizzeria Backend API",
        description=(
            "Sample upstream service demonstrating Role-Based Access Control (RBAC) "
            "with Keycloak integration. Simulates a pizzeria backend for demo and testing.\n\n"
            "**Authentication:** Click the 'Authorize' button and use the 'authorizationCode' flow "
            "to login via Keycloak. The public client is pre-configured with PKCE support.\n\n"
            "**Note:** Select 'External access' server from the dropdown above for browser testing."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        servers=[
            {"url": "http://pizzeria-backend:8080", "description": "Docker internal (for tools-provider)"},
            {"url": external_url, "description": "External access (from host) - USE THIS IN BROWSER"},
        ],
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_ui_init_oauth=get_swagger_ui_oauth2_config(),
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(menu.router, prefix="/api/menu", tags=["Menu"])
    app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
    app.include_router(kitchen.router, prefix="/api/kitchen", tags=["Kitchen"])

    @app.get("/", tags=["Health"])
    async def root():
        """Root endpoint - service info."""
        return {
            "service": "Pizzeria Backend",
            "version": "0.1.0",
            "description": "Sample upstream service demonstrating RBAC with Keycloak",
            "docs": "/docs",
        }

    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "pizzeria-backend"}

    logger.info("🍕 Pizzeria Backend application created")
    return app
