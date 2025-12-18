"""
Read Model Projection Handlers for Conversation Aggregate.

These handlers listen to domain events streamed by the ReadModelReconciliator
and update the MongoDB read model accordingly.

The ReadModelReconciliator subscribes to EventStoreDB's category stream ($ce-agent_host)
and publishes each event through the Mediator. These handlers receive those events
and project them to MongoDB, keeping the Read Model in sync with the Write Model.

IMPORTANT: These handlers use Repository[ConversationDto, str] which resolves to
MotorConversationDtoRepository to ensure writes go to MongoDB (read model).
"""

import logging
from datetime import UTC, datetime

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import DomainEventHandler

from domain.events.conversation import (
    ConversationClearedDomainEvent,
    ConversationCreatedDomainEvent,
    ConversationDeletedDomainEvent,
    ConversationTitleUpdatedDomainEvent,
    MessageAddedDomainEvent,
    ToolCallAddedDomainEvent,
    ToolResultAddedDomainEvent,
)
from domain.repositories import DefinitionRepository
from integration.models.conversation_dto import ConversationDto

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION LIFECYCLE PROJECTION HANDLERS
# =============================================================================


class ConversationCreatedProjectionHandler(DomainEventHandler[ConversationCreatedDomainEvent]):
    """Projects ConversationCreatedDomainEvent to MongoDB Read Model."""

    def __init__(
        self,
        repository: Repository[ConversationDto, str],
        definition_repository: DefinitionRepository,
    ):
        super().__init__()
        self._repository = repository
        self._definition_repository = definition_repository

    async def handle_async(self, event: ConversationCreatedDomainEvent) -> None:
        """Create ConversationDto in Read Model."""
        logger.info(f"📥 Projecting ConversationCreated: {event.aggregate_id}")

        # Idempotency check - skip if already exists
        existing = await self._repository.get_async(event.aggregate_id)
        if existing:
            logger.info(f"⏭️ Conversation already exists in Read Model, skipping: {event.aggregate_id}")
            return

        # Fetch AgentDefinition to get display name and icon
        definition_name = "Agent"
        definition_icon = "bi-robot"
        if event.definition_id:
            agent_definition = await self._definition_repository.get_async(event.definition_id)
            if agent_definition:
                definition_name = agent_definition.name or "Agent"
                definition_icon = agent_definition.icon or "bi-robot"

        # Create ConversationDto from event data
        conversation_dto = ConversationDto(
            id=event.aggregate_id,
            user_id=event.user_id,
            definition_id=event.definition_id,
            definition_name=definition_name,
            definition_icon=definition_icon,
            title=event.title,
            system_prompt=event.system_prompt,
            messages=[],
            message_count=0,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

        await self._repository.add_async(conversation_dto)
        logger.info(f"✅ Projected ConversationCreated to Read Model: {event.aggregate_id}")


class ConversationTitleUpdatedProjectionHandler(DomainEventHandler[ConversationTitleUpdatedDomainEvent]):
    """Projects ConversationTitleUpdatedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ConversationTitleUpdatedDomainEvent) -> None:
        """Update conversation title in Read Model."""
        logger.info(f"📥 Projecting ConversationTitleUpdated: {event.aggregate_id}")

        conversation = await self._repository.get_async(event.aggregate_id)
        if conversation:
            conversation.title = event.new_title
            conversation.updated_at = event.renamed_at
            await self._repository.update_async(conversation)
            logger.info(f"✅ Projected ConversationTitleUpdated to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Conversation not found in Read Model for title update: {event.aggregate_id}")


class ConversationDeletedProjectionHandler(DomainEventHandler[ConversationDeletedDomainEvent]):
    """Projects ConversationDeletedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ConversationDeletedDomainEvent) -> None:
        """Delete conversation from Read Model."""
        logger.info(f"📥 Projecting ConversationDeleted: {event.aggregate_id}")

        try:
            await self._repository.remove_async(event.aggregate_id)
            logger.info(f"✅ Projected ConversationDeleted to Read Model: {event.aggregate_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete conversation from Read Model: {event.aggregate_id} - {e}")


