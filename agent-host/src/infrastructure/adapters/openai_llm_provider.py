"""OpenAI LLM Provider implementation.

This module provides the OpenAI implementation of the LlmProvider interface,
supporting both standard OpenAI API and Azure-style endpoints (e.g., Cisco Circuit).

Features:
- Streaming and non-streaming chat completions
- Tool/function calling support
- OAuth2 and API Key authentication
- Health check and model availability verification
- Configurable via LlmConfig or Settings
- OpenTelemetry tracing and metrics

Authentication Modes:
- API Key: Standard OpenAI API with Authorization: Bearer <key>
- OAuth2: Client credentials flow for Azure-style endpoints (e.g., Cisco Circuit)
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional
from uuid import uuid4

import httpx
from opentelemetry import trace

from application.agents.llm_provider import LlmConfig, LlmMessage, LlmProvider, LlmProviderError, LlmProviderType, LlmResponse, LlmStreamChunk, LlmToolCall, LlmToolDefinition
from observability import llm_request_count, llm_request_time, llm_tool_calls

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

    from infrastructure.openai_token_cache import OpenAiTokenCache

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class OpenAiLlmProvider(LlmProvider):
    """OpenAI implementation of the LLM provider interface.

    This provider connects to OpenAI API or compatible endpoints (Azure, Cisco Circuit)
    and provides chat completion capabilities with tool/function calling.

    Configuration:
        - base_url: API endpoint (e.g., "https://api.openai.com/v1", "https://chat-ai.cisco.com")
        - model: Model name (e.g., "gpt-4o", "gpt-3.5-turbo")
        - api_key: Direct API key (for standard OpenAI)
        - extra["auth_type"]: "api_key" or "oauth2"
        - extra["api_version"]: API version for Azure-style endpoints
        - extra["app_key"]: Circuit app key
        - extra["client_id"]: OAuth2 client ID
        - extra["client_secret"]: OAuth2 client secret
        - extra["oauth_endpoint"]: OAuth2 token endpoint

    Usage:
        config = LlmConfig(
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-xxx",  # pragma: allowlist secret
            extra={"auth_type": "api_key"}
        )
        provider = OpenAiLlmProvider(config)
        response = await provider.chat([LlmMessage.user("Hello!")])
    """

    PROVIDER_NAME = "openai"

    def __init__(
        self,
        config: LlmConfig,
        token_cache: Optional["OpenAiTokenCache"] = None,
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            config: LLM configuration
            token_cache: Optional token cache for OAuth2 mode
        """
        super().__init__(config)
        self._base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        self._api_version = config.extra.get("api_version", "2024-05-01-preview")
        self._auth_type = config.extra.get("auth_type", "api_key")
        self._app_key = config.extra.get("app_key", "")
        self._client_id = config.extra.get("client_id", "")
        self._client_secret = config.extra.get("client_secret", "")
        self._oauth_endpoint = config.extra.get("oauth_endpoint", "")
        self._token_ttl = config.extra.get("token_ttl", 3600)
        self._client_id_header = config.extra.get("client_id_header", "") or self._client_id
        self._stop_sequences: list[str] = config.extra.get("stop_sequences", [])
        self._token_cache = token_cache
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_type(self) -> LlmProviderType:
        """Get the provider type identifier."""
        return LlmProviderType.OPENAI

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout,
            )
        return self._client

    async def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers based on auth type.

        Returns:
            Dictionary of headers including Authorization

        Raises:
            LlmProviderError: If authentication fails
        """
        headers: dict[str, str] = {}

        if self._auth_type == "oauth2":
            if not self._token_cache:
                raise LlmProviderError(
                    message="OAuth2 authentication requires token cache",
                    error_code="openai_auth_config_error",
                    provider=self.PROVIDER_NAME,
                    is_retryable=False,
                )

            if not all([self._oauth_endpoint, self._client_id, self._client_secret]):
                raise LlmProviderError(
                    message="OAuth2 authentication requires endpoint, client_id, and client_secret",
                    error_code="openai_auth_config_error",
                    provider=self.PROVIDER_NAME,
                    is_retryable=False,
                )

            try:
                token = await self._token_cache.get_or_refresh_token(
                    oauth_endpoint=self._oauth_endpoint,
                    client_id=self._client_id,
                    client_secret=self._client_secret,
                    token_ttl=self._token_ttl,
                )
                # Circuit/Azure-style API expects 'api-key' header, not 'Authorization: Bearer'
                headers["api-key"] = token
            except Exception as e:
                raise LlmProviderError(
                    message=f"Failed to obtain OAuth2 token: {e}",
                    error_code="openai_auth_error",
                    provider=self.PROVIDER_NAME,
                    is_retryable=True,
                )

            # Add Circuit-specific client-id header
            if self._client_id_header:
                headers["client-id"] = self._client_id_header

        else:  # api_key mode
            if not self._config.api_key:
                raise LlmProviderError(
                    message="API key authentication requires api_key",
                    error_code="openai_auth_config_error",
                    provider=self.PROVIDER_NAME,
                    is_retryable=False,
                )
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        return headers

    def _build_api_url(self, endpoint: str) -> str:
        """Build the full API URL.

        Handles both standard OpenAI format and Azure-style format.

        Args:
            endpoint: API endpoint (e.g., "chat/completions")

        Returns:
            Full URL
        """
        # Azure-style endpoints use query parameter for version
        if "azure" in self._base_url.lower() or "cisco" in self._base_url.lower():
            return f"{self._base_url}/openai/deployments/{self.current_model}/{endpoint}?api-version={self._api_version}"
        else:
            # Standard OpenAI format
            return f"{self._base_url}/{endpoint}"

    def _convert_messages(self, messages: list[LlmMessage]) -> list[dict[str, Any]]:
        """Convert LlmMessage list to OpenAI format.

        Args:
            messages: List of LlmMessage objects

        Returns:
            List of messages in OpenAI API format
        """
        openai_messages = []
        for msg in messages:
            openai_msg: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content or "",
            }

            # Handle tool calls in assistant messages
            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # Handle tool result messages
            if msg.role.value == "tool" and msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
                if msg.name:
                    openai_msg["name"] = msg.name

            openai_messages.append(openai_msg)

        return openai_messages

    def _convert_tools(self, tools: Optional[list[LlmToolDefinition]]) -> Optional[list[dict[str, Any]]]:
        """Convert tool definitions to OpenAI format.

        Args:
            tools: List of tool definitions

        Returns:
            List of tools in OpenAI API format
        """
        if not tools:
            return None
        return [tool.to_openai_format() for tool in tools]

    def _parse_tool_calls(self, openai_tool_calls: list[dict[str, Any]]) -> list[LlmToolCall]:
        """Parse tool calls from OpenAI response.

        Args:
            openai_tool_calls: Tool calls from OpenAI response

        Returns:
            List of LlmToolCall objects
        """
        tool_calls = []
        for tc in openai_tool_calls:
            func = tc.get("function", {})
            arguments = func.get("arguments", "{}")

            # Parse arguments if string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            tool_calls.append(
                LlmToolCall(
                    id=tc.get("id", str(uuid4())),
                    name=func.get("name", ""),
                    arguments=arguments,
                )
            )
        return tool_calls

    def _build_request_body(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]],
        stream: bool,
    ) -> dict[str, Any]:
        """Build the request body for chat completion.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            stream: Whether to stream the response

        Returns:
            Request body dictionary
        """
        body: dict[str, Any] = {
            "model": self.current_model,
            "messages": self._convert_messages(messages),
            "temperature": self._config.temperature,
            "top_p": self._config.top_p,
            "stream": stream,
        }

        if self._config.max_tokens:
            body["max_tokens"] = self._config.max_tokens

        # Add tools if provided
        openai_tools = self._convert_tools(tools)
        if openai_tools:
            body["tools"] = openai_tools
            body["tool_choice"] = "auto"

        # Add Circuit-specific user payload
        if self._app_key:
            body["user"] = json.dumps({"appkey": self._app_key})

        # Add stop sequences if configured (for ChatML-format models)
        if self._stop_sequences:
            body["stop"] = self._stop_sequences

        return body

    async def chat(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> LlmResponse:
        """Send a chat completion request to OpenAI.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Returns:
            Complete response from OpenAI

        Raises:
            LlmProviderError: If API call fails
        """
        client = await self._get_client()
        model = self.current_model
        start_time = time.time()

        try:
            headers = await self._get_auth_headers()
            headers["Content-Type"] = "application/json"

            body = self._build_request_body(messages, tools, stream=False)
            url = self._build_api_url("chat/completions")

            logger.debug(f"OpenAI request: model={model}, messages={len(messages)}")

            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            llm_request_count.add(1, {"model": model, "has_tools": str(bool(tools)), "provider": "openai"})
            llm_request_time.record(duration_ms, {"model": model, "provider": "openai"})

            # Parse response
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "") or ""
            tool_calls = None

            if "tool_calls" in message:
                tool_calls = self._parse_tool_calls(message["tool_calls"])
                for tc in tool_calls:
                    llm_tool_calls.add(1, {"model": model, "tool_name": tc.name, "provider": "openai"})

            finish_reason = choice.get("finish_reason", "stop")
            usage = data.get("usage")

            return LlmResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage,
            )

        except LlmProviderError:
            raise
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to OpenAI at {self._base_url}: {e}")
            raise LlmProviderError(
                message="Cannot connect to OpenAI service",
                error_code="openai_unavailable",
                provider=self.PROVIDER_NAME,
                is_retryable=True,
                details={"url": self._base_url},
            )
        except httpx.TimeoutException as e:
            logger.error(f"OpenAI request timed out: {e}")
            raise LlmProviderError(
                message="OpenAI request timed out",
                error_code="openai_timeout",
                provider=self.PROVIDER_NAME,
                is_retryable=True,
            )
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"OpenAI HTTP error: {e.response.status_code} - {error_text}")
            raise self._handle_http_error(e, model)
        except httpx.RequestError as e:
            logger.error(f"OpenAI request error: {e}")
            raise LlmProviderError(
                message="Failed to communicate with OpenAI",
                error_code="openai_request_error",
                provider=self.PROVIDER_NAME,
                is_retryable=True,
            )

    async def chat_stream(
        self,
        messages: list[LlmMessage],
        tools: Optional[list[LlmToolDefinition]] = None,
    ) -> AsyncIterator[LlmStreamChunk]:
        """Send a streaming chat completion request to OpenAI.

        Args:
            messages: Conversation messages
            tools: Optional list of available tools

        Yields:
            Streaming chunks from OpenAI

        Raises:
            LlmProviderError: If API call fails
        """
        client = await self._get_client()
        model = self.current_model
        start_time = time.time()

        # Record LLM request metric
        llm_request_count.add(1, {"model": model, "has_tools": str(bool(tools)), "provider": "openai"})

        with tracer.start_as_current_span("openai.chat_stream") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.message_count", len(messages))
            span.set_attribute("llm.provider", "openai")

            try:
                headers = await self._get_auth_headers()
                headers["Content-Type"] = "application/json"
                headers["Accept"] = "text/event-stream"

                body = self._build_request_body(messages, tools, stream=True)
                url = self._build_api_url("chat/completions")

                # Debug logging for headers (mask sensitive values)
                debug_headers = {k: (v[:20] + "..." if k.lower() == "authorization" and len(v) > 20 else v) for k, v in headers.items()}
                logger.info(f"🔧 OpenAI stream request: model={model}, messages={len(messages)}, tools={len(tools) if tools else 0}")
                logger.debug(f"🔧 OpenAI request URL: {url}")
                logger.debug(f"🔧 OpenAI request headers: {debug_headers}")

                async with client.stream("POST", url, json=body, headers=headers) as response:
                    if response.status_code != 200:
                        error_content = await response.aread()
                        error_text = error_content.decode("utf-8", errors="replace")
                        logger.error(f"OpenAI HTTP error: {response.status_code} - {error_text}")
                        raise self._handle_http_error_from_status(response.status_code, error_text, model)

                    chunk_count = 0
                    accumulated_tool_calls: dict[int, dict[str, Any]] = {}  # Index -> tool call data
                    accumulated_content = ""

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        # SSE format: "data: {...}"
                        if line.startswith("data: "):
                            data_str = line[6:]

                            if data_str.strip() == "[DONE]":
                                # Stream complete
                                duration_ms = (time.time() - start_time) * 1000
                                llm_request_time.record(duration_ms, {"model": model, "provider": "openai"})
                                span.set_attribute("llm.duration_ms", duration_ms)

                                # Parse accumulated tool calls
                                tool_calls = None
                                finish_reason = "stop"

                                if accumulated_tool_calls:
                                    tool_calls = self._parse_accumulated_tool_calls(accumulated_tool_calls)
                                    finish_reason = "tool_calls"
                                    for tc in tool_calls:
                                        llm_tool_calls.add(1, {"model": model, "tool_name": tc.name, "provider": "openai"})
                                    span.set_attribute("llm.tool_call_count", len(tool_calls))
                                    logger.info(f"✅ OpenAI returned {len(tool_calls)} tool_calls")
                                else:
                                    logger.info(f"📝 OpenAI returned TEXT response. Content length: {len(accumulated_content)}")
                                    span.set_attribute("llm.tool_call_count", 0)

                                span.set_attribute("llm.finish_reason", finish_reason)
                                yield LlmStreamChunk(
                                    content="",
                                    tool_calls=tool_calls,
                                    done=True,
                                    finish_reason=finish_reason,
                                )
                                logger.info(f"🏁 OpenAI stream completed: {chunk_count} chunks")
                                break

                            try:
                                chunk = json.loads(data_str)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse OpenAI chunk: {data_str}")
                                continue

                            chunk_count += 1

                            # Extract delta
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})

                            # Handle content chunks
                            content = delta.get("content", "")
                            if content:
                                accumulated_content += content
                                yield LlmStreamChunk(content=content, done=False)

                            # Handle tool call chunks (streamed incrementally)
                            if "tool_calls" in delta:
                                for tc_delta in delta["tool_calls"]:
                                    idx = tc_delta.get("index", 0)
                                    if idx not in accumulated_tool_calls:
                                        accumulated_tool_calls[idx] = {
                                            "id": tc_delta.get("id", ""),
                                            "type": tc_delta.get("type", "function"),
                                            "function": {"name": "", "arguments": ""},
                                        }

                                    if "id" in tc_delta and tc_delta["id"]:
                                        accumulated_tool_calls[idx]["id"] = tc_delta["id"]

                                    func_delta = tc_delta.get("function", {})
                                    if "name" in func_delta:
                                        accumulated_tool_calls[idx]["function"]["name"] += func_delta["name"]
                                    if "arguments" in func_delta:
                                        accumulated_tool_calls[idx]["function"]["arguments"] += func_delta["arguments"]

                            # Check for finish_reason in delta
                            if choices[0].get("finish_reason"):
                                # Final chunk with finish reason
                                pass

            except LlmProviderError:
                raise
            except httpx.ConnectError as e:
                span.set_attribute("error", True)
                logger.error(f"Cannot connect to OpenAI at {self._base_url}: {e}")
                raise LlmProviderError(
                    message="Cannot connect to OpenAI service",
                    error_code="openai_unavailable",
                    provider=self.PROVIDER_NAME,
                    is_retryable=True,
                    details={"url": self._base_url},
                )
            except httpx.TimeoutException as e:
                span.set_attribute("error", True)
                logger.error(f"OpenAI request timed out: {e}")
                raise LlmProviderError(
                    message="OpenAI request timed out",
                    error_code="openai_timeout",
                    provider=self.PROVIDER_NAME,
                    is_retryable=True,
                )
            except Exception as e:
                span.set_attribute("error", True)
                logger.error(f"OpenAI stream error: {e}")
                raise LlmProviderError(
                    message=f"OpenAI stream error: {e}",
                    error_code="openai_stream_error",
                    provider=self.PROVIDER_NAME,
                    is_retryable=True,
                )

    def _parse_accumulated_tool_calls(self, accumulated: dict[int, dict[str, Any]]) -> list[LlmToolCall]:
        """Parse accumulated tool call chunks into LlmToolCall objects.

        Args:
            accumulated: Dictionary of index -> tool call data

        Returns:
            List of LlmToolCall objects
        """
        tool_calls = []
        for idx in sorted(accumulated.keys()):
            tc = accumulated[idx]
            func = tc.get("function", {})
            arguments_str = func.get("arguments", "{}")

            try:
                arguments = json.loads(arguments_str) if arguments_str else {}
            except json.JSONDecodeError:
                arguments = {}

            tool_calls.append(
                LlmToolCall(
                    id=tc.get("id") or str(uuid4()),
                    name=func.get("name", ""),
                    arguments=arguments,
                )
            )
        return tool_calls

    def _handle_http_error(self, e: httpx.HTTPStatusError, model: str) -> LlmProviderError:
        """Handle HTTP errors and convert to LlmProviderError.

        Args:
            e: The HTTP error
            model: Model name for error details

        Returns:
            Appropriate LlmProviderError
        """
        return self._handle_http_error_from_status(e.response.status_code, e.response.text, model)

    def _handle_http_error_from_status(self, status_code: int, error_text: str, model: str) -> LlmProviderError:
        """Handle HTTP errors by status code.

        Args:
            status_code: HTTP status code
            error_text: Error response text
            model: Model name for error details

        Returns:
            Appropriate LlmProviderError
        """
        # Parse error response if JSON
        error_detail = ""
        try:
            error_json = json.loads(error_text)
            error_detail = error_json.get("error", {}).get("message", error_text[:200])
        except json.JSONDecodeError:
            error_detail = error_text[:200]

        if status_code == 401:
            return LlmProviderError(
                message="OpenAI authentication failed. Check your API key or OAuth credentials.",
                error_code="openai_auth_error",
                provider=self.PROVIDER_NAME,
                is_retryable=False,
            )
        elif status_code == 403:
            return LlmProviderError(
                message="Access denied to OpenAI API. Check your permissions.",
                error_code="openai_forbidden",
                provider=self.PROVIDER_NAME,
                is_retryable=False,
            )
        elif status_code == 404:
            return LlmProviderError(
                message=f"Model '{model}' not found or endpoint not available",
                error_code="openai_model_not_found",
                provider=self.PROVIDER_NAME,
                is_retryable=False,
                details={"model": model},
            )
        elif status_code == 429:
            return LlmProviderError(
                message="OpenAI rate limit exceeded. Please try again later.",
                error_code="openai_rate_limit",
                provider=self.PROVIDER_NAME,
                is_retryable=True,
            )
        elif status_code >= 500:
            return LlmProviderError(
                message=f"OpenAI server error: {error_detail}",
                error_code="openai_server_error",
                provider=self.PROVIDER_NAME,
                is_retryable=True,
            )
        else:
            return LlmProviderError(
                message=f"OpenAI API error: {error_detail}",
                error_code="openai_api_error",
                provider=self.PROVIDER_NAME,
                is_retryable=status_code >= 500,
            )

    async def health_check(self) -> bool:
        """Check if OpenAI is available.

        For OpenAI, we verify authentication works by checking models endpoint.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            headers = await self._get_auth_headers()

            # For standard OpenAI, use models endpoint
            if "openai.com" in self._base_url:
                response = await client.get(f"{self._base_url}/models", headers=headers)
            else:
                # For Azure-style, just verify auth works with a minimal request
                # Can't easily check model availability without making a chat request
                return True

            response.raise_for_status()
            logger.debug("OpenAI health check passed")
            return True

        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def configure(
        builder: "ApplicationBuilderBase",
        token_cache: Optional["OpenAiTokenCache"] = None,
    ) -> Optional["OpenAiLlmProvider"]:
        """Configure OpenAiLlmProvider in the service collection.

        Args:
            builder: The application builder
            token_cache: Optional token cache for OAuth2 mode

        Returns:
            Configured provider or None if not enabled
        """
        from application.settings import Settings, app_settings

        # Get settings
        settings: Optional[Settings] = None
        for desc in builder.services:
            if desc.service_type is Settings and desc.singleton:
                settings = desc.singleton
                break

        if settings is None:
            logger.info("Settings not found in DI services, using app_settings singleton")
            settings = app_settings

        if not settings.openai_enabled:
            logger.info("OpenAI provider is disabled (openai_enabled=False)")
            return None

        if not settings.openai_api_endpoint:
            logger.warning("OpenAI provider enabled but no endpoint configured")
            return None

        logger.info(f"OpenAiLlmProvider configuring: model='{settings.openai_model}', endpoint='{settings.openai_api_endpoint}'")

        # Build extra config
        extra: dict[str, Any] = {
            "auth_type": settings.openai_auth_type,
            "api_version": settings.openai_api_version,
            "app_key": settings.openai_app_key,
            "client_id": settings.openai_oauth_client_id,
            "client_secret": settings.openai_oauth_client_secret,
            "oauth_endpoint": settings.openai_oauth_endpoint,
            "token_ttl": settings.openai_oauth_token_ttl,
            "client_id_header": settings.openai_client_id_header,
        }

        # Parse stop sequences from JSON string
        stop_sequences: list[str] = []
        if settings.openai_stop_sequences:
            try:
                stop_sequences = json.loads(settings.openai_stop_sequences)
                if not isinstance(stop_sequences, list):
                    logger.warning(f"openai_stop_sequences must be a JSON array, got: {type(stop_sequences)}")
                    stop_sequences = []
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse openai_stop_sequences: {e}")
        extra["stop_sequences"] = stop_sequences

        config = LlmConfig(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            top_p=settings.openai_top_p,
            max_tokens=settings.openai_max_tokens,
            timeout=settings.openai_timeout,
            base_url=settings.openai_api_endpoint,
            api_key=settings.openai_api_key,
            extra=extra,
        )

        provider = OpenAiLlmProvider(config, token_cache=token_cache)

        # Register as concrete type (factory will handle abstract interface)
        builder.services.add_singleton(OpenAiLlmProvider, singleton=provider)

        logger.info(f"✅ Configured OpenAiLlmProvider: model={settings.openai_model}, auth={settings.openai_auth_type}")
        return provider
