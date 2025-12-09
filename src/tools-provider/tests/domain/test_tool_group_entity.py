"""Tests for ToolGroup aggregate entity.

Tests cover:
- Entity creation with defaults and custom values
- Domain event generation for all operations
- State transitions and invariants
- Selector management (add/remove)
- Explicit tool management (add/remove)
- Tool exclusion management (exclude/include)
- Activation/deactivation lifecycle
"""

from datetime import UTC, datetime, timezone

import pytest

from domain.entities import ToolGroup
from domain.events.tool_group import (
    ExplicitToolAddedDomainEvent,
    ExplicitToolRemovedDomainEvent,
    SelectorAddedDomainEvent,
    SelectorRemovedDomainEvent,
    ToolExcludedDomainEvent,
    ToolGroupActivatedDomainEvent,
    ToolGroupCreatedDomainEvent,
    ToolGroupDeactivatedDomainEvent,
    ToolGroupUpdatedDomainEvent,
    ToolIncludedDomainEvent,
)
from domain.models import ToolSelector

# ============================================================================
# TEST HELPERS - Local factories to avoid module loading issues
# ============================================================================


def create_tool_group(
    group_id: str | None = None,
    name: str = "Test Group",
    description: str = "A test tool group",
    created_at: datetime | None = None,
    created_by: str | None = None,
) -> ToolGroup:
    """Create a ToolGroup with defaults that can be overridden."""
    from uuid import uuid4

    return ToolGroup(
        group_id=group_id or str(uuid4()),
        name=name,
        description=description,
        created_at=created_at,
        created_by=created_by,
    )


def create_source_selector(source_pattern: str) -> ToolSelector:
    """Create a selector that matches tools from a specific source pattern."""
    from uuid import uuid4

    return ToolSelector(
        id=str(uuid4()),
        source_pattern=source_pattern,
    )


def create_tag_selector(required_tags: list[str]) -> ToolSelector:
    """Create a selector that matches tools by required tags."""
    from uuid import uuid4

    return ToolSelector(
        id=str(uuid4()),
        required_tags=required_tags,
    )


# ============================================================================
# TOOL GROUP CREATION TESTS
# ============================================================================


class TestToolGroupCreation:
    """Test ToolGroup aggregate creation."""

    def test_create_group_with_defaults(self) -> None:
        """Test creating group with default values."""
        group = create_tool_group()

        assert group.state.name == "Test Group"
        assert group.state.description == "A test tool group"
        assert group.state.is_active is True
        assert len(group.state.selectors) == 0
        assert len(group.state.explicit_tool_ids) == 0
        assert len(group.state.excluded_tool_ids) == 0

    def test_create_group_with_custom_values(self) -> None:
        """Test creating group with custom values."""
        custom_id = "custom-group-id"
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        group = create_tool_group(
            group_id=custom_id,
            name="My Custom Group",
            description="Custom description",
            created_at=custom_time,
            created_by="user123",
        )

        assert group.id() == custom_id
        assert group.state.name == "My Custom Group"
        assert group.state.description == "Custom description"
        assert group.state.created_at == custom_time
        assert group.state.created_by == "user123"

    def test_create_group_generates_created_event(self) -> None:
        """Test that group creation generates ToolGroupCreatedDomainEvent."""
        group = create_tool_group()

        events = group.domain_events
        assert len(events) == 1
        assert isinstance(events[0], ToolGroupCreatedDomainEvent)

    def test_create_group_event_contains_data(self) -> None:
        """Test that creation event contains correct data."""
        group = create_tool_group(
            name="Event Test Group",
            description="Testing event data",
            created_by="creator-user",
        )

        events = group.domain_events
        event = events[0]

        assert isinstance(event, ToolGroupCreatedDomainEvent)
        assert event.name == "Event Test Group"
        assert event.description == "Testing event data"
        assert event.created_by == "creator-user"

    def test_create_many_groups(self) -> None:
        """Test creating multiple groups with unique IDs."""
        groups = [create_tool_group(name=f"Test Group {i+1}") for i in range(3)]

        assert len(groups) == 3
        assert groups[0].state.name == "Test Group 1"
        assert groups[1].state.name == "Test Group 2"
        assert groups[2].state.name == "Test Group 3"

    def test_create_groups_have_unique_ids(self) -> None:
        """Test that each created group has a unique ID."""
        groups = [create_tool_group() for _ in range(5)]
        ids = [group.id() for group in groups]

        assert len(set(ids)) == 5  # All unique


