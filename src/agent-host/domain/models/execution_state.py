"""Execution state value objects for Agent suspend/resume.

This module contains the value objects that capture agent execution state
for persistence during suspension (waiting for client response).

Classes:
- LlmMessageSnapshot: Simplified LLM message for serialization
- PendingToolCall: A tool call awaiting client response
- ExecutionState: Complete execution context for suspend/resume
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LlmMessageSnapshot:
    """Snapshot of an LLM message for persistence.

    Simplified representation that can be serialized/deserialized.
    Captures the essential fields from LLM API message formats.

    Attributes:
        role: Message role (system, user, assistant, tool)
        content: Text content of the message
        tool_calls: List of tool calls (for assistant messages)
        tool_call_id: ID linking to a tool call (for tool result messages)
        name: Tool name (for tool result messages)
    """

    role: str  # system, user, assistant, tool
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None  # Tool name for tool results

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LlmMessageSnapshot":
        """Deserialize from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
        )


@dataclass
class PendingToolCall:
    """A tool call waiting for client response.

    Captures the tool call information needed to match the response
    when execution resumes.

    Attributes:
        call_id: Unique identifier for this tool call
        tool_name: Name of the tool being called
        arguments: Arguments passed to the tool
    """

    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingToolCall":
        """Deserialize from dictionary."""
        return cls(
            call_id=data["call_id"],
            tool_name=data["tool_name"],
            arguments=data["arguments"],
        )


@dataclass
class ExecutionState:
    """Captures agent execution state for suspension/resume.

    This is the critical state that was previously held in-memory
    by ProactiveAgent._suspended_state. Now it's persisted as part
    of the Agent aggregate.

    When an agent suspends (waiting for client widget response),
    this state captures everything needed to resume exactly where
    the agent left off.

    Attributes:
        conversation_snapshot: LLM conversation history at suspension
        iteration: Current iteration count in the agent loop
        tool_calls_made: Total tool calls made in this session
        pending_tool_call: The tool call awaiting response
        started_at_ms: Timestamp when execution started (for metrics)
        suspended_at_ms: Timestamp when execution suspended (for metrics)
    """

    # Conversation context
    conversation_snapshot: list[LlmMessageSnapshot] = field(default_factory=list)

    # Loop state
    iteration: int = 0
    tool_calls_made: int = 0

    # Pending interaction
    pending_tool_call: PendingToolCall | None = None

    # Timing (for metrics)
    started_at_ms: float = 0.0
    suspended_at_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for persistence."""
        return {
            "conversation_snapshot": [m.to_dict() for m in self.conversation_snapshot],
            "iteration": self.iteration,
            "tool_calls_made": self.tool_calls_made,
            "pending_tool_call": self.pending_tool_call.to_dict() if self.pending_tool_call else None,
            "started_at_ms": self.started_at_ms,
            "suspended_at_ms": self.suspended_at_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionState":
        """Deserialize from dictionary."""
        return cls(
            conversation_snapshot=[LlmMessageSnapshot.from_dict(m) for m in data.get("conversation_snapshot", [])],
            iteration=data.get("iteration", 0),
            tool_calls_made=data.get("tool_calls_made", 0),
            pending_tool_call=PendingToolCall.from_dict(data["pending_tool_call"]) if data.get("pending_tool_call") else None,
            started_at_ms=data.get("started_at_ms", 0.0),
            suspended_at_ms=data.get("suspended_at_ms", 0.0),
        )
