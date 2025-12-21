# WebSocket Protocol v1.0.0 - Addendum: Model Selection

> **Status:** Extension to Protocol v1.0.0
> **Date:** December 20, 2025
> **Integration Point:** To be merged into `websocket-protocol-v1.md` in a subsequent session

---

## Overview

This addendum extends the WebSocket Protocol v1.0.0 to support runtime LLM model selection. Users can view available models and switch between them during an active conversation.

### Key Features

1. **Server-Initiated Model Info**: On connection establishment, server sends available models and current selection
2. **Client-Requested Model Change**: Client can request model change via control message
3. **Server Acknowledgment**: Server confirms or rejects model change with feedback

---

## 1. Extended System Messages

### 1.1 `system.connection.established` (Extended)

The connection established message now includes optional model configuration fields.

**New Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `currentModel` | `string \| null` | No | Currently active model ID (qualified format) |
| `availableModels` | `ModelInfo[]` | No | List of models available for selection |
| `allowModelSelection` | `boolean` | No | Whether user can change the model |

**ModelInfo Structure:**

```typescript
interface ModelInfo {
    /** Provider type (e.g., "ollama", "openai") */
    provider: string;
    /** Model identifier within the provider */
    id: string;
    /** Fully qualified ID (e.g., "openai:gpt-4o") */
    qualifiedId: string;
    /** User-friendly display name */
    name: string;
    /** Brief description of model capabilities */
    description?: string;
    /** Whether this is the default model for its provider */
    isDefault?: boolean;
}
```

**Example Payload:**

```json
{
    "connectionId": "conn_abc123",
    "conversationId": "conv_xyz789",
    "userId": "user_123",
    "definitionId": "def_chat",
    "resuming": false,
    "serverTime": "2025-12-20T10:30:00.000Z",
    "serverCapabilities": ["data.content.chunk", "data.tool.call", ...],
    "currentModel": "ollama:llama3.2:3b",
    "availableModels": [
        {
            "provider": "ollama",
            "id": "llama3.2:3b",
            "qualifiedId": "ollama:llama3.2:3b",
            "name": "Llama 3.2 (3B)",
            "description": "Fast, efficient model for general tasks",
            "isDefault": true
        },
        {
            "provider": "openai",
            "id": "gpt-4o",
            "qualifiedId": "openai:gpt-4o",
            "name": "GPT-4o",
            "description": "OpenAI's most capable model",
            "isDefault": false
        }
    ],
    "allowModelSelection": true
}
```

---

## 2. New Control Messages

### 2.1 `control.conversation.model` (Client → Server)

Request to change the active LLM model for the current conversation.

**Direction:** Client → Server

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `modelId` | `string` | Yes | Qualified model ID to switch to |

**Example:**

```json
{
    "id": "msg_123",
    "type": "control.conversation.model",
    "version": "1.0",
    "timestamp": "2025-12-20T10:35:00.000Z",
    "source": "client",
    "conversationId": "conv_xyz789",
    "payload": {
        "modelId": "openai:gpt-4o"
    }
}
```

### 2.2 `control.conversation.model.ack` (Server → Client)

Server acknowledgment of model change request.

**Direction:** Server → Client

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `modelId` | `string` | Yes | The model ID that was requested |
| `success` | `boolean` | Yes | Whether the change was successful |
| `message` | `string` | No | Optional message (e.g., error reason) |

**Success Example:**

```json
{
    "id": "msg_124",
    "type": "control.conversation.model.ack",
    "version": "1.0",
    "timestamp": "2025-12-20T10:35:00.100Z",
    "source": "server",
    "conversationId": "conv_xyz789",
    "payload": {
        "modelId": "openai:gpt-4o",
        "success": true,
        "message": null
    }
}
```

**Failure Example:**

```json
{
    "id": "msg_124",
    "type": "control.conversation.model.ack",
    "version": "1.0",
    "timestamp": "2025-12-20T10:35:00.100Z",
    "source": "server",
    "conversationId": "conv_xyz789",
    "payload": {
        "modelId": "openai:gpt-5-turbo",
        "success": false,
        "message": "Model 'openai:gpt-5-turbo' is not available"
    }
}
```

---

## 3. Message Type Constants

Add to `MESSAGE_TYPES` enum:

```typescript
// Control - Conversation (add after CONTROL_CONVERSATION_COMPLETE)
CONTROL_CONVERSATION_MODEL: 'control.conversation.model',
CONTROL_CONVERSATION_MODEL_ACK: 'control.conversation.model.ack',
```

---

## 4. Sequence Diagram

### 4.1 Connection with Model Info

```
Client                                    Server
  │──── WebSocket Upgrade ────────────────────►│
  │◄─── HTTP 101 Switching Protocols ──────────│
  │◄─── system.connection.established ─────────│
  │     (includes availableModels,             │
  │      currentModel, allowModelSelection)    │
  │                                            │
  │     [UI shows model selector if allowed]   │
```

