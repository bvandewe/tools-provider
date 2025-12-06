"""Ollama LLM Provider implementation.

This module provides the Ollama implementation of the LlmProvider interface,
suitable for local development and self-hosted deployments.

Features:
- Streaming and non-streaming chat completions
- Tool/function calling support
- Health check and model availability verification
- Configurable via LlmConfig or Settings
"""

import json
import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional
from uuid import uuid4

import httpx

from application.agents.llm_provider import LlmConfig, LlmMessage, LlmProvider, LlmResponse, LlmStreamChunk, LlmToolCall, LlmToolDefinition

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

logger = logging.getLogger(__name__)


class OllamaLlmProvider(LlmProvider):
    """Ollama implementation of the LLM provider interface.

    This provider connects to a local or remote Ollama instance and provides
    chat completion capabilities with optional tool/function calling.

    Configuration:
        - base_url: Ollama API URL (default: http://localhost:11434)
        - model: Model name (e.g., "llama3.2:3b", "mistral:7b")
        - temperature, top_p: Sampling parameters
        - extra["num_ctx"]: Context window size (default: 8192)

    Usage:
        config = LlmConfig(model="llama3.2:3b", base_url="http://localhost:11434")
        provider = OllamaLlmProvider(config)
        response = await provider.chat([LlmMessage.user("Hello!")])
    """

    def __init__(self, config: LlmConfig) -> None:
        """Initialize the Ollama provider.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self._num_ctx = config.extra.get("num_ctx", 8192)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout,
            )
        return self._client

    def _convert_messages(self, messages: list[LlmMessage]) -> list[dict[str, Any]]:
        """Convert LlmMessage list to Ollama format.

        Args:
            messages: List of LlmMessage objects

        Returns:
            List of messages in Ollama API format
        """
        ollama_messages = []
        for msg in messages:
            ollama_msg: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            # Handle tool calls in assistant messages
            if msg.tool_calls:
                ollama_msg["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ]

            ollama_messages.append(ollama_msg)

        return ollama_messages

    def _convert_tools(self, tools: Optional[list[LlmToolDefinition]]) -> Optional[list[dict[str, Any]]]:
        """Convert tool definitions to Ollama format.

        Args:
            tools: List of tool definitions

        Returns:
            List of tools in Ollama API format
        """
        if not tools:
            return None
        return [tool.to_ollama_format() for tool in tools]

    def _parse_tool_calls(self, ollama_tool_calls: list[dict[str, Any]]) -> list[LlmToolCall]:
        """Parse tool calls from Ollama response.

        Args:
            ollama_tool_calls: Tool calls from Ollama response

        Returns:
            List of LlmToolCall objects
        """
        tool_calls = []
        for tc in ollama_tool_calls:
            func = tc.get("function", {})
            tool_calls.append(
                LlmToolCall(
                    id=tc.get("id", str(uuid4())),
                    name=func.get("name", ""),
                    arguments=func.get("arguments", {}),
                )
            )
        return tool_calls

    async def chat(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> LlmResponse:
        """Send a chat completion request to Ollama.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Returns:
            Complete response from Ollama
        """
        client = await self._get_client()

        payload = {
            "model": self._config.model,
            "messages": self._convert_messages(messages),
            "stream": False,
            "options": {
                "temperature": self._config.temperature,
                "top_p": self._config.top_p,
                "num_ctx": self._num_ctx,
            },
        }

        ollama_tools = self._convert_tools(tools)
        if ollama_tools:
            payload["tools"] = ollama_tools

        try:
            logger.debug(f"Ollama request: model={self._config.model}, messages={len(messages)}")
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            # Parse response
            message = data.get("message", {})
            content = message.get("content", "")
            tool_calls = None

            if "tool_calls" in message:
                tool_calls = self._parse_tool_calls(message["tool_calls"])

            finish_reason = "tool_calls" if tool_calls else "stop"

            return LlmResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=data.get("eval_count"),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            raise

    async def chat_stream(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> AsyncIterator[LlmStreamChunk]:
        """Send a streaming chat completion request to Ollama.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Yields:
            Streaming chunks from Ollama
        """
        client = await self._get_client()

        payload = {
            "model": self._config.model,
            "messages": self._convert_messages(messages),
            "stream": True,
            "options": {
                "temperature": self._config.temperature,
                "top_p": self._config.top_p,
                "num_ctx": self._num_ctx,
            },
        }

        ollama_tools = self._convert_tools(tools)
        if ollama_tools:
            payload["tools"] = ollama_tools

        try:
            logger.debug(f"Ollama stream request: model={self._config.model}, messages={len(messages)}")

            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Ollama response line: {line}")
                        continue

                    # Check if done
                    if chunk.get("done", False):
                        # Parse final message for tool calls
                        tool_calls = None
                        finish_reason = "stop"

                        if "message" in chunk:
                            msg = chunk["message"]
                            if "tool_calls" in msg:
                                tool_calls = self._parse_tool_calls(msg["tool_calls"])
                                finish_reason = "tool_calls"

                        yield LlmStreamChunk(
                            content="",
                            tool_calls=tool_calls,
                            done=True,
                            finish_reason=finish_reason,
                        )
                        break

                    # Extract content chunk
                    content = ""
                    if "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]

                    yield LlmStreamChunk(content=content, done=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            yield LlmStreamChunk(
                content="",
                done=True,
                finish_reason=f"error: HTTP {e.response.status_code}",
            )
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            yield LlmStreamChunk(
                content="",
                done=True,
                finish_reason=f"error: {str(e)}",
            )

    async def health_check(self) -> bool:
        """Check if Ollama is available and the model is loaded.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Check if our model is available
            model_name = self._config.model.split(":")[0]
            model_available = any(self._config.model in m or m.startswith(model_name) for m in models)

            if not model_available:
                logger.warning(f"Model '{self._config.model}' not found. Available: {models}")
                return False

            logger.debug(f"Ollama health check passed. Model '{self._config.model}' available.")
            return True

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def pull_model(self) -> bool:
        """Pull the configured model if not available.

        Returns:
            True if model is available after pull
        """
        try:
            client = await self._get_client()

            logger.info(f"Pulling model '{self._config.model}'...")
            response = await client.post(
                "/api/pull",
                json={"name": self._config.model},
                timeout=600.0,  # 10 minutes for model download
            )
            response.raise_for_status()
            logger.info(f"Model '{self._config.model}' pulled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False

    @staticmethod
    def configure(builder: "ApplicationBuilderBase") -> None:
        """Configure OllamaLlmProvider in the service collection.

        Args:
            builder: The application builder
        """
        from application.settings import Settings, app_settings

        # Get settings - prefer from builder's DI container, fallback to app_settings
        settings: Optional[Settings] = None
        for desc in builder.services:
            if desc.service_type is Settings and desc.singleton:
                settings = desc.singleton
                break

        if settings is None:
            logger.info("Settings not found in DI services, using app_settings singleton")
            settings = app_settings

        # Log settings for debugging
        logger.info(f"OllamaLlmProvider configuring with: model='{settings.ollama_model}', url='{settings.ollama_url}'")

        if not settings.ollama_model:
            logger.error("AGENT_HOST_OLLAMA_MODEL is empty! Check environment variables.")
            raise ValueError("ollama_model cannot be empty - set AGENT_HOST_OLLAMA_MODEL environment variable")

        # Create config from settings
        config = LlmConfig(
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
            top_p=settings.ollama_top_p,
            timeout=settings.ollama_timeout,
            base_url=settings.ollama_url,
            extra={"num_ctx": settings.ollama_num_ctx},
        )

        provider = OllamaLlmProvider(config)

        # Register as both concrete type and abstract interface
        builder.services.add_singleton(OllamaLlmProvider, singleton=provider)
        builder.services.add_singleton(LlmProvider, singleton=provider)

        logger.info(f"✅ Configured OllamaLlmProvider: model={settings.ollama_model}, url={settings.ollama_url}")
