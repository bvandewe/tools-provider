"""Protocol senders for the orchestrator.

This subpackage contains classes responsible for sending specific
types of protocol messages to WebSocket clients. Each sender is
focused on a single concern:

- ConfigSender: Conversation configuration and flow control
- WidgetSender: Widget rendering and interaction
- ContentSender: Streaming content delivery

These senders depend on the ConnectionManager for actual message
delivery but are otherwise stateless.
"""

from application.orchestrator.protocol.config_sender import ConfigSender
from application.orchestrator.protocol.content_sender import ContentSender
from application.orchestrator.protocol.widget_sender import WidgetSender

__all__ = [
    "ConfigSender",
    "WidgetSender",
    "ContentSender",
]
