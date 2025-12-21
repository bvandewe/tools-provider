"""WebSocket infrastructure for Agent Host Protocol v1.0.0.

This package provides the core WebSocket infrastructure:
- Connection lifecycle management
- Message routing
- State machine for connection states
- Handler base classes

Note: The orchestrator's core data classes (OrchestratorState, ItemExecutionState,
ConversationContext) have been moved to application.orchestrator for better modularity.
Import from application.orchestrator for new code.
"""

# Core state machine - no dependencies on protocol module
# Re-export orchestrator types for backwards compatibility
# Prefer importing from application.orchestrator for new code
from application.orchestrator import (
    ConversationContext,
    ItemExecutionState,
    OrchestratorState,
)
from application.websocket.state import ConnectionState, ConnectionStateMachine

__all__ = [
    "Connection",
    "ConnectionManager",
    "ConnectionState",
    "ConnectionStateMachine",
    "MessageRouter",
    "create_router_with_handlers",
    # Orchestrator types (backwards compat - prefer application.orchestrator)
    "ConversationContext",
    "ItemExecutionState",
    "OrchestratorState",
]


def __getattr__(name: str):
    """Lazy loading of other components to avoid circular imports."""
    if name == "Connection":
        from application.websocket.connection import Connection

        return Connection
    if name == "ConnectionManager":
        from application.websocket.manager import ConnectionManager

        return ConnectionManager
    if name == "MessageRouter":
        from application.websocket.router import MessageRouter

        return MessageRouter
    if name == "create_router_with_handlers":
        from application.websocket.router import create_router_with_handlers

        return create_router_with_handlers
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
