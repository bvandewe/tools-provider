"""Application layer command handler tests with strict type hints."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from neuroglia.core import OperationResult
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator

from application.commands.create_task_command import CreateTaskCommand, CreateTaskCommandHandler
from application.commands.delete_task_command import DeleteTaskCommand, DeleteTaskCommandHandler
from application.commands.update_task_command import UpdateTaskCommand, UpdateTaskCommandHandler
from domain.entities import Task
from domain.enums import TaskPriority, TaskStatus
from tests.fixtures.factories import TaskFactory
from tests.fixtures.mixins import BaseTestCase


class TestCreateTaskCommand(BaseTestCase):
    """Test CreateTaskCommand handler."""

    @pytest.fixture
    def handler(self, mock_repository: MagicMock) -> CreateTaskCommandHandler:
        """Create a CreateTaskCommandHandler with mocked dependencies."""
        mediator: Mediator = MagicMock(spec=Mediator)
        mapper: Mapper = MagicMock(spec=Mapper)
        cloud_event_bus: CloudEventBus = MagicMock(spec=CloudEventBus)
        # CloudEventPublishingOptions is not a standalone type, it's part of the bus
        cloud_event_publishing_options: Any = MagicMock()

        return CreateTaskCommandHandler(
            mediator=mediator,
            mapper=mapper,
            cloud_event_bus=cloud_event_bus,
            cloud_event_publishing_options=cloud_event_publishing_options,
            task_repository=mock_repository,
        )

    @pytest.mark.asyncio
    async def test_create_task_with_minimal_fields(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test creating a task with only required fields."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(title="Test Task", description="Test Description")

        created_task: Task = TaskFactory.create(title="Test Task", description="Test Description")
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        mock_repository.add_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test creating a task with all fields provided."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(
            title="Complete Task",
            description="Full description",
            status="in_progress",
            priority="high",
            assignee_id="user123",
            department="Engineering",
            user_info={"sub": "creator123", "department": "Engineering"},
        )

        created_task: Task = TaskFactory.create(
            title="Complete Task",
            description="Full description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            assignee_id="user123",
            department="Engineering",
            created_by="creator123",
        )
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        mock_repository.add_async.assert_called_once()

        # Verify task was created with correct attributes
        call_args: Any = mock_repository.add_async.call_args
        saved_task: Task = call_args[0][0]
        assert saved_task.state.title == "Complete Task"
        assert saved_task.state.status == TaskStatus.IN_PROGRESS
        assert saved_task.state.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_status(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test creating a task with invalid status defaults to PENDING."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(
            title="Task",
            description="Description",
            status="invalid_status",
        )

        created_task: Task = TaskFactory.create(title="Task", description="Description", status=TaskStatus.PENDING)
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        # Verify that the task was created with PENDING status (default for invalid)
        call_args: Any = mock_repository.add_async.call_args
        saved_task: Task = call_args[0][0]
        assert saved_task.state.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_priority(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test creating a task with invalid priority defaults to MEDIUM."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(
            title="Task",
            description="Description",
            priority="invalid_priority",
        )

        created_task: Task = TaskFactory.create(title="Task", description="Description", priority=TaskPriority.MEDIUM)
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        call_args: Any = mock_repository.add_async.call_args
        saved_task: Task = call_args[0][0]
        assert saved_task.state.priority == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_task_department_from_user_info(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test department is extracted from user_info if not explicitly provided."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(
            title="Task",
            description="Description",
            user_info={"sub": "user1", "department": "Marketing"},
        )

        created_task: Task = TaskFactory.create(title="Task", description="Description", department="Marketing")
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        call_args: Any = mock_repository.add_async.call_args
        saved_task: Task = call_args[0][0]
        assert saved_task.state.department == "Marketing"

    @pytest.mark.asyncio
    async def test_create_task_explicit_department_overrides_user_info(self, handler: CreateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test explicit department parameter overrides user_info department."""
        # Arrange
        command: CreateTaskCommand = CreateTaskCommand(
            title="Task",
            description="Description",
            department="Sales",
            user_info={"sub": "user1", "department": "Marketing"},
        )

        created_task: Task = TaskFactory.create(title="Task", description="Description", department="Sales")
        mock_repository.add_async = self.create_async_mock(return_value=created_task)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        call_args: Any = mock_repository.add_async.call_args
        saved_task: Task = call_args[0][0]
        assert saved_task.state.department == "Sales"


