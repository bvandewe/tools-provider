"""Tests for UpstreamSource aggregate entity.

Tests cover:
- Entity creation with defaults and custom values
- Domain event generation for all operations
- State transitions and invariants
- Inventory management
- Health status changes
- Enable/disable lifecycle
"""

from datetime import UTC, datetime, timezone

import pytest

from domain.entities import UpstreamSource
from domain.enums import HealthStatus, SourceType
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
)
from domain.models import AuthConfig, ToolDefinition
from tests.fixtures.factories import AuthConfigFactory, ToolDefinitionFactory, UpstreamSourceFactory

# ============================================================================
# UPSTREAM SOURCE CREATION TESTS
# ============================================================================


class TestUpstreamSourceCreation:
    """Test UpstreamSource aggregate creation."""

    def test_create_source_with_defaults(self) -> None:
        """Test creating source with default values."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        assert source.state.name == "Test API"
        assert source.state.url == "https://api.example.com/openapi.json"
        assert source.state.source_type == SourceType.OPENAPI
        assert source.state.is_enabled is True
        assert source.state.health_status == HealthStatus.UNKNOWN
        assert source.state.auth_config is None

    def test_create_source_with_custom_values(self) -> None:
        """Test creating source with custom values."""
        custom_id = "custom-source-id"
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        source: UpstreamSource = UpstreamSourceFactory.create(
            source_id=custom_id,
            name="My Custom API",
            url="https://custom.api.io/spec.yaml",
            source_type=SourceType.WORKFLOW,
            created_at=custom_time,
            created_by="user123",
        )

        assert source.id() == custom_id
        assert source.state.name == "My Custom API"
        assert source.state.url == "https://custom.api.io/spec.yaml"
        assert source.state.source_type == SourceType.WORKFLOW
        assert source.state.created_at == custom_time
        assert source.state.created_by == "user123"

    def test_create_source_generates_registered_event(self) -> None:
        """Test that source creation generates SourceRegisteredDomainEvent."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        events = source.domain_events
        assert len(events) == 1
        assert isinstance(events[0], SourceRegisteredDomainEvent)

    def test_create_source_registered_event_contains_data(self) -> None:
        """Test that registration event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create(
            name="Event Data API",
            url="https://event.example.com/api",
            source_type=SourceType.OPENAPI,
            created_by="creator-user",
        )

        events = source.domain_events
        event = events[0]

        assert isinstance(event, SourceRegisteredDomainEvent)
        assert event.name == "Event Data API"
        assert event.url == "https://event.example.com/api"
        assert event.source_type == SourceType.OPENAPI
        assert event.created_by == "creator-user"

    def test_create_source_with_auth_config(self) -> None:
        """Test creating source with authentication configuration."""
        auth_config = AuthConfigFactory.create_bearer()

        source: UpstreamSource = UpstreamSourceFactory.create(auth_config=auth_config)

        assert source.state.auth_config is not None
        assert source.state.auth_config.auth_type == "bearer"

    def test_create_many_sources(self) -> None:
        """Test creating multiple sources with factory."""
        sources: list[UpstreamSource] = UpstreamSourceFactory.create_many(3)

        assert len(sources) == 3
        assert sources[0].state.name == "Test API 1"
        assert sources[1].state.name == "Test API 2"
        assert sources[2].state.name == "Test API 3"

    def test_create_sources_have_unique_ids(self) -> None:
        """Test that each created source has a unique ID."""
        sources: list[UpstreamSource] = UpstreamSourceFactory.create_many(5)
        ids = [source.id() for source in sources]

        assert len(set(ids)) == 5  # All unique


# ============================================================================
# INVENTORY MANAGEMENT TESTS
# ============================================================================


class TestInventoryManagement:
    """Test inventory update operations."""

    def test_update_inventory_success(self) -> None:
        """Test successful inventory update."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        tools = ToolDefinitionFactory.create_many(3)

        result = source.update_inventory(tools, "hash-abc123")

        assert result is True
        assert source.state.inventory_hash == "hash-abc123"
        assert source.state.inventory_count == 3

    def test_update_inventory_generates_event(self) -> None:
        """Test that inventory update generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        tools = ToolDefinitionFactory.create_many(2)

        source.update_inventory(tools, "new-hash-xyz")

        events = source.domain_events
        assert len(events) == 2  # Registration + Ingested
        assert isinstance(events[1], InventoryIngestedDomainEvent)

    def test_update_inventory_event_contains_data(self) -> None:
        """Test that inventory event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        tools = [ToolDefinitionFactory.create_get_users()]

        source.update_inventory(tools, "users-hash")

        event = source.domain_events[1]
        assert isinstance(event, InventoryIngestedDomainEvent)
        assert event.inventory_hash == "users-hash"
        assert event.tool_count == 1
        assert len(event.tools) == 1

    def test_update_inventory_unchanged_hash_returns_false(self) -> None:
        """Test that updating with same hash returns False."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        tools = ToolDefinitionFactory.create_many(2)

        source.update_inventory(tools, "same-hash")
        result = source.update_inventory(tools, "same-hash")

        assert result is False
        # Only 2 events: Registration + first Ingested
        assert len(source.domain_events) == 2

    def test_update_inventory_updates_health_to_healthy(self) -> None:
        """Test that successful inventory update sets health to HEALTHY."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        tools = ToolDefinitionFactory.create_many(1)

        source.update_inventory(tools, "hash-1")

        assert source.state.health_status == HealthStatus.HEALTHY

    def test_update_inventory_clears_failure_state(self) -> None:
        """Test that successful update clears consecutive failures."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        # Simulate failures
        source.mark_sync_failed("Error 1")
        source.mark_sync_failed("Error 2")
        assert source.state.consecutive_failures == 2

        # Successful update should clear failures
        tools = ToolDefinitionFactory.create_many(1)
        source.update_inventory(tools, "success-hash")

        assert source.state.consecutive_failures == 0
        assert source.state.last_sync_error is None


# ============================================================================
# SYNC STARTED/FAILED TESTS
# ============================================================================


class TestSyncOperations:
    """Test sync started and failed operations."""

    def test_mark_sync_started(self) -> None:
        """Test marking sync as started."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_started(triggered_by="scheduler")

        events = source.domain_events
        assert len(events) == 2  # Registration + SyncStarted
        assert isinstance(events[1], SourceSyncStartedDomainEvent)

    def test_mark_sync_started_event_data(self) -> None:
        """Test sync started event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_started(triggered_by="manual-trigger")

        event = source.domain_events[1]
        assert isinstance(event, SourceSyncStartedDomainEvent)
        assert event.triggered_by == "manual-trigger"
        assert event.started_at is not None

    def test_mark_sync_failed(self) -> None:
        """Test marking sync as failed."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_failed("Connection timeout")

        assert source.state.last_sync_error == "Connection timeout"
        assert source.state.consecutive_failures == 1

    def test_mark_sync_failed_generates_event(self) -> None:
        """Test that sync failure generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_failed("HTTP 500 error")

        events = source.domain_events
        assert len(events) == 2  # Registration + SyncFailed
        assert isinstance(events[1], SourceSyncFailedDomainEvent)

    def test_mark_sync_failed_increments_counter(self) -> None:
        """Test that consecutive failures increment."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_failed("Error 1")
        assert source.state.consecutive_failures == 1

        source.mark_sync_failed("Error 2")
        assert source.state.consecutive_failures == 2

        source.mark_sync_failed("Error 3")
        assert source.state.consecutive_failures == 3

    def test_mark_sync_failed_degrades_health(self) -> None:
        """Test that failures degrade health status."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_failed("Error 1")
        assert source.state.health_status == HealthStatus.DEGRADED

    def test_mark_sync_failed_unhealthy_after_3_failures(self) -> None:
        """Test that 3+ failures set health to UNHEALTHY."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_sync_failed("Error 1")
        source.mark_sync_failed("Error 2")
        source.mark_sync_failed("Error 3")

        assert source.state.health_status == HealthStatus.UNHEALTHY


