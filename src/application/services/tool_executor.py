"""Tool Executor service for proxying tool execution to upstream services.

This service handles the actual execution of tools on behalf of agents:
1. Validates input arguments against the tool's JSON schema
2. Renders request templates using Jinja2
3. Exchanges agent token for upstream service token
4. Executes the HTTP request with circuit breaker protection
5. Handles both synchronous and asynchronous (polling) execution modes

Key Features:
- Jinja2 template rendering for URL, headers, and body
- JSON Schema validation (configurable per tool)
- Circuit breaker per upstream source
- Comprehensive tracing and metrics
- Request/response logging at DEBUG level with truncation
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, Optional, cast

import httpx
from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError, select_autoescape
from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError
from opentelemetry import trace

from domain.enums import ExecutionMode
from domain.models import ExecutionProfile, PollConfig, ToolDefinition
from infrastructure.adapters.keycloak_token_exchanger import CircuitBreaker, KeycloakTokenExchanger, TokenExchangeError

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Maximum length for logged request/response bodies
MAX_LOG_BODY_LENGTH = 500


class ToolExecutionError(Exception):
    """Error during tool execution.

    This exception provides detailed information about what went wrong
    during tool execution, including upstream error details when available.

    Attributes:
        message: Human-readable error message
        error_code: Categorized error code for client handling
        upstream_status: HTTP status code from upstream (if applicable)
        upstream_body: Response body from upstream (truncated for safety)
        tool_id: ID of the tool that failed
        is_retryable: Whether the error might succeed on retry
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        tool_id: Optional[str] = None,
        upstream_status: Optional[int] = None,
        upstream_body: Optional[str] = None,
        is_retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.tool_id = tool_id
        self.upstream_status = upstream_status
        self.upstream_body = upstream_body
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "tool_id": self.tool_id,
            "upstream_status": self.upstream_status,
            "upstream_body": self.upstream_body,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }


@dataclass
class ToolExecutionResult:
    """Result of a successful tool execution.

    Attributes:
        tool_id: ID of the executed tool
        status: Execution status (completed, pending, failed)
        result: Response data from the upstream service
        execution_time_ms: Total execution time in milliseconds
        upstream_status: HTTP status code from upstream
        metadata: Additional execution metadata
    """

    tool_id: str
    status: str  # "completed", "pending", "failed"
    result: Any
    execution_time_ms: float
    upstream_status: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolExecutor:
    """Executes tools by proxying requests to upstream services.

    This service is the core of Phase 5, responsible for:
    1. Validating tool arguments against JSON schema
    2. Rendering Jinja2 templates for request construction
    3. Exchanging tokens for upstream service access
    4. Executing HTTP requests with resilience patterns
    5. Handling async polling for long-running operations

    Example Usage:
        executor = ToolExecutor(token_exchanger=exchanger)
        result = await executor.execute(
            tool_id="source123:get_users",
            definition=tool_definition,
            arguments={"page": 1, "limit": 10},
            agent_token="eyJ...",
        )
    """

    def __init__(
        self,
        token_exchanger: KeycloakTokenExchanger,
        default_timeout: float = 30.0,
        max_poll_attempts: int = 60,
        enable_schema_validation: bool = True,
        on_circuit_state_change: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """Initialize the tool executor.

        Args:
            token_exchanger: Service for exchanging agent tokens
            default_timeout: Default HTTP timeout in seconds
            max_poll_attempts: Maximum polling attempts for async tools
            enable_schema_validation: Global toggle for input validation
            on_circuit_state_change: Optional callback for circuit breaker events
        """
        self._token_exchanger = token_exchanger
        self._default_timeout = default_timeout
        self._max_poll_attempts = max_poll_attempts
        self._enable_schema_validation = enable_schema_validation
        self._on_circuit_state_change = on_circuit_state_change

        # Jinja2 environment for template rendering
        # Using select_autoescape with empty list since we're generating URLs/JSON, not HTML
        self._jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(default_for_string=False, default=False),
        )

        # Circuit breakers per source (keyed by source_id or base URL)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        logger.info(f"ToolExecutor initialized: timeout={default_timeout}s, " f"validation={'enabled' if enable_schema_validation else 'disabled'}")

    async def execute(
        self,
        tool_id: str,
        definition: ToolDefinition,
        arguments: Dict[str, Any],
        agent_token: str,
        source_id: Optional[str] = None,
        validate_schema: Optional[bool] = None,
    ) -> ToolExecutionResult:
        """Execute a tool with the given arguments.

        Args:
            tool_id: Unique identifier for the tool
            definition: Tool definition with execution profile
            arguments: Arguments to pass to the tool
            agent_token: Agent's access token for token exchange
            source_id: Optional source ID for circuit breaker grouping
            validate_schema: Override global schema validation setting

        Returns:
            ToolExecutionResult with the tool's response

        Raises:
            ToolExecutionError: If execution fails
        """
        start_time = time.time()

        with tracer.start_as_current_span("execute_tool") as span:
            span.set_attribute("tool.id", tool_id)
            span.set_attribute("tool.name", definition.name)
            span.set_attribute("tool.source_path", definition.source_path)
            span.set_attribute("tool.execution_mode", definition.execution_profile.mode.value)

            try:
                # Step 1: Validate arguments
                should_validate = validate_schema if validate_schema is not None else self._enable_schema_validation
                if should_validate:
                    span.add_event("Validating arguments")
                    self._validate_arguments(tool_id, definition.input_schema, arguments)

                # Step 2: Exchange token for upstream access
                span.add_event("Exchanging token")
                upstream_token = await self._exchange_token(
                    agent_token=agent_token,
                    execution_profile=definition.execution_profile,
                )

                # Step 3: Execute based on mode
                profile = definition.execution_profile
                if profile.mode == ExecutionMode.SYNC_HTTP:
                    span.add_event("Executing sync HTTP request")
                    result = await self._execute_sync(
                        tool_id=tool_id,
                        profile=profile,
                        arguments=arguments,
                        upstream_token=upstream_token,
                        source_id=source_id,
                    )
                elif profile.mode == ExecutionMode.ASYNC_POLL:
                    span.add_event("Executing async poll request")
                    result = await self._execute_async_poll(
                        tool_id=tool_id,
                        profile=profile,
                        arguments=arguments,
                        upstream_token=upstream_token,
                        source_id=source_id,
                    )
                else:
                    raise ToolExecutionError(
                        message=f"Unsupported execution mode: {profile.mode}",
                        error_code="unsupported_mode",
                        tool_id=tool_id,
                    )

                execution_time_ms = (time.time() - start_time) * 1000
                span.set_attribute("tool.execution_time_ms", execution_time_ms)
                span.set_attribute("tool.status", result.status)

                result.execution_time_ms = execution_time_ms
                return result

            except ToolExecutionError:
                raise
            except TokenExchangeError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                span.set_attribute("tool.error", str(e))
                raise ToolExecutionError(
                    message=f"Token exchange failed: {e.message}",
                    error_code="token_exchange_failed",
                    tool_id=tool_id,
                    is_retryable=e.is_retryable,
                    details={"exchange_error": e.error_code},
                )
            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                span.set_attribute("tool.error", str(e))
                logger.exception(f"Unexpected error executing tool {tool_id}")
                raise ToolExecutionError(
                    message=f"Unexpected error: {e}",
                    error_code="internal_error",
                    tool_id=tool_id,
                    is_retryable=False,
                )

    def _validate_arguments(
        self,
        tool_id: str,
        schema: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> None:
        """Validate arguments against JSON schema.

        Args:
            tool_id: Tool ID for error context
            schema: JSON Schema to validate against
            arguments: Arguments to validate

        Raises:
            ToolExecutionError: If validation fails
        """
        if not schema:
            return

        try:
            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(arguments))
            if errors:
                # Collect all validation errors
                error_messages = []
                for error in errors[:5]:  # Limit to first 5 errors
                    path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                    error_messages.append(f"{path}: {error.message}")

                raise ToolExecutionError(
                    message=f"Argument validation failed: {'; '.join(error_messages)}",
                    error_code="validation_error",
                    tool_id=tool_id,
                    details={"validation_errors": error_messages},
                )
        except JsonSchemaValidationError as e:
            raise ToolExecutionError(
                message=f"Invalid argument schema: {e.message}",
                error_code="validation_error",
                tool_id=tool_id,
            )

    async def _exchange_token(
        self,
        agent_token: str,
        execution_profile: ExecutionProfile,
    ) -> str:
        """Exchange agent token for upstream service token.

        Args:
            agent_token: Agent's access token
            execution_profile: Execution profile with audience info

        Returns:
            Access token for the upstream service

        Raises:
            TokenExchangeError: If exchange fails
        """
        audience = execution_profile.required_audience
        if not audience:
            # No token exchange needed - use agent token directly
            logger.debug("No audience specified, using agent token directly")
            return agent_token

        scopes = execution_profile.required_scopes if execution_profile.required_scopes else None
        result = await self._token_exchanger.exchange_token(
            subject_token=agent_token,
            audience=audience,
            requested_scopes=scopes,
        )
        return result.access_token

    async def _execute_sync(
        self,
        tool_id: str,
        profile: ExecutionProfile,
        arguments: Dict[str, Any],
        upstream_token: str,
        source_id: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Execute a synchronous HTTP request.

        Args:
            tool_id: Tool identifier
            profile: Execution profile with URL/header templates
            arguments: Template arguments
            upstream_token: Token for upstream authentication
            source_id: Source ID for circuit breaker grouping

        Returns:
            ToolExecutionResult with response data
        """
        # Render request components
        url = self._render_template(profile.url_template, arguments, "url")
        headers = self._render_headers(profile.headers_template, arguments, upstream_token)
        body = self._render_body(profile.body_template, arguments) if profile.body_template else None

        # Get circuit breaker for this source
        circuit = self._get_circuit_breaker(source_id or url)

        # Log request (DEBUG level, truncated)
        self._log_request(profile.method, url, headers, body)

        try:
            response = cast(
                httpx.Response,
                await circuit.call(
                    self._do_http_request,
                    method=profile.method,
                    url=url,
                    headers=headers,
                    body=body,
                    content_type=profile.content_type,
                    timeout=profile.timeout_seconds or self._default_timeout,
                ),
            )

            # Log response (DEBUG level, truncated)
            self._log_response(response.status_code, response.text)

            # Parse response
            result_data = self._parse_response(response, profile.response_mapping)

            # Determine status based on HTTP code
            if 200 <= response.status_code < 300:
                status = "completed"
            elif 400 <= response.status_code < 500:
                status = "failed"
            else:
                status = "failed"

            return ToolExecutionResult(
                tool_id=tool_id,
                status=status,
                result=result_data,
                execution_time_ms=0,  # Will be set by caller
                upstream_status=response.status_code,
            )

        except TokenExchangeError:
            raise
        except httpx.TimeoutException:
            raise ToolExecutionError(
                message=f"Upstream request timed out after {profile.timeout_seconds}s",
                error_code="upstream_timeout",
                tool_id=tool_id,
                is_retryable=True,
            )
        except httpx.RequestError as e:
            raise ToolExecutionError(
                message=f"Upstream request failed: {e}",
                error_code="upstream_connection_error",
                tool_id=tool_id,
                is_retryable=True,
            )

    async def _execute_async_poll(
        self,
        tool_id: str,
        profile: ExecutionProfile,
        arguments: Dict[str, Any],
        upstream_token: str,
        source_id: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Execute an async request with polling for completion.

        Args:
            tool_id: Tool identifier
            profile: Execution profile with polling configuration
            arguments: Template arguments
            upstream_token: Token for upstream authentication
            source_id: Source ID for circuit breaker grouping

        Returns:
            ToolExecutionResult with final response data
        """
        poll_config = profile.poll_config
        if not poll_config:
            raise ToolExecutionError(
                message="Async poll execution requires poll_config",
                error_code="missing_poll_config",
                tool_id=tool_id,
            )

        # Step 1: Trigger the async operation
        trigger_result = await self._execute_sync(
            tool_id=tool_id,
            profile=profile,
            arguments=arguments,
            upstream_token=upstream_token,
            source_id=source_id,
        )

        # Extract job ID or status URL from trigger response
        if trigger_result.status == "failed":
            return trigger_result

        # Step 2: Poll for completion
        return await self._poll_for_completion(
            tool_id=tool_id,
            poll_config=poll_config,
            trigger_result=trigger_result.result,
            arguments=arguments,
            upstream_token=upstream_token,
            source_id=source_id,
        )

    async def _poll_for_completion(
        self,
        tool_id: str,
        poll_config: PollConfig,
        trigger_result: Any,
        arguments: Dict[str, Any],
        upstream_token: str,
        source_id: Optional[str] = None,
    ) -> ToolExecutionResult:
        """Poll for async operation completion.

        Args:
            tool_id: Tool identifier
            poll_config: Polling configuration
            trigger_result: Result from the initial trigger request
            arguments: Original arguments (may contain job_id from response)
            upstream_token: Token for upstream authentication
            source_id: Source ID for circuit breaker grouping

        Returns:
            ToolExecutionResult with final response
        """
        # Merge trigger result into arguments for status URL templating
        poll_args = {**arguments}
        if isinstance(trigger_result, dict):
            poll_args.update(trigger_result)

        interval = poll_config.poll_interval_seconds
        max_interval = poll_config.max_interval_seconds
        backoff = poll_config.backoff_multiplier

        circuit = self._get_circuit_breaker(source_id or "poll")

        for attempt in range(poll_config.max_poll_attempts):
            # Wait before polling (except first attempt)
            if attempt > 0:
                await asyncio.sleep(interval)
                interval = min(interval * backoff, max_interval)

            # Render status URL
            status_url = self._render_template(
                poll_config.status_url_template,
                poll_args,
                "status_url",
            )

            # Make status request
            try:
                response = cast(
                    httpx.Response,
                    await circuit.call(
                        self._do_http_request,
                        method="GET",
                        url=status_url,
                        headers={"Authorization": f"Bearer {upstream_token}"},
                        body=None,
                        content_type="application/json",
                        timeout=self._default_timeout,
                    ),
                )

                if response.status_code != 200:
                    logger.warning(f"Poll status request returned {response.status_code}")
                    continue

                status_data = response.json()

                # Extract status value
                status_value = self._extract_json_path(
                    status_data,
                    poll_config.status_field_path,
                )

                if status_value in poll_config.completed_values:
                    # Success - extract result
                    result_data = self._extract_json_path(
                        status_data,
                        poll_config.result_field_path,
                    )
                    return ToolExecutionResult(
                        tool_id=tool_id,
                        status="completed",
                        result=result_data,
                        execution_time_ms=0,
                        upstream_status=200,
                        metadata={"poll_attempts": attempt + 1},
                    )

                if status_value in poll_config.failed_values:
                    # Operation failed
                    return ToolExecutionResult(
                        tool_id=tool_id,
                        status="failed",
                        result=status_data,
                        execution_time_ms=0,
                        upstream_status=200,
                        metadata={"poll_attempts": attempt + 1},
                    )

                # Still pending, continue polling
                logger.debug(f"Poll attempt {attempt + 1}: status={status_value}")

            except Exception as e:
                logger.warning(f"Poll attempt {attempt + 1} failed: {e}")
                continue

        # Max attempts reached
        raise ToolExecutionError(
            message=f"Async operation did not complete within {poll_config.max_poll_attempts} attempts",
            error_code="poll_timeout",
            tool_id=tool_id,
            is_retryable=True,
            details={"max_attempts": poll_config.max_poll_attempts},
        )

    async def _do_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        content_type: str,
        timeout: float,
    ) -> httpx.Response:
        """Execute an HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body (JSON string or None)
            content_type: Content-Type header value
            timeout: Request timeout in seconds

        Returns:
            httpx.Response object
        """
        headers["Content-Type"] = content_type

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body.encode() if body else None,
            )
            return response

    def _render_template(
        self,
        template: str,
        arguments: Dict[str, Any],
        context: str,
    ) -> str:
        """Render a Jinja2 template with arguments.

        Args:
            template: Jinja2 template string
            arguments: Template variables
            context: Context name for error messages

        Returns:
            Rendered string

        Raises:
            ToolExecutionError: If template rendering fails
        """
        try:
            jinja_template = self._jinja_env.from_string(template)
            return jinja_template.render(**arguments)
        except TemplateSyntaxError as e:
            raise ToolExecutionError(
                message=f"Invalid {context} template syntax: {e}",
                error_code="template_error",
            )
        except UndefinedError as e:
            raise ToolExecutionError(
                message=f"Missing variable in {context} template: {e}",
                error_code="template_error",
                details={"template": template, "available_args": list(arguments.keys())},
            )

    def _render_headers(
        self,
        headers_template: Dict[str, str],
        arguments: Dict[str, Any],
        upstream_token: str,
    ) -> Dict[str, str]:
        """Render header templates and add authorization.

        Args:
            headers_template: Dict of header templates
            arguments: Template variables
            upstream_token: Bearer token for Authorization header

        Returns:
            Dict of rendered headers
        """
        headers = {"Authorization": f"Bearer {upstream_token}"}

        for key, template in headers_template.items():
            if key.lower() != "authorization":  # Don't override our token
                headers[key] = self._render_template(template, arguments, f"header:{key}")

        return headers

    def _render_body(
        self,
        body_template: str,
        arguments: Dict[str, Any],
    ) -> str:
        """Render body template.

        Args:
            body_template: Jinja2 template for request body
            arguments: Template variables

        Returns:
            Rendered body string (JSON)
        """
        rendered = self._render_template(body_template, arguments, "body")

        # If the template produces JSON, validate it
        try:
            json.loads(rendered)
        except json.JSONDecodeError:
            # Not valid JSON - might be intentional for non-JSON content types
            pass

        return rendered

    def _parse_response(
        self,
        response: httpx.Response,
        response_mapping: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Parse HTTP response and optionally apply JSONPath mappings.

        Args:
            response: HTTP response object
            response_mapping: Optional dict of output_field -> JSONPath

        Returns:
            Parsed response data
        """
        # Try to parse as JSON
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            # Return raw text for non-JSON responses
            return response.text

        # Apply response mappings if specified
        if response_mapping:
            mapped = {}
            for output_field, json_path in response_mapping.items():
                mapped[output_field] = self._extract_json_path(data, json_path)
            return mapped

        return data

    def _extract_json_path(
        self,
        data: Any,
        path: str,
    ) -> Any:
        """Extract a value from nested data using dot notation path.

        Args:
            data: Data to extract from
            path: Dot notation path (e.g., "result.data.items")

        Returns:
            Extracted value or None if path not found
        """
        parts = path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current

    def _get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a source/URL.

        Args:
            key: Unique key for the circuit breaker (source_id or base URL)

        Returns:
            CircuitBreaker instance
        """
        if key not in self._circuit_breakers:
            self._circuit_breakers[key] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=30.0,
                circuit_id=f"source:{key}",
                circuit_type="tool_execution",
                source_id=key,
                on_state_change=self._on_circuit_state_change,
            )
        return self._circuit_breakers[key]

    def _log_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
    ) -> None:
        """Log request details at DEBUG level with truncation.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers (Authorization header will be masked)
            body: Request body
        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        # Mask authorization header
        safe_headers = {k: ("Bearer ***" if k.lower() == "authorization" else v) for k, v in headers.items()}

        # Truncate body
        truncated_body = None
        if body:
            truncated_body = body[:MAX_LOG_BODY_LENGTH]
            if len(body) > MAX_LOG_BODY_LENGTH:
                truncated_body += f"... ({len(body)} bytes total)"

        logger.debug(f"Upstream request: {method} {url}\n" f"Headers: {safe_headers}\n" f"Body: {truncated_body}")

    def _log_response(
        self,
        status_code: int,
        body: str,
    ) -> None:
        """Log response details at DEBUG level with truncation.

        Args:
            status_code: HTTP status code
            body: Response body
        """
        if not logger.isEnabledFor(logging.DEBUG):
            return

        truncated_body = body[:MAX_LOG_BODY_LENGTH]
        if len(body) > MAX_LOG_BODY_LENGTH:
            truncated_body += f"... ({len(body)} bytes total)"

        logger.debug(f"Upstream response: {status_code}\nBody: {truncated_body}")

    def get_circuit_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all circuit breaker states for monitoring.

        Returns:
            Dict mapping source keys to circuit breaker states
        """
        return {key: cb.get_state() for key, cb in self._circuit_breakers.items()}

    async def reset_circuit_breaker(self, key: str, reset_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Reset a specific circuit breaker to closed state.

        Args:
            key: The source key (source_id or URL) for the circuit breaker
            reset_by: Username of admin who triggered the reset

        Returns:
            The new circuit breaker state, or None if not found
        """
        if key in self._circuit_breakers:
            await self._circuit_breakers[key].reset(manual=True, reset_by=reset_by)
            return self._circuit_breakers[key].get_state()
        return None

    async def reset_all_circuit_breakers(self, reset_by: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Reset all circuit breakers to closed state.

        Args:
            reset_by: Username of admin who triggered the reset

        Returns:
            Dict mapping source keys to their new circuit breaker states
        """
        results = {}
        for key, cb in self._circuit_breakers.items():
            await cb.reset(manual=True, reset_by=reset_by)
            results[key] = cb.get_state()
        return results

    # =========================================================================
    # Service Configuration (Neuroglia Pattern)
    # =========================================================================

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure and register the tool executor service.

        This method follows the Neuroglia pattern for service configuration,
        creating a singleton instance and registering it in the DI container.

        Resolves KeycloakTokenExchanger and CircuitBreakerEventPublisher from the DI container.

        Args:
            builder: WebApplicationBuilder instance for service registration

        Returns:
            The builder instance for fluent chaining

        Raises:
            RuntimeError: If KeycloakTokenExchanger is not registered
        """
        from application.settings import app_settings
        from infrastructure.services import CircuitBreakerEventPublisher

        log = logging.getLogger(__name__)
        log.info("🔧 Configuring ToolExecutor...")

        # Resolve required token exchanger from registered singletons
        token_exchanger: Optional[KeycloakTokenExchanger] = None
        for desc in builder.services:
            if desc.service_type == KeycloakTokenExchanger and desc.singleton is not None:
                token_exchanger = desc.singleton
                break

        if token_exchanger is None:
            raise RuntimeError("KeycloakTokenExchanger not found in DI container. " "Ensure KeycloakTokenExchanger.configure(builder) is called before ToolExecutor.configure(builder)")

        # Resolve optional circuit breaker event publisher
        event_publisher: Optional[CircuitBreakerEventPublisher] = None
        for desc in builder.services:
            if desc.service_type == CircuitBreakerEventPublisher and desc.singleton is not None:
                event_publisher = desc.singleton
                break

        on_circuit_state_change = event_publisher.publish_event if event_publisher else None

        tool_executor = ToolExecutor(
            token_exchanger=token_exchanger,
            default_timeout=app_settings.tool_execution_timeout,
            max_poll_attempts=app_settings.tool_execution_max_poll_attempts,
            enable_schema_validation=app_settings.tool_execution_validate_schema,
            on_circuit_state_change=on_circuit_state_change,
        )
        builder.services.add_singleton(ToolExecutor, singleton=tool_executor)
        log.info("✅ ToolExecutor configured")

        return builder
