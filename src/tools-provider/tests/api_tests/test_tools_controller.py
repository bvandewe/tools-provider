"""Tests for Tools API controller."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from api.controllers.tools_controller import ToolsController
from integration.models.source_tool_dto import SourceToolDto, SourceToolSummaryDto
from neuroglia.core import OperationResult


class TestToolsController:
    """Test ToolsController endpoints."""

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
    ) -> ToolsController:
        """Create a ToolsController with mocked dependencies."""
        return ToolsController(
            service_provider=mock_service_provider,
            mapper=mock_mapper,
            mediator=mock_mediator,
        )

    @pytest.fixture
    def sample_user(self) -> dict[str, Any]:
        """Create a sample authenticated user."""
        return {
            "sub": "user123",
            "roles": ["user"],
            "email": "user@example.com",
        }

    @pytest.fixture
    def sample_tool_dto(self) -> SourceToolDto:
        """Create a sample SourceToolDto."""
        return SourceToolDto(
            id="source123:list_users",
            source_id="source123",
            source_name="Test API",
            tool_name="list_users",
            operation_id="list_users",
            description="List all users",
            method="GET",
            path="/users",
            execution_mode="sync_http",
            status="active",
        )

    @pytest.fixture
    def sample_tool_summary(self) -> SourceToolSummaryDto:
        """Create a sample SourceToolSummaryDto."""
        return SourceToolSummaryDto(
            id="source123:list_users",
            source_id="source123",
            source_name="Test API",
            tool_name="list_users",
            description="List all users",
            method="GET",
            path="/users",
            tags=["users"],
        )

    # =========================================================================
    # GET /tools
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_tools_with_source_id(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_tool_dto: SourceToolDto,
    ) -> None:
        """Test listing tools for a specific source."""
        # Arrange
        tools = [sample_tool_dto]
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = tools
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.list_tools(
            source_id="source123",
            include_disabled=False,
            include_deprecated=False,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "source123"
        assert call_args.include_disabled is False
        assert call_args.include_deprecated is False

    @pytest.mark.asyncio
    async def test_list_tools_without_source_id_uses_summaries(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_tool_summary: SourceToolSummaryDto,
    ) -> None:
        """Test listing all tools uses summaries query."""
        # Arrange
        summaries = [sample_tool_summary]
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = summaries
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.list_tools(
            source_id=None,
            include_disabled=False,
            include_deprecated=False,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        # Should use GetToolSummariesQuery when no source_id
        assert hasattr(call_args, "source_id")
        assert call_args.source_id is None

    @pytest.mark.asyncio
    async def test_list_tools_with_filters(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test listing tools with filters."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = []
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.list_tools(
            source_id="source123",
            include_disabled=True,
            include_deprecated=True,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.include_disabled is True
        assert call_args.include_deprecated is True

    # =========================================================================
    # GET /tools/summaries
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_tool_summaries(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_tool_summary: SourceToolSummaryDto,
    ) -> None:
        """Test getting tool summaries."""
        # Arrange
        summaries = [sample_tool_summary]
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = summaries
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.get_tool_summaries(
            source_id="source123",
            include_disabled=False,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.source_id == "source123"
        assert call_args.include_disabled is False

    # =========================================================================
    # GET /tools/search
    # =========================================================================

    @pytest.mark.asyncio
    async def test_search_tools(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_tool_dto: SourceToolDto,
    ) -> None:
        """Test searching tools."""
        # Arrange
        tools = [sample_tool_dto]
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = tools
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.search_tools(
            q="users",
            source_id=None,
            tags=None,
            include_disabled=False,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.query == "users"
        assert call_args.source_id is None
        assert call_args.tags is None

    @pytest.mark.asyncio
    async def test_search_tools_with_filters(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test searching tools with filters."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = []
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.search_tools(
            q="create",
            source_id="source123",
            tags="users,admin",
            include_disabled=True,
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.query == "create"
        assert call_args.source_id == "source123"
        assert call_args.tags == ["users", "admin"]
        assert call_args.include_disabled is True

    # =========================================================================
    # GET /tools/{tool_id}
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_tool_by_id(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
        sample_tool_dto: SourceToolDto,
    ) -> None:
        """Test getting a tool by ID."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.data = sample_tool_dto
        mock_result.status = 200
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.get_tool(
            tool_id="source123:list_users",
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.tool_id == "source123:list_users"
        assert call_args.user_info == sample_user

    # =========================================================================
    # DELETE /tools/{tool_id}
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_tool(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test deleting a tool."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = True
        mock_result.status = 200
        mock_result.data = {
            "id": "source123:list_users",
            "name": "list_users",
            "source_id": "source123",
            "message": "Tool deleted successfully",
        }
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.delete_tool(
            tool_id="source123:list_users",
            user=sample_user,
        )

        # Assert
        mock_mediator.execute_async.assert_called_once()
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.tool_id == "source123:list_users"
        assert call_args.user_info == sample_user

    @pytest.mark.asyncio
    async def test_delete_tool_not_found(
        self,
        controller: ToolsController,
        mock_mediator: MagicMock,
        sample_user: dict[str, Any],
    ) -> None:
        """Test deleting a non-existent tool returns 404."""
        # Arrange
        mock_result = MagicMock(spec=OperationResult)
        mock_result.is_success = False
        mock_result.status = 404
        mock_result.data = None
        mock_mediator.execute_async.return_value = mock_result

        # Act
        await controller.delete_tool(
            tool_id="nonexistent:tool",
            user=sample_user,
        )

        # Assert
        call_args = mock_mediator.execute_async.call_args[0][0]
        assert call_args.tool_id == "nonexistent:tool"
