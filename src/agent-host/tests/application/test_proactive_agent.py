"""Unit tests for proactive agent module."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.agents.base_agent import AgentError, AgentEventType, AgentRunContext
from application.agents.llm_provider import LlmMessage, LlmStreamChunk, LlmToolCall, LlmToolDefinition
from application.agents.proactive_agent import (
    DEFAULT_PROACTIVE_PROMPT,
    LEARNING_SESSION_PROMPT,
    THOUGHT_SESSION_PROMPT,
    VALIDATION_SESSION_PROMPT,
    ProactiveAgent,
    ProactiveSessionContext,
    SuspendedState,
    get_system_prompt_for_session_type,
)
from domain.models.session_models import ClientResponse, SessionConfig, SessionType

# =============================================================================
# Helper Functions for Async Mock Generators
# =============================================================================


async def mock_stream_no_tools():
    """Mock stream with no tool calls."""
    yield LlmStreamChunk(content="Hello, I'm your tutor.")
    yield LlmStreamChunk(content="", done=True, tool_calls=None)


async def mock_stream_with_client_tool():
    """Mock stream with client tool call."""
    yield LlmStreamChunk(content="Let me ask you a question.")
    yield LlmStreamChunk(
        content="",
        done=True,
        tool_calls=[
            LlmToolCall(
                id="call-123",
                name="present_choices",
                arguments={"prompt": "What is 2+2?", "options": ["3", "4", "5"]},
            )
        ],
    )


class TestSystemPrompts:
    """Tests for session type system prompts."""

    def test_learning_prompt_exists(self) -> None:
        """Learning session prompt should be defined."""
        assert LEARNING_SESSION_PROMPT is not None
        assert len(LEARNING_SESSION_PROMPT) > 100  # Non-trivial prompt
        assert "tutor" in LEARNING_SESSION_PROMPT.lower() or "learning" in LEARNING_SESSION_PROMPT.lower()

    def test_thought_prompt_exists(self) -> None:
        """Thought session prompt should be defined."""
        assert THOUGHT_SESSION_PROMPT is not None
        assert len(THOUGHT_SESSION_PROMPT) > 100
        assert "socratic" in THOUGHT_SESSION_PROMPT.lower() or "thinking" in THOUGHT_SESSION_PROMPT.lower()

    def test_validation_prompt_exists(self) -> None:
        """Validation session prompt should be defined."""
        assert VALIDATION_SESSION_PROMPT is not None
        assert len(VALIDATION_SESSION_PROMPT) > 100
        assert "valid" in VALIDATION_SESSION_PROMPT.lower()

    def test_default_prompt_exists(self) -> None:
        """Default prompt should be defined."""
        assert DEFAULT_PROACTIVE_PROMPT is not None
        assert len(DEFAULT_PROACTIVE_PROMPT) > 50


class TestGetSystemPromptForSessionType:
    """Tests for get_system_prompt_for_session_type function."""

    def test_learning_session_returns_learning_prompt(self) -> None:
        """Learning session should return learning prompt."""
        prompt = get_system_prompt_for_session_type(SessionType.LEARNING)
        assert prompt == LEARNING_SESSION_PROMPT

    def test_thought_session_returns_thought_prompt(self) -> None:
        """Thought session should return thought prompt."""
        prompt = get_system_prompt_for_session_type(SessionType.THOUGHT)
        assert prompt == THOUGHT_SESSION_PROMPT

    def test_validation_session_returns_validation_prompt(self) -> None:
        """Validation session should return validation prompt."""
        prompt = get_system_prompt_for_session_type(SessionType.VALIDATION)
        assert prompt == VALIDATION_SESSION_PROMPT

    def test_custom_prompt_overrides(self) -> None:
        """Custom prompt should override default."""
        custom = "My custom system prompt"
        prompt = get_system_prompt_for_session_type(SessionType.LEARNING, custom)
        assert prompt == custom


class TestProactiveSessionContext:
    """Tests for ProactiveSessionContext dataclass."""

    def test_minimal_context(self) -> None:
        """Minimal context should have required fields."""
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        assert context.session_id == "session-123"
        assert context.session_type == SessionType.LEARNING
        assert context.conversation_id == "conv-456"
        assert context.initial_message is None
        assert context.items_completed == 0

    def test_full_context(self) -> None:
        """Full context should accept all fields."""
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.THOUGHT,
            config=SessionConfig(max_items=5),
            conversation_id="conv-456",
            initial_message="Let's discuss Python",
            items_completed=2,
            custom_system_prompt="Custom prompt",
            metadata={"key": "value"},
        )

        assert context.session_type == SessionType.THOUGHT
        assert context.config.max_items == 5
        assert context.initial_message == "Let's discuss Python"
        assert context.items_completed == 2
        assert context.custom_system_prompt == "Custom prompt"
        assert context.metadata == {"key": "value"}


class TestSuspendedState:
    """Tests for SuspendedState dataclass."""

    def test_suspended_state_creation(self) -> None:
        """SuspendedState should store all required data."""
        tool_call = LlmToolCall(id="call-1", name="present_choices", arguments={})
        messages = [LlmMessage.system("System"), LlmMessage.user("User")]

        state = SuspendedState(
            messages=messages,
            pending_tool_call=tool_call,
            iteration=3,
            tool_calls_made=5,
            start_time=1234567890.0,
        )

        assert len(state.messages) == 2
        assert state.pending_tool_call == tool_call
        assert state.iteration == 3
        assert state.tool_calls_made == 5
        assert state.start_time == 1234567890.0


class TestProactiveAgentInitialization:
    """Tests for ProactiveAgent initialization."""

    def test_agent_initialization(self) -> None:
        """Agent should initialize with provider."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        assert agent._llm == mock_provider
        assert agent._suspended_state is None
        assert agent._session_context is None

    def test_agent_not_suspended_initially(self) -> None:
        """Agent should not be suspended initially."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        assert agent.is_suspended is False
        assert agent.pending_tool_call is None


class TestProactiveAgentClientTools:
    """Tests for client tool handling in ProactiveAgent."""

    def test_get_combined_tools_includes_client_tools(self) -> None:
        """Combined tools should include client tools."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        tools = agent._get_combined_tools()

        # Should have client tools
        tool_names = {t.name for t in tools}
        assert "present_choices" in tool_names
        assert "request_free_text" in tool_names
        assert "present_code_editor" in tool_names

    def test_get_combined_tools_with_server_tools(self) -> None:
        """Combined tools should include server tools."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        server_tool = LlmToolDefinition(
            name="get_weather",
            description="Get weather",
            parameters={},
        )

        tools = agent._get_combined_tools([server_tool])

        tool_names = {t.name for t in tools}
        assert "get_weather" in tool_names
        assert "present_choices" in tool_names

    def test_get_combined_tools_filters_conflicting_names(self) -> None:
        """Server tools with client tool names should be filtered."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        # Try to add a server tool with same name as client tool
        conflicting_tool = LlmToolDefinition(
            name="present_choices",  # Same as client tool
            description="Different implementation",
            parameters={},
        )

        tools = agent._get_combined_tools([conflicting_tool])

        # Should only have one present_choices (the client one)
        choices_tools = [t for t in tools if t.name == "present_choices"]
        assert len(choices_tools) == 1


