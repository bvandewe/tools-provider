"""Test data factories and builders.

Provides reusable factory classes for creating test data with sensible defaults
and easy customization.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from domain.entities import SourceTool, Task, UpstreamSource
from domain.enums import ExecutionMode, SourceType, TaskPriority, TaskStatus
from domain.models import AuthConfig, ExecutionProfile, ToolDefinition
from integration.models.task_dto import TaskDto

# ============================================================================
# TASK FACTORY
# ============================================================================


class TaskFactory:
    """Factory for creating Task entities with sensible defaults."""

    @staticmethod
    def create(
        task_id: str | None = None,
        title: str = "Test Task",
        description: str = "Test task description",
        assignee_id: str | None = None,
        department: str = "Engineering",
        priority: TaskPriority = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.PENDING,
        created_by: str | None = None,
    ) -> Task:
        """Create a Task with defaults that can be overridden."""
        task: Task = Task(
            task_id=task_id or str(uuid4()),
            title=title,
            description=description,
            priority=priority,
            status=status,
            assignee_id=assignee_id,
            department=department,
            created_by=created_by,
        )
        return task

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list[Task]:
        """Create multiple tasks with incrementing titles."""
        tasks: list[Task] = [TaskFactory.create(title=f"Test Task {i+1}", **kwargs) for i in range(count)]
        return tasks

    @staticmethod
    def create_pending() -> Task:
        """Create a task with PENDING status."""
        return TaskFactory.create(status=TaskStatus.PENDING)

    @staticmethod
    def create_in_progress() -> Task:
        """Create a task with IN_PROGRESS status."""
        return TaskFactory.create(status=TaskStatus.IN_PROGRESS)

    @staticmethod
    def create_completed() -> Task:
        """Create a task with COMPLETED status."""
        return TaskFactory.create(status=TaskStatus.COMPLETED)

    @staticmethod
    def create_high_priority() -> Task:
        """Create a high priority task."""
        return TaskFactory.create(priority=TaskPriority.HIGH)

    @staticmethod
    def create_with_assignee(assignee_id: str) -> Task:
        """Create a task assigned to a specific user."""
        return TaskFactory.create(assignee_id=assignee_id)

    @staticmethod
    def create_for_department(department: str) -> Task:
        """Create a task for a specific department."""
        return TaskFactory.create(department=department)


# ============================================================================
# TASKDTO FACTORY
# ============================================================================


class TaskDtoFactory:
    """Factory for creating TaskDto instances with sensible defaults."""

    @staticmethod
    def create(
        task_id: str | None = None,
        title: str = "Test Task",
        description: str = "Test task description",
        assignee_id: str | None = None,
        department: str = "Engineering",
        priority: TaskPriority = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.PENDING,
        created_by: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> TaskDto:
        """Create a TaskDto with defaults that can be overridden."""
        return TaskDto(
            id=task_id or str(uuid4()),
            title=title,
            description=description,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            department=department,
            created_by=created_by,
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at,
        )

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list[TaskDto]:
        """Create multiple TaskDto instances with incrementing titles."""
        return [TaskDtoFactory.create(title=f"Test Task {i+1}", **kwargs) for i in range(count)]

    @staticmethod
    def create_for_department(department: str) -> TaskDto:
        """Create a TaskDto for a specific department."""
        return TaskDtoFactory.create(department=department)


# ============================================================================
# TOKEN FACTORY
# ============================================================================


class TokenFactory:
    """Factory for creating JWT tokens and auth-related test data."""

    @staticmethod
    def create_tokens(
        access_token: str | None = None,
        refresh_token: str | None = None,
        id_token: str | None = None,
    ) -> dict[str, str]:
        """Create a tokens dictionary."""
        tokens: dict[str, str] = {
            "access_token": access_token or "test_access_token",
            "refresh_token": refresh_token or "test_refresh_token",
            "id_token": id_token or "test_id_token",
        }
        return tokens

    @staticmethod
    def create_user_info(
        sub: str | None = None,
        email: str | None = None,
        name: str | None = None,
        roles: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create user info dictionary."""
        user_info: dict[str, Any] = {
            "sub": sub or str(uuid4()),
            "email": email or "test@example.com",
            "name": name or "Test User",
            "roles": roles or ["user"],
            **kwargs,
        }
        return user_info

    @staticmethod
    def create_jwt_claims(
        sub: str | None = None,
        username: str | None = None,
        roles: list[str] | None = None,
        exp_minutes: int = 15,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create JWT claims dictionary."""
        now: datetime = datetime.now(timezone.utc)
        claims: dict[str, Any] = {
            "sub": sub or str(uuid4()),
            "username": username or "testuser",
            "roles": roles or ["user"],
            "exp": now + timedelta(minutes=exp_minutes),
            "iat": now,
            **kwargs,
        }
        return claims


# ============================================================================
# SESSION FACTORY
# ============================================================================


class SessionFactory:
    """Factory for creating session data."""

    @staticmethod
    def create_session_data(
        tokens: dict[str, str] | None = None,
        user_info: dict[str, Any] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Create tokens and user_info for a session."""
        session_tokens: dict[str, str] = tokens or TokenFactory.create_tokens()
        session_user_info: dict[str, Any] = user_info or TokenFactory.create_user_info()
        return (session_tokens, session_user_info)


# ============================================================================
# UPSTREAM SOURCE FACTORY
# ============================================================================


class UpstreamSourceFactory:
    """Factory for creating UpstreamSource entities with sensible defaults."""

    @staticmethod
    def create(
        source_id: str | None = None,
        name: str = "Test API",
        url: str = "https://api.example.com/openapi.json",
        source_type: SourceType = SourceType.OPENAPI,
        auth_config: AuthConfig | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
    ) -> UpstreamSource:
        """Create an UpstreamSource with defaults that can be overridden."""
        source: UpstreamSource = UpstreamSource(
            source_id=source_id or str(uuid4()),
            name=name,
            url=url,
            source_type=source_type,
            auth_config=auth_config,
            created_at=created_at,
            created_by=created_by,
        )
        return source

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list[UpstreamSource]:
        """Create multiple sources with incrementing names."""
        sources: list[UpstreamSource] = [UpstreamSourceFactory.create(name=f"Test API {i+1}", **kwargs) for i in range(count)]
        return sources

    @staticmethod
    def create_openapi() -> UpstreamSource:
        """Create an OpenAPI source."""
        return UpstreamSourceFactory.create(source_type=SourceType.OPENAPI)

    @staticmethod
    def create_workflow() -> UpstreamSource:
        """Create a Workflow source."""
        return UpstreamSourceFactory.create(source_type=SourceType.WORKFLOW)

    @staticmethod
    def create_with_auth(auth_type: str = "bearer") -> UpstreamSource:
        """Create a source with authentication configured."""
        auth_config = AuthConfigFactory.create(auth_type=auth_type)
        return UpstreamSourceFactory.create(auth_config=auth_config)

    @staticmethod
    def create_disabled() -> UpstreamSource:
        """Create a source and then disable it."""
        source = UpstreamSourceFactory.create()
        source.disable()
        return source


# ============================================================================
# AUTH CONFIG FACTORY
# ============================================================================


class AuthConfigFactory:
    """Factory for creating AuthConfig value objects."""

    @staticmethod
    def create(
        auth_type: str = "bearer",
        bearer_token: str | None = None,
        oauth2_client_id: str | None = None,
        oauth2_client_secret: str | None = None,
        oauth2_token_url: str | None = None,
        oauth2_scopes: list[str] | None = None,
        api_key_name: str | None = None,
        api_key_value: str | None = None,
        api_key_in: str | None = None,
    ) -> AuthConfig:
        """Create an AuthConfig with defaults that can be overridden."""
        return AuthConfig(
            auth_type=auth_type,
            bearer_token=bearer_token or "test-bearer-token-12345",
            oauth2_client_id=oauth2_client_id,
            oauth2_client_secret=oauth2_client_secret,
            oauth2_token_url=oauth2_token_url,
            oauth2_scopes=oauth2_scopes or [],
            api_key_name=api_key_name,
            api_key_value=api_key_value,
            api_key_in=api_key_in,
        )

    @staticmethod
    def create_bearer(token: str = "bearer-token-xyz") -> AuthConfig:
        """Create a bearer token auth config."""
        return AuthConfig.bearer(token=token)

    @staticmethod
    def create_oauth2() -> AuthConfig:
        """Create an OAuth2 client credentials auth config."""
        return AuthConfig.oauth2(
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client-id",
            client_secret="test-client-secret",  # pragma: allowlist secret
            scopes=["read", "write"],
        )

    @staticmethod
    def create_api_key() -> AuthConfig:
        """Create an API key auth config."""
        return AuthConfig.api_key(
            name="X-API-Key",
            value="api-key-abc123",
            location="header",
        )

    @staticmethod
    def create_none() -> AuthConfig:
        """Create a no-auth config."""
        return AuthConfig.none()


# ============================================================================
# TOOL DEFINITION FACTORY
# ============================================================================


class ExecutionProfileFactory:
    """Factory for creating ExecutionProfile value objects."""

    @staticmethod
    def create(
        mode: ExecutionMode = ExecutionMode.SYNC_HTTP,
        method: str = "GET",
        url_template: str = "https://api.example.com/test",
        headers_template: dict[str, str] | None = None,
        body_template: str | None = None,
        content_type: str = "application/json",
        timeout_seconds: int = 30,
        required_audience: str = "",
        required_scopes: list[str] | None = None,
    ) -> ExecutionProfile:
        """Create an ExecutionProfile with defaults that can be overridden."""
        return ExecutionProfile(
            mode=mode,
            method=method,
            url_template=url_template,
            headers_template=headers_template or {},
            body_template=body_template,
            content_type=content_type,
            timeout_seconds=timeout_seconds,
            required_audience=required_audience,
            required_scopes=required_scopes or [],
        )


class ToolDefinitionFactory:
    """Factory for creating ToolDefinition value objects."""

    @staticmethod
    def create(
        name: str = "test_tool",
        description: str = "A test tool for unit testing",
        input_schema: dict[str, Any] | None = None,
        source_path: str = "/api/test",
        tags: list[str] | None = None,
        execution_profile: ExecutionProfile | None = None,
    ) -> ToolDefinition:
        """Create a ToolDefinition with defaults that can be overridden."""
        actual_execution_profile = execution_profile or ExecutionProfileFactory.create(url_template=f"https://api.example.com{source_path}")

        return ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema or {"type": "object", "properties": {}},
            execution_profile=actual_execution_profile,
            source_path=source_path,
            tags=tags or ["test"],
        )

    @staticmethod
    def create_get_users() -> ToolDefinition:
        """Create a GET users tool definition."""
        return ToolDefinitionFactory.create(
            name="get_users",
            description="Retrieve a list of users",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results"},
                    "offset": {"type": "integer", "description": "Skip results"},
                },
            },
            source_path="/api/users",
            tags=["users"],
            execution_profile=ExecutionProfileFactory.create(
                method="GET",
                url_template="https://api.example.com/api/users",
            ),
        )

    @staticmethod
    def create_create_user() -> ToolDefinition:
        """Create a POST create user tool definition."""
        return ToolDefinitionFactory.create(
            name="create_user",
            description="Create a new user",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "User name"},
                    "email": {"type": "string", "description": "User email"},
                },
                "required": ["name", "email"],
            },
            source_path="/api/users",
            tags=["users"],
            execution_profile=ExecutionProfileFactory.create(
                method="POST",
                url_template="https://api.example.com/api/users",
                body_template='{"name": "{{ name }}", "email": "{{ email }}"}',
            ),
        )

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list[ToolDefinition]:
        """Create multiple tool definitions with incrementing names."""
        return [
            ToolDefinitionFactory.create(
                name=f"test_tool_{i+1}",
                source_path=f"/api/tool{i+1}",
                **kwargs,
            )
            for i in range(count)
        ]


