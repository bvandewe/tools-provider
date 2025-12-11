"""Unit tests for agent factory module."""

from unittest.mock import MagicMock

from application.agents.agent_factory import (
    AgentCreationContext,
    AgentFactory,
    AgentType,
    get_agent_type_for_session,
    is_proactive_session,
)
from application.agents.proactive_agent import ProactiveAgent
from application.agents.react_agent import ReActAgent
from domain.models.session_models import SessionConfig, SessionType


class TestAgentType:
    """Tests for AgentType enum."""

    def test_agent_types(self) -> None:
        """Agent types should be defined."""
        assert AgentType.REACT.value == "react"
        assert AgentType.PROACTIVE.value == "proactive"


class TestGetAgentTypeForSession:
    """Tests for get_agent_type_for_session function."""

    def test_learning_session_is_proactive(self) -> None:
        """Learning sessions should use proactive agent."""
        agent_type = get_agent_type_for_session(SessionType.LEARNING)
        assert agent_type == AgentType.PROACTIVE

    def test_thought_session_is_reactive(self) -> None:
        """Thought sessions should use reactive agent (user-driven)."""
        agent_type = get_agent_type_for_session(SessionType.THOUGHT)
        assert agent_type == AgentType.REACT

    def test_validation_session_is_proactive(self) -> None:
        """Validation sessions should use proactive agent."""
        agent_type = get_agent_type_for_session(SessionType.VALIDATION)
        assert agent_type == AgentType.PROACTIVE


class TestIsProactiveSession:
    """Tests for is_proactive_session function."""

    def test_learning_is_proactive(self) -> None:
        """Learning sessions should be proactive."""
        assert is_proactive_session(SessionType.LEARNING) is True

    def test_thought_is_reactive(self) -> None:
        """Thought sessions are user-driven so not proactive."""
        assert is_proactive_session(SessionType.THOUGHT) is False

    def test_validation_is_proactive(self) -> None:
        """Validation sessions should be proactive."""
        assert is_proactive_session(SessionType.VALIDATION) is True


class TestAgentCreationContext:
    """Tests for AgentCreationContext dataclass."""

    def test_minimal_context(self) -> None:
        """Minimal context should have required fields."""
        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
        )

        assert context.session_type == SessionType.LEARNING
        assert context.session_config is not None
        assert context.custom_system_prompt is None
        assert context.llm_provider is None
        assert context.metadata is None

    def test_full_context(self) -> None:
        """Full context should accept all fields."""
        mock_provider = MagicMock()
        context = AgentCreationContext(
            session_type=SessionType.THOUGHT,
            session_config=SessionConfig(max_items=10),
            custom_system_prompt="Custom prompt",
            llm_provider=mock_provider,
            metadata={"key": "value"},
        )

        assert context.session_type == SessionType.THOUGHT
        assert context.session_config.max_items == 10
        assert context.custom_system_prompt == "Custom prompt"
        assert context.llm_provider == mock_provider
        assert context.metadata == {"key": "value"}


class TestAgentFactory:
    """Tests for AgentFactory class."""

    def test_factory_initialization(self) -> None:
        """Factory should initialize with default provider."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        assert factory._default_llm_provider == mock_provider

    def test_create_for_learning_session(self) -> None:
        """Factory should create ProactiveAgent for learning sessions."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert isinstance(agent, ProactiveAgent)

    def test_create_for_thought_session_reactive(self) -> None:
        """Factory should create ReActAgent for thought sessions (user-driven)."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.THOUGHT,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert isinstance(agent, ReActAgent)

    def test_create_for_validation_session(self) -> None:
        """Factory should create ProactiveAgent for validation sessions."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.VALIDATION,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert isinstance(agent, ProactiveAgent)

    def test_create_reactive(self) -> None:
        """create_reactive should return ReActAgent."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        agent = factory.create_reactive()

        assert isinstance(agent, ReActAgent)

    def test_create_reactive_with_custom_provider(self) -> None:
        """create_reactive should accept custom provider."""
        default_provider = MagicMock()
        custom_provider = MagicMock()
        factory = AgentFactory(default_provider)

        agent = factory.create_reactive(llm_provider=custom_provider)

        assert isinstance(agent, ReActAgent)
        assert agent._llm == custom_provider

    def test_create_proactive(self) -> None:
        """create_proactive should return ProactiveAgent."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        agent = factory.create_proactive(SessionType.LEARNING)

        assert isinstance(agent, ProactiveAgent)

    def test_create_proactive_with_custom_prompt(self) -> None:
        """create_proactive should accept custom system prompt."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        agent = factory.create_proactive(
            SessionType.LEARNING,
            custom_system_prompt="Custom system prompt",
        )

        assert isinstance(agent, ProactiveAgent)
        # Custom prompt should be in the config
        assert "Custom system prompt" in agent.config.system_prompt

    def test_create_uses_context_provider(self) -> None:
        """Factory should use provider from context if provided."""
        default_provider = MagicMock()
        context_provider = MagicMock()
        factory = AgentFactory(default_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
            llm_provider=context_provider,
        )

        agent = factory.create(context)

        assert agent._llm == context_provider

    def test_create_falls_back_to_default_provider(self) -> None:
        """Factory should use default provider when context has none."""
        default_provider = MagicMock()
        factory = AgentFactory(default_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert agent._llm == default_provider


class TestAgentConfigFromFactory:
    """Tests for agent configurations created by factory."""

    def test_proactive_agent_has_higher_max_iterations(self) -> None:
        """Proactive agents should have higher max iterations."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert agent.config.max_iterations >= 20

    def test_agent_config_includes_metadata(self) -> None:
        """Agent config should include context metadata."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
            metadata={"test_key": "test_value"},
        )

        agent = factory.create(context)

        assert agent.config.metadata == {"test_key": "test_value"}

    def test_agent_name_includes_type_and_session(self) -> None:
        """Agent name should reflect type and session type."""
        mock_provider = MagicMock()
        factory = AgentFactory(mock_provider)

        context = AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=SessionConfig(),
        )

        agent = factory.create(context)

        assert "proactive" in agent.config.name.lower()
        assert "learning" in agent.config.name.lower()