class TestProactiveAgentSystemMessage:
    """Tests for system message building."""

    def test_build_system_message_includes_session_type(self) -> None:
        """System message should include session type."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        message = agent._build_system_message_for_session(context)

        assert message.role.value == "system"
        assert "learning" in message.content.lower()

    def test_build_system_message_includes_items_completed(self) -> None:
        """System message should include items completed."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
            items_completed=3,
        )

        message = agent._build_system_message_for_session(context)

        assert "3" in message.content

    def test_build_system_message_includes_max_items(self) -> None:
        """System message should include max items if set."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(max_items=10),
            conversation_id="conv-456",
        )

        message = agent._build_system_message_for_session(context)

        assert "10" in message.content

    def test_build_system_message_includes_initial_message(self) -> None:
        """System message should include initial message."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
            initial_message="Teach me Python",
        )

        message = agent._build_system_message_for_session(context)

        assert "Teach me Python" in message.content


@pytest.mark.asyncio
class TestProactiveAgentStartSession:
    """Tests for start_session method."""

    async def test_start_session_emits_run_started(self) -> None:
        """start_session should emit RUN_STARTED event."""
        mock_provider = MagicMock()
        mock_provider.chat_stream = MagicMock(return_value=mock_stream_no_tools())

        agent = ProactiveAgent(mock_provider)
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        events = []
        async for event in agent.start_session(context):
            events.append(event)

        # Should have RUN_STARTED event
        run_started = [e for e in events if e.type == AgentEventType.RUN_STARTED]
        assert len(run_started) == 1
        assert run_started[0].data["session_id"] == "session-123"

    async def test_start_session_completes_without_tools(self) -> None:
        """start_session should complete if LLM returns no tool calls."""
        mock_provider = MagicMock()
        mock_provider.chat_stream = MagicMock(return_value=mock_stream_no_tools())

        agent = ProactiveAgent(mock_provider)
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        events = []
        async for event in agent.start_session(context):
            events.append(event)

        # Should have RUN_COMPLETED event
        run_completed = [e for e in events if e.type == AgentEventType.RUN_COMPLETED]
        assert len(run_completed) == 1
        assert run_completed[0].data["success"] is True

    async def test_start_session_suspends_on_client_tool(self) -> None:
        """start_session should suspend when client tool is called."""
        mock_provider = MagicMock()
        mock_provider.chat_stream = MagicMock(return_value=mock_stream_with_client_tool())

        agent = ProactiveAgent(mock_provider)
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        events = []
        async for event in agent.start_session(context):
            events.append(event)

        # Should have CLIENT_ACTION event
        client_action = [e for e in events if e.type == AgentEventType.CLIENT_ACTION]
        assert len(client_action) == 1

        # Should have RUN_SUSPENDED event
        suspended = [e for e in events if e.type == AgentEventType.RUN_SUSPENDED]
        assert len(suspended) == 1

        # Agent should be suspended
        assert agent.is_suspended is True


