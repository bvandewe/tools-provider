"""Test data factories and builders.

Provides reusable factory classes for creating test data with sensible defaults
and easy customization.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from domain.entities import SourceTool, Task, UpstreamSource
from domain.enums import ExecutionMode, McpTransportType, PluginLifecycleMode, SourceType, TaskPriority, TaskStatus
from domain.models import AuthConfig, ExecutionProfile, McpEnvironmentVariable, McpEnvVarDefinition, McpManifest, McpPackage, McpSourceConfig, ToolDefinition
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
        tasks: list[Task] = [TaskFactory.create(title=f"Test Task {i + 1}", **kwargs) for i in range(count)]
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
            created_at=created_at or datetime.now(UTC),
            updated_at=updated_at,
        )

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list[TaskDto]:
        """Create multiple TaskDto instances with incrementing titles."""
        return [TaskDtoFactory.create(title=f"Test Task {i + 1}", **kwargs) for i in range(count)]

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
        now: datetime = datetime.now(UTC)
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
        sources: list[UpstreamSource] = [UpstreamSourceFactory.create(name=f"Test API {i + 1}", **kwargs) for i in range(count)]
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

    @staticmethod
    def create_mcp(
        source_id: str | None = None,
        name: str = "Test MCP Plugin",
        url: str = "file:///app/plugins/test-mcp",
        mcp_config: McpSourceConfig | None = None,
        created_by: str | None = None,
    ) -> UpstreamSource:
        """Create an MCP source with optional configuration."""
        config = mcp_config or McpSourceConfigFactory.create()
        return UpstreamSource(
            source_id=source_id or str(uuid4()),
            name=name,
            url=url,
            source_type=SourceType.MCP,
            mcp_config=config,
            created_by=created_by,
        )


# ============================================================================
# MCP SOURCE CONFIG FACTORY
# ============================================================================


class McpSourceConfigFactory:
    """Factory for creating McpSourceConfig value objects."""

    @staticmethod
    def create(
        manifest_path: str = "/app/plugins/test-mcp/server.json",
        plugin_dir: str = "/app/plugins/test-mcp",
        transport_type: McpTransportType = McpTransportType.STDIO,
        lifecycle_mode: PluginLifecycleMode = PluginLifecycleMode.TRANSIENT,
        runtime_hint: str = "uvx",
        command: list[str] | None = None,
        environment: dict[str, str] | None = None,
        env_definitions: list[McpEnvironmentVariable] | None = None,
    ) -> McpSourceConfig:
        """Create an McpSourceConfig with defaults that can be overridden."""
        return McpSourceConfig(
            manifest_path=manifest_path,
            plugin_dir=plugin_dir,
            transport_type=transport_type,
            lifecycle_mode=lifecycle_mode,
            runtime_hint=runtime_hint,
            command=command or ["uvx", "test-mcp"],
            environment=environment or {},
            env_definitions=env_definitions or [],
        )

    @staticmethod
    def create_with_env_vars() -> McpSourceConfig:
        """Create an McpSourceConfig with environment variable definitions."""
        return McpSourceConfig(
            manifest_path="/app/plugins/cml-mcp/server.json",
            plugin_dir="/app/plugins/cml-mcp",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "cml-mcp"],
            environment={},
            env_definitions=[
                McpEnvironmentVariable(
                    name="CML_URL",
                    description="CML server URL",
                    is_required=True,
                    is_secret=False,
                    format="uri",
                ),
                McpEnvironmentVariable(
                    name="CML_TOKEN",
                    description="CML API token",
                    is_required=True,
                    is_secret=True,
                ),
            ],
        )

    @staticmethod
    def create_resolved() -> McpSourceConfig:
        """Create an McpSourceConfig with resolved environment variables."""
        return McpSourceConfig(
            manifest_path="/app/plugins/cml-mcp/server.json",
            plugin_dir="/app/plugins/cml-mcp",
            transport_type=McpTransportType.STDIO,
            lifecycle_mode=PluginLifecycleMode.TRANSIENT,
            runtime_hint="uvx",
            command=["uvx", "cml-mcp"],
            environment={
                "CML_URL": "https://cml.example.com",
                "CML_TOKEN": "test-token-123",
            },
            env_definitions=[
                McpEnvironmentVariable(
                    name="CML_URL",
                    description="CML server URL",
                    is_required=True,
                    is_secret=False,
                    format="uri",
                    value="https://cml.example.com",
                ),
                McpEnvironmentVariable(
                    name="CML_TOKEN",
                    description="CML API token",
                    is_required=True,
                    is_secret=True,
                    value="test-token-123",
                ),
            ],
        )


# ============================================================================
# MCP MANIFEST FACTORY
# ============================================================================


class McpManifestFactory:
    """Factory for creating McpManifest value objects."""

    @staticmethod
    def create(
        name: str = "test-mcp",
        title: str = "Test MCP Server",
        description: str = "A test MCP server",
        version: str = "1.0.0",
        repository_url: str | None = "https://github.com/example/test-mcp",
        packages: list[McpPackage] | None = None,
    ) -> McpManifest:
        """Create an McpManifest with defaults that can be overridden."""
        if packages is None:
            packages = [McpManifestFactory.create_package()]

        return McpManifest(
            name=name,
            title=title,
            description=description,
            version=version,
            repository_url=repository_url,
            packages=packages,
        )

    @staticmethod
    def create_package(
        registry_type: str = "pypi",
        identifier: str = "test-mcp",
        version: str = "1.0.0",
        runtime_hint: str | None = "uvx",
        transport_type: str = "stdio",
        environment_variables: list[McpEnvVarDefinition] | None = None,
        args: list[str] | None = None,
    ) -> McpPackage:
        """Create an McpPackage with defaults that can be overridden."""
        return McpPackage(
            registry_type=registry_type,
            identifier=identifier,
            version=version,
            runtime_hint=runtime_hint,
            transport_type=transport_type,
            environment_variables=environment_variables or [],
            args=args or [],
        )

    @staticmethod
    def create_cml_manifest() -> McpManifest:
        """Create a CML-like manifest for realistic testing."""
        return McpManifest(
            name="cml-mcp",
            title="Cisco Modeling Labs MCP",
            description="MCP server for Cisco Modeling Labs network simulation",
            version="0.1.0",
            repository_url="https://github.com/example/cml-mcp",
            packages=[
                McpPackage(
                    registry_type="pypi",
                    identifier="cml-mcp",
                    version="0.1.0",
                    runtime_hint="uvx",
                    transport_type="stdio",
                    environment_variables=[
                        McpEnvVarDefinition(
                            name="CML_URL",
                            description="CML server URL",
                            is_required=True,
                            is_secret=False,
                            format="uri",
                        ),
                        McpEnvVarDefinition(
                            name="CML_TOKEN",
                            description="CML API token",
                            is_required=True,
                            is_secret=True,
                        ),
                    ],
                )
            ],
        )


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
        basic_username: str | None = None,
        basic_password: str | None = None,
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
            basic_username=basic_username,
            basic_password=basic_password,
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
    def create_http_basic(username: str = "test-user", password: str = "test-password") -> AuthConfig:  # pragma: allowlist secret
        """Create an HTTP Basic auth config."""
        return AuthConfig.http_basic(
            username=username,
            password=password,
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
                name=f"test_tool_{i + 1}",
                source_path=f"/api/tool{i + 1}",
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
                operation_id=f"operation_{i + 1}",
                tool_name=f"Test Tool {i + 1}",
                definition=ToolDefinitionFactory.create(
                    name=f"tool_{i + 1}",
                    source_path=f"/api/tool{i + 1}",
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


# ============================================================================
# TOOL GROUP FACTORY
# ============================================================================


class ToolGroupFactory:
    """Factory for creating ToolGroup entities with sensible defaults."""

    @staticmethod
    def create(
        group_id: str | None = None,
        name: str = "Test Group",
        description: str = "A test tool group",
        created_at: datetime | None = None,
        created_by: str | None = None,
    ) -> "ToolGroup":
        """Create a ToolGroup with defaults that can be overridden."""
        from domain.entities import ToolGroup

        group: ToolGroup = ToolGroup(
            group_id=group_id or str(uuid4()),
            name=name,
            description=description,
            created_at=created_at,
            created_by=created_by,
        )
        return group

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list["ToolGroup"]:
        """Create multiple groups with incrementing names."""
        groups: list[ToolGroup] = [ToolGroupFactory.create(name=f"Test Group {i + 1}", **kwargs) for i in range(count)]
        return groups

    @staticmethod
    def create_inactive() -> "ToolGroup":
        """Create a group and then deactivate it."""
        group = ToolGroupFactory.create()
        group.deactivate(deactivated_by="admin")
        return group

    @staticmethod
    def create_with_selector(selector: "ToolSelector") -> "ToolGroup":
        """Create a group with a pre-configured selector."""
        group = ToolGroupFactory.create()
        group.add_selector(selector, added_by="admin")
        return group

    @staticmethod
    def create_with_tools(tool_ids: list[str]) -> "ToolGroup":
        """Create a group with explicit tools."""
        group = ToolGroupFactory.create()
        for tool_id in tool_ids:
            group.add_tool(tool_id, added_by="admin")
        return group


# ============================================================================
# TOOL SELECTOR FACTORY
# ============================================================================


class ToolSelectorFactory:
    """Factory for creating ToolSelector value objects."""

    @staticmethod
    def create(
        selector_id: str | None = None,
        source_pattern: str = "*",
        name_pattern: str = "*",
        path_pattern: str | None = None,
        method_pattern: str | None = None,
        required_tags: list[str] | None = None,
        excluded_tags: list[str] | None = None,
        required_label_ids: list[str] | None = None,
    ) -> "ToolSelector":
        """Create a ToolSelector with defaults that can be overridden."""
        from domain.models import ToolSelector

        return ToolSelector(
            id=selector_id or str(uuid4()),
            source_pattern=source_pattern,
            name_pattern=name_pattern,
            path_pattern=path_pattern,
            method_pattern=method_pattern,
            required_tags=required_tags or [],
            excluded_tags=excluded_tags or [],
            required_label_ids=required_label_ids or [],
        )

    @staticmethod
    def create_source_selector(source_pattern: str) -> "ToolSelector":
        """Create a selector that matches tools from a specific source pattern."""
        return ToolSelectorFactory.create(
            source_pattern=source_pattern,
        )

    @staticmethod
    def create_tag_selector(required_tags: list[str]) -> "ToolSelector":
        """Create a selector that matches tools by required tags."""
        return ToolSelectorFactory.create(
            required_tags=required_tags,
        )

    @staticmethod
    def create_name_selector(name_pattern: str) -> "ToolSelector":
        """Create a selector that matches tools by name pattern."""
        return ToolSelectorFactory.create(
            name_pattern=name_pattern,
        )

    @staticmethod
    def create_name_selector(pattern: str) -> "ToolSelector":
        """Create a selector that matches tools by name pattern."""
        return ToolSelectorFactory.create(
            selector_type="name",
            name_pattern=pattern,
        )

    @staticmethod
    def create_method_selector(method_pattern: str) -> "ToolSelector":
        """Create a selector that matches tools by HTTP method pattern."""
        return ToolSelectorFactory.create(
            method_pattern=method_pattern,
        )

    @staticmethod
    def create_label_selector(required_label_ids: list[str]) -> "ToolSelector":
        """Create a selector that matches tools by required label IDs."""
        return ToolSelectorFactory.create(
            required_label_ids=required_label_ids,
        )


# ============================================================================
# TOOL GROUP DTO FACTORY
# ============================================================================


class ToolGroupDtoFactory:
    """Factory for creating ToolGroupDto instances with sensible defaults."""

    @staticmethod
    def create(
        group_id: str | None = None,
        name: str = "Test Group",
        description: str = "A test tool group",
        is_active: bool = True,
        selectors: list[dict[str, Any]] | None = None,
        explicit_tool_ids: list[str] | None = None,
        excluded_tool_ids: list[str] | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        updated_at: datetime | None = None,
        updated_by: str | None = None,
    ) -> "ToolGroupDto":
        """Create a ToolGroupDto with defaults that can be overridden."""
        from integration.models import ToolGroupDto

        return ToolGroupDto(
            id=group_id or str(uuid4()),
            name=name,
            description=description,
            is_active=is_active,
            selectors=selectors or [],
            explicit_tool_ids=explicit_tool_ids or [],
            excluded_tool_ids=excluded_tool_ids or [],
            created_at=created_at or datetime.now(UTC),
            created_by=created_by,
            updated_at=updated_at,
            updated_by=updated_by,
        )

    @staticmethod
    def create_many(count: int, **kwargs: Any) -> list["ToolGroupDto"]:
        """Create multiple ToolGroupDto instances with incrementing names."""

        return [ToolGroupDtoFactory.create(name=f"Test Group {i + 1}", **kwargs) for i in range(count)]

    @staticmethod
    def create_inactive() -> "ToolGroupDto":
        """Create an inactive ToolGroupDto."""
        return ToolGroupDtoFactory.create(is_active=False)
