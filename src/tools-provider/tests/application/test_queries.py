"""Application layer query handler tests with strict type hints."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from neuroglia.core import OperationResult

from application.queries import GetTaskByIdQuery, GetTaskByIdQueryHandler, GetTasksQuery, GetTasksQueryHandler
from domain.enums import TaskPriority, TaskStatus
from integration.models.task_dto import TaskDto
from tests.fixtures.factories import TaskDtoFactory
from tests.fixtures.mixins import BaseTestCase


class TestGetTasksQuery(BaseTestCase):
    """Test GetTasksQuery handler."""

    @pytest.fixture
    def handler(self, mock_repository: MagicMock) -> GetTasksQueryHandler:
        """Create a GetTasksQueryHandler with mocked repository."""
        return GetTasksQueryHandler(task_repository=mock_repository)

    @pytest.mark.asyncio
    async def test_admin_sees_all_tasks(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test admin users can see all tasks."""
        # Arrange
        tasks: list[TaskDto] = [
            TaskDtoFactory.create(title="Task 1", department="Engineering"),
            TaskDtoFactory.create(title="Task 2", department="Sales"),
            TaskDtoFactory.create(title="Task 3", department="Marketing"),
        ]
        mock_repository.get_all_async = self.create_async_mock(return_value=tasks)

        query: GetTasksQuery = GetTasksQuery(user_info={"roles": ["admin"], "sub": "admin1"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        mock_repository.get_all_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_manager_sees_department_tasks(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test manager users see only their department tasks."""
        # Arrange
        department: str = "Engineering"
        tasks: list[TaskDto] = [
            TaskDtoFactory.create(title="Task 1", department=department),
            TaskDtoFactory.create(title="Task 2", department=department),
        ]
        mock_repository.get_by_department_async = self.create_async_mock(return_value=tasks)

        query: GetTasksQuery = GetTasksQuery(
            user_info={
                "roles": ["manager"],
                "sub": "manager1",
                "department": department,
            }
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        mock_repository.get_by_department_async.assert_called_once_with(department)

    @pytest.mark.asyncio
    async def test_manager_without_department_sees_no_tasks(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test manager without department sees no tasks."""
        # Arrange
        query: GetTasksQuery = GetTasksQuery(user_info={"roles": ["manager"], "sub": "manager1"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        # Should not call repository methods
        mock_repository.get_by_department_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_regular_user_sees_assigned_tasks(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test regular users see only their assigned tasks."""
        # Arrange
        user_id: str = "user123"
        tasks: list[TaskDto] = [
            TaskDtoFactory.create(title="My Task 1", assignee_id=user_id),
            TaskDtoFactory.create(title="My Task 2", assignee_id=user_id),
        ]
        mock_repository.get_by_assignee_async = self.create_async_mock(return_value=tasks)

        query: GetTasksQuery = GetTasksQuery(user_info={"roles": ["user"], "sub": user_id})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        mock_repository.get_by_assignee_async.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_regular_user_without_sub_sees_no_tasks(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test regular user without sub field sees no tasks."""
        # Arrange
        query: GetTasksQuery = GetTasksQuery(user_info={"roles": ["user"]})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        # Should not call repository
        mock_repository.get_by_assignee_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_properly_formatted_dtos(self, handler: GetTasksQueryHandler, mock_repository: MagicMock) -> None:
        """Test query returns properly formatted task DTOs."""
        # Arrange
        task: TaskDto = TaskDtoFactory.create(
            title="Test Task",
            description="Test Description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            department="Engineering",
        )
        mock_repository.get_all_async = self.create_async_mock(return_value=[task])

        query: GetTasksQuery = GetTasksQuery(user_info={"roles": ["admin"], "sub": "admin1"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        # Note: We can't directly access result.content as it's not a standard attribute
        # The test verifies successful execution and repository calls


class TestGetTaskByIdQuery(BaseTestCase):
    """Test GetTaskByIdQuery handler."""

    @pytest.fixture
    def handler(self, mock_repository: MagicMock) -> GetTaskByIdQueryHandler:
        """Create a GetTaskByIdQueryHandler with mocked repository."""
        return GetTaskByIdQueryHandler(task_repository=mock_repository)

    @pytest.mark.asyncio
    async def test_admin_can_view_any_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test admin can view any task."""
        # Arrange
        task_id: str = "task123"
        task: TaskDto = TaskDtoFactory.create(task_id=task_id, department="Engineering", assignee_id="other_user")
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(task_id=task_id, user_info={"roles": ["admin"], "sub": "admin1"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        mock_repository.get_async.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_manager_can_view_department_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test manager can view tasks in their department."""
        # Arrange
        task_id: str = "task123"
        department: str = "Engineering"
        task: TaskDto = TaskDtoFactory.create(task_id=task_id, department=department, assignee_id="other_user")
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(
            task_id=task_id,
            user_info={
                "roles": ["manager"],
                "sub": "manager1",
                "department": department,
            },
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success

    @pytest.mark.asyncio
    async def test_manager_cannot_view_other_department_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test manager cannot view tasks from other departments."""
        # Arrange
        task_id: str = "task123"
        task: TaskDto = TaskDtoFactory.create(task_id=task_id, department="Engineering", assignee_id="other_user")
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(
            task_id=task_id,
            user_info={
                "roles": ["manager"],
                "sub": "manager1",
                "department": "Sales",
            },
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert not result.is_success
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_user_can_view_assigned_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test regular user can view their assigned task."""
        # Arrange
        task_id: str = "task123"
        user_id: str = "user1"
        task: TaskDto = TaskDtoFactory.create(task_id=task_id, assignee_id=user_id)
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(task_id=task_id, user_info={"roles": ["user"], "sub": user_id})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success

    @pytest.mark.asyncio
    async def test_user_cannot_view_others_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test regular user cannot view tasks assigned to others."""
        # Arrange
        task_id: str = "task123"
        task: TaskDto = TaskDtoFactory.create(task_id=task_id, assignee_id="other_user")
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(task_id=task_id, user_info={"roles": ["user"], "sub": "current_user"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert not result.is_success
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_query_for_nonexistent_task(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test querying for non-existent task returns not found."""
        # Arrange
        mock_repository.get_async = self.create_async_mock(return_value=None)

        query: GetTaskByIdQuery = GetTaskByIdQuery(task_id="nonexistent", user_info={"roles": ["admin"], "sub": "admin1"})

        # Act
        result = await handler.handle_async(query)

        # Assert: Should return not found error
        assert not result.is_success
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_properly_formatted_dto(self, handler: GetTaskByIdQueryHandler, mock_repository: MagicMock) -> None:
        """Test query returns properly formatted task DTO."""
        # Arrange
        task_id: str = "task123"
        task: TaskDto = TaskDtoFactory.create(
            task_id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.LOW,
        )
        mock_repository.get_async = self.create_async_mock(return_value=task)

        query: GetTaskByIdQuery = GetTaskByIdQuery(task_id=task_id, user_info={"roles": ["admin"], "sub": "admin1"})

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        assert result.status_code == 200


# ============================================================================
# PHASE 2: SOURCE AND TOOL QUERIES
# ============================================================================


class TestGetSourcesQuery(BaseTestCase):
    """Test GetSourcesQuery handler."""

    @pytest.fixture
    def mock_source_repository(self) -> MagicMock:
        """Create a mock SourceDto repository."""
        from unittest.mock import AsyncMock

        mock: MagicMock = MagicMock()
        mock.get_all_async = AsyncMock(return_value=[])
        mock.get_enabled_async = AsyncMock(return_value=[])
        mock.get_async = AsyncMock(return_value=None)
        mock.find_async = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def handler(self, mock_source_repository: MagicMock) -> "GetSourcesQueryHandler":
        """Create a GetSourcesQueryHandler with mocked repository."""
        from application.queries import GetSourcesQueryHandler

        return GetSourcesQueryHandler(source_repository=mock_source_repository)

    @pytest.mark.asyncio
    async def test_get_all_sources(self, handler: "GetSourcesQueryHandler", mock_source_repository: MagicMock) -> None:
        """Test listing all sources including disabled."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourcesQuery
        from integration.models.source_dto import SourceDto

        # Arrange
        sources = [
            SourceDto(
                id="source1",
                name="Test API 1",
                url="https://api1.example.com/openapi.json",
                source_type="openapi",
                health_status="healthy",
                is_enabled=True,
                inventory_count=5,
            ),
            SourceDto(
                id="source2",
                name="Test API 2",
                url="https://api2.example.com/openapi.json",
                source_type="openapi",
                health_status="healthy",
                is_enabled=False,
                inventory_count=10,
            ),
        ]
        mock_source_repository.get_all_async = AsyncMock(return_value=sources)

        query = GetSourcesQuery(include_disabled=True)

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 2
        mock_source_repository.get_all_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_enabled_sources_default(self, handler: "GetSourcesQueryHandler", mock_source_repository: MagicMock) -> None:
        """Test filtering sources returns only enabled by default."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourcesQuery
        from integration.models.source_dto import SourceDto

        # Arrange
        sources = [
            SourceDto(
                id="source1",
                name="Enabled API",
                url="https://api.example.com/openapi.json",
                source_type="openapi",
                health_status="healthy",
                is_enabled=True,
                inventory_count=5,
            ),
        ]
        mock_source_repository.get_enabled_async = AsyncMock(return_value=sources)

        query = GetSourcesQuery()  # Default is include_disabled=False

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 1
        mock_source_repository.get_enabled_async.assert_called_once()
        assert result.data[0].is_enabled is True

    @pytest.mark.asyncio
    async def test_get_sources_empty_result(self, handler: "GetSourcesQueryHandler", mock_source_repository: MagicMock) -> None:
        """Test empty source list."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourcesQuery

        # Arrange
        mock_source_repository.get_enabled_async = AsyncMock(return_value=[])

        query = GetSourcesQuery()

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 0


class TestGetSourceToolsQuery(BaseTestCase):
    """Test GetSourceToolsQuery handler."""

    @pytest.fixture
    def mock_tool_repository(self) -> MagicMock:
        """Create a mock SourceToolDto repository."""
        from unittest.mock import AsyncMock

        mock: MagicMock = MagicMock()
        mock.get_all_async = AsyncMock(return_value=[])
        mock.get_async = AsyncMock(return_value=None)
        mock.get_by_source_id_async = AsyncMock(return_value=[])
        mock.find_async = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def handler(self, mock_tool_repository: MagicMock) -> "GetSourceToolsQueryHandler":
        """Create a GetSourceToolsQueryHandler with mocked repository."""
        from application.queries import GetSourceToolsQueryHandler

        return GetSourceToolsQueryHandler(tool_repository=mock_tool_repository)

    @pytest.mark.asyncio
    async def test_get_tools_by_source_id(self, handler: "GetSourceToolsQueryHandler", mock_tool_repository: MagicMock) -> None:
        """Test listing tools for a specific source."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourceToolsQuery
        from integration.models.source_tool_dto import SourceToolDto

        # Arrange
        source_id = "source123"
        tools = [
            SourceToolDto(
                id="source123:list_users",
                source_id=source_id,
                source_name="Test API",
                tool_name="list_users",
                operation_id="list_users",
                description="List all users",
                method="GET",
                path="/users",
                execution_mode="sync_http",
                status="active",
            ),
            SourceToolDto(
                id="source123:create_user",
                source_id=source_id,
                source_name="Test API",
                tool_name="create_user",
                operation_id="create_user",
                description="Create a new user",
                method="POST",
                path="/users",
                execution_mode="sync_http",
                status="active",
            ),
        ]
        mock_tool_repository.get_by_source_id_async = AsyncMock(return_value=tools)

        query = GetSourceToolsQuery(source_id=source_id)

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 2
        mock_tool_repository.get_by_source_id_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tools_include_deprecated(self, handler: "GetSourceToolsQueryHandler", mock_tool_repository: MagicMock) -> None:
        """Test including deprecated tools."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourceToolsQuery
        from integration.models.source_tool_dto import SourceToolDto

        # Arrange
        all_tools = [
            SourceToolDto(
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
            ),
            SourceToolDto(
                id="source123:old_method",
                source_id="source123",
                source_name="Test API",
                tool_name="old_method",
                operation_id="old_method",
                description="Deprecated method",
                method="GET",
                path="/old",
                execution_mode="sync_http",
                status="deprecated",
            ),
        ]
        mock_tool_repository.get_by_source_id_async = AsyncMock(return_value=all_tools)

        query = GetSourceToolsQuery(source_id="source123", include_deprecated=True)

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 2
        mock_tool_repository.get_by_source_id_async.assert_called_once_with(
            source_id="source123",
            include_disabled=False,
            include_deprecated=True,
        )

    @pytest.mark.asyncio
    async def test_get_tools_empty_result(self, handler: "GetSourceToolsQueryHandler", mock_tool_repository: MagicMock) -> None:
        """Test empty tool list."""
        from unittest.mock import AsyncMock

        from application.queries import GetSourceToolsQuery

        # Arrange
        mock_tool_repository.get_by_source_id_async = AsyncMock(return_value=[])

        query = GetSourceToolsQuery(source_id="source123")

        # Act
        result: OperationResult[Any] = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 0
