"""Tests for SourceTool aggregate entity.

Tests cover:
- Entity creation (discovery) with defaults and custom values
- Domain event generation for all operations
- State transitions and invariants
- Enable/disable lifecycle
- Definition updates
- Deprecation and restoration
- Property accessors
"""

from datetime import datetime, timezone

import pytest

from domain.entities import SourceTool
from domain.enums import ToolStatus
from domain.events.source_tool import (
    SourceToolDefinitionUpdatedDomainEvent,
    SourceToolDeprecatedDomainEvent,
    SourceToolDisabledDomainEvent,
    SourceToolDiscoveredDomainEvent,
    SourceToolEnabledDomainEvent,
    SourceToolRestoredDomainEvent,
)
from domain.models import ToolDefinition
from tests.fixtures.factories import SourceToolFactory, ToolDefinitionFactory, UpstreamSourceFactory

# ============================================================================
# SOURCE TOOL CREATION (DISCOVERY) TESTS
# ============================================================================


class TestSourceToolCreation:
    """Test SourceTool aggregate creation (discovery)."""

    def test_create_tool_with_defaults(self) -> None:
        """Test creating tool with default values."""
        tool: SourceTool = SourceToolFactory.create()

        assert tool.state.tool_name == "Test Tool"
        assert tool.state.operation_id == "test_operation"
        assert tool.state.is_enabled is True
        assert tool.state.status == ToolStatus.ACTIVE
        assert tool.state.definition is not None

    def test_create_tool_with_custom_values(self) -> None:
        """Test creating tool with custom values."""
        source_id = "source-123"
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        definition = ToolDefinitionFactory.create_get_users()

        tool: SourceTool = SourceToolFactory.create(
            source_id=source_id,
            operation_id="get_users",
            tool_name="Get Users",
            definition=definition,
            discovered_at=custom_time,
        )

        assert tool.state.source_id == source_id
        assert tool.state.operation_id == "get_users"
        assert tool.state.tool_name == "Get Users"
        assert tool.state.discovered_at == custom_time
        assert tool.state.definition.name == "get_users"

    def test_create_tool_generates_discovered_event(self) -> None:
        """Test that tool creation generates SourceToolDiscoveredDomainEvent."""
        tool: SourceTool = SourceToolFactory.create()

        events = tool.domain_events
        assert len(events) == 1
        assert isinstance(events[0], SourceToolDiscoveredDomainEvent)

    def test_create_tool_discovered_event_contains_data(self) -> None:
        """Test that discovered event contains correct data."""
        source_id = "event-source-id"
        definition = ToolDefinitionFactory.create_create_user()

        tool: SourceTool = SourceToolFactory.create(
            source_id=source_id,
            operation_id="create_user",
            tool_name="Create User",
            definition=definition,
        )

        events = tool.domain_events
        event = events[0]

        assert isinstance(event, SourceToolDiscoveredDomainEvent)
        assert event.source_id == source_id
        assert event.operation_id == "create_user"
        assert event.tool_name == "Create User"
        assert event.definition is not None
        assert event.definition_hash is not None

    def test_create_tool_generates_composite_id(self) -> None:
        """Test that tool ID is in format source_id:operation_id."""
        source_id = "src-abc"

        tool: SourceTool = SourceToolFactory.create(
            source_id=source_id,
            operation_id="my_operation",
        )

        expected_id = f"{source_id}:my_operation"
        assert tool.state.id == expected_id
        assert tool.tool_id == expected_id

    def test_create_many_tools(self) -> None:
        """Test creating multiple tools with factory."""
        source_id = "shared-source"
        tools: list[SourceTool] = SourceToolFactory.create_many(3, source_id=source_id)

        assert len(tools) == 3
        assert tools[0].state.tool_name == "Test Tool 1"
        assert tools[1].state.tool_name == "Test Tool 2"
        assert tools[2].state.tool_name == "Test Tool 3"
        # All belong to same source
        assert all(t.state.source_id == source_id for t in tools)

    def test_create_tools_have_unique_ids(self) -> None:
        """Test that each created tool has a unique ID."""
        tools: list[SourceTool] = SourceToolFactory.create_many(5)
        ids = [tool.tool_id for tool in tools]

        assert len(set(ids)) == 5  # All unique


