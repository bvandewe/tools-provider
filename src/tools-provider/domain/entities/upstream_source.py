"""UpstreamSource aggregate definition using the AggregateState pattern.

This aggregate manages the connection to an external system (OpenAPI or Workflow)
and tracks the lifecycle of its tool inventory.

Following the Task aggregate pattern:
- DomainEvents are registered via register_event()
- State is updated via @dispatch handlers
- Repository publishes events after persistence
"""

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from multipledispatch import dispatch
from neuroglia.data.abstractions import AggregateRoot, AggregateState

from domain.enums import AuthMode, HealthStatus, SourceType
from domain.events.upstream_source import (
    InventoryIngestedDomainEvent,
    SourceAuthUpdatedDomainEvent,
    SourceDeregisteredDomainEvent,
    SourceDisabledDomainEvent,
    SourceEnabledDomainEvent,
    SourceHealthChangedDomainEvent,
    SourceRegisteredDomainEvent,
    SourceSyncFailedDomainEvent,
    SourceSyncStartedDomainEvent,
    SourceUpdatedDomainEvent,
)
from domain.models import AuthConfig, McpSourceConfig, ToolDefinition

# Forward reference for DTO mapping (will be in integration layer)
# from integration.models.source_dto import SourceDto


# @map_to(SourceDto)  # Uncomment when SourceDto is created
class UpstreamSourceState(AggregateState[str]):
    """Encapsulates the persisted state for the UpstreamSource aggregate."""

    # Identity
    id: str
    name: str
    description: str | None  # Human-readable description of the source
    url: str  # Service base URL
    openapi_url: str | None  # URL to the OpenAPI specification (separate from base URL)
    source_type: SourceType

    # Authentication
    auth_config: AuthConfig | None
    default_audience: str | None  # Target audience for token exchange (client_id of upstream service)
    auth_mode: AuthMode  # Authentication mode for tool execution
    required_scopes: list[str]  # Scopes required for all tools from this source

    # Health tracking
    health_status: HealthStatus
    last_sync_at: datetime | None
    last_sync_error: str | None
    consecutive_failures: int

    # Inventory
    inventory_hash: str
    inventory_count: int

    # Lifecycle
    is_enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    # MCP-specific configuration (None for non-MCP sources)
    mcp_config: dict | None  # Serialized McpSourceConfig

    def __init__(self) -> None:
        super().__init__()
        # Initialize ALL fields with defaults (required by Neuroglia)
        self.id = ""
        self.name = ""
        self.description = None
        self.url = ""
        self.openapi_url = None
        self.source_type = SourceType.OPENAPI
        self.auth_config = None
        self.default_audience = None
        self.auth_mode = AuthMode.TOKEN_EXCHANGE  # Default for backward compatibility
        self.required_scopes = []  # Default: no source-level scope requirements

        self.health_status = HealthStatus.UNKNOWN
        self.last_sync_at = None
        self.last_sync_error = None
        self.consecutive_failures = 0

        self.inventory_hash = ""
        self.inventory_count = 0

        self.is_enabled = True
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now
        self.created_by = None
        self.mcp_config = None

    # =========================================================================
    # Event Handlers - Apply events to state
    # =========================================================================

    @dispatch(SourceRegisteredDomainEvent)
    def on(self, event: SourceRegisteredDomainEvent) -> None:  # type: ignore[override]
        """Apply the registration event to the state."""
        self.id = event.aggregate_id
        self.name = event.name
        self.description = event.description
        self.url = event.url
        self.openapi_url = event.openapi_url
        self.source_type = event.source_type
        self.created_at = event.created_at
        self.updated_at = event.created_at
        self.created_by = event.created_by
        self.default_audience = event.default_audience
        self.auth_mode = getattr(event, "auth_mode", AuthMode.TOKEN_EXCHANGE)
        # Handle backward compatibility for events without required_scopes field
        self.required_scopes = getattr(event, "required_scopes", None) or []
        # Handle MCP configuration (None for non-MCP sources)
        self.mcp_config = getattr(event, "mcp_config", None)

    @dispatch(InventoryIngestedDomainEvent)
    def on(self, event: InventoryIngestedDomainEvent) -> None:  # type: ignore[override]
        """Apply the inventory ingested event to the state."""
        self.inventory_hash = event.inventory_hash
        self.inventory_count = event.tool_count
        self.last_sync_at = event.ingested_at
        self.last_sync_error = None
        self.consecutive_failures = 0
        self.health_status = HealthStatus.HEALTHY
        self.updated_at = event.ingested_at

    @dispatch(SourceSyncStartedDomainEvent)
    def on(self, event: SourceSyncStartedDomainEvent) -> None:  # type: ignore[override]
        """Apply the sync started event to the state."""
        # Just track that sync is in progress
        self.updated_at = event.started_at

    @dispatch(SourceSyncFailedDomainEvent)
    def on(self, event: SourceSyncFailedDomainEvent) -> None:  # type: ignore[override]
        """Apply the sync failed event to the state."""
        self.last_sync_error = event.error
        self.consecutive_failures = event.attempt
        self.updated_at = event.failed_at

        # Update health status based on failure count
        if event.attempt >= 3:
            self.health_status = HealthStatus.UNHEALTHY
        elif event.attempt >= 1:
            self.health_status = HealthStatus.DEGRADED

    @dispatch(SourceHealthChangedDomainEvent)
    def on(self, event: SourceHealthChangedDomainEvent) -> None:  # type: ignore[override]
        """Apply the health changed event to the state."""
        self.health_status = event.new_status
        self.updated_at = event.changed_at

    @dispatch(SourceEnabledDomainEvent)
    def on(self, event: SourceEnabledDomainEvent) -> None:  # type: ignore[override]
        """Apply the enabled event to the state."""
        self.is_enabled = True
        self.updated_at = event.enabled_at

    @dispatch(SourceDisabledDomainEvent)
    def on(self, event: SourceDisabledDomainEvent) -> None:  # type: ignore[override]
        """Apply the disabled event to the state."""
        self.is_enabled = False
        self.updated_at = event.disabled_at

    @dispatch(SourceAuthUpdatedDomainEvent)
    def on(self, event: SourceAuthUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the auth updated event to the state.

        Note: The actual auth_config is set directly in the aggregate method
        before the event is registered, since we don't want to store secrets
        in events.
        """
        self.updated_at = event.updated_at

    @dispatch(SourceDeregisteredDomainEvent)
    def on(self, event: SourceDeregisteredDomainEvent) -> None:  # type: ignore[override]
        """Apply the deregistered event to the state."""
        self.is_enabled = False
        self.updated_at = event.deregistered_at

    @dispatch(SourceUpdatedDomainEvent)
    def on(self, event: SourceUpdatedDomainEvent) -> None:  # type: ignore[override]
        """Apply the updated event to the state."""
        if event.name is not None:
            self.name = event.name
        if event.description is not None:
            self.description = event.description
        if event.url is not None:
            self.url = event.url
        # Handle backward compatibility for events without required_scopes field
        required_scopes = getattr(event, "required_scopes", None)
        if required_scopes is not None:
            self.required_scopes = required_scopes
        self.updated_at = event.updated_at


class UpstreamSource(AggregateRoot[UpstreamSourceState, str]):
    """UpstreamSource aggregate root following the AggregateState pattern.

    Represents an external system (OpenAPI spec or Workflow Engine) that
    provides tools to be exposed to AI agents.

    Lifecycle:
    1. register() - Creates the source with connection info
    2. update_inventory() - Called after successful spec fetch
    3. mark_sync_failed() - Called when fetch fails
    4. enable()/disable() - Toggle availability
    5. mark_as_deleted() - Soft delete

    Note: Neuroglia's Aggregator.aggregate() uses object.__new__() which doesn't
    initialize _pending_events. However, register_event() lazily initializes it,
    so methods that emit events work correctly.
    """

    def __init__(
        self,
        name: str,
        url: str,
        source_type: SourceType,
        auth_config: AuthConfig | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        source_id: str | None = None,
        default_audience: str | None = None,
        openapi_url: str | None = None,
        description: str | None = None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        required_scopes: list[str] | None = None,
        mcp_config: McpSourceConfig | None = None,
    ) -> None:
        """Create a new UpstreamSource aggregate.

        Args:
            name: Human-readable name for this source
            url: Base URL of the upstream service (e.g., https://api.example.com)
            source_type: Type of source (OPENAPI, WORKFLOW, or MCP)
            auth_config: Optional authentication configuration
            created_at: Optional creation timestamp (defaults to now)
            created_by: Optional user ID who created this source
            source_id: Optional specific ID (defaults to UUID)
            default_audience: Optional target audience for token exchange (client_id of upstream service)
            openapi_url: Optional URL to the OpenAPI specification (if different from url)
            description: Optional human-readable description of the source
            auth_mode: Authentication mode for tool execution (default: TOKEN_EXCHANGE)
            required_scopes: Optional scopes required for all tools from this source
            mcp_config: Optional MCP configuration (required for MCP sources)
        """
        super().__init__()
        aggregate_id = source_id or str(uuid4())
        created_time = created_at or datetime.now(UTC)

        # Store auth config directly on state (not in event for security)
        if auth_config:
            self.state.auth_config = auth_config

        # Serialize mcp_config for event storage
        mcp_config_dict = mcp_config.to_dict() if mcp_config else None

        self.state.on(
            self.register_event(  # type: ignore
                SourceRegisteredDomainEvent(
                    aggregate_id=aggregate_id,
                    name=name,
                    url=url,
                    source_type=source_type,
                    created_at=created_time,
                    created_by=created_by,
                    default_audience=default_audience,
                    openapi_url=openapi_url,
                    description=description,
                    auth_mode=auth_mode,
                    required_scopes=required_scopes,
                    mcp_config=mcp_config_dict,
                )
            )
        )

    def id(self) -> str:
        """Return the aggregate identifier with a precise type."""
        aggregate_id = super().id()
        if aggregate_id is None:
            raise ValueError("UpstreamSource aggregate identifier has not been initialized")
        return cast(str, aggregate_id)

    # =========================================================================
    # Inventory Management
    # =========================================================================

    def update_inventory(
        self,
        tools: list[ToolDefinition],
        new_hash: str,
    ) -> bool:
        """Update the tool inventory after a successful sync.

        Args:
            tools: List of normalized ToolDefinition objects
            new_hash: Hash of the new inventory for change detection

        Returns:
            True if inventory was updated, False if unchanged
        """
        # Skip if inventory hasn't changed
        if self.state.inventory_hash == new_hash:
            return False

        # Serialize tools for event storage
        serialized_tools = [tool.to_dict() for tool in tools]

        self.state.on(
            self.register_event(  # type: ignore
                InventoryIngestedDomainEvent(
                    aggregate_id=self.id(),
                    tools=serialized_tools,
                    inventory_hash=new_hash,
                    tool_count=len(tools),
                    ingested_at=datetime.now(UTC),
                )
            )
        )
        return True

    def mark_sync_started(self, triggered_by: str | None = None) -> None:
        """Mark that inventory sync has started."""
        self.state.on(
            self.register_event(  # type: ignore
                SourceSyncStartedDomainEvent(
                    aggregate_id=self.id(),
                    started_at=datetime.now(UTC),
                    triggered_by=triggered_by,
                )
            )
        )

    def mark_sync_failed(self, error: str) -> None:
        """Mark that inventory sync has failed.

        Increments the failure counter and updates health status.

        Args:
            error: Description of the failure
        """
        new_attempt = self.state.consecutive_failures + 1

        self.state.on(
            self.register_event(  # type: ignore
                SourceSyncFailedDomainEvent(
                    aggregate_id=self.id(),
                    error=error,
                    attempt=new_attempt,
                    failed_at=datetime.now(UTC),
                )
            )
        )

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
        required_scopes: list[str] | None = None,
        updated_by: str | None = None,
    ) -> bool:
        """Update the source's editable fields.

        Note: openapi_url is immutable and cannot be changed after registration.

        Args:
            name: New name for the source (None to keep current)
            description: New description (None to keep current)
            url: New service base URL (None to keep current)
            required_scopes: New scopes required for all tools (None to keep current)
            updated_by: User ID making the update

        Returns:
            True if any field was updated, False if no changes
        """
        # Check if any actual changes are being made
        has_changes = False
        if name is not None and name != self.state.name:
            has_changes = True
        if description is not None and description != self.state.description:
            has_changes = True
        if url is not None and url != self.state.url:
            has_changes = True
        if required_scopes is not None and required_scopes != self.state.required_scopes:
            has_changes = True

        if not has_changes:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    name=name if name != self.state.name else None,
                    description=description if description != self.state.description else None,
                    url=url if url != self.state.url else None,
                    required_scopes=required_scopes if required_scopes != self.state.required_scopes else None,
                    updated_at=datetime.now(UTC),
                    updated_by=updated_by,
                )
            )
        )
        return True

    # =========================================================================
    # Health Management
    # =========================================================================

    def update_health_status(
        self,
        new_status: HealthStatus,
        reason: str | None = None,
    ) -> bool:
        """Update the health status of this source.

        Args:
            new_status: New health status
            reason: Optional reason for the change

        Returns:
            True if status was updated, False if unchanged
        """
        if self.state.health_status == new_status:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceHealthChangedDomainEvent(
                    aggregate_id=self.id(),
                    old_status=self.state.health_status,
                    new_status=new_status,
                    changed_at=datetime.now(UTC),
                    reason=reason,
                )
            )
        )
        return True

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def enable(self, enabled_by: str | None = None) -> bool:
        """Enable this source for tool discovery.

        Returns:
            True if source was enabled, False if already enabled
        """
        if self.state.is_enabled:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceEnabledDomainEvent(
                    aggregate_id=self.id(),
                    enabled_at=datetime.now(UTC),
                    enabled_by=enabled_by,
                )
            )
        )
        return True

    def disable(
        self,
        disabled_by: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """Disable this source from tool discovery.

        Args:
            disabled_by: User who disabled the source
            reason: Optional reason for disabling

        Returns:
            True if source was disabled, False if already disabled
        """
        if not self.state.is_enabled:
            return False

        self.state.on(
            self.register_event(  # type: ignore
                SourceDisabledDomainEvent(
                    aggregate_id=self.id(),
                    disabled_at=datetime.now(UTC),
                    disabled_by=disabled_by,
                    reason=reason,
                )
            )
        )
        return True

    def update_auth_config(
        self,
        auth_config: AuthConfig,
        updated_by: str | None = None,
    ) -> None:
        """Update the authentication configuration.

        Note: The auth_config is stored directly on state for security,
        not serialized in the event.

        Args:
            auth_config: New authentication configuration
            updated_by: User who updated the config
        """
        self.state.auth_config = auth_config

        self.state.on(
            self.register_event(  # type: ignore
                SourceAuthUpdatedDomainEvent(
                    aggregate_id=self.id(),
                    auth_type=auth_config.auth_type,
                    updated_at=datetime.now(UTC),
                    updated_by=updated_by,
                )
            )
        )

    def mark_as_deleted(self, deleted_by: str | None = None) -> None:
        """Mark the source as deleted by registering a deregistration event.

        Args:
            deleted_by: User ID or identifier of who deleted the source
        """
        self.state.on(
            self.register_event(  # type: ignore
                SourceDeregisteredDomainEvent(
                    aggregate_id=self.id(),
                    name=self.state.name,
                    deregistered_at=datetime.now(UTC),
                    deregistered_by=deleted_by,
                )
            )
        )
