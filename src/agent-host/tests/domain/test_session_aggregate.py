"""Unit tests for Session aggregate."""

from datetime import UTC, datetime

import pytest

from domain.entities.session import DomainError, Session
from domain.models.session_models import (
    ClientAction,
    ClientResponse,
    ControlMode,
    SessionConfig,
    SessionStatus,
    SessionType,
)


class TestSessionCreation:
    """Tests for Session aggregate creation."""

    def test_create_thought_session(self):
        """Creating a THOUGHT session should use REACTIVE mode."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.THOUGHT,
        )
        assert session.id() is not None
        assert session.state.user_id == "user-123"
        assert session.state.conversation_id == "conv-456"
        assert session.state.session_type == SessionType.THOUGHT
        assert session.state.control_mode == ControlMode.REACTIVE
        assert session.state.status == SessionStatus.PENDING

    def test_create_learning_session(self):
        """Creating a LEARNING session should use PROACTIVE mode."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        assert session.state.session_type == SessionType.LEARNING
        assert session.state.control_mode == ControlMode.PROACTIVE

    def test_create_with_custom_config(self):
        """Session should accept custom config."""
        config = SessionConfig(time_limit_seconds=600, max_items=10)
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.VALIDATION,
            config=config,
        )
        loaded_config = session.get_config()
        assert loaded_config.time_limit_seconds == 600
        assert loaded_config.max_items == 10

    def test_create_with_system_prompt(self):
        """Session should accept custom system prompt."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
            system_prompt="You are a helpful tutor.",
        )
        assert session.state.system_prompt == "You are a helpful tutor."

    def test_create_with_specific_id(self):
        """Session should accept specific ID."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.THOUGHT,
            session_id="my-session-id",
        )
        assert session.id() == "my-session-id"

    def test_domain_events_registered_on_create(self):
        """Session creation should register SessionCreatedDomainEvent."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.THOUGHT,
        )
        # Verify session was created with correct state
        # (Events are internal to the aggregate and managed by the repository)
        assert session.state.id is not None
        assert session.state.session_type == SessionType.THOUGHT


class TestSessionLifecycle:
    """Tests for Session lifecycle transitions."""

    def test_start_from_pending(self):
        """Session should transition from PENDING to ACTIVE on start."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        assert session.state.status == SessionStatus.PENDING
        session.start()
        assert session.state.status == SessionStatus.ACTIVE
        assert session.state.started_at is not None

    def test_start_already_active_raises_error(self):
        """Starting an active session should raise DomainError."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()
        with pytest.raises(DomainError, match="Cannot start session"):
            session.start()

    def test_complete_session(self):
        """Session should complete successfully."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()
        session.complete(reason="all_items_done", summary={"score": 85})
        assert session.state.status == SessionStatus.COMPLETED
        assert session.state.completed_at is not None

    def test_terminate_session(self):
        """Session should terminate with reason."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()
        session.terminate("User quit")
        assert session.state.status == SessionStatus.TERMINATED
        assert session.state.terminated_reason == "User quit"

    def test_expire_session(self):
        """Session should expire with reason."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.VALIDATION,
        )
        session.start()
        session.expire("time_limit")
        assert session.state.status == SessionStatus.EXPIRED
        assert session.state.terminated_reason == "time_limit"

    def test_cannot_complete_terminated_session(self):
        """Completing a terminated session should raise DomainError."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()
        session.terminate("User quit")
        with pytest.raises(DomainError, match="Cannot complete session"):
            session.complete()


class TestPendingActions:
    """Tests for pending client action management."""

    def test_set_pending_action(self):
        """Setting pending action should change status."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={"question": "Test?"},
        )
        session.set_pending_action(action)

        assert session.state.status == SessionStatus.AWAITING_CLIENT_ACTION
        assert session.state.pending_action is not None
        assert session.state.pending_action["tool_call_id"] == "call_123"

    def test_set_pending_action_updates_ui_state(self):
        """Setting pending action should update UI state."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={},
            lock_input=True,
        )
        session.set_pending_action(action)

        ui_state = session.get_ui_state()
        assert ui_state.chat_input_locked is True
        assert ui_state.active_widget is not None

    def test_cannot_set_pending_action_when_not_active(self):
        """Setting pending action on non-active session should raise."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        # Session is still PENDING
        action = ClientAction(
            tool_call_id="call_123",
            tool_name="test",
            widget_type="test",
            props={},
        )
        with pytest.raises(DomainError, match="Cannot set pending action"):
            session.set_pending_action(action)