# ============================================================================
# ENABLE/DISABLE LIFECYCLE TESTS
# ============================================================================


class TestSourceToolLifecycle:
    """Test enable/disable lifecycle operations."""

    def test_disable_tool(self) -> None:
        """Test disabling a tool."""
        tool: SourceTool = SourceToolFactory.create()
        assert tool.state.is_enabled is True

        result = tool.disable(disabled_by="admin", reason="Security review")

        assert result is True
        assert tool.state.is_enabled is False
        assert tool.state.disabled_by == "admin"
        assert tool.state.disable_reason == "Security review"

    def test_disable_generates_event(self) -> None:
        """Test that disable generates domain event."""
        tool: SourceTool = SourceToolFactory.create()

        tool.disable()

        events = tool.domain_events
        assert len(events) == 2  # Discovered + Disabled
        assert isinstance(events[1], SourceToolDisabledDomainEvent)

    def test_disable_event_data(self) -> None:
        """Test disabled event contains correct data."""
        tool: SourceTool = SourceToolFactory.create()

        tool.disable(disabled_by="ops", reason="Deprecated endpoint")

        event = tool.domain_events[1]
        assert isinstance(event, SourceToolDisabledDomainEvent)
        assert event.disabled_by == "ops"
        assert event.reason == "Deprecated endpoint"

    def test_disable_already_disabled_returns_false(self) -> None:
        """Test that disabling already disabled tool returns False."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        result = tool.disable()

        assert result is False
        # Only 2 events: Discovered + first Disabled
        assert len(tool.domain_events) == 2

    def test_enable_tool(self) -> None:
        """Test enabling a disabled tool."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        result = tool.enable(enabled_by="admin")

        assert result is True
        assert tool.state.is_enabled is True
        assert tool.state.enabled_by == "admin"
        assert tool.state.disabled_by is None
        assert tool.state.disable_reason is None

    def test_enable_generates_event(self) -> None:
        """Test that enable generates domain event."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        tool.enable()

        events = tool.domain_events
        # Discovered + Disabled + Enabled
        assert len(events) == 3
        assert isinstance(events[2], SourceToolEnabledDomainEvent)

    def test_enable_event_data(self) -> None:
        """Test enabled event contains correct data."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        tool.enable(enabled_by="approver")

        event = tool.domain_events[2]
        assert isinstance(event, SourceToolEnabledDomainEvent)
        assert event.enabled_by == "approver"

    def test_enable_already_enabled_returns_false(self) -> None:
        """Test that enabling already enabled tool returns False."""
        tool: SourceTool = SourceToolFactory.create()

        result = tool.enable()

        assert result is False
        # Only discovery event
        assert len(tool.domain_events) == 1

    def test_enable_deprecated_tool_raises_error(self) -> None:
        """Test that enabling deprecated tool raises ValueError."""
        tool: SourceTool = SourceToolFactory.create_deprecated()

        with pytest.raises(ValueError, match="Cannot enable a deprecated tool"):
            tool.enable()


# ============================================================================
# DEFINITION UPDATE TESTS
# ============================================================================