class ConversationClearedProjectionHandler(DomainEventHandler[ConversationClearedDomainEvent]):
    """Projects ConversationClearedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ConversationClearedDomainEvent) -> None:
        """Clear messages from conversation in Read Model."""
        logger.info(f"📥 Projecting ConversationCleared: {event.aggregate_id}")

        conversation = await self._repository.get_async(event.aggregate_id)
        if conversation:
            if event.keep_system:
                # Keep only system messages
                conversation.messages = [m for m in conversation.messages if m.get("role") == "system"]
            else:
                conversation.messages = []
            conversation.message_count = len(conversation.messages)
            conversation.updated_at = event.cleared_at
            await self._repository.update_async(conversation)
            logger.info(f"✅ Projected ConversationCleared to Read Model: {event.aggregate_id}")
        else:
            logger.warning(f"⚠️ Conversation not found in Read Model for clear: {event.aggregate_id}")


# =============================================================================
# MESSAGE PROJECTION HANDLERS
# =============================================================================


class MessageAddedProjectionHandler(DomainEventHandler[MessageAddedDomainEvent]):
    """Projects MessageAddedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: MessageAddedDomainEvent) -> None:
        """Add message to conversation in Read Model."""
        logger.debug(f"📥 Projecting MessageAdded: {event.aggregate_id}, message_id={event.message_id}")

        conversation = await self._repository.get_async(event.aggregate_id)
        if conversation:
            # Check if message already exists (idempotency)
            existing_ids = {m.get("id") for m in conversation.messages}
            if event.message_id in existing_ids:
                logger.debug(f"⏭️ Message already exists in Read Model, skipping: {event.message_id}")
                return

            # Add the new message
            message = {
                "id": event.message_id,
                "role": event.role,
                "content": event.content,
                "status": event.status,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "tool_calls": [],
                "tool_results": [],
            }
            if event.metadata:
                message["metadata"] = event.metadata

            conversation.messages.append(message)
            conversation.message_count = len(conversation.messages)
            conversation.updated_at = datetime.now(UTC)
            await self._repository.update_async(conversation)
            logger.debug(f"✅ Projected MessageAdded to Read Model: {event.message_id}")
        else:
            logger.warning(f"⚠️ Conversation not found in Read Model for message add: {event.aggregate_id}")


class ToolCallAddedProjectionHandler(DomainEventHandler[ToolCallAddedDomainEvent]):
    """Projects ToolCallAddedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolCallAddedDomainEvent) -> None:
        """Add tool call to message in Read Model."""
        logger.debug(f"📥 Projecting ToolCallAdded: {event.aggregate_id}, call_id={event.call_id}")

        conversation = await self._repository.get_async(event.aggregate_id)
        if conversation:
            # Find the message and add the tool call
            for message in conversation.messages:
                if message.get("id") == event.message_id:
                    if "tool_calls" not in message:
                        message["tool_calls"] = []

                    # Check if tool call already exists (idempotency)
                    existing_ids = {tc.get("id") for tc in message["tool_calls"]}
                    if event.call_id in existing_ids:
                        logger.debug(f"⏭️ ToolCall already exists in Read Model, skipping: {event.call_id}")
                        return

                    message["tool_calls"].append(
                        {
                            "id": event.call_id,
                            "tool_name": event.tool_name,
                            "arguments": event.arguments,
                        }
                    )
                    conversation.updated_at = datetime.now(UTC)
                    await self._repository.update_async(conversation)
                    logger.debug(f"✅ Projected ToolCallAdded to Read Model: {event.call_id}")
                    return

            logger.warning(f"⚠️ Message not found in Read Model for tool call: {event.message_id}")
        else:
            logger.warning(f"⚠️ Conversation not found in Read Model for tool call: {event.aggregate_id}")


class ToolResultAddedProjectionHandler(DomainEventHandler[ToolResultAddedDomainEvent]):
    """Projects ToolResultAddedDomainEvent to MongoDB Read Model."""

    def __init__(self, repository: Repository[ConversationDto, str]):
        super().__init__()
        self._repository = repository

    async def handle_async(self, event: ToolResultAddedDomainEvent) -> None:
        """Add tool result to message in Read Model."""
        logger.debug(f"📥 Projecting ToolResultAdded: {event.aggregate_id}, call_id={event.call_id}")

        conversation = await self._repository.get_async(event.aggregate_id)
        if conversation:
            # Find the message and add the tool result
            for message in conversation.messages:
                if message.get("id") == event.message_id:
                    if "tool_results" not in message:
                        message["tool_results"] = []

                    # Check if tool result already exists (idempotency)
                    existing_ids = {tr.get("call_id") for tr in message["tool_results"]}
                    if event.call_id in existing_ids:
                        logger.debug(f"⏭️ ToolResult already exists in Read Model, skipping: {event.call_id}")
                        return

                    message["tool_results"].append(
                        {
                            "call_id": event.call_id,
                            "tool_name": event.tool_name,
                            "success": event.success,
                            "result": event.result,
                            "error": event.error,
                            "execution_time_ms": event.execution_time_ms,
                        }
                    )
                    conversation.updated_at = datetime.now(UTC)
                    await self._repository.update_async(conversation)
                    logger.debug(f"✅ Projected ToolResultAdded to Read Model: {event.call_id}")
                    return

            logger.warning(f"⚠️ Message not found in Read Model for tool result: {event.message_id}")
        else:
            logger.warning(f"⚠️ Conversation not found in Read Model for tool result: {event.aggregate_id}")