# ============================================================================
# SOURCE TOOL FACTORY
# ============================================================================


class SourceToolFactory:
    """Factory for creating SourceTool entities with sensible defaults."""

    @staticmethod
    def create(
        source_id: str | None = None,
        operation_id: str = "test_operation",
        tool_name: str = "Test Tool",
        definition: ToolDefinition | None = None,
        discovered_at: datetime | None = None,
    ) -> SourceTool:
        """Create a SourceTool with defaults that can be overridden."""
        actual_source_id = source_id or str(uuid4())
        actual_definition = definition or ToolDefinitionFactory.create()

        tool: SourceTool = SourceTool(
            source_id=actual_source_id,
            operation_id=operation_id,
            tool_name=tool_name,
            definition=actual_definition,
            discovered_at=discovered_at,
        )
        return tool

    @staticmethod
    def create_many(
        count: int,
        source_id: str | None = None,
        **kwargs: Any,
    ) -> list[SourceTool]:
        """Create multiple tools with incrementing names."""
        actual_source_id = source_id or str(uuid4())
        tools: list[SourceTool] = [
            SourceToolFactory.create(
                source_id=actual_source_id,
                operation_id=f"operation_{i+1}",
                tool_name=f"Test Tool {i+1}",
                definition=ToolDefinitionFactory.create(
                    name=f"tool_{i+1}",
                    source_path=f"/api/tool{i+1}",
                ),
                **kwargs,
            )
            for i in range(count)
        ]
        return tools

    @staticmethod
    def create_disabled(source_id: str | None = None) -> SourceTool:
        """Create a tool and then disable it."""
        tool = SourceToolFactory.create(source_id=source_id)
        tool.disable(disabled_by="admin", reason="Testing disabled state")
        return tool

    @staticmethod
    def create_deprecated(source_id: str | None = None) -> SourceTool:
        """Create a tool and then deprecate it."""
        tool = SourceToolFactory.create(source_id=source_id)
        tool.deprecate()
        return tool

    @staticmethod
    def create_for_source(source: UpstreamSource) -> SourceTool:
        """Create a tool linked to a specific source."""
        return SourceToolFactory.create(source_id=source.id())
