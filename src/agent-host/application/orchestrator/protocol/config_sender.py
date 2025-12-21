"""Configuration and flow control protocol sender.

Handles sending:
- Conversation configuration (control.conversation.config)
- Chat input state (control.flow.chatInput)
- Item context (control.item.context)
- Error messages (system.error)
"""

import logging
from typing import TYPE_CHECKING, Any

from application.protocol.control import ConversationConfigPayload, ItemContextPayload
from application.protocol.core import create_message

if TYPE_CHECKING:
    from application.orchestrator.context import ConversationContext
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)


class ConfigSender:
    """Sends configuration and flow control messages to clients.

    This class encapsulates the logic for sending protocol messages
    related to conversation configuration and flow control.

    Attributes:
        _connection_manager: The WebSocket connection manager

    Usage:
        sender = ConfigSender(connection_manager)
        await sender.send_conversation_config(connection, context)
        await sender.send_chat_input_enabled(connection, context, enabled=True)
    """

    def __init__(self, connection_manager: "ConnectionManager"):
        """Initialize the config sender.

        Args:
            connection_manager: The WebSocket connection manager for message delivery
        """
        self._connection_manager = connection_manager

    async def send_conversation_config(
        self,
        connection: "Connection",
        context: "ConversationContext",
    ) -> None:
        """Send conversation configuration to client.

        Uses template config if available, otherwise applies sensible defaults.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        tc = context.template_config  # Shorthand for template config dict

        config_payload = ConversationConfigPayload(
            templateId=context.template_id or "default",
            templateName=context.definition_name or "Conversation",
            totalItems=context.total_items or 1,
            displayMode="append",  # DisplayMode literal
            showConversationHistory=True,
            allowBackwardNavigation=tc.get("allow_backward_navigation", not context.is_proactive),
            allowConcurrentItemWidgets=False,
            allowSkip=tc.get("allow_navigation", not context.is_proactive),
            enableChatInputInitially=tc.get("enable_chat_input_initially", not context.is_proactive),
            displayProgressIndicator=tc.get("display_progress_indicator", context.is_proactive),
            displayFinalScoreReport=tc.get("display_final_score_report", False),
            continueAfterCompletion=tc.get("continue_after_completion", True),
        )

        config_message = create_message(
            message_type="control.conversation.config",
            payload=config_payload.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )

        await self._connection_manager.send_to_connection(connection.connection_id, config_message)
        log.debug(f"📤 Sent conversation config for {context.conversation_id}")

    async def send_chat_input_enabled(
        self,
        connection: "Connection",
        context: "ConversationContext",
        enabled: bool,
    ) -> None:
        """Send chat input state to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            enabled: Whether chat input should be enabled
        """
        message = create_message(
            message_type="control.flow.chatInput",
            payload={"enabled": enabled},
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, message)
        log.debug(f"📤 Chat input {'enabled' if enabled else 'disabled'} for {context.conversation_id}")

    async def send_item_context(
        self,
        connection: "Connection",
        context: "ConversationContext",
        item_index: int,
        item: Any = None,  # Optional ConversationItemDto for additional data
    ) -> None:
        """Send item context to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_index: The item index (0-based)
            item: Optional item DTO for additional metadata
        """
        # Use item data if provided, otherwise use defaults
        item_id = item.id if item else f"item-{item_index}"
        item_title = item.title if item else f"Item {item_index + 1}"
        enable_chat = item.enable_chat_input if item else True
        time_limit = item.time_limit_seconds if item else None
        require_confirmation = getattr(item, "require_user_confirmation", False) if item else False
        confirmation_text = getattr(item, "confirmation_button_text", "Submit") if item else "Submit"

        item_context = ItemContextPayload(
            itemId=item_id,
            itemIndex=item_index,
            totalItems=max(context.total_items, 1),
            itemTitle=item_title,
            enableChatInput=enable_chat,
            timeLimitSeconds=time_limit,
            showRemainingTime=bool(time_limit),
            widgetCompletionBehavior="readonly",
            conversationDeadline=None,
            requireUserConfirmation=require_confirmation,
            confirmationButtonText=confirmation_text,
        )

        context_message = create_message(
            message_type="control.item.context",
            payload=item_context.model_dump(by_alias=True, exclude_none=True),
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, context_message)
        log.debug(f"📤 Sent item context for item {item_index} ({item_id})")

    async def send_error(
        self,
        connection: "Connection",
        conversation_id: str | None,
        code: str,
        message: str,
        is_retryable: bool = True,
        category: str = "business",
    ) -> None:
        """Send error message to client.

        Args:
            connection: The WebSocket connection
            conversation_id: The conversation ID (may be None for connection-level errors)
            code: Error code (e.g., "NO_TEMPLATE", "ITEM_LOAD_FAILED")
            message: Human-readable error message
            is_retryable: Whether the client should retry
            category: Error category ("business", "validation", "system")
        """
        error_message = create_message(
            message_type="system.error",
            payload={
                "category": category,
                "code": code,
                "message": message,
                "isRetryable": is_retryable,
            },
            conversation_id=conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, error_message)
        log.warning(f"📤 Sent error to {connection.connection_id}: [{code}] {message}")

    async def send_flow_paused(
        self,
        connection: "Connection",
        context: "ConversationContext",
        reason: str | None = None,
    ) -> None:
        """Send flow paused notification to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            reason: Optional reason for pausing
        """
        message = create_message(
            message_type="control.flow.pause",
            payload={
                "paused": True,
                "reason": reason or "User requested pause",
                "canResume": True,
            },
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, message)
        log.debug(f"📤 Flow paused for {context.conversation_id}: {reason}")

    async def send_flow_resumed(
        self,
        connection: "Connection",
        context: "ConversationContext",
    ) -> None:
        """Send flow resumed notification to client.

        Args:
            connection: The WebSocket connection
            context: The conversation context
        """
        message = create_message(
            message_type="control.flow.resume",
            payload={"resumed": True},
            conversation_id=context.conversation_id,
        )
        await self._connection_manager.send_to_connection(connection.connection_id, message)
        log.debug(f"📤 Flow resumed for {context.conversation_id}")
