"""Observability utilities and metrics for Agent Host."""

from .metrics import (
    chat_messages_received,
    chat_messages_sent,
    chat_session_duration,
    conversations_created,
    conversations_deleted,
    llm_request_count,
    llm_request_time,
    llm_token_count,
    llm_tool_calls,
    tool_cache_hits,
    tool_cache_misses,
    tool_execution_count,
    tool_execution_errors,
    tool_execution_time,
    tools_fetched,
)

__all__ = [
    # Chat metrics
    "chat_messages_received",
    "chat_messages_sent",
    "chat_session_duration",
    # Conversation metrics
    "conversations_created",
    "conversations_deleted",
    # LLM metrics
    "llm_request_count",
    "llm_request_time",
    "llm_token_count",
    "llm_tool_calls",
    # Tool metrics
    "tools_fetched",
    "tool_cache_hits",
    "tool_cache_misses",
    "tool_execution_count",
    "tool_execution_time",
    "tool_execution_errors",
]
