"""Unit tests for ConversationContext dataclass.

Tests cover:
- Context initialization
- State transitions
- Template progress tracking
- Item lifecycle management
- Serialization
"""

from application.orchestrator.context import (
    ConversationContext,
    OrchestratorState,
)


class TestConversationContextCreation:
    """Test ConversationContext initialization."""

    def test_minimal_creation(self):
        """Test creation with minimal required fields."""
        ctx = ConversationContext(
            connection_id="conn-123",
            conversation_id="conv-456",
            user_id="user-789",
        )

        assert ctx.connection_id == "conn-123"
        assert ctx.conversation_id == "conv-456"
        assert ctx.user_id == "user-789"
        assert ctx.state == OrchestratorState.INITIALIZING
        assert ctx.definition_id is None
        assert ctx.template_id is None
        assert ctx.is_proactive is False
        assert ctx.tools == []
        assert ctx.access_token is None

    def test_proactive_context_creation(self):
        """Test creation for a proactive (template-driven) conversation."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            definition_id="def-123",
            template_id="tpl-456",
            is_proactive=True,
            has_template=True,
            total_items=5,
        )

        assert ctx.is_proactive is True
        assert ctx.has_template is True
        assert ctx.template_id == "tpl-456"
        assert ctx.total_items == 5
        assert ctx.current_item_index == 0

    def test_reactive_context_creation(self):
        """Test creation for a reactive (user-driven) conversation."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            definition_id="def-123",
            is_proactive=False,
            model="openai:gpt-4o",
        )

        assert ctx.is_proactive is False
        assert ctx.has_template is False
        assert ctx.model == "openai:gpt-4o"


class TestConversationContextStateTransitions:
    """Test state transition functionality."""

    def test_transition_to_valid_state(self):
        """Valid transition should succeed and update activity."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        original_activity = ctx.last_activity

        result = ctx.transition_to(OrchestratorState.READY)

        assert result is True
        assert ctx.state == OrchestratorState.READY
        assert ctx.last_activity >= original_activity

    def test_transition_to_invalid_state(self):
        """Invalid transition should fail and preserve state."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )

        # INITIALIZING cannot transition directly to PROCESSING
        result = ctx.transition_to(OrchestratorState.PROCESSING)

        assert result is False
        assert ctx.state == OrchestratorState.INITIALIZING

    def test_complete_state_machine_flow_reactive(self):
        """Test complete reactive conversation flow."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )

        # INITIALIZING → READY
        assert ctx.transition_to(OrchestratorState.READY) is True
        assert ctx.state == OrchestratorState.READY

        # READY → PROCESSING (user sends message)
        assert ctx.transition_to(OrchestratorState.PROCESSING) is True
        assert ctx.state == OrchestratorState.PROCESSING

        # PROCESSING → READY (agent responds)
        assert ctx.transition_to(OrchestratorState.READY) is True
        assert ctx.state == OrchestratorState.READY

        # READY → COMPLETED
        assert ctx.transition_to(OrchestratorState.COMPLETED) is True
        assert ctx.state == OrchestratorState.COMPLETED
        assert ctx.state.is_terminal() is True

    def test_complete_state_machine_flow_proactive(self):
        """Test complete proactive conversation flow."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            is_proactive=True,
        )

        # INITIALIZING → PRESENTING
        assert ctx.transition_to(OrchestratorState.PRESENTING) is True

        # PRESENTING → SUSPENDED (widget rendered)
        assert ctx.transition_to(OrchestratorState.SUSPENDED) is True

        # SUSPENDED → PRESENTING (widget response received)
        assert ctx.transition_to(OrchestratorState.PRESENTING) is True

        # PRESENTING → READY (template complete)
        assert ctx.transition_to(OrchestratorState.READY) is True


class TestConversationContextTemplateProgress:
    """Test template progress tracking."""

    def test_template_progress_percentage_no_items(self):
        """Zero items should give 0% progress."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            total_items=0,
        )
        assert ctx.template_progress_percentage == 0.0

    def test_template_progress_percentage_initial(self):
        """Initial state (index 0) should be 0%."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=0,
            total_items=5,
        )
        assert ctx.template_progress_percentage == 0.0

    def test_template_progress_percentage_mid(self):
        """Halfway through should be 50%."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=5,
            total_items=10,
        )
        assert ctx.template_progress_percentage == 50.0

    def test_template_progress_percentage_complete(self):
        """All items done should be 100%."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=10,
            total_items=10,
        )
        assert ctx.template_progress_percentage == 100.0

    def test_is_template_complete_false(self):
        """Not complete when more items remain."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=2,
            total_items=5,
        )
        assert ctx.is_template_complete is False

    def test_is_template_complete_true(self):
        """Complete when index reaches total."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=5,
            total_items=5,
        )
        assert ctx.is_template_complete is True