class TestDefinitionUpdate:
    """Test tool definition update operations."""

    def test_update_definition(self) -> None:
        """Test updating tool definition."""
        tool: SourceTool = SourceToolFactory.create()
        original_hash = tool.state.definition_hash

        new_definition = ToolDefinitionFactory.create(
            name="updated_tool",
            description="Updated description",
            source_path="/api/v2/updated",
        )

        result = tool.update_definition(new_definition)

        assert result is True
        assert tool.state.definition_hash != original_hash
        assert tool.state.definition.name == "updated_tool"

    def test_update_definition_generates_event(self) -> None:
        """Test that definition update generates domain event."""
        tool: SourceTool = SourceToolFactory.create()

        new_definition = ToolDefinitionFactory.create(
            name="changed_tool",
            description="Changed",
        )
        tool.update_definition(new_definition)

        events = tool.domain_events
        assert len(events) == 2  # Discovered + DefinitionUpdated
        assert isinstance(events[1], SourceToolDefinitionUpdatedDomainEvent)

    def test_update_definition_event_data(self) -> None:
        """Test definition updated event contains correct data."""
        tool: SourceTool = SourceToolFactory.create()
        original_hash = tool.state.definition_hash

        new_definition = ToolDefinitionFactory.create(
            name="event_data_tool",
            source_path="/api/event",
        )
        tool.update_definition(new_definition)

        event = tool.domain_events[1]
        assert isinstance(event, SourceToolDefinitionUpdatedDomainEvent)
        assert event.old_definition_hash == original_hash
        assert event.new_definition_hash != original_hash
        assert event.new_definition is not None

    def test_update_definition_unchanged_returns_false(self) -> None:
        """Test that updating with same definition returns False."""
        definition = ToolDefinitionFactory.create(name="stable_tool")
        tool: SourceTool = SourceToolFactory.create(definition=definition)

        # Use same definition (same hash)
        result = tool.update_definition(definition)

        assert result is False
        # Only discovery event
        assert len(tool.domain_events) == 1

    def test_update_definition_updates_last_seen(self) -> None:
        """Test that definition update updates last_seen_at."""
        tool: SourceTool = SourceToolFactory.create()
        original_last_seen = tool.state.last_seen_at

        # Small delay to ensure time difference
        new_definition = ToolDefinitionFactory.create(name="new_def")
        tool.update_definition(new_definition)

        # last_seen should be updated
        assert tool.state.last_seen_at >= original_last_seen


# ============================================================================
# DEPRECATION TESTS
# ============================================================================


class TestDeprecation:
    """Test tool deprecation operations."""

    def test_deprecate_tool(self) -> None:
        """Test deprecating a tool."""
        tool: SourceTool = SourceToolFactory.create()

        result = tool.deprecate()

        assert result is True
        assert tool.state.status == ToolStatus.DEPRECATED
        assert tool.state.is_enabled is False

    def test_deprecate_generates_event(self) -> None:
        """Test that deprecation generates domain event."""
        tool: SourceTool = SourceToolFactory.create()

        tool.deprecate()

        events = tool.domain_events
        assert len(events) == 2  # Discovered + Deprecated
        assert isinstance(events[1], SourceToolDeprecatedDomainEvent)

    def test_deprecate_event_data(self) -> None:
        """Test deprecated event contains correct data."""
        tool: SourceTool = SourceToolFactory.create()

        tool.deprecate()

        event = tool.domain_events[1]
        assert isinstance(event, SourceToolDeprecatedDomainEvent)
        assert event.deprecated_at is not None
        assert event.last_seen_at is not None

    def test_deprecate_already_deprecated_returns_false(self) -> None:
        """Test that deprecating already deprecated tool returns False."""
        tool: SourceTool = SourceToolFactory.create_deprecated()

        result = tool.deprecate()

        assert result is False
        # Only 2 events: Discovered + first Deprecated
        assert len(tool.domain_events) == 2

    def test_deprecation_disables_tool(self) -> None:
        """Test that deprecation automatically disables the tool."""
        tool: SourceTool = SourceToolFactory.create()
        assert tool.state.is_enabled is True

        tool.deprecate()

        assert tool.state.is_enabled is False


# ============================================================================
# RESTORATION TESTS
# ============================================================================


class TestRestoration:
    """Test tool restoration operations."""

    def test_restore_deprecated_tool(self) -> None:
        """Test restoring a deprecated tool."""
        tool: SourceTool = SourceToolFactory.create_deprecated()
        new_definition = ToolDefinitionFactory.create(name="restored_tool")

        result = tool.restore(new_definition)

        assert result is True
        assert tool.state.status == ToolStatus.ACTIVE
        assert tool.state.is_enabled is True
        assert tool.state.definition.name == "restored_tool"

    def test_restore_generates_event(self) -> None:
        """Test that restoration generates domain event."""
        tool: SourceTool = SourceToolFactory.create_deprecated()
        new_definition = ToolDefinitionFactory.create(name="back_online")

        tool.restore(new_definition)

        events = tool.domain_events
        # Discovered + Deprecated + Restored
        assert len(events) == 3
        assert isinstance(events[2], SourceToolRestoredDomainEvent)

    def test_restore_event_data(self) -> None:
        """Test restored event contains correct data."""
        tool: SourceTool = SourceToolFactory.create_deprecated()
        new_definition = ToolDefinitionFactory.create(
            name="event_restore",
            source_path="/api/restored",
        )

        tool.restore(new_definition)

        event = tool.domain_events[2]
        assert isinstance(event, SourceToolRestoredDomainEvent)
        assert event.restored_at is not None
        assert event.new_definition is not None
        assert event.new_definition_hash is not None

    def test_restore_active_tool_returns_false(self) -> None:
        """Test that restoring active tool returns False."""
        tool: SourceTool = SourceToolFactory.create()
        new_definition = ToolDefinitionFactory.create()

        result = tool.restore(new_definition)

        assert result is False
        # Only discovery event
        assert len(tool.domain_events) == 1


