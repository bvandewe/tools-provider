"""Business metrics for Agent Host service.

Defines OpenTelemetry metrics for:
- Chat: Message processing and streaming
- Conversations: Lifecycle management
- LLM: Request latency, token usage, tool calls
- Tools: Fetching, caching, execution
"""

from opentelemetry import metrics

meter = metrics.get_meter("agent_host")

# =============================================================================
# CHAT METRICS
# =============================================================================

chat_messages_received = meter.create_counter(
    name="agent_host.chat.messages_received",
    description="Total chat messages received from users",
    unit="1",
)

chat_messages_sent = meter.create_counter(
    name="agent_host.chat.messages_sent",
    description="Total chat messages sent to users (including streamed)",
    unit="1",
)

chat_session_duration = meter.create_histogram(
    name="agent_host.chat.session_duration",
    description="Duration of chat sessions (from message to response completion)",
    unit="ms",
)

# =============================================================================
# CONVERSATION METRICS
# =============================================================================

conversations_created = meter.create_counter(
    name="agent_host.conversations.created",
    description="Total conversations created",
    unit="1",
)

conversations_deleted = meter.create_counter(
    name="agent_host.conversations.deleted",
    description="Total conversations deleted",
    unit="1",
)

# =============================================================================
# LLM METRICS
# =============================================================================

llm_request_count = meter.create_counter(
    name="agent_host.llm.request_count",
    description="Total LLM requests made",
    unit="1",
)

llm_request_time = meter.create_histogram(
    name="agent_host.llm.request_time",
    description="Time for LLM requests (first token to last token)",
    unit="ms",
)

llm_token_count = meter.create_histogram(
    name="agent_host.llm.token_count",
    description="Number of tokens in LLM responses",
    unit="1",
)

llm_tool_calls = meter.create_counter(
    name="agent_host.llm.tool_calls",
    description="Total tool calls made by LLM",
    unit="1",
)

# =============================================================================
# TOOL METRICS
# =============================================================================

tools_fetched = meter.create_counter(
    name="agent_host.tools.fetched",
    description="Total times tools were fetched from Tools Provider",
    unit="1",
)

tool_cache_hits = meter.create_counter(
    name="agent_host.tools.cache_hits",
    description="Tool cache hits",
    unit="1",
)

tool_cache_misses = meter.create_counter(
    name="agent_host.tools.cache_misses",
    description="Tool cache misses",
    unit="1",
)

tool_execution_count = meter.create_counter(
    name="agent_host.tools.execution_count",
    description="Total tool executions",
    unit="1",
)

tool_execution_time = meter.create_histogram(
    name="agent_host.tools.execution_time",
    description="Time to execute tools via Tools Provider",
    unit="ms",
)

tool_execution_errors = meter.create_counter(
    name="agent_host.tools.execution_errors",
    description="Total tool execution errors",
    unit="1",
)
