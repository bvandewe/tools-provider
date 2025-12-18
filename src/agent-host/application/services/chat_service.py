"""Chat service orchestrating conversation flow with Agent and tools.

This service is the high-level orchestrator that:
- Manages conversation state (Neuroglia Aggregate)
- Delegates message processing to the Agent abstraction
- Provides tool execution capability to the agent
- Streams events to the client

The Agent abstraction handles:
- LLM interaction (via LlmProvider)
- ReAct/tool-calling loop
- Response generation
"""

import json
import logging
import random
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from observability import tool_cache_hits, tool_cache_misses
from opentelemetry import trace

from application.agents import Agent, AgentEvent, AgentEventType, LlmMessage, LlmToolDefinition
from application.agents.base_agent import AgentRunContext, ToolExecutionRequest, ToolExecutionResult
from application.services.tool_provider_client import ToolProviderClient
from application.settings import Settings
from domain.entities.conversation import Conversation
from domain.models.conversation_item import ConversationItem
from domain.models.item_content import ItemContent
from domain.models.message import Message, MessageRole, MessageStatus
from domain.models.tool import Tool
from domain.repositories import AgentDefinitionDtoRepository, ConversationTemplateDtoRepository
from infrastructure.adapters import OllamaError
from integration.models.template_dto import ConversationTemplateDto

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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
    Orchestrates the chat conversation flow using the Agent abstraction.

    Responsibilities:
    - Managing conversation state (Neuroglia Aggregate with Event Sourcing)
    - Delegating message processing to Agent
    - Providing tool execution callback to Agent
    - Translating Agent events to client stream events
    - Persisting messages to conversation

    The actual LLM interaction and tool-calling loop is handled by the Agent,
    making this service provider-agnostic.
    """

    def __init__(
        self,
        conversation_repository: Repository[Conversation, str],
        tool_provider_client: ToolProviderClient,
        agent: Agent,
        settings: Settings,
        definition_repository: AgentDefinitionDtoRepository | None = None,
        template_repository: ConversationTemplateDtoRepository | None = None,
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
                    # Note: This requires the agent to accept provider changes at runtime
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

    async def send_message(
        self,
        conversation: Conversation,
        user_message: str,
        access_token: str,
        model_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Send a user message and stream the response using the Agent.

        For templated (proactive) conversations, this method enforces deterministic
        template progression: after each user response, the next template item is
        automatically presented to the user.

        Flow:
        1. Add user message to conversation (Neuroglia Aggregate)
        2. For templated conversations: record answer, advance template
        3. Build AgentRunContext with history and tools
        4. Stream Agent events, translating to client format
        5. Persist assistant messages and tool results to conversation
        6. For templated conversations: if more items, run agent again with next item

        Args:
            conversation: The conversation (Neuroglia aggregate)
            user_message: The user's message
            access_token: User's access token for tool execution
            model_id: Optional model ID to use for this message

        Yields:
            Stream events for the client (SSE format)
        """
        # Set model override if specified
        if model_id:
            logger.info(f"🎯 Model override requested: {model_id}")
            self.set_model_override(model_id)
        else:
            logger.debug("📍 No model override specified, using default provider model")

        # Load template if this is a templated conversation
        template = await self._load_conversation_template(conversation)
        is_proactive_start = not user_message.strip()

        # Initialize template on first proactive start (if not already initialized)
        if template and is_proactive_start and conversation.get_template_config() is None:
            async for event in self._initialize_template(conversation, template):
                yield event

        # Track the item the user is responding to (for feedback)
        previous_item: ConversationItem | None = None

        # Handle user message (if provided)
        if user_message.strip():
            user_msg_id = conversation.add_user_message(user_message)

            # For templated conversations, record the answer and advance
            if template:
                current_index = conversation.get_current_template_index()
                item_order = conversation.get_item_order()
                # Get actual item from order
                if item_order and current_index < len(item_order):
                    actual_item_index = item_order[current_index]
                    previous_item = template.items[actual_item_index] if actual_item_index < len(template.items) else None
                elif current_index < len(template.items):
                    previous_item = template.items[current_index]

                if previous_item:
                    conversation.record_item_answer(
                        item_id=previous_item.id,
                        user_response=user_message,
                        is_correct=None,
                    )
                    conversation.advance_template()
                    logger.info(f"📋 Template: recorded answer for item {current_index}, advanced to {current_index + 1}")

            await self._conversation_repo.update_async(conversation)

            yield {
                "event": "message_added",
                "data": {
                    "message_id": user_msg_id,
                    "role": "user",
                    "content": user_message,
                },
            }

            # Generate feedback if the previous item has it enabled
            if template and previous_item and previous_item.provide_feedback:
                async for event in self._generate_feedback(
                    conversation=conversation,
                    item=previous_item,
                    user_response=user_message,
                    template=template,
                    access_token=access_token,
                ):
                    yield event

        else:
            # Proactive start
            logger.info("🚀 Proactive agent start - agent will speak first")
            yield {
                "event": "proactive_start",
                "data": {"message": "Agent is starting the conversation..."},
            }

        # Run the agent (potentially multiple times for templated conversations)
        async for event in self._run_templated_agent_loop(
            conversation=conversation,
            template=template,
            access_token=access_token,
            is_proactive_start=is_proactive_start,
        ):
            yield event

        # Final save and stream complete
        await self._conversation_repo.update_async(conversation)
        yield {"event": "stream_complete", "data": {}}

    async def _initialize_template(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Initialize the template for a conversation.

        Sets up:
        - Item order (shuffled if shuffle_items is enabled)
        - Deadline (if max_duration_seconds is set)
        - Client-safe template configuration

        Args:
            conversation: The conversation aggregate
            template: The conversation template

        Yields:
            template_config event for the client
        """
        # Determine item order
        item_count = len(template.items)
        if template.shuffle_items:
            item_order = list(range(item_count))
            random.shuffle(item_order)
            logger.info(f"📋 Shuffled item order: {item_order}")
        else:
            item_order = list(range(item_count))

        # Calculate deadline if max_duration is set
        deadline: datetime | None = None
        if template.max_duration_seconds:
            deadline = datetime.now(UTC) + timedelta(seconds=template.max_duration_seconds)
            logger.info(f"📋 Template deadline set to: {deadline.isoformat()}")

        # Build client-safe template config (exclude correct answers, etc.)
        template_config = {
            "template_id": template.id,
            "name": template.name,
            "agent_starts_first": template.agent_starts_first,
            "allow_navigation": template.allow_navigation,
            "allow_backward_navigation": template.allow_backward_navigation,
            "continue_after_completion": template.continue_after_completion,
            "shuffle_items": template.shuffle_items,
            "display_progress_indicator": template.display_progress_indicator,
            "display_item_title": template.display_item_title,
            "display_final_score_report": template.display_final_score_report,
            "include_feedback": template.include_feedback,
            "max_duration_seconds": template.max_duration_seconds,
            "min_duration_seconds": template.min_duration_seconds,
            "passing_score_percent": template.passing_score_percent,
            "total_items": item_count,
            "deadline": deadline.isoformat() if deadline else None,
        }

        # Initialize template in conversation
        conversation.initialize_template(
            template_id=template.id,
            template_config=template_config,
            item_order=item_order,
            deadline=deadline,
        )
        await self._conversation_repo.update_async(conversation)

        # Emit template_config event to the client
        yield {
            "event": "template_config",
            "data": template_config,
        }

    async def _run_templated_agent_loop(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto | None,
        access_token: str,
        is_proactive_start: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run the agent for templated conversations with structured widget emission.

        For templated conversations:
        1. Get the current ConversationItem from the template (using item_order for shuffled templates)
        2. For each ItemContent in the item:
           - If templated: Use LLM to generate the content
           - If static: Use the content directly
        3. Emit appropriate SSE event based on widget_type:
           - 'message' → content_chunk (streamed text)
           - 'multiple_choice' → client_action with widget data
           - 'free_text' → client_action with widget data
           - etc.
        4. Record the item as presented

        Args:
            conversation: The conversation aggregate
            template: The conversation template (or None for regular conversations)
            access_token: User's access token
            is_proactive_start: Whether this is a proactive (empty message) start

        Yields:
            Stream events for the client
        """
        if not template:
            # Regular conversation - use the standard agent pass
            tools = await self.get_tools(access_token)
            tool_definitions = [self._tool_to_llm_definition(t) for t in tools]

            async def tool_executor(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
                yield await self._execute_tool(request, access_token)

            async for event in self._run_single_agent_pass(
                conversation=conversation,
                template_instructions="",
                tool_definitions=tool_definitions,
                tool_executor=tool_executor,
                access_token=access_token,
                template=None,
            ):
                yield event
            return

        # Templated conversation - handle structured widget flow
        current_index = conversation.get_current_template_index()
        item_order = conversation.get_item_order()
        total_items = len(template.items)
        logger.info(f"📋 Template flow: current_index={current_index}, total_items={total_items}, item_order={item_order}")

        # Check if template is complete
        if current_index >= total_items:
            # Template complete - generate virtual items and closing
            async for event in self._generate_template_completion(conversation, template, access_token):
                yield event
            return

        # Get current item using item_order (for shuffled templates)
        try:
            if item_order and current_index < len(item_order):
                actual_item_index = item_order[current_index]
            else:
                actual_item_index = current_index

            if actual_item_index >= len(template.items):
                logger.error(f"❌ Invalid item index: {actual_item_index} >= {len(template.items)}")
                yield {"event": "error", "data": {"error": "Invalid template item index"}}
                return

            current_item = template.items[actual_item_index]
            logger.info(f"📋 Rendering template item {current_index + 1}/{total_items}: {current_item.title or current_item.id} (actual index: {actual_item_index})")
            logger.info(f"📋 Item has {len(current_item.contents)} raw contents")

            # Determine if we should prepend introduction message to first content
            intro_prefix = ""
            if is_proactive_start and template.introduction_message and current_index == 0:
                logger.info("📋 Will prepend introduction message to first content")
                intro_prefix = template.introduction_message + "\n\n"

            # Render each content in the item
            sorted_contents = current_item.get_sorted_contents()
            logger.info(f"📋 Item has {len(sorted_contents)} contents to render")

            for i, content in enumerate(sorted_contents):
                logger.info(f"📋 Rendering content {i + 1}/{len(sorted_contents)}: widget_type={content.widget_type}, is_templated={content.is_templated}")
                # Prepend intro to first content only
                content_prefix = intro_prefix if i == 0 else ""
                async for event in self._render_item_content(
                    conversation=conversation,
                    item=current_item,
                    content=content,
                    template=template,
                    access_token=access_token,
                    message_prefix=content_prefix,
                ):
                    yield event

            # Emit template progress with additional info for the header
            deadline = conversation.get_deadline()
            yield {
                "event": "template_progress",
                "data": {
                    "current_item": current_index,
                    "total_items": total_items,
                    "item_id": current_item.id,
                    "item_title": current_item.title if template.display_item_title else None,
                    "enable_chat_input": current_item.enable_chat_input,
                    "deadline": deadline.isoformat() if deadline else None,
                    "display_progress_indicator": template.display_progress_indicator,
                    "allow_backward_navigation": template.allow_backward_navigation and current_index > 0,
                },
            }
        except Exception as e:
            logger.exception(f"❌ Error in template rendering: {e}")
            yield {
                "event": "error",
                "data": {"error": f"Template rendering error: {str(e)}"},
            }

    async def _render_item_content(
        self,
        conversation: Conversation,
        item: "ConversationItem",
        content: "ItemContent",
        template: ConversationTemplateDto,
        access_token: str,
        message_prefix: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Render a single ItemContent and emit appropriate SSE events.

        For templated content: Uses LLM to generate the final text/options.
        For static content: Uses the content directly.

        Args:
            conversation: The conversation aggregate
            item: The parent ConversationItem
            content: The ItemContent to render
            template: The conversation template
            access_token: User's access token
            message_prefix: Optional prefix to prepend (e.g., intro message)

        Yields:
            SSE events for the client
        """
        logger.info(f"📋 _render_item_content: Starting render for content_id={content.id}, widget_type={content.widget_type}")

        # Determine if we need LLM rendering
        rendered_stem: str = content.stem or ""
        rendered_options: list[str] | None = content.options

        if content.is_templated:
            logger.info("📋 _render_item_content: Content is templated, calling LLM...")
            # Use LLM to generate content from template
            rendered_content = await self._llm_render_content(
                conversation=conversation,
                item=item,
                content=content,
                template=template,
                access_token=access_token,
            )
            logger.info(f"📋 _render_item_content: LLM rendered content: {rendered_content}")
            rendered_stem = rendered_content.get("stem", rendered_stem)
            rendered_options = rendered_content.get("options", rendered_options)

        # Prepend message_prefix if provided (e.g., intro message)
        full_message = message_prefix + rendered_stem if message_prefix else rendered_stem

        # Emit based on widget type
        logger.info(f"📋 _render_item_content: Emitting for widget_type={content.widget_type}, full message length={len(full_message)}")

        if content.widget_type == "message":
            # Simple message - stream as content chunks
            logger.info("📋 Emitting content_chunk for message widget")
            yield {"event": "content_chunk", "data": {"content": full_message}}
            # Add to conversation as assistant message
            conversation.add_assistant_message(full_message)
            await self._conversation_repo.update_async(conversation)
            yield {
                "event": "message_complete",
                "data": {"role": "assistant", "content": full_message},
            }

        else:
            # Widget-based content - emit client_action
            # For widgets, the prefix is added to the stem
            logger.info(f"📋 Emitting client_action for {content.widget_type} widget")
            widget_data = {
                "action_type": "widget",
                "content_id": content.id,
                "item_id": item.id,
                "widget_type": content.widget_type,
                "stem": full_message,  # Include prefix in stem for widgets too
                "options": rendered_options,
                "widget_config": content.widget_config,
                "required": content.required,
                "skippable": content.skippable,
                "initial_value": content.initial_value,
            }

            # Record the pending action in conversation
            conversation.request_client_action(widget_data)
            await self._conversation_repo.update_async(conversation)

            yield {
                "event": "client_action",
                "data": widget_data,
            }

    async def _llm_render_content(
        self,
        conversation: Conversation,
        item: "ConversationItem",
        content: "ItemContent",
        template: ConversationTemplateDto,
        access_token: str,
    ) -> dict[str, Any]:
        """
        Use LLM to render templated content.

        Args:
            conversation: The conversation aggregate
            item: The parent ConversationItem
            content: The ItemContent with templates
            template: The conversation template
            access_token: User's access token

        Returns:
            Dict with 'stem' and optionally 'options' keys
        """
        # Build prompt for LLM to generate content
        prompt_parts = [
            "Generate content for a conversation item based on the following template.",
            "Return ONLY the requested content as valid JSON, no explanations.",
            "",
        ]

        if content.stem:
            prompt_parts.append(f"Stem template: {content.stem}")

        if content.widget_type == "multiple_choice":
            # For multiple choice, always require options
            if content.options:
                prompt_parts.append(f"Options template/hints: {', '.join(content.options)}")
                prompt_parts.append("Generate 3-5 appropriate options based on these hints.")
            else:
                prompt_parts.append("Generate 3-5 appropriate options based on the stem/context.")
            prompt_parts.append("")
            prompt_parts.append("REQUIRED FORMAT: Return a JSON object with exactly these keys:")
            prompt_parts.append('  - "stem": A string with the question or prompt text')
            prompt_parts.append('  - "options": An array of 3-5 option strings for the user to choose from')
            prompt_parts.append("")
            prompt_parts.append('Example: {"stem": "What is your preferred language?", "options": ["Python", "JavaScript", "Go", "Rust"]}')
        else:
            if content.options:
                prompt_parts.append(f"Options template: {', '.join(content.options)}")
            prompt_parts.append("")
            prompt_parts.append("Format: Return a JSON object with 'stem' (string).")

        # Include conversation context if enabled
        llm_history = []
        if item.include_conversation_context:
            context_messages = conversation.get_context_messages(max_messages=self._settings.conversation_history_max_messages)
            history_messages = [m for m in context_messages if m.role != MessageRole.SYSTEM]
            llm_history = [self._message_to_llm_message(m) for m in history_messages]

        # Call LLM
        run_context = AgentRunContext(
            user_message="\n".join(prompt_parts),
            conversation_history=llm_history,
            tools=[],
            system_prompt_suffix="You are generating content for a structured conversation. Return valid JSON only.",
            metadata={"rendering_template": True},
        )

        # Get response from LLM (non-streaming for content generation)
        result = await self._agent.run(run_context)

        # Parse JSON response
        try:
            import json
            import re

            response_text = result.response.strip()

            # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
            code_block_pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
            match = re.match(code_block_pattern, response_text, re.DOTALL)
            if match:
                response_text = match.group(1).strip()

            parsed = json.loads(response_text)

            # Validate required fields for multiple_choice
            if content.widget_type == "multiple_choice":
                if "options" not in parsed or not isinstance(parsed.get("options"), list):
                    logger.warning(f"LLM response missing 'options' for multiple_choice widget. Response: {response_text[:200]}")
                    # Try to preserve stem but ensure options is an empty list rather than None
                    parsed["options"] = parsed.get("options") or []

            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Response: {result.response[:200]}")
            # Fallback: use response as stem, provide empty options for multiple_choice
            fallback_options = [] if content.widget_type == "multiple_choice" else content.options
            return {"stem": result.response, "options": fallback_options}

    async def _generate_feedback(
        self,
        conversation: Conversation,
        item: "ConversationItem",
        user_response: str,
        template: ConversationTemplateDto,
        access_token: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate feedback for a user's response to an item.

        This is called after the user responds to an item that has provide_feedback enabled.
        The feedback is displayed as a separate assistant message before the next item.

        Args:
            conversation: The conversation aggregate
            item: The ConversationItem that was answered
            user_response: The user's response
            template: The conversation template
            access_token: User's access token

        Yields:
            SSE events for the feedback message
        """
        logger.info(f"📋 Generating feedback for item: {item.title or item.id}")

        # Build feedback prompt
        prompt_parts = [
            "Provide brief, constructive feedback on the user's response.",
            f"Item: {item.title or 'Conversation item'}",
        ]

        # Include content context
        for content in item.contents:
            if content.stem:
                prompt_parts.append(f"Question/Prompt: {content.stem}")
            if content.correct_answer and item.reveal_correct_answer:
                prompt_parts.append(f"Correct answer: {content.correct_answer}")
            if content.explanation:
                prompt_parts.append(f"Explanation to share: {content.explanation}")

        prompt_parts.append(f"User's response: {user_response}")
        prompt_parts.append("")
        prompt_parts.append("Provide encouraging feedback. If the answer was incorrect and reveal_correct_answer is enabled, explain the correct answer.")

        # Get conversation context
        context_messages = conversation.get_context_messages(max_messages=self._settings.conversation_history_max_messages)
        history_messages = [m for m in context_messages if m.role != MessageRole.SYSTEM]
        llm_history = [self._message_to_llm_message(m) for m in history_messages]

        # Call LLM for feedback
        run_context = AgentRunContext(
            user_message="\n".join(prompt_parts),
            conversation_history=llm_history,
            tools=[],
            system_prompt_suffix="You are providing feedback on a learning activity. Be encouraging and helpful.",
            metadata={"generating_feedback": True, "item_id": item.id},
        )

        result = await self._agent.run(run_context)
        feedback = result.response

        # Emit feedback as content
        yield {"event": "content_chunk", "data": {"content": feedback}}

        # Add to conversation
        conversation.add_assistant_message(feedback)
        await self._conversation_repo.update_async(conversation)

        yield {
            "event": "message_complete",
            "data": {"role": "assistant", "content": feedback, "is_feedback": True},
        }

    async def _generate_template_completion(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto,
        access_token: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate and emit template completion with virtual items.

        Virtual items are generated in this order:
        1. Overall feedback (if include_feedback is True) - LLM-generated summary of performance
        2. Final score report (if display_final_score_report is True) - Structured score summary
        3. Completion message - The template's closing message

        After completion:
        - If continue_after_completion is True, the chat input remains enabled
        - Otherwise, the conversation is marked as complete and input is disabled
        """
        logger.info(f"📋 Generating template completion for conversation {conversation.id}")

        # Virtual Item 1: Overall Feedback (if enabled)
        if template.include_feedback:
            logger.info("📋 Generating overall feedback virtual item")
            async for event in self._generate_overall_feedback(conversation, template, access_token):
                yield event

        # Virtual Item 2: Final Score Report (if enabled)
        if template.display_final_score_report:
            logger.info("📋 Generating final score report virtual item")
            async for event in self._generate_final_score_report(conversation, template):
                yield event

        # Completion message
        completion_message = template.completion_message or "Thank you for completing this conversation."

        yield {"event": "content_chunk", "data": {"content": completion_message}}

        conversation.add_assistant_message(completion_message)
        await self._conversation_repo.update_async(conversation)

        yield {
            "event": "message_complete",
            "data": {"role": "assistant", "content": completion_message},
        }

        # Handle continue_after_completion
        if not template.continue_after_completion:
            # Mark conversation as complete - disables further input
            conversation.complete()
            await self._conversation_repo.update_async(conversation)

        yield {
            "event": "template_complete",
            "data": {
                "total_items": len(template.items),
                "total_score": conversation.get_total_score(),
                "max_possible_score": conversation.get_max_possible_score(),
                "display_final_score_report": template.display_final_score_report,
                "continue_after_completion": template.continue_after_completion,
            },
        }

    async def _generate_overall_feedback(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto,
        access_token: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate overall feedback as a virtual item using LLM.

        This provides a personalized summary of the user's performance
        across all items in the template.
        """
        item_scores = conversation.get_item_scores()
        total_score = conversation.get_total_score()
        max_score = conversation.get_max_possible_score()
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        # Build context for LLM feedback generation
        feedback_prompt = f"""You are providing overall feedback for a user who just completed a structured conversation/assessment.

Template title: {template.title or "Untitled"}
Total score: {total_score} out of {max_score} ({percentage:.1f}%)
Number of items completed: {len(item_scores)}

Item scores:
"""
        for item_id, scores in item_scores.items():
            item_total = sum(s.get("score", 0) for s in scores)
            item_max = sum(s.get("max_score", 0) for s in scores)
            feedback_prompt += f"- Item {item_id}: {item_total}/{item_max}\n"

        feedback_prompt += """
Provide a brief, encouraging overall feedback summary (2-3 sentences) that:
1. Acknowledges their effort
2. Highlights their performance level
3. Provides constructive guidance if applicable

Keep it friendly and professional."""

        # Use LLM to generate feedback
        try:
            messages = [{"role": "user", "content": feedback_prompt}]
            feedback_content = ""

            yield {"event": "content_chunk", "data": {"content": "\n\n**Overall Feedback:**\n"}}

            async for chunk in self._llm_gateway.stream_chat(
                messages=messages,
                system_prompt="You are a helpful feedback assistant.",
            ):
                content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                if content:
                    feedback_content += content
                    yield {"event": "content_chunk", "data": {"content": content}}

            # Store the feedback message
            full_feedback = f"\n\n**Overall Feedback:**\n{feedback_content}"
            conversation.add_assistant_message(full_feedback)
            await self._conversation_repo.update_async(conversation)

            yield {
                "event": "message_complete",
                "data": {"role": "assistant", "content": full_feedback, "virtual_item_type": "overall_feedback"},
            }
        except Exception as e:
            logger.error(f"Error generating overall feedback: {e}")
            # Fallback to static feedback
            fallback = f"\n\n**Overall Feedback:**\nYou scored {total_score} out of {max_score} ({percentage:.1f}%). Thank you for your participation!"
            yield {"event": "content_chunk", "data": {"content": fallback}}
            conversation.add_assistant_message(fallback)
            await self._conversation_repo.update_async(conversation)
            yield {
                "event": "message_complete",
                "data": {"role": "assistant", "content": fallback, "virtual_item_type": "overall_feedback"},
            }

    async def _generate_final_score_report(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate a structured final score report as a virtual item.

        This displays a formatted breakdown of scores per item.
        """
        item_scores = conversation.get_item_scores()
        total_score = conversation.get_total_score()
        max_score = conversation.get_max_possible_score()
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        # Build score report content
        report_lines = [
            "\n\n---",
            "## 📊 Final Score Report",
            "",
            f"**Total Score: {total_score} / {max_score} ({percentage:.1f}%)**",
            "",
        ]

        if item_scores:
            report_lines.append("### Score Breakdown:")
            report_lines.append("")

            item_order = conversation.get_item_order()
            for display_idx, (item_id, scores) in enumerate(item_scores.items()):
                # Try to get item title from template
                item_title = None
                try:
                    actual_idx = item_order[display_idx] if item_order else display_idx
                    if actual_idx < len(template.items):
                        item_title = template.items[actual_idx].title
                except (IndexError, TypeError):
                    pass

                item_total = sum(s.get("score", 0) for s in scores)
                item_max = sum(s.get("max_score", 0) for s in scores)
                item_pct = (item_total / item_max * 100) if item_max > 0 else 0

                item_label = item_title or f"Item {display_idx + 1}"
                correct_count = sum(1 for s in scores if s.get("is_correct", False))
                total_count = len(scores)

                report_lines.append(f"- **{item_label}**: {item_total}/{item_max} ({item_pct:.0f}%) - {correct_count}/{total_count} correct")

            report_lines.append("")

        report_lines.append("---")
        report_content = "\n".join(report_lines)

        yield {"event": "content_chunk", "data": {"content": report_content}}

        conversation.add_assistant_message(report_content)
        await self._conversation_repo.update_async(conversation)

        yield {
            "event": "message_complete",
            "data": {"role": "assistant", "content": report_content, "virtual_item_type": "final_score_report"},
        }

    # =========================================================================
    # WebSocket-based Template Flow
    # =========================================================================

    async def run_websocket_template(
        self,
        conversation: Conversation,
        user_message: str,
        access_token: str,
        websocket: Any,  # WebSocket type, but using Any to avoid circular import
        model_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Handle template conversation flow for WebSocket connections.

        This method is designed for bidirectional WebSocket communication,
        yielding events that can be sent directly to the client. Unlike the
        SSE-based `send_message`, this method:
        - Uses simpler event types (content, widget, progress, complete)
        - Doesn't need to track pending actions (the connection stays open)
        - Can receive user responses immediately through the same connection

        Args:
            conversation: The conversation aggregate
            user_message: The user's message (empty string for proactive start)
            access_token: User's access token for tool execution
            websocket: The WebSocket connection (for potential direct sends)
            model_id: Optional model override

        Yields:
            Events to send to the WebSocket client
        """
        # Set model override if specified
        if model_id:
            self.set_model_override(model_id)

        # Load template if this is a templated conversation
        template = await self._load_conversation_template(conversation)
        is_proactive_start = not user_message.strip()

        # Emit template_config at proactive start (like SSE does)
        if template and is_proactive_start:
            template_config = {
                "title": template.name,
                "total_items": len(template.items),
                "allow_navigation": template.allow_navigation,
                "allow_backward_navigation": template.allow_backward_navigation,
                "display_progress_indicator": template.display_progress_indicator,
                "display_final_score_report": template.display_final_score_report,
                "continue_after_completion": template.continue_after_completion,
            }
            yield {"type": "template_config", "data": template_config}

        # Track the item the user is responding to (for feedback)
        previous_item: ConversationItem | None = None

        # Handle user message (if provided)
        if user_message.strip():
            user_msg_id = conversation.add_user_message(user_message)

            # For templated conversations, record the answer and advance
            if template:
                current_index = conversation.get_current_template_index()
                if current_index < len(template.items):
                    previous_item = template.items[current_index]
                    conversation.record_item_answer(
                        item_id=previous_item.id,
                        user_response=user_message,
                        is_correct=None,
                    )
                    conversation.advance_template()
                    logger.info(f"📋 WS Template: recorded answer for item {current_index}, advanced to {current_index + 1}")

            await self._conversation_repo.update_async(conversation)

            yield {
                "type": "message_added",
                "data": {
                    "message_id": user_msg_id,
                    "role": "user",
                    "content": user_message,
                },
            }

            # Generate feedback if the previous item has it enabled
            if template and previous_item and previous_item.provide_feedback:
                async for event in self._generate_ws_feedback(
                    conversation=conversation,
                    item=previous_item,
                    user_response=user_message,
                    template=template,
                    access_token=access_token,
                ):
                    yield event
        else:
            # Proactive start
            logger.info("🚀 WS Proactive agent start")

        # Run the template flow
        if template:
            async for event in self._run_ws_template_loop(
                conversation=conversation,
                template=template,
                access_token=access_token,
                is_proactive_start=is_proactive_start,
            ):
                yield event
        else:
            # Non-templated conversation - run regular agent
            tools = await self.get_tools(access_token)
            tool_definitions = [self._tool_to_llm_definition(t) for t in tools]

            async def tool_executor(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
                yield await self._execute_tool(request, access_token)

            async for event in self._run_ws_agent_pass(
                conversation=conversation,
                tool_definitions=tool_definitions,
                tool_executor=tool_executor,
                access_token=access_token,
            ):
                yield event

        # Final save
        await self._conversation_repo.update_async(conversation)

    async def _run_ws_template_loop(
        self,
        conversation: Conversation,
        template: ConversationTemplateDto,
        access_token: str,
        is_proactive_start: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run the template loop for WebSocket connections.

        Renders the current template item and yields events to send to the client.

        Args:
            conversation: The conversation aggregate
            template: The conversation template
            access_token: User's access token
            is_proactive_start: Whether this is a proactive (empty message) start

        Yields:
            Events to send to the WebSocket client
        """
        current_index = conversation.get_current_template_index()
        logger.info(f"📋 WS Template: current_index={current_index}, total_items={len(template.items)}")

        # Check if template is complete
        if current_index >= len(template.items):
            # Template complete - generate closing message
            completion_message = template.completion_message or "Thank you for completing this conversation."

            yield {"type": "content", "data": {"content": completion_message}}

            conversation.add_assistant_message(completion_message)
            conversation.complete()
            await self._conversation_repo.update_async(conversation)

            yield {
                "type": "complete",
                "data": {
                    "total_items": len(template.items),
                    "display_final_score_report": template.display_final_score_report,
                },
            }
            return

        # Get current item
        try:
            current_item = template.items[current_index]
            logger.info(f"📋 WS Rendering item {current_index + 1}/{len(template.items)}: {current_item.title or current_item.id}")

            # Determine if we should prepend introduction message
            intro_prefix = ""
            if is_proactive_start and template.introduction_message and current_index == 0:
                intro_prefix = template.introduction_message + "\n\n"

            # Render each content in the item
            sorted_contents = current_item.get_sorted_contents()

            for i, content in enumerate(sorted_contents):
                content_prefix = intro_prefix if i == 0 else ""
                async for event in self._render_ws_item_content(
                    conversation=conversation,
                    item=current_item,
                    content=content,
                    template=template,
                    access_token=access_token,
                    message_prefix=content_prefix,
                ):
                    yield event

            # Emit progress
            yield {
                "type": "progress",
                "data": {
                    "current_item": current_index,
                    "total_items": len(template.items),
                    "item_id": current_item.id,
                    "item_title": current_item.title,
                    "enable_chat_input": current_item.enable_chat_input,
                    "display_progress_indicator": template.display_progress_indicator,
                    "allow_backward_navigation": template.allow_backward_navigation,
                },
            }

        except Exception as e:
            logger.exception(f"❌ WS Template error: {e}")
            yield {"type": "error", "message": f"Template error: {str(e)}"}

    async def _render_ws_item_content(
        self,
        conversation: Conversation,
        item: "ConversationItem",
        content: "ItemContent",
        template: ConversationTemplateDto,
        access_token: str,
        message_prefix: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Render a single ItemContent for WebSocket and yield events.

        Args:
            conversation: The conversation aggregate
            item: The parent ConversationItem
            content: The ItemContent to render
            template: The conversation template
            access_token: User's access token
            message_prefix: Optional prefix to prepend (e.g., intro message)

        Yields:
            Events to send to the WebSocket client
        """
        # Determine if we need LLM rendering
        rendered_stem: str = content.stem or ""
        rendered_options: list[str] | None = content.options

        logger.info(
            f"🎯 Rendering content: id={content.id}, widget_type={content.widget_type}, "
            f"is_templated={content.is_templated}, stem={content.stem[:50] if content.stem else None}..., "
            f"options={content.options}"
        )

        if content.is_templated:
            logger.info(f"🔄 Calling LLM to render templated content: {content.id}")
            rendered_content = await self._llm_render_content(
                conversation=conversation,
                item=item,
                content=content,
                template=template,
                access_token=access_token,
            )
            logger.info(f"✅ LLM rendered content: stem={rendered_content.get('stem', '')[:50]}..., options={rendered_content.get('options')}")
            rendered_stem = rendered_content.get("stem", rendered_stem)
            rendered_options = rendered_content.get("options", rendered_options)

        # Prepend message_prefix
        full_message = message_prefix + rendered_stem if message_prefix else rendered_stem

        if content.widget_type == "message":
            # Simple message content
            yield {"type": "content", "data": {"content": full_message}}

            conversation.add_assistant_message(full_message)
            await self._conversation_repo.update_async(conversation)

        else:
            # Widget-based content
            widget_data = {
                "content_id": content.id,
                "item_id": item.id,
                "widget_type": content.widget_type,
                "stem": full_message,
                "options": rendered_options,
                "widget_config": content.widget_config,
                "required": content.required,
                "skippable": content.skippable,
                "initial_value": content.initial_value,
                "show_user_response": content.show_user_response,
            }

            yield {"type": "widget", "data": widget_data}

    async def _generate_ws_feedback(
        self,
        conversation: Conversation,
        item: "ConversationItem",
        user_response: str,
        template: ConversationTemplateDto,
        access_token: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Generate feedback for WebSocket connections."""
        logger.info(f"📋 WS Generating feedback for item: {item.title or item.id}")

        # Reuse the existing feedback generation logic
        async for event in self._generate_feedback(
            conversation=conversation,
            item=item,
            user_response=user_response,
            template=template,
            access_token=access_token,
        ):
            # Convert SSE event format to WebSocket format
            if event.get("event") == "content_chunk":
                yield {"type": "content", "data": event.get("data", {})}
            elif event.get("event") == "message_complete":
                yield {"type": "message_complete", "data": event.get("data", {})}
            else:
                yield event

    async def _run_ws_agent_pass(
        self,
        conversation: Conversation,
        tool_definitions: list[LlmToolDefinition],
        tool_executor,
        access_token: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run a single agent pass for WebSocket (non-templated conversations).

        This handles regular chat messages where the agent can use tools.
        """
        # Build context from conversation history
        context_messages = conversation.get_context_messages(max_messages=self._settings.conversation_history_max_messages)
        llm_history = [self._message_to_llm_message(m) for m in context_messages]

        # Get the last user message as the current message
        user_messages = [m for m in context_messages if m.role == MessageRole.USER]
        current_message = user_messages[-1].content if user_messages else ""

        run_context = AgentRunContext(
            user_message=current_message,
            conversation_history=llm_history[:-1] if llm_history else [],
            tools=tool_definitions,
            tool_executor=tool_executor,
            system_prompt_suffix="",
            metadata={},
        )

        # Use non-streaming run() method since ReActAgent doesn't have stream()
        # TODO: Implement proper streaming in ReActAgent for better UX
        try:
            result = await self._agent.run(run_context)

            if result.success and result.response:
                # Emit content as a single chunk
                yield {"type": "content", "data": {"content": result.response}}

                # Save the response to conversation
                conversation.add_assistant_message(result.response)
                await self._conversation_repo.update_async(conversation)

                yield {"type": "message_complete", "data": {"role": "assistant", "content": result.response}}
            elif result.error:
                yield {"type": "error", "message": str(result.error.message)}
            else:
                yield {"type": "error", "message": "Agent returned empty response"}
        except Exception as e:
            logger.exception(f"Error in agent pass: {e}")
            yield {"type": "error", "message": str(e)}

    async def _run_single_agent_pass(
        self,
        conversation: Conversation,
        template_instructions: str,
        tool_definitions: list[LlmToolDefinition],
        tool_executor,
        access_token: str,
        template: ConversationTemplateDto | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run a single agent pass (one LLM call cycle with potential tool use).

        For templated conversations, the template instructions are injected into the
        system prompt (not as a user message), ensuring the LLM follows the template
        while responding to the actual conversation history.

        Args:
            conversation: The conversation aggregate
            template_instructions: Instructions for the agent (appended to system prompt)
            tool_definitions: Available tool definitions
            tool_executor: Function to execute tools
            access_token: User's access token
            template: The conversation template (for metadata)

        Yields:
            Stream events for the client
        """
        # Get conversation history
        context_messages = conversation.get_context_messages(max_messages=self._settings.conversation_history_max_messages)
        history_messages = [m for m in context_messages if m.role != MessageRole.SYSTEM]
        llm_history = [self._message_to_llm_message(m) for m in history_messages]

        # For templated conversations:
        # - template_instructions go into system_prompt_suffix (agent guidance)
        # - user_message is empty (agent responds based on history + template instructions)
        # For regular conversations:
        # - No system_prompt_suffix
        # - user_message would be set if needed (but we use history)

        run_context = AgentRunContext(
            user_message="",  # Empty - agent responds to conversation history
            conversation_history=llm_history,
            tools=tool_definitions,
            tool_executor=tool_executor,
            access_token=access_token,
            system_prompt_suffix=template_instructions if template_instructions else None,
            metadata={
                "conversation_id": conversation.id(),
                "user_id": conversation.state.user_id,
                "is_templated": template is not None,
                "template_id": template.id if template else None,
                "current_item_index": conversation.get_current_template_index() if template else None,
            },
        )

        current_assistant_msg_id: str | None = None
        current_assistant_content: str = ""

        try:
            async for event in self._agent.run_stream(run_context):
                if event.type == AgentEventType.LLM_REQUEST_STARTED:
                    yield {"event": "assistant_thinking", "data": {}}

                elif event.type == AgentEventType.LLM_RESPONSE_CHUNK:
                    chunk = event.data.get("content", "")
                    current_assistant_content += chunk
                    yield {"event": "content_chunk", "data": {"content": chunk}}

                elif event.type == AgentEventType.LLM_RESPONSE_COMPLETED:
                    tool_calls = event.data.get("tool_calls", [])
                    status = MessageStatus.PENDING if tool_calls else MessageStatus.COMPLETED

                    current_assistant_msg_id = conversation.add_assistant_message(
                        content=current_assistant_content,
                        status=status,
                    )

                    for tc in tool_calls:
                        conversation.add_tool_call(
                            message_id=current_assistant_msg_id,
                            tool_name=tc.get("name", ""),
                            arguments=tc.get("arguments", {}),
                            call_id=tc.get("id", ""),
                        )

                    await self._conversation_repo.update_async(conversation)

                elif event.type == AgentEventType.TOOL_CALLS_DETECTED:
                    yield {
                        "event": "tool_calls_detected",
                        "data": {"tool_calls": [{"tool_name": tc.get("name", ""), "arguments": tc.get("arguments", {})} for tc in event.data.get("tool_calls", [])]},
                    }

                elif event.type == AgentEventType.TOOL_EXECUTION_STARTED:
                    yield {
                        "event": "tool_executing",
                        "data": {
                            "call_id": event.data.get("call_id", ""),
                            "tool_name": event.data.get("tool_name", ""),
                        },
                    }

                elif event.type == AgentEventType.TOOL_EXECUTION_COMPLETED:
                    result = event.data
                    yield {
                        "event": "tool_result",
                        "data": {
                            "call_id": result.get("call_id", ""),
                            "tool_name": result.get("tool_name", ""),
                            "success": result.get("success", True),
                            "result": result.get("result"),
                            "error": result.get("error"),
                            "execution_time_ms": result.get("execution_time_ms", 0),
                        },
                    }

                    if current_assistant_msg_id:
                        conversation.add_tool_result(
                            message_id=current_assistant_msg_id,
                            call_id=result.get("call_id", ""),
                            tool_name=result.get("tool_name", ""),
                            success=result.get("success", True),
                            result=result.get("result"),
                            error=result.get("error"),
                            execution_time_ms=result.get("execution_time_ms", 0),
                        )

                elif event.type == AgentEventType.TOOL_EXECUTION_FAILED:
                    yield {
                        "event": "tool_result",
                        "data": {
                            "call_id": event.data.get("call_id", ""),
                            "tool_name": event.data.get("tool_name", ""),
                            "success": False,
                            "error": event.data.get("error", "Unknown error"),
                        },
                    }

                elif event.type == AgentEventType.RUN_COMPLETED:
                    if current_assistant_msg_id:
                        conversation.update_message_status(current_assistant_msg_id, MessageStatus.COMPLETED)
                    await self._conversation_repo.update_async(conversation)

                    yield {
                        "event": "message_complete",
                        "data": {
                            "message_id": current_assistant_msg_id,
                            "role": "assistant",
                            "content": current_assistant_content,
                        },
                    }

                    # For templated conversations, emit progress info
                    if template:
                        current_index = conversation.get_current_template_index()
                        total_items = len(template.items)
                        yield {
                            "event": "template_progress",
                            "data": {
                                "current_item": current_index,
                                "total_items": total_items,
                                "is_complete": current_index >= total_items,
                            },
                        }

                elif event.type == AgentEventType.RUN_FAILED:
                    error = event.data.get("error", "Unknown error")
                    yield {"event": "error", "data": {"error": str(error)}}

                elif event.type == AgentEventType.ITERATION_STARTED:
                    current_assistant_content = ""

        except OllamaError as e:
            logger.error(f"Ollama error: {e.error_code} - {e.message}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": e.message,
                    "error_code": e.error_code,
                    "is_retryable": e.is_retryable,
                    "details": e.details,
                },
            }
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": "Cannot connect to AI service. Please try again later.",
                    "error_code": "connection_error",
                    "is_retryable": True,
                },
            }
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": "Request timed out. The AI model may be busy.",
                    "error_code": "timeout",
                    "is_retryable": True,
                },
            }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": {
                    "error": str(e),
                    "error_code": "unknown_error",
                    "is_retryable": False,
                },
            }

    def _build_template_completion_context(self, template: ConversationTemplateDto) -> str:
        """Build context for when the template is complete."""
        parts = [
            "You have covered all the topics in this conversation template.",
            "Provide a brief summary or closing statement.",
        ]
        if template.include_feedback:
            parts.append("Offer any final feedback on the user's responses.")
        return "\n".join(parts)

    async def _execute_tool(
        self,
        request: ToolExecutionRequest,
        access_token: str,
    ) -> ToolExecutionResult:
        """
        Execute a tool call via the Tools Provider.

        Args:
            request: Tool execution request from the agent
            access_token: User's access token for authentication

        Returns:
            The tool execution result
        """
        start_time = time.time()
        try:
            result = await self._tool_provider.execute_tool(
                tool_name=request.tool_name,
                arguments=request.arguments,
                access_token=access_token,
            )
            execution_time = (time.time() - start_time) * 1000

            return ToolExecutionResult(
                call_id=request.call_id,
                tool_name=request.tool_name,
                success=result.get("success", True),
                result=result.get("data", result.get("result", result)),
                error=result.get("error"),
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolExecutionResult(
                call_id=request.call_id,
                tool_name=request.tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time,
            )

    def _tool_to_llm_definition(self, tool: Tool) -> LlmToolDefinition:
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
        logger.debug(f"_tool_to_llm_definition for '{tool.name}': {len(tool.parameters)} params -> {llm_def.parameters}")
        return llm_def

    def _message_to_llm_message(self, message: Message) -> LlmMessage:
        """Convert a domain Message to an LlmMessage."""
        if message.role == MessageRole.SYSTEM:
            return LlmMessage.system(message.content)
        elif message.role == MessageRole.USER:
            return LlmMessage.user(message.content)
        elif message.role == MessageRole.ASSISTANT:
            # Handle tool calls if present
            if message.tool_calls:
                from application.agents import LlmToolCall

                tool_calls = [
                    LlmToolCall(
                        id=tc.call_id,
                        name=tc.tool_name,
                        arguments=tc.arguments,
                    )
                    for tc in message.tool_calls
                ]
                return LlmMessage.assistant(message.content, tool_calls=tool_calls)
            return LlmMessage.assistant(message.content)
        elif message.role == MessageRole.TOOL:
            # For tool results
            if message.tool_results:
                tr = message.tool_results[0]  # Use first tool result
                content = json.dumps(tr.result) if tr.success else f"Error: {tr.error}"
                return LlmMessage.tool_result(
                    tool_call_id=tr.call_id,
                    tool_name=tr.tool_name,
                    content=content,
                )
            return LlmMessage.user(message.content)  # Fallback
        else:
            return LlmMessage.user(message.content)

    def _translate_agent_event(
        self,
        event: AgentEvent,
        conversation: Conversation,
        current_msg_id: str | None,
    ) -> dict[str, Any]:
        """
        Translate an AgentEvent to client-friendly format.

        This is a passthrough for now but can be extended for
        custom event transformations.
        """
        return event.to_dict()

    async def _load_conversation_template(self, conversation: Conversation) -> ConversationTemplateDto | None:
        """
        Load the conversation template for a conversation based on its definition.

        Args:
            conversation: The conversation to load template for

        Returns:
            The ConversationTemplateDto or None if not found
        """
        if not self._definition_repo or not self._template_repo:
            logger.debug("Definition or template repository not available")
            return None

        # Get definition_id from conversation
        definition_id = getattr(conversation.state, "definition_id", None)
        if not definition_id:
            logger.debug("No definition_id on conversation")
            return None

        try:
            # Load the definition
            definition = await self._definition_repo.get_async(definition_id)
            if not definition:
                logger.warning(f"Definition not found: {definition_id}")
                return None

            # Check if definition has a template
            if not definition.conversation_template_id:
                logger.debug(f"Definition {definition_id} has no template")
                return None

            # Load the template
            template = await self._template_repo.get_async(definition.conversation_template_id)
            if not template:
                logger.warning(f"Template not found: {definition.conversation_template_id}")
                return None

            return template

        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None

    def _build_template_context(self, template: ConversationTemplateDto, conversation: Conversation) -> str:
        """
        Build a context string from the template to guide the agent's first message.

        This creates a prompt that tells the agent how to start the conversation
        based on the template's configuration.

        Args:
            template: The conversation template
            conversation: The conversation (to check progress)

        Returns:
            A context string for the agent
        """
        parts = []

        # Start with instruction
        parts.append("You are starting a new conversation. Follow this template to guide the interaction:")
        parts.append("")

        # Add introduction message if available
        if template.introduction_message:
            parts.append("## Your First Message")
            parts.append("Start the conversation with this introduction:")
            parts.append(f'"{template.introduction_message}"')
            parts.append("")

        # Add first item content if available
        if template.items:
            first_item = template.items[0]
            parts.append(f"## First Topic: {first_item.title or 'Item 1'}")

            # Add the first item's content (stem holds the question/prompt text)
            if first_item.contents:
                first_content = first_item.contents[0]
                if first_content.stem:
                    parts.append(f"Present this to the user: {first_content.stem}")
            parts.append("")

        # Add behavioral instructions based on template settings
        if template.include_feedback:
            parts.append("Provide feedback on user responses when appropriate.")

        if template.display_progress_indicator:
            parts.append(f"This conversation has {len(template.items)} items to cover.")

        # Combine all parts
        return "\n".join(parts)

    def _build_current_item_context(self, template: ConversationTemplateDto, conversation: Conversation) -> str:
        """
        Build context for the current template item to guide the agent's next response.

        This is called after each user message to tell the agent what topic to cover next.

        Args:
            template: The conversation template
            conversation: The conversation (to check progress)

        Returns:
            A context string for the agent, or empty string if template is complete
        """
        current_index = conversation.get_current_template_index()

        # Check if we've completed all items
        if current_index >= len(template.items):
            # Template complete - let agent wrap up naturally
            parts = [
                "You have covered all the topics in this conversation template.",
                "Provide a brief summary or closing statement if appropriate.",
            ]
            if template.include_feedback:
                parts.append("Offer any final feedback on the user's responses.")
            return "\n".join(parts)

        # Get current item
        current_item = template.items[current_index]
        parts = []

        parts.append(f"Now cover Topic {current_index + 1} of {len(template.items)}: {current_item.title or f'Item {current_index + 1}'}")

        # Add the item's content (stem)
        if current_item.contents:
            for content in current_item.contents:
                if content.stem:
                    parts.append(f"Present this to the user: {content.stem}")
                if content.widget_type == "multiple_choice" and content.options:
                    parts.append(f"Options: {', '.join(content.options)}")

        # Add feedback instruction if enabled
        if template.include_feedback:
            parts.append("Provide feedback on the user's previous response before presenting this topic.")

        # Progress indicator
        if template.display_progress_indicator:
            parts.append(f"Progress: {current_index + 1}/{len(template.items)} topics")

        return "\n".join(parts)

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
        from domain.repositories import AgentDefinitionDtoRepository, ConversationTemplateDtoRepository

        builder.services.add_scoped(
            ChatService,
            implementation_factory=lambda sp: ChatService(
                conversation_repository=sp.get_required_service(Repository[Conversation, str]),
                tool_provider_client=sp.get_required_service(ToolProviderClient),
                agent=sp.get_required_service(Agent),
                settings=app_settings,
                definition_repository=sp.get_required_service(AgentDefinitionDtoRepository),
                template_repository=sp.get_required_service(ConversationTemplateDtoRepository),
            ),
        )
        logger.info("Configured ChatService as scoped service")
