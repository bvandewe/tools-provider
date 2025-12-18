"""Agent Service - Stateless service for executing conversations.

This service replaces the old Agent aggregate pattern. Instead of maintaining
agent state, it loads Conversation + AgentDefinition and executes the agent loop.

All state is persisted in the Conversation aggregate (event-sourced).
"""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from application.agents import (
    Agent,
    AgentEvent,
    AgentEventType,
    AgentRunContext,
    LlmMessage,
    LlmToolDefinition,
)
from domain.entities.conversation import Conversation
from domain.models import SkillTemplate
from domain.models.client_response import ClientResponse
from domain.models.message import MessageRole
from domain.models.tool import Tool
from integration.models.definition_dto import AgentDefinitionDto
from integration.models.template_dto import ConversationTemplateDto

logger = logging.getLogger(__name__)


class AgentServiceEventType(str, Enum):
    """Events emitted by the AgentService."""

    # Conversation lifecycle
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_SUSPENDED = "conversation_suspended"
    CONVERSATION_COMPLETED = "conversation_completed"

    # Template/proactive events
    ITEM_GENERATED = "item_generated"
    ITEM_PRESENTED = "item_presented"
    ITEM_ANSWERED = "item_answered"
    TEMPLATE_ADVANCED = "template_advanced"

    # Passthrough from underlying Agent
    AGENT_EVENT = "agent_event"