class TestUpdateTaskCommand(BaseTestCase):
    """Test UpdateTaskCommand handler."""

    @pytest.fixture
    def handler(self, mock_repository: MagicMock) -> UpdateTaskCommandHandler:
        """Create an UpdateTaskCommandHandler with mocked repository."""
        return UpdateTaskCommandHandler(task_repository=mock_repository)

    @pytest.mark.asyncio
    async def test_update_task_title(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test updating task title."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, title="Old Title", assignee_id="user1")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            title="New Title",
            user_info={"user_id": "user1", "roles": ["user"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert existing_task.state.title == "New Title"
        mock_repository.update_async.assert_called_once_with(existing_task)

    @pytest.mark.asyncio
    async def test_update_task_status(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test updating task status."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, status=TaskStatus.PENDING, assignee_id="user1")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            status="completed",
            user_info={"user_id": "user1", "roles": ["user"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert existing_task.state.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test updating non-existent task returns not found."""
        # Arrange
        mock_repository.get_async = self.create_async_mock(return_value=None)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id="nonexistent",
            title="New Title",
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert - handler returns not_found result
        assert not result.is_success
        assert result.status_code == 404

        mock_repository.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_forbidden_for_non_admin(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test non-admin cannot update tasks assigned to others."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, assignee_id="other_user")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            title="New Title",
            user_info={"user_id": "current_user", "roles": ["user"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400
        mock_repository.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_allowed_for_admin(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test admin can update any task."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, assignee_id="other_user", title="Old Title")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            title="New Title",
            user_info={"user_id": "admin_user", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert existing_task.state.title == "New Title"

    @pytest.mark.asyncio
    async def test_update_task_multiple_fields(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test updating multiple task fields at once."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(
            task_id=task_id,
            title="Old Title",
            description="Old Description",
            status=TaskStatus.PENDING,
            priority=TaskPriority.LOW,
            assignee_id="user1",
        )
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            title="New Title",
            description="New Description",
            status="in_progress",
            priority="high",
            user_info={"user_id": "user1", "roles": ["user"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert existing_task.state.title == "New Title"
        assert existing_task.state.description == "New Description"
        assert existing_task.state.status == TaskStatus.IN_PROGRESS
        assert existing_task.state.priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_update_task_with_invalid_status(self, handler: UpdateTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test updating task with invalid status returns error."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, assignee_id="user1")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)

        command: UpdateTaskCommand = UpdateTaskCommand(
            task_id=task_id,
            status="invalid_status",
            user_info={"user_id": "user1", "roles": ["user"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400


class TestDeleteTaskCommand(BaseTestCase):
    """Test DeleteTaskCommand handler."""

    @pytest.fixture
    def handler(self, mock_repository: MagicMock) -> DeleteTaskCommandHandler:
        """Create a DeleteTaskCommandHandler with mocked repository."""
        return DeleteTaskCommandHandler(task_repository=mock_repository)

    @pytest.mark.asyncio
    async def test_delete_task_success(self, handler: DeleteTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test successfully deleting a task with HARD delete mode."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id, title="Task to Delete")
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)
        mock_repository.remove_async = self.create_async_mock(return_value=None)

        command: DeleteTaskCommand = DeleteTaskCommand(
            task_id=task_id,
            user_info={"sub": "user1", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        # First update_async is called to save the TaskDeletedDomainEvent
        mock_repository.update_async.assert_called_once_with(existing_task)
        # Then remove_async performs the hard delete
        mock_repository.remove_async.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, handler: DeleteTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test deleting non-existent task returns not found."""
        # Arrange
        mock_repository.get_async = self.create_async_mock(return_value=None)

        command: DeleteTaskCommand = DeleteTaskCommand(task_id="nonexistent")

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 404
        mock_repository.remove_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_task_failure(self, handler: DeleteTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test handling deletion failure at repository level."""
        # Arrange
        task_id: str = "task123"
        existing_task: Task = TaskFactory.create(task_id=task_id)
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)
        # Use AsyncMock directly to support side_effect
        from unittest.mock import AsyncMock

        mock_repository.remove_async = AsyncMock(side_effect=Exception("EventStore deletion failed"))

        command: DeleteTaskCommand = DeleteTaskCommand(task_id=task_id)

        # Act & Assert - Exception should propagate from repository
        with pytest.raises(Exception, match="EventStore deletion failed"):
            await handler.handle_async(command)

    @pytest.mark.asyncio
    async def test_delete_task_with_user_context(self, handler: DeleteTaskCommandHandler, mock_repository: MagicMock) -> None:
        """Test deleting task with user context for audit trail."""
        # Arrange
        task_id: str = "task123"
        user_id: str = "user123"
        existing_task: Task = TaskFactory.create(task_id=task_id)
        mock_repository.get_async = self.create_async_mock(return_value=existing_task)
        mock_repository.update_async = self.create_async_mock(return_value=existing_task)
        mock_repository.remove_async = self.create_async_mock(return_value=None)

        command: DeleteTaskCommand = DeleteTaskCommand(
            task_id=task_id,
            user_info={"sub": user_id, "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        # update_async saves the TaskDeletedDomainEvent (triggers read model sync)
        mock_repository.update_async.assert_called_once()
        # remove_async performs the HARD delete (removes event stream)
        mock_repository.remove_async.assert_called_once_with(task_id)


# ============================================================================
# PHASE 2: SOURCE AND TOOL COMMANDS
# ============================================================================


class TestRegisterSourceCommand(BaseTestCase):
    """Test RegisterSourceCommand handler."""

    @pytest.fixture
    def mock_source_repository(self) -> MagicMock:
        """Create a mock UpstreamSource repository."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.add_async = AsyncMock()
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=True)
        mock.contains_async = AsyncMock(return_value=False)
        return mock

    @pytest.fixture
    def handler(self, mock_source_repository: MagicMock) -> "RegisterSourceCommandHandler":
        """Create a RegisterSourceCommandHandler with mocked dependencies."""
        from application.commands.register_source_command import RegisterSourceCommandHandler

        mediator: Mediator = MagicMock(spec=Mediator)
        mapper: Mapper = MagicMock(spec=Mapper)
        cloud_event_bus: CloudEventBus = MagicMock(spec=CloudEventBus)
        cloud_event_publishing_options: Any = MagicMock()

        return RegisterSourceCommandHandler(
            mediator=mediator,
            mapper=mapper,
            cloud_event_bus=cloud_event_bus,
            cloud_event_publishing_options=cloud_event_publishing_options,
            source_repository=mock_source_repository,
        )

    @pytest.mark.asyncio
    async def test_register_source_minimal_fields(self, handler: "RegisterSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test registering a source with only required fields."""
        from application.commands.register_source_command import RegisterSourceCommand
        from domain.entities import UpstreamSource

        # Arrange
        command: RegisterSourceCommand = RegisterSourceCommand(
            name="Test API",
            url="https://api.example.com/openapi.json",
            validate_url=False,  # Skip URL validation in unit tests
        )

        # Mock add_async to capture and return the source
        async def capture_source(source: UpstreamSource) -> UpstreamSource:
            return source

        mock_source_repository.add_async = AsyncMock(side_effect=capture_source)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        mock_source_repository.add_async.assert_called_once()

        # Verify DTO response
        dto: Any = result.data
        assert dto.name == "Test API"
        assert dto.url == "https://api.example.com/openapi.json"

    @pytest.mark.asyncio
    async def test_register_source_with_bearer_auth(self, handler: "RegisterSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test registering a source with bearer token authentication."""
        from application.commands.register_source_command import RegisterSourceCommand
        from domain.entities import UpstreamSource

        # Arrange
        command: RegisterSourceCommand = RegisterSourceCommand(
            name="Secure API",
            url="https://api.secure.com/openapi.json",
            auth_type="bearer",
            bearer_token="secret-token-123",
            validate_url=False,
        )

        async def capture_source(source: UpstreamSource) -> UpstreamSource:
            return source

        mock_source_repository.add_async = AsyncMock(side_effect=capture_source)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success

        # Verify the captured source has auth_config
        call_args: Any = mock_source_repository.add_async.call_args
        saved_source: UpstreamSource = call_args[0][0]
        assert saved_source.state.auth_config is not None
        assert saved_source.state.auth_config.auth_type == "bearer"

    @pytest.mark.asyncio
    async def test_register_source_with_api_key_auth(self, handler: "RegisterSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test registering a source with API key authentication."""
        from application.commands.register_source_command import RegisterSourceCommand
        from domain.entities import UpstreamSource

        # Arrange
        command: RegisterSourceCommand = RegisterSourceCommand(
            name="API Key API",
            url="https://api.example.com/openapi.json",
            auth_type="api_key",
            api_key_name="X-API-Key",
            api_key_value="my-api-key",
            api_key_in="header",
            validate_url=False,
        )

        async def capture_source(source: UpstreamSource) -> UpstreamSource:
            return source

        mock_source_repository.add_async = AsyncMock(side_effect=capture_source)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        call_args: Any = mock_source_repository.add_async.call_args
        saved_source: UpstreamSource = call_args[0][0]
        assert saved_source.state.auth_config is not None
        assert saved_source.state.auth_config.auth_type == "api_key"

    @pytest.mark.asyncio
    async def test_register_source_invalid_source_type(self, handler: "RegisterSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test registering a source with invalid source type."""
        from application.commands.register_source_command import RegisterSourceCommand

        # Arrange
        command: RegisterSourceCommand = RegisterSourceCommand(
            name="Bad API",
            url="https://api.example.com/spec",
            source_type="invalid_type",
            validate_url=False,
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400
        mock_source_repository.add_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_source_with_user_context(self, handler: "RegisterSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test registering a source with user context for audit."""
        from application.commands.register_source_command import RegisterSourceCommand
        from domain.entities import UpstreamSource

        # Arrange
        command: RegisterSourceCommand = RegisterSourceCommand(
            name="User API",
            url="https://api.example.com/openapi.json",
            validate_url=False,
            user_info={"sub": "user123", "preferred_username": "testuser"},
        )

        async def capture_source(source: UpstreamSource) -> UpstreamSource:
            return source

        mock_source_repository.add_async = AsyncMock(side_effect=capture_source)

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        call_args: Any = mock_source_repository.add_async.call_args
        saved_source: UpstreamSource = call_args[0][0]
        assert saved_source.state.created_by == "user123"


class TestRefreshInventoryCommand(BaseTestCase):
    """Test RefreshInventoryCommand handler."""

    @pytest.fixture
    def mock_source_repository(self) -> MagicMock:
        """Create a mock UpstreamSource repository."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.add_async = AsyncMock()
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_tool_repository(self) -> MagicMock:
        """Create a mock SourceTool repository."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.add_async = AsyncMock()
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def handler(self, mock_source_repository: MagicMock, mock_tool_repository: MagicMock) -> "RefreshInventoryCommandHandler":
        """Create a RefreshInventoryCommandHandler with mocked dependencies."""
        from application.commands.refresh_inventory_command import RefreshInventoryCommandHandler

        mediator: Mediator = MagicMock(spec=Mediator)
        mapper: Mapper = MagicMock(spec=Mapper)
        cloud_event_bus: CloudEventBus = MagicMock(spec=CloudEventBus)
        cloud_event_publishing_options: Any = MagicMock()

        return RefreshInventoryCommandHandler(
            mediator=mediator,
            mapper=mapper,
            cloud_event_bus=cloud_event_bus,
            cloud_event_publishing_options=cloud_event_publishing_options,
            source_repository=mock_source_repository,
            tool_repository=mock_tool_repository,
        )

    @pytest.mark.asyncio
    async def test_refresh_inventory_source_not_found(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
    ) -> None:
        """Test refresh inventory for non-existent source."""
        from application.commands.refresh_inventory_command import RefreshInventoryCommand

        # Arrange
        mock_source_repository.get_async = AsyncMock(return_value=None)
        command: RefreshInventoryCommand = RefreshInventoryCommand(source_id="nonexistent")

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_refresh_inventory_disabled_source(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
    ) -> None:
        """Test refresh inventory for disabled source."""
        from application.commands.refresh_inventory_command import RefreshInventoryCommand
        from tests.fixtures import UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        source.disable(reason="Maintenance")
        mock_source_repository.get_async = AsyncMock(return_value=source)

        command: RefreshInventoryCommand = RefreshInventoryCommand(source_id=source.id())

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_refresh_inventory_success(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
        mock_tool_repository: MagicMock,
    ) -> None:
        """Test successful inventory refresh."""
        from unittest.mock import patch

        from application.commands.refresh_inventory_command import RefreshInventoryCommand
        from application.services import IngestionResult
        from domain.enums import ExecutionMode
        from domain.models import ExecutionProfile, ToolDefinition
        from tests.fixtures import UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        mock_source_repository.get_async = AsyncMock(return_value=source)

        # Mock the adapter's fetch_and_normalize
        mock_ingestion_result = IngestionResult(
            success=True,
            tools=[
                ToolDefinition(
                    name="test_tool",
                    description="A test tool",
                    input_schema={"type": "object", "properties": {}},
                    execution_profile=ExecutionProfile(
                        mode=ExecutionMode.SYNC_HTTP,
                        method="GET",
                        url_template="https://api.example.com/test",
                    ),
                    source_path="/test",
                )
            ],
            inventory_hash="abc123",
            source_version="1.0.0",
            warnings=[],
        )

        with patch("application.commands.refresh_inventory_command.get_adapter_for_type") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.fetch_and_normalize = AsyncMock(return_value=mock_ingestion_result)
            mock_get_adapter.return_value = mock_adapter

            command: RefreshInventoryCommand = RefreshInventoryCommand(source_id=source.id())

            # Act
            result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.data.success is True
        assert result.data.tools_discovered == 1
        mock_source_repository.update_async.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_inventory_skip_unchanged(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
    ) -> None:
        """Test refresh inventory skips update when hash unchanged."""
        from unittest.mock import PropertyMock, patch

        from application.commands.refresh_inventory_command import RefreshInventoryCommand
        from application.services import IngestionResult

        # Arrange - source already has matching hash
        existing_hash = "existing_hash_123"

        # Create a MagicMock source with controllable state
        mock_source = MagicMock()
        mock_source.id.return_value = "source123"
        mock_state = MagicMock()
        mock_state.name = "Test API"
        mock_state.source_type.value = "openapi"
        mock_state.source_type = MagicMock()
        mock_state.source_type.value = "openapi"
        mock_state.url = "https://api.example.com/openapi.json"
        mock_state.auth_config = None
        mock_state.is_enabled = True
        mock_state.inventory_hash = existing_hash
        type(mock_source).state = PropertyMock(return_value=mock_state)

        mock_source_repository.get_async = AsyncMock(return_value=mock_source)

        mock_ingestion_result = IngestionResult(
            success=True,
            tools=[],
            inventory_hash=existing_hash,  # Same hash
            source_version="1.0.0",
            warnings=[],
        )

        with patch("application.commands.refresh_inventory_command.get_adapter_for_type") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.fetch_and_normalize = AsyncMock(return_value=mock_ingestion_result)
            mock_get_adapter.return_value = mock_adapter

            command: RefreshInventoryCommand = RefreshInventoryCommand(source_id="source123", force=False)

            # Act
            result: OperationResult[Any] = await handler.handle_async(command)

        # Assert - should succeed but skip the update
        assert result.is_success
        assert "unchanged" in result.data.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_refresh_inventory_force_update(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
        mock_tool_repository: MagicMock,
    ) -> None:
        """Test force refresh updates even when hash unchanged."""
        from unittest.mock import PropertyMock, patch

        from application.commands.refresh_inventory_command import RefreshInventoryCommand
        from application.services import IngestionResult

        # Arrange - source already has matching hash
        existing_hash = "existing_hash_123"

        # Create a MagicMock source with controllable state
        mock_source = MagicMock()
        mock_source.id.return_value = "source123"
        mock_state = MagicMock()
        mock_state.name = "Test API"
        mock_state.source_type = MagicMock()
        mock_state.source_type.value = "openapi"
        mock_state.url = "https://api.example.com/openapi.json"
        mock_state.auth_config = None
        mock_state.is_enabled = True
        mock_state.inventory_hash = existing_hash
        type(mock_source).state = PropertyMock(return_value=mock_state)

        mock_source_repository.get_async = AsyncMock(return_value=mock_source)

        mock_ingestion_result = IngestionResult(
            success=True,
            tools=[],
            inventory_hash=existing_hash,  # Same hash, but force=True
            source_version="1.0.0",
            warnings=[],
        )

        with patch("application.commands.refresh_inventory_command.get_adapter_for_type") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.fetch_and_normalize = AsyncMock(return_value=mock_ingestion_result)
            mock_get_adapter.return_value = mock_adapter

            command: RefreshInventoryCommand = RefreshInventoryCommand(source_id="source123", force=True)  # Force refresh

            # Act
            result: OperationResult[Any] = await handler.handle_async(command)

        # Assert - should succeed and perform update
        assert result.is_success
        assert "unchanged" not in (result.data.warnings[0].lower() if result.data.warnings else "")

    @pytest.mark.asyncio
    async def test_refresh_inventory_adapter_error(
        self,
        handler: "RefreshInventoryCommandHandler",
        mock_source_repository: MagicMock,
    ) -> None:
        """Test refresh inventory handles adapter errors."""
        from unittest.mock import patch

        from application.commands.refresh_inventory_command import RefreshInventoryCommand
        from tests.fixtures import UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        mock_source_repository.get_async = AsyncMock(return_value=source)

        with patch("application.commands.refresh_inventory_command.get_adapter_for_type") as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_adapter.fetch_and_normalize = AsyncMock(side_effect=Exception("Connection timeout"))
            mock_get_adapter.return_value = mock_adapter

            command: RefreshInventoryCommand = RefreshInventoryCommand(source_id=source.id())

            # Act
            result: OperationResult[Any] = await handler.handle_async(command)

        # Assert - should succeed but with failure in result
        assert result.is_success  # Operation itself succeeded
        assert result.data.success is False  # But refresh failed
        assert "Connection timeout" in result.data.error


# ============================================================================
# DELETE SOURCE AND TOOL COMMANDS
# ============================================================================


class TestDeleteSourceCommand(BaseTestCase):
    """Test DeleteSourceCommand handler."""

    @pytest.fixture
    def mock_source_repository(self) -> MagicMock:
        """Create a mock UpstreamSource repository."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_source_dto_repository(self) -> MagicMock:
        """Create a mock SourceDtoRepository for read model deletion."""
        mock: MagicMock = MagicMock()
        mock.remove_async = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_tool_repository(self) -> MagicMock:
        """Create a mock SourceTool repository for cascading delete."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_tool_dto_repository(self) -> MagicMock:
        """Create a mock SourceToolDtoRepository for querying tools."""
        mock: MagicMock = MagicMock()
        mock.get_by_source_id_async = AsyncMock(return_value=[])  # Default: no tools
        mock.remove_async = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def handler(
        self,
        mock_source_repository: MagicMock,
        mock_source_dto_repository: MagicMock,
        mock_tool_repository: MagicMock,
        mock_tool_dto_repository: MagicMock,
    ) -> "DeleteSourceCommandHandler":
        """Create a DeleteSourceCommandHandler with mocked dependencies."""
        from application.commands.delete_source_command import DeleteSourceCommandHandler

        return DeleteSourceCommandHandler(
            source_repository=mock_source_repository,
            source_dto_repository=mock_source_dto_repository,
            tool_repository=mock_tool_repository,
            tool_dto_repository=mock_tool_dto_repository,
        )

    @pytest.mark.asyncio
    async def test_delete_source_success(
        self,
        handler: "DeleteSourceCommandHandler",
        mock_source_repository: MagicMock,
        mock_source_dto_repository: MagicMock,
    ) -> None:
        """Test successfully deleting a source with no tools."""
        from application.commands.delete_source_command import DeleteSourceCommand
        from tests.fixtures import UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        source_id = source.id()
        mock_source_repository.get_async = AsyncMock(return_value=source)
        mock_source_repository.update_async = AsyncMock(return_value=source)

        command: DeleteSourceCommand = DeleteSourceCommand(
            source_id=source_id,
            user_info={"sub": "admin123", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        mock_source_repository.update_async.assert_called_once()
        mock_source_repository.remove_async.assert_called_once_with(source_id)
        mock_source_dto_repository.remove_async.assert_called_once_with(source_id)
        assert result.data["message"] == "Source and all associated tools deleted successfully"
        assert result.data["tools_deleted"] == 0

    @pytest.mark.asyncio
    async def test_delete_source_not_found(self, handler: "DeleteSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test deleting non-existent source returns not found."""
        from application.commands.delete_source_command import DeleteSourceCommand

        # Arrange
        mock_source_repository.get_async = AsyncMock(return_value=None)

        command: DeleteSourceCommand = DeleteSourceCommand(source_id="nonexistent")

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 404
        mock_source_repository.update_async.assert_not_called()
        mock_source_repository.remove_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_source_with_user_context(self, handler: "DeleteSourceCommandHandler", mock_source_repository: MagicMock) -> None:
        """Test deleting source with user context for audit trail."""
        from application.commands.delete_source_command import DeleteSourceCommand
        from tests.fixtures import UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        source_id = source.id()
        mock_source_repository.get_async = AsyncMock(return_value=source)
        mock_source_repository.update_async = AsyncMock(return_value=source)

        command: DeleteSourceCommand = DeleteSourceCommand(
            source_id=source_id,
            reason="No longer needed",
            user_info={"sub": "admin123", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        mock_source_repository.update_async.assert_called_once()
        mock_source_repository.remove_async.assert_called_once_with(source_id)

    @pytest.mark.asyncio
    async def test_delete_source_cascades_tool_deletion(
        self,
        mock_source_repository: MagicMock,
        mock_source_dto_repository: MagicMock,
        mock_tool_repository: MagicMock,
        mock_tool_dto_repository: MagicMock,
    ) -> None:
        """Test that deleting a source cascades to delete all its tools."""
        from application.commands.delete_source_command import DeleteSourceCommand, DeleteSourceCommandHandler
        from tests.fixtures import SourceToolFactory, UpstreamSourceFactory

        # Arrange
        source = UpstreamSourceFactory.create()
        source_id = source.id()
        mock_source_repository.get_async = AsyncMock(return_value=source)
        mock_source_repository.update_async = AsyncMock(return_value=source)

        # Create mock tool DTOs that will be returned by the read model
        tool1 = SourceToolFactory.create(source_id=source_id)
        tool2 = SourceToolFactory.create(source_id=source_id)
        mock_tool_dtos = [
            MagicMock(id=tool1.id(), tool_name="Tool 1"),
            MagicMock(id=tool2.id(), tool_name="Tool 2"),
        ]
        mock_tool_dto_repository.get_by_source_id_async = AsyncMock(return_value=mock_tool_dtos)
        mock_tool_dto_repository.remove_async = AsyncMock()

        # Mock tool repository to return tools for deletion
        mock_tool_repository.get_async = AsyncMock(side_effect=[tool1, tool2])
        mock_tool_repository.update_async = AsyncMock()
        mock_tool_repository.remove_async = AsyncMock()

        handler = DeleteSourceCommandHandler(
            source_repository=mock_source_repository,
            source_dto_repository=mock_source_dto_repository,
            tool_repository=mock_tool_repository,
            tool_dto_repository=mock_tool_dto_repository,
        )

        command: DeleteSourceCommand = DeleteSourceCommand(
            source_id=source_id,
            user_info={"sub": "admin123", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        assert result.data["tools_deleted"] == 2

        # Verify tools were queried
        mock_tool_dto_repository.get_by_source_id_async.assert_called_once_with(
            source_id=source_id,
            include_disabled=True,
            include_deprecated=True,
        )

        # Verify each tool was deleted from both write and read models
        assert mock_tool_repository.get_async.call_count == 2
        assert mock_tool_repository.update_async.call_count == 2
        assert mock_tool_repository.remove_async.call_count == 2
        assert mock_tool_dto_repository.remove_async.call_count == 2

        # Verify source was deleted from both write and read models
        mock_source_repository.update_async.assert_called_once()
        mock_source_repository.remove_async.assert_called_once_with(source_id)
        mock_source_dto_repository.remove_async.assert_called_once_with(source_id)


class TestDeleteToolCommand(BaseTestCase):
    """Test DeleteToolCommand handler."""

    @pytest.fixture
    def mock_tool_repository(self) -> MagicMock:
        """Create a mock SourceTool repository."""
        mock: MagicMock = MagicMock()
        mock.get_async = AsyncMock(return_value=None)
        mock.update_async = AsyncMock()
        mock.remove_async = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def handler(self, mock_tool_repository: MagicMock) -> "DeleteToolCommandHandler":
        """Create a DeleteToolCommandHandler with mocked dependencies."""
        from application.commands.delete_tool_command import DeleteToolCommandHandler

        return DeleteToolCommandHandler(tool_repository=mock_tool_repository)

    @pytest.mark.asyncio
    async def test_delete_tool_success(self, handler: "DeleteToolCommandHandler", mock_tool_repository: MagicMock) -> None:
        """Test successfully deleting a tool."""
        from application.commands.delete_tool_command import DeleteToolCommand
        from tests.fixtures import SourceToolFactory

        # Arrange
        tool = SourceToolFactory.create(source_id="source123", tool_name="list_users")
        tool_id = tool.id()
        mock_tool_repository.get_async = AsyncMock(return_value=tool)
        mock_tool_repository.update_async = AsyncMock(return_value=tool)

        command: DeleteToolCommand = DeleteToolCommand(
            tool_id=tool_id,
            user_info={"sub": "admin123", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 200
        mock_tool_repository.update_async.assert_called_once()
        mock_tool_repository.remove_async.assert_called_once_with(tool_id)
        assert result.data["message"] == "Tool deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_tool_not_found(self, handler: "DeleteToolCommandHandler", mock_tool_repository: MagicMock) -> None:
        """Test deleting non-existent tool returns not found."""
        from application.commands.delete_tool_command import DeleteToolCommand

        # Arrange
        mock_tool_repository.get_async = AsyncMock(return_value=None)

        command: DeleteToolCommand = DeleteToolCommand(tool_id="source123:nonexistent")

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 404
        mock_tool_repository.update_async.assert_not_called()
        mock_tool_repository.remove_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_tool_with_reason(self, handler: "DeleteToolCommandHandler", mock_tool_repository: MagicMock) -> None:
        """Test deleting tool with reason for audit trail."""
        from application.commands.delete_tool_command import DeleteToolCommand
        from tests.fixtures import SourceToolFactory

        # Arrange
        tool = SourceToolFactory.create()
        tool_id = tool.id()
        mock_tool_repository.get_async = AsyncMock(return_value=tool)
        mock_tool_repository.update_async = AsyncMock(return_value=tool)

        command: DeleteToolCommand = DeleteToolCommand(
            tool_id=tool_id,
            reason="Security vulnerability found",
            user_info={"sub": "admin123", "roles": ["admin"]},
        )

        # Act
        result: OperationResult[Any] = await handler.handle_async(command)

        # Assert
        assert result.is_success
        mock_tool_repository.update_async.assert_called_once()
        mock_tool_repository.remove_async.assert_called_once_with(tool_id)