# ============================================================================
# HEALTH STATUS TESTS
# ============================================================================


class TestHealthStatus:
    """Test health status update operations."""

    def test_update_health_status(self) -> None:
        """Test updating health status."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        result = source.update_health_status(HealthStatus.HEALTHY, reason="All good")

        assert result is True
        assert source.state.health_status == HealthStatus.HEALTHY

    def test_update_health_status_generates_event(self) -> None:
        """Test that health update generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.update_health_status(HealthStatus.DEGRADED, reason="Slow response")

        events = source.domain_events
        assert len(events) == 2  # Registration + HealthChanged
        assert isinstance(events[1], SourceHealthChangedDomainEvent)

    def test_update_health_status_event_data(self) -> None:
        """Test health changed event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.update_health_status(HealthStatus.UNHEALTHY, reason="Service down")

        event = source.domain_events[1]
        assert isinstance(event, SourceHealthChangedDomainEvent)
        assert event.old_status == HealthStatus.UNKNOWN
        assert event.new_status == HealthStatus.UNHEALTHY
        assert event.reason == "Service down"

    def test_update_health_status_unchanged_returns_false(self) -> None:
        """Test that updating to same status returns False."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        # Initial status is UNKNOWN
        result = source.update_health_status(HealthStatus.UNKNOWN)

        assert result is False
        # Only registration event
        assert len(source.domain_events) == 1


