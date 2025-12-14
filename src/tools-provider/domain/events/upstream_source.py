"""Domain events for UpstreamSource aggregate.

These events represent state changes in the UpstreamSource lifecycle,
following the @cloudevent decorator pattern from Task events.
"""

from dataclasses import dataclass
from datetime import datetime

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent

from domain.enums import AuthMode, HealthStatus, SourceType


@cloudevent("source.registered.v1")
@dataclass
class SourceRegisteredDomainEvent(DomainEvent):
    """Event raised when a new upstream source is registered."""

    aggregate_id: str
    name: str
    url: str
    openapi_url: str | None  # URL to the OpenAPI specification (separate from base URL)
    source_type: SourceType
    created_at: datetime
    created_by: str | None
    default_audience: str | None  # Target audience for token exchange
    description: str | None  # Human-readable description of the source
    auth_mode: AuthMode  # Authentication mode for tool execution
    required_scopes: list[str]  # Scopes required for all tools from this source

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        url: str,
        source_type: SourceType,
        created_at: datetime,
        created_by: str | None = None,
        default_audience: str | None = None,
        openapi_url: str | None = None,
        description: str | None = None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        required_scopes: list[str] | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.url = url
        self.openapi_url = openapi_url
        self.source_type = source_type
        self.created_at = created_at
        self.created_by = created_by
        self.default_audience = default_audience
        self.description = description
        self.auth_mode = auth_mode
        self.required_scopes = required_scopes or []


@cloudevent("source.updated.v1")
@dataclass
class SourceUpdatedDomainEvent(DomainEvent):
    """Event raised when a source's editable fields are updated.

    Editable fields: name, description, url (service URL), required_scopes.
    Note: openapi_url is immutable after registration.
    """

    aggregate_id: str
    name: str | None
    description: str | None
    url: str | None  # Service URL (not the OpenAPI spec URL)
    required_scopes: list[str] | None  # Updated scopes for all tools from this source
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        updated_at: datetime,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
        required_scopes: list[str] | None = None,
        updated_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.description = description
        self.url = url
        self.required_scopes = required_scopes
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("source.inventory.ingested.v1")
@dataclass
class InventoryIngestedDomainEvent(DomainEvent):
    """Event raised when a source's tool inventory is successfully ingested.

    Contains the normalized tool definitions parsed from the upstream spec.
    """

    aggregate_id: str
    tools: list[dict]  # Serialized ToolDefinition objects
    inventory_hash: str
    tool_count: int
    ingested_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        tools: list[dict],
        inventory_hash: str,
        tool_count: int,
        ingested_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.tools = tools
        self.inventory_hash = inventory_hash
        self.tool_count = tool_count
        self.ingested_at = ingested_at


@cloudevent("source.sync.started.v1")
@dataclass
class SourceSyncStartedDomainEvent(DomainEvent):
    """Event raised when inventory sync begins."""

    aggregate_id: str
    started_at: datetime
    triggered_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        started_at: datetime,
        triggered_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.started_at = started_at
        self.triggered_by = triggered_by


@cloudevent("source.sync.failed.v1")
@dataclass
class SourceSyncFailedDomainEvent(DomainEvent):
    """Event raised when inventory sync fails."""

    aggregate_id: str
    error: str
    attempt: int
    failed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        error: str,
        attempt: int,
        failed_at: datetime,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.error = error
        self.attempt = attempt
        self.failed_at = failed_at


@cloudevent("source.health.changed.v1")
@dataclass
class SourceHealthChangedDomainEvent(DomainEvent):
    """Event raised when a source's health status changes."""

    aggregate_id: str
    old_status: HealthStatus
    new_status: HealthStatus
    reason: str | None
    changed_at: datetime

    def __init__(
        self,
        aggregate_id: str,
        old_status: HealthStatus,
        new_status: HealthStatus,
        changed_at: datetime,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.old_status = old_status
        self.new_status = new_status
        self.reason = reason
        self.changed_at = changed_at


@cloudevent("source.enabled.v1")
@dataclass
class SourceEnabledDomainEvent(DomainEvent):
    """Event raised when a source is enabled."""

    aggregate_id: str
    enabled_at: datetime
    enabled_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        enabled_at: datetime,
        enabled_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.enabled_at = enabled_at
        self.enabled_by = enabled_by


@cloudevent("source.disabled.v1")
@dataclass
class SourceDisabledDomainEvent(DomainEvent):
    """Event raised when a source is disabled."""

    aggregate_id: str
    disabled_at: datetime
    disabled_by: str | None
    reason: str | None

    def __init__(
        self,
        aggregate_id: str,
        disabled_at: datetime,
        disabled_by: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.disabled_at = disabled_at
        self.disabled_by = disabled_by
        self.reason = reason


@cloudevent("source.auth.updated.v1")
@dataclass
class SourceAuthUpdatedDomainEvent(DomainEvent):
    """Event raised when a source's authentication configuration is updated."""

    aggregate_id: str
    auth_type: str
    updated_at: datetime
    updated_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        auth_type: str,
        updated_at: datetime,
        updated_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.auth_type = auth_type
        self.updated_at = updated_at
        self.updated_by = updated_by


@cloudevent("source.deregistered.v1")
@dataclass
class SourceDeregisteredDomainEvent(DomainEvent):
    """Event raised when a source is removed from the system."""

    aggregate_id: str
    name: str
    deregistered_at: datetime
    deregistered_by: str | None

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        deregistered_at: datetime,
        deregistered_by: str | None = None,
    ) -> None:
        super().__init__(aggregate_id)
        self.aggregate_id = aggregate_id
        self.name = name
        self.deregistered_at = deregistered_at
        self.deregistered_by = deregistered_by
