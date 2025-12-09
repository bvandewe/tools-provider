"""Ollama LLM Provider implementation.

This module provides the Ollama implementation of the LlmProvider interface,
suitable for local development and self-hosted deployments.

Features:
- Streaming and non-streaming chat completions
- Tool/function calling support
- Health check and model availability verification
- Configurable via LlmConfig or Settings
- OpenTelemetry tracing and metrics
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional
from uuid import uuid4

import httpx
from application.agents.llm_provider import LlmConfig, LlmMessage, LlmProvider, LlmProviderError, LlmProviderType, LlmResponse, LlmStreamChunk, LlmToolCall, LlmToolDefinition
from observability import llm_request_count, llm_request_time, llm_tool_calls
from opentelemetry import trace

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# Legacy alias for backward compatibility
class OllamaError(LlmProviderError):
    """Custom exception for Ollama-specific errors.

    This is now an alias for LlmProviderError with provider="ollama".
    Kept for backward compatibility with existing code.
    """

    def __init__(self, message: str, error_code: str, is_retryable: bool = False, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code=error_code,
            provider="ollama",
            is_retryable=is_retryable,
            details=details,
        )


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

    PROVIDER_NAME = "ollama"

    def __init__(self, config: LlmConfig) -> None:
        """Initialize the Ollama provider.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        self._num_ctx = config.extra.get("num_ctx", 8192)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> LlmProviderType:
        """Get the provider type identifier."""
        return LlmProviderType.OLLAMA

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

        Raises:
            OllamaError: If Ollama is unavailable or model is not found
        """
        client = await self._get_client()
        model = self.current_model

        payload = {
            "model": model,
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
            logger.debug(f"Ollama request: model={model}, messages={len(messages)}")
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

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self._base_url}: {e}")
            raise OllamaError(
                message="Cannot connect to AI model service",
                error_code="ollama_unavailable",
                is_retryable=True,
                details={"url": self._base_url},
            )
        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out: {e}")
            raise OllamaError(
                message="AI model request timed out",
                error_code="ollama_timeout",
                is_retryable=True,
            )
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {error_text}")

            # Check for model not found error
            if "not found" in error_text.lower() or e.response.status_code == 404:
                raise OllamaError(
                    message=f"AI model '{model}' is not available",
                    error_code="model_not_found",
                    is_retryable=False,
                    details={"model": model, "hint": f"Run: ollama pull {model}"},
                )

            raise OllamaError(
                message=f"AI model error: {error_text[:200]}",
                error_code="ollama_error",
                is_retryable=e.response.status_code >= 500,
            )
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            raise OllamaError(
                message="Failed to communicate with AI model",
                error_code="ollama_request_error",
                is_retryable=True,
            )

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

        Raises:
            OllamaError: If Ollama is unavailable or model is not found
        """
        client = await self._get_client()
        start_time = time.time()
        model = self.current_model

        payload = {
            "model": model,
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

        # Record LLM request metric
        llm_request_count.add(1, {"model": model, "has_tools": str(bool(ollama_tools))})

        with tracer.start_as_current_span("ollama.chat_stream") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.message_count", len(messages))
            span.set_attribute("llm.tool_count", len(ollama_tools) if ollama_tools else 0)
            span.set_attribute("llm.temperature", self._config.temperature)

            try:
                logger.info(f"🔧 Ollama stream request: model={model}, messages={len(messages)}, tools={len(ollama_tools) if ollama_tools else 0}")
                if ollama_tools:
                    logger.info(f"🔧 Sending {len(ollama_tools)} tools to Ollama: {[t['function']['name'] for t in ollama_tools]}")
                    # Log first tool schema for debugging
                    if ollama_tools:
                        logger.debug(f"🔧 First tool schema sample: {json.dumps(ollama_tools[0], indent=2)}")
                else:
                    logger.warning("⚠️ NO TOOLS being sent to Ollama! Tool definitions list is empty or None.")

                # Log the messages being sent for debugging
                for i, msg in enumerate(payload["messages"]):
                    role = msg.get("role", "unknown")
                    content_preview = str(msg.get("content", ""))[:100] + "..." if len(str(msg.get("content", ""))) > 100 else str(msg.get("content", ""))
                    logger.debug(f"📨 Message {i}: role={role}, content_preview={content_preview!r}")

                async with client.stream("POST", "/api/chat", json=payload) as response:
                    # Check for HTTP errors before streaming
                    if response.status_code != 200:
                        error_content = await response.aread()
                        error_text = error_content.decode("utf-8", errors="replace")
                        logger.error(f"Ollama HTTP error: {response.status_code} - {error_text}")

                        if "not found" in error_text.lower() or response.status_code == 404:
                            raise OllamaError(
                                message=f"AI model '{model}' is not available",
                                error_code="model_not_found",
                                is_retryable=False,
                                details={"model": model, "hint": f"Run: ollama pull {model}"},
                            )
                        raise OllamaError(
                            message=f"AI model error: {error_text[:200]}",
                            error_code="ollama_error",
                            is_retryable=response.status_code >= 500,
                        )

                    chunk_count = 0
                    # Accumulate tool_calls across chunks - Ollama may send them before the final chunk
                    accumulated_tool_calls: list[dict[str, Any]] = []

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        chunk_count += 1
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Ollama response line: {line}")
                            continue

                        # Log EVERY chunk when done OR first few chunks for debugging
                        if chunk_count <= 3 or chunk.get("done", False):
                            logger.info(f"📦 Ollama chunk #{chunk_count}: {json.dumps(chunk)[:500]}")

                        # Accumulate tool_calls from any chunk (Ollama sends them BEFORE the final done chunk)
                        if "message" in chunk and "tool_calls" in chunk["message"]:
                            accumulated_tool_calls.extend(chunk["message"]["tool_calls"])
                            logger.info(f"🔧 Accumulated {len(chunk['message']['tool_calls'])} tool_calls from chunk #{chunk_count}")

                        # Check if done
                        if chunk.get("done", False):
                            # Record request duration
                            duration_ms = (time.time() - start_time) * 1000
                            llm_request_time.record(duration_ms, {"model": model})
                            span.set_attribute("llm.duration_ms", duration_ms)

                            # Parse accumulated tool calls
                            tool_calls = None
                            finish_reason = "stop"

                            if accumulated_tool_calls:
                                tool_calls = self._parse_tool_calls(accumulated_tool_calls)
                                finish_reason = "tool_calls"
                                logger.info(f"✅ Ollama returned {len(tool_calls)} tool_calls: {[(tc.name, list(tc.arguments.keys())) for tc in tool_calls]}")

                                # Record tool call metrics
                                for tc in tool_calls:
                                    llm_tool_calls.add(1, {"model": self._config.model, "tool_name": tc.name})
                                span.set_attribute("llm.tool_call_count", len(tool_calls))
                            else:
                                msg = chunk.get("message", {})
                                logger.info(f"📝 Ollama returned TEXT response (no tool_calls). Content length: {len(msg.get('content', ''))}")
                                span.set_attribute("llm.tool_call_count", 0)

                            span.set_attribute("llm.finish_reason", finish_reason)
                            yield LlmStreamChunk(
                                content="",
                                tool_calls=tool_calls,
                                done=True,
                                finish_reason=finish_reason,
                            )
                            logger.info(f"🏁 Ollama stream completed: {chunk_count} chunks, finish_reason={finish_reason}, tool_calls={len(tool_calls) if tool_calls else 0}")
                            break

                        # Extract content chunk
                        content = ""
                        if "message" in chunk and "content" in chunk["message"]:
                            content = chunk["message"]["content"]

                        yield LlmStreamChunk(content=content, done=False)

                    # If we exit the loop without hitting 'done', log it
                    logger.warning(f"⚠️ Ollama stream ended without 'done' flag after {chunk_count} chunks")

            except OllamaError:
                # Re-raise our custom errors
                raise
            except httpx.ConnectError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"Cannot connect to Ollama at {self._base_url}: {e}")
                raise OllamaError(
                    message="Cannot connect to AI model service",
                    error_code="ollama_unavailable",
                    is_retryable=True,
                    details={"url": self._base_url},
                )
            except httpx.TimeoutException as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"Ollama request timed out: {e}")
                raise OllamaError(
                    message="AI model request timed out",
                    error_code="ollama_timeout",
                    is_retryable=True,
                )
            except httpx.HTTPStatusError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                error_text = e.response.text if hasattr(e.response, "text") else str(e)
                logger.error(f"Ollama HTTP error: {e.response.status_code} - {error_text}")

                if "not found" in error_text.lower() or e.response.status_code == 404:
                    raise OllamaError(
                        message=f"AI model '{model}' is not available",
                        error_code="model_not_found",
                        is_retryable=False,
                        details={"model": model, "hint": f"Run: ollama pull {model}"},
                    )
                raise OllamaError(
                    message=f"AI model error: {error_text[:200]}",
                    error_code="ollama_error",
                    is_retryable=e.response.status_code >= 500,
                )
            except httpx.RequestError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error(f"Ollama request error: {e}")
                raise OllamaError(
                    message="Failed to communicate with AI model",
                    error_code="ollama_request_error",
                    is_retryable=True,
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
            model_name = self.current_model.split(":")[0]
            model_available = any(self.current_model in m or m.startswith(model_name) for m in models)

            if not model_available:
                logger.warning(f"Model '{self.current_model}' not found. Available: {models}")
                return False

            logger.debug(f"Ollama health check passed. Model '{self.current_model}' available.")
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