# ============================================================================
# ENABLE/DISABLE LIFECYCLE TESTS
# ============================================================================


class TestSourceLifecycle:
    """Test enable/disable lifecycle operations."""

    def test_disable_source(self) -> None:
        """Test disabling a source."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        assert source.state.is_enabled is True

        result = source.disable(disabled_by="admin", reason="Maintenance")

        assert result is True
        assert source.state.is_enabled is False

    def test_disable_generates_event(self) -> None:
        """Test that disable generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.disable()

        events = source.domain_events
        assert len(events) == 2  # Registration + Disabled
        assert isinstance(events[1], SourceDisabledDomainEvent)

    def test_disable_event_data(self) -> None:
        """Test disabled event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.disable(disabled_by="admin-user", reason="Security concern")

        event = source.domain_events[1]
        assert isinstance(event, SourceDisabledDomainEvent)
        assert event.disabled_by == "admin-user"
        assert event.reason == "Security concern"

    def test_disable_already_disabled_returns_false(self) -> None:
        """Test that disabling already disabled source returns False."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        source.disable()

        result = source.disable()

        assert result is False
        # Only 2 events: Registration + first Disabled
        assert len(source.domain_events) == 2

    def test_enable_source(self) -> None:
        """Test enabling a disabled source."""
        source: UpstreamSource = UpstreamSourceFactory.create_disabled()

        result = source.enable(enabled_by="admin")

        assert result is True
        assert source.state.is_enabled is True

    def test_enable_generates_event(self) -> None:
        """Test that enable generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create_disabled()

        source.enable()

        events = source.domain_events
        # Registration + Disabled + Enabled
        assert len(events) == 3
        assert isinstance(events[2], SourceEnabledDomainEvent)

    def test_enable_event_data(self) -> None:
        """Test enabled event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create_disabled()

        source.enable(enabled_by="ops-team")

        event = source.domain_events[2]
        assert isinstance(event, SourceEnabledDomainEvent)
        assert event.enabled_by == "ops-team"

    def test_enable_already_enabled_returns_false(self) -> None:
        """Test that enabling already enabled source returns False."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        result = source.enable()

        assert result is False
        # Only registration event
        assert len(source.domain_events) == 1


# ============================================================================
# AUTH CONFIG UPDATE TESTS
# ============================================================================


class TestAuthConfigUpdate:
    """Test authentication configuration update operations."""

    def test_update_auth_config(self) -> None:
        """Test updating auth configuration."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        new_auth = AuthConfigFactory.create_bearer()

        source.update_auth_config(new_auth, updated_by="admin")

        assert source.state.auth_config is not None
        assert source.state.auth_config.auth_type == "bearer"

    def test_update_auth_config_generates_event(self) -> None:
        """Test that auth update generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        new_auth = AuthConfigFactory.create_oauth2()

        source.update_auth_config(new_auth)

        events = source.domain_events
        assert len(events) == 2  # Registration + AuthUpdated
        assert isinstance(events[1], SourceAuthUpdatedDomainEvent)

    def test_update_auth_config_event_data(self) -> None:
        """Test auth updated event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create()
        new_auth = AuthConfigFactory.create_api_key()

        source.update_auth_config(new_auth, updated_by="security-team")

        event = source.domain_events[1]
        assert isinstance(event, SourceAuthUpdatedDomainEvent)
        assert event.auth_type == "api_key"
        assert event.updated_by == "security-team"

    def test_replace_existing_auth_config(self) -> None:
        """Test replacing existing auth configuration."""
        source: UpstreamSource = UpstreamSourceFactory.create_with_auth("bearer")
        assert source.state.auth_config.auth_type == "bearer"

        new_auth = AuthConfigFactory.create_oauth2()
        source.update_auth_config(new_auth)

        assert source.state.auth_config.auth_type == "oauth2"