@dataclass
class AgentServiceEvent:
    """Event emitted by AgentService."""

    type: AgentServiceEventType
    data: dict[str, Any]
    timestamp: datetime

    @classmethod
    def from_agent_event(cls, event: AgentEvent) -> "AgentServiceEvent":
        """Wrap an Agent event."""
        return cls(
            type=AgentServiceEventType.AGENT_EVENT,
            data=event.to_dict(),
            timestamp=event.timestamp,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SSE streaming."""
        return {
            "event": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class AgentService:
    """Stateless service that executes conversations.

    This service loads a Conversation aggregate and its AgentDefinition,
    then runs the appropriate agent loop (reactive or proactive).
    All state changes are recorded in the Conversation via domain events.

    Key responsibilities:
    - Determine mode (reactive/proactive) from AgentDefinition
    - For proactive: manage template progress and item generation
    - For reactive: delegate to underlying Agent implementation
    - Handle client responses (widget submissions)
    - Record all interactions in Conversation

    Usage:
        service = AgentService(agent, template_store, skill_store)
        async for event in service.run(conversation, definition, tools):
            yield event.to_dict()
    """

    def __init__(
        self,
        agent: Agent,
        template_store: "TemplateStore | None" = None,
        skill_store: "SkillStore | None" = None,
    ) -> None:
        """Initialize the AgentService.

        Args:
            agent: The underlying agent implementation (ReActAgent or similar)
            template_store: Store for ConversationTemplates (for proactive)
            skill_store: Store for SkillTemplates (for proactive)
        """
        self._agent = agent
        self._template_store = template_store
        self._skill_store = skill_store

    async def run(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        tools: list[Tool],
        access_token: str,
        tool_executor: "ToolExecutor | None" = None,
    ) -> AsyncIterator[AgentServiceEvent]:
        """Execute the agent loop for a conversation.

        This is the main entry point for running a conversation. It:
        1. Starts the conversation if not already started
        2. Determines mode (proactive vs reactive)
        3. For proactive: generates items from template
        4. For reactive: runs the standard ReAct loop
        5. Yields events for streaming to client

        Args:
            conversation: The Conversation aggregate
            definition: The AgentDefinition to use
            tools: Available tools
            access_token: User's access token for tool execution
            tool_executor: Callback for executing tools

        Yields:
            AgentServiceEvents for streaming
        """
        # Start conversation if pending
        if conversation.state.status == "pending":
            conversation.start()

        now = datetime.now(UTC)

        # Determine if this is a proactive conversation
        # Proactive requires: has template AND template.agent_starts_first=True
        is_proactive = False
        if definition.has_template and self._template_store:
            template = await self._template_store.get(definition.conversation_template_id)
            if template and template.agent_starts_first:
                is_proactive = True

        yield AgentServiceEvent(
            type=AgentServiceEventType.CONVERSATION_STARTED,
            data={
                "conversation_id": conversation.id(),
                "definition_id": definition.id,
                "mode": "proactive" if is_proactive else "reactive",
            },
            timestamp=now,
        )

        # Check if this is a proactive conversation with a template
        if is_proactive:
            async for event in self._run_proactive(conversation, definition, tools, access_token, tool_executor):
                yield event
        else:
            # Standard reactive mode
            async for event in self._run_reactive(conversation, definition, tools, access_token, tool_executor):
                yield event

    async def _run_reactive(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        tools: list[Tool],
        access_token: str,
        tool_executor: "ToolExecutor | None" = None,
    ) -> AsyncIterator[AgentServiceEvent]:
        """Run the reactive (user-initiated) agent loop.

        Delegates to the underlying Agent implementation.
        """
        # Build context from conversation - include tool_executor in context
        context = self._build_agent_context(conversation, definition, tools, tool_executor, access_token)

        # Run the agent
        async for event in self._agent.run_stream(context):
            # Add messages to conversation based on event type
            if event.type == AgentEventType.LLM_RESPONSE_COMPLETED:
                content = event.data.get("content", "")
                if content:
                    conversation.add_assistant_message(content)

            if event.type == AgentEventType.CLIENT_ACTION:
                # Agent is requesting a client action (widget)
                action_data = event.data.get("action", {})
                conversation.request_client_action(action_data)

                yield AgentServiceEvent(
                    type=AgentServiceEventType.CONVERSATION_SUSPENDED,
                    data={"action": action_data},
                    timestamp=event.timestamp,
                )
                return  # Suspend execution

            # Pass through agent events
            yield AgentServiceEvent.from_agent_event(event)

    async def _run_proactive(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        tools: list[Tool],
        access_token: str,
        tool_executor: "ToolExecutor | None" = None,
    ) -> AsyncIterator[AgentServiceEvent]:
        """Run the proactive (template-driven) agent loop.

        Flow:
        1. Load conversation template
        2. Get current item template based on progress
        3. Generate item content via LLM
        4. Present item with widget
        5. Suspend and wait for response
        """
        if not self._template_store or not definition.conversation_template_id:
            # Fall back to reactive mode
            async for event in self._run_reactive(conversation, definition, tools, access_token, tool_executor):
                yield event
            return

        # Load template
        template = await self._template_store.get(definition.conversation_template_id)
        if not template:
            logger.error(f"Template not found: {definition.conversation_template_id}")
            async for event in self._run_reactive(conversation, definition, tools, access_token, tool_executor):
                yield event
            return

        # Get current index
        current_index = conversation.get_current_template_index()

        # Check if template is complete
        if template.is_complete(current_index):
            # All items answered, complete the conversation
            conversation.complete(
                summary={
                    "total_items": template.item_count,
                    "completed_items": current_index,
                }
            )
            yield AgentServiceEvent(
                type=AgentServiceEventType.CONVERSATION_COMPLETED,
                data={
                    "conversation_id": conversation.id(),
                    "total_items": template.item_count,
                },
                timestamp=datetime.now(UTC),
            )
            return

        # Get next item template
        item_template = template.get_item_at(current_index)
        if not item_template:
            logger.error(f"Item template not found at index {current_index}")
            return

        # Generate item content if we have a skill store
        generated_item = None
        if self._skill_store:
            skill = await self._skill_store.get(item_template.skill_template_id)
            if skill:
                generated_item = await self._generate_item(conversation, definition, item_template, skill)
                if generated_item:
                    conversation.record_generated_item(generated_item)
                    yield AgentServiceEvent(
                        type=AgentServiceEventType.ITEM_GENERATED,
                        data={"item": generated_item},
                        timestamp=datetime.now(UTC),
                    )

        # Build and request client action for the widget
        action = {
            "type": "widget",
            "widget_type": item_template.widget_type,
            "config": item_template.widget_config,
            "item_id": generated_item.get("id") if generated_item else item_template.id,
            "stem": generated_item.get("stem") if generated_item else None,
            "options": generated_item.get("options") if generated_item else None,
        }

        conversation.request_client_action(action)

        yield AgentServiceEvent(
            type=AgentServiceEventType.ITEM_PRESENTED,
            data={
                "item_index": current_index,
                "total_items": template.item_count,
                "action": action,
            },
            timestamp=datetime.now(UTC),
        )

        yield AgentServiceEvent(
            type=AgentServiceEventType.CONVERSATION_SUSPENDED,
            data={"action": action},
            timestamp=datetime.now(UTC),
        )

    async def handle_response(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        response: ClientResponse,
        tools: list[Tool],
        access_token: str,
        tool_executor: "ToolExecutor | None" = None,
    ) -> AsyncIterator[AgentServiceEvent]:
        """Handle user's response to a client action.

        This is called when the user submits a widget response.
        It records the response and continues the agent loop.

        Args:
            conversation: The Conversation aggregate
            definition: The AgentDefinition
            response: The client's response
            tools: Available tools
            access_token: User's access token
            tool_executor: Tool execution callback

        Yields:
            AgentServiceEvents for continued streaming
        """
        # Record the response
        conversation.receive_client_response(
            tool_call_id=response.tool_call_id,
            response=response.response,
        )

        # Determine if proactive mode (same logic as run())
        is_proactive = False
        if definition.has_template and self._template_store:
            template = await self._template_store.get(definition.conversation_template_id)
            if template and template.agent_starts_first:
                is_proactive = True

        # If proactive with template, grade and advance
        if is_proactive:
            async for event in self._handle_proactive_response(conversation, definition, response, tools, access_token, tool_executor):
                yield event
        else:
            # Continue reactive loop
            async for event in self._run_reactive(conversation, definition, tools, access_token, tool_executor):
                yield event

    async def _handle_proactive_response(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        response: ClientResponse,
        tools: list[Tool],
        access_token: str,
        tool_executor: "ToolExecutor | None" = None,
    ) -> AsyncIterator[AgentServiceEvent]:
        """Handle response in proactive mode.

        Grades the response and advances to the next item.
        """
        # Get the pending item from generated items
        generated_items = conversation.get_generated_items()
        current_item = None
        for item in generated_items:
            if not item.get("answered_at"):
                current_item = item
                break

        if current_item:
            # Grade the response
            is_correct = self._grade_response(current_item, response.response)

            # Record the answer
            conversation.record_item_answer(
                item_id=current_item.get("id", ""),
                user_response=str(response.response),
                is_correct=is_correct,
            )

            yield AgentServiceEvent(
                type=AgentServiceEventType.ITEM_ANSWERED,
                data={
                    "item_id": current_item.get("id"),
                    "is_correct": is_correct,
                    "user_response": response.response,
                },
                timestamp=datetime.now(UTC),
            )

        # Advance template
        conversation.advance_template()

        yield AgentServiceEvent(
            type=AgentServiceEventType.TEMPLATE_ADVANCED,
            data={"new_index": conversation.get_current_template_index()},
            timestamp=datetime.now(UTC),
        )

        # Continue with next item
        async for event in self._run_proactive(conversation, definition, tools, access_token, tool_executor):
            yield event

    def _build_agent_context(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        tools: list[Tool],
        tool_executor: "ToolExecutor | None" = None,
        access_token: str | None = None,
    ) -> AgentRunContext:
        """Build the context for running the agent."""
        # Convert conversation messages to LlmMessages
        messages: list[LlmMessage] = []

        # Add system prompt from definition
        if definition.system_prompt:
            messages.append(LlmMessage.system(definition.system_prompt))

        # Add conversation history
        for msg in conversation.get_messages():
            if msg.role == MessageRole.USER:
                messages.append(LlmMessage.user(msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(LlmMessage.assistant(msg.content))

        # Convert tools to LLM tool definitions
        tool_defs = [self._tool_to_llm_def(t) for t in tools]

        # Get the last user message for the context
        user_message = ""
        for msg in reversed(conversation.get_messages()):
            if msg.role == MessageRole.USER:
                user_message = msg.content
                break

        return AgentRunContext(
            user_message=user_message,
            conversation_history=messages,
            tools=tool_defs,
            tool_executor=tool_executor,
            access_token=access_token,
        )

    def _tool_to_llm_def(self, tool: Tool) -> LlmToolDefinition:
        """Convert a Tool to an LlmToolDefinition."""
        return LlmToolDefinition(
            name=tool.name,
            description=tool.description or "",
            parameters={
                "type": "object",
                "properties": {p.name: {"type": p.type, "description": p.description} for p in tool.parameters},
                "required": [p.name for p in tool.parameters if p.required],
            },
        )

    async def _generate_item(
        self,
        conversation: Conversation,
        definition: AgentDefinitionDto,
        item_template: Any,
        skill: SkillTemplate,
    ) -> dict[str, Any] | None:
        """Generate an item using the LLM.

        This uses the skill template's prompt to generate a question
        with options and a correct answer.
        """
        from uuid import uuid4

        # Build generation prompt (will be used when LLM generation is implemented)
        _generation_prompt = skill.build_generation_prompt(
            additional_context=item_template.generation_prompt,
        )

        # For now, return a placeholder - actual LLM call would go here
        # In a full implementation, this would use _generation_prompt with the LLM
        return {
            "id": str(uuid4()),
            "item_template_id": item_template.id,
            "skill_template_id": skill.id,
            "stem": f"[Generated from {skill.name}]",
            "options": None,
            "correct_answer": "",
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _grade_response(self, item: dict[str, Any], response: Any) -> bool | None:
        """Grade a user's response against the correct answer.

        Simple exact match for now - could be extended with more
        sophisticated evaluation methods.
        """
        correct_answer = item.get("correct_answer")
        if correct_answer is None:
            return None

        # Simple comparison
        return str(response).strip().lower() == str(correct_answer).strip().lower()


# =============================================================================
# Store interfaces (to be implemented in infrastructure layer)
# =============================================================================


class TemplateStore:
    """Interface for ConversationTemplate storage."""

    async def get(self, template_id: str) -> ConversationTemplateDto | None:
        """Get a template by ID."""
        raise NotImplementedError

    async def save(self, template: ConversationTemplateDto) -> None:
        """Save a template."""
        raise NotImplementedError


class SkillStore:
    """Interface for SkillTemplate storage."""

    async def get(self, skill_id: str) -> SkillTemplate | None:
        """Get a skill template by ID."""
        raise NotImplementedError

    async def save(self, skill: SkillTemplate) -> None:
        """Save a skill template."""
        raise NotImplementedError


# Type alias for tool executor callback
ToolExecutor = Any  # Callable[[ToolExecutionRequest], Awaitable[ToolExecutionResult]]
