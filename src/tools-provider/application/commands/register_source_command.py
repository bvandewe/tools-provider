"""Register source command with handler.

This command creates a new UpstreamSource aggregate representing
an external API that provides tools to AI agents.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import CloudEventPublishingOptions
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler, Mediator
from neuroglia.observability.tracing import add_span_attributes
from opentelemetry import trace

from application.commands.refresh_inventory_command import RefreshInventoryCommand
from application.services import get_adapter_for_type
from domain.entities import UpstreamSource
from domain.enums import AuthMode, SourceType
from domain.models import AuthConfig
from integration.models.source_dto import SourceDto

from .command_handler_base import CommandHandlerBase

log = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class RegisterSourceCommand(Command[OperationResult[SourceDto]]):
    """Command to register a new upstream source.

    The command will:
    1. Validate the URL is accessible and contains a valid specification
    2. Create the UpstreamSource aggregate
    3. Automatically refresh the inventory to discover tools
    4. Return the created source DTO with inventory count
    """

    name: str
    """Human-readable name for the source."""

    url: str
    """Base URL of the upstream service (e.g., https://api.example.com)."""

    openapi_url: str | None = None
    """URL to the OpenAPI specification (if different from url). If not provided, url will be used for spec fetching."""

    description: str | None = None
    """Human-readable description of the source."""

    source_type: str = "openapi"
    """Type of source: 'openapi' or 'workflow'."""

    # Optional authentication configuration
    auth_type: str | None = None
    """Authentication type: 'none', 'bearer', 'api_key', 'oauth2'."""

    bearer_token: str | None = None
    """Bearer token for authentication."""

    api_key_name: str | None = None
    """API key header/query name."""

    api_key_value: str | None = None
    """API key value."""

    api_key_in: str | None = None
    """Where to send API key: 'header' or 'query'."""

    oauth2_client_id: str | None = None
    """OAuth2 client ID."""

    oauth2_client_secret: str | None = None
    """OAuth2 client secret."""

    oauth2_token_url: str | None = None
    """OAuth2 token endpoint URL."""

    oauth2_scopes: list[str] | None = None
    """OAuth2 scopes to request."""

    # Token exchange configuration
    default_audience: str | None = None
    """Target audience for token exchange (client_id of upstream service in Keycloak)."""

    # Authentication mode for tool execution
    auth_mode: str = "token_exchange"
    """Authentication mode for tool execution: 'none', 'api_key', 'client_credentials', 'token_exchange'."""

    # Optional validation
    validate_url: bool = True
    """Whether to validate the URL before registration."""

    # Context
    user_info: dict[str, Any] | None = None
    """User information from authentication context."""


class RegisterSourceCommandHandler(
    CommandHandlerBase,
    CommandHandler[RegisterSourceCommand, OperationResult[SourceDto]],
):
    """Handler for registering new upstream sources.

    This handler:
    1. Validates the source URL (if enabled)
    2. Creates the UpstreamSource aggregate
    3. Persists to EventStoreDB via EventSourcingRepository
    4. Returns the source DTO (read model will be updated by projection handler)
    """

    def __init__(
        self,
        mediator: Mediator,
        mapper: Mapper,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
        source_repository: Repository[UpstreamSource, str],
    ):
        super().__init__(
            mediator,
            mapper,
            cloud_event_bus,
            cloud_event_publishing_options,
        )
        self.source_repository = source_repository

    async def handle_async(self, request: RegisterSourceCommand) -> OperationResult[SourceDto]:
        """Handle the register source command."""
        command = request
        start_time = time.time()

        # Determine the URL to use for OpenAPI spec fetching
        # If openapi_url is provided, use it; otherwise fall back to url
        spec_url = command.openapi_url or command.url

        # Add tracing context
        add_span_attributes(
            {
                "source.name": command.name,
                "source.url": command.url,
                "source.openapi_url": command.openapi_url,
                "source.type": command.source_type,
                "source.validate_url": command.validate_url,
            }
        )

        with tracer.start_as_current_span("register_source") as span:
            # Parse source type
            try:
                source_type = SourceType(command.source_type.lower())
            except ValueError:
                log.warning(f"Invalid source type: {command.source_type}")
                return self.bad_request(f"Invalid source type: {command.source_type}. Valid types: openapi, workflow")

            # Parse auth mode
            try:
                auth_mode = AuthMode(command.auth_mode.lower())
            except ValueError:
                log.warning(f"Invalid auth mode: {command.auth_mode}")
                return self.bad_request(f"Invalid auth mode: {command.auth_mode}. Valid modes: none, api_key, client_credentials, token_exchange")

            # Build auth config
            auth_config = self._build_auth_config(command)

            # Validate URL if requested (validate the spec URL, not the base URL)
            if command.validate_url:
                span.add_event("Validating source URL")
                valid = await self._validate_source_url(spec_url, source_type, auth_config)
                if not valid:
                    log.warning(f"URL validation failed for: {spec_url}")
                    return self.bad_request(f"Failed to validate source URL. Ensure the URL points to a valid {source_type.value} specification.")
                span.add_event("URL validation successful")

            # Determine created_by from user context
            created_by = None
            if command.user_info:
                created_by = command.user_info.get("sub") or command.user_info.get("user_id") or command.user_info.get("preferred_username")

            # Create the aggregate
            source = UpstreamSource(
                name=command.name,
                url=command.url,
                source_type=source_type,
                auth_config=auth_config,
                created_by=created_by,
                default_audience=command.default_audience,
                openapi_url=command.openapi_url,
                description=command.description,
                auth_mode=auth_mode,
            )

            span.set_attribute("source.id", source.id())
            span.set_attribute("source.created_by", created_by or "unknown")

            # Persist to EventStoreDB
            saved_source = await self.source_repository.add_async(source)

            # Automatically refresh inventory to discover tools
            span.add_event("Triggering inventory refresh")
            inventory_count = 0
            inventory_hash = ""
            try:
                refresh_command = RefreshInventoryCommand(
                    source_id=saved_source.id(),
                    force=True,
                    user_info=command.user_info,
                )
                refresh_result = await self.mediator.execute_async(refresh_command)
                if refresh_result.is_success and refresh_result.data:
                    inventory_count = refresh_result.data.tools_created
                    inventory_hash = refresh_result.data.new_hash or ""
                    span.add_event(f"Inventory refresh completed: {inventory_count} tools discovered")
                    log.info(f"Source {saved_source.id()}: discovered {inventory_count} tools")
                else:
                    log.warning(f"Inventory refresh failed for source {saved_source.id()}: {refresh_result.error_message}")
                    span.add_event("Inventory refresh failed")
            except Exception as e:
                log.warning(f"Failed to refresh inventory for source {saved_source.id()}: {e}")
                span.add_event(f"Inventory refresh error: {str(e)}")

            # Build DTO response
            dto = SourceDto(
                id=saved_source.id(),
                name=saved_source.state.name,
                url=saved_source.state.url,
                source_type=saved_source.state.source_type,
                health_status=saved_source.state.health_status,
                is_enabled=saved_source.state.is_enabled,
                inventory_count=inventory_count,
                inventory_hash=inventory_hash,
                created_at=saved_source.state.created_at,
                updated_at=saved_source.state.updated_at,
                created_by=created_by,
                default_audience=saved_source.state.default_audience,
                openapi_url=saved_source.state.openapi_url,
                description=saved_source.state.description,
                auth_mode=saved_source.state.auth_mode,
            )

            processing_time = (time.time() - start_time) * 1000
            log.info(f"Source registered: {dto.id} ({dto.name}) in {processing_time:.2f}ms")

            return self.ok(dto)

    def _build_auth_config(self, command: RegisterSourceCommand) -> AuthConfig | None:
        """Build AuthConfig from command parameters.

        This handles both:
        - auth_type: Authentication for fetching the OpenAPI spec (legacy/explicit)
        - auth_mode: Authentication mode for tool execution

        Args:
            command: The register source command

        Returns:
            AuthConfig or None if no auth specified
        """
        # First, check explicit auth_type (legacy/spec fetching auth)
        if command.auth_type and command.auth_type != "none":
            if command.auth_type == "bearer":
                if command.bearer_token:
                    return AuthConfig.bearer(token=command.bearer_token)

            if command.auth_type == "api_key":
                if command.api_key_name and command.api_key_value:
                    return AuthConfig.api_key(
                        name=command.api_key_name,
                        value=command.api_key_value,
                        location=command.api_key_in or "header",
                    )

            if command.auth_type == "oauth2":
                if command.oauth2_client_id and command.oauth2_client_secret:
                    return AuthConfig.oauth2(
                        token_url=command.oauth2_token_url or "",
                        client_id=command.oauth2_client_id,
                        client_secret=command.oauth2_client_secret,
                        scopes=command.oauth2_scopes or [],
                    )

        # If no explicit auth_type, check auth_mode and build config from fields
        # This handles the UI flow where auth_mode is set with corresponding fields
        if command.auth_mode == "api_key":
            if command.api_key_name and command.api_key_value:
                return AuthConfig.api_key(
                    name=command.api_key_name,
                    value=command.api_key_value,
                    location=command.api_key_in or "header",
                )

        if command.auth_mode == "client_credentials":
            # Source-specific OAuth2 credentials (optional - falls back to service account)
            if command.oauth2_client_id and command.oauth2_client_secret:
                return AuthConfig.oauth2(
                    token_url=command.oauth2_token_url or "",
                    client_id=command.oauth2_client_id,
                    client_secret=command.oauth2_client_secret,
                    scopes=command.oauth2_scopes or [],
                )

        return None

    async def _validate_source_url(
        self,
        url: str,
        source_type: SourceType,
        auth_config: AuthConfig | None,
    ) -> bool:
        """Validate that the URL points to a valid specification.

        Args:
            url: URL to validate
            source_type: Type of source
            auth_config: Authentication configuration

        Returns:
            True if valid, False otherwise
        """
        try:
            adapter = get_adapter_for_type(source_type)
            return await adapter.validate_url(url, auth_config)
        except Exception as e:
            log.warning(f"URL validation error: {e}")
            return False
