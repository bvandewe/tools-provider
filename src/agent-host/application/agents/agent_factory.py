"""Agent Factory for Agent Host.

This module provides factory functions and classes for creating agents
based on session type, configuration, and available LLM providers.

The factory pattern centralizes agent creation logic, making it easy to:
- Create the appropriate agent type for a session
- Configure agents with session-specific settings
- Inject dependencies (LLM providers, tools, etc.)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from application.agents.agent_config import AgentConfig
from application.agents.base_agent import Agent
from application.agents.llm_provider import LlmProvider
from application.agents.proactive_agent import ProactiveAgent, get_system_prompt_for_session_type
from application.agents.react_agent import ReActAgent
from domain.models.session_models import ControlMode, SessionConfig, SessionType, get_control_mode_for_session_type

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of agents available in the system."""

    REACT = "react"
    PROACTIVE = "proactive"


# Mapping from ControlMode to AgentType
CONTROL_MODE_TO_AGENT: dict[ControlMode, AgentType] = {
    ControlMode.REACTIVE: AgentType.REACT,
    ControlMode.PROACTIVE: AgentType.PROACTIVE,
}


@dataclass
class AgentCreationContext:
    """Context for creating an agent.

    Attributes:
        session_type: Type of session (learning, thought, validation)
        session_config: Session configuration
        custom_system_prompt: Optional custom system prompt override
        llm_provider: LLM provider to use
        metadata: Additional context metadata
    """

    session_type: SessionType
    session_config: SessionConfig
    custom_system_prompt: str | None = None
    llm_provider: LlmProvider | None = None
    metadata: dict[str, Any] | None = None


class AgentFactory:
    """Factory for creating agents.

    The factory handles agent creation based on session type and configuration.
    It uses the ControlMode to determine whether to create a reactive or
    proactive agent.

    Usage:
        factory = AgentFactory(default_llm_provider)
        agent = factory.create(AgentCreationContext(
            session_type=SessionType.LEARNING,
            session_config=config,
        ))
    """

    def __init__(self, default_llm_provider: LlmProvider) -> None:
        """Initialize the agent factory.

        Args:
            default_llm_provider: Default LLM provider to use when not specified
        """
        self._default_llm_provider = default_llm_provider

    def create(self, context: AgentCreationContext) -> Agent:
        """Create an agent for the given context.

        Args:
            context: Agent creation context

        Returns:
            Configured agent instance
        """
        # Determine control mode from session type
        control_mode = get_control_mode_for_session_type(context.session_type)

        # Determine agent type from control mode
        agent_type = CONTROL_MODE_TO_AGENT.get(control_mode, AgentType.REACT)

        # Get LLM provider
        llm_provider = context.llm_provider or self._default_llm_provider

        # Build agent config
        config = self._build_config(context, agent_type)

        # Create appropriate agent
        if agent_type == AgentType.PROACTIVE:
            return ProactiveAgent(llm_provider, config)
        else:
            return ReActAgent(llm_provider, config)

    def create_reactive(
        self,
        llm_provider: LlmProvider | None = None,
        config: AgentConfig | None = None,
    ) -> ReActAgent:
        """Create a reactive (ReAct) agent.

        Args:
            llm_provider: LLM provider (uses default if None)
            config: Agent config (uses default if None)

        Returns:
            ReActAgent instance
        """
        return ReActAgent(
            llm_provider or self._default_llm_provider,
            config or AgentConfig.default(),
        )

    def create_proactive(
        self,
        session_type: SessionType,
        llm_provider: LlmProvider | None = None,
        config: AgentConfig | None = None,
        custom_system_prompt: str | None = None,
    ) -> ProactiveAgent:
        """Create a proactive agent.

        Args:
            session_type: Type of session
            llm_provider: LLM provider (uses default if None)
            config: Agent config (creates from session type if None)
            custom_system_prompt: Optional custom system prompt

        Returns:
            ProactiveAgent instance
        """
        if config is None:
            # Build config for session type
            system_prompt = get_system_prompt_for_session_type(session_type, custom_system_prompt)
            config = AgentConfig(
                name=f"proactive_{session_type.value}",
                system_prompt=system_prompt,
                max_iterations=20,  # Proactive sessions may need more iterations
                stream_responses=True,
            )

        return ProactiveAgent(
            llm_provider or self._default_llm_provider,
            config,
        )

    def _build_config(self, context: AgentCreationContext, agent_type: AgentType) -> AgentConfig:
        """Build agent config from creation context.

        Args:
            context: Creation context
            agent_type: Type of agent being created

        Returns:
            Agent configuration
        """
        # Get system prompt for session type
        system_prompt = get_system_prompt_for_session_type(context.session_type, context.custom_system_prompt)

        # Base config settings
        name = f"{agent_type.value}_{context.session_type.value}"
        max_iterations = 20 if agent_type == AgentType.PROACTIVE else 10

        # Build config with session-specific settings
        config = AgentConfig(
            name=name,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
            max_tool_calls_per_iteration=5,
            stream_responses=True,
            metadata=context.metadata or {},
        )

        return config


def get_agent_type_for_session(session_type: SessionType) -> AgentType:
    """Get the appropriate agent type for a session type.

    Args:
        session_type: Type of session

    Returns:
        Agent type to use
    """
    control_mode = get_control_mode_for_session_type(session_type)
    return CONTROL_MODE_TO_AGENT.get(control_mode, AgentType.REACT)


def is_proactive_session(session_type: SessionType) -> bool:
    """Check if a session type requires a proactive agent.

    Args:
        session_type: Type of session

    Returns:
        True if proactive agent needed
    """
    return get_agent_type_for_session(session_type) == AgentType.PROACTIVE