### 4.2 Model Change Flow

```
Client                                    Server
  │                                            │
  │     [User selects new model in UI]         │
  │                                            │
  │──── control.conversation.model ───────────►│
  │     {modelId: "openai:gpt-4o"}             │
  │                                            │
  │     [Server validates and sets override]   │
  │                                            │
  │◄─── control.conversation.model.ack ────────│
  │     {success: true}                        │
  │                                            │
  │     [UI updates model display]             │
  │                                            │
  │──── data.message.send ────────────────────►│
  │     (subsequent messages use new model)    │
```

---

## 5. Implementation Notes

### 5.1 Model ID Format

Model IDs use a qualified format: `{provider}:{model_id}`

Examples:

- `ollama:llama3.2:3b`
- `openai:gpt-4o`
- `anthropic:claude-3-opus`

Note: Ollama models may contain colons in their IDs (e.g., `llama3.2:3b`), so parsing should check if the first part is a known provider before splitting.

### 5.2 State Management

- Model selection is **per-connection**, not persisted to conversation state
- Reconnecting uses the server's default model unless explicitly changed again
- The orchestrator stores the selected model in `ConversationContext.model`

### 5.3 UI Considerations

- Show model selector only when `allowModelSelection` is `true`
- Disable selector during streaming to prevent mid-response changes
- Display loading state while waiting for ack
- Revert UI selection if ack indicates failure

### 5.4 Error Handling

Common failure reasons:

- `provider_not_available`: The requested provider is not registered
- `model_not_found`: The model ID is not in the available models list
- `rate_limited`: Too many model changes in a short period

---

## 6. TypeScript Interfaces

```typescript
/** Model information for UI display */
export interface ModelInfo {
    provider: string;
    id: string;
    qualifiedId: string;
    name: string;
    description?: string;
    isDefault?: boolean;
}

/** Payload for control.conversation.model (client → server) */
export interface ModelChangePayload {
    modelId: string;
}

/** Payload for control.conversation.model.ack (server → client) */
export interface ModelChangeAckPayload {
    modelId: string;
    success: boolean;
    message?: string;
}

/** Extended SystemConnectionEstablishedPayload */
export interface SystemConnectionEstablishedPayload {
    connectionId: string;
    conversationId: string;
    userId: string;
    definitionId?: string;
    resuming: boolean;
    serverTime: string;
    serverCapabilities?: string[];
    currentModel?: string | null;
    availableModels?: ModelInfo[];
    allowModelSelection?: boolean;
}
```

---

## 7. Python Pydantic Models

Located in `application/protocol/control.py`:

```python
class ModelChangePayload(BaseModel):
    """Payload for control.conversation.model (client → server)."""
    model_id: str = Field(..., alias="modelId", description="Qualified model ID to switch to")

    model_config = ConfigDict(populate_by_name=True)


class ModelChangeAckPayload(BaseModel):
    """Payload for control.conversation.model.ack (server → client)."""
    model_id: str = Field(..., alias="modelId", description="The requested model ID")
    success: bool = Field(..., description="Whether the change was successful")
    message: str | None = Field(default=None, description="Optional message")

    model_config = ConfigDict(populate_by_name=True)
```

Located in `application/protocol/system.py`:

```python
class SystemConnectionEstablishedPayload(BaseModel):
    """Extended payload with model info."""
    # ... existing fields ...
    current_model: str | None = Field(
        default=None, alias="currentModel",
        description="Currently active model ID"
    )
    available_models: list[dict[str, Any]] = Field(
        default_factory=list, alias="availableModels",
        description="List of available models"
    )
    allow_model_selection: bool = Field(
        default=False, alias="allowModelSelection",
        description="Whether user can change the model"
    )
```

---

## 8. Backend Handler Registration

In `application/websocket/router.py`:

```python
from application.websocket.handlers.control_handlers import ModelChangeHandler

# Register in MESSAGE_HANDLERS
"control.conversation.model": ModelChangeHandler(connection_manager),
```

---

## 9. Backwards Compatibility

- All new fields in `system.connection.established` are optional with sensible defaults
- Clients that don't understand model selection will simply not display the selector
- Existing messages and flows are unaffected
- Server continues to function if client never sends model change requests

---

## 10. Future Considerations

1. **Per-Message Model Selection**: Allow specifying model per message (not just conversation-wide)
2. **Model Capabilities Negotiation**: Communicate what features each model supports (vision, function calling, etc.)
3. **Cost/Token Tracking**: Include usage stats per model in responses
4. **Model Presets**: Allow named configurations (e.g., "creative", "precise") that map to model + temperature settings