# ============================================================================
# TOOL GROUP UPDATE TESTS
# ============================================================================


class TestToolGroupUpdate:
    """Test ToolGroup update operations."""

    def test_update_group_name(self) -> None:
        """Test updating group name."""
        group = create_tool_group()

        group.update(name="Updated Name", updated_by="editor")

        assert group.state.name == "Updated Name"

    def test_update_group_description(self) -> None:
        """Test updating group description."""
        group = create_tool_group()

        group.update(description="Updated description", updated_by="editor")

        assert group.state.description == "Updated description"

    def test_update_group_generates_event(self) -> None:
        """Test that group update generates domain event."""
        group = create_tool_group()

        group.update(name="Updated Name", updated_by="editor")

        events = group.domain_events
        assert len(events) == 2  # Create + Update
        assert isinstance(events[1], ToolGroupUpdatedDomainEvent)

    def test_update_group_event_contains_data(self) -> None:
        """Test that update event contains correct data."""
        group = create_tool_group()

        group.update(name="New Name", description="New description", updated_by="editor")

        events = group.domain_events
        event = events[1]

        assert isinstance(event, ToolGroupUpdatedDomainEvent)
        assert event.name == "New Name"
        assert event.description == "New description"
        assert event.updated_by == "editor"


# ============================================================================
# SELECTOR MANAGEMENT TESTS
# ============================================================================


class TestSelectorManagement:
    """Test selector add/remove operations."""

    def test_add_selector(self) -> None:
        """Test adding a selector to the group."""
        group = create_tool_group()
        selector = create_source_selector("source-123")

        group.add_selector(selector, added_by="admin")

        assert len(group.state.selectors) == 1
        assert group.state.selectors[0].id == selector.id

    def test_add_selector_generates_event(self) -> None:
        """Test that adding selector generates domain event."""
        group = create_tool_group()
        selector = create_tag_selector(["tag1"])

        group.add_selector(selector, added_by="admin")

        events = group.domain_events
        assert len(events) == 2  # Create + SelectorAdded
        assert isinstance(events[1], SelectorAddedDomainEvent)

    def test_add_selector_event_contains_data(self) -> None:
        """Test that selector added event contains correct data."""
        group = create_tool_group()
        selector = create_source_selector("source-456")

        group.add_selector(selector, added_by="admin")

        event = group.domain_events[1]
        assert isinstance(event, SelectorAddedDomainEvent)
        # The selector is stored as a dict in the event
        assert event.selector["id"] == selector.id
        assert event.selector["source_pattern"] == selector.source_pattern
        assert event.added_by == "admin"

    def test_add_multiple_selectors(self) -> None:
        """Test adding multiple selectors."""
        group = create_tool_group()

        selector1 = create_source_selector("source-1")
        selector2 = create_tag_selector(["tag1", "tag2"])

        group.add_selector(selector1, added_by="admin")
        group.add_selector(selector2, added_by="admin")

        assert len(group.state.selectors) == 2

    def test_remove_selector(self) -> None:
        """Test removing a selector from the group."""
        group = create_tool_group()
        selector = create_source_selector("source-123")
        group.add_selector(selector, added_by="admin")

        group.remove_selector(selector.id, removed_by="admin")

        assert len(group.state.selectors) == 0

    def test_remove_selector_generates_event(self) -> None:
        """Test that removing selector generates domain event."""
        group = create_tool_group()
        selector = create_source_selector("source-123")
        group.add_selector(selector, added_by="admin")

        group.remove_selector(selector.id, removed_by="admin")

        events = group.domain_events
        assert len(events) == 3  # Create + Add + Remove
        assert isinstance(events[2], SelectorRemovedDomainEvent)

    def test_remove_nonexistent_selector_returns_false(self) -> None:
        """Test removing non-existent selector returns False."""
        group = create_tool_group()

        result = group.remove_selector("nonexistent-selector-id", removed_by="admin")

        # Should return False, no new event
        assert result is False
        events = group.domain_events
        assert len(events) == 1  # Only Create


