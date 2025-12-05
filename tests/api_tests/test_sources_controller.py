"""Tests for Sources API controller."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from neuroglia.core import OperationResult

from api.controllers.sources_controller import RefreshInventoryRequest, RegisterSourceRequest, SourcesController
from application.commands import RefreshInventoryResult
from integration.models.source_dto import SourceDto


class TestSourcesController:
    """Test SourcesController endpoints."""

    @pytest.fixture
    def mock_mediator(self) -> MagicMock:
        """Create a mock mediator."""
        mock = MagicMock()
        mock.execute_async = AsyncMock()
        return mock

    @pytest.fixture
    def mock_mapper(self) -> MagicMock:
        """Create a mock mapper."""
        return MagicMock()

    @pytest.fixture
    def mock_service_provider(self) -> MagicMock:
        """Create a mock service provider."""
        return MagicMock()

    @pytest.fixture
    def controller(
        self,
        mock_service_provider: MagicMock,
        mock_mapper: MagicMock,
        mock_mediator: MagicMock,
    ) -> SourcesController:
        """Create a SourcesController with mocked dependencies."""
        return SourcesController(
            service_provider=mock_service_provider,
            mapper=mock_mapper,
            mediator=mock_mediator,
        )

    @pytest.fixture
    def sample_user(self) -> dict[str, Any]:
        """Create a sample authenticated user."""
        return {
            "sub": "user123",
            "roles": ["admin", "manager"],
            "email": "admin@example.com",
        }

    @pytest.fixture
    def sample_source_dto(self) -> SourceDto:
        """Create a sample SourceDto."""
        return SourceDto(
            id="source123",
            name="Test API",
            url="https://api.example.com/openapi.json",
            source_type="openapi",
            health_status="healthy",
            is_enabled=True,
            inventory_count=10,
        )

    # =========================================================================
    # GET /sources
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_sources_returns_list(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_source_dto: SourceDto,
    ) -> None:
        """Test listing sources returns a list of SourceDto."""
        # Arrange
        sources = [sample_source_dto]
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = sources
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        result = await controller.get_sources(
            include_disabled=False,
            health_status=None,
            source_type=None,
            user=sample_user,
        )

        # Assert
        mock_mediator.execute_async.assert_called_once()
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.include_disabled is False
        assert call_args.user_info == sample_user

    @pytest.mark.asyncio
    async def test_get_sources_with_filters(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test listing sources with filters."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = []
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.get_sources(
            include_disabled=True,
            health_status="healthy",
            source_type="openapi",
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.include_disabled is True
        assert call_args.health_status == "healthy"
        assert call_args.source_type == "openapi"

    # =========================================================================
    # GET /sources/{source_id}
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_source_by_id(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_source_dto: SourceDto,
    ) -> None:
        """Test getting a source by ID."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = sample_source_dto
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.get_source(source_id="source123", user=sample_user)

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "source123"
        assert call_args.user_info == sample_user

    # =========================================================================
    # POST /sources
    # =========================================================================

    @pytest.mark.asyncio
    async def test_register_source_minimal(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_source_dto: SourceDto,
    ) -> None:
        """Test registering a source with minimal fields."""
        # Arrange
        request = RegisterSourceRequest(
            name="Test API",
            url="https://api.example.com/openapi.json",
        )
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = sample_source_dto
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.register_source(request=request, user=sample_user)

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.name == "Test API"
        assert call_args.url == "https://api.example.com/openapi.json"
        assert call_args.source_type == "openapi"
        assert call_args.user_info == sample_user

    @pytest.mark.asyncio
    async def test_register_source_with_bearer_auth(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test registering a source with bearer authentication."""
        # Arrange
        request = RegisterSourceRequest(
            name="Secure API",
            url="https://api.secure.com/openapi.json",
            auth_type="bearer",
            bearer_token="secret-token",
        )
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.status = 200
        mock_result.data = None
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.register_source(request=request, user=sample_user)

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.auth_type == "bearer"
        assert call_args.bearer_token == "secret-token"

    @pytest.mark.asyncio
    async def test_register_source_with_api_key_auth(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test registering a source with API key authentication."""
        # Arrange
        request = RegisterSourceRequest(
            name="API Key API",
            url="https://api.example.com/openapi.json",
            auth_type="api_key",
            api_key_name="X-API-Key",
            api_key_value="my-key",
            api_key_in="header",
        )
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.status = 200
        mock_result.data = None
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.register_source(request=request, user=sample_user)

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.auth_type == "api_key"
        assert call_args.api_key_name == "X-API-Key"
        assert call_args.api_key_value == "my-key"
        assert call_args.api_key_in == "header"

    # =========================================================================
    # POST /sources/{source_id}/refresh
    # =========================================================================

    @pytest.mark.asyncio
    async def test_refresh_inventory(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test refreshing source inventory."""
        # Arrange
        request = RefreshInventoryRequest(force=False)
        refresh_result = RefreshInventoryResult(
            source_id="source123",
            success=True,
            tools_discovered=5,
            tools_created=3,
            tools_updated=2,
            tools_deprecated=0,
        )
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = refresh_result
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.refresh_inventory(
            source_id="source123",
            request=request,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "source123"
        assert call_args.force is False
        assert call_args.user_info == sample_user

    @pytest.mark.asyncio
    async def test_refresh_inventory_force(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test force refreshing source inventory."""
        # Arrange
        request = RefreshInventoryRequest(force=True)
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.status = 200
        mock_result.data = None
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.refresh_inventory(
            source_id="source123",
            request=request,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.force is True

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_source(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test deleting a source."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.status = 200
        mock_result.data = {
            "id": "source123",
            "name": "Test API",
            "message": "Source deleted successfully",
        }
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.delete_source(
            source_id="source123",
            user=sample_user,
        )

        # Assert
        mock_mediator.execute_async.assert_called_once()
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "source123"
        assert call_args.user_info == sample_user

    @pytest.mark.asyncio
    async def test_delete_source_not_found(
        self,
        controller: SourcesController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test deleting a non-existent source returns 404."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = False
        mock_result.status = 404
        mock_result.data = None
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.delete_source(
            source_id="nonexistent",
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "nonexistent"
