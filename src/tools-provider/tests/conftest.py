"""Pytest configuration and shared fixtures for all tests.

This module provides:
- Test configuration and markers
- Shared fixtures for core components (session stores, auth services)
- Database and service mocks
- Test data factories
"""

import asyncio
import os
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.config import Config
from api.services.auth import DualAuthService
from application.settings import app_settings
from infrastructure import InMemorySessionStore, SessionStore
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config: Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (may use external services)")
    config.addinivalue_line("markers", "slow: Slow tests (may take several seconds)")
    config.addinivalue_line("markers", "asyncio: Async tests")
    config.addinivalue_line("markers", "auth: Authentication/authorization tests")
    config.addinivalue_line("markers", "repository: Repository layer tests")
    config.addinivalue_line("markers", "command: Command handler tests")
    config.addinivalue_line("markers", "query: Query handler tests")


# ============================================================================
# EVENT LOOP FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# SESSION STORE FIXTURES
# ============================================================================


@pytest.fixture
def session_store() -> SessionStore:
    """Provide an in-memory session store for testing."""
    return InMemorySessionStore(session_timeout_hours=1)


@pytest.fixture
def session_timeout() -> int:
    """Configurable session timeout in hours."""
    return 1


# ============================================================================
# AUTH SERVICE FIXTURES
# ============================================================================


@pytest.fixture
def auth_service(session_store: SessionStore) -> DualAuthService:
    """Provide a DualAuthService instance for testing."""
    return DualAuthService(session_store)


# ============================================================================
# MONGODB FIXTURES
# ============================================================================


@pytest.fixture
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """Provide a MongoDB client for integration tests.

    Uses test database to avoid polluting production data.
    """
    connection_string: str = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:8022")
    client: AsyncIOMotorClient = AsyncIOMotorClient(connection_string)
    yield client
    client.close()


@pytest.fixture
async def mongo_db(
    mongo_client: AsyncIOMotorClient,
) -> AsyncGenerator[AgnosticDatabase, None]:
    """Provide a test database that is cleaned after each test."""
    test_db_name: str = "test_starter_app"
    db: AgnosticDatabase = mongo_client[test_db_name]
    yield db
    # Cleanup: drop all collections after test
    collection_names: list[str] = await db.list_collection_names()
    for collection_name in collection_names:
        await db[collection_name].drop()


# ============================================================================
# REPOSITORY FIXTURES
# ============================================================================


@pytest.fixture
def mock_repository() -> MagicMock:
    """Provide a mock repository for testing command/query handlers.

    Mocks repository methods for both:
    - Repository[Task, str] (write model): add_async, update_async, remove_async, get_async
    - TaskDtoRepository (read model): get_all_async, get_by_assignee_async, get_by_department_async
    """
    mock: MagicMock = MagicMock()
    # Base Repository methods (for Repository[Task, str] - write model)
    mock.get_async = AsyncMock(return_value=None)
    mock.add_async = AsyncMock()
    mock.update_async = AsyncMock()
    mock.remove_async = AsyncMock(return_value=True)
    mock.contains_async = AsyncMock(return_value=False)
    # TaskDtoRepository methods (read model)
    mock.get_all_async = AsyncMock(return_value=[])
    mock.get_by_assignee_async = AsyncMock(return_value=[])
    mock.get_by_department_async = AsyncMock(return_value=[])
    # Additional MotorRepository methods (if needed)
    mock.find_async = AsyncMock(return_value=[])
    return mock


# ============================================================================
# TEST SETTINGS FIXTURES
# ============================================================================


@pytest.fixture
def test_settings() -> Any:
    """Provide test-specific application settings."""
    return app_settings


@pytest.fixture
def jwt_secret() -> str:
    """Provide JWT secret for testing."""
    return app_settings.jwt_secret_key


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_environment() -> Generator[None, None, None]:
    """Reset environment variables after each test."""
    original_env: dict[str, str] = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