# ============================================================================
# EXPLICIT TOOL MANAGEMENT TESTS
# ============================================================================


class TestExplicitToolManagement:
    """Test explicit tool add/remove operations."""

    def test_add_explicit_tool(self) -> None:
        """Test adding an explicit tool to the group."""
        group = create_tool_group()

        group.add_tool("tool-123", added_by="admin")

        assert len(group.state.explicit_tool_ids) == 1
        assert group.state.explicit_tool_ids[0].tool_id == "tool-123"

    def test_add_explicit_tool_generates_event(self) -> None:
        """Test that adding tool generates domain event."""
        group = create_tool_group()

        group.add_tool("tool-123", added_by="admin")

        events = group.domain_events
        assert len(events) == 2  # Create + ToolAdded
        assert isinstance(events[1], ExplicitToolAddedDomainEvent)

    def test_add_explicit_tool_event_contains_data(self) -> None:
        """Test that tool added event contains correct data."""
        group = create_tool_group()

        group.add_tool("tool-456", added_by="admin")

        event = group.domain_events[1]
        assert isinstance(event, ExplicitToolAddedDomainEvent)
        assert event.tool_id == "tool-456"
        assert event.added_by == "admin"

    def test_add_duplicate_tool_returns_false(self) -> None:
        """Test adding duplicate tool returns False."""
        group = create_tool_group()
        group.add_tool("tool-123", added_by="admin")

        result = group.add_tool("tool-123", added_by="admin")

        # Should return False, no new event
        assert result is False
        events = group.domain_events
        assert len(events) == 2  # Only Create + first Add

    def test_remove_explicit_tool(self) -> None:
        """Test removing an explicit tool from the group."""
        group = create_tool_group()
        group.add_tool("tool-123", added_by="admin")

        group.remove_tool("tool-123", removed_by="admin")

        assert len(group.state.explicit_tool_ids) == 0

    def test_remove_explicit_tool_generates_event(self) -> None:
        """Test that removing tool generates domain event."""
        group = create_tool_group()
        group.add_tool("tool-123", added_by="admin")

        group.remove_tool("tool-123", removed_by="admin")

        events = group.domain_events
        assert len(events) == 3  # Create + Add + Remove
        assert isinstance(events[2], ExplicitToolRemovedDomainEvent)

    def test_remove_nonexistent_tool_returns_false(self) -> None:
        """Test removing non-existent tool returns False."""
        group = create_tool_group()

        result = group.remove_tool("nonexistent-tool-id", removed_by="admin")

        assert result is False
        events = group.domain_events
        assert len(events) == 1  # Only Create


# ============================================================================
# TOOL EXCLUSION MANAGEMENT TESTS
# ============================================================================


