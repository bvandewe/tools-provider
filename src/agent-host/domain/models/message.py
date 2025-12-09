"""Message model representing a single message in a conversation."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    """Role of the message sender."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageStatus(str, Enum):
    """Status of message processing."""

    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolCall:
    """Represents a tool call request from the LLM."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    call_id: str
    tool_name: str
    success: bool
    result: Any
    error: str | None = None
    execution_time_ms: float | None = None


@dataclass
class Message:
    """
    Represents a single message in a conversation.

    Messages can be from users, the assistant, the system, or tool results.
    """

    id: str
    role: MessageRole
    content: str
    created_at: datetime
    status: MessageStatus = MessageStatus.COMPLETED
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_user_message(cls, content: str) -> "Message":
        """Create a new user message."""
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.USER,
            content=content,
            created_at=datetime.now(UTC),
            status=MessageStatus.COMPLETED,
        )

    @classmethod
    def create_assistant_message(
        cls,
        content: str,
        tool_calls: list[ToolCall] | None = None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> "Message":
        """Create a new assistant message."""
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=datetime.now(UTC),
            status=status,
            tool_calls=tool_calls or [],
        )

    @classmethod
    def create_system_message(cls, content: str) -> "Message":
        """Create a new system message."""
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.SYSTEM,
            content=content,
            created_at=datetime.now(UTC),
            status=MessageStatus.COMPLETED,
        )

    @classmethod
    def create_tool_message(
        cls,
        tool_name: str,
        result: ToolResult,
    ) -> "Message":
        """Create a message containing tool execution results."""
        return cls(
            id=str(uuid.uuid4()),
            role=MessageRole.TOOL,
            content=str(result.result) if result.success else f"Error: {result.error}",
            created_at=datetime.now(UTC),
            status=MessageStatus.COMPLETED,
            tool_results=[result],
            metadata={"tool_name": tool_name},
        )

    def to_ollama_format(self) -> dict[str, Any]:
        """Convert message to Ollama chat format."""
        msg = {
            "role": self.role.value if self.role != MessageRole.TOOL else "assistant",
            "content": self.content,
        }

        # Include tool calls if present
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "function": {
                        "name": tc.tool_name,
                        "arguments": tc.arguments,
                    }
                }
                for tc in self.tool_calls
            ]

        return msg

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "tool_calls": [
                {
                    "call_id": tc.call_id,
                    "tool_name": tc.tool_name,
                    "arguments": tc.arguments,
                }
                for tc in self.tool_calls
            ],
            "tool_results": [
                {
                    "call_id": tr.call_id,
                    "tool_name": tr.tool_name,
                    "success": tr.success,
                    "result": tr.result,
                    "error": tr.error,
                    "execution_time_ms": tr.execution_time_ms,
                }
                for tr in self.tool_results
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=MessageStatus(data.get("status", "completed")),
            tool_calls=[
                ToolCall(
                    call_id=tc["call_id"],
                    tool_name=tc["tool_name"],
                    arguments=tc["arguments"],
                )
                for tc in data.get("tool_calls", [])
            ],
            tool_results=[
                ToolResult(
                    call_id=tr["call_id"],
                    tool_name=tr["tool_name"],
                    success=tr["success"],
                    result=tr["result"],
                    error=tr.get("error"),
                    execution_time_ms=tr.get("execution_time_ms"),
                )
                for tr in data.get("tool_results", [])
            ],
            metadata=data.get("metadata", {}),
        )