# ============================================================================
# MARK SEEN TESTS
# ============================================================================


class TestMarkSeen:
    """Test mark_seen operation."""

    def test_mark_seen_updates_last_seen(self) -> None:
        """Test that mark_seen updates last_seen_at."""
        tool: SourceTool = SourceToolFactory.create()
        original_last_seen = tool.state.last_seen_at

        tool.mark_seen()

        # last_seen should be updated
        assert tool.state.last_seen_at >= original_last_seen

    def test_mark_seen_does_not_emit_event(self) -> None:
        """Test that mark_seen does not emit domain event."""
        tool: SourceTool = SourceToolFactory.create()
        initial_event_count = len(tool.domain_events)

        tool.mark_seen()

        # No new events
        assert len(tool.domain_events) == initial_event_count


# ============================================================================
# PROPERTY ACCESSOR TESTS
# ============================================================================


class TestPropertyAccessors:
    """Test property accessor methods."""

    def test_tool_id_property(self) -> None:
        """Test tool_id property returns correct ID."""
        tool: SourceTool = SourceToolFactory.create(
            source_id="prop-source",
            operation_id="prop_op",
        )

        assert tool.tool_id == "prop-source:prop_op"

    def test_source_id_property(self) -> None:
        """Test source_id property returns correct source ID."""
        tool: SourceTool = SourceToolFactory.create(source_id="my-source-id")

        assert tool.source_id == "my-source-id"

    def test_is_available_active_enabled(self) -> None:
        """Test is_available is True when active and enabled."""
        tool: SourceTool = SourceToolFactory.create()

        assert tool.is_available is True

    def test_is_available_false_when_disabled(self) -> None:
        """Test is_available is False when disabled."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        assert tool.is_available is False

    def test_is_available_false_when_deprecated(self) -> None:
        """Test is_available is False when deprecated."""
        tool: SourceTool = SourceToolFactory.create_deprecated()

        assert tool.is_available is False

    def test_definition_property(self) -> None:
        """Test definition property returns ToolDefinition."""
        definition = ToolDefinitionFactory.create_get_users()
        tool: SourceTool = SourceToolFactory.create(definition=definition)

        assert tool.definition is not None
        assert tool.definition.name == "get_users"

    def test_is_enabled_property(self) -> None:
        """Test is_enabled property."""
        tool: SourceTool = SourceToolFactory.create()
        assert tool.is_enabled is True

        tool.disable()
        assert tool.is_enabled is False

    def test_is_deprecated_property(self) -> None:
        """Test is_deprecated property."""
        tool: SourceTool = SourceToolFactory.create()
        assert tool.is_deprecated is False

        tool.deprecate()
        assert tool.is_deprecated is True


# ============================================================================
# STATIC METHOD TESTS
# ============================================================================


class TestStaticMethods:
    """Test static utility methods."""

    def test_create_tool_id(self) -> None:
        """Test create_tool_id static method."""
        tool_id = SourceTool.create_tool_id("source-abc", "operation-xyz")

        assert tool_id == "source-abc:operation-xyz"

    def test_compute_definition_hash(self) -> None:
        """Test compute_definition_hash static method."""
        definition = ToolDefinitionFactory.create(name="hash_test")

        hash_value = SourceTool.compute_definition_hash(definition)

        assert hash_value is not None
        assert len(hash_value) == 16  # SHA-256 truncated to 16 chars

    def test_compute_definition_hash_deterministic(self) -> None:
        """Test that hash is deterministic for same definition."""
        definition = ToolDefinitionFactory.create(
            name="deterministic",
            source_path="/api/same",
        )

        hash1 = SourceTool.compute_definition_hash(definition)
        hash2 = SourceTool.compute_definition_hash(definition)

        assert hash1 == hash2

    def test_compute_definition_hash_different_for_different_definitions(self) -> None:
        """Test that hash differs for different definitions."""
        def1 = ToolDefinitionFactory.create(name="tool_a")
        def2 = ToolDefinitionFactory.create(name="tool_b")

        hash1 = SourceTool.compute_definition_hash(def1)
        hash2 = SourceTool.compute_definition_hash(def2)

        assert hash1 != hash2


# ============================================================================
# FACTORY UTILITY TESTS
# ============================================================================


class TestSourceToolFactory:
    """Test SourceToolFactory utility methods."""

    def test_create_disabled_tool(self) -> None:
        """Test creating disabled tool with factory."""
        tool: SourceTool = SourceToolFactory.create_disabled()

        assert tool.state.is_enabled is False
        assert tool.state.disable_reason == "Testing disabled state"
        # Has both discovery and disabled events
        assert len(tool.domain_events) == 2

    def test_create_deprecated_tool(self) -> None:
        """Test creating deprecated tool with factory."""
        tool: SourceTool = SourceToolFactory.create_deprecated()

        assert tool.state.status == ToolStatus.DEPRECATED
        assert tool.state.is_enabled is False
        # Has both discovery and deprecated events
        assert len(tool.domain_events) == 2

    def test_create_for_source(self) -> None:
        """Test creating tool linked to specific source."""
        source = UpstreamSourceFactory.create()

        tool: SourceTool = SourceToolFactory.create_for_source(source)

        assert tool.state.source_id == source.id()


# ============================================================================
# DELETION TESTS
# ============================================================================


class TestMarkAsDeleted:
    """Test mark_as_deleted method for hard deletion."""

    def test_mark_as_deleted_returns_true(self) -> None:
        """Test mark_as_deleted always returns True."""
        tool: SourceTool = SourceToolFactory.create()

        result = tool.mark_as_deleted()

        assert result is True

    def test_mark_as_deleted_generates_event(self) -> None:
        """Test mark_as_deleted generates SourceToolDeletedDomainEvent."""
        from domain.events.source_tool import SourceToolDeletedDomainEvent

        tool: SourceTool = SourceToolFactory.create()
        initial_event_count = len(tool.domain_events)

        tool.mark_as_deleted()

        assert len(tool.domain_events) == initial_event_count + 1
        deleted_event = tool.domain_events[-1]
        assert isinstance(deleted_event, SourceToolDeletedDomainEvent)

    def test_mark_as_deleted_event_data(self) -> None:
        """Test deleted event contains correct data."""
        from domain.events.source_tool import SourceToolDeletedDomainEvent

        tool: SourceTool = SourceToolFactory.create(source_id="del-source", operation_id="del_op")

        tool.mark_as_deleted(deleted_by="admin123", reason="Security issue")

        deleted_event = tool.domain_events[-1]
        assert isinstance(deleted_event, SourceToolDeletedDomainEvent)
        assert deleted_event.aggregate_id == "del-source:del_op"
        assert deleted_event.deleted_by == "admin123"
        assert deleted_event.reason == "Security issue"
        assert deleted_event.deleted_at is not None

    def test_mark_as_deleted_updates_state(self) -> None:
        """Test that mark_as_deleted updates state to deprecated/disabled."""
        tool: SourceTool = SourceToolFactory.create()
        assert tool.state.status == ToolStatus.ACTIVE
        assert tool.state.is_enabled is True

        tool.mark_as_deleted()

        assert tool.state.status == ToolStatus.DEPRECATED
        assert tool.state.is_enabled is False

    def test_mark_as_deleted_without_user(self) -> None:
        """Test mark_as_deleted without user context."""
        from domain.events.source_tool import SourceToolDeletedDomainEvent

        tool: SourceTool = SourceToolFactory.create()

        tool.mark_as_deleted()

        deleted_event = tool.domain_events[-1]
        assert isinstance(deleted_event, SourceToolDeletedDomainEvent)
        assert deleted_event.deleted_by is None
        assert deleted_event.reason is None
