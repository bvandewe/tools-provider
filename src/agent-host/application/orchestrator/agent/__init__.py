"""Agent execution package for conversation orchestration.

This subpackage contains classes responsible for agent invocation,
tool execution, and streaming response handling:

- AgentRunner: Executes agents and streams events to clients
- ToolExecutor: Creates tool execution functions for agent use
- StreamHandler: Handles streaming content to WebSocket clients

Agent Execution Architecture:
    AgentRunner
    ├── Builds agent context from conversation history
    ├── Invokes agent.run_stream()
    └── Translates AgentEvents to protocol messages

    ToolExecutor
    ├── Creates tool executor functions
    └── Calls Tools Provider service

    StreamHandler
    ├── Streams content in chunks
    └── Sends completion messages
"""

from application.orchestrator.agent.agent_runner import AgentRunner
from application.orchestrator.agent.stream_handler import StreamHandler
from application.orchestrator.agent.tool_executor import ToolExecutor

__all__ = [
    "AgentRunner",
    "StreamHandler",
    "ToolExecutor",
]
