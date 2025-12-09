"""In-memory conversation repository implementation (for testing/development)."""

import logging
from collections import defaultdict
from datetime import UTC, datetime

from neuroglia.hosting.abstractions import ApplicationBuilderBase

from domain.entities.conversation import Conversation
from domain.repositories.conversation_repository import ConversationRepository

logger = logging.getLogger(__name__)


class InMemoryConversationRepository(ConversationRepository):
    """
    In-memory implementation of ConversationRepository.

    Stores Conversation aggregates in memory, organized by user ID for efficient lookup.
    Suitable for testing and development only. Production uses MongoDB via Motor.
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        # conversation_id -> Conversation
        self._conversations: dict[str, Conversation] = {}
        # user_id -> list of conversation_ids
        self._user_conversations: dict[str, list[str]] = defaultdict(list)

    async def get_async(self, id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._conversations.get(id)

    async def get_all_async(self) -> list[Conversation]:
        """Retrieve all conversations."""
        return list(self._conversations.values())

    async def add_async(self, entity: Conversation) -> Conversation:
        """Add a conversation."""
        conv_id = entity.id()
        user_id = entity.state.user_id

        # Update the timestamp in state
        entity.state.updated_at = datetime.now(UTC)
        self._conversations[conv_id] = entity

        if conv_id not in self._user_conversations[user_id]:
            self._user_conversations[user_id].append(conv_id)

        logger.debug(f"Added conversation {conv_id} for user {user_id}")
        return entity

    async def update_async(self, entity: Conversation) -> Conversation:
        """Update a conversation."""
        conv_id = entity.id()
        entity.state.updated_at = datetime.now(UTC)
        self._conversations[conv_id] = entity
        logger.debug(f"Updated conversation {conv_id}")
        return entity

    async def remove_async(self, id: str) -> None:
        """Remove a conversation."""
        conversation = self._conversations.pop(id, None)
        if conversation:
            user_id = conversation.state.user_id
            if id in self._user_conversations.get(user_id, []):
                self._user_conversations[user_id].remove(id)
            logger.debug(f"Removed conversation {id}")

    async def contains_async(self, id: str) -> bool:
        """Check if a conversation exists."""
        return id in self._conversations

    async def _do_add_async(self, entity: Conversation) -> Conversation:
        """Internal add implementation required by Repository base class."""
        return await self.add_async(entity)

    async def _do_update_async(self, entity: Conversation) -> Conversation:
        """Internal update implementation required by Repository base class."""
        return await self.update_async(entity)

    async def _do_remove_async(self, id: str) -> None:
        """Internal remove implementation required by Repository base class."""
        await self.remove_async(id)

    async def get_by_user_async(self, user_id: str) -> list[Conversation]:
        """Retrieve conversations for a specific user."""
        conv_ids = self._user_conversations.get(user_id, [])
        conversations = [self._conversations[cid] for cid in conv_ids if cid in self._conversations]
        # Sort by updated_at descending
        return sorted(conversations, key=lambda c: c.state.updated_at, reverse=True)

    async def get_recent_by_user_async(self, user_id: str, limit: int = 10) -> list[Conversation]:
        """Retrieve the most recent conversations for a user."""
        conversations = await self.get_by_user_async(user_id)
        return conversations[:limit]

    def clear_all(self) -> None:
        """Clear all conversations (for testing)."""
        self._conversations.clear()
        self._user_conversations.clear()

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure InMemoryConversationRepository in the service collection.

        Args:
            builder: The application builder
        """
        repository = InMemoryConversationRepository()

        builder.services.add_singleton(InMemoryConversationRepository, singleton=repository)
        builder.services.add_singleton(ConversationRepository, singleton=repository)

        logger.info("Configured InMemoryConversationRepository")
