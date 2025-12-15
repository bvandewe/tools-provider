"""MCP protocol message models.

Defines the data structures used for MCP JSON-RPC communication,
following the Model Context Protocol specification.

MCP uses JSON-RPC 2.0 for all communication between clients and servers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class McpMessageType(str, Enum):
    """Types of MCP messages."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class McpContentType(str, Enum):
    """Types of content in MCP tool results."""

    TEXT = "text"
    IMAGE = "image"
    RESOURCE = "resource"


@dataclass
class McpRequest:
    """MCP JSON-RPC request message.

    Represents a request from client to server following JSON-RPC 2.0.

    Attributes:
        id: Unique request identifier for correlation
        method: The MCP method to invoke (e.g., "tools/list", "tools/call")
        params: Method parameters as a dictionary
    """

    id: int | str
    method: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-RPC format."""
        return {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpRequest":
        """Create from JSON-RPC dictionary."""
        return cls(
            id=data["id"],
            method=data["method"],
            params=data.get("params", {}),
        )


@dataclass
class McpError:
    """MCP error object within a response.

    Follows JSON-RPC 2.0 error format.

    Attributes:
        code: Numeric error code
        message: Human-readable error message
        data: Optional additional error data
    """

    code: int
    message: str
    data: Any = None

    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpError":
        """Create from dictionary."""
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data"),
        )


@dataclass
class McpResponse:
    """MCP JSON-RPC response message.

    Represents a response from server to client. Contains either
    a result or an error, but not both.

    Attributes:
        id: Correlation ID matching the request
        result: Successful result data (mutually exclusive with error)
        error: Error information (mutually exclusive with result)
    """

    id: int | str
    result: dict[str, Any] | None = None
    error: McpError | None = None

    def is_error(self) -> bool:
        """Check if this is an error response."""
        return self.error is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-RPC format."""
        response: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
        }
        if self.error:
            response["error"] = self.error.to_dict()
        else:
            response["result"] = self.result or {}
        return response

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpResponse":
        """Create from JSON-RPC dictionary."""
        error = None
        if "error" in data:
            error = McpError.from_dict(data["error"])

        return cls(
            id=data.get("id", 0),
            result=data.get("result"),
            error=error,
        )


@dataclass
class McpNotification:
    """MCP JSON-RPC notification (no response expected).

    Used for one-way messages like progress updates or events.

    Attributes:
        method: The notification method name
        params: Notification parameters
    """

    method: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-RPC format (no id for notifications)."""
        return {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpNotification":
        """Create from JSON-RPC dictionary."""
        return cls(
            method=data["method"],
            params=data.get("params", {}),
        )


@dataclass
class McpContent:
    """Content block within an MCP tool result.

    MCP tool results contain one or more content blocks,
    each with a type and corresponding data.

    Attributes:
        type: Content type (text, image, resource)
        text: Text content (for type="text")
        data: Binary data as base64 (for type="image")
        mime_type: MIME type for binary content
        uri: Resource URI (for type="resource")
    """

    type: McpContentType | str
    text: str | None = None
    data: str | None = None  # Base64 encoded for images
    mime_type: str | None = None
    uri: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {"type": self.type if isinstance(self.type, str) else self.type.value}
        if self.text is not None:
            result["text"] = self.text
        if self.data is not None:
            result["data"] = self.data
        if self.mime_type is not None:
            result["mimeType"] = self.mime_type
        if self.uri is not None:
            result["uri"] = self.uri
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpContent":
        """Create from dictionary."""
        content_type = data.get("type", "text")
        return cls(
            type=content_type,
            text=data.get("text"),
            data=data.get("data"),
            mime_type=data.get("mimeType"),
            uri=data.get("uri"),
        )

    @staticmethod
    def text_content(text: str) -> "McpContent":
        """Create a text content block."""
        return McpContent(type=McpContentType.TEXT, text=text)


@dataclass
class McpToolCall:
    """Request to call an MCP tool.

    Encapsulates the tool name and arguments for a tools/call request.

    Attributes:
        name: Name of the tool to call
        arguments: Arguments to pass to the tool
    """

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_params(self) -> dict[str, Any]:
        """Convert to tools/call params format."""
        return {
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class McpToolResult:
    """Result from an MCP tool call.

    Contains the content returned by the tool and metadata.

    Attributes:
        content: List of content blocks returned by the tool
        is_error: Whether the tool execution resulted in an error
        meta: Optional metadata from the tool
    """

    content: list[McpContent] = field(default_factory=list)
    is_error: bool = False
    meta: dict[str, Any] | None = None

    def get_text(self) -> str:
        """Get combined text from all text content blocks."""
        return "\n".join(c.text or "" for c in self.content if c.type == McpContentType.TEXT or c.type == "text")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result: dict[str, Any] = {
            "content": [c.to_dict() for c in self.content],
            "isError": self.is_error,
        }
        if self.meta:
            result["_meta"] = self.meta
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpToolResult":
        """Create from tools/call response."""
        content = [McpContent.from_dict(c) for c in data.get("content", [])]
        return cls(
            content=content,
            is_error=data.get("isError", False),
            meta=data.get("_meta"),
        )


@dataclass
class McpToolDefinition:
    """Definition of an MCP tool from tools/list.

    Describes a tool's interface as returned by the MCP server.

    Attributes:
        name: Unique tool name
        description: Human-readable description
        input_schema: JSON Schema for input parameters
    """

    name: str
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpToolDefinition":
        """Create from tools/list response item."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", {}),
        )

    def get_required_params(self) -> list[str]:
        """Get list of required parameter names."""
        return self.input_schema.get("required", [])

    def get_properties(self) -> dict[str, Any]:
        """Get parameter properties from schema."""
        return self.input_schema.get("properties", {})


@dataclass
class McpServerInfo:
    """Information about an MCP server.

    Returned during initialization handshake.

    Attributes:
        name: Server name
        version: Server version
        protocol_version: MCP protocol version supported
    """

    name: str
    version: str
    protocol_version: str = "2024-11-05"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "McpServerInfo":
        """Create from initialize response."""
        server_info = data.get("serverInfo", {})
        return cls(
            name=server_info.get("name", "unknown"),
            version=server_info.get("version", "unknown"),
            protocol_version=data.get("protocolVersion", "2024-11-05"),
        )
