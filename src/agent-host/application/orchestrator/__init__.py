"""Conversation Orchestrator package.

This package provides the core orchestration logic for conversations,
separated from WebSocket transport concerns.

Architecture:
    application/orchestrator/
    ├── __init__.py           # Package exports
    ├── orchestrator.py       # Main Orchestrator coordinator
    ├── context.py            # ConversationContext, ItemExecutionState, OrchestratorState
    ├── handlers/             # Event/message handlers
    │   ├── message_handler.py  # User text message handling
    │   ├── widget_handler.py   # Widget response handling
    │   ├── flow_handler.py     # Flow control (start/pause/cancel)
    │   └── model_handler.py    # LLM model selection
    ├── template/             # Template processing
    │   ├── jinja_renderer.py   # Jinja2 variable substitution
    │   ├── content_generator.py # LLM-based content generation
    │   ├── item_presenter.py   # Item presentation to clients
    │   └── flow_runner.py      # Proactive flow execution
    ├── agent/                # Agent execution
    │   ├── agent_runner.py     # Agent invocation and event handling
    │   ├── tool_executor.py    # Tool execution via ToolProviderClient
    │   └── stream_handler.py   # Content streaming to clients
    └── protocol/             # Protocol message senders
        ├── config_sender.py  # Configuration and flow control
        ├── widget_sender.py  # Widget rendering
        └── content_sender.py # Content streaming
"""

from application.orchestrator.agent import (
    AgentRunner,
    StreamHandler,
    ToolExecutor,
)
from application.orchestrator.context import (
    ConversationContext,
    ItemExecutionState,
    OrchestratorState,
)
from application.orchestrator.handlers import (
    FlowHandler,
    MessageHandler,
    ModelHandler,
    WidgetHandler,
)
from application.orchestrator.orchestrator import Orchestrator
from application.orchestrator.protocol import (
    ConfigSender,
    ContentSender,
    WidgetSender,
)
from application.orchestrator.template import (
    ContentGenerator,
    FlowRunner,
    ItemPresenter,
    JinjaRenderer,
)

__all__ = [
    # Main orchestrator
    "Orchestrator",
    # Context and state
    "ConversationContext",
    "ItemExecutionState",
    "OrchestratorState",
    # Agent execution
    "AgentRunner",
    "StreamHandler",
    "ToolExecutor",
    # Handlers
    "FlowHandler",
    "MessageHandler",
    "ModelHandler",
    "WidgetHandler",
    # Protocol senders
    "ConfigSender",
    "ContentSender",
    "WidgetSender",
    # Template processing
    "ContentGenerator",
    "FlowRunner",
    "ItemPresenter",
    "JinjaRenderer",
]
