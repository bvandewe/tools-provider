"""Chat service providing tool access and conversation utilities.

This service provides:
- Tool fetching from Tools Provider with caching
- Conversation utility methods (get/create, clear, delete)
- Model override support for multi-provider architecture

Note: Message streaming is now handled via WebSocket through ConversationOrchestrator.
Legacy streaming methods have been removed in favor of the WebSocket protocol.
"""

import logging

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase

from application.agents import Agent, LlmToolDefinition
from application.services.tool_provider_client import ToolProviderClient
from application.settings import Settings
from domain.entities.conversation import Conversation
from domain.models.tool import Tool
from domain.repositories import AgentDefinitionRepository, ConversationTemplateRepository
from observability import tool_cache_hits, tool_cache_misses

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Custom exception for chat service errors with user-friendly messages."""

    def __init__(self, message: str, error_code: str, is_retryable: bool = False, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "error_code": self.error_code,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }


class ChatService:
    """
    Provides tool access and conversation utilities.

    Responsibilities:
    - Fetching and caching tools from Tools Provider
    - Model override support for multi-provider LLM architecture
    - Conversation utility methods (CRUD operations)

    Note: Message streaming is handled via WebSocket through ConversationOrchestrator.
    """

    def __init__(
        self,
        conversation_repository: Repository[Conversation, str],
        tool_provider_client: ToolProviderClient,
        agent: Agent,
        settings: Settings,
        definition_repository: AgentDefinitionRepository | None = None,
        template_repository: ConversationTemplateRepository | None = None,
    ) -> None:
        """
        Initialize the chat service.

        Args:
            conversation_repository: Repository for conversation persistence (EventSourcing)
            tool_provider_client: Client for Tools Provider API
            agent: The agent implementation (e.g., ReActAgent)
            settings: Application settings
            definition_repository: Optional repository for agent definitions (read model)
            template_repository: Optional repository for conversation templates (read model)
        """
        self._conversation_repo = conversation_repository
        self._tool_provider = tool_provider_client
        self._agent = agent
        self._settings = settings
        self._definition_repo = definition_repository
        self._template_repo = template_repository
        self._tools_cache: dict[str, list[Tool]] = {}

    def set_model_override(self, model: str | None) -> None:
        """Set a temporary model override for this conversation.

        This method supports the multi-provider architecture. When a model ID
        is provided with a provider prefix (e.g., 'openai:gpt-4o', 'ollama:llama3'),
        it uses the factory to get the appropriate provider. Otherwise, it
        attempts to use the current provider's set_model_override method.

        Args:
            model: Model name to use (optionally prefixed with provider:), or None to clear override
        """
        from application.agents import LlmProvider

        logger.debug(f"🔄 set_model_override called with model='{model}'")

        if model is None:
            # Clear override on the current provider
            logger.debug("🔄 Clearing model override")
            if hasattr(self._agent, "_llm") and isinstance(self._agent._llm, LlmProvider):
                self._agent._llm.set_model_override(None)
            return

        # Check if model has a provider prefix
        if ":" in model:
            # Model is qualified (e.g., "openai:gpt-4o"), use factory singleton
            from infrastructure import get_provider_factory

            logger.info(f"🔄 Qualified model ID detected: '{model}', routing to factory")
            try:
                factory = get_provider_factory()
                if factory is None:
                    logger.error("🔄 LlmProviderFactory singleton not initialized!")
                    return

                provider = factory.get_provider_for_model(model)
                if provider and provider != self._agent._llm:
                    # Switch to the new provider
                    if hasattr(self._agent, "_llm"):
                        old_provider = type(self._agent._llm).__name__
                        self._agent._llm = provider
                        logger.info(f"🔄 Switched provider from {old_provider} to {type(provider).__name__} for model: {model}")
                elif provider:
                    # Same provider, just update the model override
                    actual_model = model.split(":", 1)[1]
                    provider.set_model_override(actual_model)
                    logger.info(f"🔄 Same provider, updated model override to: {actual_model}")
            except Exception as e:
                logger.warning(f"Failed to get provider for model '{model}': {e}", exc_info=True)
        else:
            # No provider prefix, use current provider's override
            logger.debug(f"🔄 Unqualified model ID: '{model}', using current provider override")
            if hasattr(self._agent, "_llm") and isinstance(self._agent._llm, LlmProvider):
                self._agent._llm.set_model_override(model)
                logger.info(f"🔄 Set model override to: {model}")
            else:
                logger.warning("Cannot set model override - LLM provider does not support it")

    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: str | None = None,
        definition_id: str | None = None,
    ) -> Conversation:
        """
        Get an existing conversation or create a new one.

        Args:
            user_id: The user ID
            conversation_id: Optional specific conversation ID
            definition_id: Optional agent definition ID for new conversations

        Returns:
            The conversation
        """
        if conversation_id:
            conversation = await self._conversation_repo.get_async(conversation_id)
            if conversation and conversation.state.user_id == user_id:
                return conversation

        # Create new conversation with system prompt (Neuroglia pattern)
        conversation = Conversation(
            user_id=user_id,
            definition_id=definition_id or "",
            system_prompt=self._agent.config.system_prompt,
        )
        return await self._conversation_repo.add_async(conversation)

    async def get_tools(self, access_token: str, force_refresh: bool = False) -> list[Tool]:
        """
        Get available tools, using cache if available.

        Args:
            access_token: User's access token
            force_refresh: Force refresh from Tools Provider

        Returns:
            List of available tools
        """
        cache_key = "tools"  # Could use user-specific key if needed

        if not force_refresh and cache_key in self._tools_cache:
            tool_cache_hits.add(1)
            return self._tools_cache[cache_key]

        tool_cache_misses.add(1)

        try:
            tool_data = await self._tool_provider.get_tools(access_token)
            tools = [Tool.from_bff_response(t) for t in tool_data]

            # Debug: log parsed tool parameters
            for t in tools:
                logger.debug(f"Parsed Tool '{t.name}' has {len(t.parameters)} parameters: {[p.name for p in t.parameters]}")

            # Apply tool filtering from agent config
            if self._agent.config.tool_whitelist:
                tools = [t for t in tools if t.name in self._agent.config.tool_whitelist]
            if self._agent.config.tool_blacklist:
                tools = [t for t in tools if t.name not in self._agent.config.tool_blacklist]

            self._tools_cache[cache_key] = tools
            logger.debug(f"Cached {len(tools)} tools (filtered from config)")
            return tools
        except Exception as e:
            logger.error(f"Failed to fetch tools: {e}")
            # Return cached tools if available
            return self._tools_cache.get(cache_key, [])

    def tool_to_llm_definition(self, tool: Tool) -> LlmToolDefinition:
        """Convert a domain Tool to an LLM tool definition.

        Uses ToolParameter.to_json_schema() to preserve full schema information
        including 'items' for arrays and 'properties' for objects, which is
        required by OpenAI's API.
        """
        llm_def = LlmToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters={
                "type": "object",
                "properties": {p.name: p.to_json_schema() for p in tool.parameters},
                "required": [p.name for p in tool.parameters if p.required],
            },
        )
        logger.debug(f"tool_to_llm_definition for '{tool.name}': {len(tool.parameters)} params -> {llm_def.parameters}")
        return llm_def

    async def clear_conversation(self, conversation: Conversation) -> Conversation:
        """
        Clear a conversation's messages (keeps system prompt).

        Args:
            conversation: The conversation to clear

        Returns:
            The cleared conversation
        """
        conversation.clear_messages(keep_system=True)
        await self._conversation_repo.update_async(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted
        """
        conversation = await self._conversation_repo.get_async(conversation_id)
        if conversation:
            conversation.delete()
            await self._conversation_repo.remove_async(conversation_id)
            return True
        return False

    async def get_conversations(self, user_id: str) -> list[Conversation]:
        """
        Get all conversations for a user.

        Note: This queries the read model for efficiency.
        For full aggregates, use the EventSourcing repository.

        Args:
            user_id: The user ID

        Returns:
            List of conversations (as aggregates)
        """
        # For now, return empty - the read model repository should be used for queries
        # This method is kept for backward compatibility but queries should use CQRS
        return []

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure ChatService as a scoped service in the DI container.

        ChatService is registered as scoped because it depends on Repository[Conversation, str]
        which is also scoped (one repository instance per request scope).

        Args:
            builder: The application builder
        """
        from application.agents import Agent
        from application.settings import app_settings
        from domain.entities import Conversation
        from domain.repositories import AgentDefinitionRepository, ConversationTemplateRepository

        builder.services.add_scoped(
            ChatService,
            implementation_factory=lambda sp: ChatService(
                conversation_repository=sp.get_required_service(Repository[Conversation, str]),
                tool_provider_client=sp.get_required_service(ToolProviderClient),
                agent=sp.get_required_service(Agent),
                settings=app_settings,
                definition_repository=sp.get_required_service(AgentDefinitionRepository),
                template_repository=sp.get_required_service(ConversationTemplateRepository),
            ),
        )
        logger.info("Configured ChatService as scoped service")