@pytest.mark.asyncio
class TestProactiveAgentResumeWithResponse:
    """Tests for resume_with_response method."""

    async def test_resume_fails_when_not_suspended(self) -> None:
        """resume_with_response should fail if not suspended."""
        mock_provider = MagicMock()
        agent = ProactiveAgent(mock_provider)

        response = ClientResponse(
            tool_call_id="call-123",
            response={"selection": "4"},
            timestamp=datetime.now(UTC),
        )

        with pytest.raises(AgentError) as exc_info:
            async for _ in agent.resume_with_response(response):
                pass

        assert "not suspended" in str(exc_info.value).lower()

    async def test_resume_fails_with_wrong_tool_call_id(self) -> None:
        """resume_with_response should fail if tool_call_id doesn't match."""
        mock_provider = MagicMock()
        mock_provider.chat_stream = MagicMock(return_value=mock_stream_with_client_tool())

        agent = ProactiveAgent(mock_provider)
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        # Start session to get suspended
        async for _ in agent.start_session(context):
            pass

        # Try to resume with wrong tool_call_id
        wrong_response = ClientResponse(
            tool_call_id="wrong-id",
            response={"selection": "4"},
            timestamp=datetime.now(UTC),
        )

        with pytest.raises(AgentError) as exc_info:
            async for _ in agent.resume_with_response(wrong_response):
                pass

        assert "doesn't match" in str(exc_info.value).lower()

    async def test_resume_emits_run_resumed(self) -> None:
        """resume_with_response should emit RUN_RESUMED event."""
        mock_provider = MagicMock()

        # First call suspends, second call completes
        call_count = [0]

        async def mock_stream(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                yield LlmStreamChunk(content="Question")
                yield LlmStreamChunk(
                    content="",
                    done=True,
                    tool_calls=[
                        LlmToolCall(
                            id="call-123",
                            name="present_choices",
                            arguments={"prompt": "What is 2+2?", "options": ["3", "4", "5"]},
                        )
                    ],
                )
            else:
                yield LlmStreamChunk(content="Correct!")
                yield LlmStreamChunk(content="", done=True)

        mock_provider.chat_stream = mock_stream

        agent = ProactiveAgent(mock_provider)
        context = ProactiveSessionContext(
            session_id="session-123",
            session_type=SessionType.LEARNING,
            config=SessionConfig(),
            conversation_id="conv-456",
        )

        # Start session to get suspended
        async for _ in agent.start_session(context):
            pass

        # Resume with correct response
        response = ClientResponse(
            tool_call_id="call-123",
            response={"selection": "4", "index": 1},
            timestamp=datetime.now(UTC),
        )

        events = []
        async for event in agent.resume_with_response(response):
            events.append(event)

        # Should have RUN_RESUMED event
        resumed = [e for e in events if e.type == AgentEventType.RUN_RESUMED]
        assert len(resumed) == 1
        assert resumed[0].data["tool_call_id"] == "call-123"


@pytest.mark.asyncio
class TestProactiveAgentRunMethod:
    """Tests for the run() abstract method implementation."""

    async def test_run_returns_error_on_suspension(self) -> None:
        """run() should return error if agent suspends."""
        mock_provider = MagicMock()

        async def mock_stream(*args, **kwargs):
            yield LlmStreamChunk(content="Question")
            yield LlmStreamChunk(
                content="",
                done=True,
                tool_calls=[
                    LlmToolCall(
                        id="call-123",
                        name="present_choices",
                        arguments={"prompt": "What?", "options": ["A", "B"]},
                    )
                ],
            )

        mock_provider.chat_stream = mock_stream

        agent = ProactiveAgent(mock_provider)
        context = AgentRunContext(
            user_message="Start learning",
            tools=[],
        )

        result = await agent.run(context)

        # Should fail because we can't handle suspension in run()
        assert result.success is False
        assert result.error is not None
        assert "suspend" in str(result.error.message).lower()

    async def test_run_completes_without_suspension(self) -> None:
        """run() should complete normally if no suspension."""
        mock_provider = MagicMock()

        async def mock_stream(*args, **kwargs):
            yield LlmStreamChunk(content="Hello!")
            yield LlmStreamChunk(content="", done=True)

        mock_provider.chat_stream = mock_stream

        agent = ProactiveAgent(mock_provider)
        context = AgentRunContext(
            user_message="Hello",
            tools=[],
        )

        result = await agent.run(context)

        assert result.success is True
        assert "Hello" in result.response
