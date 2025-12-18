"""Client action value object for widget rendering.

This module contains the ClientAction value object that represents
a tool call requiring client-side rendering as a widget.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ClientAction:
    """An action requiring client-side rendering.

    Represents a tool call that should be intercepted and rendered
    as a widget on the client side instead of being executed server-side.

    Used by proactive agents to present interactive widgets (multiple choice,
    text input, forms, etc.) to users during a session.

    Attributes:
        tool_call_id: Unique identifier from the LLM's tool call
        tool_name: Name of the client tool (e.g., "present_choices")
        widget_type: Type of widget to render (e.g., "multiple_choice")
        props: Widget-specific properties to pass to the frontend
        lock_input: Whether to disable free-text chat input while widget is active
    """

    tool_call_id: str
    tool_name: str
    widget_type: str
    props: dict[str, Any]
    lock_input: bool = True

    def to_sse_payload(self) -> dict[str, Any]:
        """Convert to SSE event payload format.

        This format is consumed by the frontend's showClientActionWidget function
        which expects: tool_call_id, tool_name, widget_type, props, lock_input
        """
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "widget_type": self.widget_type,
            "props": self.props,
            "lock_input": self.lock_input,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "widget_type": self.widget_type,
            "props": self.props,
            "lock_input": self.lock_input,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClientAction":
        """Create from dictionary."""
        return cls(
            tool_call_id=data["tool_call_id"],
            tool_name=data["tool_name"],
            widget_type=data["widget_type"],
            props=data.get("props", {}),
            lock_input=data.get("lock_input", True),
        )
