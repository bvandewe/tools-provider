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
import base64
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import httpx
import jwt
from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError, select_autoescape
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError
from opentelemetry import trace

from domain.enums import AuthMode, ExecutionMode
from domain.models import AuthConfig, ExecutionProfile, PollConfig, ToolDefinition
from infrastructure.adapters.keycloak_token_exchanger import CircuitBreaker, KeycloakTokenExchanger, TokenExchangeError
from infrastructure.adapters.oauth2_client import ClientCredentialsError, OAuth2ClientCredentialsService

from .builtin_source_adapter import is_builtin_tool_url
from .builtin_tool_executor import BuiltinToolExecutor, UserContext

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
        tool_id: str | None = None,
        upstream_status: int | None = None,
        upstream_body: str | None = None,
        is_retryable: bool = False,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.tool_id = tool_id
        self.upstream_status = upstream_status
        self.upstream_body = upstream_body
        self.is_retryable = is_retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
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
    upstream_status: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
        client_credentials_service: OAuth2ClientCredentialsService | None = None,
        default_timeout: float = 30.0,
        max_poll_attempts: int = 60,
        enable_schema_validation: bool = True,
        on_circuit_state_change: Callable[[Any], Awaitable[None]] | None = None,
    ):
        """Initialize the tool executor.

        Args:
            token_exchanger: Service for exchanging agent tokens (Level 3 auth)
            client_credentials_service: Service for client credentials tokens (Level 2 auth)
            default_timeout: Default HTTP timeout in seconds
            max_poll_attempts: Maximum polling attempts for async tools
            enable_schema_validation: Global toggle for input validation
            on_circuit_state_change: Optional callback for circuit breaker events
        """
        self._token_exchanger = token_exchanger
        self._client_credentials_service = client_credentials_service
        self._default_timeout = default_timeout
        self._max_poll_attempts = max_poll_attempts
        self._enable_schema_validation = enable_schema_validation
        self._on_circuit_state_change = on_circuit_state_change

        # Built-in tool executor for local tool execution
        self._builtin_executor = BuiltinToolExecutor()

        # Jinja2 environment for template rendering
        # Using select_autoescape with empty list since we're generating URLs/JSON, not HTML
        self._jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(default_for_string=False, default=False),
        )

        # Circuit breakers per source (keyed by source_id or base URL)
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        logger.info(f"ToolExecutor initialized: timeout={default_timeout}s, validation={'enabled' if enable_schema_validation else 'disabled'}")

    def _extract_user_context(self, agent_token: str) -> UserContext | None:
        """Extract user context from JWT token for scoped operations.

        Decodes the JWT without verification to extract user identity claims.
        This is safe because the token has already been verified at the API layer.

        Args:
            agent_token: JWT access token from the agent

        Returns:
            UserContext with user_id and username, or None if extraction fails
        """
        try:
            # Decode without verification - token was already verified at API layer
            claims = jwt.decode(agent_token, options={"verify_signature": False})
            user_id = claims.get("sub")  # Subject claim is the unique user ID
            username = claims.get("preferred_username") or claims.get("email") or claims.get("name")

            if user_id:
                return UserContext(user_id=user_id, username=username)
            return None
        except Exception as e:
            logger.warning(f"Failed to extract user context from token: {e}")
            return None

    async def execute(
        self,
        tool_id: str,
        definition: ToolDefinition,
        arguments: dict[str, Any],
        agent_token: str,
        source_id: str | None = None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        auth_config: AuthConfig | None = None,
        default_audience: str | None = None,
        validate_schema: bool | None = None,
    ) -> ToolExecutionResult:
        """Execute a tool with the given arguments.

        Args:
            tool_id: Unique identifier for the tool
            definition: Tool definition with execution profile
            arguments: Arguments to pass to the tool
            agent_token: Agent's access token for token exchange
            source_id: Optional source ID for circuit breaker grouping
            auth_mode: Authentication mode for upstream requests
            auth_config: Optional auth config for API key or source-specific OAuth2
            default_audience: Target audience for token exchange (Level 3)
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
            span.set_attribute("tool.auth_mode", auth_mode.value)

            try:
                # Step 1: Validate arguments
                should_validate = validate_schema if validate_schema is not None else self._enable_schema_validation
                if should_validate:
                    span.add_event("Validating arguments")
                    self._validate_arguments(tool_id, definition.input_schema, arguments)

                # Step 1.5: Check if this is a built-in tool (executes locally)
                profile = definition.execution_profile
                if is_builtin_tool_url(profile.url_template):
                    span.add_event("Executing built-in tool locally")
                    # Extract user context from agent token for scoped operations
                    user_context = self._extract_user_context(agent_token)
                    result = await self._execute_builtin(
                        tool_id=tool_id,
                        definition=definition,
                        arguments=arguments,
                        user_context=user_context,
                    )
                    execution_time_ms = (time.time() - start_time) * 1000
                    span.set_attribute("tool.execution_time_ms", execution_time_ms)
                    span.set_attribute("tool.status", result.status)
                    result.execution_time_ms = execution_time_ms
                    return result

                # Step 2: Get upstream token based on auth mode
                span.add_event("Getting upstream token", {"auth_mode": auth_mode.value})
                upstream_token = await self._get_upstream_token(
                    agent_token=agent_token,
                    auth_mode=auth_mode,
                    auth_config=auth_config,
                    default_audience=default_audience,
                )

                # Step 3: Execute based on mode
                if profile.mode == ExecutionMode.SYNC_HTTP:
                    span.add_event("Executing sync HTTP request")
                    result = await self._execute_sync(
                        tool_id=tool_id,
                        profile=profile,
                        arguments=arguments,
                        upstream_token=upstream_token,
                        auth_mode=auth_mode,
                        auth_config=auth_config,
                        source_id=source_id,
                    )
                elif profile.mode == ExecutionMode.ASYNC_POLL:
                    span.add_event("Executing async poll request")
                    result = await self._execute_async_poll(
                        tool_id=tool_id,
                        profile=profile,
                        arguments=arguments,
                        upstream_token=upstream_token,
                        auth_mode=auth_mode,
                        auth_config=auth_config,
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
            except ClientCredentialsError as e:
                execution_time_ms = (time.time() - start_time) * 1000
                span.set_attribute("tool.error", str(e))
                raise ToolExecutionError(
                    message=f"Client credentials authentication failed: {e.message}",
                    error_code="client_credentials_failed",
                    tool_id=tool_id,
                    is_retryable=False,
                    details={"error_code": e.error_code},
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
        schema: dict[str, Any],
        arguments: dict[str, Any],
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

        DEPRECATED: Use _get_upstream_token() instead for multi-mode auth support.

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

    async def _get_upstream_token(
        self,
        agent_token: str,
        auth_mode: AuthMode,
        auth_config: AuthConfig | None,
        default_audience: str | None,
    ) -> str | None:
        """Get token for upstream service based on auth_mode.

        Args:
            agent_token: Agent's access token (used for token exchange)
            auth_mode: Authentication mode for the upstream service
            auth_config: Optional auth config for source-specific credentials
            default_audience: Target audience for token exchange

        Returns:
            Access token string, or None for auth modes that don't use tokens

        Raises:
            TokenExchangeError: If token exchange fails
            ClientCredentialsError: If client credentials acquisition fails
            ValueError: If client_credentials mode is used but service not configured
        """
        if auth_mode == AuthMode.NONE:
            logger.debug("Auth mode NONE - no token needed")
            return None

        elif auth_mode == AuthMode.API_KEY:
            # API key is handled in _render_headers, not as a bearer token
            logger.debug("Auth mode API_KEY - token handled in headers")
            return None

        elif auth_mode == AuthMode.HTTP_BASIC:
            # HTTP Basic auth is handled in _render_headers, not as a bearer token
            logger.debug("Auth mode HTTP_BASIC - credentials handled in headers")
            return None

        elif auth_mode == AuthMode.CLIENT_CREDENTIALS:
            # OAuth2 client credentials grant
            if not self._client_credentials_service:
                raise ValueError("Client credentials auth mode requires OAuth2ClientCredentialsService to be configured")

            if auth_config and auth_config.oauth2_client_id:
                # Source-specific credentials (Variant B)
                logger.debug(f"Auth mode CLIENT_CREDENTIALS - using source-specific credentials for {auth_config.oauth2_client_id}")
                return await self._client_credentials_service.get_token(
                    token_url=auth_config.oauth2_token_url,
                    client_id=auth_config.oauth2_client_id,
                    client_secret=auth_config.oauth2_client_secret,
                    scopes=auth_config.oauth2_scopes if auth_config.oauth2_scopes else None,
                )
            else:
                # Tools Provider's service account (Variant A)
                logger.debug("Auth mode CLIENT_CREDENTIALS - using Tools Provider service account")
                return await self._client_credentials_service.get_token()

        elif auth_mode == AuthMode.TOKEN_EXCHANGE:
            # RFC 8693 token exchange
            if not default_audience:
                # No audience specified - pass through agent token
                logger.debug("Auth mode TOKEN_EXCHANGE - no audience, passing agent token")
                return agent_token

            logger.debug(f"Auth mode TOKEN_EXCHANGE - exchanging token for audience {default_audience}")
            result = await self._token_exchanger.exchange_token(
                subject_token=agent_token,
                audience=default_audience,
            )
            return result.access_token

        else:
            logger.warning(f"Unknown auth mode: {auth_mode}")
            return agent_token

    async def _execute_sync(
        self,
        tool_id: str,
        profile: ExecutionProfile,
        arguments: dict[str, Any],
        upstream_token: str | None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        auth_config: AuthConfig | None = None,
        source_id: str | None = None,
    ) -> ToolExecutionResult:
        """Execute a synchronous HTTP request.

        Args:
            tool_id: Tool identifier
            profile: Execution profile with URL/header templates
            arguments: Template arguments
            upstream_token: Token for upstream authentication (may be None for NONE/API_KEY modes)
            auth_mode: Authentication mode
            auth_config: Optional auth config for API key
            source_id: Source ID for circuit breaker grouping

        Returns:
            ToolExecutionResult with response data
        """
        # Render request components
        url = self._render_template(profile.url_template, arguments, "url")
        headers = self._render_headers(profile.headers_template, arguments, upstream_token, auth_mode, auth_config)
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

    async def _execute_builtin(
        self,
        tool_id: str,
        definition: ToolDefinition,
        arguments: dict[str, Any],
        user_context: UserContext | None = None,
    ) -> ToolExecutionResult:
        """Execute a built-in tool locally.

        Built-in tools are executed in-process without HTTP proxying.
        They are registered via the BuiltinSourceAdapter.

        Args:
            tool_id: Tool identifier
            definition: Tool definition
            arguments: Tool arguments
            user_context: Optional user context for scoping operations

        Returns:
            ToolExecutionResult with execution outcome
        """
        logger.info(f"Executing built-in tool: {definition.name}")

        try:
            result = await self._builtin_executor.execute(
                tool_name=definition.name,
                arguments=arguments,
                user_context=user_context,
            )

            if result.success:
                return ToolExecutionResult(
                    tool_id=tool_id,
                    status="completed",
                    result=result.result,
                    execution_time_ms=0,  # Will be set by caller
                    upstream_status=None,
                    metadata=result.metadata,
                )
            else:
                return ToolExecutionResult(
                    tool_id=tool_id,
                    status="failed",
                    result={"error": result.error},
                    execution_time_ms=0,
                    upstream_status=None,
                    metadata=result.metadata,
                )

        except Exception as e:
            logger.exception(f"Built-in tool execution failed: {definition.name}")
            raise ToolExecutionError(
                message=f"Built-in tool execution failed: {str(e)}",
                error_code="builtin_execution_error",
                tool_id=tool_id,
                is_retryable=False,
            )

    async def _execute_async_poll(
        self,
        tool_id: str,
        profile: ExecutionProfile,
        arguments: dict[str, Any],
        upstream_token: str | None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        auth_config: AuthConfig | None = None,
        source_id: str | None = None,
    ) -> ToolExecutionResult:
        """Execute an async request with polling for completion.

        Args:
            tool_id: Tool identifier
            profile: Execution profile with polling configuration
            arguments: Template arguments
            upstream_token: Token for upstream authentication (may be None for NONE/API_KEY modes)
            auth_mode: Authentication mode
            auth_config: Optional auth config for API key
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
            auth_mode=auth_mode,
            auth_config=auth_config,
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
            auth_mode=auth_mode,
            auth_config=auth_config,
            source_id=source_id,
        )

    async def _poll_for_completion(
        self,
        tool_id: str,
        poll_config: PollConfig,
        trigger_result: Any,
        arguments: dict[str, Any],
        upstream_token: str | None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        auth_config: AuthConfig | None = None,
        source_id: str | None = None,
    ) -> ToolExecutionResult:
        """Poll for async operation completion.

        Args:
            tool_id: Tool identifier
            poll_config: Polling configuration
            trigger_result: Result from the initial trigger request
            arguments: Original arguments (may contain job_id from response)
            upstream_token: Token for upstream authentication (may be None)
            auth_mode: Authentication mode
            auth_config: Optional auth config for API key
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

        # Prepare headers for polling requests
        poll_headers = self._render_headers({}, poll_args, upstream_token, auth_mode, auth_config)

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
                        headers=poll_headers,
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
        headers: dict[str, str],
        body: str | None,
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
        arguments: dict[str, Any],
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
        headers_template: dict[str, str],
        arguments: dict[str, Any],
        upstream_token: str | None,
        auth_mode: AuthMode = AuthMode.TOKEN_EXCHANGE,
        auth_config: AuthConfig | None = None,
    ) -> dict[str, str]:
        """Render header templates and add authorization based on auth mode.

        Args:
            headers_template: Dict of header templates
            arguments: Template variables
            upstream_token: Bearer token (None for NONE/API_KEY modes)
            auth_mode: Authentication mode
            auth_config: Optional auth config for API key

        Returns:
            Dict of rendered headers
        """
        headers: dict[str, str] = {}

        # Add authentication based on mode
        if auth_mode == AuthMode.NONE:
            # No authentication header
            logger.debug("_render_headers: auth_mode=NONE, no auth header added")

        elif auth_mode == AuthMode.API_KEY and auth_config:
            # Static API key
            if auth_config.api_key_in == "header" and auth_config.api_key_name and auth_config.api_key_value:  # pragma: allowlist secret
                headers[auth_config.api_key_name] = auth_config.api_key_value  # pragma: allowlist secret
                logger.debug(f"_render_headers: auth_mode=API_KEY, added header {auth_config.api_key_name}")
            # Query params are handled in URL rendering, not headers

        elif auth_mode == AuthMode.HTTP_BASIC and auth_config:
            # HTTP Basic authentication (RFC 7617)
            if auth_config.basic_username and auth_config.basic_password:
                credentials = f"{auth_config.basic_username}:{auth_config.basic_password}"
                encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
                headers["Authorization"] = f"Basic {encoded}"  # pragma: allowlist secret
                logger.debug(f"_render_headers: auth_mode=HTTP_BASIC, added Basic auth for user={auth_config.basic_username}")
            else:
                logger.warning("_render_headers: auth_mode=HTTP_BASIC but missing username or password in auth_config")

        elif auth_mode == AuthMode.HTTP_BASIC and not auth_config:
            # HTTP Basic requested but no credentials available
            logger.warning("_render_headers: auth_mode=HTTP_BASIC but auth_config is None - no credentials loaded from secrets store")

        elif auth_mode in (AuthMode.CLIENT_CREDENTIALS, AuthMode.TOKEN_EXCHANGE):  # pragma: allowlist secret
            # Bearer token authentication
            if upstream_token:
                headers["Authorization"] = f"Bearer {upstream_token}"
                logger.debug(f"_render_headers: auth_mode={auth_mode.value}, added Bearer token")

        # Render template headers
        for key, template in headers_template.items():
            key_lower = key.lower()
            # Don't override authentication headers we've already set
            if key_lower == "authorization" and "Authorization" in headers:
                continue
            if auth_config and auth_config.api_key_name and key_lower == auth_config.api_key_name.lower():
                continue
            headers[key] = self._render_template(template, arguments, f"header:{key}")

        return headers

    def _render_body(
        self,
        body_template: str,
        arguments: dict[str, Any],
    ) -> str:
        """Render body template.

        Args:
            body_template: Jinja2 template for request body
            arguments: Template variables

        Returns:
            Rendered body string (JSON)

        Raises:
            ToolExecutionError: If template rendering fails or produces invalid JSON
        """
        try:
            rendered = self._render_template(body_template, arguments, "body")
        except ToolExecutionError:
            raise
        except TypeError as e:
            # Handle cases where Jinja2 Undefined values get passed to filters like tojson
            # This can happen if body_template references variables not in arguments
            raise ToolExecutionError(
                message=f"Body template rendering failed - missing required arguments: {e}",
                error_code="template_error",
                details={
                    "template": body_template[:200] + "..." if len(body_template) > 200 else body_template,
                    "available_args": list(arguments.keys()),
                },
            )

        # If the template produces JSON, validate it
        try:
            json.loads(rendered)
        except json.JSONDecodeError as e:
            # Log the issue but don't fail - might be intentional for non-JSON content types
            logger.debug(f"Body template produced non-JSON content: {e}")

        return rendered

    def _parse_response(
        self,
        response: httpx.Response,
        response_mapping: dict[str, str] | None = None,
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
        headers: dict[str, str],
        body: str | None,
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

        # Mask authorization header, preserving the auth type (Bearer vs Basic)
        def mask_auth(k: str, v: str) -> str:
            if k.lower() != "authorization":
                return v
            if v.lower().startswith("basic "):
                return "Basic ***"
            elif v.lower().startswith("bearer "):
                return "Bearer ***"
            return "*** (unknown auth type)"

        safe_headers = {k: mask_auth(k, v) for k, v in headers.items()}

        # Truncate body
        truncated_body = None
        if body:
            truncated_body = body[:MAX_LOG_BODY_LENGTH]
            if len(body) > MAX_LOG_BODY_LENGTH:
                truncated_body += f"... ({len(body)} bytes total)"

        logger.debug(f"Upstream request: {method} {url}\nHeaders: {safe_headers}\nBody: {truncated_body}")

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

    def get_circuit_states(self) -> dict[str, dict[str, Any]]:
        """Get all circuit breaker states for monitoring.

        Returns:
            Dict mapping source keys to circuit breaker states
        """
        return {key: cb.get_state() for key, cb in self._circuit_breakers.items()}

    async def reset_circuit_breaker(self, key: str, reset_by: str | None = None) -> dict[str, Any] | None:
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

    async def reset_all_circuit_breakers(self, reset_by: str | None = None) -> dict[str, dict[str, Any]]:
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
        Creates OAuth2ClientCredentialsService if service account is configured.

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
        token_exchanger: KeycloakTokenExchanger | None = None
        for desc in builder.services:
            if desc.service_type == KeycloakTokenExchanger and desc.singleton is not None:
                token_exchanger = desc.singleton
                break

        if token_exchanger is None:
            raise RuntimeError("KeycloakTokenExchanger not found in DI container. Ensure KeycloakTokenExchanger.configure(builder) is called before ToolExecutor.configure(builder)")

        # Resolve optional circuit breaker event publisher
        event_publisher: CircuitBreakerEventPublisher | None = None
        for desc in builder.services:
            if desc.service_type == CircuitBreakerEventPublisher and desc.singleton is not None:
                event_publisher = desc.singleton
                break

        on_circuit_state_change = event_publisher.publish_event if event_publisher else None

        # Always create OAuth2ClientCredentialsService for source-specific OAuth2 credentials
        # Default service account credentials are optional - sources can provide their own
        # Build token URL if not explicitly set (used as default when sources don't specify one)
        token_url = app_settings.service_account_token_url
        if not token_url:
            # Default to Keycloak realm token endpoint
            token_url = f"{app_settings.keycloak_url_internal}/realms/{app_settings.keycloak_realm}/protocol/openid-connect/token"

        client_credentials_service = OAuth2ClientCredentialsService(
            default_token_url=token_url,
            default_client_id=app_settings.service_account_client_id or "",
            default_client_secret=app_settings.service_account_client_secret or "",
            http_timeout=app_settings.token_exchange_timeout,
            cache_buffer_seconds=app_settings.service_account_cache_buffer_seconds,
        )
        builder.services.add_singleton(OAuth2ClientCredentialsService, singleton=client_credentials_service)

        if app_settings.service_account_client_id and app_settings.service_account_client_secret:
            log.info("✅ OAuth2ClientCredentialsService configured with service account for Level 2 auth")
        else:
            log.info("✅ OAuth2ClientCredentialsService configured for source-specific OAuth2 (no service account defaults)")

        tool_executor = ToolExecutor(
            token_exchanger=token_exchanger,
            client_credentials_service=client_credentials_service,
            default_timeout=app_settings.tool_execution_timeout,
            max_poll_attempts=app_settings.tool_execution_max_poll_attempts,
            enable_schema_validation=app_settings.tool_execution_validate_schema,
            on_circuit_state_change=on_circuit_state_change,
        )
        builder.services.add_singleton(ToolExecutor, singleton=tool_executor)
        log.info("✅ ToolExecutor configured")

        return builder