# ============================================================================
# MARK AS DELETED TESTS
# ============================================================================


class TestMarkAsDeleted:
    """Test mark as deleted (deregistration) operations."""

    def test_mark_as_deleted(self) -> None:
        """Test marking source as deleted."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_as_deleted(deleted_by="admin")

        assert source.state.is_enabled is False

    def test_mark_as_deleted_generates_event(self) -> None:
        """Test that deletion generates domain event."""
        source: UpstreamSource = UpstreamSourceFactory.create()

        source.mark_as_deleted()

        events = source.domain_events
        assert len(events) == 2  # Registration + Deregistered
        assert isinstance(events[1], SourceDeregisteredDomainEvent)

    def test_mark_as_deleted_event_data(self) -> None:
        """Test deregistered event contains correct data."""
        source: UpstreamSource = UpstreamSourceFactory.create(name="API to Delete")

        source.mark_as_deleted(deleted_by="cleanup-service")

        event = source.domain_events[1]
        assert isinstance(event, SourceDeregisteredDomainEvent)
        assert event.name == "API to Delete"
        assert event.deregistered_by == "cleanup-service"


# ============================================================================
# FACTORY UTILITY TESTS
# ============================================================================


class TestUpstreamSourceFactory:
    """Test UpstreamSourceFactory utility methods."""

    def test_create_openapi_source(self) -> None:
        """Test creating OpenAPI source with factory."""
        source: UpstreamSource = UpstreamSourceFactory.create_openapi()

        assert source.state.source_type == SourceType.OPENAPI

    def test_create_workflow_source(self) -> None:
        """Test creating Workflow source with factory."""
        source: UpstreamSource = UpstreamSourceFactory.create_workflow()

        assert source.state.source_type == SourceType.WORKFLOW

    def test_create_with_auth(self) -> None:
        """Test creating source with auth using factory."""
        source: UpstreamSource = UpstreamSourceFactory.create_with_auth("bearer")

        assert source.state.auth_config is not None

    def test_create_disabled(self) -> None:
        """Test creating disabled source with factory."""
        source: UpstreamSource = UpstreamSourceFactory.create_disabled()

        assert source.state.is_enabled is False
        # Has both registration and disabled events
        assert len(source.domain_events) == 2