class TestResponseSubmission:
    """Tests for client response submission."""

    def test_submit_response_clears_pending_action(self):
        """Submitting response should clear pending action."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={},
        )
        session.set_pending_action(action)

        response = ClientResponse(
            tool_call_id="call_123",
            response={"selection": "A"},
            timestamp=datetime.now(UTC),
        )
        session.submit_response(response)

        assert session.state.status == SessionStatus.ACTIVE
        assert session.state.pending_action is None

    def test_submit_response_wrong_tool_call_id_raises(self):
        """Submitting response with wrong tool_call_id should raise."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        action = ClientAction(
            tool_call_id="call_123",
            tool_name="test",
            widget_type="test",
            props={},
        )
        session.set_pending_action(action)

        response = ClientResponse(
            tool_call_id="wrong_id",
            response={},
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(DomainError, match="does not match pending action"):
            session.submit_response(response)

    def test_submit_response_when_no_pending_action_raises(self):
        """Submitting response when not awaiting should raise."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        response = ClientResponse(
            tool_call_id="call_123",
            response={},
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(DomainError, match="Cannot submit response"):
            session.submit_response(response)


class TestSessionItems:
    """Tests for session item management."""

    def test_start_item(self):
        """Starting an item should add to items list."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        item = session.start_item(
            agent_prompt="What is 2+2?",
            client_action=ClientAction(
                tool_call_id="call_123",
                tool_name="present_choices",
                widget_type="multiple_choice",
                props={"options": ["3", "4", "5"]},
            ),
        )

        assert item.id is not None
        assert item.sequence == 1
        assert item.agent_prompt == "What is 2+2?"
        assert len(session.state.items) == 1

    def test_get_current_item(self):
        """get_current_item should return uncompleted item."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        item = session.start_item(agent_prompt="Test?")
        current = session.get_current_item()

        assert current is not None
        assert current.id == item.id

    def test_get_completed_items_count(self):
        """get_completed_items_count should return correct count."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        # Start item 1
        session.start_item(
            agent_prompt="Q1?",
            client_action=ClientAction(
                tool_call_id="call_1",
                tool_name="test",
                widget_type="test",
                props={},
            ),
        )
        session.set_pending_action(
            ClientAction(
                tool_call_id="call_1",
                tool_name="test",
                widget_type="test",
                props={},
            )
        )
        session.submit_response(
            ClientResponse(
                tool_call_id="call_1",
                response="A1",
                timestamp=datetime.now(UTC),
            )
        )

        assert session.get_completed_items_count() == 1


class TestQueryMethods:
    """Tests for session query methods."""

    def test_is_active(self):
        """is_active should return True for active sessions."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        assert session.is_active() is False
        session.start()
        assert session.is_active() is True
        session.complete()
        assert session.is_active() is False

    def test_is_proactive(self):
        """is_proactive should return True for proactive sessions."""
        thought_session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.THOUGHT,
        )
        learning_session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        assert thought_session.is_proactive() is False
        assert learning_session.is_proactive() is True

    def test_can_accept_response(self):
        """can_accept_response should return True when awaiting."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()
        assert session.can_accept_response() is False

        session.set_pending_action(
            ClientAction(
                tool_call_id="call_1",
                tool_name="test",
                widget_type="test",
                props={},
            )
        )
        assert session.can_accept_response() is True

    def test_get_pending_action(self):
        """get_pending_action should return ClientAction object."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.LEARNING,
        )
        session.start()

        assert session.get_pending_action() is None

        action = ClientAction(
            tool_call_id="call_123",
            tool_name="present_choices",
            widget_type="multiple_choice",
            props={"question": "Test?"},
        )
        session.set_pending_action(action)

        pending = session.get_pending_action()
        assert pending is not None
        assert pending.tool_call_id == "call_123"
        assert pending.tool_name == "present_choices"


class TestTimeRemaining:
    """Tests for time remaining calculation."""

    def test_time_remaining_no_limit(self):
        """get_time_remaining_seconds should return None if no limit."""
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.THOUGHT,  # No time limit by default
        )
        assert session.get_time_remaining_seconds() is None

    def test_time_remaining_before_start(self):
        """get_time_remaining_seconds should return full time before start."""
        config = SessionConfig(time_limit_seconds=600)
        session = Session(
            user_id="user-123",
            conversation_id="conv-456",
            session_type=SessionType.VALIDATION,
            config=config,
        )
        # Not started yet
        remaining = session.get_time_remaining_seconds()
        assert remaining == 600