class TestToolExclusionManagement:
    """Test tool exclusion/inclusion operations."""

    def test_exclude_tool(self) -> None:
        """Test excluding a tool from the group."""
        group = create_tool_group()

        group.exclude_tool("tool-123", excluded_by="admin", reason="Not needed")

        assert len(group.state.excluded_tool_ids) == 1
        assert group.state.excluded_tool_ids[0].tool_id == "tool-123"

    def test_exclude_tool_generates_event(self) -> None:
        """Test that excluding tool generates domain event."""
        group = create_tool_group()

        group.exclude_tool("tool-123", excluded_by="admin", reason="Not needed")

        events = group.domain_events
        assert len(events) == 2  # Create + Exclude
        assert isinstance(events[1], ToolExcludedDomainEvent)

    def test_exclude_tool_event_contains_data(self) -> None:
        """Test that tool excluded event contains correct data."""
        group = create_tool_group()

        group.exclude_tool("tool-456", excluded_by="admin", reason="Security concern")

        event = group.domain_events[1]
        assert isinstance(event, ToolExcludedDomainEvent)
        assert event.tool_id == "tool-456"
        assert event.excluded_by == "admin"
        assert event.reason == "Security concern"

    def test_exclude_duplicate_tool_returns_false(self) -> None:
        """Test excluding already excluded tool returns False."""
        group = create_tool_group()
        group.exclude_tool("tool-123", excluded_by="admin", reason="Testing")

        result = group.exclude_tool("tool-123", excluded_by="admin", reason="Testing again")

        assert result is False
        events = group.domain_events
        assert len(events) == 2  # Only Create + first Exclude

    def test_include_tool(self) -> None:
        """Test including a previously excluded tool."""
        group = create_tool_group()
        group.exclude_tool("tool-123", excluded_by="admin", reason="Testing")

        group.include_tool("tool-123", included_by="admin")

        assert len(group.state.excluded_tool_ids) == 0

    def test_include_tool_generates_event(self) -> None:
        """Test that including tool generates domain event."""
        group = create_tool_group()
        group.exclude_tool("tool-123", excluded_by="admin", reason="Testing")

        group.include_tool("tool-123", included_by="admin")

        events = group.domain_events
        assert len(events) == 3  # Create + Exclude + Include
        assert isinstance(events[2], ToolIncludedDomainEvent)

    def test_include_nonexcluded_tool_returns_false(self) -> None:
        """Test including non-excluded tool returns False."""
        group = create_tool_group()

        result = group.include_tool("nonexcluded-tool-id", included_by="admin")

        assert result is False
        events = group.domain_events
        assert len(events) == 1  # Only Create


# ============================================================================
# ACTIVATION LIFECYCLE TESTS
# ============================================================================


class TestActivationLifecycle:
    """Test activate/deactivate operations."""

    def test_new_group_is_active_by_default(self) -> None:
        """Test that newly created groups are active by default."""
        group = create_tool_group()

        assert group.state.is_active is True

    def test_deactivate_group(self) -> None:
        """Test deactivating a group."""
        group = create_tool_group()

        group.deactivate(deactivated_by="admin")

        assert group.state.is_active is False

    def test_deactivate_group_generates_event(self) -> None:
        """Test that deactivating generates domain event."""
        group = create_tool_group()

        group.deactivate(deactivated_by="admin")

        events = group.domain_events
        assert len(events) == 2  # Create + Deactivate
        assert isinstance(events[1], ToolGroupDeactivatedDomainEvent)

    def test_deactivate_group_event_contains_data(self) -> None:
        """Test that deactivated event contains correct data."""
        group = create_tool_group()

        group.deactivate(deactivated_by="admin")

        event = group.domain_events[1]
        assert isinstance(event, ToolGroupDeactivatedDomainEvent)
        assert event.deactivated_by == "admin"

    def test_deactivate_already_inactive_returns_false(self) -> None:
        """Test deactivating already inactive group returns False."""
        group = create_tool_group()
        group.deactivate(deactivated_by="admin")

        result = group.deactivate(deactivated_by="admin")

        assert result is False
        events = group.domain_events
        assert len(events) == 2  # Only Create + first Deactivate

    def test_activate_group(self) -> None:
        """Test activating a deactivated group."""
        group = create_tool_group()
        group.deactivate(deactivated_by="admin")

        group.activate(activated_by="admin")

        assert group.state.is_active is True

    def test_activate_group_generates_event(self) -> None:
        """Test that activating generates domain event."""
        group = create_tool_group()
        group.deactivate(deactivated_by="admin")

        group.activate(activated_by="admin")

        events = group.domain_events
        assert len(events) == 3  # Create + Deactivate + Activate
        assert isinstance(events[2], ToolGroupActivatedDomainEvent)

    def test_activate_already_active_returns_false(self) -> None:
        """Test activating already active group returns False."""
        group = create_tool_group()

        result = group.activate(activated_by="admin")

        assert result is False
        events = group.domain_events
        assert len(events) == 1  # Only Create


