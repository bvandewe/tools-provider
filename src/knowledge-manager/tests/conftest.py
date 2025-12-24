"""Pytest configuration and fixtures for Knowledge Manager tests."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from neuroglia.mapping import Mapper

from application.settings import Settings
from domain.entities import KnowledgeNamespace
from domain.models import KnowledgeTerm


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        app_port=8060,
        database_name="knowledge_manager_test",
        keycloak_url="http://localhost:8041",
        keycloak_realm="tools-provider",
        keycloak_client_id="knowledge-manager",
        redis_url="redis://localhost:6379/15",  # Use DB 15 for tests
    )


@pytest.fixture
def mock_mongo_client() -> MagicMock:
    """Create mock MongoDB client."""
    return MagicMock(spec=AsyncIOMotorClient)


@pytest.fixture
def mock_database() -> MagicMock:
    """Create mock MongoDB database."""
    return MagicMock(spec=AsyncIOMotorDatabase)


@pytest.fixture
def mapper() -> Mapper:
    """Create mapper instance."""
    return Mapper()


@pytest.fixture
def sample_namespace() -> KnowledgeNamespace:
    """Create sample namespace for testing."""
    namespace = KnowledgeNamespace.create(
        namespace_id="test-namespace",
        name="Test Namespace",
        description="A test namespace",
        owner_id="user-123",
        tenant_id="tenant-abc",
        is_public=False,
    )
    return namespace


@pytest.fixture
def sample_term() -> KnowledgeTerm:
    """Create sample term for testing."""
    return KnowledgeTerm.create(
        term="API",
        definition="Application Programming Interface",
        aliases=["Application Programming Interface", "interface"],
        examples=["REST API", "GraphQL API"],
        context_hint="Use when discussing software interfaces",
    )


@pytest.fixture
def sample_user() -> dict:
    """Create sample user info for testing."""
    return {
        "sub": "user-123",
        "email": "test@example.com",
        "preferred_username": "testuser",
        "name": "Test User",
        "realm_access": {"roles": ["user", "knowledge-editor"]},
    }


@pytest.fixture
async def mock_repository() -> AsyncMock:
    """Create mock repository."""
    repo = AsyncMock()
    repo.get_async = AsyncMock(return_value=None)
    repo.add_async = AsyncMock()
    repo.update_async = AsyncMock()
    repo.remove_async = AsyncMock()
    repo.contains_async = AsyncMock(return_value=False)
    return repo


# Markers for test categories
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "command: Command handler tests")
    config.addinivalue_line("markers", "query: Query handler tests")
    config.addinivalue_line("markers", "domain: Domain layer tests")
    config.addinivalue_line("markers", "api: API layer tests")