class TestConversationContextPendingOperations:
    """Test pending operation tracking."""

    def test_has_pending_operation_none(self):
        """No pending operations."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
        )
        assert ctx.has_pending_operation is False

    def test_has_pending_operation_widget(self):
        """Pending widget should be detected."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            pending_widget_id="widget-123",
        )
        assert ctx.has_pending_operation is True

    def test_has_pending_operation_tool(self):
        """Pending tool call should be detected."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            pending_tool_call_id="tool-call-456",
        )
        assert ctx.has_pending_operation is True


class TestConversationContextItemLifecycle:
    """Test item execution lifecycle."""

    def test_start_item(self):
        """Starting an item should create ItemExecutionState."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=0,
            total_items=3,
        )

        item_state = ctx.start_item("item-abc")

        assert ctx.current_item_state is not None
        assert ctx.current_item_state is item_state
        assert item_state.item_id == "item-abc"
        assert item_state.item_index == 0

    def test_start_item_with_confirmation(self):
        """Starting item with confirmation settings."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
        )

        item_state = ctx.start_item(
            "item-xyz",
            require_confirmation=True,
            button_text="Confirm Selection",
        )

        assert item_state.require_user_confirmation is True
        assert item_state.confirmation_button_text == "Confirm Selection"

    def test_advance_to_next_item(self):
        """Advancing should increment index and clear current state."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=0,
            total_items=3,
        )
        ctx.start_item("item-0")

        has_more = ctx.advance_to_next_item()

        assert has_more is True
        assert ctx.current_item_index == 1
        assert ctx.current_item_state is None
        assert ctx.pending_widget_id is None

    def test_advance_to_next_item_marks_complete(self):
        """Advancing should mark current item as complete."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            total_items=2,
        )
        item_state = ctx.start_item("item-0")
        assert item_state.completed_at is None

        ctx.advance_to_next_item()

        assert item_state.completed_at is not None

    def test_advance_to_next_item_returns_false_when_done(self):
        """Advancing past last item should return False."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            current_item_index=2,
            total_items=3,
        )
        ctx.start_item("item-2")

        has_more = ctx.advance_to_next_item()

        assert has_more is False
        assert ctx.current_item_index == 3
        assert ctx.is_template_complete is True


class TestConversationContextActivityTracking:
    """Test activity timestamp updates."""

    def test_update_activity(self):
        """update_activity should update timestamp."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
        )
        original = ctx.last_activity

        # Small delay to ensure different timestamp
        import time

        time.sleep(0.01)
        ctx.update_activity()

        assert ctx.last_activity > original


class TestConversationContextSerialization:
    """Test context serialization."""

    def test_to_dict_minimal(self):
        """Test serialization of minimal context."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
        )
        data = ctx.to_dict()

        assert data["connection_id"] == "conn-1"
        assert data["conversation_id"] == "conv-1"
        assert data["user_id"] == "user-1"
        assert data["state"] == "initializing"
        assert data["current_item_state"] is None
        assert data["tool_count"] == 0
        assert data["has_access_token"] is False

    def test_to_dict_with_item_state(self):
        """Test serialization with active item state."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            is_proactive=True,
            total_items=5,
        )
        ctx.start_item("item-test")
        ctx.current_item_state.record_response("widget-1", "answer")

        data = ctx.to_dict()

        assert data["current_item_state"] is not None
        assert data["current_item_state"]["item_id"] == "item-test"
        assert "widget-1" in data["current_item_state"]["widget_responses"]

    def test_to_dict_security_no_token_exposure(self):
        """Serialization should not expose actual access token."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            access_token="super-secret-token-12345",
        )
        data = ctx.to_dict()

        assert data["has_access_token"] is True
        assert "access_token" not in data
        assert "super-secret" not in str(data)

    def test_to_dict_with_tools(self):
        """Test serialization includes tool count but not tools."""
        ctx = ConversationContext(
            connection_id="conn-1",
            conversation_id="conv-1",
            user_id="user-1",
            tools=[{"name": "tool1"}, {"name": "tool2"}, {"name": "tool3"}],
        )
        data = ctx.to_dict()

        assert data["tool_count"] == 3
        assert "tools" not in data  # Don't serialize full tool list


class TestConversationContextEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_client_capabilities(self):
        """Empty capabilities list should be handled."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            client_capabilities=[],
        )
        assert ctx.client_capabilities == []

    def test_template_config_mutation(self):
        """Template config should be mutable."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            template_config={"theme": "dark"},
        )
        ctx.template_config["language"] = "en"

        assert ctx.template_config == {"theme": "dark", "language": "en"}

    def test_multiple_item_lifecycles(self):
        """Test processing multiple items sequentially."""
        ctx = ConversationContext(
            connection_id="c",
            conversation_id="c",
            user_id="u",
            total_items=3,
        )

        # Process item 0
        ctx.start_item("item-0")
        ctx.current_item_state.record_response("w0", "answer0")
        assert ctx.advance_to_next_item() is True

        # Process item 1
        ctx.start_item("item-1")
        ctx.current_item_state.record_response("w1", "answer1")
        assert ctx.advance_to_next_item() is True

        # Process item 2 (last)
        ctx.start_item("item-2")
        ctx.current_item_state.record_response("w2", "answer2")
        assert ctx.advance_to_next_item() is False

        assert ctx.is_template_complete is True
        assert ctx.current_item_index == 3