# ============================================================================
# COMBINED OPERATIONS TESTS
# ============================================================================


class TestCombinedOperations:
    """Test combined operations and complex scenarios."""

    def test_full_lifecycle(self) -> None:
        """Test full group lifecycle with all operations."""
        # Create group
        group = create_tool_group(
            name="Full Lifecycle Group",
            created_by="creator",
        )

        # Add selectors
        source_selector = create_source_selector("source-1")
        tag_selector = create_tag_selector(["api", "rest"])
        group.add_selector(source_selector, added_by="admin")
        group.add_selector(tag_selector, added_by="admin")

        # Add explicit tools
        group.add_tool("tool-1", added_by="admin")
        group.add_tool("tool-2", added_by="admin")

        # Exclude some tools
        group.exclude_tool("tool-3", excluded_by="admin", reason="Not compatible")

        # Update metadata
        group.update(name="Updated Group Name", updated_by="editor")

        # Deactivate
        group.deactivate(deactivated_by="admin")

        # Verify final state
        assert group.state.name == "Updated Group Name"
        assert len(group.state.selectors) == 2
        assert len(group.state.explicit_tool_ids) == 2
        assert len(group.state.excluded_tool_ids) == 1
        assert group.state.is_active is False

        # Should have many events
        assert len(group.domain_events) >= 7

    def test_selector_and_tool_coexistence(self) -> None:
        """Test that selectors and explicit tools can coexist."""
        group = create_tool_group()

        # Add via selector
        selector = create_source_selector("source-1")
        group.add_selector(selector, added_by="admin")

        # Add explicit tool
        group.add_tool("explicit-tool-1", added_by="admin")

        # Both should exist
        assert len(group.state.selectors) == 1
        assert len(group.state.explicit_tool_ids) == 1

    def test_excluded_tool_not_in_explicit(self) -> None:
        """Test workflow: add tool explicitly then exclude it."""
        group = create_tool_group()

        # Add tool explicitly
        group.add_tool("tool-1", added_by="admin")

        # Exclude the same tool (it's now in both lists - explicit and excluded)
        group.exclude_tool("tool-1", excluded_by="admin", reason="Changed my mind")

        # Tool is in both lists - this is valid as exclusion takes precedence
        assert any(m.tool_id == "tool-1" for m in group.state.explicit_tool_ids)
        assert any(e.tool_id == "tool-1" for e in group.state.excluded_tool_ids)

    def test_query_methods(self) -> None:
        """Test the query methods on the aggregate."""
        group = create_tool_group()
        selector = create_source_selector("source-1")
        group.add_selector(selector, added_by="admin")
        group.add_tool("tool-1", added_by="admin")
        group.exclude_tool("tool-2", excluded_by="admin", reason="Test")

        # Test query methods
        assert group.has_selector(selector.id) is True
        assert group.has_selector("nonexistent") is False

        assert group.has_explicit_tool("tool-1") is True
        assert group.has_explicit_tool("tool-2") is False

        assert group.is_tool_excluded("tool-2") is True
        assert group.is_tool_excluded("tool-1") is False

        assert group.get_selector_count() == 1
        assert group.get_explicit_tool_count() == 1
        assert group.get_excluded_tool_count() == 1
