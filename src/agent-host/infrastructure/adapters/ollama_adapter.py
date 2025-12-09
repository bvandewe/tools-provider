"""Ollama adapter for LLM interactions."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from neuroglia.hosting.abstractions import ApplicationBuilderBase

from application.settings import Settings

logger = logging.getLogger(__name__)


class OllamaAdapter:
    """
    Adapter for communicating with Ollama LLM API.

    Supports both streaming and non-streaming chat completions,
    with tool/function calling capabilities.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_ctx: int = 8192,
    ) -> None:
        """
        Initialize the Ollama adapter.

        Args:
            base_url: Ollama API base URL
            model: Model name to use
            timeout: HTTP timeout in seconds
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            num_ctx: Context window size
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._temperature = temperature
        self._top_p = top_p
        self._num_ctx = num_ctx
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat request (non-streaming).

        Args:
            messages: List of messages in Ollama format
            tools: Optional list of tools in Ollama function calling format

        Returns:
            Complete response from Ollama
        """
        client = await self._get_client()

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "top_p": self._top_p,
                "num_ctx": self._num_ctx,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            raise

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Send a streaming chat request.

        Args:
            messages: List of messages in Ollama format
            tools: Optional list of tools in Ollama function calling format

        Yields:
            Streaming chunks from Ollama
        """
        client = await self._get_client()

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self._temperature,
                "top_p": self._top_p,
                "num_ctx": self._num_ctx,
            },
        }

        if tools:
            payload["tools"] = tools

        try:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json

                            chunk = json.loads(line)
                            yield chunk
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Ollama response line: {line}")
                            continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            yield {
                "done": True,
                "error": f"HTTP error: {e.response.status_code}",
            }
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {e}")
            yield {
                "done": True,
                "error": f"Request error: {str(e)}",
            }

    async def health_check(self) -> bool:
        """
        Check if Ollama is available and the model is loaded.

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
            model_available = any(self._model in m or m.startswith(self._model.split(":")[0]) for m in models)

            if not model_available:
                logger.warning(f"Model '{self._model}' not found. Available: {models}")
                return False

            return True

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def pull_model(self) -> bool:
        """
        Pull the configured model if not available.

        Returns:
            True if model is available after pull
        """
        try:
            client = await self._get_client()

            # Pull model (this can take a while)
            logger.info(f"Pulling model '{self._model}'...")
            response = await client.post(
                "/api/pull",
                json={"name": self._model},
                timeout=600.0,  # 10 minutes for model download
            )
            response.raise_for_status()
            logger.info(f"Model '{self._model}' pulled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure OllamaAdapter in the service collection.

        Args:
            builder: The application builder
        """
        settings: Settings = next(
            (d.singleton for d in builder.services if d.service_type is Settings),
            None,
        )

        if settings is None:
            logger.warning("Settings not found in services, using defaults")
            settings = Settings()

        adapter = OllamaAdapter(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
            temperature=settings.ollama_temperature,
            top_p=settings.ollama_top_p,
            num_ctx=settings.ollama_num_ctx,
        )

        builder.services.add_singleton(OllamaAdapter, singleton=adapter)
        logger.info(f"Configured OllamaAdapter with model={settings.ollama_model}")
